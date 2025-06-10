"""
Mapping and Visualization Utilities for Streamlit Dashboard
Creates interactive maps with albedo data visualization
"""

import streamlit as st
import folium
from folium import plugins
import json
import random
import pandas as pd
from .ee_utils import initialize_earth_engine, get_modis_pixels_for_date, get_roi_from_geojson


def get_albedo_color_palette(albedo_value):
    """
    Convert albedo value to color using MODIS-style palette
    
    Args:
        albedo_value: Albedo value (0.0 - 1.0)
        
    Returns:
        str: Hex color code
    """
    # Normalize albedo value (0-1)
    normalized = max(0, min(1, albedo_value))
    
    # MODIS-style color palette (dark to bright)
    if normalized < 0.1:
        return '#440154'    # Dark purple (very low albedo)
    elif normalized < 0.3:
        return '#31688e'    # Blue (low albedo)
    elif normalized < 0.5:
        return '#35b779'    # Green (medium-low albedo)
    elif normalized < 0.7:
        return '#fde725'    # Yellow (medium-high albedo)
    elif normalized < 0.85:
        return '#ffffff'    # White (high albedo)
    else:
        return '#f0f0f0'    # Light gray (very high albedo)


def create_albedo_legend(map_obj, date, product='MOD10A1'):
    """
    Create detailed albedo legend for the map
    
    Args:
        map_obj: Folium map object
        date: Date string for the legend
        product: MODIS product type for display
    """
    # Product display name
    product_name = "MCD43A3 Broadband" if product == "MCD43A3" else "MOD10A1/MYD10A1 Snow"
    
    legend_html = f'''
    <div style="position: fixed; 
               bottom: 20px; left: 20px; width: 220px; height: 240px; 
               background-color: white; border: 2px solid #333; z-index:9999; 
               font-size: 11px; padding: 12px; border-radius: 8px;
               box-shadow: 0 2px 10px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #333;">MODIS Albedo</h4>
    <p style="margin: 0 0 4px 0; font-size: 10px; color: #666;">{date}</p>
    <p style="margin: 0 0 10px 0; font-size: 9px; color: #666;">{product_name}</p>
    <hr style="margin: 8px 0;">
    <div style="line-height: 18px;">
        <p style="margin: 4px 0;"><span style="color:#440154; font-size:14px;">●</span> Very Low (0.0-0.1)</p>
        <p style="margin: 4px 0;"><span style="color:#31688e; font-size:14px;">●</span> Low (0.1-0.3)</p>
        <p style="margin: 4px 0;"><span style="color:#35b779; font-size:14px;">●</span> Medium (0.3-0.5)</p>
        <p style="margin: 4px 0;"><span style="color:#fde725; font-size:14px;">●</span> High (0.5-0.7)</p>
        <p style="margin: 4px 0;"><span style="color:#ffffff; font-size:14px; text-shadow: 1px 1px 2px #000;">●</span> Very High (0.7+)</p>
    </div>
    <hr style="margin: 8px 0;">
    <p style="margin: 4px 0; font-size: 9px; color: #666; font-style: italic;">Each polygon = 500m MODIS pixel</p>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))


def create_fallback_albedo_visualization(map_obj, df_data):
    """
    Create fallback albedo visualization when Earth Engine is not available
    Uses representative points based on actual albedo data
    
    Args:
        map_obj: Folium map object
        df_data: DataFrame with albedo data
    """
    if df_data.empty:
        return
        
    # Use all data if it's for a specific date, otherwise sample
    if len(df_data) <= 50:
        sample_data = df_data
    else:
        # Use a sample of data for performance
        sample_data = df_data.sample(n=50)
    
    # Glacier center (updated to better center on Athabasca Glacier)
    center_lat = 52.188
    center_lon = -117.265
    
    # Calculate albedo range for color mapping
    min_albedo = sample_data['albedo_mean'].min()
    max_albedo = sample_data['albedo_mean'].max()
    
    # Create representative points within glacier area
    random.seed(42)  # Reproducible pattern
    
    for idx, row in sample_data.iterrows():
        # Create coordinates within glacier area
        lat_offset = random.uniform(-0.015, 0.015)
        lon_offset = random.uniform(-0.015, 0.015) 
        point_lat = center_lat + lat_offset
        point_lon = center_lon + lon_offset
        
        # Get color based on albedo value
        color = get_albedo_color_palette(row['albedo_mean'])
        
        # Create popup
        # Handle date formatting
        if 'date_str' in row:
            date_display = row['date_str']
        elif 'date' in row:
            try:
                date_display = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
            except:
                date_display = str(row['date'])
        else:
            date_display = 'N/A'
            
        popup_text = f"""
        <b>Albedo Observation</b><br>
        Date: {date_display}<br>
        Albedo: {row['albedo_mean']:.3f}<br>
        Elevation: {row.get('elevation', 'N/A')}<br>
        <i>Representative visualization</i>
        """
        
        # Add point to map
        folium.CircleMarker(
            location=[point_lat, point_lon],
            radius=6,
            popup=folium.Popup(popup_text, parse_html=True),
            color='white',
            weight=1,
            fillColor=color,
            fillOpacity=0.7,
            tooltip=f"Albedo: {row['albedo_mean']:.3f}"
        ).add_to(map_obj)
    
    # Add simple legend
    legend_html = f'''
    <div style="position: fixed; 
               bottom: 50px; left: 50px; width: 180px; height: 160px; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-size:12px; padding: 10px">
    <h4>Albedo Data</h4>
    <hr>
    <p><span style="color:#440154;">●</span> Low ({min_albedo:.2f})</p>
    <p><span style="color:#31688e;">●</span> Medium-Low</p>
    <p><span style="color:#35b779;">●</span> Medium</p>
    <p><span style="color:#fde725;">●</span> High</p>
    <p><span style="color:#ffffff; text-shadow: 1px 1px 1px #000000;">●</span> Very High ({max_albedo:.2f})</p>
    <hr>
    <small>Representative data points<br>
    Showing {len(sample_data)} points</small>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))


