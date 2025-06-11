# Guide de démarrage rapide MCD43A1

## Commandes testées qui fonctionnent :

### 1. Vérifier les fichiers disponibles (sans téléchargement)
```bash
python3 mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --list-only
```

### 2. Configuration de l'authentification NASA Earthdata

#### Option A: Fichier .netrc (recommandé)
Créer le fichier `~/.netrc` avec le contenu suivant :
```
machine urs.earthdata.nasa.gov
    login YOUR_USERNAME
    password YOUR_PASSWORD

machine ladsweb.modaps.eosdis.nasa.gov
    login YOUR_USERNAME
    password YOUR_PASSWORD
```

Puis définir les permissions :
```bash
chmod 600 ~/.netrc
```

#### Option B: Configuration JSON
Créer le fichier `earthdata_credentials.json` :
```json
{
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```

### 3. Exemples de commandes

#### Télécharger un fichier spécifique (après authentification)
```bash
python3 mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --max-files 1
```

#### Télécharger saison de fonte (juin-septembre)
```bash
python3 mcd43a1_downloader.py --year 2024 --doy-range 152 273 --tiles h10v03 --max-files 10
```

#### Traiter les fichiers téléchargés
```bash
python3 mcd43a1_processor.py --input data/2024/243/*.hdf --bands 1 2 6 7
```

#### Workflow complet de test
```bash
python3 example_workflow.py --workflow test
```

## Structure des commandes

### mcd43a1_downloader.py
- `--year YEAR` : Année (obligatoire)
- `--doy DOY` : Jour de l'année spécifique
- `--doy-range START END` : Plage de jours
- `--tiles TILES [TILES ...]` : Tuiles MODIS (obligatoire)
- `--list-only` : Lister seulement, ne pas télécharger
- `--max-files N` : Limite de fichiers à télécharger
- `--output-dir DIR` : Répertoire de sortie

### mcd43a1_processor.py
- `--input FILES` : Fichiers HDF à traiter
- `--input-dir DIR` : Répertoire contenant les HDF
- `--bands [1 2 6 7]` : Bandes MODIS à traiter
- `--solar-zenith ANGLE` : Angle zénithal solaire
- `--reproject CRS` : Reprojeter vers un CRS

## Tuiles utiles pour le Canada
- `h10v03` : Glacier Athabasca
- `h09v03` : Rocheuses ouest du Canada
- `h11v03` : Rocheuses est du Canada

## Saisons utiles (DOY)
- Saison de fonte : 152-273 (1 juin - 30 septembre)
- Été : 152-243 (1 juin - 30 août)
- Automne : 244-273 (31 août - 30 septembre)

## Exemple complet testé

1. **Lister les fichiers disponibles** :
```bash
python3 mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --list-only
```

2. **Télécharger (après configuration .netrc)** :
```bash
python3 mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --max-files 1
```

3. **Traiter** :
```bash
python3 mcd43a1_processor.py --input data/2024/243/*.hdf --bands 6 7
```

## Inscription NASA Earthdata
1. Aller sur https://urs.earthdata.nasa.gov/
2. Créer un compte gratuit
3. Utiliser ces identifiants dans .netrc ou JSON