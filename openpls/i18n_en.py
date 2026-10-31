"""Traduction anglaise de l'interface (clé : texte français du code)."""
from __future__ import annotations

import re

EN: dict[str, str] = {
    # navigation et barre latérale
    "Données": "Data",
    "Estimation": "Estimation",
    "Algorithme": "Algorithm",
    "Calculer t et p automatiquement": "Compute t and p automatically",
    "Échantillons bootstrap": "Bootstrap samples",
    "Modèle": "Model",
    "Analyses préliminaires": "Preliminary analyses",
    "Résultats": "Results",
    "Significativité": "Significance",
    "Analyses avancées": "Advanced analyses",
    "Aide": "Help",
    "Prédiction (PLSpredict, CVPAT)": "Prediction (PLSpredict, CVPAT)",
    "Multigroupe (MGA, MICOM)": "Multigroup (MGA, MICOM)",
    "Importance-performance (IPMA)": "Importance-performance (IPMA)",
    "Conditions nécessaires (NCA)": "Necessary conditions (NCA)",
    "Endogénéité (copules)": "Endogeneity (copulas)",
    "Segmentation (FIMIX-PLS)": "Segmentation (FIMIX-PLS)",
    "avec interaction": "with an interaction",
    "d'ordre supérieur": "with higher-order constructs",
    "Exporter": "Export",
    "openpls_resultats.xlsx": "openpls_results.xlsx",
    "modele.txt": "model.txt",
    "# Modèle structurel  ( cible ~ source1 + source2 ;  X:M = modération )":
        "# Structural model  ( target ~ source1 + source2 ;  X:M = moderation )",
    "# Modèle structurel": "# Structural model",
    "Quitter OpenPLS": "Quit OpenPLS",
    "OpenPLS se ferme…": "OpenPLS is closing…",
    "CSV ou Excel": "CSV or Excel",
    "PLSc corrige l'atténuation pour les construits réflectifs (modèles de facteurs communs).":
        "PLSc corrects attenuation for reflective constructs (common factor models).",
    "Lance le bootstrap juste après l'estimation : t, p, intervalles de confiance et étoiles de significativité "
    "apparaissent dans les tableaux et le diagramme.":
        "Runs the bootstrap right after estimation: t, p, confidence intervals and significance stars appear in "
        "the tables and the diagram.",
    "Options avancées": "Advanced options",
    "Langue": "Language",
    "Schéma de pondération interne": "Inner weighting scheme",
    "Méthode de modération": "Moderation method",
    "Approche d'ordre supérieur": "Higher-order approach",
    "Séparateur décimal": "Decimal separator",
    "Modèle structurel": "Structural model",
    "Modèle de mesure": "Measurement model",
    "Validité discriminante": "Discriminant validity",
    "Scores": "Scores",
    "Coefficients de chemin": "Path coefficients",
    "Bootstrap à **{n}** échantillons, IC percentile à {c} %. Peut prendre de quelques secondes à quelques minutes.":
        "Bootstrap with **{n}** samples, {c}% percentile CI. May take from a few seconds to a few minutes.",
    "Le seuil (1 %, 5 % ou 10 %) se règle au-dessus du diagramme, dans l'onglet Résultats.":
        "The threshold (1%, 5% or 10%) is set above the diagram, in the Results tab.",
    "Analyse": "Analysis",
    "Scores des variables latentes (standardisés)": "Latent variable scores (standardized)",
    "Résultats (Excel)": "Results (Excel)",
    "Syntaxe du modèle": "Model syntax",
    "# Modèle de mesure  ( =~ réflectif,  <~ formatif )": "# Measurement model  ( =~ reflective,  <~ formative )",
    "Enregistré : {path}": "Saved: {path}",
    "Ouvrir le dossier": "Open folder",
    "IC": "CI",
    "Importe tes données pour commencer": "Import your data to get started",
    "Dépose un fichier **CSV ou Excel** dans la barre latérale : une colonne par indicateur, une ligne par répondant. "
    "OpenPLS propose ensuite un modèle de départ que tu ajustes dans l'éditeur visuel.\n\nPour découvrir l'outil sans "
    "tes données, choisis « Données d'exemple ».":
        "Drop a **CSV or Excel** file in the sidebar: one column per indicator, one row per respondent. OpenPLS then "
        "suggests a starting model that you adjust in the visual editor.\n\nTo try the tool without your own data, "
        "choose “Example data”.",
    "Par défaut : la langue choisie à l'installation (ou celle du système).":
        "Default: the language chosen at installation (or the system language).",
    "Utilisée seulement si le modèle contient un terme d'interaction `X:M`.":
        "Used only if the model contains an interaction term `X:M`.",
    "Utilisée seulement si le modèle contient un construit d'ordre supérieur (`HOC =~ LV1 + LV2`).":
        "Used only if the model contains a higher-order construct (`HOC =~ LV1 + LV2`).",
    "Graine aléatoire": "Random seed",
    "Par défaut : celui de la langue de l'interface. Ici : {sep}.": "Default: that of the interface language. Here: {sep}.",
    "Aperçu des données — {r} lignes × {c} colonnes": "Data preview — {r} rows × {c} columns",
    "Éditeur visuel": "Visual editor",
    "Syntaxe": "Syntax",
    "Glisse les indicateurs sur le canevas · tire la poignée bleue d'une variable vers une autre pour créer un chemin · "
    "clique un chemin pour ajouter un modérateur · pour un construit d'ordre supérieur, crée une variable vide puis "
    "« + Composante » · enfin « Appliquer au modèle ».":
        "Drag indicators onto the canvas · drag a variable's blue handle to another one to create a path · click a "
        "path to add a moderator · for a higher-order construct, create an empty variable then “+ Component” · "
        "finally “Apply to model”.",
    "Estimer le modèle": "Estimate the model",
    "Clique sur « ▶ Estimer le modèle » dans l'onglet **Modèle** pour afficher les résultats.":
        "Click “▶ Estimate the model” in the **Model** tab to see the results.",
    "Avec PLSc, seule la modération en deux étapes est corrigée de l'atténuation (Becker et al. 2018) ; les approches "
    "par produit d'indicateurs sous-estiment l'effet d'interaction.":
        "With PLSc, only two-stage moderation is corrected for attenuation (Becker et al. 2018); product-indicator "
        "approaches underestimate the interaction effect.",
    "Méthode": "Method",
    "Observations": "Observations",
    "Convergence": "Convergence",
    "L'algorithme n'a pas convergé : vérifie la spécification du modèle.":
        "The algorithm did not converge: check the model specification.",
    "Diagramme estimé": "Estimated diagram",
    "t, p et étoiles : coche « Calculer t et p automatiquement » dans la barre latérale, ou :":
        "t, p and stars: tick “Compute t and p automatically” in the sidebar, or:",
    "Effets totaux": "Total effects",
    "Taille d'effet f²": "Effect size f²",
    "Modération : pentes simples": "Moderation: simple slopes",
    "Modération en deux étapes : le modèle de mesure est évalué sur l'estimation de l'étape 1 (modèle sans interaction).":
        "Two-stage moderation: the measurement model is assessed on the stage-1 estimation (model without "
        "interaction).",
    "Ordre supérieur en deux étapes : les construits d'ordre 1 (dont les composantes) sont évalués sur l'étape 1 ; les "
    "construits d'ordre supérieur, dans le tableau dédié plus bas.":
        "Two-stage higher-order approach: first-order constructs (including components) are assessed on stage 1; "
        "higher-order constructs in the dedicated table below.",
    "Chargements et poids externes": "Outer loadings and weights",
    "Rouge : chargement < 0,708 (Hair et al.). Pour un bloc formatif, regarde plutôt les poids.":
        "Red: loading < 0.708 (Hair et al.). For a formative block, look at the weights instead.",
    "Fiabilité et validité convergente": "Reliability and convergent validity",
    "Seuils : α, ρ_A, ρ_c ≥ 0,70 (ρ_c ≤ 0,95) · AVE ≥ 0,50. Ces critères ne s'appliquent qu'aux construits réflectifs.":
        "Thresholds: α, ρ_A, ρ_c ≥ 0.70 (ρ_c ≤ 0.95) · AVE ≥ 0.50. These criteria apply to reflective constructs only.",
    "Construits d'ordre supérieur": "Higher-order constructs",
    "Rouge : HTMT > 0,85 (seuil prudent ; 0,90 pour des construits conceptuellement proches).":
        "Red: HTMT > 0.85 (conservative threshold; 0.90 for conceptually similar constructs).",
    "Critère de Fornell-Larcker": "Fornell-Larcker criterion",
    "Diagonale = √AVE ; elle doit dépasser les corrélations de sa ligne et de sa colonne.":
        "Diagonal = √AVE; it should exceed the correlations in its row and column.",
    "Lancer le bootstrap": "Run the bootstrap",
    "{n} tirages utilisés.": "{n} draws used.",
    "Effets directs (coefficients de chemin)": "Direct effects (path coefficients)",
    "Effets indirects spécifiques": "Specific indirect effects",
    "Effets indirects totaux": "Total indirect effects",
    "Pentes simples (modération)": "Simple slopes (moderation)",
    "Chargements externes": "Outer loadings",
    "Poids externes": "Outer weights",
    "Chargements des composantes (ordre supérieur)": "Component loadings (higher-order)",
    "Poids des composantes (ordre supérieur)": "Component weights (higher-order)",
    "Validation croisée à k plis répétée : le modèle prédit-il de **nouvelles** observations mieux qu'une simple moyenne "
    "(Q²_predict > 0) et qu'une régression linéaire (LM) ?":
        "Repeated k-fold cross-validation: does the model predict **new** observations better than a simple mean "
        "(Q²_predict > 0) and a linear regression (LM)?",
    "# Construit de second ordre : ses termes sont des variables latentes":
        "# Second-order construct: its terms are latent variables",
    "Données d'exemple": "Example data",
    "Exemple de second ordre": "Second-order example",
    "Importer un fichier": "Import a file",
    "Colonnes : ": "Columns: ",
    "Aucun chemin structurel : ajoute au moins une ligne `CIBLE ~ SOURCE`.":
        "No structural path: add at least one line `TARGET ~ SOURCE`.",
    "Bootstrap (t et p)…": "Bootstrap (t and p)…",
    "{n} itérations": "{n} iterations",
    "non atteinte": "not reached",
    "{n} tirages": "{n} draws",
    "pas encore lancé": "not run yet",
    "Modération": "Moderation",
    "Ordre supérieur": "Higher-order",
    "Significativité sur le diagramme": "Significance on the diagram",
    "Seuil de {a} % (bootstrap, {n} tirages). Vert : significatif. Rouge pointillé : non significatif. L'épaisseur suit "
    "la taille de l'effet.":
        "{a}% threshold (bootstrap, {n} draws). Green: significant. Dashed red: not significant. Line width follows "
        "effect size.",
    "Calculer t et p": "Compute t and p",
    "En gras : p < {a}. t et p par bootstrap ({n} tirages) ; intervalle de confiance percentile.":
        "Bold: p < {a}. t and p from the bootstrap ({n} draws); percentile confidence interval.",
    "Repères (Cohen) : 0,02 faible · 0,15 moyen · 0,35 fort. Pour une interaction : 0,005 faible · 0,01 moyen · "
    "0,025 fort (Kenny 2018).":
        "Benchmarks (Cohen): 0.02 small · 0.15 medium · 0.35 large. For an interaction: 0.005 small · 0.01 medium · "
        "0.025 large (Kenny 2018).",
    "Les composantes jouent le rôle d'indicateurs du construit d'ordre supérieur : chargements (réflectif) ou poids et "
    "VIF (formatif). Rouge : chargement < 0,708 ou VIF > 5.":
        "Components act as indicators of the higher-order construct: loadings (reflective) or weights and VIF "
        "(formative). Red: loading < 0.708 or VIF > 5.",
    "Analyse de médiation": "Mediation analysis",
    "Typologie de Zhao, Lynch & Chen (2010). Significativité = l'IC bootstrap exclut 0. Pour tester une médiation "
    "partielle, le chemin direct doit figurer dans le modèle.":
        "Typology of Zhao, Lynch & Chen (2010). Significant = the bootstrap CI excludes 0. To test partial mediation, "
        "the direct path must be in the model.",
    "PLSpredict n'est pas disponible pour les modèles {why}.": "PLSpredict is not available for models {why}.",
    "Plis (k)": "Folds (k)",
    "Répétitions": "Repetitions",
    "Approche": "Approach",
    "Lancer PLSpredict et CVPAT": "Run PLSpredict and CVPAT",
    "Compare les coefficients de chemin de **plusieurs groupes**, après avoir vérifié l'invariance de mesure (MICOM). "
    "Avec plus de deux groupes : test omnibus, puis comparaisons deux à deux corrigées par Holm.":
        "Compares path coefficients across **several groups**, after checking measurement invariance (MICOM). With "
        "more than two groups: omnibus test, then Holm-corrected pairwise comparisons.",
    "# Modèle de mesure (ordre 1)": "# Measurement model (first order)",
    "oui": "yes",
    "non": "no",
    "Deux étapes (recommandé)": "Two-stage (recommended)",
    "Produit des indicateurs": "Product indicator",
    "Orthogonalisation": "Orthogonalization",
    "Deux étapes, disjointe (recommandé)": "Two-stage, disjoint (recommended)",
    "Deux étapes, intégrée": "Two-stage, embedded",
    "Indicateurs répétés": "Repeated indicators",
    "virgule (0,318)": "comma (0,318)",
    "point (0.318)": "point (0.318)",
    "`LATENTE =~ ind1 + ind2` (réflectif) · `LATENTE <~ ind1 + ind2` (formatif) · `CIBLE ~ SOURCE1 + SOURCE2` "
    "(chemins) · `CIBLE ~ X + M + X:M` (modération) · `HOC =~ LV1 + LV2` (ordre supérieur : les termes sont des "
    "variables latentes). `#` pour les commentaires.":
        "`LATENT =~ ind1 + ind2` (reflective) · `LATENT <~ ind1 + ind2` (formative) · `TARGET ~ SOURCE1 + SOURCE2` "
        "(paths) · `TARGET ~ X + M + X:M` (moderation) · `HOC =~ LV1 + LV2` (higher-order: terms are latent "
        "variables). `#` for comments.",
    "Échec de l'estimation : {e}": "Estimation failed: {e}",
    "Échec du bootstrap : {e}": "Bootstrap failed: {e}",
    "Clique sur « Estimer le modèle » pour afficher les estimations sur le diagramme.":
        "Click “Estimate the model” to show the estimates on the diagram.",
    "Seuil": "Threshold",
    "Coefficients seuls : le bootstrap n'a pas été lancé. Il n'est utile que pour la significativité (t, p, étoiles, "
    "intervalles de confiance) : lance-le dans l'onglet Significativité, ou coche « Calculer t et p automatiquement » "
    "dans la barre latérale.":
        "Coefficients only: the bootstrap has not been run. It is only needed for significance (t, p, stars, "
        "confidence intervals): run it in the Significance tab, or tick “Compute t and p automatically” in the "
        "sidebar.",
    "f² non calculable : {e}": "f² cannot be computed: {e}",
    "Pente de {a} sur {d} quand {b} vaut -1, 0 ou +1 écart-type.": "Slope of {a} on {d} when {b} is -1, 0 or +1 SD.",
    ". Essaie le PLS classique (au lieu de PLSc), un échantillon plus grand ou un modèle de mesure plus fiable.":
        ". Try regular PLS (instead of PLSc), a larger sample or a more reliable measurement model.",
    "EA : prédiction à partir des seules exogènes (recommandé). DA : à partir des antécédents directs.":
        "EA: prediction from exogenous constructs only (recommended). DA: from direct antecedents.",
    "Indicateurs endogènes": "Endogenous indicators",
    "élevée": "high",
    "PLS bat LM sur {k}/{n} indicateurs → puissance prédictive **{v}** (Shmueli et al. 2019). Rouge : Q²_predict ≤ 0.":
        "PLS beats LM on {k}/{n} indicators → **{v}** predictive power (Shmueli et al. 2019). Red: Q²_predict ≤ 0.",
    "Aucune colonne de groupe disponible : il faut une colonne (hors indicateurs) avec peu de modalités, par exemple "
    "« sexe » ou « pays ».":
        "No group column available: you need a column (other than indicators) with few categories, e.g. “gender” "
        "or “country”.",
    "Variable de groupe": "Group variable",
    "Groupes à comparer (au moins 2)": "Groups to compare (at least 2)",
    "Bootstrap par groupe": "Bootstrap per group",
    "Quels antécédents ont une forte **importance** (effet total non standardisé) mais une faible **performance** "
    "(score moyen sur 0-100) ? Ce sont les leviers prioritaires.":
        "Which antecedents have high **importance** (unstandardized total effect) but low **performance** (mean "
        "score on 0-100)? They are the priority levers.",
    "virgule": "comma",
    "point": "point",
    "schéma": "scheme",
    "Vert : significatif à ce seuil. Rouge : non significatif. Le seuil vaut aussi pour le gras des tableaux et les "
    "intervalles de confiance.":
        "Green: significant at this threshold. Red: not significant. The threshold also sets bold values in tables "
        "and the confidence intervals.",
    "(bootstrap, {n} tirages). Gris pointillé : non significatif même à 10 %. L'épaisseur suit la taille de l'effet.":
        "(bootstrap, {n} draws). Dashed grey: not significant even at 10%. Line width follows effect size.",
    "Inférence NON fiable — ": "Inference NOT reliable — ",
    "non estimé": "not estimated",
    "Validation croisée…": "Cross-validation…",
    "moyenne": "mean",
    "Latentes endogènes": "Endogenous latent variables",
    "Différence de perte < 0 et p < 0,05 : PLS prédit significativement mieux que le benchmark (IA = moyenne des "
    "indicateurs, LM = régression linéaire).":
        "Loss difference < 0 and p < 0.05: PLS predicts significantly better than the benchmark (IA = indicator "
        "average, LM = linear regression).",
    "Choisis au moins deux groupes.": "Choose at least two groups.",
    "Lancer MGA et MICOM": "Run MGA and MICOM",
    "MICOM — invariance de mesure": "MICOM — measurement invariance",
    "Chaque construit est testé à 5 % : avec plusieurs construits (et plusieurs paires), un rejet isolé survient souvent "
    "par hasard. Un rejet sur un construit dont la relation structurelle diffère entre groupes peut aussi refléter cette "
    "différence (poids PLS).":
        "Each construct is tested at 5%: with several constructs (and pairs), an isolated rejection often occurs by "
        "chance. A rejection on a construct whose structural relationship differs across groups can also reflect "
        "that difference (PLS weights).",
    "IPMA non disponible pour les modèles {why}.": "IPMA is not available for models {why}.",
    "Construit cible": "Target construct",
    "Bornes théoriques de l'échelle": "Theoretical scale bounds",
    "Un antécédent est-il une **condition nécessaire** de la cible (pas de niveau élevé de la cible sans un niveau "
    "suffisant de l'antécédent) ? Plafond CE-FDH, test de permutation.":
        "Is an antecedent a **necessary condition** for the target (no high target level without a sufficient level "
        "of the antecedent)? CE-FDH ceiling, permutation test.",
    "Lancer la NCA": "Run the NCA",
    "deux étapes": "two-stage",
    "produit des indicateurs": "product indicator",
    "orthogonalisation": "orthogonalization",
    "Afficher (étoiles : 1 %, 5 % et 10 %)": "Show (stars: 1%, 5% and 10%)",
    "Ne pas afficher (couleurs selon un seuil)": "Hide (colours at one threshold)",
    "faible": "low",
    "nulle": "none",
    "Effectifs : ": "Group sizes: ",
    "Coefficients par groupe": "Coefficients by group",
    "Test omnibus (tous les groupes)": "Omnibus test (all groups)",
    "H0 : le chemin est identique dans tous les groupes (test de permutation sur Σ n_g (β_g − β̄)²). N'interprète les "
    "paires que pour les chemins rejetés ici.":
        "H0: the path is identical in all groups (permutation test on Σ n_g (β_g − β̄)²). Only interpret pairs for "
        "paths rejected here.",
    "Comparaisons deux à deux": "Pairwise comparisons",
    "p_perm_Holm : p-value de permutation corrigée par Holm sur l'ensemble des paires, pour chaque chemin. Henseler et "
    "Welch : non corrigées, à titre indicatif.":
        "p_perm_Holm: permutation p-value, Holm-corrected over all pairs, for each path. Henseler and Welch: "
        "uncorrected, for information.",
    "Comparaison des chemins": "Path comparison",
    "En rouge : p < 0,05 (différence significative). Test de permutation recommandé (Chin & Dibbern 2010) ; PLS-MGA de "
    "Henseler (2009) et Welch-Satterthwaite en complément.":
        "Red: p < 0.05 (significant difference). Permutation test recommended (Chin & Dibbern 2010); Henseler's "
        "PLS-MGA (2009) and Welch-Satterthwaite as complements.",
    "Sinon, min et max observés de chaque indicateur.": "Otherwise, observed min and max of each indicator.",
    "Niveau indicateur": "Indicator level",
    "Nuage de points": "Scatter plot",
    "Ligne orange : plafond CE-FDH. La zone vide au-dessus-gauche mesure la contrainte de nécessité.":
        "Orange line: CE-FDH ceiling. The empty upper-left area measures the necessity constraint.",
    "Un antécédent est-il corrélé au terme d'erreur (endogénéité) ? Ajout de termes de **copule gaussienne** (Park & "
    "Gupta 2012) ; un terme significatif signale un problème.":
        "Is an antecedent correlated with the error term (endogeneity)? Adds **Gaussian copula** terms (Park & Gupta "
        "2012); a significant term signals a problem.",
    "Lancer le test": "Run the test",
    "Échec : {e}": "Failed: {e}",
    "Permutations et bootstrap…": "Permutations and bootstrap…",
    "Lignes pointillées : moyennes. En bas à droite : forte importance, faible performance → priorités d'action.":
        "Dashed lines: means. Bottom right: high importance, low performance → action priorities.",
    "Performance de {t}": "Performance of {t}",
    "Permutations…": "Permutations…",
    "Tailles d'effet": "Effect sizes",
    "d : 0-0,1 faible · 0,1-0,3 moyen · 0,3-0,5 fort · ≥ 0,5 très fort (Dul 2016).":
        "d: 0-0.1 small · 0.1-0.3 medium · 0.3-0.5 large · ≥ 0.5 very large (Dul 2016).",
    "Tableau des goulots": "Bottleneck table",
    "Niveau minimal de chaque antécédent (% de son étendue) requis pour atteindre chaque niveau de {t}. Vide = non "
    "nécessaire à ce niveau.":
        "Minimum level of each antecedent (% of its range) required to reach each level of {t}. Empty = not "
        "necessary at that level.",
    "Estimation par **maximum de vraisemblance** (modèle de facteurs communs), avec indices d'ajustement globaux. La CFA "
    "corrèle toutes les latentes sans chemins structurels.":
        "**Maximum likelihood** estimation (common factor model), with global fit indices. The CFA correlates all "
        "latent variables without structural paths.",
    "**Étape 2 — invariance compositionnelle**": "**Step 2 — compositional invariance**",
    "**Étape 3 — égalité des moyennes et des variances**": "**Step 3 — equality of means and variances**",
    "Non-normalité (Shapiro-Wilk)": "Non-normality (Shapiro-Wilk)",
    "Rouge : distribution normale → la copule n'est pas identifiée pour ce régresseur.":
        "Red: normal distribution → the copula is not identified for this regressor.",
    "Synthèse": "Summary",
    "La copule n'est identifiée que si le régresseur est non normal : sinon la conclusion est « non interprétable », "
    "quelle que soit la p-value.":
        "The copula is identified only if the regressor is non-normal: otherwise the conclusion is “not "
        "interpretable”, whatever the p-value.",
    "Détail de chaque modèle": "Details of each model",
    "χ² (ddl)": "χ² (df)",
    "Y a-t-il des **segments cachés** de répondants avec des relations structurelles différentes ? FIMIX-PLS estime un "
    "mélange de régressions sur les scores des latentes.":
        "Are there **hidden segments** of respondents with different structural relationships? FIMIX-PLS estimates "
        "a mixture of regressions on the latent scores.",
    "Bootstrap (t et p) {i}/{n}": "Bootstrap (t and p) {i}/{n}",
    "ET": "SD",
    "{a} (écarts-types)": "{a} (SD)",
    "{d} prédit (écarts-types)": "predicted {d} (SD)",
    "Importance (effet total non standardisé)": "Importance (unstandardized total effect)",
    "Performance (0-100)": "Performance (0-100)",
    "Carte IPMA — {t}": "IPMA map — {t}",
    "L'optimisation n'a pas pleinement convergé : interprète avec prudence.":
        "The optimization did not fully converge: interpret with caution.",
    "≥ 0,95 bon (Hu & Bentler 1999)": "≥ 0.95 good (Hu & Bentler 1999)",
    "≥ 0,95 bon": "≥ 0.95 good",
    "≤ 0,06 bon · IC 90 % [{lo} ; {hi}]": "≤ 0.06 good · 90% CI [{lo}; {hi}]",
    "≤ 0,08 bon": "≤ 0.08 good",
    "Ajustement insuffisant selon : {b} (seuils de Hu & Bentler 1999).": "Insufficient fit on: {b} (Hu & Bentler 1999 thresholds).",
    "Tous les indices respectent les seuils de Hu & Bentler (1999).": "All indices meet the Hu & Bentler (1999) thresholds.",
    "Chargements standardisés": "Standardized loadings",
    "Corrélations entre latentes": "Latent variable correlations",
    "Tous les paramètres (estimations non standardisées, erreurs-types, p-values)":
        "All parameters (unstandardized estimates, standard errors, p-values)",
    "FIMIX-PLS n'est pas disponible pour les modèles avec interaction.":
        "FIMIX-PLS is not available for models with an interaction.",
    "Nombre maximal de segments": "Maximum number of segments",
    "Départs aléatoires": "Random starts",
    "Lancer FIMIX-PLS": "Run FIMIX-PLS",
    "SEM complet": "Full SEM",
    "CFA (analyse factorielle confirmatoire)": "CFA (confirmatory factor analysis)",
    "Chemins standardisés": "Standardized paths",
    "Chargements de second ordre": "Second-order loadings",
    "Critères de choix du nombre de segments": "Criteria for choosing the number of segments",
    "En surligné : minimum de chaque critère. Retiens S quand AIC3 et CAIC s'accordent (Sarstedt et al. 2011) ; EN > 0,5 "
    "indique des segments bien séparés. Un segment très petit (< 5 %) est rarement interprétable.":
        "Highlighted: minimum of each criterion. Retain S when AIC3 and CAIC agree (Sarstedt et al. 2011); EN > 0.5 "
        "indicates well-separated segments. A very small segment (< 5%) is rarely interpretable.",
    "Solution à afficher": "Solution to show",
    "conclusion": "conclusion",
    "Algorithme EM…": "EM algorithm…",
    "**Taille des segments**": "**Segment sizes**",
    "**R² par segment**": "**R² by segment**",
    "**Coefficients de chemin par segment**": "**Path coefficients by segment**",
    "endogénéité": "endogeneity",
    "Appartenance aux segments (CSV)": "Segment membership (CSV)",
    "pas d'endogénéité": "no endogeneity",
    "# Modèle structurel  ( cible ~ source1 + source2 )": "# Structural model  ( target ~ source1 + source2 )",
    "# EXEMPLE ~ A + B": "# EXAMPLE ~ A + B",
    "ns non significatif": "ns not significant",
    "Colonnes introuvables dans les données : {cols}": "Columns not found in the data: {cols}",
    "{k} ligne(s) avec valeurs manquantes ou non numériques supprimée(s) (suppression par liste) : {n} observations "
    "utilisées.":
        "{k} row(s) with missing or non-numeric values removed (listwise deletion): {n} observations used.",
    "Moins de 30 observations : les résultats seront très instables.":
        "Fewer than 30 observations: results will be very unstable.",

    # noms de colonnes et valeurs produits par les calculs
    "chemin": "path", "coefficient": "coefficient", "chargement": "loading", "poids": "weight",
    "erreur-type": "std. error", "moyenne bootstrap": "bootstrap mean", "sig.": "sig.",
    "t (chargement)": "t (loading)", "p (chargement)": "p (loading)", "sig. chargement": "sig. loading",
    "t (poids)": "t (weight)", "p (poids)": "p (weight)", "sig. poids": "sig. weight",
    "effet": "effect", "indirect signif.": "indirect sig.", "direct signif.": "direct sig.",
    "type de médiation": "mediation type", "significatif": "significant",
    "complémentaire (partielle)": "complementary (partial)", "compétitive (partielle)": "competitive (partial)",
    "indirecte seule (totale)": "indirect-only (full)", "directe seule (pas de médiation)": "direct-only (no mediation)",
    "aucun effet": "no effect", "aucun effet indirect": "no indirect effect",
    "indirecte (type indéterminé : chemin direct non estimé)": "indirect (type undetermined: direct path not estimated)",
    "composante": "component", "construit": "construct", "latente": "latent", "indicateur": "indicator",
    "pente": "slope", "paire": "pair", "taille": "size", "proportion": "proportion", "segments": "segments",
    "paramètres": "parameters", "plus petit segment (%)": "smallest segment (%)", "statistique": "statistic",
    "modèle": "model", "régresseur": "regressor", "copule": "copula", "chemin PLS": "PLS path",
    "chemin corrigé": "corrected path", "non normal (p<0,05)": "non-normal (p<0.05)",
    "non interprétable (régresseur normal)": "not interpretable (normal regressor)",
    "condition nécessaire (d≥0,1 et p<0,05)": "necessary condition (d≥0.1 and p<0.05)",
    "moyen": "medium", "fort": "large", "très fort": "very large",
    "invariance compositionnelle": "compositional invariance", "égalité moyennes": "equal means",
    "égalité variances": "equal variances", "diff_moyenne": "mean_diff", "diff_log_variance": "log_variance_diff",
    "p_moyenne": "p_mean", "p_variance": "p_variance",
    "différence entre groupes (p<0,05)": "difference between groups (p<0.05)",
    "différence significative (Holm, 5 %)": "significant difference (Holm, 5%)",
    "différence significative (perm., 5 %)": "significant difference (perm., 5%)",
    "PLS meilleur (p<0,05)": "PLS better (p<0.05)", "perte_PLS": "PLS_loss", "perte_benchmark": "benchmark_loss",
    "diff_perte": "loss_diff", "difference": "difference",
    "invariance totale : les données peuvent être regroupées": "full invariance: the data can be pooled",
    "invariance partielle : la comparaison des chemins entre groupes est légitime":
        "partial invariance: comparing paths across groups is legitimate",
    "invariance au moins partielle pour toutes les paires : la comparaison est légitime":
        "at least partial invariance for all pairs: the comparison is legitimate",
    "invariance compositionnelle non établie pour au moins une paire : interpréter avec prudence":
        "compositional invariance not established for at least one pair: interpret with caution",
    "réflectif": "reflective", "formatif": "formative",
    # feuilles de l'export Excel
    "Chemins": "Paths", "Chargements": "Loadings", "Qualite": "Quality", "Ordre superieur": "Higher order",
    "Ordre sup qualite": "Higher order quality", "PLSpredict latentes": "PLSpredict latents",
    "MGA groupes": "MGA groups", "MGA paires": "MGA pairs", "MICOM etape 2": "MICOM step 2",
    "MICOM etape 3": "MICOM step 3", "IPMA indicateurs": "IPMA indicators", "NCA goulots": "NCA bottlenecks",
    "Endogeneite": "Endogeneity", "CB-SEM ajustement": "CB-SEM fit", "CB-SEM parametres": "CB-SEM parameters",
    "FIMIX criteres": "FIMIX criteria", "FIMIX chemins": "FIMIX paths", "Effets totaux ": "Total effects",
    "valeur": "value", "groupe": "group",
}

