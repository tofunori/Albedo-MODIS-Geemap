#!/usr/bin/env python3
"""
Carte interactive spécialisée pour le glacier Athabasca
Affiche TOUS les pixels MCD43A1 à l'intérieur du masque du glacier
"""

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import geopandas as gpd
import tempfile
import subprocess
import os
import json
from pathlib import Path
import argparse
from shapely.geometry import Point

def load_athabasca_mask():
    """
    Charge le masque du glacier Athabasca
    """
    # Chemins possibles pour le masque
    mask_paths = [
        "/mnt/d/UQTR/Maitrîse/Code/Albedo MODIS Geemap/data/geospatial/masks/athabasca_accurate_mask.geojson",
        "/mnt/d/UQTR/Maitrîse/Code/Albedo MODIS Geemap/data/geospatial/masks/athabasca_conservative_mask.geojson",
        "/mnt/d/UQTR/Maitrîse/Code/Albedo MODIS Geemap/data/geospatial/masks/athabasca_simplified_mask.geojson",
        "../../data/geospatial/masks/athabasca_accurate_mask.geojson",
        "../../data/geospatial/masks/athabasca_conservative_mask.geojson"
    ]
    
    for mask_path in mask_paths:
        if os.path.exists(mask_path):
            print(f"Utilisation du masque: {mask_path}")
            return gpd.read_file(mask_path)
    
    # Si aucun masque trouvé, créer un masque approximatif basé sur les coordonnées connues
    print("⚠️ Aucun masque trouvé, création d'un masque approximatif pour Athabasca")
    
    # Coordonnées approximatives du glacier Athabasca
    # Centre: ~52.2°N, 117.2°W
    athabasca_coords = [
        [-117.25, 52.15],  # Sud-Ouest
        [-117.25, 52.25],  # Nord-Ouest  
        [-117.15, 52.25],  # Nord-Est
        [-117.15, 52.15],  # Sud-Est
        [-117.25, 52.15]   # Fermer le polygone
    ]
    
    from shapely.geometry import Polygon
    import pandas as pd
    
    polygon = Polygon(athabasca_coords)
    gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs="EPSG:4326")
    
    return gdf

