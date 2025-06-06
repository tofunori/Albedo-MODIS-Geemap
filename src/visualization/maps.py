"""
Mapping Module for MODIS Albedo Analysis
Creates interactive maps using folium and Earth Engine
"""

import ee
import folium
import numpy as np
from config import athabasca_roi


def create_elevation_map(output_file='athabasca_elevation_map.html'):
    """
    Create an interactive elevation map of Athabasca Glacier
    Shows elevation bands and median elevation line
    
    Args:
        output_file: Output HTML filename
    
    Returns:
        folium.Map: Interactive map object
    """
    print("🗺️ Creating interactive elevation map of Athabasca Glacier...")
    
    try:
        # Get SRTM elevation data
        srtm = ee.Image("USGS/SRTMGL1_003").select('elevation')
        
        # Mask to glacier area
        glacier_elevation = srtm.clip(athabasca_roi)
        
        # Get elevation statistics
        elevation_stats = glacier_elevation.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.median(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.percentile([25, 75]),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        elev_min = elevation_stats.get('elevation_min', 1900)
        elev_max = elevation_stats.get('elevation_max', 2400)
        elev_median = elevation_stats.get('elevation_median', 2100)
        elev_p25 = elevation_stats.get('elevation_p25', 2000)
        elev_p75 = elevation_stats.get('elevation_p75', 2200)
        
        print(f"📏 Glacier elevation range: {elev_min:.0f}m - {elev_max:.0f}m")
        print(f"📏 Median elevation: {elev_median:.0f}m")
        
        # Get glacier center for map
        glacier_center = athabasca_roi.centroid().coordinates().getInfo()
        center_lat, center_lon = glacier_center[1], glacier_center[0]
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
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
        
        # Define visualization parameters for elevation
        vis_params = {
            'min': elev_min,
            'max': elev_max,
            'palette': ['#0000FF', '#00FFFF', '#FFFF00', '#FF0000', '#FFFFFF']  # Blue to white
        }
        
        # Get map ID for elevation raster
        map_id_dict = ee.Image(glacier_elevation).getMapId(vis_params)
        
        # Add elevation layer
        folium.raster_layers.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name='Glacier Elevation',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add glacier boundary
        glacier_boundary = athabasca_roi.getInfo()
        folium.GeoJson(
            glacier_boundary,
            style_function=lambda x: {
                'fillColor': 'none',
                'color': 'red',
                'weight': 3,
                'opacity': 1.0
            },
            popup='Athabasca Glacier Boundary',
            tooltip='Glacier Boundary'
        ).add_to(m)
        
        # Add median elevation marker
        folium.Marker(
            [center_lat, center_lon],
            popup=f'<b>Athabasca Glacier</b><br>Median Elevation: {elev_median:.0f}m<br>Range: {elev_min:.0f}m - {elev_max:.0f}m',
            tooltip=f'Median: {elev_median:.0f}m',
            icon=folium.Icon(color='red', icon='mountain')
        ).add_to(m)
        
        # Add elevation contour lines
        # Create contour lines at key elevations
        contour_elevations = [elev_median - 100, elev_median, elev_median + 100]
        contour_colors = ['#4682B4', '#FF0000', '#2E8B57']  # Blue, Red, Green
        contour_labels = ['Below Median Boundary', 'Median Elevation', 'Above Median Boundary']
        
        for i, (elevation, color, label) in enumerate(zip(contour_elevations, contour_colors, contour_labels)):
            # Create contour for this elevation
            contour = glacier_elevation.eq(ee.Number(elevation).round())
            
            # Convert to vectors (this is simplified - in practice you'd need more sophisticated contouring)
            try:
                contour_features = contour.selfMask().reduceToVectors(
                    geometry=athabasca_roi,
                    scale=30,
                    maxPixels=1e8
                )
                
                contour_geojson = contour_features.getInfo()
                if contour_geojson['features']:
                    folium.GeoJson(
                        contour_geojson,
                        style_function=lambda x, color=color: {
                            'color': color,
                            'weight': 3,
                            'opacity': 0.8
                        },
                        popup=f'{label}: {elevation:.0f}m',
                        tooltip=f'{elevation:.0f}m elevation'
                    ).add_to(m)
            except:
                print(f"⚠️ Could not add contour for {elevation:.0f}m")
        
        # Add legend
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 220px; height: 140px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <b>Athabasca Glacier Elevation</b><br>
        <hr>
        <b>Elevation Range:</b> {elev_min:.0f}m - {elev_max:.0f}m<br>
        <b>Median Elevation:</b> {elev_median:.0f}m<br>
        <hr>
        <b>Williamson & Menounos Bands:</b><br>
        • Above: >{elev_median+100:.0f}m<br>
        • Near: {elev_median-100:.0f}m - {elev_median+100:.0f}m<br>
        • Below: <{elev_median-100:.0f}m
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save map
        m.save(output_file)
        print(f"📊 Elevation map saved: {output_file}")
        
        return m
        
    except Exception as e:
        print(f"❌ Error creating elevation map: {e}")
        return None


def create_albedo_comparison_map(date1, date2, output_file='albedo_comparison.html'):
    """
    Create an interactive map comparing albedo between two dates
    
    Args:
        date1: First date (YYYY-MM-DD)
        date2: Second date (YYYY-MM-DD)
        output_file: Output HTML filename
    
    Returns:
        folium.Map: Interactive comparison map
    """
    print(f"🗺️ Creating albedo comparison map: {date1} vs {date2}")
    
    try:
        # Initialize Earth Engine
        ee.Initialize()
        
        # Get MODIS collections
        mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
        myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
        
        # Function to get albedo for a date
        def get_albedo(date):
            start = ee.Date(date)
            end = start.advance(1, 'day')
            
            # Combine Terra and Aqua
            combined = mod10a1.merge(myd10a1)
            
            # Filter and process
            albedo = combined.filterDate(start, end).filterBounds(athabasca_roi)\
                .select('NDSI_Snow_Cover')\
                .map(lambda img: img.divide(100).clamp(0, 1))\
                .mean()\
                .clip(athabasca_roi)
            
            return albedo
        
        # Get albedo for both dates
        albedo1 = get_albedo(date1)
        albedo2 = get_albedo(date2)
        
        # Calculate difference
        difference = albedo2.subtract(albedo1)
        
        # Get glacier center
        glacier_center = athabasca_roi.centroid().coordinates().getInfo()
        center_lat, center_lon = glacier_center[1], glacier_center[0]
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        # Add satellite base
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Albedo visualization parameters
        albedo_vis = {
            'min': 0.0,
            'max': 1.0,
            'palette': ['#000000', '#333333', '#666666', '#999999', '#CCCCCC', '#FFFFFF']
        }
        
        # Difference visualization parameters
        diff_vis = {
            'min': -0.3,
            'max': 0.3,
            'palette': ['#FF0000', '#FFFF00', '#FFFFFF', '#00FFFF', '#0000FF']
        }
        
        # Add layers
        # Date 1 albedo
        map_id1 = albedo1.getMapId(albedo_vis)
        folium.raster_layers.TileLayer(
            tiles=map_id1['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'Albedo {date1}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Date 2 albedo
        map_id2 = albedo2.getMapId(albedo_vis)
        folium.raster_layers.TileLayer(
            tiles=map_id2['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'Albedo {date2}',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Difference
        map_id_diff = difference.getMapId(diff_vis)
        folium.raster_layers.TileLayer(
            tiles=map_id_diff['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f'Change ({date2} - {date1})',
            overlay=True,
            control=True
        ).add_to(m)
        
        # Add glacier boundary
        glacier_boundary = athabasca_roi.getInfo()
        folium.GeoJson(
            glacier_boundary,
            style_function=lambda x: {
                'fillColor': 'none',
                'color': 'red',
                'weight': 3,
                'opacity': 1.0
            },
            popup='Athabasca Glacier',
            tooltip='Glacier Boundary'
        ).add_to(m)
        
        # Add legend
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <b>Albedo Comparison</b><br>
        <hr>
        <b>Date 1:</b> {date1}<br>
        <b>Date 2:</b> {date2}<br>
        <hr>
        <b>Change Colors:</b><br>
        • Red: Decrease<br>
        • Blue: Increase
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save map
        m.save(output_file)
        print(f"📊 Comparison map saved: {output_file}")
        
        return m
        
    except Exception as e:
        print(f"❌ Error creating comparison map: {e}")
        return None 