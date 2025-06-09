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
- **📚 Documentation de référence**:
  - Guide utilisateur officiel: `docs/mod10a1-user-guide.md`
  - Référence des flags QA: `docs/mod10a1-qa-flags.md`
  - Techniques de gap-filling: `docs/modis-gap-filling-interpolation.md` ⚠️ *Exemples en JavaScript*

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

### Terra-Aqua Data Fusion Strategy (Literature-Based)

#### Problématique
Les données MODIS sont disponibles depuis deux satellites:
- **Terra (MOD10A1)**: Passage à 10h30 heure locale
- **Aqua (MYD10A1)**: Passage à 13h30 heure locale

#### Méthodologie Implémentée (Basée sur la Littérature)
Contrairement à une fusion simple (`.merge()`), notre approche suit les meilleures pratiques scientifiques:

1. **Priorité Terra sur Aqua**:
   - Terra préféré car Aqua a des dysfonctionnements de la bande 6 (1600nm)
   - Cette bande est cruciale pour le calcul d'albédo de neige
   - Validation Groenland: MOD10A1 RMS=0.067 vs MYD10A1 RMS=0.075

2. **Gap-filling hierarchique**:
   ```python
   # Pseudocode de la stratégie
   if Terra_disponible and qualité_bonne:
       utiliser Terra
   elif Terra_manquant or nuageux:
       if Aqua_disponible and qualité_bonne:
           utiliser Aqua (gap-filling)
   ```

3. **Composition quotidienne intelligente**:
   - Une seule observation par jour (élimine pseudo-réplication)
   - Score de qualité: Terra=100, Aqua=50 + bonus couverture
   - Mosaïque basée sur le score de qualité le plus élevé

4. **Avantages vs fusion simple**:
   - ✅ Élimine la duplication temporelle (2 obs/jour → 1 composite/jour)
   - ✅ Privilégie les conditions d'observation optimales (10h30)
   - ✅ Suit les standards scientifiques (High Mountain Asia, Greenland studies)
   - ✅ Réduction des biais liés aux différences Terra-Aqua

#### Implémentation Technique
- **Fonction**: `combine_terra_aqua_literature_method()` dans `src/data/extraction.py`
- **Usage**: Automatique dans `extract_time_series_fast()`
- **Statistiques**: Affichage détaillé des observations Terra/Aqua/combinées

#### Références Scientifiques
- High Mountain Asia (2021): "Priority given to Terra product since Aqua MODIS instrument provides less accurate snow maps due to dysfunction of band 6"
- Greenland validation studies: Terra systématiquement plus précis
- Cloud considerations: "Terra preferred for snow retrieval due to cloud-cover considerations"

### Quality Filtering Standards
- **Approche stricte**: QA = 0 uniquement pour tous les produits
- **Pixels minimum**: ≥ 5 pixels valides par observation
- **Plage albédo valide**: 0.0 - 1.0 après mise à l'échelle
- **Période de fonte**: Juin-Septembre uniquement

### MOD10A1 QA Flags Interpretation
- **NDSI_Snow_Cover_Basic_QA**: 0=best, 1=good, 2=ok
- **NDSI_Snow_Cover_Algorithm_Flags_QA**: Bit flags pour screens spécifiques
  - Bit 0: Inland water
  - Bit 1: Low visible reflectance 
  - Bit 2: Low NDSI
  - Bit 3: Temperature/height screen
  - Bit 4: High SWIR reflectance
  - Bit 5-6: Cloud confidence
  - Bit 7: Low illumination
- **Référence complète**: Voir `docs/mod10a1-qa-flags.md` pour détails

### Advanced QA Filtering (Nouveau)
- **Fonction standard**: `mask_modis_snow_albedo_fast()` (Basic QA ≤ 1)
- **Fonction avancée**: `mask_modis_snow_albedo_advanced()` avec Algorithm flags
- **Niveaux de qualité**:
  - `strict`: Basic QA = 0, tous algorithm flags filtrés
  - `standard`: Basic QA ≤ 1, flags critiques filtrés (recommandé)
  - `relaxed`: Basic QA ≤ 2, filtrage minimal
- **Usage dans workflows**:
  ```python
  run_melt_season_analysis_williamson(
      use_advanced_qa=True,    # Active le filtrage avancé
      qa_level='standard'      # Niveau de qualité
  )
  ```
- **Avantages**: Meilleure robustesse statistique, conformité Williamson & Menounos (2021)

### QA Tracking System (Nouveau)
- **Filenames avec QA**: Les fichiers de sortie incluent automatiquement les paramètres QA
  - Format: `athabasca_melt_season_data_advanced_standard.csv`
  - Format: `athabasca_melt_season_results_basic_relaxed.csv`
- **Colonnes QA dans les données**:
  - `qa_advanced`: Boolean (True/False)
  - `qa_level`: String ('strict', 'standard', 'relaxed')  
  - `qa_description`: String lisible ("Advanced QA, standard level")
