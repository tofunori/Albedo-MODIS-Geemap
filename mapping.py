"""
Interactive mapping module for visualizing glacier extent and MODIS pixels
Displays the Athabasca Glacier boundary with MODIS data overlays
"""
import ee
import geemap
import folium
from config import athabasca_roi, ATHABASCA_STATION, MODIS_COLLECTIONS, athabasca_geojson
import json

def create_glacier_map(date='2023-08-15', scale=500, show_modis_pixels=True, 
                      show_snow_albedo=True, show_broadband=False):
    """
    Create interactive map showing glacier extent with MODIS pixels
    
    Args:
        date: Date for MODIS data display (YYYY-MM-DD)
        scale: MODIS pixel resolution to display (250, 500, 1000)
        show_modis_pixels: Whether to show MODIS pixel grid
        show_snow_albedo: Whether to show snow albedo data
        show_broadband: Whether to show broadband albedo data
    
    Returns:
        geemap.Map: Interactive map object
    """
    
    # Calculate the center of the glacier for proper map centering
    glacier_centroid = athabasca_roi.centroid().getInfo()
    center_lat = glacier_centroid['coordinates'][1]
    center_lon = glacier_centroid['coordinates'][0]
    
    # Create the map centered on the glacier centroid
    Map = geemap.Map(center=[center_lat, center_lon], zoom=13)
    
    # Add glacier boundary using the exact GeoJSON extent
    glacier_style = {
        'color': '#ff0000',
        'fillColor': '#ff0000',
        'weight': 3,
        'fillOpacity': 0.1
    }
    
    # Create feature collection from the glacier ROI
    glacier_fc = ee.FeatureCollection([ee.Feature(athabasca_roi, {'name': 'Athabasca Glacier'})])
    
    Map.add_ee_layer(
        glacier_fc,
        glacier_style,
        'Athabasca Glacier Extent (2023)',
        True
    )
    
    # Add MODIS pixel grid if requested
    if show_modis_pixels:
        try:
            # Create a MODIS pixel grid for visualization
            modis_grid = create_modis_pixel_grid(scale)
            grid_style = {
                'color': 'blue',
                'fillColor': 'transparent',
                'weight': 1,
                'fillOpacity': 0
            }
            
            Map.add_ee_layer(
                modis_grid,
                grid_style,
                f'MODIS {scale}m Pixel Grid',
                True
            )
        except Exception as e:
            print(f"Could not create MODIS pixel grid: {e}")
            print("Map will display without pixel grid overlay.")
    
    # Add MODIS snow albedo data if requested
    if show_snow_albedo:
        try:
            # Get MODIS snow albedo for the specified date
            modis_snow = get_modis_snow_albedo(date)
            
            if modis_snow is not None:
                albedo_vis = {
                    'min': 0.0,
                    'max': 1.0,
                    'palette': ['0d0887', '6a00a8', 'b12a90', 'e16462', 'fca636', 'f0f921']
                }
                
                # Clip to exact glacier extent from GeoJSON
                albedo_clipped = modis_snow.select('Snow_Albedo_Daily_Tile').clip(athabasca_roi)
                
                Map.add_ee_layer(
                    albedo_clipped,
                    albedo_vis,
                    f'Snow Albedo ({date}) - Glacier Only',
                    True
                )
            else:
                print(f"No MODIS snow data available for {date}")
        except Exception as e:
            print(f"Could not load snow albedo for {date}: {e}")
    
    # Add MODIS broadband albedo if requested
    if show_broadband:
        try:
            # Get MODIS broadband albedo for the specified date
            modis_broad = get_modis_broadband_albedo(date)
            
            if modis_broad is not None:
                broad_vis = {
                    'min': 0.0,
                    'max': 0.4,
                    'bands': ['Albedo_BSA_Band1', 'Albedo_BSA_Band4', 'Albedo_BSA_Band3'],
                    'gamma': 1.4
                }
                
                # Clip to exact glacier extent from GeoJSON
                Map.add_ee_layer(
                    modis_broad.clip(athabasca_roi),
                    broad_vis,
                    f'Broadband Albedo ({date}) - Glacier Only',
                    False
                )
            else:
                print(f"No MODIS broadband data available for {date}")
        except Exception as e:
            print(f"Could not load broadband albedo for {date}: {e}")
    
    # Add station marker
    station_marker = ee.Geometry.Point(ATHABASCA_STATION)
    Map.add_ee_layer(
        station_marker,
        {'color': 'yellow'},
        'Weather Station',
        True
    )
    
    # Add legend
    add_legend(Map)
    
    return Map