def extract_and_reproject_band(hdf_file, band=6):
    """
    Extrait et reprojette les données en WGS84
    """
    # Extraire avec gdal_translate
    cmd_info = ['gdalinfo', str(hdf_file)]
    result = subprocess.run(cmd_info, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise ValueError(f"Impossible de lire {hdf_file}")
    
    # Trouver le subdataset
    lines = result.stdout.split('\n')
    subdataset_name = None
    
    for line in lines:
        if f'BRDF_Albedo_Parameters_Band{band}' in line and 'SUBDATASET' in line and '_NAME=' in line:
            subdataset_name = line.split('=', 1)[1].strip()
            break
    
    if not subdataset_name:
        raise ValueError(f"Pas de subdataset trouvé pour la bande {band}")
    
    # Créer fichiers temporaires
    temp_dir = tempfile.mkdtemp()
    temp_tif = os.path.join(temp_dir, f'band{band}_params.tif')
    temp_wgs84 = os.path.join(temp_dir, f'band{band}_wgs84.tif')
    
    # Extraire le subdataset
    cmd_translate = ['gdal_translate', '-of', 'GTiff', subdataset_name, temp_tif]
    subprocess.run(cmd_translate, capture_output=True, check=True)
    
    # Reprojeter en WGS84
    cmd_warp = ['gdalwarp', '-t_srs', 'EPSG:4326', '-r', 'near', temp_tif, temp_wgs84]
    subprocess.run(cmd_warp, capture_output=True, check=True)
    
    # Lire les données reprojetées
    with rasterio.open(temp_wgs84) as src:
        f_iso = src.read(1)
        f_vol = src.read(2)
        f_geo = src.read(3)
        
        # Obtenir les bounds et la transformation
        bounds = src.bounds
        transform = src.transform
        
    # Nettoyer
    import shutil
    shutil.rmtree(temp_dir)
    
    # Appliquer le facteur d'échelle
    scale_factor = 0.001
    f_iso = np.where(f_iso == 32767, np.nan, f_iso * scale_factor)
    f_vol = np.where(f_vol == 32767, np.nan, f_vol * scale_factor)
    f_geo = np.where(f_geo == 32767, np.nan, f_geo * scale_factor)
    
    return {
        'f_iso': f_iso,
        'f_vol': f_vol,
        'f_geo': f_geo,
        'bounds': bounds,
        'transform': transform,
        'shape': f_iso.shape
    }

def calculate_albedo(f_iso, f_vol, f_geo):
    """Calcule BSA et WSA"""
    wsa = f_iso + 0.189 * f_vol + 1.377 * f_geo
    bsa = f_iso  # Simplifié pour angle solaire = 0
    return bsa, wsa

def filter_glacier_pixels(data, glacier_mask):
    """
    Filtre les pixels pour ne garder que ceux dans le glacier
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    transform = data['transform']
    
    glacier_pixels = []
    rows, cols = f_iso.shape
    
    # Obtenir la géométrie du glacier
    glacier_geom = glacier_mask.geometry.iloc[0]
    
    print(f"Recherche des pixels dans le glacier...")
    pixel_count = 0
    
    for i in range(rows):
        for j in range(cols):
            if not np.isnan(f_iso[i, j]):
                # Convertir indices pixel en coordonnées
                lon, lat = transform * (j, i)
                
                # Créer un point et vérifier s'il est dans le glacier
                point = Point(lon, lat)
                
                if glacier_geom.contains(point):
                    # Calculer les albédos
                    bsa, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                    
                    # Déterminer le type de surface
                    if wsa > 0.8:
                        surface_type = "Glace pure"
                        color = '#ffffff'
                    elif wsa > 0.6:
                        surface_type = "Neige/Glace"
                        color = '#f0f8ff'
                    elif wsa > 0.4:
                        surface_type = "Glace sale"
                        color = '#b0c4de'
                    elif wsa > 0.2:
                        surface_type = "Roche/Débris"
                        color = '#8b7d6b'
                    else:
                        surface_type = "Débris sombres"
                        color = '#556b2f'
                    
                    glacier_pixels.append({
                        'lat': lat,
                        'lon': lon,
                        'f_iso': f_iso[i, j],
                        'f_vol': f_vol[i, j],
                        'f_geo': f_geo[i, j],
                        'bsa': bsa,
                        'wsa': wsa,
                        'surface_type': surface_type,
                        'color': color,
                        'row': i,
                        'col': j
                    })
                    
                    pixel_count += 1
                    
                    if pixel_count % 10 == 0:
                        print(f"  Trouvé {pixel_count} pixels du glacier...")
    
    print(f"✅ {len(glacier_pixels)} pixels trouvés dans le glacier Athabasca")
    return glacier_pixels

def create_athabasca_map(glacier_pixels, glacier_mask, band=6, output_file='athabasca_glacier.html'):
    """
    Crée une carte spécialisée pour le glacier Athabasca
    """
    if not glacier_pixels:
        print("❌ Aucun pixel trouvé dans le glacier!")
        return
    
    # Calculer le centre du glacier
    lats = [p['lat'] for p in glacier_pixels]
    lons = [p['lon'] for p in glacier_pixels]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # Obtenir les bounds du glacier
    glacier_bounds = glacier_mask.bounds
    
    # Statistiques
    wsas = [p['wsa'] for p in glacier_pixels]
    bsas = [p['bsa'] for p in glacier_pixels]
    
    # Convertir le masque en GeoJSON pour affichage
    glacier_geojson = glacier_mask.to_json()
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Glacier Athabasca - Pixels MCD43A1 Bande {band}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        #map {{
            height: 100vh;
            width: 100%;
        }}
        .glacier-info {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            max-width: 300px;
        }}
        .controls {{
            position: absolute;
            top: 10px;
            left: 60px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            line-height: 20px;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            border: 1px solid #000;
        }}
        select, input {{
            margin: 3px;
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }}
        .stat {{
            margin: 5px 0;
            padding: 5px;
            background: #f8f9fa;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="glacier-info">
        <h3>🏔️ Glacier Athabasca</h3>
        <div class="stat"><strong>Pixels analysés:</strong> {len(glacier_pixels)}</div>
        <div class="stat"><strong>Albédo WSA moyen:</strong> {np.mean(wsas):.3f}</div>
        <div class="stat"><strong>Albédo BSA moyen:</strong> {np.mean(bsas):.3f}</div>
        <div class="stat"><strong>WSA min-max:</strong> {min(wsas):.3f} - {max(wsas):.3f}</div>
        <div class="stat"><strong>Bande MODIS:</strong> {band}</div>
        <div class="stat"><strong>Produit:</strong> MCD43A1 BRDF</div>
    </div>
    
    <div class="controls">
        <h4>🎛️ Filtres</h4>
        <select id="surfaceFilter" onchange="filterPixels()">
            <option value="">Tous les types</option>
            <option value="Glace pure">Glace pure</option>
            <option value="Neige/Glace">Neige/Glace</option>
            <option value="Glace sale">Glace sale</option>
            <option value="Roche/Débris">Roche/Débris</option>
            <option value="Débris sombres">Débris sombres</option>
        </select>
        <br>
        <label>WSA min: <input type="number" id="wsaMin" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <label>WSA max: <input type="number" id="wsaMax" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <button onclick="showAllPixels()">Tout afficher</button>
        <button onclick="showOnlyIce()">Glace seulement</button>
    </div>
    
    <div class="legend">
        <h4>🎨 Types de surface</h4>
        <i style="background: #ffffff;"></i> Glace pure (WSA > 0.8)<br>
        <i style="background: #f0f8ff;"></i> Neige/Glace (0.6-0.8)<br>
        <i style="background: #b0c4de;"></i> Glace sale (0.4-0.6)<br>
        <i style="background: #8b7d6b;"></i> Roche/Débris (0.2-0.4)<br>
        <i style="background: #556b2f;"></i> Débris sombres (< 0.2)<br>
    </div>
    
    <div id="map"></div>

    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    
    <script>
        // Initialiser la carte centrée sur Athabasca
        var map = L.map('map').setView([{center_lat}, {center_lon}], 13);
        
        // Ajouter les couches de base
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Tiles © Esri'
        }}).addTo(map);
        
        var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }});
        
        var terrainLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenTopoMap contributors'
        }});
        
        // Contrôle des couches
        var baseMaps = {{
            "Satellite (défaut)": satelliteLayer,
            "OpenStreetMap": osmLayer,
            "Terrain": terrainLayer
        }};
        
        L.control.layers(baseMaps).addTo(map);
        
        // Ajouter le contour du glacier
        var glacierMask = {glacier_geojson};
        var glacierLayer = L.geoJSON(glacierMask, {{
            style: {{
                color: '#ff0000',
                weight: 3,
                opacity: 0.8,
                fillOpacity: 0.1,
                fillColor: '#ff0000'
            }}
        }}).addTo(map);
        
        glacierLayer.bindPopup('<h4>🏔️ Contour du Glacier Athabasca</h4>');
        
        // Données des pixels du glacier
        var glacierPixels = {json.dumps(glacier_pixels, indent=8)};
        
        // Groupes de marqueurs pour filtrage
        var allMarkers = [];
        
        // Ajouter les pixels du glacier à la carte
        glacierPixels.forEach(function(pixel) {{
            var marker = L.circleMarker([pixel.lat, pixel.lon], {{
                radius: 5,
                fillColor: pixel.color,
                color: '#000',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.9
            }});
            
            // Popup détaillé pour chaque pixel du glacier
            var popupContent = `
                <div style="font-family: monospace; max-width: 250px;">
                    <h4>🏔️ Pixel Glacier [${{pixel.row}}, ${{pixel.col}}]</h4>
                    
                    <div style="background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 4px;">
                        <strong>📍 Position:</strong><br>
                        Lat: ${{pixel.lat.toFixed(6)}}°<br>
                        Lon: ${{pixel.lon.toFixed(6)}}°
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 8px; margin: 5px 0; border-radius: 4px;">
                        <strong>🔬 Paramètres BRDF:</strong><br>
                        f_iso: ${{pixel.f_iso.toFixed(4)}}<br>
                        f_vol: ${{pixel.f_vol.toFixed(4)}}<br>
                        f_geo: ${{pixel.f_geo.toFixed(4)}}
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 8px; margin: 5px 0; border-radius: 4px;">
                        <strong>☀️ Albédos:</strong><br>
                        BSA: ${{pixel.bsa.toFixed(4)}}<br>
                        WSA: ${{pixel.wsa.toFixed(4)}}
                    </div>
                    
                    <div style="background: #fff3e0; padding: 8px; margin: 5px 0; border-radius: 4px;">
                        <strong>🏔️ Type:</strong> ${{pixel.surface_type}}
                    </div>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            marker.addTo(map);
            
            // Stocker les données pour le filtrage
            marker.pixelData = pixel;
            allMarkers.push(marker);
        }});
        
        // Fonctions de filtrage
        function filterPixels() {{
            var surfaceFilter = document.getElementById('surfaceFilter').value;
            var wsaMin = parseFloat(document.getElementById('wsaMin').value) || 0;
            var wsaMax = parseFloat(document.getElementById('wsaMax').value) || 1;
            
            var visibleCount = 0;
            
            allMarkers.forEach(function(marker) {{
                var pixel = marker.pixelData;
                var show = true;
                
                // Filtre par type de surface
                if (surfaceFilter && pixel.surface_type !== surfaceFilter) {{
                    show = false;
                }}
                
                // Filtre par WSA
                if (pixel.wsa < wsaMin || pixel.wsa > wsaMax) {{
                    show = false;
                }}
                
                // Afficher/masquer le marqueur
                if (show) {{
                    marker.addTo(map);
                    visibleCount++;
                }} else {{
                    map.removeLayer(marker);
                }}
            }});
            
            console.log(`Pixels visibles: ${{visibleCount}}/${{allMarkers.length}}`);
        }}
        
        function showAllPixels() {{
            document.getElementById('surfaceFilter').value = '';
            document.getElementById('wsaMin').value = '';
            document.getElementById('wsaMax').value = '';
            filterPixels();
        }}
        
        function showOnlyIce() {{
            document.getElementById('surfaceFilter').value = '';
            document.getElementById('wsaMin').value = '0.6';
            document.getElementById('wsaMax').value = '1.0';
            filterPixels();
        }}
        
        // Ajuster la vue sur le glacier
        map.fitBounds(glacierLayer.getBounds(), {{padding: [20, 20]}});
        
    </script>
</body>
</html>
    """
    
    # Sauvegarder le fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Carte du glacier Athabasca sauvegardée: {output_file}")
    print(f"🏔️ {len(glacier_pixels)} pixels du glacier affichés")
    
    return glacier_pixels

def main():
    parser = argparse.ArgumentParser(description='Carte spécialisée du glacier Athabasca')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--output', default='athabasca_glacier.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print("🏔️ Analyse spécialisée du glacier Athabasca")
    print("=" * 50)
    
    # Charger le masque du glacier
    print("📍 Chargement du masque du glacier...")
    glacier_mask = load_athabasca_mask()
    print(f"✅ Masque chargé: {len(glacier_mask)} polygone(s)")
    
    # Extraire les données
    print(f"\n🔬 Extraction de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    print(f"✅ Dimensions: {data['shape']}")
    print(f"✅ Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    # Filtrer les pixels du glacier
    print(f"\n🎯 Filtrage des pixels du glacier...")
    glacier_pixels = filter_glacier_pixels(data, glacier_mask)
    
    if not glacier_pixels:
        print("❌ Aucun pixel trouvé dans le glacier!")
        print("Vérifiez que le fichier MCD43A1 couvre bien la région d'Athabasca")
        return
    
    # Créer la carte spécialisée
    print(f"\n🗺️ Création de la carte interactive...")
    create_athabasca_map(glacier_pixels, glacier_mask, args.band, args.output)
    
    # Statistiques finales
    wsas = [p['wsa'] for p in glacier_pixels]
    print(f"\n📊 Statistiques du glacier Athabasca:")
    print(f"   • Pixels analysés: {len(glacier_pixels)}")
    print(f"   • Albédo WSA moyen: {np.mean(wsas):.3f}")
    print(f"   • Albédo WSA médian: {np.median(wsas):.3f}")
    print(f"   • Plage WSA: {min(wsas):.3f} - {max(wsas):.3f}")
    
    # Répartition par type de surface
    surface_types = {}
    for pixel in glacier_pixels:
        surface_type = pixel['surface_type']
        surface_types[surface_type] = surface_types.get(surface_type, 0) + 1
    
    print(f"\n🏔️ Répartition des types de surface:")
    for surface_type, count in surface_types.items():
        percentage = (count / len(glacier_pixels)) * 100
        print(f"   • {surface_type}: {count} pixels ({percentage:.1f}%)")
    
    print(f"\n✅ Carte créée avec succès!")
    print(f"🌐 Ouvrez '{args.output}' dans votre navigateur")

if __name__ == "__main__":
    main()