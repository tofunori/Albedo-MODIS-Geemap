# Méthodologie Détaillée - Analyse MODIS Albédo

## Williamson & Menounos (2021) - Implémentation Rigoureuse

### 1. Extraction des Données MODIS

#### Source de Données
- **Produit**: MOD/MYD10A1 v6.1 (Combined Aqua and Terra)
- **Variable**: Snow Albedo Daily (albédo de neige quotidien)
- **Résolution**: 500m (pixel natif)
- **Projection**: Sinusoidal (conversion automatique vers WGS84)

#### Stratégie d'Extraction Optimisée
```python
def extract_melt_season_data_yearly(start_year, end_year, scale=500):
    """
    Extraction année par année pour éviter les timeouts GEE
    - Période: juin-septembre de chaque année
    - Échantillonnage: tous les 7 jours
    - Filtre qualité: pixels valides uniquement
    """
```

**Innovation**: Contrairement aux méthodes standards qui extraient toute la période d'un coup, notre approche année par année évite les limitations de Google Earth Engine pour les séries temporelles longues.

### 2. Méthodologie Albédo (Adaptation Forest Fire Paper)

#### Acquisition des Données d'Albédo
1. **Produit MODIS MCD43A3 v006**:
   - Albédo bidirectionnel journalier (500m)
   - Bande spectrale: Visible (0.3-0.7 μm)
   - Black-sky albedo (directional hemispherical reflectance)
   - White-sky albedo (bihemispherical reflectance)

2. **Calcul de l'Albédo Réel**:
   ```python
   # Albédo réel = moyenne pondérée black-sky et white-sky
   albedo_actual = (1 - diffuse_fraction) * black_sky + diffuse_fraction * white_sky
   ```

3. **Filtrage Qualité**:
   - QA flags MODIS: uniquement pixels "good quality" (QA = 0)
   - Filtre de couverture nuageuse: MOD35 cloud mask
   - Validation croisée avec NDSI (Normalized Difference Snow Index)

#### Critères de Sélection Spécifiques
1. **Période temporelle**: Saison de fonte uniquement (1er juin - 30 septembre)
2. **Qualité spatiale**: Masque vectoriel précis du glacier Athabasca
3. **Seuils statistiques**:
   - Minimum 5 observations par année
   - Minimum 4 années pour calculs de tendances
   - Exclusion des valeurs aberrantes (> 3 écarts-types)
4. **Critères additionnels Forest Fire Paper**:
   - Angle solaire zénithal < 70° pour minimiser les effets d'ombre
   - Exclusion des pixels mixtes glace/roche (NDSI < 0.4)
   - Moyennes mobiles 5 jours pour réduire le bruit

#### Gestion des Années de Feux
Les années avec impacts de feux de forêt majeurs sont identifiées et analysées séparément:
- **2017**: Feux de Fort McMurray prolongés
- **2018**: Saison de feux extrême en Colombie-Britannique  
- **2021**: Dôme de chaleur et feux record
- **2023**: Feux exceptionnels au Canada

### 3. Traitement de l'Albédo (Forest Fire Paper Methods)

#### Corrections et Normalisation
1. **Correction Topographique**:
   ```python
   # Correction pour l'angle d'incidence solaire sur terrain incliné
   albedo_corrected = albedo_observed * cos(solar_zenith) / cos(local_incidence_angle)
   ```

2. **Normalisation Temporelle**:
   - Standardisation par jour julien pour comparer inter-annuellement
   - Anomalies calculées par rapport à la moyenne 2000-2010 (période de référence)
   - Détrending pour isoler les signaux de court terme

3. **Agrégation Spatiale**:
   - Moyenne pondérée par l'aire des pixels
   - Exclusion des pixels de bordure (buffer 100m)
   - Calcul des percentiles (10e, 50e, 90e) pour caractériser la distribution

#### Métriques d'Albédo Spécifiques
1. **Albédo Intégré de Saison (SIA)**:
   ```python
   SIA = Σ(albedo_daily × days) / total_days
   ```

2. **Date de Minimum d'Albédo (MAD)**:
   - Jour julien où l'albédo atteint son minimum annuel
   - Indicateur de l'intensité maximale de fonte

