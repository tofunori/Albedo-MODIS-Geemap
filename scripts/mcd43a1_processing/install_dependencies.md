# Installation des dépendances MCD43A1

## État actuel
✅ **Downloader fonctionne** - peut lister les fichiers disponibles  
❌ **Processor nécessite** - numpy, rasterio, GDAL  
❌ **GDAL manquant** - nécessaire pour traiter les fichiers HDF  

## Solution recommandée avec conda

### Dans PowerShell (votre environnement geo-env) :

```powershell
# Activer votre environnement existant
conda activate geo-env

# Installer les dépendances manquantes
conda install -c conda-forge numpy rasterio gdal

# Ou installer toutes les dépendances recommandées
conda install -c conda-forge numpy rasterio gdal pandas scipy matplotlib plotly

# Vérifier l'installation
python -c "import numpy, rasterio; print('✅ Dependencies OK')"
gdalinfo --version
```

### Alternative avec pip (si conda ne fonctionne pas) :

```powershell
# Dans votre environnement geo-env
pip install numpy rasterio pandas requests

# Pour GDAL, utiliser la version conda (plus fiable)
conda install -c conda-forge gdal
```

## Test après installation

```powershell
# Aller dans le dossier
cd "D:\UQTR\Maitrîse\Code\Albedo MODIS Geemap\scripts\mcd43a1_processing"

# Tester le système
python test_system.py

# Si tout est OK, tester le processeur
python mcd43a1_processor.py --help
```

## Commandes testées qui fonctionnent DÉJÀ

### 1. Lister fichiers disponibles (PAS d'authentification nécessaire)
```powershell
python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --list-only
```

### 2. Voir l'aide du téléchargeur
```powershell
python mcd43a1_downloader.py --help
```

## Prochaines étapes après installation des dépendances

1. **Configurer authentification NASA Earthdata** (gratuit)
   - Aller sur https://urs.earthdata.nasa.gov/ 
   - Créer compte gratuit
   - Configurer .netrc ou JSON

2. **Télécharger un fichier test**
   ```powershell
   python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --max-files 1
   ```

3. **Traiter le fichier téléchargé**
   ```powershell
   python mcd43a1_processor.py --input data/2024/243/*.hdf --bands 6 7
   ```

## Environnement recommandé

Votre environnement `geo-env` devrait avoir après installation :
- ✅ Python 3.x
- ✅ requests (pour téléchargement)
- ➕ numpy (calculs numériques)
- ➕ rasterio (lecture/écriture raster)
- ➕ gdal (outils géospatiaux)
- ➕ pandas (manipulation données)

## Résolution de problèmes

### Si conda install ne fonctionne pas :
```powershell
# Mettre à jour conda
conda update conda

# Essayer avec mamba (plus rapide)
conda install mamba -c conda-forge
mamba install -c conda-forge numpy rasterio gdal
```

### Si erreurs de conflits :
```powershell
# Créer un nouvel environnement dédié
conda create -n mcd43a1-env python=3.9 numpy rasterio gdal pandas requests -c conda-forge
conda activate mcd43a1-env
```