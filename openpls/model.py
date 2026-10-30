"""Spécification d'un modèle PLS-SEM : modèle de mesure (externe) + modèle structurel (interne)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Model:
    """Décrit un modèle PLS-SEM.

    measurement : {variable_latente: [indicateurs]}
    structural  : [(source, cible), ...]  — chemins entre variables latentes
    modes       : {variable_latente: "A" | "B"}  — A = réflectif, B = formatif (défaut A)
    """

    measurement: dict[str, list[str]]
    structural: list[tuple[str, str]]
    modes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.latents: list[str] = list(self.measurement)
        idx = {lv: i for i, lv in enumerate(self.latents)}
        for src, dst in self.structural:
            if src not in idx or dst not in idx:
                raise ValueError(f"Chemin {src} -> {dst} : variable latente inconnue")
            if src == dst:
                raise ValueError(f"Boucle sur {src} interdite")
        for lv in self.latents:
            mode = self.modes.setdefault(lv, "A").upper()
            if mode not in ("A", "B"):
                raise ValueError(f"Mode inconnu pour {lv} : {mode}")
            self.modes[lv] = mode
            if not self.measurement[lv]:
                raise ValueError(f"{lv} n'a aucun indicateur")

        # path[i, j] = 1 si latente i -> latente j
        k = len(self.latents)
        self.path = np.zeros((k, k), dtype=int)
        for src, dst in self.structural:
            self.path[idx[src], idx[dst]] = 1
        self._check_acyclic()

    def _check_acyclic(self) -> None:
        # PLS-SEM classique exige un modèle récursif (pas de cycle)
        # Dans un graphe orienté sans cycle à k nœuds, aucun chemin de longueur k n'existe
        if np.linalg.matrix_power(self.path, len(self.latents)).any():
            raise ValueError("Le modèle structurel contient un cycle")

    @property
    def indicators(self) -> list[str]:
        return [ind for lv in self.latents for ind in self.measurement[lv]]

    def predecessors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[:, j])

    def successors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[j, :])

    def endogenous(self) -> list[int]:
        return [j for j in range(len(self.latents)) if self.path[:, j].any()]