def create_modis_pixel_grid(scale=500):
    """
    Create a pixel grid showing MODIS pixel boundaries within glacier extent
    
    Args:
        scale: Pixel size in meters
        
    Returns:
        ee.FeatureCollection: Grid features clipped to glacier extent
    """
    
    # Use the actual glacier ROI instead of just bounds
    glacier_area = athabasca_roi
    
    # Create a sample MODIS image to get the correct projection and pixel grid
    # Using a recent MODIS snow product to match the analysis data
    modis_collection = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra'])
    sample_image = modis_collection.filterDate('2023-08-01', '2023-08-31').first()
    
    if sample_image is None:
        # Fallback: create a simple grid
        grid_image = ee.Image(1).reproject(
            crs='EPSG:4326',
            scale=scale
        ).clip(glacier_area)
    else:
        # Use actual MODIS projection and pixel boundaries
        grid_image = sample_image.select(0).multiply(0).add(1).reproject(
            crs=sample_image.projection(),
            scale=scale
        ).clip(glacier_area)
    
    # Convert to vectors using the constant image, clipped to glacier
    grid_features = grid_image.reduceToVectors(
        geometry=glacier_area,
        crs=grid_image.projection(),
        scale=scale,
        geometryType='polygon',
        eightConnected=False,
        maxPixels=1e6,
        bestEffort=True
    )
    
    return grid_features

def get_modis_snow_albedo(date):
    """
    Get MODIS snow albedo data for a specific date
    
    Args:
        date: Date string (YYYY-MM-DD)
        
    Returns:
        ee.Image: MODIS snow albedo image
    """
    
    # Combine Terra and Aqua collections
    terra_snow = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra'])
    aqua_snow = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua'])
    
    # Filter by date (±1 day for better coverage)
    start_date = ee.Date(date).advance(-1, 'day')
    end_date = ee.Date(date).advance(1, 'day')
    
    terra_image = terra_snow.filterDate(start_date, end_date).first()
    aqua_image = aqua_snow.filterDate(start_date, end_date).first()
    
    # Combine Terra and Aqua (prioritize Terra)
    combined = ee.ImageCollection([terra_image, aqua_image]).mosaic()
    
    return combined

def get_modis_broadband_albedo(date):
    """
    Get MODIS broadband albedo data for a specific date
    
    Args:
        date: Date string (YYYY-MM-DD)
        
    Returns:
        ee.Image: MODIS broadband albedo image
    """
    
    broadband_collection = ee.ImageCollection(MODIS_COLLECTIONS['broadband'])
    
    # Filter by date (±8 days for MCD43A3 16-day composite)
    start_date = ee.Date(date).advance(-8, 'day')
    end_date = ee.Date(date).advance(8, 'day')
    
    image = broadband_collection.filterDate(start_date, end_date).first()
    
    return image

