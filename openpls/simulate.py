"""Génère des données dont la vraie structure est connue — sert à valider l'implémentation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(n: int = 500, loading: float = 0.8, seed: int = 0) -> pd.DataFrame:
    """Modèle vrai :  XI1 -> ETA1 (0.5), XI2 -> ETA1 (0.3), ETA1 -> ETA2 (0.6) ; corr(XI1, XI2) = 0.3.
    Chaque latente a 3 indicateurs réflectifs de chargement `loading`."""
    rng = np.random.default_rng(seed)
    xi = rng.multivariate_normal([0, 0], [[1, 0.3], [0.3, 1]], n)
    b1, b2, b3 = 0.5, 0.3, 0.6
    var_eta1 = b1**2 + b2**2 + 2 * b1 * b2 * 0.3
    eta1 = b1 * xi[:, 0] + b2 * xi[:, 1] + rng.normal(0, np.sqrt(1 - var_eta1), n)
    eta2 = b3 * eta1 + rng.normal(0, np.sqrt(1 - b3**2), n)
    latents = {"XI1": xi[:, 0], "XI2": xi[:, 1], "ETA1": eta1, "ETA2": eta2}
    cols = {}
    for name, lv in latents.items():
        for k in range(1, 4):
            cols[f"{name.lower()}_{k}"] = loading * lv + rng.normal(0, np.sqrt(1 - loading**2), n)
    return pd.DataFrame(cols)