# textes qui contiennent des noms (variables, groupes) : traduits par motif
PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^pas d'invariance compositionnelle pour (.+) : interpréter la MGA avec prudence$"),
     r"no compositional invariance for \1: interpret the MGA with caution"),
    (re.compile(r"^(\d+)/(\d+) permutations en échec exclues$"), r"\1/\2 failed permutations excluded"),
    (re.compile(r"^omnibus : (\d+)/(\d+) permutations en échec exclues$"), r"omnibus: \1/\2 failed permutations excluded"),
    (re.compile(r"^(.+) ~~ (.+) \(résiduelle\)$"), r"\1 ~~ \2 (residual)"),
    (re.compile(r"^copules : (.+)$"), r"copulas: \1"),
    (re.compile(r"^copule\((.+)\)$"), r"copula(\1)"),
    (re.compile(r"^(.+) si (.+)=([+-]1)$"), r"\1 if \2=\3"),
    (re.compile(r"^(.+) = ([+-]\d+) ET$"), r"\1 = \2 SD"),
    (re.compile(r"^(.+) \(ET\)$"), r"\1 (SD)"),
    (re.compile(r"^IC (.+)$"), r"CI \1"),
    (re.compile(r"^IC_moy_(.+)$"), r"CI_mean_\1"),
    (re.compile(r"^IC_var_(.+)$"), r"CI_var_\1"),
    (re.compile(r"^(.+) n'a aucun (prédécesseur|antécédent)$"), r"\1 has no antecedent"),
    (re.compile(r"^(\d+)/(\d+) tirages n'ont pas convergé$"), r"\1/\2 draws did not converge"),
]


