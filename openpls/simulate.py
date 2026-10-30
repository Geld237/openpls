"""Génère des données dont la vraie structure est connue — sert à valider l'implémentation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(n: int = 500, loading: float = 0.8, seed: int = 0, direct: float = 0.0,
             eta_path: float = 0.6) -> pd.DataFrame:
    """Modèle vrai :  XI1 -> ETA1 (0.5), XI2 -> ETA1 (0.3), ETA1 -> ETA2 (0.6),
    XI1 -> ETA2 (`direct`, 0 par défaut) ; corr(XI1, XI2) = 0.3.
    `eta_path` remplace le 0.6 de ETA1 -> ETA2 (utile pour simuler des groupes différents).
    Chaque latente a 3 indicateurs réflectifs de chargement `loading`.

    Effet indirect vrai XI1 -> ETA1 -> ETA2 = 0.5 * 0.6 = 0.30."""
    rng = np.random.default_rng(seed)
    xi = rng.multivariate_normal([0, 0], [[1, 0.3], [0.3, 1]], n)
    b1, b2, b3 = 0.5, 0.3, eta_path
    var_eta1 = b1**2 + b2**2 + 2 * b1 * b2 * 0.3
    eta1 = b1 * xi[:, 0] + b2 * xi[:, 1] + rng.normal(0, np.sqrt(1 - var_eta1), n)
    cov_eta1_xi1 = b1 + b2 * 0.3
    var_eta2 = b3**2 + direct**2 + 2 * b3 * direct * cov_eta1_xi1
    if var_eta2 >= 1:
        raise ValueError("Effet direct trop fort : variance expliquée > 1")
    eta2 = b3 * eta1 + direct * xi[:, 0] + rng.normal(0, np.sqrt(1 - var_eta2), n)
    latents = {"XI1": xi[:, 0], "XI2": xi[:, 1], "ETA1": eta1, "ETA2": eta2}
    cols = {}
    for name, lv in latents.items():
        for k in range(1, 4):
            cols[f"{name.lower()}_{k}"] = loading * lv + rng.normal(0, np.sqrt(1 - loading**2), n)
    return pd.DataFrame(cols)


def simulate_moderation(n: int = 500, loading: float = 0.8, seed: int = 0,
                        b_x: float = 0.4, b_m: float = 0.2, b_xm: float = 0.25) -> pd.DataFrame:
    """Modèle vrai : Y = b_x·X + b_m·M + b_xm·X·M + erreur, X et M normales indépendantes
    (donc X·M de variance 1 et les coefficients sont directement standardisés).
    Indicateurs x_1..3, m_1..3, y_1..3."""
    rng = np.random.default_rng(seed)
    x, m = rng.normal(size=(2, n))
    explained = b_x**2 + b_m**2 + b_xm**2
    if explained >= 1:
        raise ValueError("Variance expliquée > 1")
    y = b_x * x + b_m * m + b_xm * x * m + rng.normal(0, np.sqrt(1 - explained), n)
    cols = {}
    for name, lv in {"x": x, "m": m, "y": y}.items():
        for k in range(1, 4):
            cols[f"{name}_{k}"] = loading * lv + rng.normal(0, np.sqrt(1 - loading**2), n)
    return pd.DataFrame(cols)


def simulate_higher_order(n: int = 500, loading: float = 0.8, seed: int = 0,
                          second_order=(0.8, 0.75, 0.7), b_in: float = 0.5, b_out: float = 0.6) -> pd.DataFrame:
    """Modèle vrai de second ordre (réflectif-réflectif) :
    X -> HOC (b_in), HOC -> Y (b_out) ; HOC -> L1, L2, L3 (chargements `second_order`).
    Indicateurs x_1..3, l1_1..3, l2_1..3, l3_1..3, y_1..3."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    hoc = b_in * x + rng.normal(0, np.sqrt(1 - b_in**2), n)
    y = b_out * hoc + rng.normal(0, np.sqrt(1 - b_out**2), n)
    lat = {"x": x, "y": y}
    for k, lam in enumerate(second_order, 1):
        lat[f"l{k}"] = lam * hoc + rng.normal(0, np.sqrt(1 - lam**2), n)
    cols = {}
    for name in ["x"] + [f"l{k}" for k in range(1, len(second_order) + 1)] + ["y"]:
        for k in range(1, 4):
            cols[f"{name}_{k}"] = loading * lat[name] + rng.normal(0, np.sqrt(1 - loading**2), n)
    return pd.DataFrame(cols)