3. **Durée de Faible Albédo (LAD)**:
   - Nombre de jours avec albédo < 0.4
   - Proxy pour la durée de fonte active

### 4. Tests Statistiques

#### Test de Mann-Kendall
```python
def mann_kendall_test(data):
    """
    Test non-paramétrique pour détecter les tendances monotones
    - H0: Pas de tendance
    - H1: Tendance croissante ou décroissante
    - Seuil: p < 0.05 pour significativité
    """
    tau, p_value = kendalltau(x_sequence, data)
    # Retourne: trend, p_value, tau
```

**Avantages**:
- Robuste aux valeurs aberrantes
- Ne suppose pas de distribution normale
- Adapté aux séries temporelles courtes (≥4 points)

#### Estimateur de Pente de Sen
```python
def sens_slope_estimate(data):
    """
    Estimation robuste de la magnitude de tendance
    - Calcule toutes les pentes possibles entre paires de points
    - Retourne la médiane de ces pentes
    - Moins sensible aux valeurs aberrantes que la régression linéaire
    """
```

### 4. Analyses Multiscalaires

#### Analyse Annuelle Globale
- Moyenne de la saison de fonte par année
- Test de tendance sur la série 2015-2024
- Quantification du changement total et par an

#### Décomposition Mensuelle
- Analyse séparée pour juin, juillet, août, septembre
- Identification des mois avec changements significatifs
- Compréhension de l'évolution intra-saisonnière

#### Impact des Feux de Forêt
- Comparaison années de feux vs années normales
- Test t de Student pour différences de moyennes
- Quantification de l'impact en pourcentage

### 5. Visualisations Scientifiques

#### Graphique Composite 4 Panneaux
```
┌─────────────────┬─────────────────┐
│   Tendance      │   Décomposition │
│   Annuelle      │   Mensuelle     │
├─────────────────┼─────────────────┤
│   Série         │   Résumé        │
│   Temporelle    │   Statistique   │
└─────────────────┴─────────────────┘
```

**Éléments inclus**:
- Barres d'erreur (écart-type)
- Ligne de tendance (pente de Sen)
- Années de feux marquées (étoiles rouges)
- Tests de significativité (p-values)

### 6. Validation et Reproductibilité

#### Critères de Validation
1. **Cohérence temporelle**: Vérification de la continuité des données
2. **Validation spatiale**: Comparaison avec contours glaciaires récents
3. **Contrôle qualité**: Identification automatique des anomalies

#### Reproductibilité
- Code entièrement documenté
- Paramètres configurables
- Sorties standardisées (CSV, PNG, HTML)
- Versioning des analyses

### 7. Comparaison avec la Littérature

#### Williamson & Menounos (2021) - Points de Convergence
✅ **Période d'analyse**: Saison de fonte (juin-septembre)  
✅ **Tests statistiques**: Mann-Kendall + Sen's slope  
✅ **Seuils de significativité**: p < 0.05  
✅ **Gestion des feux**: Analyse séparée des impacts  

#### Améliorations Méthodologiques
🔬 **Extraction optimisée**: Année par année vs extraction globale  
🔬 **Résolution temporelle**: 7 jours vs mensuel  
🔬 **Validation automatique**: Critères de qualité programmés  
🔬 **Visualisation intégrée**: Graphiques prêts pour publication  

### 8. Limitations et Perspectives

#### Limitations Actuelles
- **Résolution spatiale**: 500m peut moyenner les variations locales
- **Période d'étude**: 10 ans, relativement courte pour tendances climatiques
- **Données MODIS**: Sensibilité aux conditions nuageuses

#### Perspectives d'Amélioration
- **Fusion multi-capteurs**: Intégration Landsat pour validation
- **Modélisation**: Couplage avec modèles de bilan énergétique
- **Expansion temporelle**: Extension vers données MODIS complètes (2000-)

### 9. Applications et Impact

#### Contributions Scientifiques
1. **Méthodologique**: Optimisation pour séries temporelles longues
2. **Régionale**: Première analyse systématique Athabasca 2015-2024
3. **Technique**: Workflow reproductible et open-source

#### Applications Pratiques
- **Gestion des parcs**: Suivi des impacts climatiques
- **Recherche glaciologique**: Données de base pour modélisation
- **Enseignement**: Exemple pédagogique d'analyse MODIS rigoreuse