def _load_glacier_boundary_for_bounds():
    """
    Load glacier boundary for bounds calculation (without adding to map)
    Same logic as add_glacier_boundary but just returns the geojson
    """
    import json
    
    # PRIORITY 1: Try to load from shapefile (most accurate)
    shapefile_paths = [
        '../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # New organized path
        '../../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # Alternative organized path
    ]
    
    for shp_path in shapefile_paths:
        try:
            import geopandas as gpd
            
            # Load shapefile with geopandas
            gdf = gpd.read_file(shp_path)
            
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            
            # Convert to GeoJSON for compatibility
            glacier_geojson = json.loads(gdf.to_json())
            return glacier_geojson
            
        except (ImportError, Exception):
            # Geopandas not available or shapefile loading failed, continue to GeoJSON fallback
            continue
    
    # PRIORITY 2: Fallback to GeoJSON files
    geojson_paths = [
        '../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # New organized path
        '../../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # Alternative organized path
        '../Athabasca_mask_2023_cut.geojson',  # Legacy fallback
        '../../Athabasca_mask_2023_cut.geojson',  # Legacy fallback
        'Athabasca_mask_2023_cut.geojson'  # Same directory fallback
    ]
    
    for path in geojson_paths:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            continue
    
    # If all paths failed, create a fallback boundary
    try:
        fallback_boundary = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"name": "Athabasca Glacier (Approximate)"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-117.273, 52.179],
                        [-117.258, 52.162],
                        [-117.255, 52.162],
                        [-117.249, 52.195],
                        [-117.270, 52.202],
                        [-117.273, 52.179]
                    ]]
                }
            }]
        }
        return fallback_boundary
    except:
        return None


