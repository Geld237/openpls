"""Préférences de l'interface : séparateur décimal (virgule ou point).

Ordre de priorité :
1. variable d'environnement OPENPLS_DECIMAL ("," ou ".") ;
2. choix enregistré dans l'application (~/.openpls/settings.json) ;
3. langue choisie dans l'installateur Windows (settings.ini à côté d'OpenPLS.exe) ;
4. langue du système.
Virgule pour le français et la plupart des langues européennes, point pour l'anglais.
"""
from __future__ import annotations

import configparser
import json
import locale
import os
import subprocess
import sys
from pathlib import Path

# langues qui écrivent 0.318 (les autres écrivent 0,318)
_POINT_LANGS = ("en", "english", "zh", "chinese", "ja", "japanese", "ko", "korean", "he", "hebrew",
                "th", "thai", "hi", "hindi", "ms", "malay")


def _prefs_path() -> Path:
    return Path(os.environ.get("OPENPLS_HOME") or (Path.home() / ".openpls")) / "settings.json"


def load_prefs() -> dict:
    try:
        return json.loads(_prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_pref(key: str, value) -> None:
    prefs = load_prefs()
    prefs[key] = value
    try:
        _prefs_path().parent.mkdir(parents=True, exist_ok=True)
        _prefs_path().write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except OSError:
        pass  # dossier personnel en lecture seule : le choix vaut pour la session


def install_language() -> str | None:
    """Langue choisie dans l'installateur (Windows), écrite dans settings.ini à côté de l'exécutable."""
    if not getattr(sys, "frozen", False):
        return None
    ini = Path(sys.executable).resolve().parent / "settings.ini"
    cp = configparser.ConfigParser()
    try:
        cp.read(ini, encoding="utf-8")
        return cp.get("general", "language", fallback=None) or None
    except (OSError, configparser.Error):
        return None


def system_language() -> str | None:
    for var in ("LC_ALL", "LC_NUMERIC", "LANG"):
        v = os.environ.get(var)
        if v and v not in ("C", "POSIX") and not v.startswith("C."):
            return v
    try:
        name = locale.getlocale()[0]
    except ValueError:
        name = None
    if name and name not in ("C", "POSIX"):
        return name
    if sys.platform == "darwin":  # application lancée depuis le Finder : LANG n'est pas défini
        try:
            return subprocess.run(["defaults", "read", "-g", "AppleLocale"], capture_output=True, text=True,
                                  timeout=3).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            return None
    return None


def separator_for(language: str | None) -> str:
    if not language:
        return "."
    lang = language.lower().replace("-", "_")
    return "." if lang.startswith(_POINT_LANGS) else ","


def default_decimal() -> str:
    """Séparateur de la langue de l'interface : choix enregistré, sinon installation, sinon système."""
    lang = os.environ.get("OPENPLS_LANG") or load_prefs().get("language")
    return separator_for(lang or install_language() or system_language())


def decimal_separator() -> str:
    env = os.environ.get("OPENPLS_DECIMAL")
    if env in (",", "."):
        return env
    saved = load_prefs().get("decimal")
    if saved in (",", "."):
        return saved
    return default_decimal()
