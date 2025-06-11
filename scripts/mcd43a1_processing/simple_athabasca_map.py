#!/usr/bin/env python3
"""
Carte simplifiée du glacier Athabasca
Évite les problèmes de PROJ en utilisant des coordonnées simples
"""

import numpy as np
import rasterio
import tempfile
import subprocess
import os
import json
from pathlib import Path
import argparse

def load_athabasca_coordinates():
    """
    Retourne les coordonnées étendues de la région d'Athabasca
    Zone élargie pour capturer plus de pixels
    """
    # Zone étendue autour du glacier Athabasca et Jasper
    # Centre: ~52.2°N, 117.2°W avec zone élargie
    athabasca_bounds = {
        'lat_min': 52.0,    # Sud (étendu)
        'lat_max': 52.5,    # Nord (étendu)
        'lon_min': -117.5,  # Ouest (étendu)
        'lon_max': -116.8   # Est (étendu)
    }
    
    print(f"Zone du glacier Athabasca:")
    print(f"  Latitude: {athabasca_bounds['lat_min']}° à {athabasca_bounds['lat_max']}°")
    print(f"  Longitude: {athabasca_bounds['lon_min']}° à {athabasca_bounds['lon_max']}°")
    
    return athabasca_bounds

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

def is_point_in_glacier(lat, lon, glacier_bounds):
    """
    Vérifie si un point est dans la zone du glacier
    """
    return (glacier_bounds['lat_min'] <= lat <= glacier_bounds['lat_max'] and
            glacier_bounds['lon_min'] <= lon <= glacier_bounds['lon_max'])