def calculate_glacier_bounds(glacier_geojson):
    """
    Calculate the bounding box and center of glacier from GeoJSON
    
    Args:
        glacier_geojson: GeoJSON data of glacier boundary
        
    Returns:
        tuple: (center_lat, center_lon, bounds) where bounds = [[south, west], [north, east]]
    """
    if not glacier_geojson or 'features' not in glacier_geojson:
        # Fallback to default Athabasca coordinates
        return 52.188, -117.265, [[52.17, -117.28], [52.21, -117.24]]
    
    try:
        # Extract all coordinates from all features
        all_lats = []
        all_lons = []
        
        for feature in glacier_geojson['features']:
            if 'geometry' in feature and feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
                coords = feature['geometry']['coordinates']
                
                # Handle Polygon vs MultiPolygon
                if feature['geometry']['type'] == 'Polygon':
                    coord_rings = coords
                else:  # MultiPolygon
                    coord_rings = []
                    for polygon in coords:
                        coord_rings.extend(polygon)
                
                # Extract lat/lon from coordinate rings
                for ring in coord_rings:
                    for coord in ring:
                        if len(coord) >= 2:
                            lon, lat = coord[0], coord[1]
                            all_lons.append(lon)
                            all_lats.append(lat)
        
        if all_lats and all_lons:
            # Calculate bounds
            min_lat, max_lat = min(all_lats), max(all_lats)
            min_lon, max_lon = min(all_lons), max(all_lons)
            
            # Calculate center
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            
            # Create bounds in folium format [[south, west], [north, east]]
            bounds = [[min_lat, min_lon], [max_lat, max_lon]]
            
            return center_lat, center_lon, bounds
        
    except Exception as e:
        print(f"Error calculating glacier bounds: {e}")
    
    # Fallback to default Athabasca coordinates
    return 52.188, -117.265, [[52.17, -117.28], [52.21, -117.24]]


def create_base_map(center_lat=52.188, center_lon=-117.265, zoom_start=13, satellite_only=False):
    """
    Create base map with satellite imagery
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        zoom_start: Initial zoom level
        satellite_only: If True, only use satellite basemap
        
    Returns:
        folium.Map: Base map with tile layers
    """
    if satellite_only:
        # Create map with satellite imagery as default
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles=None  # No default tiles
        )
        
        # Add satellite imagery as the only basemap
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Satellite',
            overlay=False,
            control=False  # No layer control since it's the only option
        ).add_to(m)
        
    else:
        # Create base map with multiple options
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # Add satellite imagery
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add terrain layer  
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', 
            name='Terrain',
            overlay=False,
            control=True
        ).add_to(m)
    
    return m


def add_glacier_boundary(map_obj, glacier_geojson_path=None):
    """
    Add glacier boundary to map from shapefile (preferred) or GeoJSON file
    
    Args:
        map_obj: Folium map object
        glacier_geojson_path: Path to glacier GeoJSON file (optional)
        
    Returns:
        dict: Loaded glacier GeoJSON data (None if failed)
    """
    # PRIORITY 1: Try to load from shapefile (most accurate)
    shapefile_paths = [
        '../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # New organized path
        '../../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # Alternative organized path
    ]
    
    for shp_path in shapefile_paths:
        try:
            import geopandas as gpd
            import json
            
            # Load shapefile with geopandas
            gdf = gpd.read_file(shp_path)
            
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            
            # Convert to GeoJSON for folium
            glacier_geojson = json.loads(gdf.to_json())
            
            # Add glacier boundary with enhanced styling
            folium.GeoJson(
                glacier_geojson,
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'blue',  # Blue color for shapefile
                    'weight': 3,
                    'fillOpacity': 0.1,
                    'dashArray': '5, 5'
                },
                popup=folium.Popup("Athabasca Glacier Boundary (Shapefile)", parse_html=True),
                tooltip="Athabasca Glacier (2023 ArcGIS)"
            ).add_to(map_obj)
            
            
            return glacier_geojson
            
        except ImportError:
            # Geopandas not available, continue to GeoJSON fallback
            continue
        except Exception as e:
            # Shapefile loading failed, continue to GeoJSON fallback
            continue
    
    # PRIORITY 2: Fallback to GeoJSON files
    geojson_paths = [
        glacier_geojson_path,  # User provided path
        '../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # New organized path
        '../../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # Alternative organized path
        '../Athabasca_mask_2023_cut.geojson',  # Legacy path (fallback)
        '../../Athabasca_mask_2023_cut.geojson',  # Legacy path (fallback)
        'Athabasca_mask_2023_cut.geojson',  # Same directory (fallback)
    ]
    
    # Filter out None values
    geojson_paths = [path for path in geojson_paths if path is not None]
    
    # Try to load from any of the GeoJSON paths
    for path in geojson_paths:
        try:
            with open(path, 'r') as f:
                glacier_geojson = json.load(f)
            
            # Add glacier boundary with standard styling
            folium.GeoJson(
                glacier_geojson,
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'red',  # Red color for GeoJSON
                    'weight': 3,
                    'fillOpacity': 0.1
                },
                popup=folium.Popup("Athabasca Glacier Boundary (GeoJSON)", parse_html=True),
                tooltip="Athabasca Glacier Boundary"
            ).add_to(map_obj)
            
            
            return glacier_geojson
            
        except Exception as e:
            continue  # Try next path
    
    # If all paths failed, create a fallback boundary
    try:
        # Create a simple polygon boundary from known coordinates
        fallback_boundary = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"name": "Athabasca Glacier (Approximate)"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-117.273, 52.179],
                        [-117.258, 52.162],
                        [-117.255, 52.162],
                        [-117.249, 52.195],
                        [-117.270, 52.202],
                        [-117.273, 52.179]
                    ]]
                }
            }]
        }
        
        # Add fallback boundary
        folium.GeoJson(
            fallback_boundary,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'orange',
                'weight': 2,
                'fillOpacity': 0.1,
                'dashArray': '5, 5'  # Dashed line to indicate it's approximate
            },
            popup=folium.Popup("Athabasca Glacier (Approximate Boundary)", parse_html=True),
            tooltip="Athabasca Glacier (Approximate)"
        ).add_to(map_obj)
        
        
        return fallback_boundary
        
    except Exception as e:
        with st.sidebar:
            st.warning(f"Could not load glacier boundary: {e}")
        return None


