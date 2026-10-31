"""Contenu de l'onglet Aide, par rubrique, en français et en anglais."""
from __future__ import annotations

FR: list[tuple[str, str]] = [
("Démarrer", """
OpenPLS estime des modèles d'équations structurelles par les moindres carrés partiels (PLS-SEM), comme SmartPLS.

**Démarche conseillée**

1. **Données** : importe un fichier CSV, Excel, SPSS (.sav) ou Stata (.dta), une ligne par répondant et une colonne par indicateur. Tu peux aussi partir des données d'exemple.
2. **Modèle** : dessine le modèle dans l'éditeur visuel (ou écris la syntaxe), puis clique sur *Appliquer au modèle*.
3. **Analyses préliminaires** : vérifie les valeurs manquantes, les valeurs aberrantes, la distribution des indicateurs et la taille d'échantillon.
4. **Estimer le modèle** : OpenPLS calcule les coefficients et, si l'option est cochée, le bootstrap (t, p, intervalles de confiance).
5. **Résultats** : évalue d'abord le modèle de mesure (fiabilité, validité), puis seulement le modèle structurel.
6. **Analyses avancées** : prédiction, multigroupe, IPMA, conditions nécessaires, endogénéité, CB-SEM, segmentation.
7. **Exporter** : tableaux Excel, rapport Word, projet OpenPLS.

Les données restent sur ton ordinateur : rien n'est envoyé sur internet.
"""),
("Préparer les données", """
- **Une ligne par répondant, une colonne par indicateur.** La première ligne contient les noms des colonnes.
- **Noms d'indicateurs simples** : lettres, chiffres et `_` (par exemple `sat_1`). OpenPLS regroupe automatiquement les colonnes de même préfixe pour proposer un modèle de départ.
- **Variables de groupe** (sexe, pays…) : garde-les dans le fichier ; elles servent à l'analyse multigroupe et ne sont pas utilisées comme indicateurs.
- **Valeurs manquantes** : cellules vides. Choisis leur traitement dans la barre latérale (*Valeurs manquantes*) : suppression par liste (par défaut), remplacement par la moyenne, ou imputation par régression. Au-delà de 5 % de manquants sur un indicateur, signale-le dans l'article.
- **Items inversés** : recode-les avant l'import pour qu'une valeur élevée signifie toujours plus du construit.
- **CSV français** : le séparateur `;` et la virgule décimale sont reconnus automatiquement.
"""),
("Écrire la syntaxe du modèle", """
| Écriture | Signification |
|---|---|
| `SAT =~ sat1 + sat2 + sat3` | construit **réflectif** (les indicateurs reflètent le construit) |
| `IMG <~ img1 + img2` | construit **formatif** (les indicateurs forment le construit) |
| `LOY ~ SAT + IMG` | chemins structurels : SAT → LOY et IMG → LOY |
| `LOY ~ SAT + AGE + SAT:AGE` | **modération** : AGE modère l'effet de SAT sur LOY |
| `LOY ~ SAT + SAT:SAT` | **effet quadratique** (non linéaire) de SAT |
| `QUAL =~ L1 + L2 + L3` | construit **d'ordre supérieur** dont les termes sont des variables latentes |
| `LOY ~ SAT + age` | `age` (colonne du fichier) entre comme **variable de contrôle** à un seul indicateur |
| `# texte` | commentaire |

Un indicateur n'appartient qu'à un seul construit. Le modèle structurel doit être récursif (pas de boucle).
"""),
("Analyses préliminaires", """
| Analyse | Repère | Référence |
|---|---|---|
| Valeurs manquantes | < 5 % par indicateur | Hair et al. (2022) |
| Asymétrie, aplatissement | \\|asymétrie\\| < 2, \\|aplatissement\\| < 7 | Curran, West & Finch (1996) |
| Mardia | p < 0,05 : non-normalité multivariée | Mardia (1970) |
| Mahalanobis | p < 0,001 : observation aberrante | Tabachnick & Fidell (2019) |
| Harman | premier facteur < 50 % de la variance | Podsakoff et al. (2003) |
| Colinéarité complète | VIF ≤ 3,3 | Kock (2015) |
| Taille d'échantillon | n ≥ (2,486 / \\|β_min\\|)² à 5 % | Kock & Hadaya (2018) |

PLS-SEM ne suppose pas la normalité : la non-normalité est plutôt un argument pour PLS-SEM. Une valeur aberrante n'est pas forcément une erreur : vérifie-la avant de la retirer.
"""),
("Modèle de mesure réflectif", """
Évalue chaque construit réflectif avant de regarder les chemins.

| Critère | Seuil | Si le critère n'est pas atteint |
|---|---|---|
| Chargement externe | ≥ 0,708 (0,40-0,70 : à discuter) | retirer l'indicateur seulement si cela améliore l'AVE ou ρ_c et ne nuit pas à la validité de contenu |
| Alpha de Cronbach | ≥ 0,70 | borne inférieure de la fiabilité |
| ρ_A | ≥ 0,70 | fiabilité « exacte » (Dijkstra-Henseler) |
| Fiabilité composite ρ_c | 0,70 à 0,95 | > 0,95 : items redondants |
| AVE | ≥ 0,50 | le construit explique moins de la moitié de la variance de ses indicateurs |

**Comment rapporter** : « Tous les chargements dépassent 0,708, sauf X (0,65), conservé pour la validité de contenu. Les fiabilités composites vont de 0,82 à 0,91 et les AVE de 0,58 à 0,74 (Hair et al. 2022). »
"""),
("Modèle de mesure formatif", """
Les indicateurs formatifs ne sont pas interchangeables : les critères de fiabilité (α, AVE) ne s'appliquent pas.

1. **Validité convergente** (analyse de redondance) : corrélation ≥ 0,70 entre le construit formatif et une mesure globale du même concept (Cheah et al. 2018).
2. **Colinéarité** : VIF des indicateurs < 3 idéalement, < 5 au maximum.
3. **Poids** : significatif (bootstrap) → l'indicateur contribue. Non significatif mais chargement ≥ 0,50 → conserver (contribution absolue). Ni l'un ni l'autre → envisager de le retirer, en tenant compte de la validité de contenu.
"""),
("Validité discriminante", """
- **HTMT** (Henseler et al. 2015) : < 0,85 (construits conceptuellement distincts) ou < 0,90 (proches). L'intervalle de confiance bootstrap de l'HTMT ne doit pas contenir 1.
- **Fornell-Larcker** : la racine carrée de l'AVE d'un construit dépasse ses corrélations avec les autres. Ce critère détecte mal les problèmes ; préfère l'HTMT.
- **Chargements croisés** : chaque indicateur charge plus sur son construit que sur les autres.
"""),
("Modèle structurel", """
1. **Colinéarité** entre prédicteurs : VIF < 3 (idéal), < 5.
2. **Coefficients de chemin** : signe, taille, significativité (bootstrap, intervalle de confiance qui exclut 0).
3. **R²** : 0,25 faible, 0,50 moyen, 0,75 élevé (repères de marketing, à adapter au domaine).
4. **f²** : 0,02 faible, 0,15 moyen, 0,35 fort (Cohen 1988).
5. **Pouvoir prédictif** : PLSpredict (Q²_predict > 0, comparaison avec LM).

**Comment rapporter** : « SAT a un effet positif et significatif sur LOY (β = 0,42 ; t = 6,1 ; p < 0,001 ; IC 95 % [0,29 ; 0,55] ; f² = 0,21). »
"""),
("Bootstrap et significativité", """
Le bootstrap rééchantillonne les répondants (5 000 tirages recommandés pour la version finale, 1 000 pour explorer) et estime la variabilité de chaque coefficient.

- **t** = coefficient / erreur-type ; **p** bilatéral.
- **Étoiles** : \\*\\*\\* p < 0,01 ; \\*\\* p < 0,05 ; \\* p < 0,10 ; ns non significatif.
- **Intervalles** : percentile (par défaut) ou **BCa** (corrigé du biais et de l'asymétrie, recommandé pour les effets indirects). Un effet est significatif si l'intervalle exclut 0.
- **Différence entre deux coefficients** : l'onglet Significativité teste si deux chemins diffèrent (intervalle bootstrap de la différence).

Le bootstrap n'est pas obligatoire : sans lui, on obtient les coefficients mais pas leur significativité.
"""),
("Médiation", """
Typologie de Zhao, Lynch & Chen (2010), à partir de l'effet indirect (a × b) et de l'effet direct (c') :

| Effet indirect | Effet direct | Type |
|---|---|---|
| significatif | non significatif | médiation indirecte seule (totale) |
| significatif | significatif, même signe | médiation complémentaire (partielle) |
| significatif | significatif, signe opposé | médiation compétitive (partielle) |
| non significatif | significatif | effet direct seul, pas de médiation |
| non significatif | non significatif | aucun effet |

Le chemin direct doit figurer dans le modèle pour distinguer médiation totale et partielle. N'utilise pas le test de Sobel.
"""),
("Modération et médiation modérée", """
- **Syntaxe** : `Y ~ X + M + X:M`.
- **Méthode** : deux étapes (recommandée, Becker et al. 2018), produit des indicateurs ou orthogonalisation.
- **Interprétation** : le coefficient de `X:M` indique de combien l'effet de X sur Y change quand M augmente d'un écart-type. Les pentes simples (M à -1, 0, +1 écart-type) et le graphique aident à l'expliquer.
- **f² de l'interaction** : 0,005 faible, 0,01 moyen, 0,025 fort (Kenny 2018).
- **Médiation modérée** : si le modèle contient X → Me → Y et une interaction sur l'un de ces chemins, l'onglet Significativité donne l'**indice de médiation modérée** (Hayes 2015) et les effets indirects conditionnels. L'indice significatif (IC qui exclut 0) montre que l'effet indirect dépend du modérateur.
- **Effet quadratique** : `Y ~ X + X:X` teste une relation en U ou en U inversé.
"""),
("Construits d'ordre supérieur", """
- **Syntaxe** : `QUAL =~ L1 + L2 + L3` où L1, L2, L3 sont des construits d'ordre 1.
- **Approches** : deux étapes disjointe (recommandée), deux étapes intégrée, indicateurs répétés.
- **Évaluation** : les construits d'ordre 1 se jugent comme d'habitude ; les relations entre l'ordre supérieur et ses composantes se jugent comme des chargements (réflectif) ou des poids et VIF (formatif) (Sarstedt et al. 2019).
"""),
("Prédiction : PLSpredict et CVPAT", """
- **Q²_predict > 0** : le modèle prédit mieux que la moyenne.
- **Comparaison avec LM** (régression linéaire des indicateurs) sur le RMSE ou le MAE : PLS meilleur sur tous les indicateurs → pouvoir prédictif élevé ; sur la majorité → moyen ; sur une minorité → faible ; sur aucun → nul (Shmueli et al. 2019).
- **CVPAT** (Liengaard et al. 2021) : test de la perte prédictive moyenne face à la moyenne des indicateurs (IA) et à LM ; différence < 0 et p < 0,05 → PLS prédit significativement mieux.
"""),
("Multigroupe : MGA et MICOM", """
1. **MICOM** (Henseler et al. 2016) : étape 1 (même configuration, automatique), étape 2 (invariance compositionnelle, test de permutation), étape 3 (égalité des moyennes et des variances).
   - Étapes 2 et 3 validées → invariance totale : on peut regrouper les données.
   - Étape 2 seule → invariance partielle : la comparaison des chemins est légitime.
   - Étape 2 rejetée → interprète la MGA avec prudence.
2. **MGA** : le test de permutation (Chin & Dibbern 2010) est recommandé. Avec plus de deux groupes : test omnibus puis comparaisons deux à deux corrigées par Holm.
"""),
("IPMA", """
L'analyse importance-performance croise l'**importance** (effet total non standardisé sur la cible) et la **performance** (score moyen rapporté à 0-100). Les construits en bas à droite de la carte (importants mais peu performants) sont les priorités d'action (Ringle & Sarstedt 2016). Les indicateurs doivent être sur la même échelle et avoir des poids positifs.
"""),
("Conditions nécessaires : NCA", """
La NCA (Dul 2016) vérifie si un niveau minimal d'un antécédent est **indispensable** pour atteindre un niveau donné de la cible, ce que la régression ne montre pas.

- **Taille d'effet d** : 0-0,1 faible, 0,1-0,3 moyen, 0,3-0,5 fort, ≥ 0,5 très fort.
- **Condition nécessaire** si d ≥ 0,1 et p < 0,05 (test de permutation).
- Le tableau des goulots indique le niveau minimal de l'antécédent requis pour chaque niveau de la cible (Richter et al. 2020).
"""),
("Endogénéité : copules gaussiennes", """
Un prédicteur corrélé au terme d'erreur (variable omise, causalité inverse) biaise les coefficients. La méthode des copules gaussiennes (Park & Gupta 2012 ; Hult et al. 2018) ajoute un terme de copule pour chaque prédicteur :

- terme **significatif** → endogénéité probable ;
- la copule n'est identifiée que si le prédicteur est **non normal** (Shapiro-Wilk p < 0,05) ; sinon le test n'est pas interprétable.
"""),
("CB-SEM et CFA", """
Estimation par maximum de vraisemblance d'un modèle de facteurs communs, utile pour confirmer une structure de mesure ou comparer avec PLS-SEM.

| Indice | Bon ajustement (Hu & Bentler 1999) |
|---|---|
| CFI, TLI | ≥ 0,95 |
| RMSEA | ≤ 0,06 |
| SRMR | ≤ 0,08 |

Le χ² est presque toujours significatif sur de grands échantillons : interprète-le avec les autres indices.
"""),
("Segmentation : FIMIX-PLS", """
FIMIX-PLS cherche des **segments cachés** de répondants dont les chemins structurels diffèrent (hétérogénéité non observée).

- Choisis le nombre de segments quand **AIC3 et CAIC** s'accordent (Sarstedt et al. 2011) ; EN > 0,5 indique des segments bien séparés.
- Un segment de moins de 5 % de l'échantillon est rarement interprétable.
- Cherche ensuite à expliquer les segments par des variables observées (âge, pays…) puis fais une MGA.
"""),
("Comparer des modèles", """
L'onglet *Analyses avancées → Comparaison de modèles* estime plusieurs modèles concurrents sur les mêmes données et compare leurs critères d'information pour une cible donnée (Sharma et al. 2019, 2021) :

- **BIC** et **GM** (Geweke-Meese) : retiens le modèle de valeur la plus faible ;
- les **poids d'Akaike/BIC** donnent la probabilité relative de chaque modèle.

Les modèles comparés doivent expliquer la même variable cible avec les mêmes données.
"""),
("Analyse tétrade confirmatoire (CTA-PLS)", """
La CTA-PLS (Gudergan et al. 2008) aide à choisir entre mesure **réflective** et **formative**. Pour un bloc d'au moins 4 indicateurs, elle teste les tétrades (différences de produits de covariances) :

- si toutes les tétrades non redondantes valent 0 (intervalles corrigés par Bonferroni qui contiennent 0) → le modèle **réflectif** est compatible avec les données ;
- si au moins une tétrade diffère de 0 → le modèle réflectif est rejeté, une mesure **formative** est plus plausible.

Le choix doit avant tout reposer sur la théorie.
"""),
("Rédiger les résultats", """
**Ordre de présentation** (Hair et al. 2022) :

1. Échantillon, données manquantes, logiciel et réglages (OpenPLS, schéma path, bootstrap à 5 000 tirages, intervalles BCa).
2. Modèle de mesure : chargements, fiabilité, AVE, HTMT.
3. Modèle structurel : VIF, chemins (β, t, p, IC), R², f², Q²_predict.
4. Analyses complémentaires : médiation, modération, MGA…

**Rapport Word** : *Exporter → Rapport (Word)* produit les tableaux au format APA et un paragraphe de méthode prêt à adapter.

**Citer OpenPLS** : voir *À propos d'OpenPLS*.

**Références principales**
- Hair, J. F., Hult, G. T. M., Ringle, C. M., & Sarstedt, M. (2022). *A primer on partial least squares structural equation modeling (PLS-SEM)* (3e éd.). Sage.
- Henseler, J., Ringle, C. M., & Sarstedt, M. (2015). A new criterion for assessing discriminant validity. *JAMS*, 43(1), 115-135.
- Shmueli, G., et al. (2019). Predictive model assessment in PLS-SEM. *European Journal of Marketing*, 53(11), 2322-2347.
- Zhao, X., Lynch, J. G., & Chen, Q. (2010). Reconsidering Baron and Kenny. *Journal of Consumer Research*, 37(2), 197-206.
"""),
]

