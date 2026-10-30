"""Analyse multigroupe (MGA) et invariance de mesure (MICOM).

`mga` compare deux groupes ; `mga_multi` en compare k ≥ 2 (omnibus + paires corrigées par Holm).

MGA — compare les coefficients de chemin de deux groupes :
  * test de permutation (Chin & Dibbern 2010) : on permute les étiquettes de groupe ;
  * PLS-MGA de Henseler (2009) : comparaison de toutes les paires de tirages bootstrap ;
  * test paramétrique de Welch-Satterthwaite à partir des erreurs-types bootstrap.

MICOM (Henseler, Ringle & Sarstedt 2016) — à vérifier AVANT de comparer des groupes :
  1. invariance de configuration : même modèle, mêmes indicateurs, même traitement des
     données (garanti par construction ici) ;
  2. invariance compositionnelle : corrélation c entre les scores calculés avec les poids
     du groupe 1 et ceux du groupe 2 ; c doit dépasser le quantile 5 % de sa distribution
     par permutation ;
  3. égalité des moyennes et des variances des composites (scores calculés avec les poids
     de l'échantillon complet) : la différence observée doit tomber dans l'intervalle de
     permutation à 95 %. Si 1 et 2 sont établies : invariance partielle (MGA légitime) ;
     si 3 l'est aussi : invariance totale (on peut regrouper les données).
"""
from __future__ import annotations

import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

from .algorithm import ConvergenceWarning
from .model import Model


def _paths(res) -> pd.Series:
    from .higher_order import structural_view

    res = structural_view(res)
    m = res.model
    return pd.Series([res.path_coefficients.loc[s, d] for s, d in m.structural],
                     index=[f"{s} -> {d}" for s, d in m.structural])


def _align_groups(data: pd.DataFrame, groups) -> pd.Series:
    """Série de groupes alignée sur data : par étiquette d'index si `groups` est une Series,
    par position sinon (liste, tableau)."""
    if isinstance(groups, pd.Series):
        if not groups.index.is_unique:
            raise ValueError("L'index de la variable de groupe contient des doublons")
        g = groups.reindex(data.index)
        if g.isna().any() and not groups.isna().any():
            raise ValueError("La variable de groupe ne couvre pas toutes les lignes des données (index différents)")
        return g
    g = np.asarray(groups)
    if len(g) != len(data):
        raise ValueError(f"La variable de groupe a {len(g)} valeurs pour {len(data)} lignes")
    return pd.Series(g, index=data.index)


def _split(data: pd.DataFrame, groups) -> tuple[pd.Series, list]:
    g = _align_groups(data, groups)
    if g.isna().any():
        raise ValueError("La variable de groupe contient des valeurs manquantes")
    levels = list(pd.unique(g))
    if len(levels) != 2:
        raise ValueError(f"La MGA compare exactement 2 groupes (trouvé : {len(levels)})")
    for lv in levels:
        if (g == lv).sum() < 10:
            raise ValueError(f"Le groupe {lv!r} a moins de 10 observations")
    return g, levels


def _std(x: pd.DataFrame) -> np.ndarray:
    a = x.to_numpy(float)
    return (a - a.mean(axis=0)) / a.std(axis=0, ddof=1)


def _composite(xz: np.ndarray, cols: list[str], w: pd.Series) -> np.ndarray:
    return xz[:, [cols.index(c) for c in w.index]] @ w.to_numpy()


