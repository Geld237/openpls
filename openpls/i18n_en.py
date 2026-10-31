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
