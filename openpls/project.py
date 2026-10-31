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


def save_project(raw: pd.DataFrame, file_name: str, syntax: str, positions: dict | None, settings: dict,
                 results: dict | None = None) -> bytes:
    meta = {"openpls": __version__, "file_name": file_name, "syntax": syntax,
            "editor_pos": {k: list(v) for k, v in (positions or {}).items()},
            "settings": {k: settings[k] for k in SETTINGS if k in settings},
            "labels": raw.attrs.get("labels", {})}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(meta, ensure_ascii=False, indent=2, default=str))
        z.writestr("data.csv", raw.to_csv(index=False))
        if results:
            z.writestr("results.json", encode_results(results))
    return buf.getvalue()


def load_project(content: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        meta = json.loads(z.read("project.json").decode("utf-8"))
        raw = pd.read_csv(io.BytesIO(z.read("data.csv")))
        meta["results"] = decode_results(z.read("results.json").decode("utf-8")) if "results.json" in z.namelist() \
            else None
    raw.attrs["labels"] = meta.get("labels", {})
    meta["data"] = raw
    meta["editor_pos"] = {k: tuple(v) for k, v in meta.get("editor_pos", {}).items()}
    return meta


# ---------------------------------------------------------------- résultats (sans pickle : un projet partagé
# ne doit jamais pouvoir exécuter de code à l'ouverture)
def _enc(obj):
    import numpy as np

    if isinstance(obj, pd.DataFrame):
        return {"__df__": {"columns": [_enc(c) for c in obj.columns], "index": [_enc(i) for i in obj.index],
                           "index_names": list(obj.index.names), "column_names": list(obj.columns.names),
                           "dtypes": [str(t) for t in obj.dtypes],
                           "data": [[_enc(v) for v in row] for row in obj.itertuples(index=False, name=None)],
                           "attrs": _enc(dict(obj.attrs))}}
    if isinstance(obj, pd.Series):
        return {"__series__": _enc(obj.to_frame(name=obj.name if obj.name is not None else "__value__"))}
    if isinstance(obj, np.ndarray):
        return {"__nd__": [_enc(v) for v in obj.tolist()], "dtype": str(obj.dtype)}
    if isinstance(obj, tuple):
        return {"__tuple__": [_enc(v) for v in obj]}
    if isinstance(obj, list):
        return [_enc(v) for v in obj]
    if isinstance(obj, dict):
        return {"__dict__": [[_enc(k), _enc(v)] for k, v in obj.items()]}
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if f == f and abs(f) != float("inf") else {"__float__": repr(f)}
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    if isinstance(obj, (pd.Timestamp,)):
        return {"__ts__": obj.isoformat()}
    return {"__str__": str(obj)}


def _dec(obj):
    import numpy as np

    if isinstance(obj, list):
        return [_dec(v) for v in obj]
    if not isinstance(obj, dict):
        return obj
    if "__df__" in obj:
        d = obj["__df__"]
        cols = [_dec(c) for c in d["columns"]]
        idx = [_dec(i) for i in d["index"]]
        df = pd.DataFrame([[_dec(v) for v in row] for row in d["data"]], columns=range(len(cols)))
        for j, t in enumerate(d["dtypes"]):
            try:
                if t.startswith(("float", "int", "bool")):
                    df[j] = df[j].astype(t)
            except (ValueError, TypeError):
                pass
        df.columns = (pd.MultiIndex.from_tuples(cols, names=d["column_names"]) if cols and isinstance(cols[0], tuple)
                      else pd.Index(cols, name=d["column_names"][0] if d["column_names"] else None))
        df.index = (pd.MultiIndex.from_tuples(idx, names=d["index_names"]) if idx and isinstance(idx[0], tuple)
                    else pd.Index(idx, name=d["index_names"][0] if d["index_names"] else None))
        df.attrs = _dec(d.get("attrs", {})) or {}
        return df
    if "__series__" in obj:
        df = _dec(obj["__series__"])
        s = df.iloc[:, 0]
        s.name = None if s.name == "__value__" else s.name
        return s
    if "__nd__" in obj:
        return np.array(_dec(obj["__nd__"]), dtype=obj.get("dtype") or None)
    if "__tuple__" in obj:
        return tuple(_dec(v) for v in obj["__tuple__"])
    if "__dict__" in obj:
        return {_dec(k): _dec(v) for k, v in obj["__dict__"]}
    if "__float__" in obj:
        return float(obj["__float__"])
    if "__ts__" in obj:
        return pd.Timestamp(obj["__ts__"])
    if "__str__" in obj:
        return obj["__str__"]
    return {k: _dec(v) for k, v in obj.items()}


def encode_results(results: dict | None) -> str | None:
    return None if not results else json.dumps(_enc(results), ensure_ascii=False, allow_nan=False)


def decode_results(text: str | None) -> dict | None:
    return None if not text else _dec(json.loads(text))


# ---------------------------------------------------------------- dossier de travail (sauvegarde auto, récents)
def data_dir():
    """~/.openpls, ou le dossier indiqué par OPENPLS_HOME (tests, installations portables)."""
    import os
    from pathlib import Path

    d = Path(os.environ.get("OPENPLS_HOME") or (Path.home() / ".openpls"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_autosave(blob: bytes, info: dict) -> None:
    d = data_dir()
    tmp = d / "autosave.openpls.tmp"
    tmp.write_bytes(blob)
    tmp.replace(d / "autosave.openpls")  # remplacement atomique : jamais de fichier à moitié écrit
    (d / "autosave.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")


def read_autosave() -> tuple[bytes, dict] | None:
    d = data_dir()
    try:
        return (d / "autosave.openpls").read_bytes(), json.loads((d / "autosave.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clear_autosave() -> None:
    for name in ("autosave.openpls", "autosave.json"):
        try:
            (data_dir() / name).unlink()
        except OSError:
            pass


def remember_recent(name: str, blob: bytes, info: dict, keep: int = 8) -> None:
    """Copie le projet dans ~/.openpls/recent et met à jour la liste (les plus récents d'abord)."""
    import hashlib
    import re

    d = data_dir() / "recent"
    d.mkdir(exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", name.rsplit(".", 1)[0])[:60] or "projet"
    fname = f"{stem}-{hashlib.sha256(blob).hexdigest()[:8]}.openpls"
    (d / fname).write_bytes(blob)
    items = [it for it in list_recent() if it["name"] != info.get("name", name)]
    items.insert(0, {**info, "name": info.get("name", name), "file": fname})
    for old in items[keep:]:
        try:
            (d / old["file"]).unlink()
        except OSError:
            pass
    (d / "recent.json").write_text(json.dumps(items[:keep], ensure_ascii=False, indent=1), encoding="utf-8")


def list_recent() -> list[dict]:
    d = data_dir() / "recent"
    try:
        items = json.loads((d / "recent.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [it for it in items if (d / it.get("file", "")).is_file()]


def read_recent(item: dict) -> bytes:
    return (data_dir() / "recent" / item["file"]).read_bytes()


def clear_history() -> None:
    import shutil

    clear_autosave()
    shutil.rmtree(data_dir() / "recent", ignore_errors=True)