def _corr(a, b) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def mga(data: pd.DataFrame, model: Model, groups, n_perm: int = 1000, n_boot: int = 1000,
        seed: int | None = 42, statistic: Callable = _paths, progress=None, **fit_kwargs) -> dict:
    """Analyse multigroupe complète, MICOM inclus.

    Retourne un dict : "groups" (effectifs), "comparison" (estimations par groupe, différences et
    p-values des 3 tests), "micom_step2", "micom_step3", "verdict", "invariant",
    "n_perm_ok", "n_perm_failed"."""
    from .algorithm import fit
    from .bootstrap import bootstrap_statistics

    g, levels = _split(data, groups)
    rng = np.random.default_rng(seed)
    d1, d2 = data[g == levels[0]], data[g == levels[1]]
    r1, r2 = fit(d1, model, **fit_kwargs), fit(d2, model, **fit_kwargs)
    pooled = fit(data, model, **fit_kwargs)
    meas_model = pooled.model if pooled.stage1 is None else pooled.stage1.model
    hoc = set(model.higher_order)
    # MICOM porte sur les composites d'ordre 1 mesurés par des colonnes des données
    lvs = [lv for lv in meas_model.latents if ":" not in lv and lv not in hoc
           and all(c in data.columns for c in meas_model.measurement[lv])]
    m1 = r1.measurement_result.outer_weights
    m2 = r2.measurement_result.outer_weights
    mp = pooled.measurement_result.outer_weights
    cols = list(dict.fromkeys(c for lv in lvs for c in meas_model.measurement[lv]))
    xz = _std(data[cols])

    s1, s2 = statistic(r1), statistic(r2)
    diff = s1 - s2
    c_obs = {lv: _corr(_composite(xz, cols, m1[lv]), _composite(xz, cols, m2[lv])) for lv in lvs}
    pooled_scores = {lv: _composite(xz, cols, mp[lv]) for lv in lvs}
    pooled_scores = {lv: (v - v.mean()) / v.std(ddof=1) for lv, v in pooled_scores.items()}
    mask = (g == levels[0]).to_numpy()

    def step3(msk):
        return ({lv: v[msk].mean() - v[~msk].mean() for lv, v in pooled_scores.items()},
                {lv: np.log(v[msk].var(ddof=1)) - np.log(v[~msk].var(ddof=1)) for lv, v in pooled_scores.items()})

    mean_obs, var_obs = step3(mask)

    perm_diff, perm_c, perm_mean, perm_var, fails = [], [], [], [], 0
    for b in range(n_perm):
        msk = rng.permutation(mask)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                p1, p2 = fit(data[msk], model, **fit_kwargs), fit(data[~msk], model, **fit_kwargs)
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
            continue
        perm_diff.append((statistic(p1) - statistic(p2)).reindex(diff.index).to_numpy())
        w1, w2 = p1.measurement_result.outer_weights, p2.measurement_result.outer_weights
        perm_c.append([_corr(_composite(xz, cols, w1[lv]), _composite(xz, cols, w2[lv])) for lv in lvs])
        mm, vv = step3(msk)
        perm_mean.append([mm[lv] for lv in lvs])
        perm_var.append([vv[lv] for lv in lvs])
        if progress:
            progress(b + 1, n_perm + 2 * n_boot)
    perm_diff, perm_c = np.array(perm_diff), np.array(perm_c)
    perm_mean, perm_var = np.array(perm_mean), np.array(perm_var)
    if len(perm_diff) < 20:
        raise RuntimeError("Trop de permutations en échec")

    p_perm = ((np.abs(perm_diff) >= np.abs(diff.to_numpy()) - 1e-12).sum(axis=0) + 1) / (len(perm_diff) + 1)

    # bootstrap par groupe (Henseler + Welch)
    def prog_offset(off):
        return (lambda i, n: progress(n_perm + off + i, n_perm + 2 * n_boot)) if progress else None

    draws, boot_msgs = [], []
    for k, dk in enumerate((d1, d2)):
        collected = []

        def keep(res, collected=collected):
            s = statistic(res)
            collected.append(s.reindex(diff.index).to_numpy())
            return s
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            bt = bootstrap_statistics(dk.reset_index(drop=True), model, keep, n_boot=n_boot,
                                      seed=None if seed is None else seed + 1 + k,
                                      progress=prog_offset(k * n_boot), **fit_kwargs)
        boot_msgs += [f"groupe {levels[k]} : {m}" for m in bt.attrs["warnings"]]
        draws.append(np.array(collected[1:]))  # le 1er appel = estimation sur l'échantillon complet
    b1, b2 = draws
    # Henseler (2009) : p unilatérale de H1 « beta1 > beta2 » = 1 - sum Θ(2·mean1 - b1_j - 2·mean2 + b2_i) / B²
    c1 = 2 * b1.mean(axis=0) - b1   # (B1, p)
    c2 = 2 * b2.mean(axis=0) - b2
    p_one = np.empty(diff.size)
    for j in range(diff.size):
        sorted2 = np.sort(c2[:, j])
        # Θ(c1 - c2) > 0  <=>  c2 < c1 : nombre de c2 strictement inférieurs à chaque c1
        count = np.searchsorted(sorted2, c1[:, j], side="left").sum()
        p_one[j] = 1 - count / (len(c1) * len(c2))
    p_henseler = 2 * np.minimum(p_one, 1 - p_one)
    se1, se2 = b1.std(axis=0, ddof=1), b2.std(axis=0, ddof=1)
    n1, n2 = len(d1), len(d2)
    t_welch = diff.to_numpy() / np.sqrt(se1**2 + se2**2)
    df_welch = (se1**2 + se2**2) ** 2 / (se1**4 / (n1 - 1) + se2**4 / (n2 - 1))
    p_welch = 2 * stats.t.sf(np.abs(t_welch), df_welch)

    lbl1, lbl2 = str(levels[0]), str(levels[1])
    comparison = pd.DataFrame({
        f"{lbl1}": s1, f"{lbl2}": s2, "difference": diff,
        "p_permutation": p_perm, "p_henseler": p_henseler, "p_welch": p_welch,
    })
    comparison["différence significative (perm., 5 %)"] = comparison["p_permutation"] < 0.05

    q05 = np.quantile(perm_c, 0.05, axis=0)
    step2 = pd.DataFrame({
        "c": [c_obs[lv] for lv in lvs], "quantile_5%": q05,
        "p_value": [((perm_c[:, i] <= c_obs[lv] + 1e-12).sum() + 1) / (len(perm_c) + 1) for i, lv in enumerate(lvs)],
    }, index=lvs)
    step2["invariance compositionnelle"] = step2["c"] >= step2["quantile_5%"]

    rows = {}
    for i, lv in enumerate(lvs):
        lo_m, hi_m = np.quantile(perm_mean[:, i], [0.025, 0.975])
        lo_v, hi_v = np.quantile(perm_var[:, i], [0.025, 0.975])
        rows[lv] = {
            "diff_moyenne": mean_obs[lv], "IC_moy_2.5%": lo_m, "IC_moy_97.5%": hi_m,
            "p_moyenne": ((np.abs(perm_mean[:, i]) >= abs(mean_obs[lv]) - 1e-12).sum() + 1) / (len(perm_mean) + 1),
            "égalité moyennes": lo_m <= mean_obs[lv] <= hi_m,
            "diff_log_variance": var_obs[lv], "IC_var_2.5%": lo_v, "IC_var_97.5%": hi_v,
            "p_variance": ((np.abs(perm_var[:, i]) >= abs(var_obs[lv]) - 1e-12).sum() + 1) / (len(perm_var) + 1),
            "égalité variances": lo_v <= var_obs[lv] <= hi_v,
        }
    step3_tbl = pd.DataFrame(rows).T
    for c in step3_tbl.columns:
        if not c.startswith("égalité"):
            step3_tbl[c] = step3_tbl[c].astype(float)
        else:
            step3_tbl[c] = step3_tbl[c].astype(bool)

    if step2["invariance compositionnelle"].all():
        verdict = ("invariance totale : les données peuvent être regroupées"
                   if (step3_tbl["égalité moyennes"] & step3_tbl["égalité variances"]).all()
                   else "invariance partielle : la comparaison des chemins entre groupes est légitime")
    else:
        bad = ", ".join(step2.index[~step2["invariance compositionnelle"]])
        verdict = f"pas d'invariance compositionnelle pour {bad} : interpréter la MGA avec prudence"

    msgs = list(boot_msgs)
    if fails:
        msgs.insert(0, f"{fails}/{n_perm} permutations en échec exclues")
    return {
        "warnings": msgs,
        "invariant": bool(step2["invariance compositionnelle"].all()),
        "groups": pd.Series({lbl1: n1, lbl2: n2}, name="n"),
        "comparison": comparison,
        "micom_step2": step2,
        "micom_step3": step3_tbl,
        "verdict": verdict,
        "n_perm_ok": len(perm_diff), "n_perm_failed": fails,
    }


