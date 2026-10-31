"""Interface graphique OpenPLS (Streamlit).

Lancement :  openpls-gui      ou      streamlit run openpls/app.py
"""
from __future__ import annotations

import html
import os
import sys
import time
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from openpls import Model, fit, bootstrap_statistics, quality_criteria, htmt, fornell_larcker, f_squared
from openpls.effects import classify_mediation, effect_statistics, total_effects, specific_indirect_effects
from openpls.editor import model_editor
from openpls.assessment import measurement_statistics
from openpls.bootstrap import with_confidence_level
from openpls.gui_helpers import (fmt_p, guess_syntax, model_to_dot, num, prepare_data, set_decimal, stars,
                                 stars_legend, to_excel)
from openpls.settings import decimal_separator, default_decimal, load_prefs, save_pref, separator_for
from openpls.i18n import T, tr, set_language, ui_language
from openpls.higher_order import higher_order_measurement, higher_order_statistics, structural_view
from openpls.moderation import simple_slopes, simple_slope_statistics
from openpls.simulate import simulate, simulate_higher_order

_HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="OpenPLS", page_icon=str(_HERE / "static" / "icon.png"), layout="wide")
st.html(f"<style>{(_HERE / 'style.css').read_text(encoding='utf-8')}</style>")
if "lang" not in st.session_state:
    st.session_state["lang"] = ui_language()
for _k, _v in st.session_state.pop("_carry", {}).items():  # valeurs des widgets après un changement de langue
    st.session_state[_k] = _v
set_language(st.session_state["lang"])
if "decimal" not in st.session_state:
    st.session_state["decimal"] = decimal_separator()
set_decimal(st.session_state["decimal"])
st.logo(str(_HERE / "static" / "logo.svg"), size="large", icon_image=str(_HERE / "static" / "mark.svg"))
from openpls import menu as _menu

_menu.render()  # À propos, Mises à jour, Paramètres : en haut à droite, sur la ligne des onglets

EXAMPLE_SYNTAX = T("# Modèle de mesure  ( =~ réflectif,  <~ formatif )") + """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3

""" + T("# Modèle structurel  ( cible ~ source1 + source2 ;  X:M = modération )") + """
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1
"""
HOC_SYNTAX = T("# Modèle de mesure (ordre 1)") + """
X  =~ x_1 + x_2 + x_3
L1 =~ l1_1 + l1_2 + l1_3
L2 =~ l2_1 + l2_2 + l2_3
L3 =~ l3_1 + l3_2 + l3_3
Y  =~ y_1 + y_2 + y_3

""" + T("# Construit de second ordre : ses termes sont des variables latentes") + """
QUALITE =~ L1 + L2 + L3

""" + T("# Modèle structurel") + """
QUALITE ~ X
Y ~ QUALITE
"""
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # 3 premières teintes catégorielles validées (daltonisme)
RED = "color:#C0392B;font-weight:600"


# ---------------------------------------------------------------- utilitaires d'affichage
def _is_p(col) -> bool:
    c = str(col)
    return c in ("p", "p_value") or c.startswith(("p (", "p_", "p "))


def translate_df(df: pd.DataFrame) -> pd.DataFrame:
    """Interface en anglais : noms de colonnes, d'index et textes des cellules traduits."""
    if os.environ.get("OPENPLS_I18N_LOG"):
        from openpls.i18n import _log

        for v in list(df.columns) + list(df.index) + list(df.columns.names) + list(df.index.names):
            for x in (v if isinstance(v, tuple) else (v,)):
                _log(x)
        for c in df.select_dtypes(include=["object", "string"]).columns:
            for x in df[c].dropna().unique():
                _log(x)
    if st.session_state.get("lang") != "en":
        return df
    df = df.rename(columns=tr, index=tr)
    df.columns.names = [tr(n) for n in df.columns.names]
    df.index.names = [tr(n) for n in df.index.names]
    obj = df.select_dtypes(include=["object", "string"]).columns
    if len(obj):
        df = df.copy()
        for c in obj:
            df[c] = df[c].map(tr)
    return df


def fmt(df, digits: int = 3):
    """Mise en forme unique : `digits` décimales ; colonnes de p-values en « < 0.001 » / 3 décimales."""
    if isinstance(df, pd.Series):
        df = df.to_frame()
    df = translate_df(df)
    cols = df.select_dtypes("number").columns
    formats = {c: (lambda v: "" if pd.isna(v) else fmt_p(v)) if _is_p(c)
               else (lambda v: "" if pd.isna(v) else f"{int(v)}") if pd.api.types.is_integer_dtype(df[c])
               else (lambda v, d=digits: "" if pd.isna(v) else num(v, d)) for c in cols}
    return df.style.format(formats, na_rep="")


def flag(df: pd.DataFrame, rules: dict, digits: int = 3):
    """Colore en rouge les valeurs qui violent un seuil : rules = {colonne: fonction -> bool (True = problème)}."""
    sty = fmt(df, digits)
    cols = set(sty.data.columns)
    for col, bad in rules.items():
        col = tr(col)
        if col in cols:
            sty = sty.map(lambda v, bad=bad: RED if pd.notna(v) and bad(v) else "", subset=[col])
    return sty