def translate(text: str) -> str:
    if text in EN:
        return EN[text]
    for pat, rep in PATTERNS:
        if pat.match(text):
            return pat.sub(rep, text)
    return text

# ---------------------------------------------------------------- analyses préliminaires et aide
EN.update({
    "Calculées sur les données brutes ({n} lignes), indicateurs regroupés par construit. À examiner avant "
    "d'interpréter le modèle.":
        "Computed on the raw data ({n} rows), indicators grouped by construct. Check them before interpreting the model.",
    "openpls_preliminaires.xlsx": "openpls_preliminary.xlsx",
    "Aucun indicateur numérique à analyser.": "No numeric indicator to analyse.",
    "Statistiques descriptives": "Descriptive statistics",
    "Manquants et aberrants": "Missing values and outliers",
    "Normalité": "Normality",
    "Corrélations": "Correlations",
    "Biais de méthode commune": "Common method bias",
    "Taille d'échantillon": "Sample size",
    "Figures": "Figures",
    "Aplatissement = excès de kurtosis (0 pour une loi normale). Rouge : |asymétrie| > 2 ou |aplatissement| > 7 "
    "(Curran, West & Finch 1996 ; Kline 2016). PLS-SEM ne suppose pas la normalité, mais une distribution très "
    "asymétrique mérite d'être signalée.":
        "Kurtosis = excess kurtosis (0 for a normal distribution). Red: |skewness| > 2 or |kurtosis| > 7 (Curran, "
        "West & Finch 1996; Kline 2016). PLS-SEM does not assume normality, but a strongly skewed distribution is "
        "worth reporting.",
    "Lignes complètes": "Complete rows",
    "Valeurs manquantes": "Missing values",
    "Rouge : plus de 5 % de valeurs manquantes. L'estimation utilise la suppression par liste (lignes incomplètes "
    "retirées) sauf si tu choisis un autre traitement dans la barre latérale.":
        "Red: more than 5% missing values. Estimation uses listwise deletion (incomplete rows removed) unless you "
        "choose another treatment in the sidebar.",
    "Valeurs aberrantes multivariées": "Multivariate outliers",
    "**{k}** observation(s) aberrante(s) sur {n} (distance de Mahalanobis, p < 0,001).":
        "**{k}** outlying observation(s) out of {n} (Mahalanobis distance, p < 0.001).",
    "Les 20 distances les plus grandes. Numéro d'observation = ligne du fichier (à partir de 0). Vérifie ces réponses "
    "avant de les retirer : une valeur extrême n'est pas forcément une erreur.":
        "The 20 largest distances. Observation number = file row (starting at 0). Check these responses before "
        "removing them: an extreme value is not necessarily an error.",
    "Indicateur": "Indicator",
    "Coefficient": "Coefficient",
    "Variance du premier facteur": "Variance of the first factor",
    "Facteurs de valeur propre > 1": "Factors with eigenvalue > 1",
    "Colinéarité complète (Kock 2015)": "Full collinearity (Kock 2015)",
    "Plus petit coefficient de chemin attendu |β_min|": "Smallest expected path coefficient |β_min|",
    "n minimal (racine carrée inverse)": "minimum n (inverse square root)",
    "n minimal (règle des 10 fois)": "minimum n (10-times rule)",
    "n disponible (lignes complètes)": "available n (complete rows)",
    "Méthode de la racine carrée inverse (Kock & Hadaya 2018) : taille minimale pour détecter |β_min| avec une "
    "puissance de 80 %. La règle des 10 fois (10 × le plus grand nombre de flèches pointant vers un construit) est plus "
    "ancienne et souvent trop optimiste.":
        "Inverse square root method (Kock & Hadaya 2018): minimum size to detect |β_min| with 80% power. The "
        "10-times rule (10 × the largest number of arrows pointing at a construct) is older and often too optimistic.",
    "Construit": "Construct",
    "Points rouges : valeurs au-delà de 1,5 écart interquartile. Les figures s'exportent en PNG (300 ppp) pour Word ou "
    "en SVG pour une mise en page vectorielle.":
        "Red dots: values beyond 1.5 interquartile ranges. Figures export as PNG (300 dpi) for Word or SVG for "
        "vector layout.",
    "Analyses préliminaires (Excel)": "Preliminary analyses (Excel)",
    "PNG (300 ppp)": "PNG (300 dpi)",
    "Test de Mardia": "Mardia's test",
    "p < 0,05 : les données s'écartent de la normalité multivariée. C'est fréquent avec des échelles de Likert et "
    "c'est une raison d'utiliser PLS-SEM avec un bootstrap plutôt qu'un CB-SEM par maximum de vraisemblance.":
        "p < 0.05: the data depart from multivariate normality. This is common with Likert scales and is a reason "
        "to use PLS-SEM with a bootstrap rather than maximum-likelihood CB-SEM.",
    "Corrélations entre indicateurs": "Correlations between indicators",
    "Test à un facteur de Harman : > 50 % suggère un biais de méthode commune (Podsakoff et al. 2003).":
        "Harman's single-factor test: > 50% suggests common method bias (Podsakoff et al. 2003).",
    "Le premier facteur explique plus de 50 % de la variance : biais de méthode commune possible.":
        "The first factor explains more than 50% of the variance: common method bias is possible.",
    "Le premier facteur explique moins de 50 % de la variance : pas de signe de biais de méthode commune selon le "
    "test de Harman.":
        "The first factor explains less than 50% of the variance: no sign of common method bias according to "
        "Harman's test.",
    "Éboulis des valeurs propres": "Scree plot",
    "facteur": "factor",
    "valeur propre": "eigenvalue",
    "Disponible après l'estimation du modèle (onglet Modèle).": "Available after estimating the model (Model tab).",
    "VIF de chaque variable latente régressée sur toutes les autres. Rouge : VIF > 3,3, signe possible de biais de "
    "méthode commune ou de colinéarité (Kock 2015). Plus sensible que le test de Harman.":
        "VIF of each latent variable regressed on all the others. Red: VIF > 3.3, a possible sign of common method "
        "bias or collinearity (Kock 2015). More sensitive than Harman's test.",
    "Après estimation : le plus petit chemin observé. Sinon, la plus petite valeur que tu veux pouvoir détecter.":
        "After estimation: the smallest observed path. Otherwise, the smallest value you want to be able to detect.",
    "Boîtes à moustaches — {g}": "Box plots — {g}",
    "test": "test",
    "Test de Mardia non calculable : {e}": "Mardia's test cannot be computed: {e}",
    "loi normale": "normal distribution",
    "Diagramme quantile-quantile": "Quantile-quantile plot",
    "quantiles théoriques": "theoretical quantiles",
    "quantiles observés": "observed quantiles",
    "Asymétrie multivariée": "Multivariate skewness",
    "Aplatissement multivarié": "Multivariate kurtosis",
    "tous les indicateurs": "all indicators",
    "indicateurs": "indicators",
    "Rechercher dans l'aide": "Search help",
    "Rubriques": "Topics",
    "ex. HTMT, médiation": "e.g. HTMT, mediation",
    "Aucune rubrique ne contient « {q} ».": "No topic contains “{q}”.",
    "Rubrique suivante : {t}": "Next topic: {t}",
    # colonnes des tableaux préliminaires
    "manquants": "missing", "écart-type": "SD", "médiane": "median", "asymétrie": "skewness",
    "aplatissement": "kurtosis", "Shapiro-Wilk p": "Shapiro-Wilk p", "non numériques": "non-numeric",
    "% manquants": "% missing", "aberrante": "outlier", "observation": "observation",
    "Descriptives": "Descriptives", "Manquants": "Missing", "Correlations": "Correlations",
    "VIF complet": "Full VIF",
})