def create_albedo_map(df_data, selected_date=None, product='MOD10A1', qa_threshold=1, use_advanced_qa=False, algorithm_flags={}, selected_band=None, diffuse_fraction=None):
    """
    Create interactive Folium map showing MODIS albedo pixels within glacier mask
    Shows actual MODIS 500m pixel grid with real albedo values from Earth Engine
    
    Args:
        df_data: DataFrame with albedo observations (used for date filtering)
        selected_date: Specific date to show MODIS pixels for (YYYY-MM-DD format)
        product: MODIS product type ('MOD10A1' or 'MCD43A3')
        qa_threshold: Quality threshold for filtering (0, 1, or 2)
    
    Returns:
        folium.Map: Interactive map with real MODIS pixel visualization
    """
    # First, load glacier boundary to get its bounds
    glacier_geojson = _load_glacier_boundary_for_bounds()
    
    # Calculate glacier center and bounds for auto-centering
    center_lat, center_lon, bounds = calculate_glacier_bounds(glacier_geojson)
    
    # Create base map centered on glacier with high zoom for detailed MODIS pixel analysis
    m = create_base_map(center_lat=center_lat, center_lon=center_lon, zoom_start=17, satellite_only=True)
    
    # Add glacier boundary to the map (and get updated geojson if needed)
    glacier_geojson = add_glacier_boundary(m) or glacier_geojson
    
    # Fit map to glacier bounds with tight padding for close-up view
    if bounds:
        try:
            # Calculate tighter bounds for closer zoom
            min_lat, min_lon = bounds[0]
            max_lat, max_lon = bounds[1]
            
            # Add minimal buffer around glacier (about 200m on each side) for tight centered view
            lat_buffer = 0.0018  # ~200m at this latitude
            lon_buffer = 0.003   # ~200m at this latitude (adjusted for longitude at 52°N)
            
            tight_bounds = [
                [min_lat - lat_buffer, min_lon - lon_buffer],
                [max_lat + lat_buffer, max_lon + lon_buffer]
            ]
            
            m.fit_bounds(tight_bounds, padding=(3, 3))  # Minimal padding for tight centered view
        except:
            pass  # If fit_bounds fails, keep the centered view
    
    # Add MODIS pixel visualization if we have a specific date
    if selected_date:
        # Check if Earth Engine is available and initialized
        with st.spinner("Checking Earth Engine authentication..."):
            ee_available = initialize_earth_engine()
        
        if not ee_available:
            # Show clear message about Earth Engine requirement
            st.warning("🌍 **Earth Engine Authentication Needed for Real MODIS Pixels**")
            
            # Check what's missing
            if 'gee_service_account' not in st.secrets and 'gee_project' not in st.secrets:
                st.markdown("""
                **📋 Quick Setup Options:**
                
                **Option A: Service Account** (recommended)
                1. Add your service account JSON to Streamlit secrets as `[gee_service_account]`
                2. Make sure it's registered at [code.earthengine.google.com/register](https://code.earthengine.google.com/register)
                
                **Option B: Project ID** (simpler)
                1. Add to Streamlit secrets: `gee_project = "your-google-cloud-project-id"`
                """)
            else:
                st.error("Authentication configured but failed. Check the sidebar for error details.")
            
            st.info("💡 **For now:** Map shows glacier boundary only. Add authentication to see real MODIS pixels!")
            return m
            
        try:
            import ee
            
            # Define Athabasca ROI from the geojson if available
            athabasca_roi = get_roi_from_geojson(glacier_geojson)
            
            # Get MODIS data for the selected date
            print(f"DEBUG MAPS: About to call get_modis_pixels_for_date for {selected_date}")
            modis_pixels = get_modis_pixels_for_date(
                selected_date, athabasca_roi, product, qa_threshold,
                use_advanced_qa=use_advanced_qa, algorithm_flags=algorithm_flags,
                selected_band=selected_band, diffuse_fraction=diffuse_fraction
            )
            print(f"DEBUG MAPS: Successfully got MODIS pixels for {selected_date}")
            
            if modis_pixels and 'features' in modis_pixels:
                pixel_count = len(modis_pixels['features'])
                # Display final pixel count in sidebar
                with st.sidebar:
                    st.write(f"🗺️ Displaying {pixel_count} MODIS pixels for {selected_date}")
                
                # Add each MODIS pixel as a colored polygon
                for feature in modis_pixels['features']:
                    if 'properties' in feature and 'albedo_value' in feature['properties']:
                        albedo_value = feature['properties']['albedo_value']
                        
                        # Skip invalid values
                        if albedo_value is None or albedo_value < 0 or albedo_value > 1:
                            continue
                            
                        # Get color based on albedo value
                        color = get_albedo_color_palette(albedo_value)
                        
                        # Create enhanced popup with detailed technical info
                        product_display = feature['properties'].get('product', product)
                        quality_filter = feature['properties'].get('quality_filter', 'Standard filtering')
                        
                        # Get satellite source - different for MCD43A3
                        if product == 'MCD43A3':
                            satellite_source = 'Combined Terra+Aqua'
                        else:
                            satellite_source = feature['properties'].get('satellite', 'Terra/Aqua')
                        
                        # Calculate pixel coordinates (approximate center) with safe handling
                        try:
                            coords = feature['geometry']['coordinates'][0]
                            if coords and len(coords) > 0:
                                # Get bounding box with safe coordinate extraction
                                lons = []
                                lats = []
                                for coord in coords:
                                    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                                        # Ensure we get numbers, not nested lists
                                        lon = coord[0]
                                        lat = coord[1]
                                        if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
                                            lons.append(lon)
                                            lats.append(lat)
                                
                                if lons and lats:
                                    center_lon = sum(lons) / len(lons)
                                    center_lat = sum(lats) / len(lats)
                                else:
                                    center_lon = center_lat = "N/A"
                            else:
                                center_lon = center_lat = "N/A"
                        except Exception as coord_error:
                            print(f"DEBUG COORDS ERROR: {coord_error} for feature: {feature.get('properties', {}).get('date', 'unknown')}")
                            center_lon = center_lat = "N/A"
                        
                        # Format coordinates safely
                        if isinstance(center_lat, (int, float)) and isinstance(center_lon, (int, float)):
                            coord_text = f"{center_lat:.4f}°N, {abs(center_lon):.4f}°W"
                        else:
                            coord_text = "N/A"
                        
                        # Create appropriate tooltip content based on product
                        if 'MCD43A3' in product_display:
                            if 'Visible' in product_display:
                                albedo_type = "Visible Albedo"
                                extra_info = "<br><small style='color: #666;'>0.3-0.7 μm BSA</small>"
                            elif 'NIR' in product_display:
                                albedo_type = "NIR Albedo"
                                extra_info = "<br><small style='color: #666;'>0.7-5.0 μm BSA</small>"
                            else:
                                albedo_type = "Blue-Sky Albedo"
                                # Get dynamic BSA/WSA percentages from feature properties
                                bsa_pct = feature['properties'].get('bsa_percentage', 80)
                                wsa_pct = feature['properties'].get('wsa_percentage', 20)
                                extra_info = f"<br><small style='color: #666;'>BSA: {bsa_pct:.0f}%, WSA: {wsa_pct:.0f}%</small>"
                        else:
                            albedo_type = "Albedo"
                            extra_info = ""
                        
                        # Simple and concise HTML content for tooltip
                        html_content = f"""
                        <div style="font-family: Arial, sans-serif; padding: 10px; background: rgba(255,255,255,0.95); border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                            <div style="font-size: 18px; font-weight: bold; color: #e65100; margin-bottom: 8px;">
                                {albedo_type}: {albedo_value:.3f}{extra_info}
                            </div>
                            <div style="font-size: 13px; line-height: 1.5;">
                                <strong>Product:</strong> {product_display}<br>
                                <strong>Date:</strong> {selected_date}<br>
                                <strong>Source:</strong> {satellite_source}<br>
                                <strong>Quality:</strong> {quality_filter}
                            </div>
                        </div>
                        """
                        
                        # Use the full HTML content in tooltip (no popup needed)
                        # Add pixel polygon to map with comprehensive tooltip only
                        folium.GeoJson(
                            feature,
                            style_function=lambda x, color=color: {
                                'fillColor': color,
                                'color': 'white',
                                'weight': 1,
                                'fillOpacity': 0.8,
                                'opacity': 1.0
                            },
                            tooltip=folium.Tooltip(html_content, max_width=280, sticky=True)
                        ).add_to(m)
                
                # Create detailed color legend
                # create_albedo_legend(m, selected_date, product)  # Commented out per user request
                
            else:
                st.warning(f"No valid MODIS pixels found for {selected_date}")
                
        except Exception as e:
            print(f"DEBUG MAPS ERROR: {e}")
            print(f"DEBUG MAPS ERROR TYPE: {type(e)}")
            print(f"DEBUG MAPS ERROR STR: {str(e)}")
            st.error(f"Error loading MODIS pixels: {e}")
            st.info("Falling back to basic map view")
    
    else:
        st.info("Select a specific date to view MODIS pixel data")
        
        # Show fallback visualization with available data
        if not df_data.empty:
            # Create representative points from actual data
            create_fallback_albedo_visualization(m, df_data)
    
    # Add measurement tool
    add_measurement_tool(m)
    
    # No layer control needed for satellite-only map
    return m


