"""Fichier projet OpenPLS (.openpls) : une archive zip avec les données (data.csv) et project.json
(syntaxe, disposition de l'éditeur, réglages). Il permet de rouvrir ou de partager une analyse."""
from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

from . import __version__

SETTINGS = ("algo", "scheme", "moderation", "hoc_method", "missing", "n_boot", "seed", "auto_boot", "boot_ci",
            "alpha_saved", "sig_view")


def save_project(raw: pd.DataFrame, file_name: str, syntax: str, positions: dict | None, settings: dict) -> bytes:
    meta = {"openpls": __version__, "file_name": file_name, "syntax": syntax,
            "editor_pos": {k: list(v) for k, v in (positions or {}).items()},
            "settings": {k: settings[k] for k in SETTINGS if k in settings},
            "labels": raw.attrs.get("labels", {})}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(meta, ensure_ascii=False, indent=2, default=str))
        z.writestr("data.csv", raw.to_csv(index=False))
    return buf.getvalue()


def load_project(content: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        meta = json.loads(z.read("project.json").decode("utf-8"))
        raw = pd.read_csv(io.BytesIO(z.read("data.csv")))
    raw.attrs["labels"] = meta.get("labels", {})
    meta["data"] = raw
    meta["editor_pos"] = {k: tuple(v) for k, v in meta.get("editor_pos", {}).items()}
    return meta
