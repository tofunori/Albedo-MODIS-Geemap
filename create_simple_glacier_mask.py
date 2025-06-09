#!/usr/bin/env python3
"""
Create a simplified glacier mask using known coordinates
Based on approximate glacier boundaries
"""

import json
import os

def create_simple_mask():
    """Create a simplified rectangular glacier mask"""
    print("🎯 Création d'un masque glacier simplifié")
    print("=" * 40)
    
    # Approximate Athabasca Glacier bounds (you can adjust these)
    # Based on known location: 52.2°N, 117.2°W
    glacier_bounds = [
        [-117.28, 52.19],  # Southwest
        [-117.22, 52.19],  # Southeast  
        [-117.22, 52.22],  # Northeast
        [-117.28, 52.22],  # Northwest
        [-117.28, 52.19]   # Close polygon
    ]
    
    # Calculate approximate area
    # Rough calculation for this lat/lon box
    lat_diff = 52.22 - 52.19  # 0.03 degrees
    lon_diff = 117.28 - 117.22  # 0.06 degrees
    
    # At this latitude, 1 degree ≈ 111 km lat, ≈ 65 km lon
    approx_area = (lat_diff * 111) * (lon_diff * 65)  # km²
    
    simple_data = {
        "type": "FeatureCollection",
        "name": "Athabasca_glacier_simple",
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
                    "name": "Athabasca Glacier - Simplified",
                    "area_km2_approx": round(approx_area, 2),
                    "method": "Simplified rectangular bounds",
                    "note": "Adjust coordinates for precise boundaries"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [glacier_bounds]
                }
            }
        ]
    }
    
    # Save simplified version
    output_path = 'data/masks/Athabasca_glacier_simple.geojson'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(simple_data, f, indent=2)
    
    print(f"✅ Masque simplifié créé: {output_path}")
    print(f"   Type: Polygon simple")
    print(f"   Surface approximative: {approx_area:.2f} km²")
    print(f"   Coordonnées: {len(glacier_bounds)} points")
    
    print(f"\n📋 Coordonnées du masque:")
    for i, coord in enumerate(glacier_bounds):
        print(f"   Point {i+1}: {coord[0]:.3f}, {coord[1]:.3f}")
    
    return output_path

if __name__ == "__main__":
    result = create_simple_mask()
    if result:
        print("\n🎉 MASQUE SIMPLIFIÉ CRÉÉ!")
        print("💡 Ce masque est très approximatif")
        print("🎯 Recommandations:")
        print("   1. Ouvrez dans QGIS pour ajuster les coordonnées")
        print("   2. Digitalisez le vrai contour du glacier")
        print("   3. Visez une surface de ~3.63 km²")
        print("   4. Exportez en shapefile pour plus de précision")