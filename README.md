# OpenPLS

Implémentation **libre et open source** du PLS-SEM (*Partial Least Squares Structural Equation Modeling*) en Python : une alternative gratuite aux logiciels commerciaux pour estimer des modèles d'équations structurelles par moindres carrés partiels.

Le code est une **réimplémentation indépendante, écrite à partir de la littérature scientifique publiée**. Il ne contient aucun code, fichier ni ressource d'un logiciel propriétaire.

## Fonctionnalités (v0.1)

| | |
|---|---|
| Algorithme PLS | Wold / Lohmöller, schémas *path*, *factorial*, *centroid* |
| Modèle de mesure | Mode A (réflectif) et mode B (formatif) |
| PLSc | PLS consistant (Dijkstra & Henseler 2015), corrige l'atténuation |
| Fiabilité | Alpha de Cronbach, ρ_A, ρ_c (fiabilité composite), AVE |
| Validité discriminante | HTMT, Fornell-Larcker |
| Modèle structurel | Coefficients de chemin, R², f² |
| Inférence | Bootstrap : SE, t, p-values, IC percentiles |

## Installation

```bash
git clone https://github.com/<ton-compte>/openpls.git
cd openpls
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
```

## Utilisation

```python
import pandas as pd
from openpls import Model, fit, bootstrap

data = pd.read_csv("mes_donnees.csv")   # une colonne par indicateur

model = Model(
    measurement={
        "Image":        ["img1", "img2", "img3"],
        "Satisfaction": ["sat1", "sat2", "sat3"],
        "Fidelite":     ["fid1", "fid2", "fid3"],
    },
    structural=[("Image", "Satisfaction"), ("Satisfaction", "Fidelite")],
    modes={"Image": "A"},          # facultatif, "A" par défaut
)

res = fit(data, model)                    # PLS classique
# res = fit(data, model, consistent=True) # PLSc
print(res.summary())
print(bootstrap(data, model, n_boot=5000))
```

Démo sur données simulées : `python examples/demo.py` (ou `python examples/demo.py ton_fichier.csv`).

## Validation

- `pytest` : les tests vérifient que les scores sont un **point fixe exact** des équations PLS, que l'atténuation correspond à la théorie, que **PLSc retrouve les vrais coefficients** d'un modèle simulé, et que le bootstrap fonctionne.
- `python tests/crosscheck_plspm.py` : compare avec la bibliothèque indépendante [`plspm`](https://pypi.org/project/plspm/) (nécessite `pandas<3`).

## Feuille de route

- [ ] Lecture des valeurs manquantes (moyenne, suppression)
- [ ] Effets indirects / médiation avec bootstrap
- [ ] PLSpredict, Q²
- [ ] Analyse multigroupe (MGA), MICOM
- [ ] Interface graphique (dessin du modèle) — ex. web avec Streamlit ou application desktop

## Références

- Wold, H. (1982). *Soft modeling: the basic design and some extensions.*
- Lohmöller, J.-B. (1989). *Latent Variable Path Modeling with Partial Least Squares.* Physica.
- Dijkstra, T. K. & Henseler, J. (2015). Consistent partial least squares path modeling. *MIS Quarterly*, 39(2).
- Henseler, J., Ringle, C. M. & Sarstedt, M. (2015). A new criterion for assessing discriminant validity. *JAMS*, 43.
- Hair, J. F. et al. (2022). *A Primer on Partial Least Squares Structural Equation Modeling (PLS-SEM)*, 3e éd.

## Licence

MIT — voir [LICENSE](LICENSE).