def yes_no(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == bool:
            out[c] = out[c].map({True: T("oui"), False: T("non")})
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
    """450 répondants, trois groupes ; le chemin ETA1 -> ETA2 vaut 0,6 dans A et C, 0,3 dans B."""
    parts = [simulate(150, seed=11, direct=0.15), simulate(150, seed=12, direct=0.15, eta_path=0.3),
             simulate(150, seed=13, direct=0.15)]
    d = pd.concat(parts, ignore_index=True)
    d.insert(0, "groupe", ["A"] * 150 + ["B"] * 150 + ["C"] * 150)
    return d


def stored(name: str, key):
    """Résultat d'une analyse avancée mémorisé pour la même configuration, sinon None."""
    hit = st.session_state.get("adv", {}).get(name)
    return hit[1] if hit and hit[0] == key else None


def store(name: str, key, value):
    st.session_state.setdefault("adv", {})[name] = (key, value)


DESKTOP = bool(os.environ.get("OPENPLS_DESKTOP"))  # lancé par l'application de bureau (fenêtre)


def export_dir() -> Path:
    docs = Path.home() / "Documents"
    out = (docs if docs.is_dir() else Path.home()) / "OpenPLS"
    out.mkdir(parents=True, exist_ok=True)
    return out


def open_folder(path: Path) -> None:
    import subprocess

    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def offer_file(label: str, data, filename: str, key: str, mime: str = "text/plain", container=st) -> None:
    """Navigateur : bouton de téléchargement. Application de bureau : enregistrement direct dans
    Documents/OpenPLS (les fenêtres intégrées gèrent mal les téléchargements)."""
    if not DESKTOP:
        container.download_button(label, data, filename, mime=mime, key=key, width="stretch")
        return
    if container.button(label.replace("⬇", "💾", 1), key=key, width="stretch"):
        stem, ext = os.path.splitext(filename)
        path = export_dir() / f"{stem}_{time.strftime('%Y-%m-%d_%H%M%S')}{ext}"
        path.write_bytes(data if isinstance(data, bytes) else str(data).encode("utf-8"))
        st.session_state["last_export"] = str(path)
    last = st.session_state.get("last_export")
    if last and Path(last).name.startswith(os.path.splitext(filename)[0]):
        container.success(T("Enregistré : {path}", path=last))
        if container.button(T("Ouvrir le dossier"), key=f"{key}_open", width="stretch"):
            open_folder(Path(last).parent)


def ic_label(col: str) -> str:
    """« ci_0.025 » -> « IC 2,5 % »."""
    v = float(str(col)[3:]) * 100
    return f"{T('IC')} {num(v, 1).rstrip('0').rstrip(',.')} %"


def boot_display(df: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """Tableau de bootstrap présenté en français, avec étoiles de significativité."""
    lo = next(c for c in df.columns if str(c).startswith("ci_"))
    hi = [c for c in df.columns if str(c).startswith("ci_")][-1]
    out = pd.DataFrame({
        "coefficient": df["estimate"], "sig.": df["p_value"].map(lambda p: stars(p, alpha)), "t": df["t_value"], "p": df["p_value"],
        "erreur-type": df["std_error"], "moyenne bootstrap": df["boot_mean"],
        ic_label(lo): df[lo], ic_label(hi): df[hi],
    }, index=df.index)
    return out


def run_button(label: str, key: str) -> bool:
    return st.button(f"▶  {label}", key=key, type="primary")


# ---------------------------------------------------------------- barre latérale
if DESKTOP and st.sidebar.button(T("Quitter OpenPLS"), key="quit_app", type="tertiary"):
    st.sidebar.info(T("OpenPLS se ferme…"))
    os._exit(0)  # arrête le serveur ; la fenêtre de l'application se ferme d'elle-même

st.sidebar.subheader(T("Données"))
source = st.sidebar.radio("Source", ["example", "example_hoc", "file"], key="source", label_visibility="collapsed",
                          format_func={"example": T("Données d'exemple"), "example_hoc": T("Exemple de second ordre"),
                                       "file": T("Importer un fichier")}.get)
if source == "file":
    up = st.sidebar.file_uploader(T("CSV ou Excel"), type=["csv", "txt", "xlsx", "xls"])
    if up is None:
        st.html('<div style="height:1.5rem"></div>')
        st.subheader(T("Importe tes données pour commencer"))
        st.markdown(T("Dépose un fichier **CSV ou Excel** dans la barre latérale : une colonne par indicateur, "
                      "une ligne par répondant. OpenPLS propose ensuite un modèle de départ que tu ajustes "
                      "dans l'éditeur visuel.\n\nPour découvrir l'outil sans tes données, choisis "
                      "« Données d'exemple »."))
        st.stop()
    content = up.getvalue()
    raw = read_file(content, up.name)
    # identifié par son contenu : un fichier corrigé de même nom et même taille réinitialise les résultats
    import hashlib

    data_id = f"file:{up.name}:{hashlib.sha256(content).hexdigest()[:16]}"
elif source == "example_hoc":
    raw = simulate_higher_order(400, seed=21)
    data_id = "example_hoc"
else:
    raw = example_data()
    data_id = "example"

st.sidebar.subheader(T("Estimation"))
algo = st.sidebar.selectbox(T("Algorithme"), ["PLS", "PLSc (consistent)"], key="algo",
                            help=T("PLSc corrige l'atténuation pour les construits réflectifs (modèles de facteurs communs)."))
auto_boot = st.sidebar.checkbox(T("Calculer t et p automatiquement"), value=True, key="auto_boot",
                                help=T("Lance le bootstrap juste après l'estimation : t, p, intervalles de confiance "
                                       "et étoiles de significativité apparaissent dans les tableaux et le diagramme."))
n_boot = st.sidebar.number_input(T("Échantillons bootstrap"), 100, 20000, int(load_prefs().get("n_boot", 1000)),
                                 step=500, key="n_boot")
# seuil choisi au-dessus du diagramme des résultats ; gardé hors widget pour survivre aux changements de page
alpha = st.session_state.setdefault("alpha_saved", 0.05)
with st.sidebar.expander(T("Options avancées")):
    scheme = st.selectbox(T("Schéma de pondération interne"), ["path", "factorial", "centroid"], key="scheme")
    moderation = st.selectbox(
        T("Méthode de modération"), ["two_stage", "product_indicator", "orthogonal"], key="moderation",
        format_func={"two_stage": T("Deux étapes (recommandé)"), "product_indicator": T("Produit des indicateurs"),
                     "orthogonal": T("Orthogonalisation")}.get,
        help=T("Utilisée seulement si le modèle contient un terme d'interaction `X:M`."))
    hoc_method = st.selectbox(
        T("Approche d'ordre supérieur"), ["two_stage_disjoint", "two_stage_embedded", "repeated_indicators"],
        key="hoc_method",
        format_func={"two_stage_disjoint": T("Deux étapes, disjointe (recommandé)"),
                     "two_stage_embedded": T("Deux étapes, intégrée"),
                     "repeated_indicators": T("Indicateurs répétés")}.get,
        help=T("Utilisée seulement si le modèle contient un construit d'ordre supérieur (`HOC =~ LV1 + LV2`)."))
    seed = int(st.number_input(T("Graine aléatoire"), 0, 10**6, 42, key="seed"))

# ---------------------------------------------------------------- définition du modèle
raw = raw.rename(columns=str)  # en-têtes numériques (fréquents dans Excel) -> texte, comme dans la syntaxe
numeric_cols = [c for c in raw.columns if pd.api.types.is_numeric_dtype(raw[c])]
if st.session_state.get("data_id") != data_id:
    prev_id, prev_cols = st.session_state.get("data_id"), st.session_state.get("data_cols")
    st.session_state["data_id"] = data_id
    st.session_state["data_cols"] = list(raw.columns)
    # nouvelle version d'un fichier aux mêmes colonnes (données corrigées) : on garde le modèle saisi,
    # mais tous les résultats sont effacés ; sinon, modèle par défaut
    same_layout = (prev_id or "").startswith("file:") and data_id.startswith("file:") and prev_cols == list(raw.columns)
    if same_layout and st.session_state.get("syntax_saved"):
        st.session_state["syntax"] = st.session_state["syntax_saved"]
    else:
        st.session_state["syntax"] = {"example": EXAMPLE_SYNTAX, "example_hoc": HOC_SYNTAX}.get(
            data_id, guess_syntax(numeric_cols) if data_id.startswith("file:") else EXAMPLE_SYNTAX)
        st.session_state.pop("editor_pos", None)
    for k in ("results", "boot", "adv", "boot_table"):
        st.session_state.pop(k, None)
    st.session_state["page"] = T("Modèle")  # nouvelles données : retour à la définition du modèle
elif "syntax" not in st.session_state:  # état du widget perdu (passage sans zone de texte)
    st.session_state["syntax"] = st.session_state.get("syntax_saved", EXAMPLE_SYNTAX)

# ---------------------------------------------------------------- navigation
PAGES = [T("Modèle"), T("Analyses préliminaires"), T("Résultats"), T("Significativité"), T("Analyses avancées"),
         T("Aide")]
if "_goto" in st.session_state:  # bascule automatique (ex. vers Résultats après l'estimation)
    st.session_state["page"] = st.session_state.pop("_goto")
if st.session_state.get("page") not in PAGES:  # langue changée : ancien nom d'onglet
    st.session_state.pop("page", None)
page_model, page_prelim, page_res, page_sig, page_adv, page_help = st.tabs(PAGES, key="page", on_change="rerun")

with page_model:
    with st.expander(T("Aperçu des données — {r} lignes × {c} colonnes", r=raw.shape[0], c=raw.shape[1])):
        st.dataframe(raw.head(50), width="stretch")
        st.caption(T("Colonnes : ") + ", ".join(map(str, raw.columns)))

    tab_editor, tab_syntax = st.tabs([T("Éditeur visuel"), T("Syntaxe")])
    with tab_editor:
        st.caption(T("Glisse les indicateurs sur le canevas · tire la poignée bleue d'une variable vers une autre pour "
                     "créer un chemin · clique un chemin pour ajouter un modérateur · pour un construit d'ordre "
                     "supérieur, crée une variable vide puis « + Composante » · enfin « Appliquer au modèle »."))
        # une instance d'éditeur par jeu de données : sa dernière valeur ne doit jamais être réappliquée
        # à d'autres données (elle porterait l'ancienne syntaxe)
        out = model_editor(numeric_cols, st.session_state["syntax"], st.session_state.get("editor_pos"),
                           key=f"editor:{data_id}", lang=st.session_state["lang"])
        applied = st.session_state.setdefault("editor_applied", set())
        if out and out.get("nonce") not in applied:
            applied.add(out["nonce"])
            st.session_state["editor_pos"] = {k: tuple(v) for k, v in out.get("positions", {}).items()}
            st.session_state["syntax"] = out["syntax"]

    with tab_syntax:
        left, right = st.columns([2, 3])
        with left:
            st.text_area(T("Syntaxe du modèle"), key="syntax", height=320,
                         help=T("`LATENTE =~ ind1 + ind2` (réflectif) · `LATENTE <~ ind1 + ind2` (formatif) · "
                                "`CIBLE ~ SOURCE1 + SOURCE2` (chemins) · `CIBLE ~ X + M + X:M` (modération) · "
                                "`HOC =~ LV1 + LV2` (ordre supérieur : les termes sont des variables latentes). "
                                "`#` pour les commentaires."))

    st.session_state["syntax_saved"] = st.session_state["syntax"]  # copie hors widget (survit aux passages sans lui)
    try:
        model = Model.from_syntax(st.session_state["syntax"])
        data, warns = prepare_data(raw, model)
        if not model.structural:
            warns.append(T("Aucun chemin structurel : ajoute au moins une ligne `CIBLE ~ SOURCE`."))
        ok = bool(model.structural)
        model_error = None
    except (ValueError, KeyError) as e:
        model, data, warns, ok, model_error = None, None, [], False, str(e).strip("'\"")

    fit_kwargs = dict(scheme=scheme, consistent=algo.startswith("PLSc"))
    if model is not None and model.interactions:
        fit_kwargs["moderation"] = moderation
    if model is not None and model.higher_order:
        fit_kwargs["hoc_method"] = hoc_method

    if model_error:
        st.error(model_error)
    for w in warns:
        st.warning(w)
    run = st.button("▶  " + T("Estimer le modèle"), type="primary", disabled=not ok)

    res = None
    if run and ok:
        try:
            res = fit(data, model, **fit_kwargs)
            st.session_state["results"] = (st.session_state["syntax"], fit_kwargs, res, data, data_id)
            st.session_state.pop("boot", None)
        except Exception as e:  # noqa: BLE001 - message lisible pour l'utilisateur
            st.error(T("Échec de l'estimation : {e}", e=e))

    prev = st.session_state.get("results")
    if prev and prev[0] == st.session_state["syntax"] and prev[1] == fit_kwargs and prev[4] == data_id:
        _, _, res, data, _ = prev

    # ---------------------------------------------------------------- bootstrap (t, p, IC)
    def boot_stats(r):
        parts = [effect_statistics(r), measurement_statistics(r)]
        if r.spec is not None and r.spec.interactions:
            parts.append(simple_slope_statistics(r))
        if r.spec is not None and r.spec.higher_order:
            parts.append(higher_order_statistics(r))
        return pd.concat(parts)


    def boot_key():  # le seuil n'en fait pas partie : changer de seuil ne relance pas le bootstrap
        return (st.session_state["syntax"], fit_kwargs, int(n_boot), seed)


    def current_boot():
        b = st.session_state.get("boot")
        if not (b and b[:4] == boot_key() and b[6] == data_id):
            return None
        return with_confidence_level(b[4], b[5], alpha)


    def run_bootstrap() -> None:
        bar = st.progress(0.0, text=T("Bootstrap (t et p)…"))
        try:
            import warnings as _w

            with _w.catch_warnings():
                _w.simplefilter("ignore")
                bt = bootstrap_statistics(
                    data, model, boot_stats, n_boot=int(n_boot), seed=seed, alpha=alpha, keep_draws=True,
                    progress=lambda i, n: bar.progress(i / n, text=T("Bootstrap (t et p) {i}/{n}", i=i, n=n))
                    if i % 25 == 0 or i == n else None,
                    **fit_kwargs,
                )
            draws = bt.attrs.pop("draws")
            st.session_state["boot"] = boot_key() + (bt, draws, data_id)
        except Exception as e:  # noqa: BLE001
            st.error(T("Échec du bootstrap : {e}", e=e))
        bar.empty()


    if run and ok and res is not None and auto_boot:
        run_bootstrap()
    if run and ok and res is not None:
        st.session_state["_goto"] = T("Résultats")  # on montre directement les résultats
        st.rerun()
    boot = current_boot() if res is not None else None
    label_mode = st.session_state.get("sig_view", "stars")

    with right:
        if model is not None:
            st.graphviz_chart(model_to_dot(model, res, positions=st.session_state.get("editor_pos"), boot=boot, label_mode=label_mode, alpha=alpha), width="stretch")
            if res is None:
                st.caption(T("Clique sur « Estimer le modèle » pour afficher les estimations sur le diagramme."))

with page_prelim:
    from openpls import page_prelim as _prelim

    _prelim.render(raw, model, res, numeric_cols, fmt, flag, offer_file)

with page_help:
    from openpls import page_help as _help

    _help.render()

if res is None:
    for _p in (page_res, page_sig, page_adv):
        _p.info(T("Clique sur « ▶ Estimer le modèle » dans l'onglet **Modèle** pour afficher les résultats."))
    st.stop()

# ---------------------------------------------------------------- résultats
with page_res:
    conv_res = res.measurement_result  # en deux étapes : l'itératif PLS est celui de l'étape 1
    converged = bool(res.converged and conv_res.converged)
    if res.moderation in ("product_indicator", "orthogonal") and fit_kwargs.get("consistent"):
        st.warning(T("Avec PLSc, seule la modération en deux étapes est corrigée de l'atténuation (Becker et al. "
                     "2018) ; les approches par produit d'indicateurs sous-estiment l'effet d'interaction."))
    _sv = structural_view(res)
    _r2 = "".join(f"<span>{html.escape(str(k))} {num(v)}</span>" for k, v in _sv.r_squared.items())
    _items = [
        (T("Méthode"), ("PLSc" if res.consistent else "PLS") + f" <span>{T('schéma')} {scheme}</span>"),
        (T("Observations"), f"{len(data)}"),
        (T("Convergence"), T("{n} itérations", n=conv_res.iterations) if converged else T("non atteinte"), not converged),
        ("Bootstrap", T("{n} tirages", n=boot.attrs.get('n_boot_ok', len(boot))) if boot is not None
         else T("pas encore lancé")),
        ("R²", _r2 or "—"),
    ]
    if res.moderation:
        _items.append((T("Modération"), {"two_stage": T("deux étapes"), "product_indicator": T("produit des indicateurs"),
                                         "orthogonal": T("orthogonalisation")}.get(res.moderation, res.moderation)))
    if res.hoc_method:
        _items.append((T("Ordre supérieur"), res.hoc_method.replace("_", " ")))
    st.html('<dl class="opls-summary">' + "".join(
        f'<div><dt>{it[0]}</dt><dd{" class=warn" if len(it) > 2 and it[2] else ""}>{it[1]}</dd></div>'
        for it in _items) + "</dl>")
    if not converged:
        st.error(T("L'algorithme n'a pas convergé : vérifie la spécification du modèle."))
    with st.expander(T("Diagramme estimé"), expanded=True):
        if boot is not None:
            st.session_state.setdefault("sig_view", "stars")
            st.radio(T("Significativité sur le diagramme"), ["stars", "colors"], horizontal=True, key="sig_view",
                     format_func={"stars": T("Afficher (étoiles : 1 %, 5 % et 10 %)"),
                                  "colors": T("Ne pas afficher (couleurs selon un seuil)")}.get)
            if "alpha" not in st.session_state:
                st.session_state["alpha"] = alpha
            if st.session_state["sig_view"] == "colors":
                st.radio(T("Seuil"), [0.01, 0.05, 0.10], horizontal=True, key="alpha",
                         format_func=lambda a: f"{num(a * 100, 0)} %",
                         on_change=lambda: st.session_state.update(alpha_saved=st.session_state["alpha"]),
                         help=T("Vert : significatif à ce seuil. Rouge : non significatif. Le seuil vaut aussi pour "
                                "le gras des tableaux et les intervalles de confiance."))
                alpha = st.session_state["alpha"]
        _mode = st.session_state.get("sig_view", "stars")
        st.graphviz_chart(model_to_dot(model, res, positions=st.session_state.get("editor_pos"), boot=boot, label_mode=_mode,
                                       alpha=alpha),
                          width="stretch")
        if boot is not None and _mode == "colors":
            st.caption(T("Seuil de {a} % (bootstrap, {n} tirages). Vert : significatif. Rouge pointillé : non "
                         "significatif. L'épaisseur suit la taille de l'effet.",
                         a=num(alpha * 100, 0), n=boot.attrs.get('n_boot_ok', '')))
        elif boot is not None:
            st.caption(stars_legend() + " " + T("(bootstrap, {n} tirages). Gris pointillé : non significatif même à "
                                                "10 %. L'épaisseur suit la taille de l'effet.",
                                                n=boot.attrs.get('n_boot_ok', '')))
        else:
            st.caption(T("Coefficients seuls : le bootstrap n'a pas été lancé. Il n'est utile que pour la "
                         "significativité (t, p, étoiles, intervalles de confiance) : lance-le dans l'onglet "
                         "Significativité, ou coche « Calculer t et p automatiquement » dans la barre latérale."))

meas = res.measurement_result
sres = structural_view(res)  # sans les relations HOC <-> composantes (indicateurs répétés)
q = quality_criteria(meas)
paths_tbl = pd.DataFrame(
    [{"chemin": f"{s} -> {d}", "coefficient": res.path_coefficients.loc[s, d]} for s, d in sres.model.structural]
).set_index("chemin")


def with_inference(tbl: pd.DataFrame, kind: str, keys: list[str]) -> pd.DataFrame:
    """Ajoute t, p, IC et étoiles (bootstrap) à un tableau d'estimations."""
    if boot is None:
        return tbl
    lo, hi = boot.columns[-2], boot.columns[-1]
    rows = [boot.loc[(kind, k)] if (kind, k) in boot.index else None for k in keys]
    tbl = tbl.copy()
    tbl["erreur-type"] = [r["std_error"] if r is not None else np.nan for r in rows]
    tbl["t"] = [r["t_value"] if r is not None else np.nan for r in rows]
    tbl["p"] = [r["p_value"] if r is not None else np.nan for r in rows]
    tbl[ic_label(lo)] = [r[lo] if r is not None else np.nan for r in rows]
    tbl[ic_label(hi)] = [r[hi] if r is not None else np.nan for r in rows]
    tbl["sig."] = [stars(r["p_value"], alpha) if r is not None else "" for r in rows]
    ic = T("IC") + " "
    first = [c for c in tbl.columns if c not in ("sig.", "t", "p", "erreur-type") and not str(c).startswith(ic)]
    return tbl[first + ["sig.", "t", "p", "erreur-type"] + [c for c in tbl.columns if str(c).startswith(ic)]]


paths_tbl = with_inference(paths_tbl, "direct", list(paths_tbl.index))
loadings_tbl = pd.DataFrame({"chargement": meas.outer_loadings, "poids": meas.outer_weights})
loadings_tbl = loadings_tbl[~loadings_tbl.index.get_level_values(0).isin(list(model.higher_order))]
htmt_tbl = htmt(meas)
fl_tbl = fornell_larcker(meas)
endogenous = list(sres.r_squared.index)
hoc_eval = higher_order_measurement(res) if model.higher_order else None
excel_extra: dict[str, pd.DataFrame] = {}

_sub = page_res.tabs([T("Modèle structurel"), T("Modèle de mesure"), T("Validité discriminante"), T("Scores")])
# anciens onglets -> nouvelle organisation : Significativité et Analyses avancées sont des onglets principaux
tabs = [_sub[0], _sub[1], _sub[2], page_sig, page_adv, _sub[3]]

with tabs[0]:
    st.subheader(T("Coefficients de chemin"))
    if boot is None:
        st.info(T("t, p et étoiles : coche « Calculer t et p automatiquement » dans la barre latérale, ou :"))
        if st.button("▶  " + T("Calculer t et p"), key="run_boot_paths"):
            run_bootstrap()
            st.rerun()
        st.dataframe(fmt(paths_tbl), width="stretch")
    else:
        sig_style = lambda v: "font-weight:700;color:#2E5E9E" if v not in ("", "ns") else "color:#6B7889"  # noqa: E731
        sty = fmt(paths_tbl).map(lambda v: "font-weight:700" if pd.notna(v) and v < alpha else "color:#6B7889",
                                 subset=["p"]).map(sig_style, subset=["sig."])
        st.dataframe(sty, width="stretch")
        st.caption(stars_legend(alpha) + ". " + T("En gras : p < {a}. t et p par bootstrap ({n} tirages) ; "
                                                  "intervalle de confiance percentile.",
                                                  a=num(alpha, 2), n=boot.attrs.get('n_boot_ok', '')))
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("R²")
        st.dataframe(fmt(sres.r_squared.rename("R²").to_frame()), width="stretch")
        st.subheader(T("Effets totaux"))
        st.dataframe(fmt(total_effects(res).loc[:, endogenous]), width="stretch")
    with c2:
        st.subheader(T("Taille d'effet f²"))
        try:
            f2 = f_squared(res, data, **fit_kwargs)
            st.dataframe(fmt(f2), width="stretch")
            st.caption(T("Repères (Cohen) : 0,02 faible · 0,15 moyen · 0,35 fort. "
                         "Pour une interaction : 0,005 faible · 0,01 moyen · 0,025 fort (Kenny 2018)."))
        except Exception as e:  # noqa: BLE001
            st.info(T("f² non calculable : {e}", e=e))
        ind = specific_indirect_effects(res)
        if len(ind):
            st.subheader(T("Effets indirects spécifiques"))
            st.dataframe(fmt(ind.rename("effet").to_frame()), width="stretch")

    if model.interactions:
        st.subheader(T("Modération : pentes simples"))
        for a, b, d in model.interactions:
            ss = simple_slopes(res, a, b, d)
            c1, c2 = st.columns([2, 3])
            with c1:
                st.markdown(f"**{a} × {b} → {d}** (interaction = {res.path_coefficients.loc[f'{a}:{b}', d]:.3f})")
                st.dataframe(fmt(ss), width="stretch")
                st.caption(T("Pente de {a} sur {d} quand {b} vaut -1, 0 ou +1 écart-type.", a=a, b=b, d=d))
            with c2:
                lines = pd.DataFrame([{"x": xv, "y": row[f"{d} si {a}={'-1' if xv < 0 else '+1'}"],
                                       "niveau": f"{b} = {lvl:+.0f} {T('ET')}" if lvl else f"{b} = {T('moyenne')}"}
                                      for lvl, row in ss.iterrows() for xv in (-1, 1)])
                ch = (alt.Chart(lines).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=64, filled=True))
                      .encode(x=alt.X("x:Q", title=T("{a} (écarts-types)", a=a), scale=alt.Scale(domain=[-1.2, 1.2])),
                              y=alt.Y("y:Q", title=T("{d} prédit (écarts-types)", d=d)),
                              color=alt.Color("niveau:N", title=b, sort=list(dict.fromkeys(lines["niveau"])),
                                              scale=alt.Scale(range=SERIES)),
                              tooltip=["niveau", alt.Tooltip("x:Q", title=a), alt.Tooltip("y:Q", format=".3f", title=d)])
                      .properties(height=260))
                st.altair_chart(ch, width="stretch")

