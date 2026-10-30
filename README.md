# OpenPLS

Implémentation **libre et open source** du PLS-SEM (*Partial Least Squares Structural Equation Modeling*) en Python : une alternative gratuite aux logiciels commerciaux pour estimer des modèles d'équations structurelles par moindres carrés partiels.

Le code est une **réimplémentation indépendante, écrite à partir de la littérature scientifique publiée**. Il ne contient aucun code, fichier ni ressource d'un logiciel propriétaire.

## Fonctionnalités (v0.3)

| | |
|---|---|
| Algorithme PLS | Wold / Lohmöller, schémas *path*, *factorial*, *centroid* |
| Modèle de mesure | Mode A (réflectif) et mode B (formatif) |
| PLSc | PLS consistant (Dijkstra & Henseler 2015), corrige l'atténuation |
| Fiabilité | Alpha de Cronbach, ρ_A, ρ_c (fiabilité composite), AVE |
| Validité discriminante | HTMT, Fornell-Larcker |
| Modèle structurel | Coefficients de chemin, R², f², effets totaux |
| Médiation | Effets indirects spécifiques (y compris en série), indirects totaux, typologie de Zhao et al. (2010) |
| Inférence | Bootstrap : SE, t, p-values, IC percentiles, sur tous les effets |
| Modération | Termes d'interaction `X:M` : deux étapes, produit des indicateurs, orthogonalisation ; pentes simples |
| Prédiction | PLSpredict (Q²_predict, RMSE, MAE vs régression linéaire), CVPAT |
| Multigroupe | MGA par permutation, PLS-MGA de Henseler, Welch ; invariance de mesure MICOM (étapes 1 à 3) |
| IPMA | Carte importance-performance, niveau latente et indicateur |
| NCA | Conditions nécessaires : plafond CE-FDH, taille d'effet d, test de permutation, tableau des goulots |
| Endogénéité | Copules gaussiennes (toutes combinaisons), contrôle de non-normalité |
| CB-SEM / CFA | Maximum de vraisemblance, χ², CFI, TLI, RMSEA (+ IC 90 %), SRMR, AIC, BIC |
| Segmentation | FIMIX-PLS, critères AIC3/AIC4/BIC/CAIC/EN |
| Interface graphique | Éditeur de modèle par glisser-déposer, diagramme en direct, toutes les analyses ci-dessus, tableaux colorés selon les seuils, export Excel |

## Installation

```bash
git clone https://github.com/<ton-compte>/openpls.git
cd openpls
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -e ".[gui]"      # ou ".[dev]" pour lancer aussi les tests
```

## Interface graphique

![Éditeur de modèle OpenPLS](docs/editeur.png)

```bash
openpls-gui
```

Le navigateur s'ouvre sur `http://localhost:8501`. Ensuite :

1. Importe ton fichier CSV ou Excel (une colonne par indicateur), ou essaie les données d'exemple (deux groupes A et B, pour tester la MGA).
2. Construis le modèle dans l'**éditeur visuel** :
   - glisse les indicateurs sur une variable latente, ou sur le fond pour en créer une ;
   - tire la poignée bleue d'une variable vers une autre pour créer un chemin ;
   - clique sur une variable pour la renommer ou la passer en formatif ;
   - clique sur un chemin pour lui ajouter un modérateur.

   Termine par **Appliquer au modèle**. Tu peux aussi écrire directement la syntaxe dans l'onglet *Syntaxe*.
3. **Estimer le modèle**, puis **Lancer le bootstrap** dans l'onglet *Bootstrap & médiation*.
4. L'onglet *Analyses avancées* regroupe PLSpredict/CVPAT, MGA/MICOM, IPMA, NCA, endogénéité, CB-SEM/CFA et FIMIX-PLS.
5. Exporte tous les résultats en Excel depuis la barre latérale.

![Analyse multigroupe et MICOM](docs/mga.png)

## Syntaxe du modèle

Inspirée de lavaan, elle fonctionne aussi bien dans l'interface qu'en Python :

```
Image        =~ img1 + img2 + img3        # réflectif (mode A)
Prix         <~ prix1 + prix2             # formatif (mode B)
Satisfaction =~ sat1 + sat2 + sat3
Fidelite     =~ fid1 + fid2 + fid3

Satisfaction ~ Image + Prix               # chemins structurels : cible ~ sources
Fidelite     ~ Satisfaction + Image + Satisfaction:Image   # modération (X:M)
```

Une interaction `X:M` exige les effets simples `X` et `M` sur la même cible.

## Utilisation en Python

```python
import pandas as pd
from openpls import Model, fit, bootstrap, mediation_analysis

data = pd.read_csv("mes_donnees.csv")
model = Model.from_syntax(open("modele.txt").read())

res = fit(data, model)                    # PLS classique
# res = fit(data, model, consistent=True) # PLSc
print(res.summary())
print(bootstrap(data, model, n_boot=5000))

mediation, effets = mediation_analysis(data, model, n_boot=5000)
print(mediation)   # effet indirect, IC, effet direct, type de médiation
```

Analyses avancées :

```python
from openpls.moderation import simple_slopes
from openpls.predict import pls_predict, cvpat
from openpls.mga import mga
from openpls.ipma import ipma
from openpls.nca import nca
from openpls.endogeneity import gaussian_copula
from openpls.cbsem import fit_cbsem
from openpls.fimix import fimix

res = fit(data, model, moderation="two_stage")    # si la syntaxe contient X:M
simple_slopes(res, "Satisfaction", "Image", "Fidelite")
pls_predict(data, model, k=10, repetitions=10)    # {"indicators", "latents"}
cvpat(data, model)
mga(data[model.indicators], model, groups=data["pays"])  # comparaison, MICOM, verdict
ipma(res, data, "Fidelite", scale=(1, 7))
nca(res, "Fidelite")
gaussian_copula(res, "Fidelite")
fit_cbsem(data, model)                 # ou cfa=True
fimix(res, segments=range(1, 5))
```