def add_legend(Map):
    """
    Add a legend to the map
    
    Args:
        Map: geemap.Map object
    """
    
    # Legend as list of tuples (label, color)
    legend_elements = [
        ('Glacier Boundary', '#ff0000'),
        ('MODIS Pixel Grid', '#0000ff'), 
        ('Weather Station', '#ffff00'),
        ('Low Albedo', '#0d0887'),
        ('High Albedo', '#f0f921')
    ]
    
    try:
        Map.add_legend(
            legend_dict=dict(legend_elements), 
            title="Map Legend",
            position='bottomright'
        )
    except:
        # If legend still fails, create a simple text legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 150px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; font-weight: bold;">
        <p style="margin: 10px;"><b>Map Legend</b></p>
        <p style="margin: 5px; color: red;">■ Glacier Boundary</p>
        <p style="margin: 5px; color: blue;">■ MODIS Pixels</p>
        <p style="margin: 5px; color: #0d0887;">■ Low Albedo</p>
        <p style="margin: 5px; color: #f0f921;">■ High Albedo</p>
        </div>
        '''
        Map.get_root().html.add_child(folium.Element(legend_html))

def create_comparison_map(date1='2023-06-15', date2='2023-09-15', scale=500):
    """
    Create a side-by-side comparison map for two different dates using glacier extent
    
    Args:
        date1: First date for comparison (YYYY-MM-DD)
        date2: Second date for comparison (YYYY-MM-DD)
        scale: MODIS pixel resolution
        
    Returns:
        geemap.Map: Split-panel map
    """
    
    # Calculate the center of the glacier for proper map centering
    glacier_centroid = athabasca_roi.centroid().getInfo()
    center_lat = glacier_centroid['coordinates'][1]
    center_lon = glacier_centroid['coordinates'][0]
    
    # Create split map centered on glacier
    Map = geemap.Map(center=[center_lat, center_lon], zoom=13)
    
    print(f"🗺️ Loading MODIS data for comparison...")
    print(f"   • Date 1: {date1}")
    print(f"   • Date 2: {date2}")
    
    # Get MODIS data for both dates
    modis1 = get_modis_snow_albedo(date1)
    modis2 = get_modis_snow_albedo(date2)
    
    # Visualization parameters
    albedo_vis = {
        'min': 0.0,
        'max': 1.0,
        'palette': ['0d0887', '6a00a8', 'b12a90', 'e16462', 'fca636', 'f0f921']
    }
    
    # Glacier boundary style
    glacier_style = {
        'color': '#ff0000', 
        'fillColor': '#ff0000', 
        'weight': 2,
        'fillOpacity': 0.1
    }
    glacier_fc = ee.FeatureCollection([ee.Feature(athabasca_roi, {'name': 'Athabasca Glacier'})])
    
    # Prepare layers for split map
    if modis1 is not None and modis2 is not None:
        # Left side (date1) - clipped to exact glacier extent
        left_layers = [
            (modis1.select('Snow_Albedo_Daily_Tile').clip(athabasca_roi), albedo_vis, f'Albedo {date1}'),
            (glacier_fc, glacier_style, 'Glacier Extent')
        ]
        
        # Right side (date2) - clipped to exact glacier extent
        right_layers = [
            (modis2.select('Snow_Albedo_Daily_Tile').clip(athabasca_roi), albedo_vis, f'Albedo {date2}'),
            (glacier_fc, glacier_style, 'Glacier Extent')
        ]
        
        Map.split_map(left_layers=left_layers, right_layers=right_layers)
        print(f"✅ Comparison map created successfully!")
        
    else:
        print(f"❌ Could not load MODIS data for one or both dates")
        # Fallback: just show glacier boundary
        Map.add_ee_layer(glacier_fc, glacier_style, 'Athabasca Glacier Extent', True)
    
    return Map

def save_glacier_extent_kml():
    """
    Export glacier boundary as KML file for use in other applications
    
    Returns:
        str: Path to saved KML file
    """
    
    # Convert glacier boundary to feature collection
    glacier_fc = ee.FeatureCollection([ee.Feature(athabasca_roi, {'name': 'Athabasca Glacier 2023'})])
    
    # Export as KML
    kml_path = 'athabasca_glacier_boundary.kml'
    
    # Save as GeoJSON first (easier with current tools)
    geojson_path = 'athabasca_glacier_boundary_export.geojson'
    geemap.ee_to_geojson(glacier_fc, geojson_path)
    
    print(f"Glacier boundary saved as: {geojson_path}")
    return geojson_path

def display_glacier_info():
    """
    Display glacier information and statistics
    
    Returns:
        dict: Glacier information
    """
    
    try:
        # Calculate glacier area
        area_km2 = athabasca_roi.area().divide(1e6).getInfo()
        
        # Calculate glacier bounds
        bounds = athabasca_roi.bounds().getInfo()
        
        # Get centroid
        centroid = athabasca_roi.centroid().getInfo()
        
        info = {
            'area_km2': round(area_km2, 2),
            'bounds': bounds,
            'centroid': centroid['coordinates'],
            'station_coords': ATHABASCA_STATION
        }
        
        print("🏔️ GLACIER INFORMATION")
        print("=" * 40)
        print(f"Area: {info['area_km2']} km²")
        print(f"Center: {info['centroid'][1]:.3f}°N, {info['centroid'][0]:.3f}°W")
        print(f"Weather Station: {info['station_coords'][1]:.3f}°N, {info['station_coords'][0]:.3f}°W")
        
        return info
        
    except Exception as e:
        print(f"Error calculating glacier info: {e}")
        return None

# Convenience function for quick map display
def show_glacier_map(date='2023-08-15', scale=500, simple_mode=False):
    """
    Quick function to display glacier map with default settings
    
    Args:
        date: Date for MODIS data (YYYY-MM-DD)
        scale: MODIS pixel resolution (250, 500, 1000)
        simple_mode: If True, skips pixel grid to avoid errors
        
    Returns:
        geemap.Map: Interactive map
    """
    
    print(f"🗺️ Creating glacier map for {date} at {scale}m resolution...")
    
    # Display glacier info
    display_glacier_info()
    
    # Create and return map
    Map = create_glacier_map(
        date=date,
        scale=scale,
        show_modis_pixels=not simple_mode,  # Skip pixels if in simple mode
        show_snow_albedo=True,
        show_broadband=False
    )
    
    print(f"✅ Map created! Use Map.to_html() to save or display in Jupyter.")
    
    return Map

def show_simple_glacier_map(date='2023-08-15', scale=500):
    """
    Simplified version that avoids potential pixel grid errors
    """
    return show_glacier_map(date=date, scale=scale, simple_mode=True)