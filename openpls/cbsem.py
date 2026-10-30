"""SEM basé sur les covariances (CB-SEM) et analyse factorielle confirmatoire (CFA),
estimés par maximum de vraisemblance (Jöreskog 1969 ; Bollen 1989).

Modèle (notation LISREL « tout-y ») :
    x = Λ η + ε,    η = B η + ζ,    Cov(ζ) = Ψ,   Cov(ε) = Θ (diagonale)
    Σ(θ) = Λ (I - B)⁻¹ Ψ (I - B)⁻ᵀ Λᵀ + Θ
Fonction d'ajustement : F_ML = log|Σ| + tr(S Σ⁻¹) - log|S| - p, avec S la matrice de covariance
(diviseur N, comme lavaan). Identification par variable marqueur (1er chargement fixé à 1).
Ψ : variances et covariances libres entre latentes exogènes ; variances résiduelles des
endogènes. Les construits doivent être réflectifs. Second ordre : HOC -> composantes dans B,
première relation fixée à 1 ; la CFA de second ordre s'obtient avec cfa=True.

Indices : χ² = N·F, ddl, CFI, TLI, RMSEA (+ IC 90 %), SRMR, AIC, BIC.
Erreurs-types : inverse de la matrice d'information (hessienne numérique de F).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

from .model import Model


@dataclass
class CBSEMResult:
    model: Model
    estimates: pd.DataFrame        # paramètres libres : estimation, SE, z, p, standardisé
    loadings: pd.Series            # chargements standardisés
    path_coefficients: pd.DataFrame  # chemins standardisés
    latent_correlations: pd.DataFrame
    r_squared: pd.Series
    fit_indices: pd.Series
    residuals: pd.DataFrame        # résidus standardisés (corrélations)
    converged: bool
    n: int
    higher_order_loadings: pd.Series = None  # chargements standardisés de second ordre (HOC -> composante)


class _Spec:
    def __init__(self, model: Model, cfa: bool):
        if any(m != "A" for m in model.modes.values()):
            raise ValueError("Le CB-SEM exige des construits réflectifs (=~), y compris d'ordre supérieur")
        if model.interactions:
            raise ValueError("Les interactions ne sont pas prises en charge en CB-SEM")
        self.lvs = model.latents
        self.inds = model.indicators
        k, p = len(self.lvs), len(self.inds)
        self.k, self.p = k, p
        path = np.zeros((k, k), int) if cfa else model.path.copy()
        # second ordre : HOC -> composante, 1re relation fixée à 1 (échelle du HOC)
        self.b0 = np.zeros((k, k))
        fixed = set()
        for hoc, locs in model.higher_order.items():
            h = self.lvs.index(hoc)
            for r, loc in enumerate(locs):
                c = self.lvs.index(loc)
                path[h, c] = 1
                if r == 0:
                    self.b0[c, h] = 1.0
                    fixed.add((h, c))
        self.hoc_edges = {(self.lvs.index(h), self.lvs.index(l)) for h, ls in model.higher_order.items() for l in ls}
        exo = [j for j in range(k) if not path[:, j].any()]
        params = []  # (type, i, j, libellé)
        for j, lv in enumerate(self.lvs):
            for r, ind in enumerate(model.measurement.get(lv, [])):
                if r > 0:
                    params.append(("L", self.inds.index(ind), j, f"{lv} =~ {ind}"))
        for i in range(k):
            for j in range(k):
                if path[i, j] and (i, j) not in fixed:
                    lbl = (f"{self.lvs[i]} =~ {self.lvs[j]}" if (i, j) in self.hoc_edges
                           else f"{self.lvs[j]} ~ {self.lvs[i]}")
                    params.append(("B", j, i, lbl))
        for a_i, a in enumerate(exo):
            for b in exo[a_i:]:
                params.append(("P", a, b, f"{self.lvs[a]} ~~ {self.lvs[b]}"))
        for j in range(k):
            if j not in exo:
                params.append(("P", j, j, f"{self.lvs[j]} ~~ {self.lvs[j]} (résiduelle)"))
        for i, ind in enumerate(self.inds):
            params.append(("T", i, i, f"{ind} ~~ {ind}"))
        self.params = params
        self.lam0 = np.zeros((p, k))
        for j, lv in enumerate(self.lvs):
            if lv in model.measurement:
                self.lam0[self.inds.index(model.measurement[lv][0]), j] = 1.0
        # indicateur de référence pour les valeurs de départ (1er indicateur de la 1re composante pour un HOC)
        self.marker = {}
        for j, lv in enumerate(self.lvs):
            first = lv if lv in model.measurement else model.higher_order[lv][0]
            self.marker[j] = self.inds.index(model.measurement[first][0])
        self.exo = exo
        self.path = path

    def matrices(self, theta):
        lam, b = self.lam0.copy(), self.b0.copy()
        psi, th = np.zeros((self.k, self.k)), np.zeros((self.p, self.p))
        for (t, i, j, _), v in zip(self.params, theta):
            if t == "L":
                lam[i, j] = v
            elif t == "B":
                b[i, j] = v
            elif t == "P":
                psi[i, j] = psi[j, i] = v
            else:
                th[i, i] = v
        return lam, b, psi, th

    def sigma(self, theta):
        lam, b, psi, th = self.matrices(theta)
        ib = np.linalg.inv(np.eye(self.k) - b)
        cov_eta = ib @ psi @ ib.T
        return lam @ cov_eta @ lam.T + th, cov_eta


def _f_ml(sig, s, logdet_s, p):
    sign, logdet = np.linalg.slogdet(sig)
    if sign <= 0:
        return 1e10
    return logdet + np.trace(s @ np.linalg.inv(sig)) - logdet_s - p


def fit_cbsem(data: pd.DataFrame, model: Model, cfa: bool = False, max_iter: int = 2000) -> CBSEMResult:
    """Estime le modèle en CB-SEM (cfa=False) ou en CFA (cfa=True : toutes les latentes corrélées,
    pas de chemins structurels)."""
    spec = _Spec(model, cfa)
    x = data[spec.inds].to_numpy(float)
    if np.isnan(x).any():
        raise ValueError("Valeurs manquantes : traite-les avant l'estimation")
    n, p = x.shape
    s = np.cov(x, rowvar=False, ddof=0)
    sign, logdet_s = np.linalg.slogdet(s)
    if n <= p or sign <= 0 or np.linalg.matrix_rank(s) < p:
        raise ValueError(f"Matrice de covariance singulière (n = {n} pour {p} indicateurs, ou indicateurs "
                         "colinéaires) : le CB-SEM exige nettement plus d'observations que d'indicateurs")
    df_model = p * (p + 1) // 2 - len(spec.params)
    if df_model < 0:
        raise ValueError(f"Modèle non identifié : {len(spec.params)} paramètres pour {p * (p + 1) // 2} "
                         f"moments (ddl = {df_model}). Ajoute des indicateurs (au moins 3 par construit "
                         "est recommandé en CB-SEM).")

    # valeurs de départ
    start, bounds = [], []
    for t, i, j, _ in spec.params:
        if t == "L":
            start.append(1.0); bounds.append((None, None))
        elif t == "B":
            start.append(1.0 if (j, i) in spec.hoc_edges else 0.0); bounds.append((None, None))
        elif t == "P":
            marker = spec.marker[i]
            v = 0.5 * s[marker, marker]
            if i == j:
                start.append(v); bounds.append((1e-8, None))
            else:
                start.append(0.0); bounds.append((None, None))
        else:
            start.append(0.5 * s[i, i]); bounds.append((1e-8, None))
    start = np.array(start)

    def obj(th):
        sig, _ = spec.sigma(th)
        return _f_ml(sig, s, logdet_s, p)

    r = optimize.minimize(obj, start, method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": max_iter, "maxfun": 200000, "ftol": 1e-14, "gtol": 1e-9})
    theta = r.x
    fmin = obj(theta)
    q = len(theta)
    # L-BFGS-B signale parfois un arrêt « anormal » dans la recherche linéaire alors que l'optimum
    # est atteint : on juge la convergence sur le gradient (différences centrées), hors bornes actives.
    grad = np.empty(q)
    for a in range(q):
        e = np.zeros(q)
        e[a] = 1e-6 * max(1, abs(theta[a]))
        grad[a] = (obj(theta + e) - obj(theta - e)) / (2 * e[a])
    at_bound = np.array([lo is not None and th <= lo + 1e-7 for (lo, _), th in zip(bounds, theta)])
    converged = bool(r.success or np.max(np.abs(grad[~at_bound]), initial=0) < 1e-4)

    # erreurs-types : Cov(θ) = 2/N · H⁻¹, H = hessienne de F_ML (différences centrées)
    h = np.zeros((q, q))
    eps = 1e-4 * np.maximum(1, np.abs(theta))
    for a in range(q):
        for b_ in range(a, q):
            ea, eb = np.zeros(q), np.zeros(q)
            ea[a], eb[b_] = eps[a], eps[b_]
            v = (obj(theta + ea + eb) - obj(theta + ea - eb) - obj(theta - ea + eb) + obj(theta - ea - eb)) / (
                4 * eps[a] * eps[b_])
            h[a, b_] = h[b_, a] = v
    try:
        cov = 2 / n * np.linalg.inv(h)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        se = np.full(q, np.nan)

    sig, cov_eta = spec.sigma(theta)
    lam, b, psi, th = spec.matrices(theta)
    sd_eta = np.sqrt(np.diag(cov_eta))
    sd_x = np.sqrt(np.diag(sig))

    std = []
    for (t, i, j, _), v in zip(spec.params, theta):
        if t == "L":
            std.append(v * sd_eta[j] / sd_x[i])
        elif t == "B":
            std.append(v * sd_eta[j] / sd_eta[i])
        elif t == "P":
            std.append(v / (sd_eta[i] * sd_eta[j]))
        else:
            std.append(v / sig[i, i])
    with np.errstate(divide="ignore", invalid="ignore"):
        z = theta / se
    est = pd.DataFrame({"estimate": theta, "std_error": se, "z_value": z,
                        "p_value": 2 * stats.norm.sf(np.abs(z)), "standardized": std},
                       index=[lbl for *_, lbl in spec.params])

    std_lam = lam * sd_eta[None, :] / sd_x[:, None]
    idx = pd.MultiIndex.from_tuples([(lv, ind) for lv in spec.lvs for ind in model.measurement.get(lv, [])],
                                    names=["latent", "indicator"])
    loadings = pd.Series([std_lam[spec.inds.index(ind), spec.lvs.index(lv)] for lv, ind in idx], index=idx)
    std_b = (b * sd_eta[None, :] / sd_eta[:, None]).T  # [source, cible]
    hoc_load = pd.Series({f"{spec.lvs[h]} -> {spec.lvs[c]}": std_b[h, c] for h, c in sorted(spec.hoc_edges)},
                         dtype=float)
    for h, c in spec.hoc_edges:
        std_b[h, c] = 0.0   # relation de mesure, rapportée à part
    paths = pd.DataFrame(std_b, index=spec.lvs, columns=spec.lvs)
    lat_corr = pd.DataFrame(cov_eta / np.outer(sd_eta, sd_eta), index=spec.lvs, columns=spec.lvs)
    locs = {c for _, c in spec.hoc_edges}
    r2 = {spec.lvs[j]: 1 - psi[j, j] / cov_eta[j, j] for j in range(spec.k) if j not in spec.exo and j not in locs}

    # indices d'ajustement
    chi2 = n * fmin
    df = p * (p + 1) // 2 - q
    f_base = np.log(np.diag(s)).sum() - logdet_s
    chi2_b, df_b = n * f_base, p * (p - 1) // 2
    cfi = 1 - max(chi2 - df, 0) / max(chi2_b - df_b, chi2 - df, 1e-12)
    tli = ((chi2_b / df_b) - (chi2 / df)) / ((chi2_b / df_b) - 1) if df > 0 else np.nan
    rmsea = np.sqrt(max(chi2 - df, 0) / (df * n)) if df > 0 else np.nan

    def ncp_bound(target):
        f = lambda lam_: stats.ncx2.cdf(chi2, df, lam_) - target if lam_ > 0 else stats.chi2.cdf(chi2, df) - target
        if f(0) < 0:
            return 0.0
        hi = max(chi2, 1.0)
        while f(hi) > 0:
            hi *= 2
        return optimize.brentq(f, 1e-10, hi)

    rmsea_lo = np.sqrt(ncp_bound(0.95) / (df * n)) if df > 0 else np.nan
    rmsea_hi = np.sqrt(ncp_bound(0.05) / (df * n)) if df > 0 else np.nan
    d = np.sqrt(np.diag(s))
    resid = (s - sig) / np.outer(d, d)
    srmr = np.sqrt(np.mean(resid[np.tril_indices(p)] ** 2))
    loglik = -n / 2 * (p * np.log(2 * np.pi) + np.linalg.slogdet(sig)[1] + np.trace(s @ np.linalg.inv(sig)))
    fit_idx = pd.Series({
        "chi2": chi2, "ddl": df, "p_value": stats.chi2.sf(chi2, df) if df > 0 else np.nan,
        "CFI": cfi, "TLI": tli, "RMSEA": rmsea, "RMSEA IC90 bas": rmsea_lo, "RMSEA IC90 haut": rmsea_hi,
        "SRMR": srmr, "AIC": -2 * loglik + 2 * q, "BIC": -2 * loglik + np.log(n) * q, "paramètres": q,
    })
    return CBSEMResult(model=model, estimates=est, loadings=loadings, path_coefficients=paths,
                       latent_correlations=lat_corr, r_squared=pd.Series(r2, dtype=float), fit_indices=fit_idx,
                       residuals=pd.DataFrame(resid, index=spec.inds, columns=spec.inds), higher_order_loadings=hoc_load,
                       converged=converged, n=n)
