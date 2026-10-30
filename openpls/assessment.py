"""Critères d'évaluation du modèle de mesure (Hair et al., Henseler et al. 2015)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def quality_criteria(res) -> pd.DataFrame:
    """Alpha de Cronbach, fiabilité composite (rho_c) et AVE pour chaque latente réflective."""
    rows = {}
    for lv in res.model.latents:
        inds = res.model.measurement[lv]
        lam = res.outer_loadings[lv].to_numpy()
        x = res.data_std[inds].to_numpy()
        m = len(inds)
        if m > 1:
            item_var = x.var(axis=0, ddof=1).sum()
            total_var = x.sum(axis=1).var(ddof=1)
            alpha = m / (m - 1) * (1 - item_var / total_var)
        else:
            alpha = np.nan
        s = lam.sum() ** 2
        rho_c = s / (s + (1 - lam**2).sum())
        ave = (lam**2).mean()
        rows[lv] = {"cronbach_alpha": alpha, "rho_A": res.rho_a[lv], "rho_c": rho_c, "AVE": ave}
    return pd.DataFrame(rows).T


def fornell_larcker(res) -> pd.DataFrame:
    """Diagonale = racine de l'AVE, hors diagonale = corrélations entre latentes."""
    corr = res.scores.corr()
    ave = quality_criteria(res)["AVE"]
    out = corr.copy()
    for lv in out.index:
        out.loc[lv, lv] = np.sqrt(ave[lv])
    return out


def htmt(res) -> pd.DataFrame:
    """Ratio heterotrait-monotrait (Henseler, Ringle & Sarstedt 2015). Seuil usuel : < 0.85 / 0.90."""
    lvs = res.model.latents
    corr = res.data_std.corr().abs()
    out = pd.DataFrame(np.nan, index=lvs, columns=lvs)

    def mono(lv):
        inds = res.model.measurement[lv]
        if len(inds) < 2:
            return np.nan
        c = corr.loc[inds, inds].to_numpy()
        return c[np.triu_indices(len(inds), 1)].mean()

    for a_i, a in enumerate(lvs):
        for b in lvs[a_i + 1 :]:
            hetero = corr.loc[res.model.measurement[a], res.model.measurement[b]].to_numpy().mean()
            val = hetero / np.sqrt(mono(a) * mono(b))
            out.loc[b, a] = val
    return out


def f_squared(res, data, **fit_kwargs) -> pd.DataFrame:
    """Taille d'effet f² : (R²_inclus - R²_exclu) / (1 - R²_inclus)."""
    from .algorithm import fit
    from .model import Model

    m = res.model
    rows = []
    for src, dst in m.structural:
        reduced = [p for p in m.structural if p != (src, dst)]
        r2_in = res.r_squared[dst]
        if not any(d == dst for _, d in reduced):
            r2_out = 0.0
        else:
            sub = fit(data, Model(m.measurement, reduced, dict(m.modes)), **fit_kwargs)
            r2_out = sub.r_squared[dst]
        rows.append({"path": f"{src} -> {dst}", "f2": (r2_in - r2_out) / (1 - r2_in)})
    return pd.DataFrame(rows).set_index("path")