# ---------------------------------------------------------------- plus de deux groupes
def holm(p: np.ndarray) -> np.ndarray:
    """Correction de Holm-Bonferroni (contrôle du taux d'erreur familial)."""
    p = np.asarray(p, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(running, 1.0)
    return adj


def mga_multi(data: pd.DataFrame, model: Model, groups, n_perm: int = 1000, n_boot: int = 500,
              seed: int | None = 42, statistic: Callable = _paths, progress=None, **fit_kwargs) -> dict:
    """MGA pour k ≥ 2 groupes.

    1. Test omnibus par permutation de l'égalité de chaque chemin entre TOUS les groupes :
       statistique  Σ_g n_g (β_g - β̄)²  (β̄ = moyenne pondérée par les effectifs), comparée à
       sa distribution quand les étiquettes de groupe sont permutées.
    2. Comparaisons deux à deux avec `mga` (permutation, Henseler, Welch, MICOM) ; les p-values
       de permutation sont corrigées par Holm pour chaque chemin, sur l'ensemble des paires.
    Bonne pratique : n'interpréter les paires que pour les chemins dont l'omnibus est significatif.
    """
    from itertools import combinations

    from .algorithm import fit

    g = _align_groups(data, groups)
    if g.isna().any():
        raise ValueError("La variable de groupe contient des valeurs manquantes")
    levels = list(pd.unique(g))
    if len(levels) < 2:
        raise ValueError("Il faut au moins 2 groupes")
    for lv in levels:
        if (g == lv).sum() < 10:
            raise ValueError(f"Le groupe {lv!r} a moins de 10 observations")
    pairs = list(combinations(levels, 2))
    total = n_perm + len(pairs) * (n_perm + 2 * n_boot)
    done = [0]

    def tick(k=1):
        done[0] += k
        if progress:
            progress(min(done[0], total), total)

    labels = g.to_numpy()
    sizes = np.array([(labels == lv).sum() for lv in levels], float)

    def group_stats(lab):
        est = [statistic(fit(data[lab == lv], model, **fit_kwargs)) for lv in levels]
        return pd.concat(est, axis=1, keys=[str(lv) for lv in levels])

    est = group_stats(labels)

    def omni(e: pd.DataFrame) -> np.ndarray:
        v = e.to_numpy()
        mean = (v * sizes).sum(axis=1) / sizes.sum()
        return ((v - mean[:, None]) ** 2 * sizes).sum(axis=1)

    obs = omni(est)
    rng = np.random.default_rng(seed)
    perm, fails = [], 0
    for _ in range(n_perm):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                perm.append(omni(group_stats(rng.permutation(labels)).reindex(est.index)))
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
        tick()
    perm = np.array(perm)
    if len(perm) < 20:
        raise RuntimeError("Trop de permutations en échec")
    p_omni = ((perm >= obs - 1e-12).sum(axis=0) + 1) / (len(perm) + 1)
    omnibus = pd.DataFrame({"statistique": obs, "p_value": p_omni}, index=est.index)
    omnibus["différence entre groupes (p<0,05)"] = omnibus["p_value"] < 0.05

    rows, micom, pair_msgs = [], {}, []
    for k, (a, b) in enumerate(pairs):
        mask = np.isin(labels, [a, b])
        base = done[0]
        out = mga(data[mask], model, labels[mask], n_perm=n_perm, n_boot=n_boot,
                  seed=None if seed is None else seed + 101 * (k + 1), statistic=statistic,
                  progress=(lambda i, n, base=base: progress(min(base + i, total), total)) if progress else None,
                  **fit_kwargs)
        done[0] = base + n_perm + 2 * n_boot
        tick(0)
        name = f"{a} vs {b}"
        micom[name] = {"step2": out["micom_step2"], "step3": out["micom_step3"], "verdict": out["verdict"],
                       "invariant": out["invariant"]}
        pair_msgs += [f"{name} — {m}" for m in out["warnings"]]
        c = out["comparison"]
        for path, r in c.iterrows():
            rows.append({"paire": name, "chemin": path, "difference": r["difference"],
                         "p_permutation": r["p_permutation"], "p_henseler": r["p_henseler"], "p_welch": r["p_welch"]})
    pw = pd.DataFrame(rows)
    pw["p_perm_Holm"] = pw.groupby("chemin")["p_permutation"].transform(lambda s: holm(s.to_numpy()))
    pw["différence significative (Holm, 5 %)"] = pw["p_perm_Holm"] < 0.05
    pw = pw.set_index(["chemin", "paire"]).sort_index()

    invariant = all(v["invariant"] for v in micom.values())
    verdict = ("invariance au moins partielle pour toutes les paires : la comparaison est légitime" if invariant
               else "invariance compositionnelle non établie pour au moins une paire : interpréter avec prudence")
    msgs = ([f"omnibus : {fails}/{n_perm} permutations en échec exclues"] if fails else []) + pair_msgs
    return {
        "warnings": msgs,
        "invariant": invariant,
        "groups": pd.Series({str(lv): int(n) for lv, n in zip(levels, sizes)}, name="n"),
        "estimates": est, "omnibus": omnibus, "pairwise": pw, "micom": micom, "verdict": verdict,
        "n_perm_ok": len(perm), "n_perm_failed": fails,
    }
