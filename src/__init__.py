"""
MODIS Albedo Analysis Package for Athabasca Glacier
Université du Québec à Trois-Rivières - Master's Research Project

This package provides tools for analyzing MODIS albedo data from the Athabasca Glacier
in Alberta, Canada, with focus on melt season dynamics and fire impact assessment.

Modules:
- config: Configuration parameters and glacier geometry
- data_processing: MODIS data extraction and processing functions  
- visualization: Plotting and graphical analysis functions
- melt_season: Specialized melt season analysis
- analysis: General statistical analysis functions
- mapping: Interactive mapping and visualization functions
- main: Main analysis runner with convenience functions
"""

__version__ = "1.0.0"
__author__ = "UQTR Graduate Student"
__email__ = "student@uqtr.ca"

# Import main functions for easy access
try:
    from .main import (
        run_analysis_optimized,
        quick_recent_analysis,
        fire_impact_analysis,
        decade_trend_analysis,
        fast_test_analysis,
        custom_analysis,
        interactive_menu,
        williamson_melt_season_analysis
    )
    from .trend_analysis import run_melt_season_analysis_williamson
except ImportError:
    pass

from config import (
    athabasca_roi,
    PERIODS_RAPIDE,
    SAMPLING_OPTIONS,
    SCALE_OPTIONS,
    FIRE_YEARS
)

from data.extraction import (
    extract_time_series_fast,
    mask_modis_snow_albedo_fast
)

# Legacy imports commented out - use organized modules instead
# from visualization import (
#     plot_albedo_evolution_enhanced,
#     plot_albedo_fast
# )

# from melt_season import (
#     analyze_melt_season,
#     plot_melt_season_analysis
# )

# from analysis import (
#     calculate_annual_trends,
#     calculate_seasonal_statistics,
#     identify_extreme_years
# )

# from mapping import (
#     show_glacier_map,
#     create_comparison_map,
#     display_glacier_info,
#     create_glacier_map
# )

__all__ = [
    # Main analysis functions
    'run_analysis_optimized',
    'quick_recent_analysis', 
    'fire_impact_analysis',
    'decade_trend_analysis',
    'fast_test_analysis',
    'custom_analysis',
    'interactive_menu',
    
    # Configuration
    'athabasca_roi',
    'PERIODS_RAPIDE',
    'SAMPLING_OPTIONS', 
    'SCALE_OPTIONS',
    'FIRE_YEARS',
    
    # Data processing
    'extract_time_series_fast',
    'mask_modis_snow_albedo_fast'
    
    # Note: Use organized modules for specific functionality:
    # - src.workflows.melt_season for melt season analysis
    # - src.visualization.plots for plotting functions
    # - src.visualization.maps for mapping functions
    # - src.analysis.temporal for trend analysis
    # - src.analysis.hypsometric for elevation-based analysis
]