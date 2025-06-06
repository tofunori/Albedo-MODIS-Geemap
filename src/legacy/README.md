# Legacy Code Archive

This folder contains older code files that have been superseded by the new organized module structure.

## Files in this folder:

### `trend_analysis.py` (66KB)
- **Status**: Replaced by organized workflow and analysis modules
- **Original purpose**: Large monolithic file containing trend analysis functions
- **Replaced by**: 
  - `src/workflows/melt_season.py`
  - `src/workflows/hypsometric.py`
  - `src/analysis/temporal.py`
  - `src/analysis/hypsometric.py`

### `visualization.py` (12KB)
- **Status**: Replaced by organized visualization module
- **Original purpose**: Basic plotting and visualization functions
- **Replaced by**: 
  - `src/visualization/plots.py`
  - `src/visualization/maps.py`

### `data_processing.py` (7.4KB)
- **Status**: Replaced by organized data module
- **Original purpose**: Data extraction and processing functions
- **Replaced by**: 
  - `src/data/extraction.py`
  - `src/data/processing.py`

### `mapping.py` (24KB)
- **Status**: Replaced by organized visualization module
- **Original purpose**: Interactive mapping and Google Earth Engine functions
- **Replaced by**: 
  - `src/visualization/maps.py`
  - Enhanced functionality in organized modules

## Why these files were moved:

1. **Code Organization**: The new structure follows Python package best practices
2. **Maintainability**: Smaller, focused modules are easier to maintain
3. **Reusability**: Functions are better organized and more reusable
4. **Following Standards**: Follows Williamson & Menounos (2021) methodology more precisely

## ⚠️ Important Note:

These files are kept for reference only. **Do not use these files directly** - they may have outdated imports and dependencies. Use the new organized modules instead.

## Migration Status:

✅ **Complete** - All functionality has been migrated to the new structure
📊 **Improved** - Enhanced with proper error handling and documentation
🔬 **Scientific** - Better aligned with research methodology standards

---

**Date archived**: 2024
**New structure**: Use `src/workflows/`, `src/analysis/`, `src/visualization/`, and `src/data/` modules 