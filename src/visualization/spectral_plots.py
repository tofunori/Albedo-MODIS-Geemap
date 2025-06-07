"""
Spectral Visualization Module - Main Interface
Imports from modular components for better organization
Following Williamson & Menounos (2021) methodology
"""

# Import static matplotlib plots
from .static_plots import (
    create_spectral_plot_fixed,
    create_spectral_ratio_plot,
    create_multi_year_seasonal_evolution,
    create_seasonal_spectral_plot
)

# Import interactive plotly plots
from .interactive_plots import (
    create_interactive_seasonal_evolution
)

# Make all functions available at module level
__all__ = [
    'create_spectral_plot_fixed',
    'create_spectral_ratio_plot', 
    'create_multi_year_seasonal_evolution',
    'create_seasonal_spectral_plot',
    'create_interactive_seasonal_evolution'
]