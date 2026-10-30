"""Compare OpenPLS à la bibliothèque indépendante `plspm` (pip install plspm).

python tests/crosscheck_plspm.py
"""
import numpy as np
import pandas as pd
import plspm.config as c
from plspm.mode import Mode
from plspm.plspm import Plspm
from plspm.scheme import Scheme

from openpls import Model, fit
from openpls.simulate import simulate

LVS = ["XI1", "XI2", "ETA1", "ETA2"]
PATHS = [("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2")]
MEAS = {lv: [f"{lv.lower()}_{k}" for k in (1, 2, 3)] for lv in LVS}

data = simulate(n=500, seed=7)

# plspm attend une matrice triangulaire inférieure : path.loc[cible, source] = 1
path = pd.DataFrame(0, index=LVS, columns=LVS)
for s, d in PATHS:
    path.loc[d, s] = 1

worst = 0.0
for scheme_name, scheme in [("centroid", Scheme.CENTROID), ("factorial", Scheme.FACTORIAL), ("path", Scheme.PATH)]:
    for modeB in (False, True):
        cfg = c.Config(path, scaled=True)
        for lv in LVS:
            mode = Mode.B if (modeB and lv == "XI1") else Mode.A
            cfg.add_lv(lv, mode, *[c.MV(m) for m in MEAS[lv]])
        ref = Plspm(data, cfg, scheme, iterations=500, tolerance=1e-10)
        ref_paths = ref.path_coefficients()
        ref_load = ref.outer_model()["loading"]

        ours = fit(data, Model(MEAS, PATHS, modes={"XI1": "B"} if modeB else {}), scheme=scheme_name, tol=1e-10)
        d_path = max(abs(ours.path_coefficients.loc[s, d] - ref_paths.loc[d, s]) for s, d in PATHS)
        d_load = max(abs(ours.outer_loadings[lv][m] - ref_load[m]) for lv in LVS for m in MEAS[lv])
        worst = max(worst, d_path, d_load)
        tag = f"{scheme_name:<9} XI1 mode {'B' if modeB else 'A'}"
        print(f"{tag}  écart max chemins = {d_path:.2e}   chargements = {d_load:.2e}")

print(f"\nÉcart maximal global : {worst:.2e}")
# plspm s'arrête un peu avant le vrai point fixe (critère calculé sur des poids non normalisés) :
# ses scores violent les équations PLS d'environ 1e-4, ceux d'OpenPLS d'environ 0
# (voir test_fixed_point dans test_core.py). D'où une tolérance de 2e-2 sur les chargements.
assert worst < 2e-2, "Divergence avec plspm"
print("OK — OpenPLS concorde avec plspm (aux imprécisions de convergence de plspm près).")
