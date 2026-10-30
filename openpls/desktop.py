"""Lanceur de l'application autonome (installateur Windows / macOS / Linux construit avec PyInstaller).

Ouvre l'interface dans le navigateur par défaut ; tout reste sur l'ordinateur (localhost)."""
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _free_port(start: int = 8501) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Aucun port libre entre 8501 et 8550")


def _open_when_ready(url: str, port: int, timeout: float = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.3)


def main() -> None:
    from streamlit.web import cli

    frozen_root = getattr(sys, "_MEIPASS", None)  # dossier de l'application empaquetée
    base = Path(frozen_root) if frozen_root else Path(__file__).resolve().parent.parent
    app = base / "openpls" / "app.py"
    port = _free_port()
    url = f"http://localhost:{port}"
    print(f"OpenPLS démarre dans votre navigateur ({url})…\n"
          "Si la page ne s'ouvre pas, copiez cette adresse dans votre navigateur.\n"
          "Fermez cette fenêtre pour quitter OpenPLS.", flush=True)
    if "--no-browser" not in sys.argv:
        threading.Thread(target=_open_when_ready, args=(url, port), daemon=True).start()
    # headless : pas de question interactive au premier lancement ; le navigateur est ouvert ci-dessus
    sys.argv = ["streamlit", "run", str(app),
                "--global.developmentMode=false", "--server.headless=true",
                "--server.address=localhost", f"--server.port={port}",
                "--browser.gatherUsageStats=false", "--client.toolbarMode=minimal",
                "--theme.primaryColor=#2E5E9E"]
    sys.exit(cli.main())


if __name__ == "__main__":
    main()
