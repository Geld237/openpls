"""Effets directs, indirects et totaux ; analyse de médiation.

Avec B la matrice des coefficients de chemin (B[i, j] = effet direct de i sur j),
dans un modèle récursif : effets totaux T = B + B² + B³ + ... = (I - B)^-1 - I,
effets indirects = T - B. Un effet indirect spécifique est le produit des coefficients
le long d'un chemin particulier (ex. A -> M1 -> M2 -> Y).

Typologie de la médiation : Zhao, Lynch & Chen (2010), reprise par Hair et al. (2022).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _b(res) -> np.ndarray:
    return res.path_coefficients.to_numpy()


def total_effects(res) -> pd.DataFrame:
    b = _b(res)
    k = b.shape[0]
    t = np.linalg.inv(np.eye(k) - b) - np.eye(k)
    lvs = res.model.latents
    return pd.DataFrame(t, index=lvs, columns=lvs)


def total_indirect_effects(res) -> pd.DataFrame:
    return total_effects(res) - res.path_coefficients


def mediation_paths(model, min_len: int = 2) -> list[list[int]]:
    """Tous les chemins orientés de longueur >= min_len (en nombre d'arcs) du modèle structurel."""
    k = len(model.latents)
    out: list[list[int]] = []

    def walk(path):
        if len(path) - 1 >= min_len:
            out.append(path)
        for nxt in model.successors(path[-1]):
            walk(path + [int(nxt)])

    for start in range(k):
        walk([start])
    return out


def specific_indirect_effects(res) -> pd.Series:
    b = _b(res)
    lvs = res.model.latents
    vals = {}
    for p in mediation_paths(res.model):
        vals[" -> ".join(lvs[i] for i in p)] = float(np.prod([b[p[i], p[i + 1]] for i in range(len(p) - 1)]))
    return pd.Series(vals, dtype=float)


def effect_statistics(res) -> pd.Series:
    """Toutes les quantités qu'on veut bootstrapper, dans une seule série plate."""
    m = res.model
    lvs = m.latents
    b = res.path_coefficients
    t = total_effects(res)
    stats = {}
    for s, d in m.structural:
        stats[("direct", f"{s} -> {d}")] = b.loc[s, d]
    for name, v in specific_indirect_effects(res).items():
        stats[("specific_indirect", name)] = v
    # couples (i, j) reliés par au moins un chemin, et ceux reliés par un chemin de longueur >= 2
    reach = {(p[0], p[-1]) for p in mediation_paths(m, min_len=1)}
    mediated = {(p[0], p[-1]) for p in mediation_paths(m, min_len=2)}
    for i, j in sorted(mediated):
        stats[("total_indirect", f"{lvs[i]} -> {lvs[j]}")] = t.iloc[i, j] - b.iloc[i, j]
    for i, j in sorted(reach):
        stats[("total", f"{lvs[i]} -> {lvs[j]}")] = t.iloc[i, j]
    return pd.Series(stats, dtype=float)


def classify_mediation(direct_sig: bool, indirect_sig: bool, direct: float, indirect: float) -> str:
    """Typologie de Zhao et al. (2010)."""
    if indirect_sig and direct_sig:
        return "complémentaire (partielle)" if np.sign(direct) == np.sign(indirect) else "compétitive (partielle)"
    if indirect_sig:
        return "indirecte seule (totale)"
    if direct_sig:
        return "directe seule (pas de médiation)"
    return "aucun effet"


def mediation_analysis(data, model, n_boot: int = 2000, seed: int | None = 42, alpha: float = 0.05, **fit_kwargs):
    """Teste chaque effet indirect spécifique par bootstrap et classe la médiation.

    Retourne (tableau_médiation, tableau_bootstrap_complet).
    Significativité = IC percentile qui exclut 0 (recommandation Hair et al. 2022)."""
    from .bootstrap import bootstrap_statistics

    boot = bootstrap_statistics(data, model, effect_statistics, n_boot=n_boot, seed=seed, alpha=alpha, **fit_kwargs)
    lo, hi = boot.columns[-2], boot.columns[-1]
    sig = (boot[lo] > 0) | (boot[hi] < 0)

    rows = []
    for (kind, name), r in boot.iterrows():
        if kind != "specific_indirect":
            continue
        nodes = name.split(" -> ")
        pair = f"{nodes[0]} -> {nodes[-1]}"
        direct_key = ("direct", pair)
        has_direct = direct_key in boot.index
        d_est = boot.loc[direct_key, "estimate"] if has_direct else 0.0
        d_sig = bool(sig[direct_key]) if has_direct else False
        rows.append(
            {
                "chemin": name,
                "effet_indirect": r["estimate"],
                lo: r[lo],
                hi: r[hi],
                "p_value": r["p_value"],
                "indirect_significatif": bool(sig[(kind, name)]),
                "effet_direct": d_est if has_direct else np.nan,
                "direct_significatif": d_sig if has_direct else np.nan,
                "type_mediation": (
                    classify_mediation(d_sig, bool(sig[(kind, name)]), d_est, r["estimate"])
                    if has_direct
                    else ("indirecte (type indéterminé : chemin direct non estimé)"
                          if sig[(kind, name)] else "aucun effet indirect")
                ),
            }
        )
    return pd.DataFrame(rows).set_index("chemin"), boot
