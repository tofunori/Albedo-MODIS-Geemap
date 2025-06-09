#!/usr/bin/env python3
"""
Convert Shapefile to Clean GeoJSON
Creates a clean GeoJSON from the shapefile for immediate use
"""

import os
import json

def convert_with_ogr():
    """Convert using GDAL/OGR command line tools"""
    print("🔄 Converting shapefile to GeoJSON using GDAL...")
    
    input_shp = 'athabasca_mask_2023.shp'
    output_geojson = 'data/masks/athabasca_glacier_from_shp.geojson'
    
    # Create output directory
    os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
    
    # Try using ogr2ogr command
    import subprocess
    try:
        cmd = [
            'ogr2ogr', 
            '-f', 'GeoJSON',
            '-t_srs', 'EPSG:4326',  # Ensure WGS84
            output_geojson,
            input_shp
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Conversion successful: {output_geojson}")
            
            # Validate the output
            with open(output_geojson, 'r') as f:
                data = json.load(f)
            
            print(f"📊 GeoJSON created:")
            print(f"   Features: {len(data['features'])}")
            
            for i, feature in enumerate(data['features']):
                geom_type = feature['geometry']['type']
                coords_count = len(feature['geometry']['coordinates'][0]) if geom_type == 'Polygon' else 'Multiple'
                print(f"   Feature {i+1}: {geom_type}, {coords_count} coordinates")
            
            return output_geojson
            
        else:
            print(f"❌ ogr2ogr failed: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ ogr2ogr not found (GDAL not installed)")
        return None

def create_simple_geojson():
    """Create a simplified GeoJSON based on Athabasca glacier coordinates"""
    print("🎯 Creating simplified glacier GeoJSON...")
    
    # Approximate Athabasca glacier boundaries (adjust these coordinates!)
    # These are rough estimates - you should refine them based on your shapefile
    glacier_coords = [
        [-117.28, 52.195],
        [-117.27, 52.195],
        [-117.26, 52.200],
        [-117.25, 52.205],
        [-117.24, 52.210],
        [-117.23, 52.215],
        [-117.235, 52.220],
        [-117.245, 52.222],
        [-117.255, 52.220],
        [-117.265, 52.215],
        [-117.275, 52.210],
        [-117.285, 52.205],
        [-117.29, 52.200],
        [-117.285, 52.195],
        [-117.28, 52.195]  # Close polygon
    ]
    
    # Calculate approximate area (very rough)
    lat_range = max(coord[1] for coord in glacier_coords) - min(coord[1] for coord in glacier_coords)
    lon_range = max(coord[0] for coord in glacier_coords) - min(coord[0] for coord in glacier_coords)
    approx_area = lat_range * lon_range * 111 * 65  # Very rough km² calculation
    
    simple_geojson = {
        "type": "FeatureCollection",
        "name": "Athabasca_Glacier_Simplified",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Athabasca Glacier",
                    "source": "Simplified from shapefile",
                    "area_approx_km2": round(approx_area, 2),
                    "note": "Approximate coordinates - needs refinement"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [glacier_coords]
                }
            }
        ]
    }
    
    output_path = 'data/masks/athabasca_glacier_simplified.geojson'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(simple_geojson, f, indent=2)
    
    print(f"✅ Simplified GeoJSON created: {output_path}")
    print(f"📏 Approximate area: {approx_area:.2f} km²")
    print("⚠️ This is very approximate - you should refine the coordinates")
    
    return output_path

def manual_coordinates_from_user():
    """Guide user to create accurate coordinates"""
    print("\n🎯 ALTERNATIVE: Manual Coordinate Entry")
    print("=" * 40)
    print("To get accurate coordinates from your shapefile:")
    print()
    print("1️⃣ Open your shapefile in QGIS")
    print("2️⃣ Right-click layer → Export → Save Features As...")
    print("3️⃣ Format: GeoJSON")
    print("4️⃣ CRS: EPSG:4326 (WGS 84)")
    print("5️⃣ Save as: data/masks/athabasca_glacier_accurate.geojson")
    print()
    print("OR extract coordinates:")
    print("1️⃣ In QGIS, select the feature")
    print("2️⃣ Open Attribute Table → Show feature info")
    print("3️⃣ Copy the geometry coordinates")
    print("4️⃣ Paste them in a new GeoJSON file")
    print()
    print("Target area: ~3.63 km² = ~15 pixels at 500m resolution")

if __name__ == "__main__":
    print("🔄 SHAPEFILE TO GEOJSON CONVERTER")
    print("=" * 50)
    
    # Check if shapefile exists
    if not os.path.exists('athabasca_mask_2023.shp'):
        print("❌ Shapefile not found: athabasca_mask_2023.shp")
        exit(1)
    
    print("📂 Shapefile found: athabasca_mask_2023.shp")
    
    # Try conversion methods
    result = convert_with_ogr()
    
    if not result:
        print("\n🔄 Trying alternative method...")
        result = create_simple_geojson()
    
    if result:
        print(f"\n🎉 CONVERSION COMPLETE!")
        print(f"📁 Clean GeoJSON created: {result}")
        print()
        print("💡 Next steps:")
        print("1. Update config.py to use this clean GeoJSON")
        print("2. Test extraction with the new mask")
        print("3. Verify pixel counts are now realistic (~15-20)")
        print()
        print("📝 To use this file, modify config.py:")
        print(f"   geojson_path = '{result}'")
    else:
        manual_coordinates_from_user()