EN: list[tuple[str, str]] = [
("Getting started", """
OpenPLS estimates structural equation models by partial least squares (PLS-SEM), like SmartPLS.

**Recommended workflow**

1. **Data**: import a CSV, Excel, SPSS (.sav) or Stata (.dta) file, one row per respondent and one column per indicator. You can also start from the example data.
2. **Model**: draw the model in the visual editor (or write the syntax), then click *Apply to model*.
3. **Preliminary analyses**: check missing values, outliers, indicator distributions and sample size.
4. **Estimate the model**: OpenPLS computes the coefficients and, if the option is ticked, the bootstrap (t, p, confidence intervals).
5. **Results**: assess the measurement model first (reliability, validity), and only then the structural model.
6. **Advanced analyses**: prediction, multigroup, IPMA, necessary conditions, endogeneity, CB-SEM, segmentation.
7. **Export**: Excel tables, Word report, OpenPLS project.

Your data stays on your computer: nothing is sent over the internet.
"""),
("Preparing the data", """
- **One row per respondent, one column per indicator.** The first row holds the column names.
- **Simple indicator names**: letters, digits and `_` (e.g. `sat_1`). OpenPLS groups columns with the same prefix to suggest a starting model.
- **Group variables** (gender, country…): keep them in the file; they are used for multigroup analysis, not as indicators.
- **Missing values**: empty cells. Choose how to handle them in the sidebar (*Missing values*): listwise deletion (default), mean replacement, or regression imputation. Report any indicator with more than 5% missing values.
- **Reverse-coded items**: recode them before import so that a high value always means more of the construct.
- **European CSV**: the `;` separator and decimal comma are detected automatically.
"""),
("Writing the model syntax", """
| Syntax | Meaning |
|---|---|
| `SAT =~ sat1 + sat2 + sat3` | **reflective** construct (indicators reflect the construct) |
| `IMG <~ img1 + img2` | **formative** construct (indicators form the construct) |
| `LOY ~ SAT + IMG` | structural paths: SAT → LOY and IMG → LOY |
| `LOY ~ SAT + AGE + SAT:AGE` | **moderation**: AGE moderates the effect of SAT on LOY |
| `LOY ~ SAT + SAT:SAT` | **quadratic** (non-linear) effect of SAT |
| `QUAL =~ L1 + L2 + L3` | **higher-order** construct whose terms are latent variables |
| `LOY ~ SAT + age` | `age` (a file column) enters as a single-indicator **control variable** |
| `# text` | comment |

An indicator belongs to one construct only. The structural model must be recursive (no loop).
"""),
("Preliminary analyses", """
| Analysis | Benchmark | Reference |
|---|---|---|
| Missing values | < 5% per indicator | Hair et al. (2022) |
| Skewness, kurtosis | \\|skewness\\| < 2, \\|kurtosis\\| < 7 | Curran, West & Finch (1996) |
| Mardia | p < 0.05: multivariate non-normality | Mardia (1970) |
| Mahalanobis | p < 0.001: outlier | Tabachnick & Fidell (2019) |
| Harman | first factor < 50% of variance | Podsakoff et al. (2003) |
| Full collinearity | VIF ≤ 3.3 | Kock (2015) |
| Sample size | n ≥ (2.486 / \\|β_min\\|)² at 5% | Kock & Hadaya (2018) |

PLS-SEM does not assume normality: non-normality is rather an argument for PLS-SEM. An outlier is not necessarily an error: check it before removing it.
"""),
("Reflective measurement model", """
Assess every reflective construct before looking at the paths.

| Criterion | Threshold | If not met |
|---|---|---|
| Outer loading | ≥ 0.708 (0.40-0.70: discuss) | remove the indicator only if it improves AVE or ρ_c without hurting content validity |
| Cronbach's alpha | ≥ 0.70 | lower bound of reliability |
| ρ_A | ≥ 0.70 | "exact" reliability (Dijkstra-Henseler) |
| Composite reliability ρ_c | 0.70 to 0.95 | > 0.95: redundant items |
| AVE | ≥ 0.50 | the construct explains less than half of its indicators' variance |

**How to report**: "All loadings exceed 0.708 except X (0.65), retained for content validity. Composite reliabilities range from 0.82 to 0.91 and AVEs from 0.58 to 0.74 (Hair et al. 2022)."
"""),
("Formative measurement model", """
Formative indicators are not interchangeable: reliability criteria (α, AVE) do not apply.

1. **Convergent validity** (redundancy analysis): correlation ≥ 0.70 between the formative construct and a global measure of the same concept (Cheah et al. 2018).
2. **Collinearity**: indicator VIF ideally < 3, at most < 5.
3. **Weights**: significant (bootstrap) → the indicator contributes. Not significant but loading ≥ 0.50 → keep it (absolute contribution). Neither → consider removing it, keeping content validity in mind.
"""),
("Discriminant validity", """
- **HTMT** (Henseler et al. 2015): < 0.85 (conceptually distinct constructs) or < 0.90 (similar ones). The bootstrap confidence interval of HTMT must not include 1.
- **Fornell-Larcker**: the square root of a construct's AVE exceeds its correlations with other constructs. This criterion detects problems poorly; prefer HTMT.
- **Cross-loadings**: each indicator loads more on its own construct than on the others.
"""),
("Structural model", """
1. **Collinearity** among predictors: VIF < 3 (ideal), < 5.
2. **Path coefficients**: sign, size, significance (bootstrap, confidence interval excluding 0).
3. **R²**: 0.25 weak, 0.50 moderate, 0.75 substantial (marketing benchmarks, adapt to your field).
4. **f²**: 0.02 small, 0.15 medium, 0.35 large (Cohen 1988).
5. **Predictive power**: PLSpredict (Q²_predict > 0, comparison with LM).

**How to report**: "SAT has a positive and significant effect on LOY (β = 0.42; t = 6.1; p < 0.001; 95% CI [0.29; 0.55]; f² = 0.21)."
"""),
("Bootstrap and significance", """
The bootstrap resamples respondents (5,000 draws recommended for the final version, 1,000 to explore) and estimates the variability of each coefficient.

- **t** = coefficient / standard error; two-tailed **p**.
- **Stars**: \\*\\*\\* p < 0.01; \\*\\* p < 0.05; \\* p < 0.10; ns not significant.
- **Intervals**: percentile (default) or **BCa** (bias-corrected and accelerated, recommended for indirect effects). An effect is significant if its interval excludes 0.
- **Difference between two coefficients**: the Significance tab tests whether two paths differ (bootstrap interval of the difference).

The bootstrap is optional: without it you get the coefficients but not their significance.
"""),
("Mediation", """
Typology of Zhao, Lynch & Chen (2010), based on the indirect effect (a × b) and the direct effect (c'):

| Indirect effect | Direct effect | Type |
|---|---|---|
| significant | not significant | indirect-only (full) mediation |
| significant | significant, same sign | complementary (partial) mediation |
| significant | significant, opposite sign | competitive (partial) mediation |
| not significant | significant | direct-only, no mediation |
| not significant | not significant | no effect |

The direct path must be in the model to tell full from partial mediation. Do not use the Sobel test.
"""),
("Moderation and moderated mediation", """
- **Syntax**: `Y ~ X + M + X:M`.
- **Method**: two-stage (recommended, Becker et al. 2018), product indicator or orthogonalization.
- **Interpretation**: the `X:M` coefficient tells how much the effect of X on Y changes when M increases by one standard deviation. Simple slopes (M at -1, 0, +1 SD) and the chart help explain it.
- **f² of the interaction**: 0.005 small, 0.01 medium, 0.025 large (Kenny 2018).
- **Moderated mediation**: if the model contains X → Me → Y and an interaction on one of those paths, the Significance tab gives the **index of moderated mediation** (Hayes 2015) and the conditional indirect effects. A significant index (CI excluding 0) shows that the indirect effect depends on the moderator.
- **Quadratic effect**: `Y ~ X + X:X` tests a U-shaped or inverted-U relationship.
"""),
("Higher-order constructs", """
- **Syntax**: `QUAL =~ L1 + L2 + L3` where L1, L2, L3 are first-order constructs.
- **Approaches**: two-stage disjoint (recommended), two-stage embedded, repeated indicators.
- **Assessment**: first-order constructs are assessed as usual; relationships between the higher-order construct and its components are assessed as loadings (reflective) or weights and VIF (formative) (Sarstedt et al. 2019).
"""),
("Prediction: PLSpredict and CVPAT", """
- **Q²_predict > 0**: the model predicts better than the mean.
- **Comparison with LM** (linear regression of the indicators) on RMSE or MAE: PLS better on all indicators → high predictive power; on the majority → medium; on a minority → low; on none → no predictive power (Shmueli et al. 2019).
- **CVPAT** (Liengaard et al. 2021): tests the average predictive loss against the indicator average (IA) and LM; difference < 0 and p < 0.05 → PLS predicts significantly better.
"""),
("Multigroup: MGA and MICOM", """
1. **MICOM** (Henseler et al. 2016): step 1 (configural, automatic), step 2 (compositional invariance, permutation test), step 3 (equal means and variances).
   - Steps 2 and 3 met → full invariance: data can be pooled.
   - Step 2 only → partial invariance: comparing paths is legitimate.
   - Step 2 rejected → interpret the MGA with caution.
2. **MGA**: the permutation test (Chin & Dibbern 2010) is recommended. With more than two groups: omnibus test, then Holm-corrected pairwise comparisons.
"""),
("IPMA", """
Importance-performance map analysis crosses **importance** (unstandardized total effect on the target) with **performance** (mean score rescaled to 0-100). Constructs in the bottom right of the map (important but performing poorly) are action priorities (Ringle & Sarstedt 2016). Indicators must share the same scale and have positive weights.
"""),
("Necessary conditions: NCA", """
NCA (Dul 2016) checks whether a minimum level of an antecedent is **required** to reach a given level of the target, which regression does not show.

- **Effect size d**: 0-0.1 small, 0.1-0.3 medium, 0.3-0.5 large, ≥ 0.5 very large.
- **Necessary condition** if d ≥ 0.1 and p < 0.05 (permutation test).
- The bottleneck table shows the minimum antecedent level required for each target level (Richter et al. 2020).
"""),
("Endogeneity: Gaussian copulas", """
A predictor correlated with the error term (omitted variable, reverse causality) biases the coefficients. The Gaussian copula approach (Park & Gupta 2012; Hult et al. 2018) adds a copula term for each predictor:

- **significant** term → endogeneity is likely;
- the copula is identified only if the predictor is **non-normal** (Shapiro-Wilk p < 0.05); otherwise the test cannot be interpreted.
"""),
("CB-SEM and CFA", """
Maximum likelihood estimation of a common factor model, useful to confirm a measurement structure or compare with PLS-SEM.

| Index | Good fit (Hu & Bentler 1999) |
|---|---|
| CFI, TLI | ≥ 0.95 |
| RMSEA | ≤ 0.06 |
| SRMR | ≤ 0.08 |

χ² is almost always significant in large samples: read it together with the other indices.
"""),
("Segmentation: FIMIX-PLS", """
FIMIX-PLS looks for **hidden segments** of respondents whose structural paths differ (unobserved heterogeneity).

- Choose the number of segments where **AIC3 and CAIC** agree (Sarstedt et al. 2011); EN > 0.5 indicates well-separated segments.
- A segment smaller than 5% of the sample is rarely interpretable.
- Then try to explain the segments with observed variables (age, country…) and run an MGA.
"""),
("Comparing models", """
*Advanced analyses → Model comparison* estimates several competing models on the same data and compares their information criteria for a given target (Sharma et al. 2019, 2021):

- **BIC** and **GM** (Geweke-Meese): retain the model with the lowest value;
- **Akaike/BIC weights** give each model's relative probability.

The compared models must explain the same target variable with the same data.
"""),
("Confirmatory tetrad analysis (CTA-PLS)", """
CTA-PLS (Gudergan et al. 2008) helps choose between **reflective** and **formative** measurement. For a block of at least 4 indicators, it tests the tetrads (differences of covariance products):

- if all non-redundant tetrads equal 0 (Bonferroni-adjusted intervals containing 0) → the **reflective** model is consistent with the data;
- if at least one tetrad differs from 0 → the reflective model is rejected; **formative** measurement is more plausible.

The choice should rest primarily on theory.
"""),
("Reporting the results", """
**Order of presentation** (Hair et al. 2022):

1. Sample, missing data, software and settings (OpenPLS, path scheme, 5,000 bootstrap draws, BCa intervals).
2. Measurement model: loadings, reliability, AVE, HTMT.
3. Structural model: VIF, paths (β, t, p, CI), R², f², Q²_predict.
4. Further analyses: mediation, moderation, MGA…

**Word report**: *Export → Report (Word)* produces APA-style tables and a method paragraph ready to adapt.

**Citing OpenPLS**: see *About OpenPLS*.

**Key references**
- Hair, J. F., Hult, G. T. M., Ringle, C. M., & Sarstedt, M. (2022). *A primer on partial least squares structural equation modeling (PLS-SEM)* (3rd ed.). Sage.
- Henseler, J., Ringle, C. M., & Sarstedt, M. (2015). A new criterion for assessing discriminant validity. *JAMS*, 43(1), 115-135.
- Shmueli, G., et al. (2019). Predictive model assessment in PLS-SEM. *European Journal of Marketing*, 53(11), 2322-2347.
- Zhao, X., Lynch, J. G., & Chen, Q. (2010). Reconsidering Baron and Kenny. *Journal of Consumer Research*, 37(2), 197-206.
"""),
]

HELP = {"fr": FR, "en": EN}
