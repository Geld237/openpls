"""Point d'entrée `openpls-gui` : lance l'interface Streamlit."""
import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        sys.exit("L'interface nécessite Streamlit : pip install 'openpls[gui]'")
    app = Path(__file__).with_name("app.py")
    # localhost par défaut : les données importées ne sont pas exposées au réseau local.
    # Pour partager volontairement : openpls-gui --server.address 0.0.0.0
    sys.argv = ["streamlit", "run", str(app), "--server.address=localhost", "--browser.gatherUsageStats=false",
                "--client.toolbarMode=minimal", "--theme.primaryColor=#2E5E9E", *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
