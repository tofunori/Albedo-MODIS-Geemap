"""
Path management utilities for the Athabasca Glacier analysis project
"""

import os
from pathlib import Path

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent

# Main directories
DATA_DIR = BASE_DIR / 'data'
FIGURES_DIR = BASE_DIR / 'figures'
OUTPUTS_DIR = BASE_DIR / 'outputs'
MAPS_DIR = BASE_DIR / 'maps'

# Sub-directories
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'

CSV_OUTPUT_DIR = OUTPUTS_DIR / 'csv'
GEOJSON_OUTPUT_DIR = OUTPUTS_DIR / 'geojson'

MELT_SEASON_FIGURES_DIR = FIGURES_DIR / 'melt_season'
TRENDS_FIGURES_DIR = FIGURES_DIR / 'trends'
EVOLUTION_FIGURES_DIR = FIGURES_DIR / 'evolution'

INTERACTIVE_MAPS_DIR = MAPS_DIR / 'interactive'
COMPARISON_MAPS_DIR = MAPS_DIR / 'comparison'

# Create directories if they don't exist
def ensure_directories():
    """Create all necessary directories if they don't exist"""
    directories = [
        DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR,
        FIGURES_DIR, MELT_SEASON_FIGURES_DIR, TRENDS_FIGURES_DIR, EVOLUTION_FIGURES_DIR,
        OUTPUTS_DIR, CSV_OUTPUT_DIR, GEOJSON_OUTPUT_DIR,
        MAPS_DIR, INTERACTIVE_MAPS_DIR, COMPARISON_MAPS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_output_path(filename, category='csv'):
    """
    Get the full path for an output file
    
    Args:
        filename: Name of the file
        category: Type of output ('csv', 'geojson')
    
    Returns:
        pathlib.Path: Full path to the output file
    """
    ensure_directories()
    
    if category == 'csv':
        return CSV_OUTPUT_DIR / filename
    elif category == 'geojson':
        return GEOJSON_OUTPUT_DIR / filename
    else:
        return OUTPUTS_DIR / filename

def get_figure_path(filename, category='general'):
    """
    Get the full path for a figure file
    
    Args:
        filename: Name of the figure file
        category: Type of figure ('melt_season', 'trends', 'evolution', 'general')
    
    Returns:
        pathlib.Path: Full path to the figure file
    """
    ensure_directories()
    
    if category == 'melt_season':
        return MELT_SEASON_FIGURES_DIR / filename
    elif category == 'trends':
        return TRENDS_FIGURES_DIR / filename
    elif category == 'evolution':
        return EVOLUTION_FIGURES_DIR / filename
    else:
        return FIGURES_DIR / filename

def get_map_path(filename, category='interactive'):
    """
    Get the full path for a map file
    
    Args:
        filename: Name of the map file
        category: Type of map ('interactive', 'comparison')
    
    Returns:
        pathlib.Path: Full path to the map file
    """
    ensure_directories()
    
    if category == 'interactive':
        return INTERACTIVE_MAPS_DIR / filename
    elif category == 'comparison':
        return COMPARISON_MAPS_DIR / filename
    else:
        return MAPS_DIR / filename

# Initialize directories when module is imported
ensure_directories()