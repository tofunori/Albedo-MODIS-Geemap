# 🏔️ Athabasca Glacier Albedo Dashboard

Live interactive web dashboard for Athabasca Glacier albedo analysis using MODIS data.

## 📁 Folder Structure
```
streamlit_app/
├── streamlit_dashboard.py     # Main Streamlit web app
├── deploy_streamlit.py        # Deployment automation script
├── STREAMLIT_DEPLOYMENT.md    # Complete deployment guide
├── README.md                  # This file
└── .streamlit/
    ├── config.toml           # Streamlit configuration
    └── secrets.toml          # Data source URLs (configure these!)
```

## 🚀 Quick Start

### Run Locally
```bash
# From project root
cd streamlit_app
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

## 📖 Documentation
See `STREAMLIT_DEPLOYMENT.md` for complete setup instructions.