- **Auto-détection**: Le système trouve automatiquement les fichiers QA les plus récents
- **Traçabilité**: Chaque analyse peut être reproduite avec les mêmes paramètres QA
- **Exemple de filenames**:
  - `athabasca_melt_season_data_advanced_standard.csv` - Données avec Advanced QA, niveau standard
  - `athabasca_melt_season_results_basic_strict.csv` - Résultats avec Basic QA, niveau strict

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

## Data Processing Techniques

### Gap-Filling and Interpolation
- **Problème**: Données MODIS manquantes dues aux nuages, ombres, etc.
- **Solutions disponibles**: 
  - Interpolation temporelle
  - Moyennes mobiles
  - Fusion multi-capteurs (Terra + Aqua)
- **⚠️ Note importante**: Le document `docs/modis-gap-filling-interpolation.md` contient des exemples en **JavaScript (Google Earth Engine)**. Pour l'implémentation Python, adapter la syntaxe en utilisant:
  - `ee.ImageCollection` au lieu de `ee.ImageCollection()`
  - Méthodes Python équivalentes pour les fonctions JavaScript
  - Attention aux différences de syntaxe pour les callbacks et lambdas

## Recent Updates
- Harmonisation des filtres qualité MCD43A3 avec MOD10A1 (QA = 0 uniquement)
- Correction du clipping DEM avec le masque du glacier
- Ajout des données annuelles dans les résultats hypsométriques
- Amélioration de la visualisation des bandes d'élévation
- Clarification: MCD43A3 est un produit QUOTIDIEN (fenêtre mobile 16 jours)
- **QA Tracking System**: Filenames and data now include QA settings for reproducibility

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

## Critical Bug Fixes & Solutions

### ⚠️ STREAMLIT APP CRASHES - INFINITE RECURSION BUG (SOLVED)

**Problem**: Streamlit app was dying silently during data processing at ~65% completion (CSV export phase).

**Root Cause**: Infinite recursion caused by dangerous monkey-patching of pandas DataFrame.to_csv()

```python
# DEADLY CODE (NEVER DO THIS):
pd.DataFrame.to_csv = safe_to_csv  # Monkey patch

def safe_to_csv(self, path_or_buf=None, **kwargs):
    return safe_csv_write(self, str(path_or_buf), ...)

def safe_csv_write(df, file_path, ...):
    df.to_csv(temp_file, ...)  # <-- CALLS MONKEY-PATCHED VERSION = INFINITE RECURSION!
```

**Death Cycle**:
1. `safe_csv_write()` called
2. Calls `df.to_csv()` 
3. Monkey patch redirects back to `safe_csv_write()` 
4. **INFINITE RECURSION**
5. Stack overflow in pandas C extension
6. **SILENT PROCESS DEATH** (no Python exception)
7. Streamlit loses connection → apparent "crash"

**✅ SOLUTION**: 
- **NEVER monkey-patch pandas methods** in workflows
- Use direct calls to original pandas methods:
```python
# SAFE CODE:
import pandas as pd
original_to_csv = pd.DataFrame.to_csv
original_to_csv(df, file_path, index=False, encoding='utf-8')
```

**Files Fixed**:
- `src/workflows/melt_season.py`: Removed monkey patching, fixed fallback functions
- `src/utils/file_utils.py`: Added explicit original method calls
- `streamlit_app/src/utils/processing_manager.py`: Enhanced error handling

**Result**: Streamlit app now completes full workflow without crashes ✅

### File Permission Issues on Windows (SOLVED)

**Problem**: Windows file locking issues with CSV exports

**Solutions Applied**:
1. **Atomic file operations**: Write to `.tmp` files, then rename
2. **Retry mechanisms**: Multiple attempts with backoff
3. **Safe path resolution**: Cross-platform path normalization
4. **Backup/restore**: Safe file replacement on Windows

**Implementation**: `src/utils/file_utils.py` - `safe_csv_write()` function

### Import Path Issues in Streamlit Context (SOLVED)

**Problem**: Different import paths when running from Streamlit vs direct execution

**Solution**: Fallback import strategy with inline function definitions
```python
try:
    from utils.file_utils import safe_csv_write
except ImportError:
    try:
        from src.utils.file_utils import safe_csv_write
    except ImportError:
        # Inline fallback definitions
        def safe_csv_write(...): ...
```

## Debugging Guidelines

### When Streamlit App Crashes/Dies:
1. **Check for infinite recursion** - especially in monkey-patched methods
2. **Look for silent C extension crashes** - no Python traceback
3. **Monitor memory usage** - but crashes can happen with low memory too
4. **Add progress tracking** - identify exact failure point
5. **Use threading timeouts** - detect infinite hangs

### Warning Signs:
- Process dies at exact same point repeatedly
- No Python exception/traceback shown
- "Connection lost" or similar Streamlit messages
- High CPU usage with no progress

### Prevention:
- ❌ Never monkey-patch pandas/numpy methods
- ✅ Use explicit method references: `pd.DataFrame.to_csv(df, path)`
- ✅ Add comprehensive error handling in workflows
- ✅ Use timeouts for potentially hanging operations
- ✅ Test with small datasets first