Démo en ligne de commande : `python examples/demo.py` (ou `python examples/demo.py ton_fichier.csv`).

> **Médiation :** pour pouvoir distinguer une médiation totale d'une médiation partielle, le chemin direct (X → Y) doit figurer dans le modèle. Sinon, OpenPLS indique que le type de médiation est indéterminé.

## Validation

`pytest` lance 76 tests, organisés en quatre familles.

**Cœur PLS**
- Les scores sont un **point fixe exact** des équations PLS.
- L'atténuation correspond à la théorie.
- **PLSc retrouve les vrais coefficients** et les vrais effets indirects d'un modèle simulé.

**Résultats exacts**
- **Modération :** avec un indicateur unique, l'approche en deux étapes reproduit la régression OLS avec terme produit, à 10⁻¹⁰ près.
- **PLSpredict :** dans un modèle à une seule régression, PLS et LM donnent la même erreur.
- **NCA :** un exemple est calculé à la main, et un cas d = 0,5 est connu analytiquement.

**Simulations**
- **MGA :** détecte une vraie différence de chemin.
- **MICOM :** le taux de faux positifs est vérifié autour de 5 %.
- **Copules :** elles corrigent un biais d'endogénéité simulé et déclarent « non interprétable » un régresseur normal.
- **FIMIX :** retrouve deux segments avec une précision égale à celle d'un classifieur qui connaîtrait les vrais paramètres.

**Interface**
- Elle est pilotée de bout en bout, pour chaque analyse.

Deux scripts comparent aussi OpenPLS à des logiciels indépendants. Ils demandent `pandas<3` et se lancent dans un environnement séparé.
- `python tests/crosscheck_plspm.py` : comparaison avec [`plspm`](https://pypi.org/project/plspm/).
- `python tests/crosscheck_semopy.py` : comparaison du CB-SEM avec [`semopy`](https://pypi.org/project/semopy/). Le χ² est identique et les estimations concordent à 3·10⁻⁴ près.

## Feuille de route

- [x] Effets indirects / médiation avec bootstrap
- [x] Interface graphique
- [x] Modérateurs (termes d'interaction)
- [x] PLSpredict, CVPAT
- [x] Analyse multigroupe (MGA), MICOM
- [x] IPMA, NCA
- [x] Endogénéité (copules gaussiennes)
- [x] CB-SEM / CFA
- [x] FIMIX-PLS
- [x] Éditeur de modèle par glisser-déposer
- [ ] PLS-POS (segmentation orientée prédiction)
- [ ] Modèles d'ordre supérieur, MGA à plus de deux groupes
- [ ] Imputation des valeurs manquantes (aujourd'hui : suppression par liste)

## Références

- Wold, H. (1982). *Soft modeling: the basic design and some extensions.*
- Lohmöller, J.-B. (1989). *Latent Variable Path Modeling with Partial Least Squares.* Physica.
- Dijkstra, T. K. & Henseler, J. (2015). Consistent partial least squares path modeling. *MIS Quarterly*, 39(2).
- Zhao, X., Lynch, J. G. & Chen, Q. (2010). Reconsidering Baron and Kenny: Myths and truths about mediation analysis. *Journal of Consumer Research*, 37(2).
- Henseler, J., Ringle, C. M. & Sarstedt, M. (2015). A new criterion for assessing discriminant validity. *JAMS*, 43.
- Hair, J. F. et al. (2022). *A Primer on Partial Least Squares Structural Equation Modeling (PLS-SEM)*, 3e éd.
- Becker, J.-M., Ringle, C. M. & Sarstedt, M. (2018). Estimating moderating effects in PLS-SEM and PLSc-SEM. *JAMS*, 46.
- Shmueli, G. et al. (2019). Predictive model assessment in PLS-SEM: guidelines for using PLSpredict. *European Journal of Marketing*, 53(11).
- Liengaard, B. D. et al. (2021). Prediction: coveted, yet forsaken? Introducing a cross-validated predictive ability test in PLS-SEM. *Decision Sciences*, 52(2).
- Henseler, J., Ringle, C. M. & Sarstedt, M. (2016). Testing measurement invariance of composites using partial least squares. *International Marketing Review*, 33(3).
- Chin, W. W. & Dibbern, J. (2010). An introduction to a permutation based procedure for multi-group PLS analysis. In *Handbook of Partial Least Squares*.
- Ringle, C. M. & Sarstedt, M. (2016). Gain more insight from your PLS-SEM results: the importance-performance map analysis. *IMDS*, 116(9).
- Dul, J. (2016). Necessary condition analysis (NCA). *Organizational Research Methods*, 19(1).
- Park, S. & Gupta, S. (2012). Handling endogenous regressors by joint estimation using copulas. *Marketing Science*, 31(4).
- Hult, G. T. M. et al. (2018). Addressing endogeneity in international marketing applications of PLS-SEM. *Journal of International Marketing*, 26(3).
- Hahn, C. et al. (2002). Capturing customer heterogeneity using a finite mixture PLS approach. *Schmalenbach Business Review*, 54.
- Sarstedt, M. et al. (2011). Uncovering and treating unobserved heterogeneity with FIMIX-PLS: which model selection criterion provides an appropriate number of segments? *Schmalenbach Business Review*, 63.
- Hu, L. & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure analysis. *Structural Equation Modeling*, 6(1).

## Licence

MIT — voir [LICENSE](LICENSE).