def filter_glacier_pixels(data, glacier_bounds):
    """
    Filtre les pixels pour ne garder que ceux dans la zone du glacier
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    transform = data['transform']
    
    glacier_pixels = []
    rows, cols = f_iso.shape
    
    print(f"Recherche de TOUS les pixels dans la zone étendue...")
    pixel_count = 0
    total_valid = 0
    
    for i in range(rows):
        for j in range(cols):
            if not np.isnan(f_iso[i, j]):
                total_valid += 1
                # Convertir indices pixel en coordonnées
                lon, lat = transform * (j, i)
                
                # Vérifier si le point est dans la zone étendue
                if is_point_in_glacier(lat, lon, glacier_bounds):
                    # Calculer les albédos
                    bsa, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                    
                    # Classification détaillée basée sur l'albédo
                    if wsa > 0.8:
                        surface_type = "Glace pure"
                        color = '#ffffff'
                    elif wsa > 0.6:
                        surface_type = "Neige/Glace"
                        color = '#f0f8ff'
                    elif wsa > 0.4:
                        surface_type = "Glace sale"
                        color = '#b0c4de'
                    elif wsa > 0.3:
                        surface_type = "Végétation dense"
                        color = '#228b22'
                    elif wsa > 0.2:
                        surface_type = "Roche/Sol nu"
                        color = '#8b7d6b'
                    elif wsa > 0.1:
                        surface_type = "Forêt/Végétation"
                        color = '#556b2f'
                    else:
                        surface_type = "Eau/Ombre"
                        color = '#191970'
                    
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
                    
                    if pixel_count % 100 == 0:
                        print(f"  Trouvé {pixel_count} pixels dans la zone...")
    
    print(f"✅ {len(glacier_pixels)} pixels trouvés dans la zone étendue")
    print(f"📊 Pixels valides dans l'image: {total_valid}")
    print(f"📈 Pourcentage de couverture: {(len(glacier_pixels)/total_valid)*100:.1f}%")
    return glacier_pixels

def create_athabasca_map(glacier_pixels, glacier_bounds, band=6, output_file='athabasca_simple.html'):
    """
    Crée une carte spécialisée pour le glacier Athabasca
    """
    if not glacier_pixels:
        print("❌ Aucun pixel trouvé dans la zone du glacier!")
        return
    
    # Calculer le centre du glacier
    center_lat = (glacier_bounds['lat_min'] + glacier_bounds['lat_max']) / 2
    center_lon = (glacier_bounds['lon_min'] + glacier_bounds['lon_max']) / 2
    
    # Statistiques
    wsas = [p['wsa'] for p in glacier_pixels]
    bsas = [p['bsa'] for p in glacier_pixels]
    
    # Créer le polygone du glacier pour affichage
    glacier_polygon = [
        [glacier_bounds['lat_min'], glacier_bounds['lon_min']],  # SW
        [glacier_bounds['lat_min'], glacier_bounds['lon_max']],  # SE
        [glacier_bounds['lat_max'], glacier_bounds['lon_max']],  # NE
        [glacier_bounds['lat_max'], glacier_bounds['lon_min']],  # NW
        [glacier_bounds['lat_min'], glacier_bounds['lon_min']]   # Fermer
    ]
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🏔️ Glacier Athabasca - Pixels MCD43A1 Bande {band}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
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
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            max-width: 320px;
            border-left: 5px solid #2196F3;
        }}
        .controls {{
            position: absolute;
            top: 10px;
            left: 60px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            border-left: 5px solid #4CAF50;
        }}
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            line-height: 22px;
            border-left: 5px solid #FF9800;
        }}
        .legend i {{
            width: 20px;
            height: 20px;
            float: left;
            margin-right: 10px;
            border: 1px solid #333;
            border-radius: 3px;
        }}
        select, input {{
            margin: 3px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-family: inherit;
        }}
        .stat {{
            margin: 8px 0;
            padding: 8px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 5px;
            border-left: 3px solid #007bff;
        }}
        button {{
            margin: 5px;
            padding: 8px 12px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-family: inherit;
        }}
        button:hover {{
            background: #0056b3;
        }}
        h3, h4 {{
            margin-top: 0;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="glacier-info">
        <h3>🏔️ Glacier Athabasca</h3>
        <div class="stat"><strong>📊 Pixels analysés:</strong> {len(glacier_pixels)}</div>
        <div class="stat"><strong>🌟 Albédo WSA moyen:</strong> {np.mean(wsas):.3f}</div>
        <div class="stat"><strong>🌞 Albédo BSA moyen:</strong> {np.mean(bsas):.3f}</div>
        <div class="stat"><strong>📈 WSA min-max:</strong> {min(wsas):.3f} - {max(wsas):.3f}</div>
        <div class="stat"><strong>📡 Bande MODIS:</strong> {band} (SWIR)</div>
        <div class="stat"><strong>🛰️ Produit:</strong> MCD43A1 BRDF</div>
        <div class="stat"><strong>📅 Date:</strong> 2025-05-25</div>
    </div>
    
    <div class="controls">
        <h4>🎛️ Contrôles de filtrage</h4>
        <select id="surfaceFilter" onchange="filterPixels()">
            <option value="">🌍 Tous les types</option>
            <option value="Glace pure">❄️ Glace pure</option>
            <option value="Neige/Glace">🏔️ Neige/Glace</option>
            <option value="Glace sale">🗻 Glace sale</option>
            <option value="Végétation dense">🌲 Végétation dense</option>
            <option value="Roche/Sol nu">🪨 Roche/Sol nu</option>
            <option value="Forêt/Végétation">🌲 Forêt/Végétation</option>
            <option value="Eau/Ombre">💧 Eau/Ombre</option>
        </select>
        <br>
        <label>🌟 WSA min: <input type="number" id="wsaMin" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <label>🌟 WSA max: <input type="number" id="wsaMax" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <button onclick="showAllPixels()">🌍 Tout afficher</button>
        <button onclick="showOnlyIce()">❄️ Glace seulement</button>
        <button onclick="showHighAlbedo()">✨ Albédo élevé</button>
    </div>
    
    <div class="legend">
        <h4>🎨 Classification des surfaces</h4>
        <i style="background: #ffffff;"></i> ❄️ Glace pure (WSA > 0.8)<br>
        <i style="background: #f0f8ff;"></i> 🏔️ Neige/Glace (0.6-0.8)<br>
        <i style="background: #b0c4de;"></i> 🗻 Glace sale (0.4-0.6)<br>
        <i style="background: #228b22;"></i> 🌲 Végétation dense (0.3-0.4)<br>
        <i style="background: #8b7d6b;"></i> 🪨 Roche/Sol nu (0.2-0.3)<br>
        <i style="background: #556b2f;"></i> 🌲 Forêt/Végétation (0.1-0.2)<br>
        <i style="background: #191970;"></i> 💧 Eau/Ombre (< 0.1)<br>
    </div>
    
    <div id="map"></div>

    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    
    <script>
        // Initialiser la carte centrée sur Athabasca avec zoom plus large
        var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
        
        // Ajouter les couches de base
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }}).addTo(map);
        
        var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }});
        
        var topoLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenTopoMap (CC-BY-SA)'
        }});
        
        // Contrôle des couches
        var baseMaps = {{
            "🛰️ Satellite (défaut)": satelliteLayer,
            "🗺️ OpenStreetMap": osmLayer,
            "🏔️ Topographique": topoLayer
        }};
        
        L.control.layers(baseMaps).addTo(map);
        
        // Ajouter le contour de la zone du glacier
        var glacierBounds = {json.dumps(glacier_polygon)};
        var glacierLayer = L.polygon(glacierBounds, {{
            color: '#ff0000',
            weight: 3,
            opacity: 0.8,
            fillOpacity: 0.1,
            fillColor: '#ff0000'
        }}).addTo(map);
        
        glacierLayer.bindPopup('<h4>🏔️ Zone du Glacier Athabasca</h4><p>Zone d\\'analyse approximative</p>');
        
        // Données des pixels du glacier
        var glacierPixels = {json.dumps(glacier_pixels, indent=8)};
        
        // Groupes de marqueurs pour filtrage
        var allMarkers = [];
        
        // Ajouter les pixels du glacier à la carte
        glacierPixels.forEach(function(pixel, index) {{
            var marker = L.circleMarker([pixel.lat, pixel.lon], {{
                radius: 6,
                fillColor: pixel.color,
                color: '#000',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.9
            }});
            
            // Popup détaillé pour chaque pixel du glacier
            var popupContent = `
                <div style="font-family: monospace; max-width: 280px; font-size: 12px;">
                    <h4 style="margin: 0 0 10px 0; color: #007bff;">🏔️ Pixel Glacier [${{pixel.row}}, ${{pixel.col}}]</h4>
                    
                    <div style="background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #007bff;">
                        <strong>📍 Position géographique:</strong><br>
                        <span style="color: #666;">Latitude:</span> ${{pixel.lat.toFixed(6)}}°<br>
                        <span style="color: #666;">Longitude:</span> ${{pixel.lon.toFixed(6)}}°
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 8px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #2196F3;">
                        <strong>🔬 Paramètres BRDF:</strong><br>
                        <span style="color: #666;">f_iso (isotropique):</span> ${{pixel.f_iso.toFixed(4)}}<br>
                        <span style="color: #666;">f_vol (volumétrique):</span> ${{pixel.f_vol.toFixed(4)}}<br>
                        <span style="color: #666;">f_geo (géométrique):</span> ${{pixel.f_geo.toFixed(4)}}
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 8px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #4CAF50;">
                        <strong>☀️ Albédos calculés:</strong><br>
                        <span style="color: #666;">BSA (Black-Sky):</span> ${{pixel.bsa.toFixed(4)}}<br>
                        <span style="color: #666;">WSA (White-Sky):</span> ${{pixel.wsa.toFixed(4)}}
                    </div>
                    
                    <div style="background: #fff3e0; padding: 8px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #FF9800;">
                        <strong>🏔️ Classification:</strong><br>
                        <span style="color: #666;">Type de surface:</span> ${{pixel.surface_type}}<br>
                        <span style="color: #666;">Réflectivité:</span> ${{(pixel.wsa * 100).toFixed(1)}}%
                    </div>
                </div>
            `;
            
            marker.bindPopup(popupContent, {{maxWidth: 300}});
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
        
        function showHighAlbedo() {{
            document.getElementById('surfaceFilter').value = '';
            document.getElementById('wsaMin').value = '0.8';
            document.getElementById('wsaMax').value = '1.0';
            filterPixels();
        }}
        
        // Ajuster la vue sur la zone du glacier
        map.fitBounds(glacierLayer.getBounds(), {{padding: [30, 30]}});
        
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
    parser = argparse.ArgumentParser(description='Carte simplifiée du glacier Athabasca')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--output', default='athabasca_simple.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print("🏔️ Analyse simplifiée du glacier Athabasca")
    print("=" * 50)
    
    # Charger les coordonnées du glacier
    print("📍 Définition de la zone du glacier...")
    glacier_bounds = load_athabasca_coordinates()
    
    # Extraire les données
    print(f"\n🔬 Extraction de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    print(f"✅ Dimensions: {data['shape']}")
    print(f"✅ Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    # Filtrer les pixels du glacier
    print(f"\n🎯 Filtrage des pixels dans la zone du glacier...")
    glacier_pixels = filter_glacier_pixels(data, glacier_bounds)
    
    if not glacier_pixels:
        print("❌ Aucun pixel trouvé dans la zone du glacier!")
        print("Le fichier MCD43A1 ne couvre peut-être pas la région d'Athabasca")
        return
    
    # Créer la carte spécialisée
    print(f"\n🗺️ Création de la carte interactive...")
    create_athabasca_map(glacier_pixels, glacier_bounds, args.band, args.output)
    
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
    
    print(f"\n🏔️ Répartition des types de surface glaciaire:")
    for surface_type, count in surface_types.items():
        percentage = (count / len(glacier_pixels)) * 100
        print(f"   • {surface_type}: {count} pixels ({percentage:.1f}%)")
    
    print(f"\n✅ Carte créée avec succès!")
    print(f"🌐 Ouvrez '{args.output}' dans votre navigateur")

if __name__ == "__main__":
    main()