EN.update({
    "Projet illisible : {e}": "Unreadable project: {e}",
    "Projet": "Project",
    "Enregistrer le projet (.openpls)": "Save project (.openpls)",
    "Données, modèle, disposition et réglages dans un seul fichier, à rouvrir avec « Importer un fichier ».":
        "Data, model, layout and settings in a single file, to reopen with “Import a file”.",
})

# ---------------------------------------------------------------- menu du haut
EN.update({
    "À propos d’OpenPLS": "About OpenPLS",
    "**Version {v}**  \nModélisation par équations structurelles (PLS-SEM, PLSc, CB-SEM), libre et open source.":
        "**Version {v}**  \nFree and open-source structural equation modeling (PLS-SEM, PLSc, CB-SEM).",
    "Les données restent sur ton ordinateur : OpenPLS ne les envoie nulle part. Seule la recherche de mises à jour "
    "contacte GitHub, et seulement quand tu la demandes.":
        "Your data stays on your computer: OpenPLS never sends it anywhere. Only the update check contacts GitHub, "
        "and only when you ask for it.",
    "**Licence** : MIT. Tu peux utiliser, modifier et redistribuer OpenPLS librement, y compris pour des travaux "
    "publiés.":
        "**License**: MIT. You may use, modify and redistribute OpenPLS freely, including for published work.",
    "**Citer OpenPLS** : OpenPLS contributors ({y}). *OpenPLS* (version {v}) [logiciel]. https://github.com/{r}":
        "**Cite OpenPLS**: OpenPLS contributors ({y}). *OpenPLS* (version {v}) [software]. https://github.com/{r}",
    "Code source et documentation": "Source code and documentation",
    "Composants": "Components",
    "Rechercher des mises à jour": "Check for updates",
    "Connexion à GitHub…": "Contacting GitHub…",
    "Impossible de joindre GitHub. Vérifie ta connexion, ou consulte la page des versions.":
        "Could not reach GitHub. Check your connection, or visit the releases page.",
    "Page des versions": "Releases page",
    "Une nouvelle version est disponible : **{new}** (publiée le {d}). Tu utilises la {cur}.":
        "A new version is available: **{new}** (released {d}). You are using {cur}.",
    "Télécharger la version {v}": "Download version {v}",
    "Sous Windows, lance le nouvel installateur : il remplace l'ancienne version et garde tes réglages.":
        "On Windows, run the new installer: it replaces the old version and keeps your settings.",
    "OpenPLS {v} est à jour.": "OpenPLS {v} is up to date.",
    "Paramètres": "Settings",
    "Langue de l'interface": "Interface language",
    "Échantillons bootstrap par défaut": "Default bootstrap samples",
    "Valeur proposée au démarrage. 5 000 est recommandé pour les résultats publiés.":
        "Value proposed at start-up. 5,000 is recommended for published results.",
    "Les réglages sont enregistrés sur cet ordinateur et repris au prochain lancement.":
        "Settings are saved on this computer and restored at the next launch.",
    "Fermer": "Close",
    "À propos": "About",
    "Mises à jour": "Updates",
})

