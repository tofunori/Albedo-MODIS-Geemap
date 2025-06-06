"""
Interactive mapping module for visualizing glacier extent and MODIS pixels
Displays the Athabasca Glacier boundary with MODIS data overlays
"""
import ee
import geemap
import folium
from config import athabasca_roi, ATHABASCA_STATION, MODIS_COLLECTIONS, athabasca_geojson
import json
import ipywidgets as widgets
from IPython.display import display
import datetime

def create_glacier_map(date='2023-08-15', show_modis_pixels=True, 
                      show_snow_albedo=True, show_broadband=False):
    """
    Create interactive map showing glacier extent with MODIS 500m pixels
    
    Args:
        date: Date for MODIS data display (YYYY-MM-DD)
        show_modis_pixels: Whether to show MODIS 500m pixel grid
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
    
    # Add valid MODIS pixels that pass quality masks and are within glacier
    if show_modis_pixels:
        try:
            # Create boundaries for valid MODIS pixels with data
            valid_pixels = create_modis_valid_pixels(date)
            
            # Style for valid pixel boundaries
            pixel_style = {
                'color': '#0066cc',
                'fillColor': 'transparent',
                'weight': 2,
                'fillOpacity': 0
            }
            
            Map.add_ee_layer(
                valid_pixels,
                pixel_style,
                f'Valid MODIS Pixels ({date})',
                True
            )
            
            # Count valid pixels
            pixel_count = valid_pixels.size().getInfo()
            print(f"📊 Found {pixel_count} valid MODIS pixels within glacier boundary")
            
        except Exception as e:
            print(f"Could not create valid MODIS pixels: {e}")
            print("Map will display without pixel overlay.")
    
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
    
    # Add map instructions
    print("🗺️ Map layers:")
    print("   • Red boundary: Exact glacier extent from GeoJSON")
    print("   • Blue outlines: MODIS pixels with valid data (passed QA masks)")
    print("   • Color overlay: Snow albedo values within glacier")
    print("   • Click on blue pixels to see albedo values and properties")
    
    return Map

def create_modis_valid_pixels(date='2023-08-15'):
    """
    Create boundaries for MODIS pixels that contain valid, quality-masked data within glacier
    
    Args:
        date: Date to get MODIS data for showing valid pixels
        
    Returns:
        ee.FeatureCollection: Valid MODIS pixel boundaries with albedo values
    """
    
    # Get MODIS snow albedo data for the specified date
    modis_snow = get_modis_snow_albedo(date)
    
    if modis_snow is not None:
        # Apply the same quality masking as in data processing
        from data_processing import mask_modis_snow_albedo_fast
        
        # Get both Terra and Aqua for the date
        terra_collection = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra'])
        aqua_collection = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua'])
        
        # Filter by date (±1 day)
        start_date = ee.Date(date).advance(-1, 'day')
        end_date = ee.Date(date).advance(1, 'day')
        
        terra_image = terra_collection.filterDate(start_date, end_date).first()
        aqua_image = aqua_collection.filterDate(start_date, end_date).first()
        
        # Process the images with quality masking
        valid_images = []
        
        if terra_image is not None:
            terra_masked = mask_modis_snow_albedo_fast(terra_image)
            valid_images.append(terra_masked)
        
        if aqua_image is not None:
            aqua_masked = mask_modis_snow_albedo_fast(aqua_image)
            valid_images.append(aqua_masked)
        
        if valid_images:
            # Combine valid images
            combined_image = ee.ImageCollection(valid_images).mosaic()
            
            # Clip to glacier boundary
            glacier_masked = combined_image.clip(athabasca_roi)
            
            # Convert valid pixels to vectors
            valid_pixel_vectors = glacier_masked.select('albedo_daily').reduceToVectors(
                geometry=athabasca_roi,
                crs=combined_image.projection(),
                scale=combined_image.projection().nominalScale(),
                geometryType='polygon',
                eightConnected=False,
                maxPixels=1e6,
                bestEffort=True,
                labelProperty='albedo_value'
            )
            
            # Add information about each valid pixel
            def add_pixel_info(feature):
                # Get the albedo value for this pixel
                albedo_val = glacier_masked.select('albedo_daily').reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=feature.geometry(),
                    scale=500,
                    maxPixels=1
                ).get('albedo_daily')
                
                return feature.set({
                    'albedo_value': albedo_val,
                    'area_m2': feature.geometry().area(),
                    'pixel_type': 'Valid_MODIS',
                    'date': date,
                    'passes_qa': True
                })
            
            return valid_pixel_vectors.map(add_pixel_info)
        
        else:
            print(f"⚠️ No valid MODIS data for {date}")
            return ee.FeatureCollection([])
    
    else:
        print(f"⚠️ No MODIS data available for {date}")
        return ee.FeatureCollection([])

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

def create_comparison_map(date1='2023-06-15', date2='2023-09-15'):
    """
    Create a side-by-side comparison map for two different dates using glacier extent
    
    Args:
        date1: First date for comparison (YYYY-MM-DD)
        date2: Second date for comparison (YYYY-MM-DD)
        
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
def show_glacier_map(date='2023-08-15', simple_mode=False):
    """
    Quick function to display glacier map with MODIS 500m data
    
    Args:
        date: Date for MODIS data (YYYY-MM-DD)
        simple_mode: If True, skips pixel grid to avoid errors
        
    Returns:
        geemap.Map: Interactive map
    """
    
    print(f"🗺️ Creating glacier map for {date} with MODIS 500m snow albedo...")
    
    # Display glacier info
    display_glacier_info()
    
    # Create and return map
    Map = create_glacier_map(
        date=date,
        show_modis_pixels=not simple_mode,  # Skip pixels if in simple mode
        show_snow_albedo=True,
        show_broadband=False
    )
    
    print(f"✅ Map created! Use Map.to_html() to save or display in Jupyter.")
    
    return Map

