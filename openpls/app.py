"""Interface graphique OpenPLS (Streamlit).

Lancement :  openpls-gui      ou      streamlit run openpls/app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from openpls import Model, fit, bootstrap_statistics, quality_criteria, htmt, fornell_larcker, f_squared
from openpls.effects import classify_mediation, effect_statistics, total_effects, specific_indirect_effects
from openpls.gui_helpers import guess_syntax, model_to_dot, prepare_data, to_excel
from openpls.simulate import simulate

st.set_page_config(page_title="OpenPLS", page_icon="◎", layout="wide")

EXAMPLE_SYNTAX = """# Modèle de mesure  ( =~ réflectif,  <~ formatif )
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3

# Modèle structurel  ( cible ~ source1 + source2 )
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1
"""


# ---------------------------------------------------------------- utilitaires d'affichage
def fmt(df: pd.DataFrame, digits: int = 3):
    num = df.select_dtypes("number").columns
    return df.style.format({c: f"{{:.{digits}f}}" for c in num}, na_rep="")


def flag(df: pd.DataFrame, rules: dict, digits: int = 3):
    """Colore en rouge les valeurs qui violent un seuil : rules = {colonne: fonction -> bool (True = problème)}."""
    sty = fmt(df, digits)
    for col, bad in rules.items():
        if col in df.columns:
            sty = sty.map(lambda v, bad=bad: "color:#C0392B;font-weight:600" if pd.notna(v) and bad(v) else "",
                          subset=[col])
    return sty


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
    raw = simulate(n=400, seed=11, direct=0.15)
    data_id = "example"

st.sidebar.header("2. Paramètres")
algo = st.sidebar.selectbox("Algorithme", ["PLS", "PLSc (consistent)"], key="algo",
                            help="PLSc corrige l'atténuation pour les construits réflectifs (modèles de facteurs communs).")
scheme = st.sidebar.selectbox("Schéma de pondération interne", ["path", "factorial", "centroid"], key="scheme")
n_boot = st.sidebar.number_input("Échantillons bootstrap", 100, 20000, 1000, step=500, key="n_boot")
alpha = st.sidebar.selectbox("Seuil de significativité", [0.05, 0.01, 0.10], key="alpha")
seed = st.sidebar.number_input("Graine aléatoire", 0, 10**6, 42, key="seed")
fit_kwargs = dict(scheme=scheme, consistent=algo.startswith("PLSc"))

# ---------------------------------------------------------------- définition du modèle
st.title("Modèle")
if st.session_state.get("data_id") != data_id:
    st.session_state["data_id"] = data_id
    numeric_cols = [c for c in raw.columns if pd.api.types.is_numeric_dtype(raw[c])]
    st.session_state["syntax"] = EXAMPLE_SYNTAX if data_id == "example" else guess_syntax(numeric_cols)
    st.session_state.pop("results", None)
    st.session_state.pop("boot", None)

with st.expander(f"Aperçu des données — {raw.shape[0]} lignes × {raw.shape[1]} colonnes"):
    st.dataframe(raw.head(50), width="stretch")
    st.caption("Colonnes : " + ", ".join(map(str, raw.columns)))

left, right = st.columns([2, 3])
with left:
    st.text_area("Syntaxe du modèle", key="syntax", height=320,
                 help="`LATENTE =~ ind1 + ind2` (réflectif) · `LATENTE <~ ind1 + ind2` (formatif) · "
                      "`CIBLE ~ SOURCE1 + SOURCE2` (chemins). `#` pour les commentaires.")
    try:
        model = Model.from_syntax(st.session_state["syntax"])
        data, warns = prepare_data(raw, model)
        if not model.structural:
            warns.append("Aucun chemin structurel : ajoute au moins une ligne `CIBLE ~ SOURCE`.")
        ok = bool(model.structural)
    except (ValueError, KeyError) as e:
        st.error(str(e).strip("'\""))
        model, data, warns, ok = None, None, [], False
    for w in warns:
        st.warning(w)
    run = st.button("▶  Estimer le modèle", type="primary", disabled=not ok, width="stretch")

res = None
if run and ok:
    try:
        res = fit(data, model, **fit_kwargs)
        st.session_state["results"] = (st.session_state["syntax"], fit_kwargs, res, data)
        st.session_state.pop("boot", None)
    except Exception as e:  # noqa: BLE001 - message lisible pour l'utilisateur
        st.error(f"Échec de l'estimation : {e}")

stored = st.session_state.get("results")
if stored and stored[0] == st.session_state["syntax"] and stored[1] == fit_kwargs:
    _, _, res, data = stored

with right:
    if model is not None:
        st.graphviz_chart(model_to_dot(model, res), width="stretch")
        if res is None:
            st.caption("Clique sur « Estimer le modèle » pour afficher les estimations sur le diagramme.")

if res is None:
    st.stop()

# ---------------------------------------------------------------- résultats
st.title("Résultats")
status = "convergé" if res.converged else "NON convergé"
st.caption(f"{'PLSc' if res.consistent else 'PLS'} · schéma {scheme} · {status} en {res.iterations} itérations · "
           f"n = {len(data)}")
if not res.converged:
    st.error("L'algorithme n'a pas convergé : vérifie la spécification du modèle.")

q = quality_criteria(res)
paths_tbl = pd.DataFrame(
    [{"chemin": f"{s} -> {d}", "coefficient": res.path_coefficients.loc[s, d]} for s, d in model.structural]
).set_index("chemin")
loadings_tbl = pd.DataFrame({"chargement": res.outer_loadings, "poids": res.outer_weights})
htmt_tbl = htmt(res)
fl_tbl = fornell_larcker(res)

tabs = st.tabs(["Modèle structurel", "Modèle de mesure", "Validité discriminante",
                "Bootstrap & médiation", "Scores"])

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
            st.caption("Repères (Cohen) : 0,02 faible · 0,15 moyen · 0,35 fort")
        except Exception as e:  # noqa: BLE001
            f2 = None
            st.info(f"f² non calculable : {e}")
        st.subheader("Effets totaux")
        st.dataframe(fmt(total_effects(res).loc[:, res.r_squared.index]), width="stretch")
        ind = specific_indirect_effects(res)
        if len(ind):
            st.subheader("Effets indirects spécifiques")
            st.dataframe(fmt(ind.rename("effet").to_frame()), width="stretch")

with tabs[1]:
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
        st.dataframe(fmt(htmt_tbl).map(lambda v: "color:#C0392B;font-weight:600" if pd.notna(v) and v > 0.85 else ""),
                     width="stretch")
        st.caption("Rouge : HTMT > 0,85 (seuil prudent ; 0,90 pour des construits conceptuellement proches).")
    with c2:
        st.subheader("Critère de Fornell-Larcker")
        st.dataframe(fmt(fl_tbl), width="stretch")
        st.caption("Diagonale = √AVE ; elle doit dépasser les corrélations de sa ligne et de sa colonne.")

with tabs[3]:
    st.write(f"Bootstrap à **{int(n_boot)}** échantillons, IC percentile à {int((1 - alpha) * 100)} %. "
             "Peut prendre de quelques secondes à quelques minutes.")
    if st.button("▶  Lancer le bootstrap", key="run_boot"):
        bar = st.progress(0.0, text="Bootstrap…")
        try:
            boot = bootstrap_statistics(
                data, model, effect_statistics, n_boot=int(n_boot), seed=int(seed), alpha=alpha,
                progress=lambda i, n: bar.progress(i / n, text=f"Bootstrap {i}/{n}") if i % 25 == 0 or i == n else None,
                **fit_kwargs,
            )
            st.session_state["boot"] = (st.session_state["syntax"], fit_kwargs, int(n_boot), alpha, int(seed), boot)
        except Exception as e:  # noqa: BLE001
            st.error(f"Échec du bootstrap : {e}")
        bar.empty()

    b = st.session_state.get("boot")
    if b and b[:5] == (st.session_state["syntax"], fit_kwargs, int(n_boot), alpha, int(seed)):
        boot = b[5]
        lo, hi = boot.columns[-2], boot.columns[-1]
        sig = (boot[lo] > 0) | (boot[hi] < 0)
        boot_view = boot.assign(significatif=sig.map({True: "oui", False: "non"}))
        labels = {"direct": "Effets directs (coefficients de chemin)", "specific_indirect": "Effets indirects spécifiques",
                  "total_indirect": "Effets indirects totaux", "total": "Effets totaux"}
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

with tabs[4]:
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
st.sidebar.header("3. Export")
st.sidebar.download_button("⬇  Résultats (Excel)", to_excel(sheets), "openpls_resultats.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width="stretch")
st.sidebar.download_button("⬇  Syntaxe du modèle", st.session_state["syntax"], "modele.txt",
                           width="stretch")
