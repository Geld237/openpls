import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # pour importer reference_pls depuis les tests

import os

# affichage déterministe des nombres dans les tests (sinon : langue du système ou préférence enregistrée)
os.environ.setdefault("OPENPLS_DECIMAL", ".")

# interface en français dans les tests (sinon : langue du système ou préférence enregistrée)
os.environ.setdefault("OPENPLS_LANG", "fr")
