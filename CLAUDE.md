# Claude Code Project Context

## Project Overview
Analyse de l'albédo du glacier Athabasca utilisant les données MODIS et Google Earth Engine.
Implémentation de la méthodologie de Williamson & Menounos (2021) pour l'analyse hypsométrique.

## Key Commands

### Testing & Validation
```bash
# Run main analysis
python simple_main.py

# Check code quality
python -m pylint src/
python -m flake8 src/
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Project Structure
- `src/`: Code source principal
  - `analysis/`: Modules d'analyse statistique et hypsométrique
  - `data/`: Extraction de données GEE
  - `visualization/`: Création de graphiques et cartes
  - `workflows/`: Flux de travail complets
- `outputs/`: Résultats CSV
- `figures/`: Graphiques générés
- `maps/`: Cartes interactives HTML

## Key Technical Details

### MODIS Data Products

#### MOD10A1/MYD10A1 (Daily Snow Albedo)
- Collections: MODIS/061/MOD10A1 (Terra), MODIS/061/MYD10A1 (Aqua)
- Résolution: 500m
- Bande principale: Snow_Albedo_Daily_Tile
- Bande qualité: NDSI_Snow_Cover_Basic_QA
- Filtre qualité: QA = 0 uniquement (best quality)
- Plage valide: 5-99 (avant mise à l'échelle)
- Facteur d'échelle: 0.01
- Usage: Analyse quotidienne de l'albédo de neige

#### MCD43A3 (Daily Broadband Albedo - 16-day moving window)
- Collection: MODIS/061/MCD43A3
- Résolution: 500m
- **Résolution temporelle**: DAILY product (not 16-day composite!)
  - Utilise une fenêtre mobile de 16 jours centrée sur chaque jour
  - La date du produit = centre de la fenêtre (9e jour)
  - Pondération temporelle vers le jour central
  - Fournit des valeurs d'albédo quotidiennes avec robustesse statistique
- Bandes spectrales:
  - Albedo_BSA_Band1-4 (bandes spectrales individuelles)
  - Albedo_BSA_vis (albédo visible large bande)
  - Albedo_BSA_nir (albédo proche infrarouge)
  - Albedo_BSA_shortwave (albédo courtes longueurs d'onde)
- Bandes qualité: BRDF_Albedo_Band_Mandatory_Quality_*
- Filtre qualité: QA = 0 uniquement (full BRDF inversions)
- Facteur d'échelle: 0.001
- Usage: Analyse spectrale quotidienne suivant Williamson & Menounos (2021)

### Quality Filtering Standards
- **Approche stricte**: QA = 0 uniquement pour tous les produits
- **Pixels minimum**: ≥ 5 pixels valides par observation
- **Plage albédo valide**: 0.0 - 1.0 après mise à l'échelle
- **Période de fonte**: Juin-Septembre uniquement

### Analyse Hypsométrique
- Bandes d'élévation: ±100m autour de l'élévation médiane
- DEM: SRTM clippé avec le masque du glacier
- Tests statistiques: Mann-Kendall et pente de Sen

### Important Files
- `config.py`: ROI du glacier Athabasca
- `paths.py`: Gestion des chemins de fichiers
- `simple_main.py`: Point d'entrée principal

## Common Issues & Solutions

### DEM Masking
Le DEM doit être clippé avec `athabasca_roi` avant utilisation:
```python
srtm_clipped = srtm.clip(athabasca_roi)
```

### Memory Management
Extraction année par année pour éviter les timeouts GEE.

## Data Processing Workflows

### Extraction de données
1. **MOD10A1/MYD10A1**: Extraction année par année via `extract_melt_season_data_yearly()`
2. **MCD43A3**: Extraction via `extract_mcd43a3_data()` dans `broadband_albedo.py`
3. **Fusion**: Les données Terra et Aqua sont fusionnées pour MOD10A1/MYD10A1

### Analyses principales
1. **Tendances temporelles**: Analyse des changements d'albédo sur la période d'étude
2. **Analyse hypsométrique**: Variation de l'albédo selon l'élévation (Williamson & Menounos 2021)
3. **Analyse spectrale**: Comparaison visible vs NIR pour détecter la contamination
4. **Statistiques saisonnières**: Focus sur la période de fonte (juin-septembre)

## Recent Updates
- Harmonisation des filtres qualité MCD43A3 avec MOD10A1 (QA = 0 uniquement)
- Correction du clipping DEM avec le masque du glacier
- Ajout des données annuelles dans les résultats hypsométriques
- Amélioration de la visualisation des bandes d'élévation
- Clarification: MCD43A3 est un produit QUOTIDIEN (fenêtre mobile 16 jours)

## Code Organization Guidelines

### File Length Management
- **Maximum file length**: Garder les fichiers Python sous 500 lignes si possible
- **Diviser les longs fichiers**: Quand un fichier dépasse 500-700 lignes, refactoriser en modules
- **Structure modulaire**: Séparer les responsabilités en modules logiques:
  - Extraction/traitement de données
  - Fonctions d'analyse
  - Visualisation/graphiques
  - Orchestration du workflow principal

### Stratégie de Refactorisation
- **Exemple 1**: `broadband_albedo.py` (1000+ lignes) divisé en:
  - `src/data/mcd43a3_extraction.py` - Fonctions d'extraction
  - `src/analysis/spectral_analysis.py` - Méthodes d'analyse
  - `src/visualization/spectral_plots.py` - Fonctions de visualisation
  - `src/workflows/broadband_albedo.py` - Workflow principal (~200 lignes)

- **Exemple 2**: `spectral_plots.py` (967 lignes) divisé en:
  - `src/visualization/static_plots.py` (604 lignes) - Graphiques matplotlib
  - `src/visualization/interactive_plots.py` (369 lignes) - Tableaux de bord plotly
  - `src/visualization/spectral_plots.py` (26 lignes) - Interface principale
  
### Avantages de cette approche:
- ✅ Fichiers maintenables et lisibles
- ✅ Séparation claire des responsabilités
- ✅ Backwards compatibility des imports
- ✅ Possibilité d'extension future
- **Bénéfices**: Meilleure maintenabilité, réutilisabilité et tests

### Principes de Code
- Un fichier = une responsabilité claire
- Imports explicites entre modules
- Documentation des interfaces entre modules
- Tests unitaires plus faciles avec des modules courts