# ---------------------------------------------------------------- données : import, manquants
EN.update({
    "CSV, Excel, SPSS, Stata ou projet OpenPLS": "CSV, Excel, SPSS, Stata or OpenPLS project",
    "Valeurs manquantes": "Missing values",
    "Suppression par liste": "Listwise deletion",
    "Remplacement par la moyenne": "Mean replacement",
    "Imputation par régression": "Regression imputation",
    "Suppression par liste : lignes incomplètes retirées (recommandé si peu de manquants). Moyenne : simple mais "
    "réduit la variance. Régression : chaque indicateur est prédit par les autres (imputation itérative).":
        "Listwise deletion: incomplete rows removed (recommended with few missing values). Mean: simple but "
        "shrinks variance. Regression: each indicator is predicted from the others (iterative imputation).",
    "{k} valeur(s) manquante(s) remplacée(s) ({how}) : {n} observations utilisées.":
        "{k} missing value(s) replaced ({how}): {n} observations used.",
    "régression": "regression",
})

EN.update({
    "{c} : variable de contrôle (construit {n} à un indicateur)": "{c}: control variable (single-indicator construct {n})",
    "{c} : variable catégorielle, {k} indicatrice(s) (référence : {r})":
        "{c}: categorical variable, {k} dummy variable(s) (reference: {r})",
    "# Variables de contrôle (un indicateur)": "# Control variables (single indicator)",
})

