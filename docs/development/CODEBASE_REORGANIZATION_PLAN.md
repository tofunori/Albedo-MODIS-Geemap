# Codebase Reorganization Plan

## Current Issues
1. **streamlit_dashboard_modular.py** is too long (1500+ lines)
2. Inconsistent file organization across project
3. Some modules are still oversized
4. Unclear separation between core logic and UI components

## Proposed New Structure

```
Albedo MODIS Geemap/
├── README.md
├── requirements.txt
├── CLAUDE.md
├── .gitignore
│
├── config/                          # Configuration files
│   ├── __init__.py
│   ├── settings.py                  # Global settings and constants
│   ├── paths.py                     # Path configurations
│   └── roi_config.py               # Region of interest configurations
│
├── data/                           # Data storage
│   ├── raw/                        # Raw MODIS data
│   ├── processed/                  # Processed datasets
│   └── masks/                      # Glacier masks and boundaries
│       ├── Athabasca_mask_2023.geojson
│       └── Athabasca_mask_2023_cut.geojson
│
├── outputs/                        # Analysis outputs
│   ├── csv/                        # CSV results
│   ├── figures/                    # Generated plots
│   │   ├── evolution/
│   │   ├── melt_season/
│   │   └── trends/
│   ├── maps/                       # Interactive maps
│   │   ├── interactive/
│   │   └── comparison/
│   └── reports/                    # Text reports
│
├── docs/                          # Documentation
│   ├── methodology.md
│   ├── MOD10A1_QA_Flags_Guide.md
│   ├── qa-filtering-guide.md
│   └── api/                       # API documentation
│
├── src/                           # Core Python modules
│   ├── __init__.py
│   │
│   ├── core/                      # Core analysis modules
│   │   ├── __init__.py
│   │   ├── albedo_analysis.py     # Core albedo analysis functions
│   │   ├── qa_filtering.py        # Quality assessment filtering
│   │   ├── temporal_analysis.py   # Temporal trend analysis
│   │   └── spatial_analysis.py    # Spatial analysis functions
│   │
│   ├── data/                      # Data extraction and processing
│   │   ├── __init__.py
│   │   ├── extractors/            # Data extraction modules
│   │   │   ├── __init__.py
│   │   │   ├── mod10a1_extractor.py
│   │   │   ├── mcd43a3_extractor.py
│   │   │   └── dem_extractor.py
│   │   ├── processors/            # Data processing modules
│   │   │   ├── __init__.py
│   │   │   ├── qa_processor.py
│   │   │   ├── temporal_processor.py
│   │   │   └── spatial_processor.py
│   │   └── loaders/               # Data loading utilities
│   │       ├── __init__.py
│   │       ├── csv_loader.py
│   │       └── geojson_loader.py
│   │
│   ├── analysis/                  # Analysis workflows
│   │   ├── __init__.py
│   │   ├── workflows/             # Complete analysis workflows
│   │   │   ├── __init__.py
│   │   │   ├── melt_season_workflow.py
│   │   │   ├── broadband_albedo_workflow.py
│   │   │   └── hypsometric_workflow.py
│   │   ├── statistics/            # Statistical analysis
│   │   │   ├── __init__.py
│   │   │   ├── trend_analysis.py
│   │   │   ├── correlation_analysis.py
│   │   │   └── mann_kendall.py
│   │   └── validation/            # Validation and QA
│   │       ├── __init__.py
│   │       ├── data_validation.py
│   │       └── result_validation.py
│   │
│   ├── visualization/             # Visualization modules
│   │   ├── __init__.py
│   │   ├── plots/                 # Plot generation
│   │   │   ├── __init__.py
│   │   │   ├── time_series_plots.py
│   │   │   ├── spatial_plots.py
│   │   │   ├── statistical_plots.py
│   │   │   └── comparison_plots.py
│   │   ├── maps/                  # Map generation
│   │   │   ├── __init__.py
│   │   │   ├── interactive_maps.py
│   │   │   ├── static_maps.py
│   │   │   └── earth_engine_maps.py
│   │   └── dashboards/            # Dashboard components
│   │       ├── __init__.py
│   │       ├── plotly_components.py
│   │       └── streamlit_components.py
│   │
│   └── utils/                     # Utility modules
│       ├── __init__.py
│       ├── file_utils.py          # File I/O utilities
│       ├── date_utils.py          # Date/time utilities
│       ├── math_utils.py          # Mathematical utilities
│       ├── earth_engine_utils.py  # Google Earth Engine utilities
│       └── report_generator.py    # Report generation
│
├── web/                           # Web interface (Streamlit)
│   ├── __init__.py
│   ├── main.py                    # Main Streamlit entry point
│   │
│   ├── pages/                     # Individual dashboard pages
│   │   ├── __init__.py
│   │   ├── data_processing.py     # Data processing page
│   │   ├── mcd43a3_analysis.py    # MCD43A3 analysis page
│   │   ├── mod10a1_analysis.py    # MOD10A1 analysis page
│   │   ├── hypsometric_analysis.py # Hypsometric analysis page
│   │   ├── statistical_analysis.py # Statistical analysis page
│   │   ├── interactive_maps.py    # Interactive visualization page
│   │   └── qa_comparison.py       # QA comparison page
│   │
│   ├── components/                # Reusable UI components
│   │   ├── __init__.py
│   │   ├── data_tables.py         # Interactive data tables
│   │   ├── file_upload.py         # File upload interfaces
│   │   ├── parameter_selectors.py # Parameter selection widgets
│   │   ├── progress_indicators.py # Progress bars and status
│   │   └── map_components.py      # Map display components
│   │
│   ├── utils/                     # Web-specific utilities
│   │   ├── __init__.py
│   │   ├── session_management.py # Streamlit session state
│   │   ├── data_caching.py        # Data caching strategies
│   │   └── ui_helpers.py          # UI helper functions
│   │
│   ├── assets/                    # Static assets
│   │   ├── styles/                # CSS styles
│   │   ├── images/                # Images and icons
│   │   └── configs/               # Configuration files
│   │       ├── streamlit_config.toml
│   │       └── secrets_template.toml
│   │
│   └── requirements.txt           # Web-specific requirements
│
├── scripts/                       # Standalone scripts
│   ├── __init__.py
│   ├── data_download.py           # Data download scripts
│   ├── batch_processing.py        # Batch processing scripts
│   ├── quality_checks.py          # Data quality validation
│   └── migration/                 # Data migration scripts
│       ├── __init__.py
│       └── reorganize_files.py
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── unit/                      # Unit tests
│   │   ├── test_core/
│   │   ├── test_data/
│   │   ├── test_analysis/
│   │   └── test_utils/
│   ├── integration/               # Integration tests
│   └── fixtures/                  # Test data and fixtures
│
├── notebooks/                     # Jupyter notebooks
│   ├── 01_Data_Exploration.ipynb
│   ├── 02_Method_Development.ipynb
│   ├── 03_Quality_Assessment.ipynb
│   └── 04_Results_Validation.ipynb
│
└── legacy/                        # Legacy code (to be phased out)
    ├── README.md
    ├── old_main.py
    └── deprecated/
```

