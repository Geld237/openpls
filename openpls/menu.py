"""Menu de la barre du haut : À propos d'OpenPLS, Rechercher des mises à jour, Paramètres."""
from __future__ import annotations

import json
import platform
import re
import urllib.request

import streamlit as st

from . import __version__
from .i18n import T
from .settings import load_prefs, save_pref, separator_for

REPO = "Geld237/openpls"
RELEASES = f"https://github.com/{REPO}/releases"


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def latest_release(timeout: float = 6.0) -> dict:
    """Dernière version publiée sur GitHub : {"version", "url", "date"}. Lève une exception hors ligne."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "OpenPLS"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - URL fixe en https
        data = json.loads(r.read().decode("utf-8"))
    return {"version": data["tag_name"].lstrip("v"), "url": data.get("html_url", RELEASES),
            "date": (data.get("published_at") or "")[:10]}


def update_status(current: str, latest: str) -> str:
    return "newer" if _vtuple(latest) > _vtuple(current) else "current"


def about() -> None:
    import numpy
    import pandas
    import scipy

    st.markdown(T("**Version {v}**  \nModélisation par équations structurelles (PLS-SEM, PLSc, CB-SEM), libre et "
                  "open source.", v=__version__))
    st.markdown(T("Les données restent sur ton ordinateur : OpenPLS ne les envoie nulle part. Seule la recherche "
                  "de mises à jour contacte GitHub, et seulement quand tu la demandes."))
    st.markdown(T("**Licence** : MIT. Tu peux utiliser, modifier et redistribuer OpenPLS librement, y compris "
                  "pour des travaux publiés."))
    st.markdown(T("**Citer OpenPLS** : OpenPLS contributors ({y}). *OpenPLS* (version {v}) [logiciel]. "
                  "https://github.com/{r}", y=2026, v=__version__, r=REPO))
    st.link_button(T("Code source et documentation"), f"https://github.com/{REPO}")
    with st.expander(T("Composants")):
        st.caption(f"Python {platform.python_version()} · NumPy {numpy.__version__} · pandas {pandas.__version__} · "
                   f"SciPy {scipy.__version__} · Streamlit {st.__version__} · {platform.system()} {platform.release()}")


def check_updates() -> None:
    with st.spinner(T("Connexion à GitHub…")):
        try:
            info = latest_release()
        except Exception:  # noqa: BLE001 - hors ligne, proxy, limite de l'API
            st.warning(T("Impossible de joindre GitHub. Vérifie ta connexion, ou consulte la page des versions."))
            st.link_button(T("Page des versions"), RELEASES)
            return
    if update_status(__version__, info["version"]) == "newer":
        st.info(T("Une nouvelle version est disponible : **{new}** (publiée le {d}). Tu utilises la {cur}.",
                  new=info["version"], d=info["date"], cur=__version__))
        st.link_button(T("Télécharger la version {v}", v=info["version"]), info["url"], type="primary")
        st.caption(T("Sous Windows, lance le nouvel installateur : il remplace l'ancienne version et garde tes "
                     "réglages."))
    else:
        st.success(T("OpenPLS {v} est à jour.", v=__version__))


# widgets dont le libellé change avec la langue : Streamlit les recrée, on reporte leur valeur
CARRY = ("source", "algo", "auto_boot", "n_boot", "scheme", "moderation", "hoc_method", "seed", "sig_view",
         "cb_kind", "corr_m", "pp_k", "pp_r", "pp_a", "mga_col", "mga_np", "mga_nb", "ipma_t", "nca_t", "endo_t",
         "fx_s", "fx_st", "norm_ind", "fig_lv", "n_beta", "n_alpha", "missing", "boot_ci")


def _apply_language():
    st.session_state["_carry"] = {k: st.session_state[k] for k in CARRY if k in st.session_state}
    lang = st.session_state["set_lang"]
    st.session_state["lang"] = lang
    save_pref("language", lang)
    if "decimal" not in load_prefs():  # séparateur jamais choisi : il suit la langue
        st.session_state["decimal"] = separator_for(lang)
    st.session_state.pop("page", None)
    st.session_state.pop("help_topic", None)


def _apply_decimal():
    st.session_state["decimal"] = st.session_state["set_decimal"]
    save_pref("decimal", st.session_state["decimal"])


def settings() -> None:
    st.session_state["set_lang"] = st.session_state.get("lang", "fr")
    st.selectbox(T("Langue de l'interface"), ["fr", "en"], key="set_lang",
                 format_func={"fr": "Français", "en": "English"}.get, on_change=_apply_language,
                 help=T("Par défaut : la langue choisie à l'installation (ou celle du système)."))
    st.session_state["set_decimal"] = st.session_state.get("decimal", ",")
    st.selectbox(T("Séparateur décimal"), [",", "."], key="set_decimal",
                 format_func={",": T("virgule (0,318)"), ".": T("point (0.318)")}.get, on_change=_apply_decimal)
    st.session_state["set_nboot"] = int(load_prefs().get("n_boot", 1000))
    st.number_input(T("Échantillons bootstrap par défaut"), 100, 20000, key="set_nboot", step=500,
                    on_change=lambda: save_pref("n_boot", int(st.session_state["set_nboot"])),
                    help=T("Valeur proposée au démarrage. 5 000 est recommandé pour les résultats publiés."))
    st.caption(T("Les réglages sont enregistrés sur cet ordinateur et repris au prochain lancement."))
    if st.button(T("Fermer"), type="primary"):
        st.rerun()


def render() -> None:
    """Boutons en haut à droite, sur la ligne des onglets (position fixée en CSS : .st-key-topmenu)."""
    with st.container(key="topmenu", horizontal=True, gap="small"):
        # boîtes de dialogue créées à chaque passage : leur titre suit la langue de l'interface
        if st.button(T("À propos"), key="m_about", type="tertiary", icon=":material/info:"):
            st.dialog(T("À propos d’OpenPLS"), width="medium")(about)()
        if st.button(T("Mises à jour"), key="m_update", type="tertiary", icon=":material/update:"):
            st.dialog(T("Rechercher des mises à jour"), width="medium")(check_updates)()
        if st.button(T("Paramètres"), key="m_settings", type="tertiary", icon=":material/settings:"):
            st.dialog(T("Paramètres"), width="medium")(settings)()