EN.update({
    "Jackknife (correction BCa)…": "Jackknife (BCa correction)…",
    "Bootstrap à **{n}** échantillons, IC à {c} %. Peut prendre de quelques secondes à quelques minutes.":
        "Bootstrap with **{n}** samples, {c}% CI. May take from a few seconds to a few minutes.",
    "Intervalles de confiance": "Confidence intervals",
    "percentile": "percentile",
    "BCa (corrigé du biais et accéléré)": "BCa (bias-corrected and accelerated)",
    "BCa : recommandé pour les effets indirects (asymétriques). Demande un jackknife en plus du bootstrap.":
        "BCa: recommended for (skewed) indirect effects. Requires a jackknife in addition to the bootstrap.",
    "Intervalles BCa.": "BCa intervals.",
    "Intervalles percentiles.": "Percentile intervals.",
    "Indice de médiation modérée (Hayes 2015)": "Index of moderated mediation (Hayes 2015)",
    "Effets indirects conditionnels (modérateur à -1, 0, +1 ET)":
        "Conditional indirect effects (moderator at -1, 0, +1 SD)",
    "Comparer deux coefficients": "Compare two coefficients",
    "Coefficient A": "Coefficient A",
    "Coefficient B": "Coefficient B",
    "différence": "difference",
    "Différence significative si l'intervalle exclut 0 (p bootstrap bilatéral). Utile pour comparer deux effets "
    "indirects ou deux chemins vers la même cible.":
        "Significant difference if the interval excludes 0 (two-sided bootstrap p). Useful to compare two indirect "
        "effects or two paths to the same target.",
})