## Migration Steps

### Phase 1: Core Restructuring (Immediate)
1. ✅ **Streamlit Modularization**
   - Break down `streamlit_dashboard_modular.py` into smaller modules
   - Create `web/` directory structure
   - Move dashboard components to appropriate modules

2. **Core Module Organization**
   - Move `src/config.py` → `config/settings.py`
   - Move `src/paths.py` → `config/paths.py`
   - Reorganize analysis modules by functionality

3. **Data Organization**
   - Move glacier masks to `data/masks/`
   - Organize outputs by type in `outputs/`

### Phase 2: Advanced Restructuring
4. **Visualization Separation**
   - Separate plotting logic from analysis logic
   - Create dedicated visualization modules
   - Standardize plot generation interfaces

5. **Workflow Standardization**
   - Create standardized workflow interfaces
   - Implement consistent error handling
   - Add progress reporting capabilities

### Phase 3: Quality Improvements
6. **Documentation**
   - Add comprehensive API documentation
   - Create usage examples
   - Document best practices

7. **Testing**
   - Add unit tests for core functions
   - Integration tests for workflows
   - Performance benchmarks

## Benefits of This Structure

### 1. **Modularity**
- Clear separation of concerns
- Easier testing and debugging
- Better code reuse

### 2. **Scalability**
- Easy to add new analysis types
- Extensible visualization system
- Pluggable data sources

### 3. **Maintainability**
- Consistent file organization
- Clear dependencies
- Standardized interfaces

### 4. **User Experience**
- Faster loading times
- Better error handling
- More responsive interface

## Implementation Priority

### High Priority (Week 1)
- ✅ Break down oversized Streamlit files
- Reorganize web interface structure
- Move configuration files

### Medium Priority (Week 2)
- Reorganize core analysis modules
- Standardize data processing workflows
- Improve visualization organization

### Low Priority (Week 3+)
- Add comprehensive testing
- Create API documentation
- Implement performance optimizations

## File Size Guidelines

Following the project's established guidelines:
- **Maximum file length**: 500 lines (target)
- **Refactoring threshold**: 500-700 lines
- **Module organization**: Single responsibility principle
- **Documentation**: Comprehensive docstrings and type hints

## Backward Compatibility

- Maintain existing entry points during transition
- Create migration scripts for data files
- Preserve existing CSV output formats
- Keep legacy code in `legacy/` directory until fully migrated