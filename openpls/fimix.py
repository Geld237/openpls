"""FIMIX-PLS : segmentation par mélange fini (Hahn et al. 2002 ; Sarstedt et al. 2011 ;
Hair et al. 2018, chap. 5).

On part des scores de l'estimation PLS sur tout l'échantillon. Pour S segments, chaque
équation structurelle j s'écrit dans le segment s :  η_j = B_js · η_pred + ζ_js,
ζ_js ~ N(0, ψ_js). L'algorithme EM alterne :
  E : probabilité a posteriori que l'observation i appartienne au segment s ;
  M : proportions, puis régressions pondérées (B_js, ψ_js) par segment.
Plusieurs départs aléatoires ; on garde la meilleure vraisemblance.

Critères pour choisir S (Sarstedt et al. 2011) : AIC3 et CAIC ensemble (ou AIC4 + BIC),
plus l'entropie normée EN (> 0,5 : segments bien séparés).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logsumexp


def _equations(model):
    return [(j, list(model.predecessors(j))) for j in model.endogenous()]


def _em(y: np.ndarray, eqs, s: int, post: np.ndarray, max_iter: int, tol: float):
    n = y.shape[0]
    ll_old = -np.inf
    for it in range(max_iter):
        rho = post.mean(axis=0)
        coefs, psis = [], []
        log_l = np.tile(np.log(np.maximum(rho, 1e-300)), (n, 1))
        for seg in range(s):
            w = post[:, seg]
            cs, ps = [], []
            for j, pred in eqs:
                x = y[:, pred]
                xw = x * w[:, None]
                b = np.linalg.solve(x.T @ xw + 1e-10 * np.eye(len(pred)), xw.T @ y[:, j])
                res = y[:, j] - x @ b
                psi = max((w * res**2).sum() / max(w.sum(), 1e-12), 1e-8)
                cs.append(b)
                ps.append(psi)
                log_l[:, seg] += -0.5 * (np.log(2 * np.pi * psi) + res**2 / psi)
            coefs.append(cs)
            psis.append(ps)
        ll = logsumexp(log_l, axis=1).sum()
        post = np.exp(log_l - logsumexp(log_l, axis=1, keepdims=True))
        if abs(ll - ll_old) < tol:
            break
        ll_old = ll
    return ll, post, coefs, psis, it + 1


def fimix(res, segments=range(1, 5), starts: int = 10, max_iter: int = 5000, tol: float = 1e-7,
          seed: int | None = 42) -> dict:
    """Retourne {"criteria": un tableau par nombre de segments, "solutions": {S: détails}}."""
    model = res.model
    eqs = _equations(model)
    if not eqs:
        raise ValueError("Le modèle n'a pas d'équation structurelle")
    y = res.scores.to_numpy()
    n = y.shape[0]
    rng = np.random.default_rng(seed)
    n_par_eq = sum(len(p) + 1 for _, p in eqs)
    rows, solutions = {}, {}
    for s in segments:
        # départs aléatoires courts (30 itérations), puis on mène les 2 meilleurs à convergence
        trials = [_em(y, eqs, s, rng.dirichlet(np.ones(s), size=n), 30, tol) for _ in range(1 if s == 1 else starts)]
        trials.sort(key=lambda t: -t[0])
        best = None
        for t in trials[:2]:
            out = _em(y, eqs, s, t[1], max_iter, tol)
            if best is None or out[0] > best[0]:
                best = out
        ll, post, coefs, psis, iters = best
        k = (s - 1) + s * n_par_eq
        with np.errstate(divide="ignore", invalid="ignore"):
            ent = -(post * np.log(np.where(post > 0, post, 1))).sum()
        en = 1 - ent / (n * np.log(s)) if s > 1 else np.nan
        rows[s] = {"logL": ll, "AIC": -2 * ll + 2 * k, "AIC3": -2 * ll + 3 * k, "AIC4": -2 * ll + 4 * k,
                   "BIC": -2 * ll + np.log(n) * k, "CAIC": -2 * ll + (np.log(n) + 1) * k, "EN": en,
                   "paramètres": k, "plus petit segment (%)": 100 * post.mean(axis=0).min()}
        lvs = model.latents
        paths = {}
        for seg in range(s):
            for (j, pred), b in zip(eqs, coefs[seg]):
                for i, v in zip(pred, b):
                    paths.setdefault(f"{lvs[i]} -> {lvs[j]}", {})[f"segment {seg + 1}"] = v
        r2 = {f"segment {seg + 1}": {lvs[j]: 1 - psis[seg][q] / np.average(
                  (y[:, j] - np.average(y[:, j], weights=post[:, seg])) ** 2, weights=post[:, seg])
              for q, (j, _) in enumerate(eqs)} for seg in range(s)}
        order = np.argsort(-post.mean(axis=0))  # segments triés du plus grand au plus petit
        cols = [f"segment {i + 1}" for i in order]
        ren = {c: f"segment {r + 1}" for r, c in enumerate(cols)}
        solutions[s] = {
            "sizes": pd.Series(post.mean(axis=0)[order], index=[ren[c] for c in cols], name="proportion"),
            "paths": pd.DataFrame(paths).T[cols].rename(columns=ren),
            "r_squared": pd.DataFrame(r2)[cols].rename(columns=ren),
            "posterior": pd.DataFrame(post[:, order], index=res.scores.index,
                                      columns=[ren[c] for c in cols]),
            "membership": pd.Series(np.argmax(post[:, order], axis=1) + 1, index=res.scores.index,
                                    name="segment"),
            "iterations": iters,
        }
    crit = pd.DataFrame.from_dict(rows, orient="index")
    crit.index.name = "segments"
    return {"criteria": crit, "solutions": solutions}