with tabs[1]:
    if res.stage1 is not None and res.moderation:
        st.info(T("Modération en deux étapes : le modèle de mesure est évalué sur l'estimation de l'étape 1 "
                  "(modèle sans interaction)."))
    if res.stage1 is not None and res.hoc_method:
        st.info(T("Ordre supérieur en deux étapes : les construits d'ordre 1 (dont les composantes) sont évalués "
                  "sur l'étape 1 ; les construits d'ordre supérieur, dans le tableau dédié plus bas."))
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(T("Chargements et poids externes"))
        if boot is not None:
            keys_l = [f"{lv} -> {ind}" for lv, ind in loadings_tbl.index]
            keys_w = [f"{ind} -> {lv}" for lv, ind in loadings_tbl.index]
            inf_l = with_inference(pd.DataFrame(index=loadings_tbl.index), "outer_loading", keys_l)
            inf_w = with_inference(pd.DataFrame(index=loadings_tbl.index), "outer_weight", keys_w)
            loadings_tbl = loadings_tbl.assign(**{"t (chargement)": inf_l["t"], "p (chargement)": inf_l["p"],
                                                  "sig. chargement": inf_l["sig."], "t (poids)": inf_w["t"],
                                                  "p (poids)": inf_w["p"], "sig. poids": inf_w["sig."]})
        st.dataframe(flag(loadings_tbl, {"chargement": lambda v: v < 0.708}), width="stretch", height=420)
        st.caption(T("Rouge : chargement < 0,708 (Hair et al.). Pour un bloc formatif, regarde plutôt les poids."))
    with c2:
        st.subheader(T("Fiabilité et validité convergente"))
        st.dataframe(flag(q, {"cronbach_alpha": lambda v: v < 0.7, "rho_A": lambda v: v < 0.7,
                              "rho_c": lambda v: v < 0.7 or v > 0.95, "AVE": lambda v: v < 0.5}),
                     width="stretch")
        st.caption(T("Seuils : α, ρ_A, ρ_c ≥ 0,70 (ρ_c ≤ 0,95) · AVE ≥ 0,50. "
                     "Ces critères ne s'appliquent qu'aux construits réflectifs."))
    if hoc_eval is not None:
        st.subheader(T("Construits d'ordre supérieur"))
        c1, c2 = st.columns([3, 2])
        with c1:
            st.dataframe(flag(hoc_eval["components"], {"chargement": lambda v: v < 0.708, "VIF": lambda v: v > 5}),
                         width="stretch")
            st.caption(T("Les composantes jouent le rôle d'indicateurs du construit d'ordre supérieur : chargements "
                         "(réflectif) ou poids et VIF (formatif). Rouge : chargement < 0,708 ou VIF > 5."))
        with c2:
            st.dataframe(flag(hoc_eval["quality"], {"cronbach_alpha": lambda v: v < 0.7, "rho_c": lambda v: v < 0.7,
                                                    "AVE": lambda v: v < 0.5, "VIF max": lambda v: v > 5}),
                         width="stretch")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("HTMT")
        st.dataframe(fmt(htmt_tbl).map(lambda v: RED if pd.notna(v) and v > 0.85 else ""), width="stretch")
        st.caption(T("Rouge : HTMT > 0,85 (seuil prudent ; 0,90 pour des construits conceptuellement proches)."))
    with c2:
        st.subheader(T("Critère de Fornell-Larcker"))
        st.dataframe(fmt(fl_tbl), width="stretch")
        st.caption(T("Diagonale = √AVE ; elle doit dépasser les corrélations de sa ligne et de sa colonne."))

