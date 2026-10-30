"""Construit l'application autonome OpenPLS avec PyInstaller.

    pip install -e ".[gui]" pyinstaller
    python packaging/build.py          # résultat : dist/OpenPLS/
"""
import sys
from pathlib import Path

import PyInstaller.__main__

root = Path(__file__).resolve().parent.parent
sep = ";" if sys.platform == "win32" else ":"
PyInstaller.__main__.run([
    str(root / "packaging" / "launcher.py"),
    "--name", "OpenPLS",
    "--noconfirm", "--clean",
    "--distpath", str(root / "dist"), "--workpath", str(root / "build"), "--specpath", str(root / "build"),
    # Streamlit lit ses fichiers statiques et ses métadonnées à l'exécution
    "--collect-all", "streamlit", "--copy-metadata", "streamlit",
    "--collect-data", "altair", "--copy-metadata", "altair",
    "--collect-all", "openpls",
    # le script de l'interface doit exister comme fichier : Streamlit l'exécute
    "--add-data", f"{root / 'openpls' / 'app.py'}{sep}openpls",
    "--hidden-import", "openpyxl", "--hidden-import", "scipy.special._cdflib",
    *(["--osx-bundle-identifier", "org.openpls.app"] if sys.platform == "darwin" else []),
])
