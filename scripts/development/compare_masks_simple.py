#!/usr/bin/env python3
"""
Simple comparison between different masks to understand pixel count differences
"""

import ee
import json
import os

ee.Initialize()

print("🔍 COMPARING GLACIER MASKS")
print("=" * 50)

# Load different masks
masks = {}

# 1. Current ArcGIS shapefile
shapefile_path = 'Masque_athabasca_2023_Arcgis.shp'
if os.path.exists(shapefile_path):
    import geopandas as gpd
    gdf = gpd.read_file(shapefile_path)
    
    if len(gdf) > 1:
        unified_geom = gdf.geometry.unary_union
    else:
        unified_geom = gdf.geometry.iloc[0]
    
    coords = [list(unified_geom.exterior.coords)]
    masks['ArcGIS_Shapefile'] = ee.Geometry.Polygon(coords)
    
    area_gdf = gdf.to_crs('EPSG:3857').geometry.area.sum() / 1e6
    print(f"✅ ArcGIS Shapefile: {area_gdf:.2f} km² (geopandas)")

# 2. GeoJSON with first polygon only (Streamlit method)
geojson_path = 'Athabasca_mask_2023_cut.geojson'
if os.path.exists(geojson_path):
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    first_feature = data['features'][0]
    geometry = first_feature['geometry']
    
    if geometry['type'] == 'MultiPolygon':
        coords = geometry['coordinates'][0]  # First polygon only
        masks['GeoJSON_FirstPolygon'] = ee.Geometry.Polygon(coords)
        print(f"✅ GeoJSON (first polygon): Loaded")
    
# Compare areas in Earth Engine
print(f"\n📏 EARTH ENGINE AREA COMPARISON:")
for name, mask in masks.items():
    try:
        area_km2 = mask.area().divide(1e6).getInfo()
        print(f"   {name}: {area_km2:.2f} km²")
    except Exception as e:
        print(f"   {name}: Error - {e}")

# Test pixel counts with a known date that had 36 pixels
print(f"\n🧮 PIXEL COUNT COMPARISON:")
print(f"Using date range 2023-07-01 to 2023-07-10 with QA ≤ 1")

for name, mask in masks.items():
    try:
        # Get MODIS collection
        collection = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterBounds(mask) \
            .filterDate('2023-07-01', '2023-07-10')
        
        # Take first available image
        if collection.size().getInfo() > 0:
            image = collection.first()
            
            # Apply same QA filtering as in your extraction
            albedo = image.select('Snow_Albedo_Daily_Tile')
            qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            valid_albedo = albedo.gte(5).And(albedo.lte(99))
            good_quality = qa.lte(1)
            masked_albedo = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
            
            # Count pixels
            pixel_count = masked_albedo.reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=mask,
                scale=500,
                maxPixels=1e6
            ).get('Snow_Albedo_Daily_Tile').getInfo()
            
            estimated_area = pixel_count * 0.25
            print(f"   {name}: {pixel_count} pixels ({estimated_area:.2f} km²)")
        else:
            print(f"   {name}: No MODIS data available")
            
    except Exception as e:
        print(f"   {name}: Error - {str(e)[:60]}...")

# Test with the exact same fusion method as your extraction
print(f"\n🛰️ TESTING WITH TERRA-AQUA FUSION (like your extraction):")

for name, mask in masks.items():
    try:
        # Same as your extraction code
        mod_col = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterBounds(mask) \
            .filterDate('2023-07-01', '2023-07-10')
        
        myd_col = ee.ImageCollection('MODIS/061/MYD10A1') \
            .filterBounds(mask) \
            .filterDate('2023-07-01', '2023-07-10')
        
        # Simple merge (not the full literature method, but similar)
        combined = mod_col.merge(myd_col)
        
        if combined.size().getInfo() > 0:
            # Take first image and apply QA
            image = combined.first()
            
            albedo = image.select('Snow_Albedo_Daily_Tile')
            qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            valid_albedo = albedo.gte(5).And(albedo.lte(99))
            good_quality = qa.lte(1)
            masked_albedo = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
            
            pixel_count = masked_albedo.reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=mask,
                scale=500,
                maxPixels=1e6
            ).get('Snow_Albedo_Daily_Tile').getInfo()
            
            estimated_area = pixel_count * 0.25
            print(f"   {name}: {pixel_count} pixels ({estimated_area:.2f} km²)")
        else:
            print(f"   {name}: No MODIS data available")
            
    except Exception as e:
        print(f"   {name}: Error - {str(e)[:60]}...")

print(f"\n📊 SUMMARY:")
print(f"   - Your manual count: ~20 pixels")
print(f"   - Expected area: ~3.6 km²") 
print(f"   - If a mask gives ~36 pixels (9 km²), it's 2.5x too large")
print(f"   - The difference might be due to:")
print(f"     • Different glacier boundaries in each mask")
print(f"     • Edge pixels being counted differently") 
print(f"     • QA filtering removing different amounts of data")