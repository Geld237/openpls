"""Éditeur graphique de modèle (glisser-déposer), composant Streamlit sans étape de build."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .model import Model

_component = None


def _get_component():
    global _component
    if _component is None:
        import streamlit.components.v1 as components

        _component = components.declare_component("openpls_model_editor", path=str(Path(__file__).parent / "editor"))
    return _component


def editor_state(syntax: str, positions: dict | None = None) -> dict:
    """Convertit une syntaxe en état de l'éditeur (latentes positionnées, chemins, interactions)."""
    positions = positions or {}
    try:
        model = Model.from_syntax(syntax)
    except ValueError:
        return {"latents": [], "paths": [], "interactions": []}
    # disposition par couches : profondeur = plus long chemin depuis une exogène
    depth: dict[int, int] = {}

    def d(j):
        if j not in depth:
            pred = model.predecessors(j)
            depth[j] = 0 if not len(pred) else 1 + max(d(i) for i in pred)
        return depth[j]

    rows: dict[int, int] = {}
    latents = []
    for j, lv in enumerate(model.latents):
        col = d(j)
        row = rows.get(col, 0)
        rows[col] = row + 1
        x, y = positions.get(lv, (30 + 230 * col, 30 + 130 * row + 65 * (col % 2)))
        latents.append({"name": lv, "mode": model.modes[lv], "indicators": list(model.measurement[lv]),
                        "x": x, "y": y})
    return {"latents": latents, "paths": [list(p) for p in model.structural],
            "interactions": [list(i) for i in model.interactions]}


def model_editor(columns: list[str], syntax: str, positions: dict | None = None, key: str = "editor"):
    """Affiche l'éditeur. Retourne None, ou {"nonce", "syntax", "positions"} quand l'utilisateur applique."""
    state = editor_state(syntax, positions)
    version = hashlib.sha1((syntax + repr(sorted((positions or {}).items()))).encode()).hexdigest()
    return _get_component()(columns=[str(c) for c in columns], state=state, version=version, key=key, default=None)
