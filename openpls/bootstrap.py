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


def with_confidence_level(boot: pd.DataFrame, draws: np.ndarray, alpha: float) -> pd.DataFrame:
    """Remplace les intervalles percentiles de `boot` par ceux du seuil `alpha`, à partir des tirages.

    t, p et erreurs-types ne dépendent pas du seuil : seul l'intervalle change."""
    out = boot[[c for c in boot.columns if not str(c).startswith("ci_")]].copy()
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)], axis=0)
    out[f"ci_{alpha/2:.3f}"] = lo
    out[f"ci_{1-alpha/2:.3f}"] = hi
    out.attrs = {k: v for k, v in boot.attrs.items() if k != "draws"}
    out.attrs["alpha"] = alpha
    return out
