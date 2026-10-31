"""Onglet « Analyses préliminaires » : à faire avant d'interpréter le modèle."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from . import descriptives as ds
from . import figures as fg
from .gui_helpers import num, to_excel
from .i18n import T


def _cached(key, make):
    """Résultat mémorisé pour ces données (les onglets sont tous recalculés à chaque interaction)."""
    cache = st.session_state.setdefault("_prelim_cache", {})
    full = (st.session_state.get("data_id"), st.session_state.get("lang"), st.session_state.get("decimal")) + key
    if full not in cache:
        if len(cache) > 60:
            cache.clear()
        cache[full] = make()
    return cache[full]


def _figure(make_fig, name: str, key: str, offer_file, cache_key) -> None:
    def build():
        import matplotlib.pyplot as plt

        fig = make_fig()
        out = (fg.to_bytes(fig, "png"), fg.to_bytes(fig, "svg"), fig.get_size_inches()[0])
        plt.close(fig)
        return out

    png, svg, width_in = _cached(("fig",) + cache_key, build)
    st.image(png, width=int(width_in * 100))
    c1, c2, _ = st.columns([1, 1, 1])
    with c1:
        offer_file("⬇  PNG", png, f"{name}.png", key=f"{key}_png", mime="image/png")
    with c2:
        offer_file("⬇  SVG", svg, f"{name}.svg", key=f"{key}_svg", mime="image/svg+xml")


def render(raw: pd.DataFrame, model, res, numeric_cols: list[str], fmt, flag, offer_file) -> None:
    blocks = ds.indicator_blocks(model, numeric_cols)
    blocks = {c: lv for c, lv in blocks.items() if c in raw.columns}
    if not blocks:
        st.info(T("Aucun indicateur numérique à analyser."))
        return
    cols = list(blocks)
    st.caption(T("Calculées sur les données brutes ({n} lignes), indicateurs regroupés par construit. "
                 "À examiner avant d'interpréter le modèle.", n=len(raw)))
    sheets: dict[str, pd.DataFrame] = {}
    t_desc, t_miss, t_norm, t_corr, t_cmb, t_n, t_fig = st.tabs([
        T("Statistiques descriptives"), T("Manquants et aberrants"), T("Normalité"), T("Corrélations"),
        T("Biais de méthode commune"), T("Taille d'échantillon"), T("Figures")])

    with t_desc:
        desc = _cached(("desc", tuple(blocks.items())), lambda: ds.descriptive_statistics(raw, blocks))
        sheets["Descriptives"] = desc
        st.dataframe(flag(desc, {"asymétrie": lambda v: abs(v) > 2, "aplatissement": lambda v: abs(v) > 7}),
                     width="stretch", height=min(3 + 35 * (len(desc) + 1), 520))
        st.caption(T("Aplatissement = excès de kurtosis (0 pour une loi normale). Rouge : |asymétrie| > 2 ou "
                     "|aplatissement| > 7 (Curran, West & Finch 1996 ; Kline 2016). PLS-SEM ne suppose pas la "
                     "normalité, mais une distribution très asymétrique mérite d'être signalée."))

    with t_miss:
        ms = ds.missing_summary(raw, cols)
        sheets["Manquants"] = ms["columns"]
        m = st.columns(3)
        m[0].metric(T("Observations"), ms["rows"])
        m[1].metric(T("Lignes complètes"), ms["complete_rows"])
        m[2].metric(T("Valeurs manquantes"), f"{num(ms['pct_missing'], 1)} %")
        st.dataframe(flag(ms["columns"], {"% manquants": lambda v: v > 5}), width="stretch",
                     height=min(3 + 35 * (len(cols) + 1), 360))
        st.caption(T("Rouge : plus de 5 % de valeurs manquantes. L'estimation utilise la suppression par liste "
                     "(lignes incomplètes retirées) sauf si tu choisis un autre traitement dans la barre latérale."))
        st.subheader(T("Valeurs aberrantes multivariées"))
        out = _cached(("maha", tuple(cols)), lambda: ds.mahalanobis_outliers(raw, cols))
        n_out = int(out["aberrante"].sum())
        sheets["Mahalanobis"] = out
        st.write(T("**{k}** observation(s) aberrante(s) sur {n} (distance de Mahalanobis, p < 0,001).",
                   k=n_out, n=len(out)))
        st.dataframe(fmt(out.head(20).assign(aberrante=out.head(20)["aberrante"].map(
            {True: T("oui"), False: T("non")}))), width="stretch")
        st.caption(T("Les 20 distances les plus grandes. Numéro d'observation = ligne du fichier (à partir de 0). "
                     "Vérifie ces réponses avant de les retirer : une valeur extrême n'est pas forcément une erreur."))

    with t_norm:
        try:
            mm = _cached(("mardia", tuple(cols)),
                         lambda: ds.mardia(ds.numeric_frame(raw, cols).dropna().to_numpy(dtype=float)))
            tbl = pd.DataFrame({
                T("statistique"): [mm["asymétrie (b1p)"], mm["aplatissement (b2p)"]],
                T("test"): [f"χ²({num(mm['ddl'], 0)}) = {num(mm['chi²'], 2)}", f"z = {num(mm['z'], 2)}"],
                "p": [mm["p asymétrie"], mm["p aplatissement"]],
            }, index=[T("Asymétrie multivariée"), T("Aplatissement multivarié")])
            sheets["Mardia"] = tbl
            st.subheader(T("Test de Mardia"))
            st.dataframe(fmt(tbl), width="stretch")
            st.caption(T("p < 0,05 : les données s'écartent de la normalité multivariée. C'est fréquent avec des "
                         "échelles de Likert et c'est une raison d'utiliser PLS-SEM avec un bootstrap plutôt qu'un "
                         "CB-SEM par maximum de vraisemblance."))
        except Exception as e:  # noqa: BLE001
            st.info(T("Test de Mardia non calculable : {e}", e=e))
        pick = st.selectbox(T("Indicateur"), cols, key="norm_ind")
        c1, c2 = st.columns(2)
        with c1:
            _figure(lambda: fg.histogram(raw[pick], pick, T("valeur"), T("loi normale")), f"histogramme_{pick}",
                    "fig_h1", offer_file, ("hist", pick))
        with c2:
            _figure(lambda: fg.qq_plot(raw[pick], T("Diagramme quantile-quantile"), T("quantiles théoriques"),
                                       T("quantiles observés")), f"qq_{pick}", "fig_qq", offer_file, ("qq", pick))

    with t_corr:
        method = st.radio(T("Coefficient"), ["pearson", "spearman"], horizontal=True, key="corr_m",
                          format_func={"pearson": "Pearson", "spearman": "Spearman"}.get)
        corr = ds.numeric_frame(raw, cols).corr(method=method)
        sheets["Correlations"] = corr
        st.dataframe(fmt(corr).background_gradient(cmap="RdBu_r", vmin=-1, vmax=1), width="stretch")
        _figure(lambda: fg.correlation_heatmap(corr, T("Corrélations entre indicateurs")), "correlations", "fig_corr",
                offer_file, ("corr", method, tuple(cols)))

    with t_cmb:
        hm = _cached(("harman", tuple(cols)), lambda: ds.harman_single_factor(raw, cols))
        m = st.columns(2)
        m[0].metric(T("Variance du premier facteur"), f"{num(hm['pct_first'], 1)} %",
                    help=T("Test à un facteur de Harman : > 50 % suggère un biais de méthode commune "
                           "(Podsakoff et al. 2003)."))
        m[1].metric(T("Facteurs de valeur propre > 1"), hm["n_eigen_gt1"])
        if hm["pct_first"] > 50:
            st.warning(T("Le premier facteur explique plus de 50 % de la variance : biais de méthode commune possible."))
        else:
            st.success(T("Le premier facteur explique moins de 50 % de la variance : pas de signe de biais de méthode "
                         "commune selon le test de Harman."))
        _figure(lambda: fg.scree_plot(hm["eigenvalues"], T("Éboulis des valeurs propres"), T("facteur"),
                                      T("valeur propre")), "eboulis", "fig_scree", offer_file, ("scree", tuple(cols)))
        st.subheader(T("Colinéarité complète (Kock 2015)"))
        if res is None:
            st.info(T("Disponible après l'estimation du modèle (onglet Modèle)."))
        else:
            vif = ds.full_collinearity_vif(res.scores).to_frame()
            sheets["VIF complet"] = vif
            st.dataframe(flag(vif, {"VIF": lambda v: v > 3.3}), width="stretch")
            st.caption(T("VIF de chaque variable latente régressée sur toutes les autres. Rouge : VIF > 3,3, signe "
                         "possible de biais de méthode commune ou de colinéarité (Kock 2015). Plus sensible que le "
                         "test de Harman."))

    with t_n:
        n_avail = int(ds.numeric_frame(raw, cols).dropna().shape[0])
        beta_obs = None
        if res is not None and model is not None and model.structural:
            beta_obs = float(np.nanmin([abs(res.path_coefficients.loc[s, d]) for s, d in model.structural]))
        c1, c2 = st.columns(2)
        beta = c1.number_input(T("Plus petit coefficient de chemin attendu |β_min|"), 0.01, 0.99,
                               round(beta_obs, 2) if beta_obs and beta_obs >= 0.01 else 0.20, 0.01, key="n_beta",
                               help=T("Après estimation : le plus petit chemin observé. Sinon, la plus petite valeur "
                                      "que tu veux pouvoir détecter."))
        a = c2.radio(T("Seuil"), [0.01, 0.05, 0.10], index=1, horizontal=True, key="n_alpha",
                     format_func=lambda v: f"{num(v * 100, 0)} %")
        n_isr = ds.inverse_square_root_n(beta, a)
        m = st.columns(3)
        m[0].metric(T("n minimal (racine carrée inverse)"), n_isr)
        m[1].metric(T("n minimal (règle des 10 fois)"), ds.ten_times_rule(model) if model is not None else "—")
        m[2].metric(T("n disponible (lignes complètes)"), n_avail,
                    delta=n_avail - n_isr, delta_color="normal")
        st.caption(T("Méthode de la racine carrée inverse (Kock & Hadaya 2018) : taille minimale pour détecter "
                     "|β_min| avec une puissance de 80 %. La règle des 10 fois (10 × le plus grand nombre de flèches "
                     "pointant vers un construit) est plus ancienne et souvent trop optimiste."))

    with t_fig:
        lvs = sorted({lv for lv in blocks.values()}, key=list(blocks.values()).index)
        grp = st.selectbox(T("Construit"), lvs, key="fig_lv", format_func=lambda v: v or T("tous les indicateurs"))
        sub = [c for c, lv in blocks.items() if lv == grp]
        _figure(lambda: fg.boxplots(raw[sub], T("Boîtes à moustaches — {g}", g=grp or T("indicateurs"))),
                f"boites_{grp}", "fig_box", offer_file, ("box", grp, tuple(sub)))
        st.caption(T("Points rouges : valeurs au-delà de 1,5 écart interquartile. Les figures s'exportent en PNG "
                     "(300 ppp) pour Word ou en SVG pour une mise en page vectorielle."))

    st.session_state["prelim_sheets"] = sheets
    fp = None if res is None else (id(res), tuple(res.scores.columns))  # résultats d'une autre estimation
    xlsx = _cached(("xlsx", tuple(cols), st.session_state.get("corr_m"), fp), lambda: to_excel(sheets))
    offer_file("⬇  " + T("Analyses préliminaires (Excel)"), xlsx, T("openpls_preliminaires.xlsx"),
               key="dl_prelim", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
