# MCD43A1 BRDF/Albedo Processing Scripts

Suite d'outils Python pour télécharger et traiter les données MODIS MCD43A1 (paramètres BRDF) et calculer l'albédo BSA et WSA.

## Vue d'ensemble

Le produit MCD43A1 contient les paramètres BRDF (Bidirectional Reflectance Distribution Function) qui permettent de calculer l'albédo directement avec un contrôle total sur les méthodes et angles solaires, contrairement au produit MCD43A3 qui fournit les albédos déjà calculés.

### Avantages du MCD43A1 vs MCD43A3

- **Contrôle total** : Choix de l'angle zénithal solaire pour BSA
- **Flexibilité** : Calcul personnalisé des albédos selon vos besoins
- **Transparence** : Compréhension complète du processus de calcul
- **Recherche avancée** : Idéal pour études méthodologiques

## Structure des fichiers

```
mcd43a1_processing/
├── mcd43a1_downloader.py      # Téléchargeur de données LAADS DAAC
├── mcd43a1_processor.py       # Processeur BRDF → Albédo
├── setup_earthdata_auth.py    # Configuration authentification
├── example_workflow.py        # Exemples de workflows complets
├── config_example.json        # Configuration d'exemple
└── README.md                  # Documentation
```

## Installation et configuration

### 1. Prérequis

```bash
# Dépendances Python
pip install rasterio numpy requests pandas

# Outils système (pour curl et gdal)
# Ubuntu/Debian:
sudo apt-get install curl gdal-bin

# macOS:
brew install curl gdal

# Windows: Installer OSGeo4W ou conda
conda install -c conda-forge gdal
```

### 2. Configuration de l'authentification NASA Earthdata

```bash
# Exécuter le script de configuration
python setup_earthdata_auth.py
```

Ou manuellement créer `.netrc` :

```bash
# Créer ~/.netrc avec:
machine urs.earthdata.nasa.gov
    login your_username
    password your_password

machine ladsweb.modaps.eosdis.nasa.gov
    login your_username
    password your_password

# Permissions restrictives
chmod 600 ~/.netrc
```

## Utilisation

### Workflow de base

```bash
# 1. Test rapide
python example_workflow.py --workflow test

# 2. Télécharger données pour une date spécifique
python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03

# 3. Traiter les fichiers téléchargés
python mcd43a1_processor.py --input data/2024/243/*.hdf --bands 1 2 6 7

# 4. Workflow complet Athabasca
python example_workflow.py --workflow athabasca
```

### Téléchargement avancé

```bash
# Télécharger saison de fonte
python mcd43a1_downloader.py \
    --year 2024 \
    --doy-range 152 273 \
    --tiles h10v03 h09v03 \
    --max-files 50

# Lister les fichiers disponibles sans télécharger
python mcd43a1_downloader.py \
    --year 2024 \
    --doy 243 \
    --tiles h10v03 \
    --list-only
```

### Traitement personnalisé

```bash
# Traiter avec angle solaire spécifique
python mcd43a1_processor.py \
    --input data/2024/243/*.hdf \
    --bands 1 2 6 7 \
    --solar-zenith 30.0 \
    --reproject EPSG:32612

# Traitement en lot d'un répertoire
python mcd43a1_processor.py \
    --input-dir data/2024 \
    --process-all \
    --bands 6 7 \
    --summary-report
```

## Configuration avec JSON

Créer un fichier de configuration basé sur `config_example.json` :

```json
{
  "study_areas": {
    "athabasca_glacier": {
      "tiles": ["h10v03"],
      "target_crs": "EPSG:32612",
      "seasons": {
        "melt_season": [152, 273]
      }
    }
  },
  "processing_settings": {
    "default_bands": [1, 2, 6, 7],
    "solar_zenith_angle": 0.0,
    "calculate_shortwave": true
  }
}
```

## Formules d'albédo

### Paramètres BRDF
- **f_iso** : Paramètre isotropique
- **f_vol** : Diffusion volumétrique (Ross kernel)
- **f_geo** : Diffusion géométrique (Li kernel)

### Calculs d'albédo

**White-Sky Albedo (WSA)** - Réflectance hémisphérique-directionnelle :
```
WSA = f_iso + 0.189 × f_vol + 1.377 × f_geo
```

**Black-Sky Albedo (BSA)** - Réflectance directionnelle-hémisphérique :
- **Nadir (θs = 0°)** : `BSA = f_iso`
- **Angles quelconques** : Nécessite les noyaux Ross-Li complets

### Albédo shortwave (large bande)

Combinaison pondérée des bandes MODIS (coefficients Liang 2001) :
- Bande 1 (Rouge) : 0.3973
- Bande 2 (PIR) : 0.2382  
- Bande 3 (Bleu) : 0.3489
- Bande 6 (SWIR2) : 0.0845
- Bande 7 (SWIR3) : 0.0639

