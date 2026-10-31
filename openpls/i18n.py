"""Langue de l'interface (français ou anglais).

Ordre de priorité :
1. variable d'environnement OPENPLS_LANG ("fr" ou "en") ;
2. choix enregistré dans l'application (~/.openpls/settings.json, clé "language") ;
3. langue choisie dans l'installateur Windows (settings.ini à côté d'OpenPLS.exe) ;
4. langue du système : français si elle commence par « fr », anglais sinon.

Les textes sont écrits en français dans le code ; `T(texte)` renvoie la traduction anglaise
(dictionnaire `EN` de i18n_en.py) quand l'interface est en anglais. Un texte absent du
dictionnaire reste en français (un test vérifie qu'il n'en manque aucun dans app.py).
"""
from __future__ import annotations

import os

from .settings import install_language, load_prefs, system_language

LANGS = ("fr", "en")
_lang = "fr"


def normalize(language: str | None) -> str | None:
    if not language:
        return None
    return "fr" if language.lower().replace("-", "_").startswith(("fr", "french")) else "en"


def default_language() -> str:
    """Langue de l'installation, sinon du système (sans tenir compte du choix enregistré)."""
    return normalize(install_language() or system_language()) or "en"


def ui_language() -> str:
    env = os.environ.get("OPENPLS_LANG")
    if env in LANGS:
        return env
    saved = load_prefs().get("language")
    if saved in LANGS:
        return saved
    return default_language()


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else "fr"


def get_language() -> str:
    return _lang


def T(text: str, **kw) -> str:
    """Traduit `text` (source française) dans la langue courante, puis remplace les {champs}."""
    if _lang == "en":
        from .i18n_en import EN

        text = EN.get(text, text)
    return text.format(**kw) if kw else text


def _log(value) -> None:
    """Collecte (pour les traducteurs) des textes affichés : OPENPLS_I18N_LOG=fichier."""
    path = os.environ.get("OPENPLS_I18N_LOG")
    if path and isinstance(value, str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(value.replace("\n", "\\n") + "\n")


def tr(value):
    """Traduit une valeur affichée (nom de colonne, cellule) si elle figure dans le dictionnaire."""
    _log(value)
    if _lang != "en" or not isinstance(value, str):
        return value
    from .i18n_en import translate

    return translate(value)
