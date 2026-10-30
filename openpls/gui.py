"""Point d'entrée `openpls-gui` : lance l'interface Streamlit."""
import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        sys.exit("L'interface nécessite Streamlit : pip install 'openpls[gui]'")
    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app), "--browser.gatherUsageStats=false",
                "--client.toolbarMode=minimal", "--theme.primaryColor=#2E5E9E", *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
