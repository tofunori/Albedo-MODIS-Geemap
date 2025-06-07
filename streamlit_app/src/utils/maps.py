"""
Mapping and Visualization Utilities for Streamlit Dashboard
Creates interactive maps with albedo data visualization
"""

import streamlit as st
import folium
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
        sample_size = min(50, len(df_data))
        sample_data = df_data.sample(n=sample_size)
    
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
    Add glacier boundary to map from GeoJSON file
    
    Args:
        map_obj: Folium map object
        glacier_geojson_path: Path to glacier GeoJSON file (optional)
        
    Returns:
        dict: Loaded glacier GeoJSON data (None if failed)
    """
    # Try multiple possible paths for the glacier boundary file
    possible_paths = [
        glacier_geojson_path,  # User provided path
        '../Athabasca_mask_2023_cut.geojson',  # Local development
        '../../Athabasca_mask_2023_cut.geojson',  # Alternative local
        'Athabasca_mask_2023_cut.geojson',  # Same directory
    ]
    
    # Filter out None values
    possible_paths = [path for path in possible_paths if path is not None]
    
    # Try to load from any of the possible paths
    for path in possible_paths:
        try:
            with open(path, 'r') as f:
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
        
        with st.sidebar:
            st.info("ℹ️ Using approximate glacier boundary")
        
        return fallback_boundary
        
    except Exception as e:
        with st.sidebar:
            st.warning(f"Could not load glacier boundary: {e}")
        return None


def create_albedo_map(df_data, selected_date=None, product='MOD10A1', qa_threshold=1):
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
    # Create base map with satellite imagery only
    m = create_base_map(satellite_only=True)
    
    # Load glacier boundary
    glacier_geojson = add_glacier_boundary(m)
    
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
            modis_pixels = get_modis_pixels_for_date(selected_date, athabasca_roi, product, qa_threshold)
            
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
                        
                        # Create popup with pixel info
                        product_display = feature['properties'].get('product', product)
                        quality_filter = feature['properties'].get('quality_filter', 'Standard filtering')
                        popup_text = f"""
                        <b>MODIS Pixel</b><br>
                        Date: {selected_date}<br>
                        Albedo: {albedo_value:.3f}<br>
                        Pixel Area: ~500m x 500m<br>
                        Product: {product_display}<br>
                        Quality: {quality_filter}
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
                create_albedo_legend(m, selected_date, product)
                
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
    
    # No layer control needed for satellite-only map
    return m