def show_simple_glacier_map(date='2023-08-15'):
    """
    Simplified version that avoids potential pixel grid errors
    """
    return show_glacier_map(date=date, simple_mode=True)

def create_interactive_glacier_map():
    """
    Create an interactive map with date picker for dynamic MODIS data visualization
    
    Returns:
        Interactive widget with map and date controls
    """
    
    try:
        # Create initial map
        initial_date = '2023-08-15'
        Map = create_glacier_map(date=initial_date, show_modis_pixels=True, show_snow_albedo=True)
        
        # Create date picker widget
        date_picker = widgets.DatePicker(
            description='Select Date:',
            value=datetime.date(2023, 8, 15),
            disabled=False,
            style={'description_width': 'initial'}
        )
        
        # Create update button
        update_button = widgets.Button(
            description='Update Map',
            button_style='primary',
            tooltip='Click to update map with selected date'
        )
        
        # Create loading indicator
        loading_label = widgets.Label(value='Ready')
        
        # Create options checkboxes
        show_pixels_checkbox = widgets.Checkbox(
            value=True,
            description='Show Valid MODIS Pixels',
            disabled=False,
            indent=False
        )
        
        show_albedo_checkbox = widgets.Checkbox(
            value=True,
            description='Show Snow Albedo Data',
            disabled=False,
            indent=False
        )
        
        # Statistics display
        stats_output = widgets.Output()
        
        def update_map(b):
            """Update map when button is clicked"""
            with stats_output:
                stats_output.clear_output()
                loading_label.value = 'Loading...'
                
                try:
                    # Get selected date
                    selected_date = date_picker.value.strftime('%Y-%m-%d')
                    
                    print(f"🔄 Updating map for {selected_date}...")
                    
                    # Create new map with selected parameters
                    new_map = create_glacier_map(
                        date=selected_date,
                        show_modis_pixels=show_pixels_checkbox.value,
                        show_snow_albedo=show_albedo_checkbox.value
                    )
                    
                    # Replace the map (this works in Jupyter environments)
                    Map.layers = new_map.layers
                    
                    loading_label.value = f'Updated: {selected_date}'
                    
                except Exception as e:
                    print(f"❌ Error updating map: {e}")
                    loading_label.value = 'Error occurred'
        
        # Connect button to update function
        update_button.on_click(update_map)
        
        # Create control panel
        controls = widgets.VBox([
            widgets.HTML("<h3>🗺️ Interactive Glacier Map Controls</h3>"),
            date_picker,
            show_pixels_checkbox,
            show_albedo_checkbox,
            update_button,
            loading_label,
            widgets.HTML("<hr>"),
            stats_output
        ])
        
        # Combine map and controls
        map_widget = widgets.HBox([
            widgets.VBox([Map], layout=widgets.Layout(width='70%')),
            widgets.VBox([controls], layout=widgets.Layout(width='30%'))
        ])
        
        # Display glacier info
        display_glacier_info()
        
        print("🎛️ Interactive map created!")
        print("💡 Use the date picker and checkboxes to customize the display")
        print("🔄 Click 'Update Map' to refresh with new settings")
        
        return map_widget
        
    except ImportError:
        print("⚠️ Interactive widgets require Jupyter environment")
        print("💡 Falling back to standard map...")
        return show_glacier_map()
    
    except Exception as e:
        print(f"❌ Error creating interactive map: {e}")
        print("💡 Falling back to standard map...")
        return show_glacier_map()

