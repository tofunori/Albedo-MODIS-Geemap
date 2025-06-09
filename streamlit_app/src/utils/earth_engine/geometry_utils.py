"""
Geometry Utilities for Earth Engine
Handles GeoJSON to Earth Engine geometry conversion
"""


def get_roi_from_geojson(glacier_geojson):
    """
    Convert GeoJSON to Earth Engine geometry
    
    Args:
        glacier_geojson: Loaded GeoJSON data
        
    Returns:
        ee.Geometry: Earth Engine geometry for the glacier
    """
    try:
        import ee
        
        if glacier_geojson:
            # Convert geojson to Earth Engine geometry
            coords = glacier_geojson['features'][0]['geometry']['coordinates'][0]
            return ee.Geometry.Polygon(coords)
        else:
            # Fallback to approximate coordinates
            return ee.Geometry.Polygon([
                [[-117.3, 52.15], [-117.15, 52.15], [-117.15, 52.25], [-117.3, 52.25]]
            ])
    except Exception as e:
        print(f"Error creating ROI: {e}")
        # Fallback geometry
        import ee
        return ee.Geometry.Polygon([
            [[-117.3, 52.15], [-117.15, 52.15], [-117.15, 52.25], [-117.3, 52.25]]
        ])