# 🏔️ Athabasca Glacier Albedo Dashboard

Live interactive web dashboard for Athabasca Glacier albedo analysis using MODIS data.

## 📁 Folder Structure
```
streamlit_app/
├── streamlit_dashboard.py         # Original monolithic web app (1800+ lines)
├── streamlit_dashboard_modular.py # New modular web app (recommended)
├── deploy_streamlit.py            # Deployment automation script
├── STREAMLIT_DEPLOYMENT.md        # Complete deployment guide
├── README.md                      # This file
├── src/                           # Modular components (NEW!)
│   ├── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_loader.py         # Data loading from URLs/local files
│   │   ├── ee_utils.py            # Earth Engine initialization & pixel extraction
│   │   └── maps.py                # Folium mapping and albedo visualization
│   └── dashboards/
│       ├── __init__.py
│       └── mcd43a3_dashboard.py   # MCD43A3 spectral analysis dashboard
└── .streamlit/
    ├── config.toml               # Streamlit configuration
    └── secrets.toml              # Data source URLs (configure these!)
```

## 🚀 Quick Start

### Install Dependencies
```bash
# From project root - install required packages
pip install streamlit-folium earthengine-api

# Or if you have conda
conda install -c conda-forge streamlit-folium
pip install earthengine-api
```

### Setup Earth Engine Authentication
For MODIS pixel visualization to work:
```bash
# Authenticate with Google Earth Engine
earthengine authenticate

# This will open a web browser for Google account authentication
# Follow the prompts and paste the verification code
```

### Run Locally
```bash
# From project root
cd streamlit_app

# Run modular version (recommended)
streamlit run streamlit_dashboard_modular.py

# Or run original version
streamlit run streamlit_dashboard.py
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