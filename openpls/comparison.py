"""Comparaison de modèles concurrents (critères d'information) et analyse tétrade confirmatoire (CTA-PLS).

- Sharma, Sarstedt, Shmueli, Kim & Thiele (2019), PLS-based model selection, JAIS ;
  Sharma, Shmueli, Sarstedt, Danks & Ray (2021), Prediction-oriented model selection, Psychological Methods.
- Bollen & Ting (2000) ; Gudergan, Ringle, Wende & Will (2008), Confirmatory tetrad analysis in PLS, JBR.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def information_criteria(results: dict, target: str) -> pd.DataFrame:
    """`results` : {nom: (résultat PLS, n)}. Critères pour l'équation de `target` :
    AIC, BIC, HQ et GM (Geweke-Meese), plus les poids d'Akaike et de BIC. Plus petit = meilleur."""
    from .higher_order import structural_view

    rows = {}
    for name, (res, n) in results.items():
        sv = structural_view(res)
        if target not in sv.r_squared.index:
            raise ValueError(f"{target} n'est pas expliquée par le modèle {name}")
        r2 = float(sv.r_squared[target])
        p = int(sum(1 for s, d in sv.model.structural if d == target)
                + sum(1 for *_, d in getattr(sv.model, "interactions", []) if d == target))
        sse = (1 - r2) * (n - 1)  # scores standardisés : variance totale n - 1
        rows[name] = {"R²": r2, "prédicteurs": p, "n": n, "SSE": sse}  # paramètres : prédicteurs + constante
    tbl = pd.DataFrame(rows).T
    n = tbl["n"].astype(float)
    ll = n * np.log(tbl["SSE"].astype(float) / n)
    p = tbl["prédicteurs"].astype(float) + 1  # Sharma et al. (2019) : p_k = prédicteurs + constante
    tbl["AIC"] = ll + 2 * p
    tbl["BIC"] = ll + p * np.log(n)
    tbl["HQ"] = ll + 2 * p * np.log(np.log(n))
    full = tbl["prédicteurs"].astype(float).idxmax()  # σ² du modèle le plus général
    sigma2 = float(tbl.loc[full, "SSE"]) / max(float(tbl.loc[full, "n"]) - float(tbl.loc[full, "prédicteurs"]) - 1, 1)  # noqa: E501
    tbl["GM"] = tbl["SSE"].astype(float) / sigma2 + p * np.log(n)
    for crit in ("AIC", "BIC"):
        delta = tbl[crit] - tbl[crit].min()
        w = np.exp(-delta / 2)
        tbl[f"poids {crit}"] = w / w.sum()
    tbl["prédicteurs"] = tbl["prédicteurs"].astype(int)
    tbl["n"] = tbl["n"].astype(int)
    return tbl.drop(columns="SSE")


# ---------------------------------------------------------------- CTA-PLS
def _tetrads(cov: np.ndarray, quads: list[tuple]) -> np.ndarray:
    out = []
    for g, h, i, j in quads:
        out.append(cov[g, h] * cov[i, j] - cov[g, i] * cov[h, j])
        out.append(cov[g, h] * cov[i, j] - cov[g, j] * cov[h, i])
    return np.array(out)


def cta(data: pd.DataFrame, model, n_boot: int = 1000, alpha: float = 0.10, seed: int = 0,
        progress=None) -> dict:
    """CTA-PLS pour chaque bloc d'au moins 4 indicateurs. Pour chaque quadruplet d'indicateurs, deux tétrades
    (la troisième s'en déduit) ; intervalles bootstrap percentiles corrigés par Bonferroni sur le nombre de
    tétrades réellement testées dans le bloc (2 × C(k, 4)), ce qui garde le taux de rejet à tort sous le seuil.
    Le modèle réflectif est compatible avec les données si tous les intervalles contiennent 0
    (Gudergan et al. 2008, seuil 10 % recommandé)."""
    rng = np.random.default_rng(seed)
    blocks = {lv: inds for lv, inds in model.measurement.items() if len(inds) >= 4}
    if not blocks:
        raise ValueError("La CTA-PLS demande au moins un bloc de 4 indicateurs ou plus")
    rows, verdicts = [], {}
    for b_i, (lv, inds) in enumerate(blocks.items()):
        x = data[inds].to_numpy(dtype=float)
        x = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
        quads = list(combinations(range(len(inds)), 4))
        est = _tetrads(np.cov(x, rowvar=False), quads)
        draws = np.empty((n_boot, len(est)))
        n = len(x)
        for r in range(n_boot):
            idx = rng.integers(0, n, n)
            draws[r] = _tetrads(np.cov(x[idx], rowvar=False), quads)
            if progress and r % 50 == 0:
                progress((b_i + r / n_boot) / len(blocks))
        a_adj = alpha / len(est)  # Bonferroni sur toutes les tétrades testées
        se = draws.std(axis=0, ddof=1)
        # intervalle normal (erreur-type bootstrap) : les percentiles extrêmes qu'impose Bonferroni
        # seraient très mal estimés avec quelques centaines de tirages (rejets à tort trop fréquents)
        from scipy import stats as _st

        z = _st.norm.ppf(1 - a_adj / 2)
        lo, hi = est - z * se, est + z * se
        names = []
        for g, h, i, j in quads:
            a, b, c, d = (inds[q] for q in (g, h, i, j))
            names += [f"τ({a},{b},{c},{d})", f"τ({a},{b},{d},{c})"]
        for nm, e, s, l_, h_ in zip(names, est, se, lo, hi):
            rows.append({"construit": lv, "tétrade": nm, "valeur": e, "erreur-type": s,
                         "IC bas (Bonferroni)": l_, "IC haut (Bonferroni)": h_, "différente de 0": not (l_ <= 0 <= h_)})
        verdicts[lv] = not any(not (l_ <= 0 <= h_) for l_, h_ in zip(lo, hi))
    tbl = pd.DataFrame(rows).set_index(["construit", "tétrade"])
    summary = pd.DataFrame({"indicateurs": {lv: len(i) for lv, i in blocks.items()},
                            "tétrades testées": tbl.groupby(level=0).size(),
                            "tétrades ≠ 0": tbl.groupby(level=0)["différente de 0"].sum().astype(int),
                            "réflectif compatible": pd.Series(verdicts)})
    return {"tetrads": tbl, "summary": summary, "alpha": alpha}
