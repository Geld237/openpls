"""Bootstrap pour l'inférence (erreurs-types, t, p-values, IC percentiles)."""
from __future__ import annotations

import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

from .algorithm import ConvergenceWarning, fit
from .model import Model


class BootstrapWarning(UserWarning):
    """Tirages bootstrap en échec, non convergés ou inadmissibles : l'inférence peut être biaisée."""


FAILURE_ALERT = 0.05  # au-delà de 5 % de tirages en échec, l'inférence n'est pas fiable


def _diagnose(res) -> tuple[bool, bool]:
    """(non convergé, inadmissible) pour un tirage : |chemin| > 1 ou |chargement| > 1 (PLSc)."""
    meas = res.measurement_result
    nonconv = not (res.converged and meas.converged)
    inadm = bool((res.path_coefficients.abs().to_numpy() > 1 + 1e-9).any()
                 or (meas.outer_loadings.abs().to_numpy() > 1 + 1e-9).any())
    return nonconv, inadm


def bootstrap_statistics(
    data: pd.DataFrame,
    model: Model,
    statistic: Callable[..., pd.Series],
    n_boot: int = 1000,
    seed: int | None = 42,
    alpha: float = 0.05,
    progress: Callable[[int, int], None] | None = None,
    keep_draws: bool = False,
    **fit_kwargs,
) -> pd.DataFrame:
    """Bootstrap générique : `statistic(résultat) -> pd.Series` est recalculée sur chaque échantillon.

    `keep_draws=True` conserve les tirages dans `attrs["draws"]` (tableau tirages × statistiques) :
    `with_confidence_level` peut alors recalculer les intervalles à un autre seuil sans relancer."""
    rng = np.random.default_rng(seed)
    est = statistic(fit(data, model, **fit_kwargs))
    n = len(data)
    draws, failures, nonconv, inadm = [], 0, 0, 0
    for b in range(n_boot):
        sample = data.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        try:
            with warnings.catch_warnings():  # non-convergence comptée ci-dessous
                warnings.simplefilter("ignore", ConvergenceWarning)
                r = fit(sample, model, **fit_kwargs)
            draws.append(statistic(r).reindex(est.index).to_numpy())
            nc, ia = _diagnose(r)
            nonconv += nc
            inadm += ia
        except (ValueError, np.linalg.LinAlgError):
            failures += 1
        if progress:
            progress(b + 1, n_boot)
    draws = np.array(draws)
    if len(draws) < 2:
        raise RuntimeError("Bootstrap impossible : trop d'échantillons en échec")

    e = est.to_numpy()
    se = draws.std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = e / se
    p = 2 * stats.t.sf(np.abs(t), df=len(draws) - 1)
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)], axis=0)
    out = pd.DataFrame(
        {
            "estimate": e,
            "boot_mean": draws.mean(axis=0),
            "std_error": se,
            "t_value": t,
            "p_value": p,
            f"ci_{alpha/2:.3f}": lo,
            f"ci_{1-alpha/2:.3f}": hi,
        },
        index=est.index,
    )
    out.attrs["n_boot_ok"] = len(draws)
    if keep_draws:
        out.attrs["draws"] = draws
    out.attrs["n_boot_failed"] = failures
    out.attrs["n_boot_nonconverged"] = nonconv
    out.attrs["n_boot_inadmissible"] = inadm
    out.attrs["failure_rate"] = failures / n_boot
    msgs = []
    if failures:
        msgs.append(f"{failures}/{n_boot} tirages en échec ont été exclus : les tirages restants ne sont pas "
                    "représentatifs, erreurs-types et intervalles peuvent être biaisés"
                    + (" (inférence NON fiable)" if failures / n_boot > FAILURE_ALERT else ""))
    if nonconv:
        msgs.append(f"{nonconv}/{n_boot} tirages n'ont pas convergé")
    if inadm:
        msgs.append(f"{inadm}/{n_boot} tirages ont un coefficient ou un chargement > 1 en valeur absolue "
                    "(solution inadmissible, fréquent en PLSc avec de petits échantillons)")
    out.attrs["warnings"] = msgs
    for m in msgs:
        warnings.warn(m, BootstrapWarning, stacklevel=2)
    return out


