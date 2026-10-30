"""Interface graphique OpenPLS (Streamlit).

Lancement :  openpls-gui      ou      streamlit run openpls/app.py
"""
from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from openpls import Model, fit, bootstrap_statistics, quality_criteria, htmt, fornell_larcker, f_squared
from openpls.effects import classify_mediation, effect_statistics, total_effects, specific_indirect_effects
from openpls.editor import model_editor
from openpls.gui_helpers import guess_syntax, model_to_dot, prepare_data, to_excel
from openpls.moderation import simple_slopes, simple_slope_statistics
from openpls.simulate import simulate

st.set_page_config(page_title="OpenPLS", page_icon="◎", layout="wide")

EXAMPLE_SYNTAX = """# Modèle de mesure  ( =~ réflectif,  <~ formatif )
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3

# Modèle structurel  ( cible ~ source1 + source2 ;  X:M = modération )
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1
"""
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # 3 premières teintes catégorielles validées (daltonisme)
RED = "color:#C0392B;font-weight:600"


# ---------------------------------------------------------------- utilitaires d'affichage
def fmt(df, digits: int = 3):
    if isinstance(df, pd.Series):
        df = df.to_frame()
    num = df.select_dtypes("number").columns
    return df.style.format({c: f"{{:.{digits}f}}" for c in num}, na_rep="")


def flag(df: pd.DataFrame, rules: dict, digits: int = 3):
    """Colore en rouge les valeurs qui violent un seuil : rules = {colonne: fonction -> bool (True = problème)}."""
    sty = fmt(df, digits)
    for col, bad in rules.items():
        if col in df.columns:
            sty = sty.map(lambda v, bad=bad: RED if pd.notna(v) and bad(v) else "", subset=[col])
    return sty