with tabs[3]:
    st.write(T("Bootstrap à **{n}** échantillons, IC percentile à {c} %. "
               "Peut prendre de quelques secondes à quelques minutes.", n=int(n_boot), c=int(round((1 - alpha) * 100))))
    st.caption(T("Le seuil (1 %, 5 % ou 10 %) se règle au-dessus du diagramme, dans l'onglet Résultats."))

    if st.button("▶  " + T("Lancer le bootstrap"), key="run_boot"):
        run_bootstrap()
        st.rerun()

    if boot is not None:
        if boot.attrs.get("failure_rate", 0) > 0.05:
            st.error(T("Inférence NON fiable — ") + " · ".join(boot.attrs["warnings"]) +
                     T(". Essaie le PLS classique (au lieu de PLSc), un échantillon plus grand ou un modèle de mesure "
                       "plus fiable."))
        elif boot.attrs.get("warnings"):
            st.warning(" · ".join(boot.attrs["warnings"]))
        st.caption(T("{n} tirages utilisés.", n=boot.attrs.get('n_boot_ok', len(boot))))
        lo, hi = boot.columns[-2], boot.columns[-1]
        sig = (boot[lo] > 0) | (boot[hi] < 0)
        boot_view = boot.assign(significatif=sig.map({True: T("oui"), False: T("non")}))
        labels = {"direct": T("Effets directs (coefficients de chemin)"),
                  "specific_indirect": T("Effets indirects spécifiques"),
                  "total_indirect": T("Effets indirects totaux"), "total": T("Effets totaux"),
                  "simple_slope": T("Pentes simples (modération)"),
                  "outer_loading": T("Chargements externes"), "outer_weight": T("Poids externes"),
                  "hoc_loading": T("Chargements des composantes (ordre supérieur)"),
                  "hoc_weight": T("Poids des composantes (ordre supérieur)")}
        for kind, title in labels.items():
            if kind in boot_view.index.get_level_values(0):
                st.subheader(title)
                st.dataframe(fmt(boot_display(boot_view.loc[kind], alpha)), width="stretch")

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
            rows.append({"chemin": name, "indirect": i_est, "indirect signif.": T("oui") if i_sig else T("non"),
                         "direct": num(d_est) if has_d else "—",
                         "direct signif.": (T("oui") if d_sig else T("non")) if has_d else T("non estimé"),
                         "type de médiation": kind_lbl})
        if rows:
            st.subheader(T("Analyse de médiation"))
            st.dataframe(fmt(pd.DataFrame(rows).set_index("chemin")), width="stretch")
            st.caption(T("Typologie de Zhao, Lynch & Chen (2010). Significativité = l'IC bootstrap exclut 0. "
                         "Pour tester une médiation partielle, le chemin direct doit figurer dans le modèle."))
        st.session_state["boot_table"] = boot_view
    else:
        st.session_state.pop("boot_table", None)

