"""OpenPLS — implémentation libre du PLS-SEM, réécrite à partir de la littérature publiée."""
from .model import Model
from .algorithm import fit, PLSResult
from .bootstrap import bootstrap
from .assessment import quality_criteria, fornell_larcker, htmt, f_squared

__all__ = ["Model", "fit", "PLSResult", "bootstrap", "quality_criteria", "fornell_larcker", "htmt", "f_squared"]
__version__ = "0.1.0"
