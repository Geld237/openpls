"""Onglet « Aide » : interprétation et repères, par rubrique, dans la langue de l'interface."""
from __future__ import annotations

import streamlit as st

from .help_content import HELP
from .i18n import T, get_language


def render() -> None:
    topics = HELP[get_language()]
    titles = [t for t, _ in topics]
    left, right = st.columns([1, 3], gap="large")
    with left:
        query = st.text_input(T("Rechercher dans l'aide"), key="help_q", placeholder=T("ex. HTMT, médiation"))
        shown = [t for t, body in topics if not query or query.lower() in (t + body).lower()]
        if not shown:
            st.caption(T("Aucune rubrique ne contient « {q} ».", q=query))
            return
        if st.session_state.get("help_topic") not in shown:
            st.session_state["help_topic"] = shown[0]
        st.radio(T("Rubriques"), shown, key="help_topic", label_visibility="collapsed")
    with right:
        title = st.session_state["help_topic"]
        st.subheader(title)
        st.markdown(dict(topics)[title])
        i = titles.index(title)
        if i + 1 < len(titles):
            st.caption(T("Rubrique suivante : {t}", t=titles[i + 1]))