# ---------------------------------------------------------------- analyses avancées
ADV = [T("Prédiction (PLSpredict, CVPAT)"), T("Multigroupe (MGA, MICOM)"), T("Importance-performance (IPMA)"),
       T("Conditions nécessaires (NCA)"), T("Endogénéité (copules)"), "CB-SEM / CFA", T("Segmentation (FIMIX-PLS)")]
base_key = (data_id, st.session_state["syntax"], tuple(sorted(fit_kwargs.items())), seed, len(data))
plain = not model.interactions and not model.higher_order
plain_why = T("avec interaction") if model.interactions else T("d'ordre supérieur")

with tabs[4]:
    if st.session_state.get("adv_choice") not in ADV:  # langue changée
        st.session_state.pop("adv_choice", None)
    choice = st.radio(T("Analyse"), ADV, horizontal=True, key="adv_choice", label_visibility="collapsed")
    st.divider()

    if choice == ADV[0]:
        st.markdown(T("Validation croisée à k plis répétée : le modèle prédit-il de **nouvelles** observations "
                      "mieux qu'une simple moyenne (Q²_predict > 0) et qu'une régression linéaire (LM) ?"))
        if not plain:
            st.warning(T("PLSpredict n'est pas disponible pour les modèles {why}.", why=plain_why))
        else:
            c = st.columns(3)
            k = c[0].number_input(T("Plis (k)"), 2, 50, 10, key="pp_k")
            reps = c[1].number_input(T("Répétitions"), 1, 100, 10, key="pp_r")
            approach = c[2].selectbox(T("Approche"), ["EA", "DA"], key="pp_a",
                                      help=T("EA : prédiction à partir des seules exogènes (recommandé). "
                                             "DA : à partir des antécédents directs."))
            key = base_key + ("pred", k, reps, approach)
            if run_button(T("Lancer PLSpredict et CVPAT"), "run_pred"):
                from openpls.predict import pls_predict, cvpat

                with st.spinner(T("Validation croisée…")):
                    try:
                        store("pred", key, (pls_predict(data, model, k=int(k), repetitions=int(reps), seed=seed,
                                                        approach=approach, **fit_kwargs),
                                            cvpat(data, model, k=int(k), repetitions=int(reps), seed=seed,
                                                  approach=approach, **fit_kwargs)))
                    except Exception as e:  # noqa: BLE001
                        st.error(T("Échec : {e}", e=e))
            out = stored("pred", key)
            if out:
                pp, cv = out
                st.subheader(T("Indicateurs endogènes"))
                st.dataframe(flag(yes_no(pp["indicators"]), {"Q2_predict": lambda v: v <= 0}), width="stretch")
                n_better = int(pp["indicators"]["PLS < LM (RMSE)"].sum())
                n_tot = len(pp["indicators"])
                verdict = (T("élevée") if n_better == n_tot else T("moyenne") if n_better > n_tot / 2
                           else T("faible") if n_better > 0 else T("nulle"))
                st.caption(T("PLS bat LM sur {k}/{n} indicateurs → puissance prédictive **{v}** "
                             "(Shmueli et al. 2019). Rouge : Q²_predict ≤ 0.", k=n_better, n=n_tot, v=verdict))
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader(T("Latentes endogènes"))
                    st.dataframe(fmt(pp["latents"]), width="stretch")
                with c2:
                    st.subheader("CVPAT")
                    st.dataframe(fmt(yes_no(cv)), width="stretch")
                    st.caption(T("Différence de perte < 0 et p < 0,05 : PLS prédit significativement mieux que "
                                 "le benchmark (IA = moyenne des indicateurs, LM = régression linéaire)."))
                excel_extra.update({"PLSpredict": pp["indicators"], "PLSpredict latentes": pp["latents"], "CVPAT": cv})

    elif choice == ADV[1]:
        st.markdown(T("Compare les coefficients de chemin de **plusieurs groupes**, après avoir vérifié "
                      "l'invariance de mesure (MICOM). Avec plus de deux groupes : test omnibus, puis comparaisons "
                      "deux à deux corrigées par Holm."))
        cand = [c for c in raw.columns if c not in model.indicators and raw[c].nunique(dropna=True) <= 20]
        if not cand:
            st.info(T("Aucune colonne de groupe disponible : il faut une colonne (hors indicateurs) avec peu de "
                      "modalités, par exemple « sexe » ou « pays »."))
        else:
            c = st.columns(4)
            gcol = c[0].selectbox(T("Variable de groupe"), cand, key="mga_col")
            levels = list(pd.unique(raw[gcol].dropna()))
            pick = c[1].multiselect(T("Groupes à comparer (au moins 2)"), levels, default=levels, key="mga_lv")
            n_perm = c[2].number_input("Permutations", 100, 10000, 1000 if len(pick) <= 2 else 500, step=100,
                                       key="mga_np")
            n_bt = c[3].number_input(T("Bootstrap par groupe"), 100, 10000, 500 if len(pick) <= 2 else 200, step=100,
                                     key="mga_nb")
            key = base_key + ("mga", gcol, tuple(map(str, pick)), n_perm, n_bt)
            if len(pick) < 2:
                st.info(T("Choisis au moins deux groupes."))
            elif run_button(T("Lancer MGA et MICOM"), "run_mga"):
                from openpls.mga import mga, mga_multi

                dg, _ = prepare_data(raw, model, keep=[gcol])
                dg = dg[dg[gcol].isin(pick)].reset_index(drop=True)
                bar = st.progress(0.0, text=T("Permutations et bootstrap…"))
                tick = lambda i, n: bar.progress(min(i / n, 1.0)) if i % 20 == 0 else None  # noqa: E731
                try:
                    fn = mga if len(pick) == 2 else mga_multi
                    store("mga", key, fn(dg[model.indicators], model, dg[gcol], n_perm=int(n_perm), n_boot=int(n_bt),
                                         seed=seed, progress=tick, **fit_kwargs))
                except Exception as e:  # noqa: BLE001
                    st.error(T("Échec : {e}", e=e))
                bar.empty()
            out = stored("mga", key)
            if out:
                st.write(T("Effectifs : ") + " · ".join(f"**{g}** n = {n}" for g, n in out["groups"].items()))
                for msg in out.get("warnings", []):
                    st.warning(tr(msg))
                st.subheader(T("MICOM — invariance de mesure"))
                if out["invariant"]:
                    st.success(tr(out["verdict"]).capitalize())
                else:
                    st.warning(tr(out["verdict"]).capitalize())
                st.caption(T("Chaque construit est testé à 5 % : avec plusieurs construits (et plusieurs paires), un "
                             "rejet isolé survient souvent par hasard. Un rejet sur un construit dont la relation "
                             "structurelle diffère entre groupes peut aussi refléter cette différence (poids PLS)."))
                micoms = out["micom"] if "micom" in out else {
                    "": {"step2": out["micom_step2"], "step3": out["micom_step3"], "verdict": out["verdict"],
                         "invariant": out["invariant"]}}
                for pair, mi in micoms.items():
                    box = st.expander(f"MICOM — {pair} : {tr(mi['verdict'])}") if pair else st.container()
                    with box:
                        c1, c2 = st.columns([2, 3])
                        with c1:
                            st.markdown(T("**Étape 2 — invariance compositionnelle**"))
                            st.dataframe(flag(yes_no(mi["step2"]),
                                              {"invariance compositionnelle": lambda v: v == T("non")},
                                              digits=4), width="stretch")
                        with c2:
                            st.markdown(T("**Étape 3 — égalité des moyennes et des variances**"))
                            st.dataframe(fmt(yes_no(mi["step3"])), width="stretch")
                if "omnibus" in out:
                    st.subheader(T("Coefficients par groupe"))
                    st.dataframe(fmt(out["estimates"]), width="stretch")
                    st.subheader(T("Test omnibus (tous les groupes)"))
                    st.dataframe(flag(yes_no(out["omnibus"]), {"p_value": lambda v: v < 0.05}), width="stretch")
                    st.caption(T("H0 : le chemin est identique dans tous les groupes (test de permutation sur "
                                 "Σ n_g (β_g − β̄)²). N'interprète les paires que pour les chemins rejetés ici."))
                    st.subheader(T("Comparaisons deux à deux"))
                    st.dataframe(flag(yes_no(out["pairwise"]), {"p_perm_Holm": lambda v: v < 0.05}), width="stretch")
                    st.caption(T("p_perm_Holm : p-value de permutation corrigée par Holm sur l'ensemble des paires, "
                                 "pour chaque chemin. Henseler et Welch : non corrigées, à titre indicatif."))
                    excel_extra.update({"MGA groupes": out["estimates"], "MGA omnibus": out["omnibus"],
                                        "MGA paires": out["pairwise"]})
                else:
                    st.subheader(T("Comparaison des chemins"))
                    st.dataframe(flag(yes_no(out["comparison"]),
                                      {"p_permutation": lambda v: v < 0.05, "p_henseler": lambda v: v < 0.05,
                                       "p_welch": lambda v: v < 0.05}), width="stretch")
                    st.caption(T("En rouge : p < 0,05 (différence significative). Test de permutation recommandé "
                                 "(Chin & Dibbern 2010) ; PLS-MGA de Henseler (2009) et Welch-Satterthwaite en "
                                 "complément."))
                    excel_extra.update({"MGA": out["comparison"], "MICOM etape 2": out["micom_step2"],
                                        "MICOM etape 3": out["micom_step3"]})

    elif choice == ADV[2]:
        st.markdown(T("Quels antécédents ont une forte **importance** (effet total non standardisé) mais une faible "
                      "**performance** (score moyen sur 0-100) ? Ce sont les leviers prioritaires."))
        if not plain:
            st.warning(T("IPMA non disponible pour les modèles {why}.", why=plain_why))
        else:
            c = st.columns(4)
            target = c[0].selectbox(T("Construit cible"), endogenous, index=len(endogenous) - 1, key="ipma_t")
            theo = c[1].checkbox(T("Bornes théoriques de l'échelle"), key="ipma_theo",
                                 help=T("Sinon, min et max observés de chaque indicateur."))
            lo_s = c[2].number_input("Minimum", value=1.0, key="ipma_lo", disabled=not theo)
            hi_s = c[3].number_input("Maximum", value=7.0, key="ipma_hi", disabled=not theo)
            from openpls.ipma import ipma

            try:
                out = ipma(res, data, target, scale=(lo_s, hi_s) if theo else None)
            except Exception as e:  # noqa: BLE001
                out = None
                st.error(tr(str(e)))
            if out:
                lat = out["latents"].reset_index()
                ch = (alt.Chart(lat).mark_circle(size=140, color=SERIES[0], opacity=0.9)
                      .encode(x=alt.X("importance:Q", title=T("Importance (effet total non standardisé)"),
                                      scale=alt.Scale(domain=[min(0, lat["importance"].min()),
                                                              lat["importance"].max() * 1.25])),
                              y=alt.Y("performance:Q", title=T("Performance (0-100)"),
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
                    st.altair_chart((ch + txt + rx + ry).properties(height=340, title=T("Carte IPMA — {t}", t=target)),
                                    width="stretch")
                    st.caption(T("Lignes pointillées : moyennes. En bas à droite : forte importance, faible "
                                 "performance → priorités d'action."))
                with c2:
                    st.metric(T("Performance de {t}", t=target), f"{num(out['target_performance'], 1)} / 100")
                    st.dataframe(fmt(out["latents"]), width="stretch")
                st.subheader(T("Niveau indicateur"))
                st.dataframe(fmt(out["indicators"]), width="stretch")
                excel_extra.update({"IPMA": out["latents"], "IPMA indicateurs": out["indicators"]})

    elif choice == ADV[3]:
        st.markdown(T("Un antécédent est-il une **condition nécessaire** de la cible (pas de niveau élevé de la "
                      "cible sans un niveau suffisant de l'antécédent) ? Plafond CE-FDH, test de permutation."))
        c = st.columns(3)
        target = c[0].selectbox(T("Construit cible"), endogenous, key="nca_t")
        n_perm = c[1].number_input("Permutations", 100, 10000, 1000, step=500, key="nca_np")
        key = base_key + ("nca", target, n_perm)
        if run_button(T("Lancer la NCA"), "run_nca"):
            from openpls.nca import nca

            with st.spinner(T("Permutations…")):
                try:
                    store("nca", key, nca(res, target, n_perm=int(n_perm), seed=seed))
                except Exception as e:  # noqa: BLE001
                    st.error(T("Échec : {e}", e=e))
        out = stored("nca", key)
        if out:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.subheader(T("Tailles d'effet"))
                st.dataframe(fmt(yes_no(out["effects"])), width="stretch")
                st.caption(T("d : 0-0,1 faible · 0,1-0,3 moyen · 0,3-0,5 fort · ≥ 0,5 très fort (Dul 2016)."))
            with c2:
                st.subheader(T("Tableau des goulots"))
                st.dataframe(fmt(out["bottleneck"], 1), width="stretch")
                st.caption(T("Niveau minimal de chaque antécédent (% de son étendue) requis pour atteindre chaque "
                             "niveau de {t}. Vide = non nécessaire à ce niveau.", t=target))
            lv_pick = st.selectbox(T("Nuage de points"), list(out["effects"].index), key="nca_plot")
            x, y = res.scores[lv_pick].to_numpy(), res.scores[target].to_numpy()
            order = np.argsort(x)
            ceil = np.maximum.accumulate(y[order])
            step = pd.DataFrame({"x": np.append(x[order], x.max()), "y": np.append(ceil, ceil[-1])})
            pts = alt.Chart(pd.DataFrame({"x": x, "y": y})).mark_circle(size=40, opacity=0.5, color=SERIES[0]).encode(
                x=alt.X("x:Q", title=f"{lv_pick} (score)"), y=alt.Y("y:Q", title=f"{target} (score)"),
                tooltip=[alt.Tooltip("x:Q", format=".2f", title=lv_pick), alt.Tooltip("y:Q", format=".2f", title=target)])
            line = alt.Chart(step).mark_line(interpolate="step-after", color=SERIES[1], strokeWidth=2).encode(x="x:Q", y="y:Q")
            st.altair_chart((pts + line).properties(height=320), width="stretch")
            st.caption(T("Ligne orange : plafond CE-FDH. La zone vide au-dessus-gauche mesure la contrainte de "
                         "nécessité."))
            excel_extra.update({"NCA": out["effects"], "NCA goulots": out["bottleneck"]})

    elif choice == ADV[4]:
        st.markdown(T("Un antécédent est-il corrélé au terme d'erreur (endogénéité) ? Ajout de termes de **copule "
                      "gaussienne** (Park & Gupta 2012) ; un terme significatif signale un problème."))
        c = st.columns(3)
        target = c[0].selectbox(T("Construit cible"), endogenous, key="endo_t")
        nb = c[1].number_input("Bootstrap", 100, 10000, 1000, step=500, key="endo_nb")
        key = base_key + ("endo", target, nb)
        if run_button(T("Lancer le test"), "run_endo"):
            from openpls.endogeneity import gaussian_copula

            with st.spinner("Bootstrap…"):
                try:
                    store("endo", key, gaussian_copula(res, target, n_boot=int(nb), seed=seed))
                except Exception as e:  # noqa: BLE001
                    st.error(T("Échec : {e}", e=e))
        out = stored("endo", key)
        if out:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.subheader(T("Non-normalité (Shapiro-Wilk)"))
                st.dataframe(flag(yes_no(out["normality"]), {"non normal (p<0,05)": lambda v: v == T("non")}),
                             width="stretch")
                st.caption(T("Rouge : distribution normale → la copule n'est pas identifiée pour ce régresseur."))
            with c2:
                st.subheader(T("Synthèse"))
                summ = out["summary"].set_index(["modèle", "régresseur"])
                st.dataframe(fmt(summ).map(lambda v: RED if v == tr("endogénéité") else
                                           "color:#6b7280;font-style:italic" if v not in (tr("endogénéité"),
                                                                                        tr("pas d'endogénéité"))
                                           else "", subset=[tr("conclusion")]), width="stretch")
                st.caption(T("La copule n'est identifiée que si le régresseur est non normal : sinon la conclusion "
                             "est « non interprétable », quelle que soit la p-value."))
            with st.expander(T("Détail de chaque modèle")):
                st.dataframe(fmt(out["models"]), width="stretch")
            excel_extra.update({"Endogeneite": out["summary"]})

    elif choice == ADV[5]:
        st.markdown(T("Estimation par **maximum de vraisemblance** (modèle de facteurs communs), avec indices "
                      "d'ajustement globaux. La CFA corrèle toutes les latentes sans chemins structurels."))
        kind = st.radio("Type", ["sem", "cfa"], horizontal=True, key="cb_kind",
                        format_func={"sem": T("SEM complet"), "cfa": T("CFA (analyse factorielle confirmatoire)")}.get)
        from openpls.cbsem import fit_cbsem

        try:
            cb = fit_cbsem(data, model, cfa=kind == "cfa")
        except Exception as e:  # noqa: BLE001
            cb = None
            st.error(tr(str(e)))
        if cb is not None:
            if not cb.converged:
                st.warning(T("L'optimisation n'a pas pleinement convergé : interprète avec prudence."))
            fi = cb.fit_indices
            m = st.columns(5)
            m[0].metric(T("χ² (ddl)"), f"{num(fi['chi2'], 1)} ({int(fi['ddl'])})", help=f"p = {num(fi['p_value'])}")
            m[1].metric("CFI", num(fi["CFI"]), help=T("≥ 0,95 bon (Hu & Bentler 1999)"))
            m[2].metric("TLI", num(fi["TLI"]), help=T("≥ 0,95 bon"))
            m[3].metric("RMSEA", num(fi["RMSEA"]), help=T("≤ 0,06 bon · IC 90 % [{lo} ; {hi}]",
                                                          lo=num(fi['RMSEA IC90 bas']), hi=num(fi['RMSEA IC90 haut'])))
            m[4].metric("SRMR", num(fi["SRMR"]), help=T("≤ 0,08 bon"))
            bad = [n for n, v, t in (("CFI", fi["CFI"], fi["CFI"] < 0.95), ("TLI", fi["TLI"], fi["TLI"] < 0.95),
                                     ("RMSEA", fi["RMSEA"], fi["RMSEA"] > 0.06), ("SRMR", fi["SRMR"], fi["SRMR"] > 0.08)) if t]
            if bad:
                st.warning(T("Ajustement insuffisant selon : {b} (seuils de Hu & Bentler 1999).", b=", ".join(bad)))
            else:
                st.success(T("Tous les indices respectent les seuils de Hu & Bentler (1999)."))
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(T("Chargements standardisés"))
                st.dataframe(flag(cb.loadings.rename("chargement").to_frame(), {"chargement": lambda v: v < 0.708}),
                             width="stretch", height=380)
            with c2:
                if kind != "cfa":
                    st.subheader(T("Chemins standardisés"))
                    st.dataframe(fmt(pd.DataFrame([{"chemin": f"{s} -> {d}", "coefficient": cb.path_coefficients.loc[s, d]}
                                                   for s, d in model.structural]).set_index("chemin")), width="stretch")
                    st.subheader("R²")
                    st.dataframe(fmt(cb.r_squared.rename("R²")), width="stretch")
                if len(cb.higher_order_loadings):
                    st.subheader(T("Chargements de second ordre"))
                    st.dataframe(flag(cb.higher_order_loadings.rename("chargement").to_frame(),
                                      {"chargement": lambda v: v < 0.708}), width="stretch")
                st.subheader(T("Corrélations entre latentes"))
                st.dataframe(fmt(cb.latent_correlations), width="stretch")
            with st.expander(T("Tous les paramètres (estimations non standardisées, erreurs-types, p-values)")):
                st.dataframe(fmt(cb.estimates, 4), width="stretch")
            excel_extra.update({"CB-SEM ajustement": fi.to_frame("valeur"), "CB-SEM parametres": cb.estimates})

    elif choice == ADV[6]:
        st.markdown(T("Y a-t-il des **segments cachés** de répondants avec des relations structurelles "
                      "différentes ? FIMIX-PLS estime un mélange de régressions sur les scores des latentes."))
        if model.interactions:
            st.warning(T("FIMIX-PLS n'est pas disponible pour les modèles avec interaction."))
        else:
            c = st.columns(3)
            smax = c[0].slider(T("Nombre maximal de segments"), 2, 8, 4, key="fx_s")
            starts = c[1].number_input(T("Départs aléatoires"), 1, 100, 10, key="fx_st")
            key = base_key + ("fimix", smax, starts)
            if run_button(T("Lancer FIMIX-PLS"), "run_fimix"):
                from openpls.fimix import fimix

                with st.spinner(T("Algorithme EM…")):
                    try:
                        store("fimix", key, fimix(res, segments=range(1, smax + 1), starts=int(starts), seed=seed))
                    except Exception as e:  # noqa: BLE001
                        st.error(T("Échec : {e}", e=e))
            out = stored("fimix", key)
            if out:
                crit = out["criteria"]
                st.subheader(T("Critères de choix du nombre de segments"))
                sty = fmt(crit)
                for col in ("AIC", "AIC3", "AIC4", "BIC", "CAIC"):
                    best = crit[col].idxmin()
                    sty = sty.map(lambda v, best_v=crit.loc[best, col]: "font-weight:700;background:#DCE8F7"
                                  if v == best_v else "", subset=[tr(col)])
                st.dataframe(sty, width="stretch")
                st.caption(T("En surligné : minimum de chaque critère. Retiens S quand AIC3 et CAIC s'accordent "
                             "(Sarstedt et al. 2011) ; EN > 0,5 indique des segments bien séparés. Un segment très "
                             "petit (< 5 %) est rarement interprétable."))
                pick = st.selectbox(T("Solution à afficher"), list(out["solutions"]),
                                    index=int(crit["CAIC"].idxmin()) - 1, key="fx_pick")
                sol = out["solutions"][pick]
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(T("**Taille des segments**"))
                    st.dataframe(fmt(sol["sizes"]), width="stretch")
                    st.markdown(T("**R² par segment**"))
                    st.dataframe(fmt(sol["r_squared"]), width="stretch")
                with c2:
                    st.markdown(T("**Coefficients de chemin par segment**"))
                    st.dataframe(fmt(sol["paths"]), width="stretch")
                    offer_file("⬇  " + T("Appartenance aux segments (CSV)"),
                               sol["posterior"].assign(segment=sol["membership"]).to_csv(index_label="observation"),
                               "segments_fimix.csv", key="fx_dl", mime="text/csv")
                excel_extra.update({"FIMIX criteres": crit, "FIMIX chemins": sol["paths"]})

with tabs[5]:
    st.subheader(T("Scores des variables latentes (standardisés)"))
    st.dataframe(fmt(res.scores), width="stretch", height=400)

# ---------------------------------------------------------------- export
sheets = {
    "Chemins": paths_tbl, "R2": sres.r_squared.rename("R2").to_frame(), "Effets totaux": total_effects(res),
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
    elif name == "mga" and "omnibus" in v:
        excel_extra.setdefault("MGA omnibus", v["omnibus"]); excel_extra.setdefault("MGA paires", v["pairwise"])
    elif name == "mga":
        excel_extra.setdefault("MGA", v["comparison"]); excel_extra.setdefault("MICOM etape 2", v["micom_step2"])
        excel_extra.setdefault("MICOM etape 3", v["micom_step3"])
    elif name == "nca":
        excel_extra.setdefault("NCA", v["effects"]); excel_extra.setdefault("NCA goulots", v["bottleneck"])
    elif name == "endo":
        excel_extra.setdefault("Endogeneite", v["summary"])
    elif name == "fimix":
        excel_extra.setdefault("FIMIX criteres", v["criteria"])
if hoc_eval is not None:
    sheets["Ordre superieur"] = hoc_eval["components"]
    sheets["Ordre sup qualite"] = hoc_eval["quality"]
sheets.update(excel_extra)
if st.session_state.get("lang") == "en":  # feuilles et colonnes de l'export dans la langue de l'interface
    sheets = {tr(k): translate_df(v.to_frame() if isinstance(v, pd.Series) else v) for k, v in sheets.items()}
st.sidebar.subheader(T("Exporter"))
offer_file("⬇  " + T("Résultats (Excel)"), to_excel(sheets), T("openpls_resultats.xlsx"), key="dl_xlsx",
           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", container=st.sidebar)
offer_file("⬇  " + T("Syntaxe du modèle"), st.session_state["syntax"], T("modele.txt"), key="dl_syntax",
           container=st.sidebar)
