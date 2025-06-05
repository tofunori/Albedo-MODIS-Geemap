# 🏔️ Analyse MODIS Albedo - Glacier Athabasca

## Projet de Maîtrise UQTR - Version Finale Épurée

### 🎯 Interface Simple - 2 Options

```bash
python simple_main.py
```

**Menu:**
1. **Analyse saison de fonte** (Williamson & Menounos 2021) ✅
2. **Cartographie interactive** ✅

### 📊 Résultats

- **CSV**: `outputs/csv/athabasca_melt_season_focused_data.csv`
- **Figure**: `figures/melt_season/athabasca_melt_season_comprehensive_analysis.png`
- **Carte**: `maps/interactive/glacier_map_YYYY-MM-DD.html`

### 🔧 Structure Épurée

```
📁 Projet Final
├── simple_main.py              # 🎯 MENU PRINCIPAL
├── requirements.txt            # 📦 Dépendances
├── Athabasca_mask_2023.geojson # 🗺️ Géométrie glacier
│
├── src/                        # 📚 Modules essentiels
│   ├── trend_analysis.py       # 📊 Analyse Williamson
│   ├── mapping.py             # 🗺️ Cartographie
│   ├── config.py              # ⚙️ Configuration
│   ├── data_processing.py     # 🔄 Traitement MODIS
│   ├── visualization.py       # 📈 Graphiques
│   └── paths.py              # 📁 Chemins
│
├── outputs/csv/               # 📄 Données finales
├── figures/melt_season/       # 📊 Graphiques pour mémoire
├── maps/interactive/          # 🗺️ Cartes HTML
├── docs/methodology.md        # 📚 Méthodologie
└── Jupyter/                   # 📓 Notebooks (optionnel)
```

### 🚀 Installation

```bash
pip install -r requirements.txt
earthengine authenticate
python simple_main.py
```

### 🎓 Pour le Mémoire

1. **Analyse**: Option 1 → Récupérer PNG et CSV
2. **Cartographie**: Option 2 → Cartes pour présentation
3. **Méthodologie**: Consulter `docs/methodology.md`

**Projet optimisé et prêt pour soutenance!** 🎉