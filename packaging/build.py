"""Construit l'application de bureau OpenPLS (fenêtre, sans console) avec PyInstaller.

    pip install -e ".[gui,desktop]" pyinstaller
    python packaging/build.py
Résultat : dist/OpenPLS/ (Windows, Linux) ou dist/OpenPLS.app (macOS).
"""
import sys
from pathlib import Path

import PyInstaller.__main__

root = Path(__file__).resolve().parent.parent
sep = ";" if sys.platform == "win32" else ":"
icon = {"win32": "icon.ico", "darwin": "icon.icns"}.get(sys.platform, "icon.png")
args = [
    str(root / "packaging" / "launcher.py"),
    "--name", "OpenPLS",
    "--noconfirm", "--clean",
    "--distpath", str(root / "dist"), "--workpath", str(root / "build"), "--specpath", str(root / "build"),
    "--icon", str(root / "packaging" / icon),
    # Streamlit lit ses fichiers statiques et ses métadonnées à l'exécution
    "--collect-all", "streamlit", "--copy-metadata", "streamlit",
    "--collect-data", "altair", "--copy-metadata", "altair",
    "--collect-all", "openpls",
    # le script de l'interface doit exister comme fichier : Streamlit l'exécute
    "--add-data", f"{root / 'openpls' / 'app.py'}{sep}openpls",
    # thème, police et logo (dossiers cachés et données non Python : ajoutés explicitement)
    "--add-data", f"{root / 'openpls' / '.streamlit' / 'config.toml'}{sep}openpls/.streamlit",
    "--add-data", f"{root / 'openpls' / 'static'}{sep}openpls/static",
    "--add-data", f"{root / 'openpls' / 'style.css'}{sep}openpls",
    "--hidden-import", "openpyxl", "--hidden-import", "scipy.special._cdflib",
    # moteur de fenêtre (pywebview)
    "--collect-all", "webview",
]
if sys.platform in ("win32", "darwin"):
    args.append("--windowed")  # pas de console
if sys.platform == "win32":
    args += ["--collect-all", "clr_loader", "--collect-all", "pythonnet", "--hidden-import", "clr"]
if sys.platform == "darwin":
    args += ["--osx-bundle-identifier", "org.openpls.app",
             "--hidden-import", "objc", "--hidden-import", "AppKit", "--hidden-import", "Foundation",
             "--hidden-import", "WebKit", "--hidden-import", "Quartz", "--hidden-import", "UniformTypeIdentifiers"]
PyInstaller.__main__.run(args)
