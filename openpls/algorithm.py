"""Algorithme PLS-SEM (Wold 1982 ; Lohmöller 1989).

Boucle itérative :
  1. approximation externe  : Y_j = X_j w_j
  2. approximation interne  : Z_j = sum_i e_ij Y_i   (schéma path / factorial / centroid)
  3. mise à jour des poids  : mode A (corrélations) ou mode B (régression)
  4. répéter jusqu'à convergence, puis estimer chemins, chargements et R².
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .model import Model


def _standardize(a: np.ndarray) -> np.ndarray:
    sd = a.std(axis=0, ddof=1)
    if np.any(sd == 0):
        raise ValueError("Un indicateur a une variance nulle")
    return (a - a.mean(axis=0)) / sd


def _ols(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(x, y, rcond=None)[0]


@dataclass
class PLSResult:
    model: Model
    outer_weights: pd.Series
    outer_loadings: pd.Series
    path_coefficients: pd.DataFrame
    r_squared: pd.Series
    scores: pd.DataFrame
    data_std: pd.DataFrame
    rho_a: pd.Series
    iterations: int
    converged: bool
    consistent: bool = False
    spec: Model | None = None          # modèle tel que spécifié (avec interactions) si différent de `model`
    stage1: "PLSResult | None" = None  # modération en deux étapes : estimation sans interaction
    moderation: str | None = None

    @property
    def measurement_result(self) -> "PLSResult":
        """Résultat à utiliser pour évaluer le modèle de mesure."""
        return self.stage1 if self.stage1 is not None else self

    def summary(self) -> str:
        from .assessment import quality_criteria, htmt

        algo = "PLSc (consistent)" if self.consistent else "PLS"
        lines = [f"{algo} — convergence : {'oui' if self.converged else 'NON'} en {self.iterations} itérations", ""]
        lines.append("== Coefficients de chemin ==")
        for src, dst in self.model.structural:
            lines.append(f"  {src:>12} -> {dst:<12} {self.path_coefficients.loc[src, dst]: .4f}")
        lines.append("\n== R² ==")
        for lv, r2 in self.r_squared.items():
            lines.append(f"  {lv:<12} {r2: .4f}")
        lines.append("\n== Chargements externes ==")
        for (lv, ind), val in self.outer_loadings.items():
            lines.append(f"  {lv:<12} {ind:<10} {val: .4f}")
        lines.append("\n== Fiabilité et validité convergente ==")
        lines.append(quality_criteria(self).round(4).to_string())
        lines.append("\n== HTMT ==")
        lines.append(htmt(self).round(4).to_string())
        return "\n".join(lines)


def _inner_weights(scores: np.ndarray, model: Model, scheme: str) -> np.ndarray:
    k = scores.shape[1]
    corr = np.corrcoef(scores, rowvar=False)
    adj = (model.path + model.path.T) > 0
    e = np.zeros((k, k))  # e[i, j] = poids de Y_i dans le proxy interne de Z_j
    if scheme == "centroid":
        e = np.sign(corr) * adj
    elif scheme == "factorial":
        e = corr * adj
    elif scheme == "path":
        for j in range(k):
            for i in model.successors(j):
                e[i, j] = corr[i, j]
            pred = model.predecessors(j)
            if len(pred):
                e[pred, j] = _ols(scores[:, j], scores[:, pred])
    else:
        raise ValueError(f"Schéma inconnu : {scheme}")
    # Latente isolée (aucun voisin structurel, ex. modèle réduit pour f²) : proxy = elle-même
    for j in range(k):
        if not adj[:, j].any():
            e[j, j] = 1.0
    return e


def fit(
    data: pd.DataFrame,
    model: Model,
    scheme: str = "path",
    max_iter: int = 300,
    tol: float = 1e-7,
    consistent: bool = False,
    moderation: str = "two_stage",
) -> PLSResult:
    """Estime un modèle PLS-SEM sur `data` (un indicateur par colonne).

    consistent=True active PLSc (Dijkstra & Henseler 2015) : corrige l'atténuation
    des blocs réflectifs pour estimer des modèles de facteurs communs.
    moderation : méthode pour les termes d'interaction X:M — "two_stage" (défaut),
    "product_indicator" ou "orthogonal" (voir openpls.moderation)."""
    if model.interactions:
        from .moderation import fit_moderated

        return fit_moderated(data, model, method=moderation, scheme=scheme, max_iter=max_iter,
                             tol=tol, consistent=consistent)
    return _fit_plain(data, model, scheme=scheme, max_iter=max_iter, tol=tol, consistent=consistent)


def _fit_plain(data, model, scheme="path", max_iter=300, tol=1e-7, consistent=False) -> PLSResult:
    missing = [c for c in model.indicators if c not in data.columns]
    if missing:
        raise KeyError(f"Indicateurs absents des données : {missing}")
    raw = data[model.indicators].to_numpy(dtype=float)
    if np.isnan(raw).any():
        raise ValueError("Valeurs manquantes : traite-les avant l'estimation")
    x = _standardize(raw)
    n = x.shape[0]

    blocks, start = [], 0
    for lv in model.latents:
        m = len(model.measurement[lv])
        blocks.append(slice(start, start + m))
        start += m
    k = len(model.latents)

    weights = [np.ones(b.stop - b.start) for b in blocks]

    def outer_scores(ws):
        y = np.column_stack([x[:, b] @ w for b, w in zip(blocks, ws)])
        sd = y.std(axis=0, ddof=1)
        return y / sd, [w / s for w, s in zip(ws, sd)]

    y, weights = outer_scores(weights)
    converged, it = False, 0
    for it in range(1, max_iter + 1):
        e = _inner_weights(y, model, scheme)
        z = y @ e
        new_w = []
        for j, b in enumerate(blocks):
            xj = x[:, b]
            if model.modes[model.latents[j]] == "A":
                new_w.append(xj.T @ z[:, j] / (n - 1))
            else:
                new_w.append(_ols(z[:, j], xj))
        y, new_w = outer_scores(new_w)
        delta = max(np.max(np.abs(a - b_)) for a, b_ in zip(new_w, weights))
        weights = new_w
        if delta < tol:
            converged = True
            break

    # Estimations finales
    idx = pd.MultiIndex.from_tuples(
        [(lv, ind) for lv in model.latents for ind in model.measurement[lv]], names=["latent", "indicator"]
    )
    w_flat = np.concatenate(weights)
    loadings = np.concatenate(
        [[np.corrcoef(x[:, c], y[:, j])[0, 1] for c in range(b.start, b.stop)] for j, b in enumerate(blocks)]
    )

    # rho_A de Dijkstra & Henseler (2015) : fiabilité de chaque composite
    rho_a = np.ones(k)
    c_fac = np.ones(k)
    s_all = np.corrcoef(x, rowvar=False)
    for j, b in enumerate(blocks):
        w = weights[j]
        if model.modes[model.latents[j]] != "A" or len(w) < 2:
            continue
        s = s_all[b, b]
        ww = np.outer(w, w)
        c2 = (w @ (s - np.diag(np.diag(s))) @ w) / (w @ (ww - np.diag(np.diag(ww))) @ w)
        if not c2 > 0:  # bloc dégénéré (corrélations négatives) : rho_A indéfini
            if consistent:
                raise ValueError(f"PLSc impossible : rho_A indéfini pour {model.latents[j]}")
            c_fac[j], rho_a[j] = np.nan, np.nan
            continue
        c_fac[j] = np.sqrt(c2)
        rho_a[j] = (w @ w) ** 2 * c2

    # Corrélations entre latentes (corrigées de l'atténuation si PLSc)
    r_lat = np.corrcoef(y, rowvar=False)
    if consistent:
        r_lat = r_lat / np.sqrt(np.outer(rho_a, rho_a))
        np.fill_diagonal(r_lat, 1.0)
        # chargements corrigés pour les blocs réflectifs
        loadings = np.concatenate([weights[j] * c_fac[j] if c_fac[j] != 1 else loadings[b]
                                   for j, b in enumerate(blocks)])

    paths = np.zeros((k, k))
    r2 = {}
    for j in model.endogenous():
        pred = model.predecessors(j)
        beta = np.linalg.solve(r_lat[np.ix_(pred, pred)], r_lat[pred, j])
        paths[pred, j] = beta
        r2[model.latents[j]] = float(beta @ r_lat[pred, j])

    return PLSResult(
        model=model,
        outer_weights=pd.Series(w_flat, index=idx),
        outer_loadings=pd.Series(loadings, index=idx),
        path_coefficients=pd.DataFrame(paths, index=model.latents, columns=model.latents),
        r_squared=pd.Series(r2),
        scores=pd.DataFrame(y, columns=model.latents, index=data.index),
        data_std=pd.DataFrame(x, columns=model.indicators, index=data.index),
        rho_a=pd.Series(rho_a, index=model.latents),
        iterations=it,
        converged=converged,
        consistent=consistent,
    )