def add_measurement_tool(m):
    """
    Add measurement tool to the map for measuring distances between pixels
    """
    # Add measurement plugin
    measure_control = plugins.MeasureControl(
        position='topleft',
        primary_length_unit='meters',
        secondary_length_unit='kilometers',
        primary_area_unit='sqmeters',
        secondary_area_unit='hectares',
        active_color='red',
        completed_color='blue'
    )
    measure_control.add_to(m)
    
    # Pixel size reference validated (494-497m measured vs 500m theoretical)
    # add_pixel_size_reference(m)  # Commented out after validation
    
    # Add draw plugin for more advanced measurements
    draw = plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': {'allowIntersection': False},
            'polygon': {'allowIntersection': False},
            'circle': False,
            'rectangle': True,
            'marker': True,
            'circlemarker': False
        },
        edit_options={'edit': True}
    )
    draw.add_to(m)
    
    return m


def add_pixel_size_reference(m):
    """
    Add a 500m × 500m reference square to show theoretical MODIS pixel size
    """
    # Athabasca Glacier center coordinates
    center_lat = 52.194
    center_lon = -117.238
    
    # Calculate 500m offset in degrees (approximate)
    # At 52°N: 1 degree lat ≈ 111,320m, 1 degree lon ≈ 67,800m
    lat_offset = 250 / 111320  # 250m = half pixel
    lon_offset = 250 / 67800   # 250m = half pixel
    
    # Create 500m × 500m square
    square_coords = [
        [center_lat - lat_offset, center_lon - lon_offset],  # SW
        [center_lat - lat_offset, center_lon + lon_offset],  # SE
        [center_lat + lat_offset, center_lon + lon_offset],  # NE
        [center_lat + lat_offset, center_lon - lon_offset],  # NW
        [center_lat - lat_offset, center_lon - lon_offset]   # Close
    ]
    
    # Add reference square
    folium.Polygon(
        locations=square_coords,
        color='yellow',
        weight=3,
        fill=False,
        opacity=0.8,
        popup=folium.Popup(
            "<b>📏 MODIS Pixel Reference</b><br>"
            "Theoretical size: 500m × 500m<br>"
            "<small>Use measurement tool to compare</small>",
            max_width=200
        ),
        tooltip="📏 500m Reference Square"
    ).add_to(m)
    
    return m