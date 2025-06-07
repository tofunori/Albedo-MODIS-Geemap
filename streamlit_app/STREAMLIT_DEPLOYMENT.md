# Streamlit Dashboard Deployment Guide

## 🎯 Overview
This guide shows how to deploy your Athabasca Glacier Albedo Analysis as a live web dashboard that automatically updates when you rerun your analysis.

## 🚀 Quick Start

### 1. Local Testing
```bash
# Install Streamlit (if not already installed)
pip install -r requirements.txt

# Navigate to streamlit app folder
cd streamlit_app

# Run dashboard locally
streamlit run streamlit_dashboard.py

# Open in browser: http://localhost:8501
```

### 2. Deploy to Streamlit Cloud (Free)

#### Prerequisites
- GitHub account
- Your code pushed to a GitHub repository

#### Steps:
1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Add Streamlit dashboard"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Set main file path: `streamlit_app/streamlit_dashboard.py`
   - Click "Deploy"

3. **Configure data sources:**
   - Edit `streamlit_app/.streamlit/secrets.toml`
   - Update URLs to match your GitHub repository:
   ```toml
   [data_sources]
   mcd43a3_url = "YOUR-USERNAME/YOUR-REPO/main/outputs/csv/athabasca_mcd43a3_results.csv"
   ```

## 🔄 Automatic Updates

### Method 1: Manual Upload
After running your analysis:
```bash
cd streamlit_app && python deploy_streamlit.py --upload
```

### Method 2: Automatic GitHub Actions
1. **Setup workflow:**
   ```bash
   python deploy_streamlit.py --create-workflow
   ```

2. **Commit and push:**
   ```bash
   git add .github/workflows/deploy-streamlit.yml
   git commit -m "Add auto-deployment workflow"
   git push
   ```

Now every time you push CSV updates, the dashboard updates automatically!

## 📊 Dashboard Features

### Interactive Views
- **🌊 Seasonal Evolution**: Daily albedo patterns by year
- **📊 Visible vs NIR**: Annual comparison scatter plot
- **🌈 Spectral Bands**: All MODIS bands visualization
- **📈 Vis/NIR Ratio**: Temporal ratio trends

### Real-time Controls
- ✅ **Auto-refresh**: Updates every 5 minutes
- 🔄 **Manual refresh**: Force reload data
- 📅 **Year filtering**: Select specific years
- 📈 **Multi-dataset**: Switch between MCD43A3, melt season, hypsometric

### Data Sources
- **Online**: Reads CSV files from GitHub URLs
- **Fallback**: Uses local files if online unavailable
- **Caching**: 5-minute cache for performance

## 🛠️ Configuration

### Data Source URLs
Edit `streamlit_dashboard.py` line 19-31:
```python
DATA_SOURCES = {
    'mcd43a3': {
        'url': 'https://raw.githubusercontent.com/YOUR-USERNAME/YOUR-REPO/main/outputs/csv/athabasca_mcd43a3_results.csv',
        # ...
    }
}
```

### Styling
Edit `.streamlit/config.toml` for custom theme:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

## 🔧 Integration with Analysis

### Automatic Upload
Add to your analysis scripts:
```python
# At the end of your analysis
import subprocess
subprocess.run(['python', 'deploy_streamlit.py', '--upload', '--message', 'Updated analysis results'])
```

### Modified Workflows
Update `src/workflows/broadband_albedo.py` (example):
```python
def run_complete_analysis():
    # ... existing analysis code ...
    
    # Auto-upload results
    if os.path.exists('deploy_streamlit.py'):
        subprocess.run(['python', 'deploy_streamlit.py', '--upload'])
        print("🌐 Dashboard updated!")
```

## 🌐 Live Dashboard URLs

Once deployed, your dashboard will be available at:
- **Streamlit Cloud**: `https://YOUR-APP-NAME.streamlit.app`
- **Local**: `http://localhost:8501`

## 📋 Checklist for Deployment

### Before First Deployment:
- [ ] Update data source URLs in `streamlit_dashboard.py`
- [ ] Test locally: `streamlit run streamlit_dashboard.py`
- [ ] Push code to GitHub
- [ ] Deploy on Streamlit Cloud

### For Each Analysis Update:
- [ ] Run your analysis (generates CSV files)
- [ ] Upload CSV files: `cd streamlit_app && python deploy_streamlit.py --upload`
- [ ] Dashboard updates automatically (5-min cache)

### Optional Automation:
- [ ] Setup GitHub Actions workflow
- [ ] Integrate upload into analysis scripts
- [ ] Configure auto-refresh intervals

## ⚡ Performance Tips

1. **CSV Size**: Keep CSV files under 25MB for best performance
2. **Caching**: Use Streamlit's `@st.cache_data` for expensive operations
3. **Filtering**: Pre-filter data before visualization
4. **Memory**: Use `st.cache_data(ttl=300)` to refresh cache every 5 minutes

## 🐛 Troubleshooting

### Common Issues:

**"Data loading failed"**
- Check CSV file URLs are correct
- Verify files exist in GitHub repository
- Test URLs manually in browser

**"Dashboard not updating"**
- Clear cache: Click "Refresh Data Now"
- Check CSV files were uploaded to GitHub
- Verify timestamp in dashboard footer

**"Deployment failed"**
- Check `requirements.txt` includes all dependencies
- Verify Streamlit Cloud has access to repository
- Check logs in Streamlit Cloud console

### Debug Mode:
```bash
# Run with debug logging
streamlit run streamlit_dashboard.py --logger.level=debug
```

## 🎉 Success!

Your dashboard is now live and will automatically update when you rerun your analysis. Share the URL with colleagues and stakeholders for real-time access to your glacier albedo analysis results!