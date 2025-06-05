"""
Path configuration for MODIS Albedo Analysis project
Centralizes all file paths for consistent organization
"""
import os
from pathlib import Path

# Base directory (parent of src folder)
BASE_DIR = Path(__file__).parent.parent

# Main directories
DATA_DIR = BASE_DIR / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_CSV_DIR = OUTPUTS_DIR / "csv"
OUTPUTS_GEOJSON_DIR = OUTPUTS_DIR / "geojson"

FIGURES_DIR = BASE_DIR / "figures"
FIGURES_TRENDS_DIR = FIGURES_DIR / "trends"
FIGURES_MELT_DIR = FIGURES_DIR / "melt_season"
FIGURES_EVOLUTION_DIR = FIGURES_DIR / "evolution"

MAPS_DIR = BASE_DIR / "maps"
MAPS_INTERACTIVE_DIR = MAPS_DIR / "interactive"
MAPS_COMPARISON_DIR = MAPS_DIR / "comparison"

DOCS_DIR = BASE_DIR / "docs"

# Create directories if they don't exist
for directory in [
    DATA_RAW_DIR, DATA_PROCESSED_DIR,
    OUTPUTS_CSV_DIR, OUTPUTS_GEOJSON_DIR,
    FIGURES_TRENDS_DIR, FIGURES_MELT_DIR, FIGURES_EVOLUTION_DIR,
    MAPS_INTERACTIVE_DIR, MAPS_COMPARISON_DIR,
    DOCS_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)

# Helper functions for file paths
def get_data_path(filename, raw=False):
    """Get path for data files"""
    if raw:
        return DATA_RAW_DIR / filename
    return DATA_PROCESSED_DIR / filename

def get_figure_path(filename, category='trends'):
    """Get path for figure files"""
    if category == 'trends':
        return FIGURES_TRENDS_DIR / filename
    elif category == 'melt_season':
        return FIGURES_MELT_DIR / filename
    elif category == 'evolution':
        return FIGURES_EVOLUTION_DIR / filename
    else:
        return FIGURES_DIR / filename

def get_map_path(filename, comparison=False):
    """Get path for map files"""
    if comparison:
        return MAPS_COMPARISON_DIR / filename
    return MAPS_INTERACTIVE_DIR / filename

def get_output_path(filename, file_type='csv'):
    """Get path for output files"""
    if file_type == 'csv':
        return OUTPUTS_CSV_DIR / filename
    elif file_type == 'geojson':
        return OUTPUTS_GEOJSON_DIR / filename
    else:
        return OUTPUTS_DIR / filename