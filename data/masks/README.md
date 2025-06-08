# Glacier Masks

Contains glacier boundary and mask files for the Athabasca Glacier analysis.

## Files

### **`Athabasca_mask_2023_cut.geojson`**
- **Type**: GeoJSON polygon
- **Description**: Clipped glacier boundary for 2023
- **Usage**: Primary mask for MODIS pixel extraction
- **Coordinate System**: WGS84 (EPSG:4326)
- **Source**: Processed from original glacier boundary data

## Usage in Code

```python
import json
import ee

# Load glacier boundary
with open('data/masks/Athabasca_mask_2023_cut.geojson', 'r') as f:
    glacier_geojson = json.load(f)

# Convert to Earth Engine geometry
athabasca_roi = ee.Geometry.Polygon(glacier_geojson['features'][0]['geometry']['coordinates'])
```

## Important Notes

- **Always clip DEM data** with this mask before analysis
- **Use for all MODIS data extraction** to ensure consistent spatial extent
- **Check coordinate system** matches your analysis requirements
- **File size**: ~32KB - appropriate for web applications

## References
- Based on glacier inventory data
- Updated for 2023 analysis period
- Matches extent used in Williamson & Menounos (2021) methodology