#!/usr/bin/env python3
"""
Test Shapefile Integration
Validates that the shapefile is correctly loaded and provides realistic pixel counts
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

print("🧪 Testing Shapefile Integration")
print("=" * 50)

# Test shapefile loading
print("📂 Checking shapefile availability...")
shapefile_path = os.path.join(project_root, 'athabasca_mask_2023.shp')

if os.path.exists(shapefile_path):
    print(f"✅ Shapefile found: {shapefile_path}")
    
    # Test with geopandas if available
    try:
        import geopandas as gpd
        print("✅ geopandas available")
        
        # Read shapefile
        gdf = gpd.read_file(shapefile_path)
        print(f"📊 Shapefile loaded: {len(gdf)} features")
        print(f"   CRS: {gdf.crs}")
        print(f"   Columns: {list(gdf.columns)}")
        
        # Calculate area
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf_wgs84 = gdf.to_crs(4326)
        else:
            gdf_wgs84 = gdf
            
        # Area calculation in UTM (more accurate)
        # Use UTM zone 11N for Alberta, Canada
        gdf_utm = gdf_wgs84.to_crs('EPSG:32611')  # UTM Zone 11N
        areas_m2 = gdf_utm.geometry.area
        total_area_km2 = areas_m2.sum() / 1e6
        
        print(f"📏 Surface analysis:")
        print(f"   Total area: {total_area_km2:.2f} km²")
        print(f"   Expected ~3.63 km² (from documentation)")
        
        if 2.0 <= total_area_km2 <= 6.0:
            print(f"   ✅ REALISTIC: Area within expected range")
        else:
            print(f"   ⚠️ WARNING: Area outside expected range")
            
        # Estimate pixel count at 500m resolution
        pixels_500m = total_area_km2 / 0.25  # 500m pixel = 0.25 km²
        print(f"📊 Estimated pixel count at 500m: {pixels_500m:.0f} pixels")
        
        if 10 <= pixels_500m <= 25:
            print(f"   ✅ REALISTIC: Pixel count matches your manual count of ~20")
        else:
            print(f"   ⚠️ WARNING: Pixel count differs from manual count")
            
        # Show geometry type
        geom_types = gdf.geometry.type.value_counts()
        print(f"🗺️ Geometry types: {dict(geom_types)}")
        
        # Show bounds
        bounds = gdf_wgs84.total_bounds  # [minx, miny, maxx, maxy]
        print(f"📍 Bounding box:")
        print(f"   West: {bounds[0]:.6f}°")
        print(f"   South: {bounds[1]:.6f}°") 
        print(f"   East: {bounds[2]:.6f}°")
        print(f"   North: {bounds[3]:.6f}°")
        
    except ImportError:
        print("❌ geopandas not installed")
        print("💡 Install with: pip install geopandas")
        
else:
    print(f"❌ Shapefile not found: {shapefile_path}")
    print("💡 Make sure the shapefile is in the project root")

# Test config loading
print(f"\n🔧 Testing config loading...")
try:
    import ee
    ee.Initialize()
    print("✅ Earth Engine initialized")
    
    # Import config (this will load the shapefile)
    from config import athabasca_roi
    print("✅ Config loaded successfully")
    print("✅ athabasca_roi created")
    
    # Test a simple Earth Engine operation
    roi_area = athabasca_roi.area().getInfo()  # Area in square meters
    roi_area_km2 = roi_area / 1e6
    print(f"📏 Earth Engine ROI area: {roi_area_km2:.2f} km²")
    
except Exception as e:
    print(f"❌ Config loading failed: {e}")

print(f"\n🎯 SUMMARY:")
print("If you see realistic values above (area ~3.63 km², pixels ~15), your shapefile is ready!")
print("The pixel counts in your extractions should now be much closer to your manual count of ~20.")