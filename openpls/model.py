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
    interactions: [(X, M, cible), ...]  — effets de modération X × M -> cible
    """

    measurement: dict[str, list[str]]
    structural: list[tuple[str, str]]
    modes: dict[str, str] = field(default_factory=dict)
    interactions: list[tuple[str, str, str]] = field(default_factory=list)

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

        for a, b, dst in self.interactions:
            for lv in (a, b, dst):
                if lv not in idx:
                    raise ValueError(f"Interaction {a}:{b} -> {dst} : variable latente inconnue {lv}")
            if a == b:
                raise ValueError(f"Interaction {a}:{b} : il faut deux variables différentes")
            missing = [lv for lv in (a, b) if (lv, dst) not in self.structural]
            if missing:
                raise ValueError(f"Interaction {a}:{b} -> {dst} : ajoute aussi les effets simples "
                                 f"({dst} ~ {' + '.join(missing)})")

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

    # ------------------------------------------------------------------ syntaxe
    @classmethod
    def from_syntax(cls, text: str) -> "Model":
        """Construit un modèle à partir d'une syntaxe inspirée de lavaan :

            Image        =~ img1 + img2 + img3     # réflectif (mode A)
            Prix         <~ prix1 + prix2          # formatif (mode B)
            Satisfaction ~  Image + Prix           # chemins structurels
            Fidelite     ~  Satisfaction + Prix + Satisfaction:Prix   # modération
        """
        measurement: dict[str, list[str]] = {}
        modes: dict[str, str] = {}
        structural: list[tuple[str, str]] = []
        interactions: list[tuple[str, str, str]] = []
        for no, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            for op, mode in (("=~", "A"), ("<~", "B"), ("~", None)):
                if op in line:
                    lhs, rhs = (s.strip() for s in line.split(op, 1))
                    break
            else:
                raise ValueError(f"Ligne {no} : opérateur manquant (=~, <~ ou ~) : {raw!r}")
            terms = [t.strip() for t in rhs.split("+") if t.strip()]
            if not lhs or not terms or not lhs.replace("_", "").replace(".", "").isalnum():
                raise ValueError(f"Ligne {no} : syntaxe invalide : {raw!r}")
            if mode:
                if lhs in measurement:
                    raise ValueError(f"Ligne {no} : {lhs} est déjà défini")
                measurement[lhs] = terms
                modes[lhs] = mode
            else:
                for t in terms:
                    if ":" in t:
                        parts = [p.strip() for p in t.split(":")]
                        if len(parts) != 2 or not all(parts):
                            raise ValueError(f"Ligne {no} : interaction invalide {t!r} (forme attendue X:M)")
                        interactions.append((parts[0], parts[1], lhs))
                    else:
                        structural.append((t, lhs))
        if not measurement:
            raise ValueError("Aucune variable latente définie (utilise =~ ou <~)")
        return cls(measurement, structural, modes, interactions)

    def to_syntax(self) -> str:
        lines = ["# Modèle de mesure"]
        width = max(len(lv) for lv in self.latents)
        for lv in self.latents:
            op = "=~" if self.modes[lv] == "A" else "<~"
            lines.append(f"{lv:<{width}} {op} " + " + ".join(self.measurement[lv]))
        lines.append("\n# Modèle structurel")
        for j, lv in enumerate(self.latents):
            pred = self.predecessors(j)
            terms = [self.latents[i] for i in pred] + [f"{a}:{b}" for a, b, d in self.interactions if d == lv]
            if terms:
                lines.append(f"{lv:<{width}} ~  " + " + ".join(terms))
        return "\n".join(lines)

    def without_interactions(self) -> "Model":
        return Model(self.measurement, list(self.structural), dict(self.modes))

    @property
    def indicators(self) -> list[str]:
        return [ind for lv in self.latents for ind in self.measurement[lv]]

    def predecessors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[:, j])

    def successors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[j, :])

    def endogenous(self) -> list[int]:
        return [j for j in range(len(self.latents)) if self.path[:, j].any()]
