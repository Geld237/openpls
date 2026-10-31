"""Analyses préliminaires : statistiques descriptives, données manquantes, normalité, valeurs
aberrantes, biais de méthode commune, taille d'échantillon minimale.

Références
- Mardia (1970) : asymétrie et aplatissement multivariés.
- Curran, West & Finch (1996) ; Kline (2016) : repères |asymétrie| > 2, |aplatissement| > 7.
- Podsakoff et al. (2003) : test à un facteur de Harman.
- Kock (2015) : VIF de colinéarité complète > 3,3 (biais de méthode commune).
- Kock & Hadaya (2018) : méthode de la racine carrée inverse, n_min = (2,486 / |β_min|)² à 5 %.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .model import Model


def indicator_blocks(model: Model | None, columns: list[str]) -> dict[str, str]:
    """Indicateur -> construit (les colonnes hors modèle ne sont pas reprises)."""
    if model is None:
        return {c: "" for c in columns}
    out = {}
    for lv in model.latents:
        for ind in model.measurement.get(lv, []):
            out.setdefault(ind, lv)
    return out


def numeric_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[cols].apply(pd.to_numeric, errors="coerce")


def descriptive_statistics(df: pd.DataFrame, blocks: dict[str, str]) -> pd.DataFrame:
    """Une ligne par indicateur : n, manquants, moyenne, écart-type, médiane, min, max, asymétrie,
    aplatissement (excès), test de Shapiro-Wilk (p) ; repères de non-normalité."""
    x = numeric_frame(df, list(blocks))
    rows = []
    for c, lv in blocks.items():
        v = x[c].dropna().to_numpy(dtype=float)
        n = len(v)
        sw_p = np.nan
        if 3 <= n <= 5000 and np.ptp(v) > 0:
            sw_p = float(stats.shapiro(v).pvalue)
        rows.append({
            "construit": lv, "indicateur": c, "n": n, "manquants": int(x[c].isna().sum()),
            "moyenne": v.mean() if n else np.nan, "écart-type": v.std(ddof=1) if n > 1 else np.nan,
            "médiane": np.median(v) if n else np.nan, "min": v.min() if n else np.nan, "max": v.max() if n else np.nan,
            "asymétrie": float(stats.skew(v, bias=False)) if n > 2 else np.nan,
            "aplatissement": float(stats.kurtosis(v, bias=False)) if n > 3 else np.nan,
            "Shapiro-Wilk p": sw_p,
        })
    return pd.DataFrame(rows).set_index(["construit", "indicateur"])


def missing_summary(df: pd.DataFrame, cols: list[str]) -> dict:
    x = numeric_frame(df, cols)
    raw_missing = df[cols].isna()
    non_numeric = x.isna() & ~raw_missing  # texte dans une colonne numérique
    per_col = pd.DataFrame({
        "manquants": raw_missing.sum(), "non numériques": non_numeric.sum(),
        "% manquants": 100 * x.isna().mean(),
    })
    complete = int(x.notna().all(axis=1).sum())
    return {"columns": per_col, "rows": len(df), "complete_rows": complete,
            "pct_missing": float(100 * x.isna().to_numpy().mean()) if len(df) else 0.0}


def mardia(x: np.ndarray) -> dict:
    """Test de Mardia : asymétrie (chi² à p(p+1)(p+2)/6 ddl) et aplatissement (z)."""
    x = np.asarray(x, dtype=float)
    n, p = x.shape
    xc = x - x.mean(axis=0)
    s = np.cov(xc, rowvar=False, bias=True)
    s_inv = np.linalg.pinv(s)
    y = xc @ s_inv  # par blocs : la matrice n × n complète coûterait O(n²) en mémoire
    b1 = 0.0
    for start in range(0, n, 1000):
        b1 += float(((y[start:start + 1000] @ xc.T) ** 3).sum())
    b1 /= n ** 2
    b2 = float((np.einsum("ij,ij->i", y, xc) ** 2).mean())
    k1 = n * b1 / 6
    df1 = p * (p + 1) * (p + 2) / 6
    z2 = (b2 - p * (p + 2)) / np.sqrt(8 * p * (p + 2) / n)
    return {"asymétrie (b1p)": b1, "chi²": k1, "ddl": df1, "p asymétrie": float(stats.chi2.sf(k1, df1)),
            "aplatissement (b2p)": b2, "z": z2, "p aplatissement": float(2 * stats.norm.sf(abs(z2)))}


def mahalanobis_outliers(df: pd.DataFrame, cols: list[str], alpha: float = 0.001) -> pd.DataFrame:
    """Distance de Mahalanobis au carré de chaque observation complète ; aberrante si p < alpha (chi², p ddl)."""
    x = numeric_frame(df, cols).dropna()
    xc = x.to_numpy(dtype=float) - x.to_numpy(dtype=float).mean(axis=0)
    s_inv = np.linalg.pinv(np.cov(xc, rowvar=False))
    d2 = np.einsum("ij,jk,ik->i", xc, s_inv, xc)
    p = stats.chi2.sf(d2, len(cols))
    out = pd.DataFrame({"D²": d2, "p": p, "aberrante": p < alpha}, index=x.index)
    out.index.name = "observation"
    return out.sort_values("D²", ascending=False)


def harman_single_factor(df: pd.DataFrame, cols: list[str]) -> dict:
    """Part de variance du premier facteur non pivoté (analyse en composantes principales sur les corrélations).
    > 50 % : signe possible de biais de méthode commune (Podsakoff et al. 2003)."""
    x = numeric_frame(df, cols).dropna()
    r = np.corrcoef(x.to_numpy(dtype=float), rowvar=False)
    ev = np.sort(np.linalg.eigvalsh(r))[::-1]
    return {"pct_first": float(100 * ev[0] / ev.sum()), "eigenvalues": ev, "n_eigen_gt1": int((ev > 1).sum())}


def full_collinearity_vif(scores: pd.DataFrame) -> pd.Series:
    """VIF de chaque variable latente régressée sur toutes les autres (Kock 2015) ; > 3,3 : alerte."""
    z = scores.to_numpy(dtype=float)
    r_inv = np.linalg.pinv(np.corrcoef(z, rowvar=False))
    return pd.Series(np.diag(r_inv), index=scores.columns, name="VIF")


def inverse_square_root_n(beta_min: float, alpha: float = 0.05) -> int:
    """Taille minimale (Kock & Hadaya 2018) pour détecter |β_min| avec une puissance de 80 %."""
    z = {0.01: 3.168, 0.05: 2.486, 0.10: 2.123}[alpha]
    return int(np.ceil((z / max(abs(beta_min), 1e-9)) ** 2))


def ten_times_rule(model: Model) -> int:
    """10 × le plus grand nombre de flèches pointant vers un construit (indicateurs formatifs ou chemins)."""
    arrows = [len(model.measurement.get(lv, [])) for lv in model.latents if model.modes.get(lv) == "B"]
    preds: dict[str, int] = {}
    for _, d in model.structural:
        preds[d] = preds.get(d, 0) + 1
    for *_, d in getattr(model, "interactions", []):  # le terme d'interaction est une flèche de plus
        preds[d] = preds.get(d, 0) + 1
    arrows += list(preds.values())
    return 10 * max(arrows, default=1)