def _paths(res) -> pd.Series:
    m = res.model
    return pd.Series(
        [res.path_coefficients.loc[s, d] for s, d in m.structural],
        index=[f"{s} -> {d}" for s, d in m.structural],
    )


def bootstrap(
    data: pd.DataFrame,
    model: Model,
    n_boot: int = 1000,
    seed: int | None = 42,
    alpha: float = 0.05,
    **fit_kwargs,
) -> pd.DataFrame:
    """Bootstrap des coefficients de chemin : estimation, moyenne bootstrap, SE, t, p, IC."""
    return bootstrap_statistics(data, model, _paths, n_boot=n_boot, seed=seed, alpha=alpha, **fit_kwargs)


def jackknife(data: pd.DataFrame, model, statistic, max_groups: int = 200, progress=None, **fit_kwargs) -> np.ndarray:
    """Valeurs jackknife de `statistic` (une ligne par groupe d'observations retiré), pour l'accélération BCa.
    Au-delà de `max_groups` observations, jackknife par blocs (groupes consécutifs de taille égale)."""
    from .algorithm import fit

    n = len(data)
    # groupes tirés au hasard (graine fixe) : des données triées ne biaisent pas l'accélération
    groups = np.array_split(np.random.default_rng(0).permutation(n), min(n, max_groups))
    est_index = statistic(fit(data, model, **fit_kwargs)).index
    out, failures = [], 0
    for i, g in enumerate(groups):
        keep = np.setdiff1d(np.arange(n), g)
        try:
            out.append(statistic(fit(data.iloc[keep].reset_index(drop=True), model, **fit_kwargs))
                       .reindex(est_index).to_numpy())
        except Exception:  # noqa: BLE001 - un échec isolé ne bloque pas le calcul
            failures += 1
        if progress:
            progress(i + 1, len(groups))
    if failures:
        import warnings

        warnings.warn(f"{failures}/{len(groups)} tirages en échec (jackknife)", stacklevel=2)
    return np.array(out)


def bca_bounds(estimate: np.ndarray, draws: np.ndarray, jack: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """Intervalles BCa (Efron 1987) : correction du biais z0 et accélération a (jackknife)."""
    est = np.asarray(estimate, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        prop = np.clip((draws < est).mean(axis=0) + 0.5 * (draws == est).mean(axis=0), 1e-6, 1 - 1e-6)
        z0 = stats.norm.ppf(prop)
        jm = np.nanmean(jack, axis=0)
        num = np.nansum((jm - jack) ** 3, axis=0)
        den = 6 * np.nansum((jm - jack) ** 2, axis=0) ** 1.5
        acc = np.where(den > 0, num / den, 0.0)
        bounds = []
        for q in (alpha / 2, 1 - alpha / 2):
            zq = stats.norm.ppf(q)
            adj = stats.norm.cdf(z0 + (z0 + zq) / (1 - acc * (z0 + zq)))
            adj = np.where(np.isfinite(adj), adj, q)
            bounds.append(np.array([np.nanpercentile(draws[:, j], 100 * adj[j]) for j in range(draws.shape[1])]))
    return bounds[0], bounds[1]


def with_confidence_level(boot: pd.DataFrame, draws: np.ndarray, alpha: float, jack: np.ndarray | None = None
                          ) -> pd.DataFrame:
    """Remplace les intervalles de `boot` par ceux du seuil `alpha`, à partir des tirages : percentiles,
    ou BCa si les valeurs jackknife `jack` sont fournies.

    t, p et erreurs-types ne dépendent pas du seuil : seul l'intervalle change."""
    out = boot[[c for c in boot.columns if not str(c).startswith("ci_")]].copy()
    if jack is not None and len(jack) > 2:
        lo, hi = bca_bounds(boot["estimate"].to_numpy(), draws, jack, alpha)
        out.attrs["ci_method"] = "BCa"
    else:
        lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)], axis=0)
    out[f"ci_{alpha/2:.3f}"] = lo
    out[f"ci_{1-alpha/2:.3f}"] = hi
    method = out.attrs.get("ci_method", "percentile")
    out.attrs = {k: v for k, v in boot.attrs.items() if k != "draws"}
    out.attrs["alpha"] = alpha
    out.attrs["ci_method"] = method
    return out
