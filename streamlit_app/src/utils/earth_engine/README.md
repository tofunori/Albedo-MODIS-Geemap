# Earth Engine Module Structure

This module provides a clean, modular structure for Earth Engine operations in the Streamlit dashboard.

## Files Overview

### 📁 **Module Structure**
```
earth_engine/
├── __init__.py              (15 lines)  - Module exports
├── geometry_utils.py        (34 lines)  - GeoJSON to EE geometry conversion
├── initialization.py        (109 lines) - EE authentication & initialization  
├── modis_extraction.py      (230 lines) - Main MODIS data extraction
└── pixel_processing.py      (331 lines) - Pixel vectorization & GeoJSON export
```

### 🎯 **Key Benefits**

1. **File Size Control**: All files under 350 lines (target: <500)
2. **Clear Separation**: Each file has a single responsibility
3. **Backwards Compatibility**: Original `ee_utils.py` imports everything
4. **Maintainability**: Easier to navigate and modify
5. **Testing**: Each module can be tested independently

### 📊 **Module Responsibilities**

- **`initialization.py`**: Earth Engine auth with multiple fallback methods
- **`geometry_utils.py`**: Simple geometry conversions
- **`modis_extraction.py`**: High-level MODIS data extraction with Terra-Aqua fusion
- **`pixel_processing.py`**: Low-level pixel vectorization and property extraction

### 🔄 **Migration**

No code changes needed! The original `ee_utils.py` now acts as a compatibility wrapper:
```python
from .earth_engine import (
    initialize_earth_engine,
    get_modis_pixels_for_date,
    count_modis_pixels_for_date,
    get_roi_from_geojson
)
```

All existing imports continue to work seamlessly.

### 🚀 **Usage**

```python
# Still works exactly the same
from src.utils.ee_utils import initialize_earth_engine, get_modis_pixels_for_date

# Or use the new modular imports directly
from src.utils.earth_engine import get_modis_pixels_for_date
```