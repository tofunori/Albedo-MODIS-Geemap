"""
Mapping and Visualization Utilities for Streamlit Dashboard
Creates interactive maps with albedo data visualization
"""

import streamlit as st
import folium
import json
import random
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


def create_albedo_legend(map_obj, date):
    """
    Create detailed albedo legend for the map
    
    Args:
        map_obj: Folium map object
        date: Date string for the legend
    """
    legend_html = f'''
    <div style="position: fixed; 
               bottom: 50px; left: 50px; width: 200px; height: 180px; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-size:12px; padding: 10px">
    <h4>MODIS Albedo - {date}</h4>
    <hr>
    <p><span style="color:#440154; font-size:16px;">●</span> Very Low (0.0-0.1)</p>
    <p><span style="color:#31688e; font-size:16px;">●</span> Low (0.1-0.3)</p>
    <p><span style="color:#35b779; font-size:16px;">●</span> Medium (0.3-0.5)</p>
    <p><span style="color:#fde725; font-size:16px;">●</span> High (0.5-0.7)</p>
    <p><span style="color:#ffffff; font-size:16px; text-shadow: 1px 1px 1px #000000;">●</span> Very High (0.7+)</p>
    <hr>
    <small>Each polygon = 500m MODIS pixel</small>
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
        
    # Use a sample of recent data
    sample_size = min(30, len(df_data))
    sample_data = df_data.sample(n=sample_size) if len(df_data) > sample_size else df_data
    
    # Glacier center
    center_lat = 52.2
    center_lon = -117.25
    
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
        popup_text = f"""
        <b>Albedo Observation</b><br>
        Date: {row['date']}<br>
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
               bottom: 50px; left: 50px; width: 180px; height: 140px; 
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
    <small>Representative data points</small>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))


def create_base_map(center_lat=52.2, center_lon=-117.25, zoom_start=13):
    """
    Create base map with multiple tile layers
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        zoom_start: Initial zoom level
        
    Returns:
        folium.Map: Base map with tile layers
    """
    # Create base map
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


def add_glacier_boundary(map_obj, glacier_geojson_path='../Athabasca_mask_2023_cut.geojson'):
    """
    Add glacier boundary to map from GeoJSON file
    
    Args:
        map_obj: Folium map object
        glacier_geojson_path: Path to glacier GeoJSON file
        
    Returns:
        dict: Loaded glacier GeoJSON data (None if failed)
    """
    try:
        with open(glacier_geojson_path, 'r') as f:
            glacier_geojson = json.load(f)
        
        # Add glacier boundary
        folium.GeoJson(
            glacier_geojson,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'red',
                'weight': 3,
                'fillOpacity': 0.1
            },
            popup=folium.Popup("Athabasca Glacier Boundary", parse_html=True),
            tooltip="Athabasca Glacier Boundary"
        ).add_to(map_obj)
        
        return glacier_geojson
        
    except Exception as e:
        st.warning(f"Could not load glacier boundary: {e}")
        return None


def create_albedo_map(df_data, selected_date=None):
    """
    Create interactive Folium map showing MODIS albedo pixels within glacier mask
    Shows actual MODIS 500m pixel grid with real albedo values from Earth Engine
    
    Args:
        df_data: DataFrame with albedo observations (used for date filtering)
        selected_date: Specific date to show MODIS pixels for (YYYY-MM-DD format)
    
    Returns:
        folium.Map: Interactive map with real MODIS pixel visualization
    """
    # Create base map
    m = create_base_map()
    
    # Load glacier boundary
    glacier_geojson = add_glacier_boundary(m)
    
    # Add MODIS pixel visualization if we have a specific date
    if selected_date:
        # Check if Earth Engine is available and initialized
        if not initialize_earth_engine():
            st.info("🗺️ Showing basic map without MODIS pixels due to Earth Engine authentication issue")
            return m
            
        try:
            import ee
            
            # Define Athabasca ROI from the geojson if available
            athabasca_roi = get_roi_from_geojson(glacier_geojson)
            
            # Get MODIS data for the selected date
            modis_pixels = get_modis_pixels_for_date(selected_date, athabasca_roi)
            
            if modis_pixels and 'features' in modis_pixels:
                pixel_count = len(modis_pixels['features'])
                st.info(f"Found {pixel_count} MODIS pixels with data for {selected_date}")
                
                # Add each MODIS pixel as a colored polygon
                for feature in modis_pixels['features']:
                    if 'properties' in feature and 'albedo_value' in feature['properties']:
                        albedo_value = feature['properties']['albedo_value']
                        
                        # Skip invalid values
                        if albedo_value is None or albedo_value < 0 or albedo_value > 1:
                            continue
                            
                        # Get color based on albedo value
                        color = get_albedo_color_palette(albedo_value)
                        
                        # Create popup with pixel info
                        popup_text = f"""
                        <b>MODIS Pixel</b><br>
                        Date: {selected_date}<br>
                        Albedo: {albedo_value:.3f}<br>
                        Pixel Area: ~500m x 500m<br>
                        Product: MOD10A1/MYD10A1
                        """
                        
                        # Add pixel polygon to map
                        folium.GeoJson(
                            feature,
                            style_function=lambda x, color=color: {
                                'fillColor': color,
                                'color': 'white',
                                'weight': 1,
                                'fillOpacity': 0.8,
                                'opacity': 1.0
                            },
                            popup=folium.Popup(popup_text, parse_html=True),
                            tooltip=f"Albedo: {albedo_value:.3f}"
                        ).add_to(m)
                
                # Create detailed color legend
                create_albedo_legend(m, selected_date)
                
            else:
                st.warning(f"No valid MODIS pixels found for {selected_date}")
                
        except Exception as e:
            st.error(f"Error loading MODIS pixels: {e}")
            st.info("Falling back to basic map view")
    
    else:
        st.info("Select a specific date to view MODIS pixel data")
        
        # Show fallback visualization with available data
        if not df_data.empty:
            # Create representative points from actual data
            create_fallback_albedo_visualization(m, df_data)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m