def create_date_range_browser():
    """
    Create a browser for exploring MODIS data across date ranges
    """
    
    try:
        # Date range selectors
        start_date_picker = widgets.DatePicker(
            description='Start Date:',
            value=datetime.date(2023, 6, 1),
            disabled=False
        )
        
        end_date_picker = widgets.DatePicker(
            description='End Date:',
            value=datetime.date(2023, 9, 30),
            disabled=False
        )
        
        # Create browse button
        browse_button = widgets.Button(
            description='Browse Date Range',
            button_style='success'
        )
        
        # Output for results
        browse_output = widgets.Output()
        
        def browse_dates(b):
            """Browse available MODIS data in date range"""
            with browse_output:
                browse_output.clear_output()
                
                start_str = start_date_picker.value.strftime('%Y-%m-%d')
                end_str = end_date_picker.value.strftime('%Y-%m-%d')
                
                print(f"🔍 Searching for MODIS data from {start_str} to {end_str}...")
                
                try:
                    # Check data availability
                    terra_collection = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
                        .filterBounds(athabasca_roi) \
                        .filterDate(start_str, end_str)
                    
                    aqua_collection = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
                        .filterBounds(athabasca_roi) \
                        .filterDate(start_str, end_str)
                    
                    terra_count = terra_collection.size().getInfo()
                    aqua_count = aqua_collection.size().getInfo()
                    
                    print(f"📊 Found {terra_count} Terra images and {aqua_count} Aqua images")
                    
                    # Get some sample dates
                    if terra_count > 0:
                        terra_dates = terra_collection.limit(10).aggregate_array('system:index').getInfo()
                        print(f"📅 Sample Terra dates: {terra_dates[:5]}")
                    
                    if aqua_count > 0:
                        aqua_dates = aqua_collection.limit(10).aggregate_array('system:index').getInfo()
                        print(f"📅 Sample Aqua dates: {aqua_dates[:5]}")
                        
                except Exception as e:
                    print(f"❌ Error browsing dates: {e}")
        
        browse_button.on_click(browse_dates)
        
        # Create browser widget
        browser_widget = widgets.VBox([
            widgets.HTML("<h3>📅 MODIS Data Browser</h3>"),
            start_date_picker,
            end_date_picker,
            browse_button,
            browse_output
        ])
        
        return browser_widget
        
    except Exception as e:
        print(f"❌ Error creating date browser: {e}")
        return None