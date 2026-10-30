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
    higher_order: {construit_ordre_sup: [composantes d'ordre 1]}  — modèles de second ordre
    """

    measurement: dict[str, list[str]]
    structural: list[tuple[str, str]]
    modes: dict[str, str] = field(default_factory=dict)
    interactions: list[tuple[str, str, str]] = field(default_factory=list)
    higher_order: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.latents: list[str] = list(self.measurement) + [h for h in self.higher_order if h not in self.measurement]
        idx = {lv: i for i, lv in enumerate(self.latents)}
        seen: dict[str, str] = {}
        for lv, inds in self.measurement.items():
            for ind in inds:
                if ind in seen:
                    where = "deux fois dans " + lv if seen[ind] == lv else f"dans {seen[ind]} et dans {lv}"
                    raise ValueError(f"L'indicateur {ind} apparaît {where} : un indicateur ne peut mesurer "
                                     "qu'un seul construit (pour un construit d'ordre supérieur, utilise "
                                     "la syntaxe HOC =~ LV1 + LV2)")
                seen[ind] = lv
        owner: dict[str, str] = {}
        for hoc, locs in self.higher_order.items():
            if hoc in self.measurement:
                raise ValueError(f"{hoc} ne peut pas avoir à la fois des indicateurs et des composantes")
            if len(locs) < 2:
                raise ValueError(f"Le construit d'ordre supérieur {hoc} doit avoir au moins 2 composantes")
            for loc in locs:
                if loc not in self.measurement:
                    raise ValueError(f"{hoc} : la composante {loc} doit être une variable latente d'ordre 1 "
                                     "(les modèles de troisième ordre ne sont pas pris en charge)")
                if loc in owner:
                    raise ValueError(f"{loc} est composante de deux construits ({owner[loc]} et {hoc})")
                owner[loc] = hoc
        for src, dst in self.structural:
            for lv in (src, dst):
                if lv in owner:
                    raise ValueError(f"Chemin {src} -> {dst} : {lv} est une composante de {owner[lv]} ; "
                                     f"relie plutôt {owner[lv]} aux autres construits")
        for a, b, dst in self.interactions:
            if any(lv in self.higher_order or lv in owner for lv in (a, b, dst)):
                raise ValueError("Les interactions impliquant un construit d'ordre supérieur ou ses composantes "
                                 "ne sont pas prises en charge")
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
            if lv in self.measurement and not self.measurement[lv]:
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
        blocks: dict[str, list[str]] = {}
        modes: dict[str, str] = {}
        lines_of: dict[str, int] = {}
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
                if lhs in blocks:
                    raise ValueError(f"Ligne {no} : {lhs} est déjà défini")
                blocks[lhs] = terms
                modes[lhs] = mode
                lines_of[lhs] = no
            else:
                for t in terms:
                    if ":" in t:
                        parts = [p.strip() for p in t.split(":")]
                        if len(parts) != 2 or not all(parts):
                            raise ValueError(f"Ligne {no} : interaction invalide {t!r} (forme attendue X:M)")
                        interactions.append((parts[0], parts[1], lhs))
                    else:
                        structural.append((t, lhs))
        if not blocks:
            raise ValueError("Aucune variable latente définie (utilise =~ ou <~)")
        # un bloc dont les termes sont tous des variables latentes = construit d'ordre supérieur
        measurement, higher = {}, {}
        for lv, terms in blocks.items():
            n_lat = sum(t in blocks for t in terms)
            if n_lat == len(terms):
                higher[lv] = terms
            elif n_lat:
                raise ValueError(f"Ligne {lines_of[lv]} : {lv} mélange indicateurs et variables latentes")
            else:
                measurement[lv] = terms
        return cls(measurement, structural, modes, interactions, higher)

    def to_syntax(self) -> str:
        lines = ["# Modèle de mesure"]
        width = max(len(lv) for lv in self.latents)
        for lv in self.latents:
            op = "=~" if self.modes[lv] == "A" else "<~"
            terms = self.measurement[lv] if lv in self.measurement else self.higher_order[lv]
            lines.append(f"{lv:<{width}} {op} " + " + ".join(terms))
        lines.append("\n# Modèle structurel")
        for j, lv in enumerate(self.latents):
            pred = self.predecessors(j)
            terms = [self.latents[i] for i in pred] + [f"{a}:{b}" for a, b, d in self.interactions if d == lv]
            if terms:
                lines.append(f"{lv:<{width}} ~  " + " + ".join(terms))
        return "\n".join(lines)

    def without_interactions(self) -> "Model":
        return Model(self.measurement, list(self.structural), dict(self.modes), [], dict(self.higher_order))

    def components(self) -> dict[str, str]:
        """{composante: construit d'ordre supérieur}."""
        return {loc: hoc for hoc, locs in self.higher_order.items() for loc in locs}

    @property
    def indicators(self) -> list[str]:
        return [ind for lv in self.latents for ind in self.measurement.get(lv, [])]

    def predecessors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[:, j])

    def successors(self, j: int) -> np.ndarray:
        return np.flatnonzero(self.path[j, :])

    def endogenous(self) -> list[int]:
        return [j for j in range(len(self.latents)) if self.path[:, j].any()]
