"""Bootstrap pour l'inférence (erreurs-types, t, p-values, IC percentiles)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .algorithm import fit
from .model import Model


def bootstrap(
    data: pd.DataFrame,
    model: Model,
    n_boot: int = 1000,
    seed: int | None = 42,
    alpha: float = 0.05,
    **fit_kwargs,
) -> pd.DataFrame:
    """Retourne, pour chaque chemin : estimation, moyenne bootstrap, SE, t, p, IC."""
    rng = np.random.default_rng(seed)
    full = fit(data, model, **fit_kwargs)
    n = len(data)
    draws, failures = [], 0
    for _ in range(n_boot):
        sample = data.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        try:
            r = fit(sample, model, **fit_kwargs)
        except (ValueError, np.linalg.LinAlgError):
            failures += 1
            continue
        draws.append([r.path_coefficients.loc[s, d] for s, d in model.structural])
    draws = np.array(draws)

    est = np.array([full.path_coefficients.loc[s, d] for s, d in model.structural])
    se = draws.std(axis=0, ddof=1)
    t = est / se
    p = 2 * stats.t.sf(np.abs(t), df=len(draws) - 1)
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)], axis=0)

    out = pd.DataFrame(
        {
            "estimate": est,
            "boot_mean": draws.mean(axis=0),
            "std_error": se,
            "t_value": t,
            "p_value": p,
            f"ci_{alpha/2:.3f}": lo,
            f"ci_{1-alpha/2:.3f}": hi,
        },
        index=[f"{s} -> {d}" for s, d in model.structural],
    )
    out.attrs["n_boot_ok"] = len(draws)
    out.attrs["n_boot_failed"] = failures
    return out
