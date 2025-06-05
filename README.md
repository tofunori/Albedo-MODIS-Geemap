# MODIS Albedo Analysis - Athabasca Glacier

This project analyzes albedo (surface reflectance) data from the Athabasca Glacier in Alberta, Canada using MODIS satellite imagery and Google Earth Engine. The codebase is organized in a modular structure for better maintainability and reusability.

## 🏔️ Project Overview

The project uses MODIS Terra and Aqua satellite data to monitor glacier albedo changes over time, with a focus on:
- Daily snow albedo measurements using MODIS Version 6.1 collections
- Seasonal and annual trend analysis
- Melt season dynamics (June-September)
- Wildfire impact assessment (2017-2021 period)
- Advanced data visualization and statistical analysis

## 📁 File Structure and Descriptions

### Core Analysis Files

#### `main.py` - Main Analysis Runner
**Purpose**: Central orchestration script with convenience functions for different analysis types.

**Key Functions**:
- `run_analysis_optimized()` - Main analysis function with customizable parameters
- `quick_recent_analysis()` - Rapid analysis of 2019-2024 period
- `fire_impact_analysis()` - Wildfire impact assessment (2017-2021)
- `decade_trend_analysis()` - Long-term trend analysis (2015-2024)
- `interactive_menu()` - User-friendly menu system

**Usage**: 
```python
python main.py  # Runs automatic recent analysis
# or
from main import quick_recent_analysis
df = quick_recent_analysis()
```

#### `config.py` - Configuration and Parameters
**Purpose**: Central configuration management for the entire project.

**Contents**:
- Glacier geometry setup from GeoJSON file
- Time period definitions (recent, fire_years, decade, full_recent)
- MODIS collection references (MOD10A1, MYD10A1, MCD43A3 v6.1)
- Spatial resolution options (250m, 500m, 1000m)
- Temporal sampling configurations
- Fire year annotations for visualization

**Key Variables**:
- `athabasca_roi` - Glacier region of interest geometry
- `PERIODS_RAPIDE` - Predefined time periods
- `SCALE_OPTIONS` - Spatial resolution choices
- `FIRE_YEARS` - Major wildfire years for annotations

#### `data_processing.py` - MODIS Data Processing
**Purpose**: Core functions for extracting and processing MODIS satellite data.

**Key Functions**:
- `mask_modis_snow_albedo_fast()` - Quality masking for daily snow albedo
- `mask_modis_broadband_albedo_fast()` - Processing for broadband albedo
- `extract_time_series_fast()` - Main data extraction from Google Earth Engine
- `smooth_timeseries()` - Data smoothing (rolling average, Savitzky-Golay, spline)

**Features**:
- Optimized Google Earth Engine operations
- Quality control and cloud masking
- Multiple temporal smoothing algorithms
- Automatic DataFrame creation with temporal attributes

#### `visualization.py` - Plotting and Graphics
**Purpose**: Comprehensive visualization functions for data analysis and presentation.

**Key Functions**:
- `plot_albedo_evolution_enhanced()` - Detailed time series with trends and annotations
- `plot_albedo_fast()` - Multi-panel dashboard with statistics

**Features**:
- Fire year annotations and seasonal markers
- Trend analysis with linear regression
- Confidence intervals and statistical overlays
- Publication-quality graphics with customizable styling
- Automatic saving of high-resolution plots

#### `melt_season.py` - Specialized Melt Season Analysis
**Purpose**: Focused analysis of June-September melt season dynamics.

**Key Functions**:
- `analyze_melt_season()` - Comprehensive melt season statistics by year
- `plot_melt_season_analysis()` - Specialized multi-panel melt season visualization

**Analysis Features**:
- Inter-annual melt season comparisons
- Melt timing and intensity metrics
- Advanced curve smoothing for seasonal patterns
- Variability and extreme year identification

#### `analysis.py` - Statistical Analysis Functions
**Purpose**: General statistical utilities and trend analysis functions.

**Key Functions**:
- `calculate_annual_trends()` - Long-term trend analysis with R² calculations
- `calculate_seasonal_statistics()` - Seasonal pattern analysis
- `identify_extreme_years()` - Anomaly detection using statistical thresholds

### Supporting Files

#### `requirements.txt` - Python Dependencies
**Purpose**: Specifies all required Python packages and versions.

**Key Packages**:
- `earthengine-api` - Google Earth Engine Python API
- `geemap` - Interactive Earth Engine mapping
- `pandas` - Data manipulation and analysis
- `matplotlib`, `seaborn` - Visualization libraries
- `scipy` - Scientific computing and signal processing
- `numpy` - Numerical computations

