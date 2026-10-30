"""OpenPLS — implémentation libre du PLS-SEM, réécrite à partir de la littérature publiée."""
from .model import Model
from .algorithm import fit, PLSResult
from .bootstrap import bootstrap, bootstrap_statistics
from .assessment import quality_criteria, fornell_larcker, htmt, f_squared
from .effects import (
    total_effects,
    total_indirect_effects,
    specific_indirect_effects,
    mediation_analysis,
)

__all__ = [
    "Model", "fit", "PLSResult", "bootstrap", "bootstrap_statistics",
    "quality_criteria", "fornell_larcker", "htmt", "f_squared",
    "total_effects", "total_indirect_effects", "specific_indirect_effects", "mediation_analysis",
]
__version__ = "0.2.0"
