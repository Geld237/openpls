"""Diagramme des résultats interactif : variables déplaçables, espacement réglable, feuille ajustée au contenu.

La disposition est décrite par `{"lv": {id: [x, y]}, "off": {id: [dx, dy]}}` (pixels, y vers le bas) :
positions des variables latentes, et décalage de chaque indicateur (ou terme d'interaction) par rapport à la
variable à laquelle il est rattaché. L'espacement rapproche ou écarte les latentes autour de leur centre sans
toucher aux décalages : les indicateurs restent collés à leur variable."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .diagram_export import parse_dot

_component = None


def _get_component():
    global _component
    if _component is None:
        import streamlit.components.v1 as components

        _component = components.declare_component("openpls_results_diagram",
                                                  path=str(Path(__file__).parent / "diagram"))
    return _component


def diagram_data(dot: str, model) -> tuple[list, list, dict]:
    """Nœuds, arêtes et disposition automatique à partir du DOT à positions fixées de model_to_dot."""
    nodes_raw, edges = parse_dot(dot)
    owner = {}
    for lv, inds in model.measurement.items():
        for ind in inds:
            owner.setdefault(f"mv:{ind}", f"lv:{lv}")
    for a, b, d in getattr(model, "interactions", []):
        owner[f"ix:{a}:{b}"] = f"lv:{d}"
    nodes, layout = [], {"lv": {}, "off": {}}
    pos = {nid: (72 * n["x"], -72 * n["y"]) for nid, n in nodes_raw.items()}
    for nid, n in nodes_raw.items():
        kind = nid.split(":", 1)[0]
        kind = kind if kind in ("lv", "mv", "ix") else "mv"
        node = {"id": nid, "kind": kind, "label": n["label"], "fill": n["fill"], "stroke": n["color"],
                "double": n["double"]}
        if kind == "lv":
            layout["lv"][nid] = list(pos[nid])
        else:
            own = owner.get(nid)
            if own not in pos:  # rattachement inconnu : nœud libre, déplacé comme une latente
                layout["lv"][nid] = list(pos[nid])
                node["owner"] = None
            else:
                node["owner"] = own
                layout["off"][nid] = [pos[nid][0] - pos[own][0], pos[nid][1] - pos[own][1]]
        nodes.append(node)
    for e in edges:
        e["small"] = e["a"].startswith("mv:") or e["b"].startswith("mv:")
    return nodes, edges, layout


def display_positions(nodes: list, layout: dict, spacing: float) -> dict:
    """Même calcul que le composant : latentes mises à l'échelle autour de leur centre, décalages conservés."""
    lv = layout["lv"]
    cx = sum(p[0] for p in lv.values()) / max(len(lv), 1)
    cy = sum(p[1] for p in lv.values()) / max(len(lv), 1)
    P = {k: (cx + spacing * (p[0] - cx), cy + spacing * (p[1] - cy)) for k, p in lv.items()}
    for n in nodes:
        if n["id"] not in P:
            o = P.get(n.get("owner"), (0.0, 0.0))
            d = layout["off"].get(n["id"], (0.0, 0.0))
            P[n["id"]] = (o[0] + d[0], o[1] + d[1])
    return P


def merge_layout(auto: dict, saved: dict | None) -> dict:
    """Disposition enregistrée par l'utilisateur, complétée par l'automatique pour les nouveaux nœuds."""
    if not saved:
        return auto
    return {"lv": {k: saved.get("lv", {}).get(k, v) for k, v in auto["lv"].items()},
            "off": {k: saved.get("off", {}).get(k, v) for k, v in auto["off"].items()}}


def results_diagram(dot: str, model, signature: str, texts: dict, key: str = "res_diagram"):
    """Affiche le diagramme interactif ; renvoie (nœuds, arêtes, positions affichées) pour l'export."""
    import streamlit as st

    nodes, edges, auto = diagram_data(dot, model)
    store = st.session_state.get("res_layout")
    if not store or store.get("sig") != signature:  # autre modèle : disposition automatique
        store = {"sig": signature, "lv": None, "off": None, "spacing": 1.0, "reset": 0}
        st.session_state["res_layout"] = store
    saved = {"lv": store["lv"], "off": store["off"]} if store.get("lv") else None
    layout = merge_layout(auto, saved)
    version = hashlib.sha1(f"{signature}|{store['reset']}".encode()).hexdigest()
    out = _get_component()(nodes=nodes, edges=edges, layout=layout, auto=auto, spacing=store["spacing"],
                           auto_spacing=1.0, version=version, text=texts, paper="#F5F7FA", max_height=900,
                           key=f"{key}:{version}", default=None)
    if out and out.get("nonce") != store.get("nonce"):
        store["nonce"] = out["nonce"]
        if out.get("reset"):
            store.update(lv=None, off=None, spacing=1.0)
            layout = auto
        else:
            store.update(lv=out["lv"], off=out["off"], spacing=float(out.get("spacing", 1.0)))
            layout = merge_layout(auto, {"lv": out["lv"], "off": out["off"]})
    return nodes, edges, display_positions(nodes, layout, store["spacing"])
