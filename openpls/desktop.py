"""Application de bureau OpenPLS : une fenêtre, sans terminal ni navigateur.

Architecture
------------
* Le processus principal ouvre une fenêtre native (pywebview : WebView2 sous Windows,
  WebKit sous macOS, Qt/GTK sous Linux si disponibles) qui affiche l'interface.
* Un processus enfant, invisible, fait tourner le serveur Streamlit sur localhost.
* Fermer la fenêtre arrête le serveur ; si le processus principal disparaît, le serveur
  s'arrête de lui-même (surveillance du processus parent).
* Si aucun moteur de fenêtre n'est disponible, repli sur le navigateur par défaut ; un
  bouton « Quitter OpenPLS » dans l'interface arrête alors l'application.

Options (diagnostic) : --serve PORT (serveur seul), --selftest (ouvre la fenêtre, vérifie
que l'interface s'affiche, écrit ~/.openpls/selftest.json et quitte).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
LOG_DIR = Path.home() / ".openpls"


def _app_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "openpls" / "app.py"


def _redirect_streams(name: str):
    """Application fenêtrée : pas de console, donc stdout/stderr vers un fichier journal."""
    LOG_DIR.mkdir(exist_ok=True)
    log = open(LOG_DIR / f"{name}.log", "w", encoding="utf-8", buffering=1)  # noqa: SIM115
    if sys.stdout is None or FROZEN:
        sys.stdout = log
    if sys.stderr is None or FROZEN:
        sys.stderr = log
    return log


def _free_port(start: int = 8501) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Aucun port libre entre 8501 et 8550")


def _ready(port: int) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- processus serveur
def serve(port: int) -> None:
    from streamlit.web import cli

    parent = os.environ.get("OPENPLS_PARENT_PID")
    if parent:  # s'arrêter si l'application principale a disparu
        parent_pid = int(parent)

        def alive() -> bool:
            if sys.platform == "win32":
                return _pid_alive(parent_pid)
            # POSIX : un parent tué peut rester « zombie » (kill(pid, 0) réussit encore) ;
            # en revanche, nous sommes alors rattachés à un autre processus parent
            return os.getppid() == parent_pid

        def watch():
            while alive():
                time.sleep(1)
            os._exit(0)
        threading.Thread(target=watch, daemon=True).start()
    os.chdir(_app_path().parent)  # thème : ./.streamlit/config.toml ; police et logo : ./static
    sys.argv = ["streamlit", "run", str(_app_path()),
                "--global.developmentMode=false", "--server.headless=true",
                "--server.address=localhost", f"--server.port={port}",
                "--server.enableStaticServing=true",
                "--browser.gatherUsageStats=false", "--client.toolbarMode=minimal"]
    sys.exit(cli.main())


def _start_server(port: int, log) -> subprocess.Popen:
    env = {**os.environ, "OPENPLS_DESKTOP": "1", "OPENPLS_PARENT_PID": str(os.getpid())}
    cmd = [sys.executable, "--serve", str(port)] if FROZEN else [sys.executable, "-m", "openpls.desktop",
                                                                 "--serve", str(port)]
    flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    return subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags)


# ---------------------------------------------------------------- fenêtre
_SELFTEST_JS = ("(function(){var t=document.body?document.body.innerText:'';"
                "return JSON.stringify({ok:t.indexOf('Estimer le mod')>=0||t.indexOf('Estimate the mod')>=0,"
                "editor:!!document.querySelector('iframe[title*=openpls_model_editor]')});})()")


def _run_window(url: str, server: subprocess.Popen, selftest: bool) -> bool:
    """Ouvre la fenêtre native. Renvoie False si aucun moteur de fenêtre n'est disponible."""
    try:
        import webview
    except Exception as e:  # noqa: BLE001
        print(f"pywebview indisponible : {e}", flush=True)
        return False
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    window = webview.create_window("OpenPLS", url, width=1400, height=900, min_size=(960, 640))
    result = {"ok": False, "editor": False, "error": None}

    def background():
        # fermer la fenêtre si le serveur s'arrête (bouton « Quitter » ou plantage)
        if selftest:
            deadline = time.time() + 90
            while time.time() < deadline:
                try:
                    got = json.loads(window.evaluate_js(_SELFTEST_JS) or "{}")
                    result.update(got)
                    if got.get("ok") and got.get("editor"):
                        break
                except Exception as e:  # noqa: BLE001
                    result["error"] = str(e)
                time.sleep(1)
            window.destroy()
            return
        while server.poll() is None:
            time.sleep(1)
        window.destroy()

    try:
        import inspect

        extra = {}  # icône de fenêtre (GTK/Qt ; Windows et macOS prennent celle de l'exécutable)
        # Windows (WinForms) n'accepte qu'un .ico et lève une exception .NET avec un PNG
        if sys.platform.startswith("linux") and "icon" in inspect.signature(webview.start).parameters:
            extra["icon"] = str(_app_path().parent / "static" / "icon.png")
        webview.start(background, private_mode=False, **extra)
    except Exception as e:  # noqa: BLE001 - aucun moteur (Linux sans Qt/GTK, Windows sans WebView2…)
        print(f"Fenêtre impossible : {e}", flush=True)
        return False
    if selftest:
        result["gui"] = getattr(webview, "guilib", None).__name__ if getattr(webview, "guilib", None) else None
        (LOG_DIR / "selftest.json").write_text(json.dumps(result), encoding="utf-8")
    return True


def main() -> None:
    args = sys.argv[1:]
    if "--serve" in args:
        _redirect_streams("serveur")
        serve(int(args[args.index("--serve") + 1]))
        return
    log = _redirect_streams("openpls")
    selftest = "--selftest" in args
    port = _free_port()
    url = f"http://localhost:{port}"
    server = _start_server(port, log)
    try:
        deadline = time.time() + 120
        while not _ready(port):
            if server.poll() is not None or time.time() > deadline:
                raise RuntimeError(f"le serveur OpenPLS n'a pas démarré (voir {LOG_DIR / 'serveur.log'})")
            time.sleep(0.3)
        if not _run_window(url, server, selftest):
            if selftest:
                (LOG_DIR / "selftest.json").write_text(json.dumps({"ok": False, "error": "pas de fenêtre"}))
                sys.exit(2)
            # repli : navigateur ; l'application s'arrête via le bouton « Quitter OpenPLS »
            webbrowser.open(url)
            server.wait()
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(5)
            except subprocess.TimeoutExpired:
                server.kill()
    if selftest:
        res = json.loads((LOG_DIR / "selftest.json").read_text(encoding="utf-8"))
        sys.exit(0 if res.get("ok") and res.get("editor") else 1)


if __name__ == "__main__":
    main()
