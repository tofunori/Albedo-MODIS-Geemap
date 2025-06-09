#!/usr/bin/env python3
"""
Create a clean glacier mask from the existing GeoJSON
Removes artifacts and keeps only the main glacier polygon
"""

import json
import os

def create_clean_mask():
    """Create a clean GeoJSON with only the main glacier"""
    print("🧹 Nettoyage du masque glacier")
    print("=" * 40)
    
    # Load existing GeoJSON
    input_path = 'Athabasca_mask_2023_cut.geojson'
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    print(f"📂 Lecture: {input_path}")
    print(f"   Features originales: {len(data['features'])}")
    
    # Find main feature (largest count)
    main_feature = None
    max_count = 0
    
    for feature in data['features']:
        count = feature['properties'].get('count', 0)
        print(f"   Feature: count={count}, type={feature['geometry']['type']}")
        
        if count > max_count and feature['geometry']['coordinates']:
            max_count = count
            main_feature = feature
    
    if not main_feature:
        print("❌ Aucune feature principale trouvée")
        return
    
    print(f"\n🎯 Feature principale sélectionnée:")
    print(f"   Count: {max_count}")
    print(f"   Type: {main_feature['geometry']['type']}")
    print(f"   Surface théorique: {max_count * 0.25 / 1000:.2f} km²")
    
    # Create clean GeoJSON with only main feature
    clean_data = {
        "type": "FeatureCollection",
        "name": "Athabasca_glacier_clean",
        "crs": data['crs'],
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Athabasca Glacier",
                    "area_km2": round(max_count * 0.25 / 1000, 2),
                    "pixel_count": max_count,
                    "source": "Cleaned from original mask",
                    "notes": "Main glacier polygon only, artifacts removed"
                },
                "geometry": main_feature['geometry']
            }
        ]
    }
    
    # Save clean version
    output_path = 'data/masks/Athabasca_glacier_clean.geojson'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(clean_data, f, indent=2)
    
    print(f"\n✅ Masque nettoyé créé: {output_path}")
    print(f"   Features: 1 (feature principale seulement)")
    print(f"   Surface estimée: {clean_data['features'][0]['properties']['area_km2']} km²")
    
    # Create simple coordinates version for manual verification
    coords_file = 'data/masks/glacier_coordinates.txt'
    with open(coords_file, 'w') as f:
        f.write(f"Athabasca Glacier Coordinates\n")
        f.write(f"Surface estimée: {clean_data['features'][0]['properties']['area_km2']} km²\n")
        f.write(f"Pixel count: {max_count}\n\n")
        
        geom = main_feature['geometry']
        if geom['type'] == 'MultiPolygon':
            for i, polygon in enumerate(geom['coordinates']):
                if polygon:
                    f.write(f"Polygon {i+1}:\n")
                    for ring in polygon:
                        f.write(f"  Ring with {len(ring)} points\n")
                        # Show first few coordinates
                        for j, coord in enumerate(ring[:3]):
                            f.write(f"    Point {j+1}: {coord[0]:.6f}, {coord[1]:.6f}\n")
                        if len(ring) > 3:
                            f.write(f"    ... {len(ring)-3} more points\n")
                    f.write("\n")
    
    print(f"📝 Coordonnées exportées: {coords_file}")
    
    return output_path

if __name__ == "__main__":
    result = create_clean_mask()
    if result:
        print("\n🎉 NETTOYAGE TERMINÉ!")
        print("💡 Prochaines étapes:")
        print("   1. Vérifiez le fichier créé dans data/masks/")
        print("   2. Ouvrez-le dans QGIS pour validation visuelle")
        print("   3. Si satisfaisant, modifiez config.py pour l'utiliser")
        print("   4. Ou créez un shapefile propre dans QGIS")
    else:
        print("\n❌ NETTOYAGE ÉCHOUÉ")