def yes_no(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == bool:
            out[c] = out[c].map({True: "oui", False: "non"})
    return out


@st.cache_data(show_spinner=False)
def read_file(content: bytes, name: str) -> pd.DataFrame:
    import io

    if name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    # séparateur détecté automatiquement (virgule, point-virgule, tabulation…)
    df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    if df.select_dtypes("number").shape[1] == 0:  # CSV français avec virgule décimale
        df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", decimal=",")
    return df


@st.cache_data(show_spinner=False)
def example_data() -> pd.DataFrame:
    """400 répondants, deux groupes dont le chemin ETA1 -> ETA2 diffère (0,6 vs 0,3)."""
    a = simulate(200, seed=11, direct=0.15)
    b = simulate(200, seed=12, direct=0.15, eta_path=0.3)
    d = pd.concat([a, b], ignore_index=True)
    d.insert(0, "groupe", ["A"] * 200 + ["B"] * 200)
    return d


def stored(name: str, key):
    """Résultat d'une analyse avancée mémorisé pour la même configuration, sinon None."""
    hit = st.session_state.get("adv", {}).get(name)
    return hit[1] if hit and hit[0] == key else None


def store(name: str, key, value):
    st.session_state.setdefault("adv", {})[name] = (key, value)


def run_button(label: str, key: str) -> bool:
    return st.button(f"▶  {label}", key=key, type="primary")


# ---------------------------------------------------------------- barre latérale
st.sidebar.title("◎ OpenPLS")
st.sidebar.caption("PLS-SEM libre et open source")

st.sidebar.header("1. Données")
source = st.sidebar.radio("Source", ["Données d'exemple", "Importer un fichier"], key="source")
if source == "Importer un fichier":
    up = st.sidebar.file_uploader("CSV ou Excel", type=["csv", "txt", "xlsx", "xls"])
    if up is None:
        st.info("Importe un fichier CSV ou Excel (une colonne par indicateur, une ligne par répondant) "
                "dans la barre latérale, ou choisis les données d'exemple.")
        st.stop()
    raw = read_file(up.getvalue(), up.name)
    data_id = f"file:{up.name}:{len(raw)}"
else:
    raw = example_data()
    data_id = "example"

st.sidebar.header("2. Paramètres")
algo = st.sidebar.selectbox("Algorithme", ["PLS", "PLSc (consistent)"], key="algo",
                            help="PLSc corrige l'atténuation pour les construits réflectifs (modèles de facteurs communs).")
scheme = st.sidebar.selectbox("Schéma de pondération interne", ["path", "factorial", "centroid"], key="scheme")
moderation = st.sidebar.selectbox(
    "Méthode de modération", ["two_stage", "product_indicator", "orthogonal"], key="moderation",
    format_func={"two_stage": "Deux étapes (recommandé)", "product_indicator": "Produit des indicateurs",
                 "orthogonal": "Orthogonalisation"}.get,
    help="Utilisée seulement si le modèle contient un terme d'interaction `X:M`.")
n_boot = st.sidebar.number_input("Échantillons bootstrap", 100, 20000, 1000, step=500, key="n_boot")
alpha = st.sidebar.selectbox("Seuil de significativité", [0.05, 0.01, 0.10], key="alpha")
seed = int(st.sidebar.number_input("Graine aléatoire", 0, 10**6, 42, key="seed"))

# ---------------------------------------------------------------- définition du modèle
st.title("Modèle")
numeric_cols = [c for c in raw.columns if pd.api.types.is_numeric_dtype(raw[c])]
if st.session_state.get("data_id") != data_id:
    st.session_state["data_id"] = data_id
    st.session_state["syntax"] = EXAMPLE_SYNTAX if data_id == "example" else guess_syntax(numeric_cols)
    for k in ("results", "boot", "adv", "editor_pos", "editor_nonce"):
        st.session_state.pop(k, None)

with st.expander(f"Aperçu des données — {raw.shape[0]} lignes × {raw.shape[1]} colonnes"):
    st.dataframe(raw.head(50), width="stretch")
    st.caption("Colonnes : " + ", ".join(map(str, raw.columns)))

tab_editor, tab_syntax = st.tabs(["Éditeur visuel", "Syntaxe"])
with tab_editor:
    st.caption("Glisse les indicateurs sur le canevas · tire la poignée bleue d'une variable vers une autre pour "
               "créer un chemin · clique un chemin pour ajouter un modérateur · puis « Appliquer au modèle ».")
    out = model_editor(numeric_cols, st.session_state["syntax"], st.session_state.get("editor_pos"))
    if out and out.get("nonce") != st.session_state.get("editor_nonce"):
        st.session_state["editor_nonce"] = out["nonce"]
        st.session_state["editor_pos"] = {k: tuple(v) for k, v in out.get("positions", {}).items()}
        st.session_state["syntax"] = out["syntax"]

with tab_syntax:
    left, right = st.columns([2, 3])
    with left:
        st.text_area("Syntaxe du modèle", key="syntax", height=320,
                     help="`LATENTE =~ ind1 + ind2` (réflectif) · `LATENTE <~ ind1 + ind2` (formatif) · "
                          "`CIBLE ~ SOURCE1 + SOURCE2` (chemins) · `CIBLE ~ X + M + X:M` (modération). "
                          "`#` pour les commentaires.")

try:
    model = Model.from_syntax(st.session_state["syntax"])
    data, warns = prepare_data(raw, model)
    if not model.structural:
        warns.append("Aucun chemin structurel : ajoute au moins une ligne `CIBLE ~ SOURCE`.")
    ok = bool(model.structural)
    model_error = None
except (ValueError, KeyError) as e:
    model, data, warns, ok, model_error = None, None, [], False, str(e).strip("'\"")

fit_kwargs = dict(scheme=scheme, consistent=algo.startswith("PLSc"))
if model is not None and model.interactions:
    fit_kwargs["moderation"] = moderation

if model_error:
    st.error(model_error)
for w in warns:
    st.warning(w)
run = st.button("▶  Estimer le modèle", type="primary", disabled=not ok)

res = None
if run and ok:
    try:
        res = fit(data, model, **fit_kwargs)
        st.session_state["results"] = (st.session_state["syntax"], fit_kwargs, res, data)
        st.session_state.pop("boot", None)
    except Exception as e:  # noqa: BLE001 - message lisible pour l'utilisateur
        st.error(f"Échec de l'estimation : {e}")

prev = st.session_state.get("results")
if prev and prev[0] == st.session_state["syntax"] and prev[1] == fit_kwargs:
    _, _, res, data = prev

with right:
    if model is not None:
        st.graphviz_chart(model_to_dot(model, res), width="stretch")
        if res is None:
            st.caption("Clique sur « Estimer le modèle » pour afficher les estimations sur le diagramme.")

if res is None:
    st.stop()

# ---------------------------------------------------------------- résultats
st.title("Résultats")
conv_res = res.measurement_result  # en deux étapes : l'itératif PLS est celui de l'étape 1
status = "convergé" if res.converged and conv_res.converged else "NON convergé"
mod_txt = f" · modération : {res.moderation}" if res.moderation else ""
st.caption(f"{'PLSc' if res.consistent else 'PLS'} · schéma {scheme} · {status} en {conv_res.iterations} itérations · "
           f"n = {len(data)}{mod_txt}")
if status != "convergé":
    st.error("L'algorithme n'a pas convergé : vérifie la spécification du modèle.")
with st.expander("Diagramme estimé", expanded=False):
    st.graphviz_chart(model_to_dot(model, res), width="stretch")

meas = res.measurement_result
q = quality_criteria(meas)
paths_tbl = pd.DataFrame(
    [{"chemin": f"{s} -> {d}", "coefficient": res.path_coefficients.loc[s, d]} for s, d in res.model.structural]
).set_index("chemin")
loadings_tbl = pd.DataFrame({"chargement": meas.outer_loadings, "poids": meas.outer_weights})
htmt_tbl = htmt(meas)
fl_tbl = fornell_larcker(meas)
endogenous = list(res.r_squared.index)
excel_extra: dict[str, pd.DataFrame] = {}

tabs = st.tabs(["Modèle structurel", "Modèle de mesure", "Validité discriminante",
                "Bootstrap & médiation", "Analyses avancées", "Scores"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Coefficients de chemin")
        st.dataframe(fmt(paths_tbl), width="stretch")
        st.subheader("R²")
        st.dataframe(fmt(res.r_squared.rename("R²").to_frame()), width="stretch")
    with c2:
        st.subheader("Taille d'effet f²")
        try:
            f2 = f_squared(res, data, **fit_kwargs)
            st.dataframe(fmt(f2), width="stretch")
            st.caption("Repères (Cohen) : 0,02 faible · 0,15 moyen · 0,35 fort. "
                       "Pour une interaction : 0,005 faible · 0,01 moyen · 0,025 fort (Kenny 2018).")
        except Exception as e:  # noqa: BLE001
            st.info(f"f² non calculable : {e}")
        st.subheader("Effets totaux")
        st.dataframe(fmt(total_effects(res).loc[:, endogenous]), width="stretch")
        ind = specific_indirect_effects(res)
        if len(ind):
            st.subheader("Effets indirects spécifiques")
            st.dataframe(fmt(ind.rename("effet").to_frame()), width="stretch")

    if model.interactions:
        st.subheader("Modération : pentes simples")
        for a, b, d in model.interactions:
            ss = simple_slopes(res, a, b, d)
            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown(f"**{a} × {b} → {d}** (interaction = {res.path_coefficients.loc[f'{a}:{b}', d]:.3f})")
                st.dataframe(fmt(ss), width="stretch")
                st.caption(f"Pente de {a} sur {d} quand {b} vaut -1, 0 ou +1 écart-type.")
            with c2:
                lines = pd.DataFrame([{"x": xv, "y": row[f"{d} si {a}={'-1' if xv < 0 else '+1'}"],
                                       "niveau": f"{b} = {lvl:+.0f} ET" if lvl else f"{b} = moyenne"}
                                      for lvl, row in ss.iterrows() for xv in (-1, 1)])
                ch = (alt.Chart(lines).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=64, filled=True))
                      .encode(x=alt.X("x:Q", title=f"{a} (écarts-types)", scale=alt.Scale(domain=[-1.2, 1.2])),
                              y=alt.Y("y:Q", title=f"{d} prédit (écarts-types)"),
                              color=alt.Color("niveau:N", title=b, sort=list(dict.fromkeys(lines["niveau"])),
                                              scale=alt.Scale(range=SERIES)),
                              tooltip=["niveau", alt.Tooltip("x:Q", title=a), alt.Tooltip("y:Q", format=".3f", title=d)])
                      .properties(height=260))
                st.altair_chart(ch, width="stretch")

with tabs[1]:
    if res.stage1 is not None:
        st.info("Modération en deux étapes : le modèle de mesure est évalué sur l'estimation de l'étape 1 "
                "(modèle sans interaction).")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Chargements et poids externes")
        st.dataframe(flag(loadings_tbl, {"chargement": lambda v: v < 0.708}), width="stretch", height=420)
        st.caption("Rouge : chargement < 0,708 (Hair et al.). Pour un bloc formatif, regarde plutôt les poids.")
    with c2:
        st.subheader("Fiabilité et validité convergente")
        st.dataframe(flag(q, {"cronbach_alpha": lambda v: v < 0.7, "rho_A": lambda v: v < 0.7,
                              "rho_c": lambda v: v < 0.7 or v > 0.95, "AVE": lambda v: v < 0.5}),
                     width="stretch")
        st.caption("Seuils : α, ρ_A, ρ_c ≥ 0,70 (ρ_c ≤ 0,95) · AVE ≥ 0,50. "
                   "Ces critères ne s'appliquent qu'aux construits réflectifs.")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("HTMT")
        st.dataframe(fmt(htmt_tbl).map(lambda v: RED if pd.notna(v) and v > 0.85 else ""), width="stretch")
        st.caption("Rouge : HTMT > 0,85 (seuil prudent ; 0,90 pour des construits conceptuellement proches).")
    with c2:
        st.subheader("Critère de Fornell-Larcker")
        st.dataframe(fmt(fl_tbl), width="stretch")
        st.caption("Diagonale = √AVE ; elle doit dépasser les corrélations de sa ligne et de sa colonne.")

with tabs[3]:
    st.write(f"Bootstrap à **{int(n_boot)}** échantillons, IC percentile à {int((1 - alpha) * 100)} %. "
             "Peut prendre de quelques secondes à quelques minutes.")

    def boot_stats(r):
        s = effect_statistics(r)
        return pd.concat([s, simple_slope_statistics(r)]) if r.spec is not None and r.spec.interactions else s

    if st.button("▶  Lancer le bootstrap", key="run_boot"):
        bar = st.progress(0.0, text="Bootstrap…")
        try:
            boot = bootstrap_statistics(
                data, model, boot_stats, n_boot=int(n_boot), seed=seed, alpha=alpha,
                progress=lambda i, n: bar.progress(i / n, text=f"Bootstrap {i}/{n}") if i % 25 == 0 or i == n else None,
                **fit_kwargs,
            )
            st.session_state["boot"] = (st.session_state["syntax"], fit_kwargs, int(n_boot), alpha, seed, boot)
        except Exception as e:  # noqa: BLE001
            st.error(f"Échec du bootstrap : {e}")
        bar.empty()

    b = st.session_state.get("boot")
    if b and b[:5] == (st.session_state["syntax"], fit_kwargs, int(n_boot), alpha, seed):
        boot = b[5]
        lo, hi = boot.columns[-2], boot.columns[-1]
        sig = (boot[lo] > 0) | (boot[hi] < 0)
        boot_view = boot.assign(significatif=sig.map({True: "oui", False: "non"}))
        labels = {"direct": "Effets directs (coefficients de chemin)", "specific_indirect": "Effets indirects spécifiques",
                  "total_indirect": "Effets indirects totaux", "total": "Effets totaux",
                  "simple_slope": "Pentes simples (modération)"}
        for kind, title in labels.items():
            if kind in boot_view.index.get_level_values(0):
                st.subheader(title)
                st.dataframe(fmt(boot_view.loc[kind]), width="stretch")

        rows = []
        for name in boot.loc["specific_indirect"].index if "specific_indirect" in boot.index.get_level_values(0) else []:
            nodes = name.split(" -> ")
            pair = f"{nodes[0]} -> {nodes[-1]}"
            has_d = ("direct", pair) in boot.index
            d_est = boot.loc[("direct", pair), "estimate"] if has_d else 0.0
            d_sig = bool(sig[("direct", pair)]) if has_d else False
            i_est = boot.loc[("specific_indirect", name), "estimate"]
            i_sig = bool(sig[("specific_indirect", name)])
            if has_d:
                kind_lbl = classify_mediation(d_sig, i_sig, d_est, i_est)
            else:
                kind_lbl = ("indirecte (type indéterminé : chemin direct non estimé)" if i_sig
                            else "aucun effet indirect")
            rows.append({"chemin": name, "indirect": i_est, "indirect signif.": "oui" if i_sig else "non",
                         "direct": f"{d_est:.3f}" if has_d else "—",
                         "direct signif.": ("oui" if d_sig else "non") if has_d else "non estimé",
                         "type de médiation": kind_lbl})
        if rows:
            st.subheader("Analyse de médiation")
            st.dataframe(fmt(pd.DataFrame(rows).set_index("chemin")), width="stretch")
            st.caption("Typologie de Zhao, Lynch & Chen (2010). Significativité = l'IC bootstrap exclut 0. "
                       "Pour tester une médiation partielle, le chemin direct doit figurer dans le modèle.")
        st.session_state["boot_table"] = boot_view
    else:
        st.session_state.pop("boot_table", None)

# ---------------------------------------------------------------- analyses avancées
ADV = ["Prédiction (PLSpredict, CVPAT)", "Multigroupe (MGA, MICOM)", "Importance-performance (IPMA)",
       "Conditions nécessaires (NCA)", "Endogénéité (copules)", "CB-SEM / CFA", "Segmentation (FIMIX-PLS)"]
base_key = (st.session_state["syntax"], tuple(sorted(fit_kwargs.items())), seed, len(data))
plain = not model.interactions

with tabs[4]:
    choice = st.radio("Analyse", ADV, horizontal=True, key="adv_choice", label_visibility="collapsed")
    st.divider()

    if choice == ADV[0]:
        st.markdown("Validation croisée à k plis répétée : le modèle prédit-il de **nouvelles** observations "
                    "mieux qu'une simple moyenne (Q²_predict > 0) et qu'une régression linéaire (LM) ?")
        if not plain:
            st.warning("PLSpredict n'est pas disponible pour les modèles avec interaction.")
        else:
            c = st.columns(3)
            k = c[0].number_input("Plis (k)", 2, 50, 10, key="pp_k")
            reps = c[1].number_input("Répétitions", 1, 100, 10, key="pp_r")
            approach = c[2].selectbox("Approche", ["EA", "DA"], key="pp_a",
                                      help="EA : prédiction à partir des seules exogènes (recommandé). "
                                           "DA : à partir des antécédents directs.")
            key = base_key + ("pred", k, reps, approach)
            if run_button("Lancer PLSpredict et CVPAT", "run_pred"):
                from openpls.predict import pls_predict, cvpat

                with st.spinner("Validation croisée…"):
                    try:
                        store("pred", key, (pls_predict(data, model, k=int(k), repetitions=int(reps), seed=seed,
                                                        approach=approach, **fit_kwargs),
                                            cvpat(data, model, k=int(k), repetitions=int(reps), seed=seed,
                                                  approach=approach, **fit_kwargs)))
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Échec : {e}")
            out = stored("pred", key)
            if out:
                pp, cv = out
                st.subheader("Indicateurs endogènes")
                st.dataframe(flag(yes_no(pp["indicators"]), {"Q2_predict": lambda v: v <= 0}), width="stretch")
                n_better = int(pp["indicators"]["PLS < LM (RMSE)"].sum())
                n_tot = len(pp["indicators"])
                verdict = ("élevée" if n_better == n_tot else "moyenne" if n_better > n_tot / 2
                           else "faible" if n_better > 0 else "nulle")
                st.caption(f"PLS bat LM sur {n_better}/{n_tot} indicateurs → puissance prédictive **{verdict}** "
                           "(Shmueli et al. 2019). Rouge : Q²_predict ≤ 0.")
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Latentes endogènes")
                    st.dataframe(fmt(pp["latents"]), width="stretch")
                with c2:
                    st.subheader("CVPAT")
                    st.dataframe(fmt(yes_no(cv)), width="stretch")
                    st.caption("Différence de perte < 0 et p < 0,05 : PLS prédit significativement mieux que "
                               "le benchmark (IA = moyenne des indicateurs, LM = régression linéaire).")
                excel_extra.update({"PLSpredict": pp["indicators"], "PLSpredict latentes": pp["latents"], "CVPAT": cv})

    elif choice == ADV[1]:
        st.markdown("Compare les coefficients de chemin de **deux groupes**, après avoir vérifié l'invariance "
                    "de mesure (MICOM).")
        cand = [c for c in raw.columns if c not in model.indicators and raw[c].nunique(dropna=True) <= 20]
        if not cand:
            st.info("Aucune colonne de groupe disponible : il faut une colonne (hors indicateurs) avec peu de "
                    "modalités, par exemple « sexe » ou « pays ».")
        else:
            c = st.columns(4)
            gcol = c[0].selectbox("Variable de groupe", cand, key="mga_col")
            levels = list(pd.unique(raw[gcol].dropna()))
            pick = c[1].multiselect("Deux groupes à comparer", levels, default=levels[:2], max_selections=2,
                                    key="mga_lv")
            n_perm = c[2].number_input("Permutations", 100, 10000, 1000, step=500, key="mga_np")
            n_bt = c[3].number_input("Bootstrap par groupe", 100, 10000, 500, step=500, key="mga_nb")
            key = base_key + ("mga", gcol, tuple(map(str, pick)), n_perm, n_bt)
            if len(pick) != 2:
                st.info("Choisis exactement deux groupes.")
            elif run_button("Lancer MGA et MICOM", "run_mga"):
                from openpls.mga import mga

                dg, _ = prepare_data(raw, model, keep=[gcol])
                dg = dg[dg[gcol].isin(pick)].reset_index(drop=True)
                bar = st.progress(0.0, text="Permutations et bootstrap…")
                try:
                    store("mga", key, mga(dg[model.indicators], model, dg[gcol], n_perm=int(n_perm), n_boot=int(n_bt),
                                          seed=seed, progress=lambda i, n: bar.progress(min(i / n, 1.0))
                                          if i % 20 == 0 else None, **fit_kwargs))
                except Exception as e:  # noqa: BLE001
                    st.error(f"Échec : {e}")
                bar.empty()
            out = stored("mga", key)
            if out:
                st.write("Effectifs : " + " · ".join(f"**{g}** n = {n}" for g, n in out["groups"].items()))
                st.subheader("MICOM — invariance de mesure")
                ok_inv = out["verdict"].startswith("invariance")
                if ok_inv:
                    st.success(out["verdict"].capitalize())
                else:
                    st.warning(out["verdict"].capitalize())
                c1, c2 = st.columns([2, 3])
                with c1:
                    st.markdown("**Étape 2 — invariance compositionnelle**")
                    st.dataframe(flag(yes_no(out["micom_step2"]), {"invariance compositionnelle": lambda v: v == "non"},
                                      digits=4), width="stretch")
                with c2:
                    st.markdown("**Étape 3 — égalité des moyennes et des variances**")
                    st.dataframe(fmt(yes_no(out["micom_step3"])), width="stretch")
                st.subheader("Comparaison des chemins")
                st.dataframe(flag(yes_no(out["comparison"]),
                                  {"p_permutation": lambda v: v < 0.05, "p_henseler": lambda v: v < 0.05,
                                   "p_welch": lambda v: v < 0.05}), width="stretch")
                st.caption("En rouge : p < 0,05 (différence significative). Test de permutation recommandé "
                           "(Chin & Dibbern 2010) ; PLS-MGA de Henseler (2009) et Welch-Satterthwaite en complément.")
                excel_extra.update({"MGA": out["comparison"], "MICOM etape 2": out["micom_step2"],
                                    "MICOM etape 3": out["micom_step3"]})

    elif choice == ADV[2]:
        st.markdown("Quels antécédents ont une forte **importance** (effet total non standardisé) mais une faible "
                    "**performance** (score moyen sur 0-100) ? Ce sont les leviers prioritaires.")
        if not plain:
            st.warning("IPMA non disponible pour les modèles avec interaction.")
        else:
            c = st.columns(4)
            target = c[0].selectbox("Construit cible", endogenous, index=len(endogenous) - 1, key="ipma_t")
            theo = c[1].checkbox("Bornes théoriques de l'échelle", key="ipma_theo",
                                 help="Sinon, min et max observés de chaque indicateur.")
            lo_s = c[2].number_input("Minimum", value=1.0, key="ipma_lo", disabled=not theo)
            hi_s = c[3].number_input("Maximum", value=7.0, key="ipma_hi", disabled=not theo)
            from openpls.ipma import ipma

            try:
                out = ipma(res, data, target, scale=(lo_s, hi_s) if theo else None)
            except Exception as e:  # noqa: BLE001
                out = None
                st.error(str(e))
            if out:
                lat = out["latents"].reset_index()
                ch = (alt.Chart(lat).mark_circle(size=140, color=SERIES[0], opacity=0.9)
                      .encode(x=alt.X("importance:Q", title="Importance (effet total non standardisé)",
                                      scale=alt.Scale(domain=[min(0, lat["importance"].min()),
                                                              lat["importance"].max() * 1.25])),
                              y=alt.Y("performance:Q", title="Performance (0-100)",
                                      scale=alt.Scale(zero=False, padding=20)),
                              tooltip=["latente", alt.Tooltip("importance:Q", format=".3f"),
                                       alt.Tooltip("performance:Q", format=".1f")]))
                txt = ch.mark_text(dx=10, align="left", fontSize=12, color="#52514e").encode(text="latente")
                rx = alt.Chart(pd.DataFrame({"v": [lat["importance"].mean()]})).mark_rule(
                    strokeDash=[4, 4], color="#9a9893").encode(x="v:Q")
                ry = alt.Chart(pd.DataFrame({"v": [lat["performance"].mean()]})).mark_rule(
                    strokeDash=[4, 4], color="#9a9893").encode(y="v:Q")
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.altair_chart((ch + txt + rx + ry).properties(height=340, title=f"Carte IPMA — {target}"),
                                    width="stretch")
                    st.caption("Lignes pointillées : moyennes. En bas à droite : forte importance, faible "
                               "performance → priorités d'action.")
                with c2:
                    st.metric(f"Performance de {target}", f"{out['target_performance']:.1f} / 100")
                    st.dataframe(fmt(out["latents"]), width="stretch")
                st.subheader("Niveau indicateur")
                st.dataframe(fmt(out["indicators"]), width="stretch")
                excel_extra.update({"IPMA": out["latents"], "IPMA indicateurs": out["indicators"]})

    elif choice == ADV[3]:
        st.markdown("Un antécédent est-il une **condition nécessaire** de la cible (pas de niveau élevé de la "
                    "cible sans un niveau suffisant de l'antécédent) ? Plafond CE-FDH, test de permutation.")
        c = st.columns(3)
        target = c[0].selectbox("Construit cible", endogenous, key="nca_t")
        n_perm = c[1].number_input("Permutations", 100, 10000, 1000, step=500, key="nca_np")
        key = base_key + ("nca", target, n_perm)
        if run_button("Lancer la NCA", "run_nca"):
            from openpls.nca import nca

            with st.spinner("Permutations…"):
                try:
                    store("nca", key, nca(res, target, n_perm=int(n_perm), seed=seed))
                except Exception as e:  # noqa: BLE001
                    st.error(f"Échec : {e}")
        out = stored("nca", key)
        if out:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.subheader("Tailles d'effet")
                st.dataframe(fmt(yes_no(out["effects"])), width="stretch")
                st.caption("d : 0-0,1 faible · 0,1-0,3 moyen · 0,3-0,5 fort · ≥ 0,5 très fort (Dul 2016).")
            with c2:
                st.subheader("Tableau des goulots")
                st.dataframe(fmt(out["bottleneck"], 1), width="stretch")
                st.caption(f"Niveau minimal de chaque antécédent (% de son étendue) requis pour atteindre chaque "
                           f"niveau de {target}. Vide = non nécessaire à ce niveau.")
            lv_pick = st.selectbox("Nuage de points", list(out["effects"].index), key="nca_plot")
            x, y = res.scores[lv_pick].to_numpy(), res.scores[target].to_numpy()
            order = np.argsort(x)
            ceil = np.maximum.accumulate(y[order])
            step = pd.DataFrame({"x": np.append(x[order], x.max()), "y": np.append(ceil, ceil[-1])})
            pts = alt.Chart(pd.DataFrame({"x": x, "y": y})).mark_circle(size=40, opacity=0.5, color=SERIES[0]).encode(
                x=alt.X("x:Q", title=f"{lv_pick} (score)"), y=alt.Y("y:Q", title=f"{target} (score)"),
                tooltip=[alt.Tooltip("x:Q", format=".2f", title=lv_pick), alt.Tooltip("y:Q", format=".2f", title=target)])
            line = alt.Chart(step).mark_line(interpolate="step-after", color=SERIES[1], strokeWidth=2).encode(x="x:Q", y="y:Q")
            st.altair_chart((pts + line).properties(height=320), width="stretch")
            st.caption("Ligne orange : plafond CE-FDH. La zone vide au-dessus-gauche mesure la contrainte de nécessité.")
            excel_extra.update({"NCA": out["effects"], "NCA goulots": out["bottleneck"]})

    elif choice == ADV[4]:
        st.markdown("Un antécédent est-il corrélé au terme d'erreur (endogénéité) ? Ajout de termes de **copule "
                    "gaussienne** (Park & Gupta 2012) ; un terme significatif signale un problème.")
        c = st.columns(3)
        target = c[0].selectbox("Construit cible", endogenous, key="endo_t")
        nb = c[1].number_input("Bootstrap", 100, 10000, 1000, step=500, key="endo_nb")
        key = base_key + ("endo", target, nb)
        if run_button("Lancer le test", "run_endo"):
            from openpls.endogeneity import gaussian_copula

            with st.spinner("Bootstrap…"):
                try:
                    store("endo", key, gaussian_copula(res, target, n_boot=int(nb), seed=seed))
                except Exception as e:  # noqa: BLE001
                    st.error(f"Échec : {e}")
        out = stored("endo", key)
        if out:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.subheader("Non-normalité (Shapiro-Wilk)")
                st.dataframe(flag(yes_no(out["normality"]), {"non normal (p<0,05)": lambda v: v == "non"}),
                             width="stretch")
                st.caption("Rouge : distribution normale → la copule n'est pas identifiée pour ce régresseur.")
            with c2:
                st.subheader("Synthèse")
                summ = out["summary"].set_index(["modèle", "régresseur"])
                st.dataframe(fmt(summ).map(lambda v: RED if v == "endogénéité" else
                                           "color:#6b7280;font-style:italic" if str(v).startswith("non interp") else "",
                                           subset=["conclusion"]), width="stretch")
                st.caption("La copule n'est identifiée que si le régresseur est non normal : sinon la conclusion "
                           "est « non interprétable », quelle que soit la p-value.")
            with st.expander("Détail de chaque modèle"):
                st.dataframe(fmt(out["models"]), width="stretch")
            excel_extra.update({"Endogeneite": out["summary"]})

    elif choice == ADV[5]:
        st.markdown("Estimation par **maximum de vraisemblance** (modèle de facteurs communs), avec indices "
                    "d'ajustement globaux. La CFA corrèle toutes les latentes sans chemins structurels.")
        kind = st.radio("Type", ["SEM complet", "CFA (analyse factorielle confirmatoire)"], horizontal=True, key="cb_kind")
        from openpls.cbsem import fit_cbsem

        try:
            cb = fit_cbsem(data, model, cfa=kind.startswith("CFA"))
        except Exception as e:  # noqa: BLE001
            cb = None
            st.error(str(e))
        if cb is not None:
            if not cb.converged:
                st.warning("L'optimisation n'a pas pleinement convergé : interprète avec prudence.")
            fi = cb.fit_indices
            m = st.columns(5)
            m[0].metric("χ² (ddl)", f"{fi['chi2']:.1f} ({int(fi['ddl'])})", help=f"p = {fi['p_value']:.3f}")
            m[1].metric("CFI", f"{fi['CFI']:.3f}", help="≥ 0,95 bon (Hu & Bentler 1999)")
            m[2].metric("TLI", f"{fi['TLI']:.3f}", help="≥ 0,95 bon")
            m[3].metric("RMSEA", f"{fi['RMSEA']:.3f}", help=f"≤ 0,06 bon · IC 90 % [{fi['RMSEA IC90 bas']:.3f} ; "
                                                             f"{fi['RMSEA IC90 haut']:.3f}]")
            m[4].metric("SRMR", f"{fi['SRMR']:.3f}", help="≤ 0,08 bon")
            bad = [n for n, v, t in (("CFI", fi["CFI"], fi["CFI"] < 0.95), ("TLI", fi["TLI"], fi["TLI"] < 0.95),
                                     ("RMSEA", fi["RMSEA"], fi["RMSEA"] > 0.06), ("SRMR", fi["SRMR"], fi["SRMR"] > 0.08)) if t]
            if bad:
                st.warning(f"Ajustement insuffisant selon : {', '.join(bad)} (seuils de Hu & Bentler 1999).")
            else:
                st.success("Tous les indices respectent les seuils de Hu & Bentler (1999).")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Chargements standardisés")
                st.dataframe(flag(cb.loadings.rename("chargement").to_frame(), {"chargement": lambda v: v < 0.708}),
                             width="stretch", height=380)
            with c2:
                if not kind.startswith("CFA"):
                    st.subheader("Chemins standardisés")
                    st.dataframe(fmt(pd.DataFrame([{"chemin": f"{s} -> {d}", "coefficient": cb.path_coefficients.loc[s, d]}
                                                   for s, d in model.structural]).set_index("chemin")), width="stretch")
                    st.subheader("R²")
                    st.dataframe(fmt(cb.r_squared.rename("R²")), width="stretch")
                st.subheader("Corrélations entre latentes")
                st.dataframe(fmt(cb.latent_correlations), width="stretch")
            with st.expander("Tous les paramètres (estimations non standardisées, erreurs-types, p-values)"):
                st.dataframe(fmt(cb.estimates, 4), width="stretch")
            excel_extra.update({"CB-SEM ajustement": fi.to_frame("valeur"), "CB-SEM parametres": cb.estimates})

    elif choice == ADV[6]:
        st.markdown("Y a-t-il des **segments cachés** de répondants avec des relations structurelles différentes ? "
                    "FIMIX-PLS estime un mélange de régressions sur les scores des latentes.")
        if not plain:
            st.warning("FIMIX-PLS n'est pas disponible pour les modèles avec interaction.")
        else:
            c = st.columns(3)
            smax = c[0].slider("Nombre maximal de segments", 2, 8, 4, key="fx_s")
            starts = c[1].number_input("Départs aléatoires", 1, 100, 10, key="fx_st")
            key = base_key + ("fimix", smax, starts)
            if run_button("Lancer FIMIX-PLS", "run_fimix"):
                from openpls.fimix import fimix

                with st.spinner("Algorithme EM…"):
                    try:
                        store("fimix", key, fimix(res, segments=range(1, smax + 1), starts=int(starts), seed=seed))
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Échec : {e}")
            out = stored("fimix", key)
            if out:
                crit = out["criteria"]
                st.subheader("Critères de choix du nombre de segments")
                sty = fmt(crit)
                for col in ("AIC", "AIC3", "AIC4", "BIC", "CAIC"):
                    best = crit[col].idxmin()
                    sty = sty.map(lambda v, best_v=crit.loc[best, col]: "font-weight:700;background:#DCE8F7"
                                  if v == best_v else "", subset=[col])
                st.dataframe(sty, width="stretch")
                st.caption("En surligné : minimum de chaque critère. Retiens S quand AIC3 et CAIC s'accordent "
                           "(Sarstedt et al. 2011) ; EN > 0,5 indique des segments bien séparés. Un segment très "
                           "petit (< 5 %) est rarement interprétable.")
                pick = st.selectbox("Solution à afficher", list(out["solutions"]),
                                    index=int(crit["CAIC"].idxmin()) - 1, key="fx_pick")
                sol = out["solutions"][pick]
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown("**Taille des segments**")
                    st.dataframe(fmt(sol["sizes"]), width="stretch")
                    st.markdown("**R² par segment**")
                    st.dataframe(fmt(sol["r_squared"]), width="stretch")
                with c2:
                    st.markdown("**Coefficients de chemin par segment**")
                    st.dataframe(fmt(sol["paths"]), width="stretch")
                    st.download_button("⬇  Appartenance aux segments (CSV)",
                                       sol["posterior"].assign(segment=sol["membership"]).to_csv(index_label="observation"),
                                       "segments_fimix.csv", key="fx_dl")
                excel_extra.update({"FIMIX criteres": crit, "FIMIX chemins": sol["paths"]})

with tabs[5]:
    st.subheader("Scores des variables latentes (standardisés)")
    st.dataframe(fmt(res.scores), width="stretch", height=400)

# ---------------------------------------------------------------- export
sheets = {
    "Chemins": paths_tbl, "R2": res.r_squared.rename("R2").to_frame(), "Effets totaux": total_effects(res),
    "Chargements": loadings_tbl, "Qualite": q, "HTMT": htmt_tbl, "Fornell-Larcker": fl_tbl,
    "Scores": res.scores,
}
if st.session_state.get("boot_table") is not None:
    sheets["Bootstrap"] = st.session_state["boot_table"]
# résultats d'analyses avancées déjà calculés pour ce modèle (même si un autre onglet est affiché)
for name, (k, v) in st.session_state.get("adv", {}).items():
    if k[: len(base_key)] != base_key:
        continue
    if name == "pred":
        excel_extra.setdefault("PLSpredict", v[0]["indicators"]); excel_extra.setdefault("CVPAT", v[1])
    elif name == "mga":
        excel_extra.setdefault("MGA", v["comparison"]); excel_extra.setdefault("MICOM etape 2", v["micom_step2"])
        excel_extra.setdefault("MICOM etape 3", v["micom_step3"])
    elif name == "nca":
        excel_extra.setdefault("NCA", v["effects"]); excel_extra.setdefault("NCA goulots", v["bottleneck"])
    elif name == "endo":
        excel_extra.setdefault("Endogeneite", v["summary"])
    elif name == "fimix":
        excel_extra.setdefault("FIMIX criteres", v["criteria"])
sheets.update(excel_extra)
st.sidebar.header("3. Export")
st.sidebar.download_button("⬇  Résultats (Excel)", to_excel(sheets), "openpls_resultats.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width="stretch")
st.sidebar.download_button("⬇  Syntaxe du modèle", st.session_state["syntax"], "modele.txt",
                           width="stretch")
