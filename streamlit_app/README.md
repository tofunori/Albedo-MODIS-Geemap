# 🏔️ Athabasca Glacier Albedo Dashboard

Interface web interactive pour l'analyse de l'albédo du glacier Athabasca utilisant Streamlit.

## 📁 **Structure Organisée** ✅
```
streamlit_app/
├── streamlit_main.py              # Point d'entrée principal ✅
├── requirements.txt               # Dépendances web
├── README.md                      # This file
├── src/                          # Code source modulaire ✅
│   ├── dashboards/               # Pages de tableaux de bord
│   ├── utils/                    # Utilitaires web
│   └── config/                   # Configuration
├── scripts/                      # Scripts utilitaires ✅
│   ├── deploy_streamlit.py       # Script de déploiement
│   ├── fix_pyarrow.py           # Correctif PyArrow
│   └── generate_pixel_data.py   # Génération données
├── docs/setup/                   # Documentation configuration ✅
│   ├── EARTH_ENGINE_SETUP.md    # Configuration Google EE
│   ├── QA_IMPLEMENTATION_SUMMARY.md # Résumé QA
│   └── STREAMLIT_DEPLOYMENT.md  # Guide déploiement
└── assets/credentials/           # Fichiers credentials ✅
    └── leafy-bulwark-*.json     # Clé Google Earth Engine
```

## 🚀 **Démarrage Rapide**

### Installation des dépendances
```bash
# Installation des dépendances web
pip install -r requirements.txt
```

### Configuration Google Earth Engine
Pour la visualisation des pixels MODIS :
```bash
# Authentification Google Earth Engine
earthengine authenticate

# Configuration de la variable d'environnement
export GOOGLE_APPLICATION_CREDENTIALS="assets/credentials/leafy-bulwark-442103-e7-40c3cef68089.json"
```

### Lancement de l'application
```bash
# Depuis le dossier streamlit_app
streamlit run streamlit_main.py
```

### Deploy Online
1. Configure your GitHub URLs in `.streamlit/secrets.toml`
2. Deploy to [Streamlit Cloud](https://share.streamlit.io)
3. Set main file: `streamlit_app/streamlit_dashboard.py`

## 📊 Features
- **Live Data**: Reads CSV files from GitHub URLs
- **Auto-refresh**: Updates every 5 minutes
- **Interactive**: Multiple views (seasonal, spectral, trends)
- **Mobile-friendly**: Responsive design
- **Cached**: 5-minute data caching for performance

## 🔄 Workflow
1. Run analysis → generates CSV files
2. Upload CSV: `python deploy_streamlit.py --upload`
3. Dashboard updates automatically!

## 🔧 Troubleshooting

### PyArrow DLL Issues (Windows)
If you get `DLL load failed` errors with PyArrow:

```bash
# Automated fix
python fix_pyarrow.py

# Manual fix with conda
conda remove pyarrow
conda install -c conda-forge pyarrow

# Manual fix with pip
pip install --force-reinstall pyarrow
```

### Earth Engine Authentication
```bash
earthengine authenticate
```

## 📖 Documentation
See `STREAMLIT_DEPLOYMENT.md` for complete setup instructions.