# MODIS Albedo Analysis - Athabasca Glacier

This project analyzes albedo (surface reflectance) data from the Athabasca Glacier in Alberta, Canada using MODIS satellite imagery and Google Earth Engine.

## Overview

The project uses MODIS Terra and Aqua satellite data to monitor glacier albedo changes over time, with a focus on:
- Daily snow albedo measurements
- Elevation-based zone analysis (accumulation vs ablation zones)
- Seasonal and annual trends
- Impact assessment during wildfire years (2017-2021)

## Key Features

- **Data Source**: MODIS Version 6.1 collections (MOD10A1, MYD10A1, MCD43A3)
- **Study Area**: Athabasca Glacier, Alberta, Canada (52.214°N, 117.245°W)
- **Analysis Zones**: 
  - High elevation zone (accumulation area)
  - Low elevation zone (ablation area)
  - Full glacier extent
- **Time Periods**: Configurable, with focus on recent years and fire impact periods

## Technical Stack

- **Google Earth Engine**: Cloud-based geospatial analysis platform
- **Python Libraries**:
  - `ee` (earthengine-api): GEE Python API
  - `geemap`: Interactive mapping
  - `pandas`: Data manipulation
  - `matplotlib` & `seaborn`: Visualization
  - `numpy`: Numerical computations

## Usage

### Quick Start

```python
# Run default analysis (fire years 2017-2021)
python MODIS_Albedo+Athasbaca.py
```

### Custom Analysis Options

```python
# Example configurations
run_analysis_optimized(
    period='fire_years',    # or 'recent', 'decade', 'sample'
    sampling=None,          # or 'weekly', 'monthly', 'seasonal'
    scale=500,              # resolution in meters (250, 500, 1000)
    use_broadband=False     # True for broadband albedo
)
```

### Available Periods

- `'recent'`: 2020-2024 (last 5 years)
- `'fire_years'`: 2017-2021 (wildfire impact period)
- `'decade'`: 2015-2024 (last 10 years)
- `'sample'`: 2010-2024 (15 years)
- Custom: `('YYYY-MM-DD', 'YYYY-MM-DD')`

## Output

- **CSV File**: Time series data with albedo values by elevation zone
- **Visualizations**:
  - Time series plots by elevation zone
  - Annual trends with linear regression
  - Seasonal cycles
  - Distribution boxplots

## Data Structure

The output CSV contains:
- `date`: Observation date
- `albedo_above`: Mean albedo for high elevation zone
- `albedo_below`: Mean albedo for low elevation zone  
- `albedo_total`: Mean albedo for entire glacier
- `count_*`: Number of valid pixels
- `year`, `month`, `season`: Temporal attributes

## Requirements

- Google Earth Engine account and authentication
- Python 3.7+
- Required packages: see imports in script

## Setup

1. Install required packages:
```bash
pip install earthengine-api geemap pandas matplotlib seaborn numpy folium
```

2. Authenticate GEE (first time only):
```python
ee.Authenticate()
```

3. Run the analysis script

## Notes

- The script uses optimized processing for faster execution
- MODIS collections Version 6.1 (061) are used (Version 6 deprecated in 2023)
- Multiple resolution and sampling options available for performance tuning
- Elevation zones are defined relative to median glacier elevation

## Author

UQTR Master's Research Project