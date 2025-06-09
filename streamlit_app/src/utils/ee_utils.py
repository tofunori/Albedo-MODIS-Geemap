"""
Earth Engine Utilities for Streamlit Dashboard
Backwards compatibility wrapper - imports from modular earth_engine package
"""

# Import everything from the new modular structure
from .earth_engine import (
    initialize_earth_engine,
    get_modis_pixels_for_date,
    count_modis_pixels_for_date, 
    get_roi_from_geojson
)

# Re-export for backwards compatibility
__all__ = [
    'initialize_earth_engine',
    'get_modis_pixels_for_date',
    'count_modis_pixels_for_date',
    'get_roi_from_geojson'
]