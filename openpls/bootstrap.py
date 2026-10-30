"""Bootstrap pour l'inférence (erreurs-types, t, p-values, IC percentiles)."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

from .algorithm import fit
from .model import Model


def bootstrap_statistics(
    data: pd.DataFrame,
    model: Model,
    statistic: Callable[..., pd.Series],
    n_boot: int = 1000,
    seed: int | None = 42,
    alpha: float = 0.05,
    progress: Callable[[int, int], None] | None = None,
    **fit_kwargs,
) -> pd.DataFrame:
    """Bootstrap générique : `statistic(résultat) -> pd.Series` est recalculée sur chaque échantillon."""
    rng = np.random.default_rng(seed)
    est = statistic(fit(data, model, **fit_kwargs))
    n = len(data)
    draws, failures = [], 0
    for b in range(n_boot):
        sample = data.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        try:
            draws.append(statistic(fit(sample, model, **fit_kwargs)).reindex(est.index).to_numpy())
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
    out.attrs["n_boot_failed"] = failures
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