## Bandes MODIS recommandées

### Pour glaciers et neige
- **Bandes 1, 2, 6, 7** : Rouge, PIR, SWIR1, SWIR2
- Sensibles aux transitions neige/glace
- Bon pour détection de contamination

### Pour végétation
- **Bandes 1, 2, 3, 4** : Rouge, PIR, Bleu, Vert
- NDVI et indices végétation

### Shortwave complet
- **Bandes 1-7** : Couverture spectrale complète 0.3-3.0 μm

## Projections et mosaïquage

### Reprojection automatique

```bash
# Reprojeter vers WGS84
python mcd43a1_processor.py \
    --input data/*.hdf \
    --reproject EPSG:4326

# Reprojeter vers UTM local
python mcd43a1_processor.py \
    --input data/*.hdf \
    --reproject EPSG:32612  # UTM 12N pour Rocheuses canadiennes
```

### Mosaïquage manuel avec GDAL

```bash
# Créer mosaïque virtuelle
gdalbuildvrt albedo_mosaic.vrt WSA_band6_*.tif

# Convertir en fichier physique
gdal_translate albedo_mosaic.vrt albedo_mosaic.tif

# Reprojection avec gdalwarp
gdalwarp -t_srs EPSG:4326 -r bilinear \
         albedo_mosaic.tif albedo_mosaic_wgs84.tif
```

## Tuiles MODIS pour le Canada

### Glacier Athabasca et Rocheuses canadiennes
- **h10v03** : Glacier Athabasca (primaire)
- **h09v03** : Rocheuses ouest
- **h11v03** : Rocheuses est

### Couverture étendue
- **h09v04** : Alberta ouest
- **h10v04** : Alberta central  
- **h11v04** : Saskatchewan ouest

## Exemples de workflows

### 1. Analyse glacier Athabasca (saison de fonte)

```python
# Configuration pour Athabasca
config = {
    'year': 2024,
    'doy_range': (152, 273),  # 1 juin - 30 septembre
    'tiles': ['h10v03'],
    'bands': [1, 2, 6, 7],    # Rouge, PIR, SWIR1, SWIR2
    'target_crs': 'EPSG:32612'  # UTM 12N
}

# Exécution
python example_workflow.py --workflow athabasca
```

### 2. Analyse multi-annuelle

```python
# 5 ans de données pour analyse de tendances
python example_workflow.py --workflow multi-year
```

### 3. Test rapide du système

```python
# Vérification de la configuration
python example_workflow.py --workflow test
```

## Structure des sorties

```
output_directory/
├── data/                           # Fichiers HDF téléchargés
│   └── 2024/
│       └── 243/
│           └── MCD43A1.A2024243.h10v03.061.*.hdf
├── processed/                      # Produits albédo
│   ├── BSA_band1_A2024243_h10v03.tif
│   ├── WSA_band1_A2024243_h10v03.tif
│   ├── BSA_shortwave_A2024243_h10v03.tif
│   └── WSA_shortwave_A2024243_h10v03.tif
└── processing_summary.json        # Rapport de traitement
```

## Métadonnées et qualité

### Validation automatique
- **Valeurs valides** : -100 à 16000 (avant mise à l'échelle)
- **Facteur d'échelle** : 0.001
- **Valeurs manquantes** : 32767 → NaN
- **Plage albédo** : 0.0 à 1.0 après traitement

### Contrôle qualité
- Masquage automatique des valeurs invalides
- Vérification des plages physiques
- Rapport de couverture par fichier

## Dépannage

### Erreurs d'authentification
```bash
# Vérifier .netrc
ls -la ~/.netrc
cat ~/.netrc

# Reconfigurer si nécessaire
python setup_earthdata_auth.py
```

### Erreurs de téléchargement
```bash
# Test manuel avec curl
curl -n -L -O "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCD43A1/2024/243/MCD43A1.A2024243.h10v03.061.2024252033649.hdf"
```

### Erreurs de traitement
```bash
# Vérifier les sous-datasets
gdalinfo data/2024/243/MCD43A1.*.hdf

# Test avec un seul fichier
python mcd43a1_processor.py --input data/2024/243/MCD43A1.*.hdf --bands 6 --verbose
```

## Références

- **MODIS BRDF/Albedo Product** : [User Guide](https://modis.gsfc.nasa.gov/data/dataprod/mod43.php)
- **LAADS DAAC** : [Archive Access](https://ladsweb.modaps.eosdis.nasa.gov/)
- **Earthdata Login** : [Registration](https://urs.earthdata.nasa.gov/)
- **Liang (2001)** : Coefficients albédo shortwave MODIS

## Support

Pour les problèmes spécifiques :
1. Vérifier les logs avec `--verbose`
2. Tester avec le workflow de test
3. Vérifier l'authentification NASA Earthdata
4. Consulter la documentation MODIS officielle