EN.update({
    "Comparaison de modèles": "Model comparison",
    "Tétrades (CTA-PLS)": "Tetrads (CTA-PLS)",
    "Compare le modèle actuel à des modèles **concurrents** sur les mêmes données, pour une même variable cible : "
    "critères d'information (BIC, GM…) et poids de chaque modèle (Sharma et al. 2019, 2021).":
        "Compares the current model with **competing** models on the same data, for the same target variable: "
        "information criteria (BIC, GM…) and each model's weight (Sharma et al. 2019, 2021).",
    "Modèles concurrents": "Competing models",
    "Modèle {i}": "Model {i}",
    "(actuel)": "(current)",
    "Comparer les modèles": "Compare models",
    "{m} : {n} observations au lieu de {k} (indicateurs différents) ; les critères ne sont comparables qu'à données "
    "identiques.":
        "{m}: {n} observations instead of {k} (different indicators); criteria are only comparable on identical data.",
    "Plus petit = meilleur (en surligné). BIC et GM sont recommandés pour choisir entre modèles explicatifs ; le poids "
    "BIC donne la probabilité relative de chaque modèle (Sharma et al. 2019).":
        "Smaller = better (highlighted). BIC and GM are recommended to choose among explanatory models; the BIC "
        "weight gives each model's relative probability (Sharma et al. 2019).",
    "Le modèle de mesure **réflectif** est-il compatible avec les données ? La CTA-PLS teste les tétrades des blocs "
    "d'au moins 4 indicateurs : une tétrade différente de 0 contredit le modèle réflectif et plaide pour une mesure "
    "formative (Gudergan et al. 2008).":
        "Is the **reflective** measurement model consistent with the data? CTA-PLS tests the tetrads of blocks with "
        "at least 4 indicators: a tetrad different from 0 contradicts the reflective model and points to formative "
        "measurement (Gudergan et al. 2008).",
    "Lancer la CTA-PLS": "Run CTA-PLS",
    "Bootstrap des tétrades…": "Bootstrapping tetrads…",
    "Intervalles bootstrap corrigés par Bonferroni sur l'ensemble des tétrades testées du bloc. « non » : au moins une "
    "tétrade diffère de 0, le modèle réflectif est rejeté. Le choix réflectif/formatif doit d'abord reposer sur la "
    "théorie.":
        "Bootstrap intervals Bonferroni-adjusted over all tetrads tested in the block. “no”: at least one tetrad "
        "differs from 0, the reflective model is rejected. The reflective/formative choice should rest on theory first.",
    "Détail des tétrades": "Tetrad details",
    "prédicteurs": "predictors", "poids AIC": "AIC weight", "poids BIC": "BIC weight",
    "tétrade": "tetrad", "IC bas (Bonferroni)": "CI low (Bonferroni)", "IC haut (Bonferroni)": "CI high (Bonferroni)",
    "différente de 0": "different from 0", "indicateurs": "indicators", "tétrades testées": "tetrads tested",
    "tétrades ≠ 0": "tetrads ≠ 0", "réflectif compatible": "reflective consistent",
    "Comparaison modeles": "Model comparison", "CTA tetrades": "CTA tetrads",
    "La CTA-PLS demande au moins un bloc de 4 indicateurs ou plus":
        "CTA-PLS requires at least one block with 4 or more indicators",
})

EN.update({
    "diagramme.png": "diagram.png", "diagramme.svg": "diagram.svg", "diagramme.dot": "diagram.dot",
    "Script Python (reproductible)": "Python script (reproducible)",
    "analyse_openpls.py": "openpls_analysis.py",
})

EN.update({
    "Rapport (Word)": "Report (Word)", "rapport_openpls.docx": "openpls_report.docx",
    "Tableau": "Table", "Note.": "Note.", "Résultats de l'analyse PLS-SEM": "PLS-SEM analysis results",
    "Rapport généré par OpenPLS {v} le {d}. Texte à relire et à adapter avant publication.":
        "Report generated by OpenPLS {v} on {d}. Review and adapt the text before publication.",
    "Méthode": "Method",
    "suppression par liste": "listwise deletion", "remplacement par la moyenne": "mean replacement",
    "imputation par régression": "regression imputation",
    "La significativité a été évaluée par bootstrap ({b} tirages ; intervalles de confiance {m} à {c} %).":
        "Significance was assessed by bootstrapping ({b} draws; {c}% {m} confidence intervals).",
    "Le bootstrap n'a pas été réalisé : la significativité n'est pas rapportée.":
        "No bootstrap was run: significance is not reported.",
    "Le modèle a été estimé par {algo} (OpenPLS {v} ; schéma de pondération {s}) sur n = {n} observations "
    "(valeurs manquantes : {m}). ":
        "The model was estimated with {algo} (OpenPLS {v}; {s} weighting scheme) on n = {n} observations "
        "(missing values: {m}). ",
    "L'évaluation suit les recommandations de Hair et al. (2022) : modèle de mesure (fiabilité, validité convergente "
    "et discriminante), puis modèle structurel.":
        "The assessment follows Hair et al. (2022): measurement model (reliability, convergent and discriminant "
        "validity), then structural model.",
    "Chargements ≥ 0,708 recommandés (Hair et al., 2022).": "Loadings ≥ 0.708 recommended (Hair et al., 2022).",
    "α, ρ_A et ρ_c ≥ 0,70 ; AVE ≥ 0,50.": "α, ρ_A and ρ_c ≥ 0.70; AVE ≥ 0.50.",
    "Validité discriminante (HTMT)": "Discriminant validity (HTMT)",
    "HTMT < 0,85 (Henseler et al., 2015).": "HTMT < 0.85 (Henseler et al., 2015).",
    "Coefficients de chemin : ": "Path coefficients: ",
    "*** p < 0,01 ; ** p < 0,05 ; * p < 0,10 ; ns non significatif.": "*** p < .01; ** p < .05; * p < .10; ns not significant.",
    "Variance expliquée (R²)": "Explained variance (R²)",
    "0,02 faible ; 0,15 moyen ; 0,35 fort (Cohen, 1988).": "0.02 small; 0.15 medium; 0.35 large (Cohen, 1988).",
    "Figure 1": "Figure 1", "Modèle estimé": "Estimated model", "Références": "References",
})
EN["Rapport Word indisponible : {e}"] = "Word report unavailable: {e}"
EN["Lecture SPSS/Stata indisponible : installe le module pyreadstat (pip install pyreadstat), ou enregistre le fichier en CSV."] = \
    "SPSS/Stata import unavailable: install the pyreadstat module (pip install pyreadstat), or save the file as CSV."

