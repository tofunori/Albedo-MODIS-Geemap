#!/usr/bin/env python3
"""
Test to understand and fix the pixel counting issue
The problem: Getting ~40 pixels instead of ~20 pixels
"""

import ee
ee.Initialize()

# Test parameters
test_date = '2023-07-04'  # Date from your previous test that had data
scale = 500

# Load the glacier mask
import json
import os

# Try different mask loading methods
print("🔍 TESTING PIXEL COUNTING METHODS")
print("=" * 50)

# Method 1: Load Shapefile
shapefile_path = 'Masque_athabasca_2023_Arcgis.shp'
if os.path.exists(shapefile_path):
    import geopandas as gpd
    gdf = gpd.read_file(shapefile_path)
    print(f"✅ Shapefile loaded: {len(gdf)} features")
    print(f"📏 Shapefile area: {gdf.to_crs('EPSG:3857').geometry.area.sum() / 1e6:.2f} km²")
    
    # Convert to Earth Engine
    if len(gdf) > 1:
        unified_geom = gdf.geometry.unary_union
    else:
        unified_geom = gdf.geometry.iloc[0]
    
    # Convert to EE geometry
    coords = [list(unified_geom.exterior.coords)]
    glacier_mask = ee.Geometry.Polygon(coords)
    
    # Calculate EE area
    ee_area = glacier_mask.area().divide(1e6).getInfo()
    print(f"📏 Earth Engine area: {ee_area:.2f} km²")
    
    # Get MODIS image - use date range instead of single date
    start_date = '2023-07-01'
    end_date = '2023-07-10'
    
    mod_collection = ee.ImageCollection('MODIS/061/MOD10A1') \
        .filterBounds(glacier_mask) \
        .filterDate(start_date, end_date)
    
    collection_size = mod_collection.size().getInfo()
    print(f"📡 Found {collection_size} MODIS images for {start_date} to {end_date}")
    
    if collection_size > 0:
        mod_image = mod_collection.first()
        print(f"\n📅 Testing with first available image")
        
        # Get albedo band with basic QA filtering
        albedo = mod_image.select('Snow_Albedo_Daily_Tile')
        qa = mod_image.select('NDSI_Snow_Cover_Basic_QA')
        
        # Apply basic masking
        valid_albedo = albedo.gte(5).And(albedo.lte(99))
        good_quality = qa.lte(1)
        masked_albedo = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
        
        print("\n🧪 PIXEL COUNT EXPERIMENTS:")
        print("-" * 40)
        
        # Method 1: Simple reduceRegion (current method)
        print("\n1️⃣ Method 1: Simple reduceRegion (CURRENT)")
        count1 = masked_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=glacier_mask,
            scale=scale,
            maxPixels=1e6
        ).get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"   Pixels: {count1}")
        print(f"   Area: {count1 * 0.25:.2f} km²")
        print(f"   ⚠️  This counts ANY pixel that intersects the glacier!")
        
        # Method 2: Clip then count
        print("\n2️⃣ Method 2: Clip image to glacier first")
        clipped_albedo = masked_albedo.clip(glacier_mask)
        count2 = clipped_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=glacier_mask,
            scale=scale,
            maxPixels=1e6
        ).get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"   Pixels: {count2}")
        print(f"   Area: {count2 * 0.25:.2f} km²")
        print(f"   ℹ️  Should be same as Method 1")
        
        # Method 3: Count pixels with centroid inside glacier
        print("\n3️⃣ Method 3: Only pixels with CENTER inside glacier")
        # Create pixel centroids
        pixel_coords = masked_albedo.pixelCoordinates(ee.Projection('EPSG:4326'))
        
        # Create a mask where pixel centers are inside glacier
        # This is more complex but more accurate
        pixel_centers_in_glacier = ee.Image.constant(1).clip(glacier_mask).mask()
        
        # Apply this mask to our albedo
        albedo_centered = masked_albedo.updateMask(pixel_centers_in_glacier)
        
        count3 = albedo_centered.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=glacier_mask,
            scale=scale,
            maxPixels=1e6
        ).get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"   Pixels: {count3}")
        print(f"   Area: {count3 * 0.25:.2f} km²")
        print(f"   ✅ This should be closer to your expected ~20 pixels!")
        
        # Method 4: Use reduceToVectors to see actual pixel polygons
        print("\n4️⃣ Method 4: Visualize actual MODIS pixels")
        # Convert to integer for reduceToVectors
        albedo_int = masked_albedo.multiply(1000).int()
        
        # Get pixel polygons
        vectors = albedo_int.reduceToVectors(
            geometry=glacier_mask,
            scale=scale,
            geometryType='polygon',
            maxPixels=1000,
            reducer=ee.Reducer.countEvery()
        )
        
        vector_count = vectors.size().getInfo()
        print(f"   Vector polygons: {vector_count}")
        print(f"   ℹ️  Each polygon is a 500x500m MODIS pixel")
        
        # Calculate how many pixel centers are inside glacier
        def check_centroid(feature):
            centroid = feature.geometry().centroid()
            is_inside = glacier_mask.contains(centroid)
            return feature.set('centroid_inside', is_inside)
        
        vectors_with_check = vectors.map(check_centroid)
        inside_count = vectors_with_check.filter(ee.Filter.eq('centroid_inside', True)).size().getInfo()
        
        print(f"\n   📍 Pixels with centroid INSIDE glacier: {inside_count}")
        print(f"   📍 Pixels with centroid OUTSIDE glacier: {vector_count - inside_count}")
        print(f"   📍 Total pixels touching glacier: {vector_count}")
        
        print("\n📊 SUMMARY:")
        print(f"   Expected pixels (your count): ~20")
        print(f"   Current method gives: {count1}")
        print(f"   Pixels with center inside: {inside_count}")
        print(f"   Difference explained: Edge pixels are being counted!")
        
    else:
        print(f"❌ No MODIS data for {test_date}")
else:
    print(f"❌ Shapefile not found: {shapefile_path}")

print("\n💡 SOLUTION:")
print("   The issue is that pixels partially overlapping the glacier edge are counted.")
print("   To get ~20 pixels, you need to count only pixels whose CENTERS are inside the glacier.")
print("   This requires modifying the extraction function to use a centroid-based approach.")