#### `__init__.py` - Package Initialization
**Purpose**: Makes the directory a Python package and provides convenient imports.

**Features**:
- Exposes main functions for easy importing
- Package metadata and version information
- Simplified API for external use

#### `Athabasca_mask_2023 (1).geojson` - Glacier Boundary
**Purpose**: Precise glacier outline for spatial analysis.

**Contents**:
- High-resolution glacier boundary polygon
- Geographic coordinates in WGS84
- Used for masking MODIS data to glacier extent

#### `MODIS_Albedo+Athasbaca.py` - Original Monolithic File
**Purpose**: Original complete analysis script (kept for reference).

**Status**: Legacy file containing all functionality before modularization. Preserved for comparison and backup purposes.

## 🚀 Quick Start Guide

### 1. Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up Google Earth Engine (first time only)
python -c "import ee; ee.Authenticate()"
```

### 2. Basic Usage
```python
# Run automatic analysis
python main.py

# Or use specific functions
from main import quick_recent_analysis, fire_impact_analysis

# Recent years analysis (2019-2024)
df_recent = quick_recent_analysis()

# Fire impact analysis (2017-2021)
df_fire = fire_impact_analysis()
```

### 3. Custom Analysis
```python
from main import run_analysis_optimized

# Custom parameters
df = run_analysis_optimized(
    period='decade',        # Time period
    sampling=None,          # Temporal sampling
    scale=500,              # Spatial resolution (meters)
    use_broadband=False,    # Data type
    smoothing='savgol'      # Smoothing method
)
```

### 4. Individual Modules
```python
# Use individual components
from data_processing import extract_time_series_fast
from visualization import plot_albedo_evolution_enhanced
from melt_season import analyze_melt_season

# Extract data
df = extract_time_series_fast('2020-01-01', '2023-12-31')

# Analyze melt season
melt_stats, df_melt = analyze_melt_season(df)

# Create visualization
plot_albedo_evolution_enhanced(df, save_path='albedo_trend.png')
```

## 📊 Analysis Options

### Time Periods
- **`'recent'`**: 2020-2024 (last 5 years)
- **`'fire_years'`**: 2017-2021 (wildfire impact period)
- **`'decade'`**: 2015-2024 (last 10 years)
- **`'full_recent'`**: 2019-2024 (6 years for better trends)
- **Custom**: `('YYYY-MM-DD', 'YYYY-MM-DD')`

### Spatial Resolutions
- **250m**: Native MODIS resolution (slower, high detail)
- **500m**: Balanced performance (recommended)
- **1000m**: Fast processing (for testing)

### Temporal Sampling
- **None**: All available images
- **Weekly**: One image per week
- **Monthly**: One image per month
- **Seasonal**: One image per season

## 📈 Output Files

### Data Files
- **`athabasca_albedo_[period]_[resolution]m.csv`** - Complete time series data
- **`athabasca_melt_season_[period]_[resolution]m.csv`** - Melt season subset

### Visualizations
- **`evolution_albedo_[period]_[resolution]m.png`** - Enhanced time series plot
- **`melt_season_analysis_[period]_[resolution]m.png`** - Melt season analysis

### Data Structure
Each CSV contains:
- `date` - Observation date
- `albedo_mean` - Mean albedo for entire glacier
- `albedo_stdDev` - Spatial variability
- `albedo_min/max` - Range of values
- `pixel_count` - Number of valid MODIS pixels
- `year`, `month`, `season` - Temporal attributes

## 🔧 Technical Details

### Data Sources
- **MODIS/061/MOD10A1** - Terra daily snow albedo
- **MODIS/061/MYD10A1** - Aqua daily snow albedo  
- **MODIS/061/MCD43A3** - Combined broadband albedo

### Processing Features
- Quality control and cloud masking
- Temporal gap filling and smoothing
- Statistical trend analysis
- Fire year impact assessment
- Seasonal decomposition

### Performance Optimizations
- Parallel Google Earth Engine operations
- Configurable spatial and temporal sampling
- Efficient memory management
- Optimized visualization rendering

## 📝 Research Context

**Institution**: Université du Québec à Trois-Rivières (UQTR)  
**Project**: Master's Research on Glacier Albedo Dynamics  
**Study Area**: Athabasca Glacier, Alberta, Canada (52.214°N, 117.245°W)  
**Focus**: Climate change impacts and wildfire effects on glacier surface properties

## 🤝 Contributing

The modular structure facilitates collaboration:
- Each module has single responsibility
- Functions can be imported independently
- Easy to add new analysis types
- Clear separation of concerns

## 📄 License

UQTR Master's Research Project - Academic Use