EN.update({
    "exemple": "example", "exemple_second_ordre": "second_order_example",
    "Données, modèle, disposition, réglages et résultats dans un seul fichier, à rouvrir avec « Importer un fichier ».":
        "Data, model, layout, settings and results in a single file, to reopen with “Import a file”.",
    "Projets récents": "Recent projects",
    "{d}, {n} lignes": "{d}, {n} rows",
    "**Reprendre le travail en cours ?** {name}, enregistré automatiquement le {d} ({n} lignes{r}).":
        "**Resume your work?** {name}, saved automatically on {d} ({n} rows{r}).",
    ", avec résultats": ", with results",
    "Reprendre": "Resume", "Ignorer": "Dismiss",
    "Sauvegarde automatique du travail en cours": "Automatically save work in progress",
    "Une copie du projet (données comprises) est gardée sur cet ordinateur ; au démarrage, OpenPLS propose de reprendre "
    "là où tu t'étais arrêté.":
        "A copy of the project (including data) is kept on this computer; at start-up, OpenPLS offers to resume "
        "where you left off.",
    "Effacer la sauvegarde automatique et les projets récents": "Clear the automatic save and recent projects",
    "Historique effacé.": "History cleared.",
})

# ---------------------------------------------------------------- erreurs de syntaxe et avertissements du bootstrap
PATTERNS += [
    (re.compile(r"^L'indicateur (\S+) apparaît deux fois dans (\S+) : .*$", re.S),
     r"Indicator \1 appears twice in \2: an indicator can measure only one construct (for a higher-order construct, "
     r"use the syntax HOC =~ LV1 + LV2)"),
    (re.compile(r"^L'indicateur (\S+) apparaît dans (\S+) et dans (\S+) : .*$", re.S),
     r"Indicator \1 appears in \2 and in \3: an indicator can measure only one construct (for a higher-order "
     r"construct, use the syntax HOC =~ LV1 + LV2)"),
    (re.compile(r"^(\S+) ne peut pas avoir à la fois des indicateurs et des composantes$"),
     r"\1 cannot have both indicators and components"),
    (re.compile(r"^Le construit d'ordre supérieur (\S+) doit avoir au moins 2 composantes$"),
     r"Higher-order construct \1 must have at least 2 components"),
    (re.compile(r"^(\S+) : la composante (\S+) doit être une variable latente d'ordre 1 .*$", re.S),
     r"\1: component \2 must be a first-order latent variable (third-order models are not supported)"),
    (re.compile(r"^(\S+) est composante de deux construits \((\S+) et (\S+)\)$"),
     r"\1 is a component of two constructs (\2 and \3)"),
    (re.compile(r"^Chemin (\S+) -> (\S+) : (\S+) est une composante de (\S+) ; relie plutôt (\S+) aux autres construits$"),
     r"Path \1 -> \2: \3 is a component of \4; connect \5 to the other constructs instead"),
    (re.compile(r"^Les interactions impliquant un construit d'ordre supérieur ou ses composantes ne sont pas prises en "
                r"charge$"), "Interactions involving a higher-order construct or its components are not supported"),
    (re.compile(r"^Chemin (\S+) -> (\S+) : variable latente inconnue$"), r"Path \1 -> \2: unknown latent variable"),
    (re.compile(r"^Boucle sur (\S+) interdite$"), r"Self-loop on \1 is not allowed"),
    (re.compile(r"^Mode inconnu pour (\S+) : (.+)$"), r"Unknown mode for \1: \2"),
    (re.compile(r"^(\S+) n'a aucun indicateur$"), r"\1 has no indicator"),
    (re.compile(r"^Interaction (\S+) -> (\S+) : variable latente inconnue (\S+)$"),
     r"Interaction \1 -> \2: unknown latent variable \3"),
    (re.compile(r"^Interaction (\S+) -> (\S+) : ajoute aussi les effets simples \((.+)\)$"),
     r"Interaction \1 -> \2: also add the simple effects (\3)"),
    (re.compile(r"^Le modèle structurel contient un cycle$"), "The structural model contains a cycle"),
    (re.compile(r"^Ligne (\d+) : opérateur manquant \(=~, <~ ou ~\) : (.+)$"),
     r"Line \1: missing operator (=~, <~ or ~): \2"),
    (re.compile(r"^Ligne (\d+) : syntaxe invalide : (.+)$"), r"Line \1: invalid syntax: \2"),
    (re.compile(r"^Ligne (\d+) : (\S+) est déjà défini$"), r"Line \1: \2 is already defined"),
    (re.compile(r"^Ligne (\d+) : interaction invalide (.+) \(forme attendue X:M\)$"),
     r"Line \1: invalid interaction \2 (expected form X:M)"),
    (re.compile(r"^Aucune variable latente définie \(utilise =~ ou <~\)$"), "No latent variable defined (use =~ or <~)"),
    (re.compile(r"^Ligne (\S+) : (\S+) mélange indicateurs et variables latentes$"),
     r"Line \1: \2 mixes indicators and latent variables"),
    (re.compile(r"^(\d+)/(\d+) tirages en échec ont été exclus : .*?( \(inférence NON fiable\))?$", re.S),
     lambda m: f"{m.group(1)}/{m.group(2)} failed draws were excluded: the remaining draws are not representative, "
               f"standard errors and intervals may be biased" + (" (inference NOT reliable)" if m.group(3) else "")),
    (re.compile(r"^(\d+)/(\d+) tirages ont un coefficient ou un chargement > 1 en valeur absolue .*$", re.S),
     r"\1/\2 draws have a coefficient or loading > 1 in absolute value (inadmissible solution, common with PLSc "
     r"and small samples)"),
    (re.compile(r"^(\d+)/(\d+) tirages en échec \(jackknife\)$"), r"\1/\2 failed jackknife subsamples"),
]

EN.update({
    "Les résultats enregistrés ne correspondent pas aux données du projet : ils ont été ignorés. Estime à nouveau le "
    "modèle.": "The saved results do not match the project data: they were ignored. Estimate the model again.",
    "Projet créé avec une autre version d'OpenPLS : les résultats enregistrés ont été ignorés pour éviter toute "
    "différence. Estime à nouveau le modèle.":
        "Project created with another version of OpenPLS: the saved results were ignored to avoid any discrepancy. "
        "Estimate the model again.",
    "Les résultats enregistrés sont illisibles : données et modèle ont été ouverts, estime à nouveau le modèle.":
        "The saved results are unreadable: data and model were opened; estimate the model again.",
})
