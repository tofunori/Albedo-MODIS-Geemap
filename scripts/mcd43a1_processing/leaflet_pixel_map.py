#!/usr/bin/env python3
"""
Carte interactive des pixels MCD43A1 avec Leaflet
Version simple et robuste qui évite les problèmes de Folium
"""

import numpy as np
import rasterio
import tempfile
import subprocess
import os
import json
from pathlib import Path
import argparse

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

def get_pixel_color(wsa):
    """Retourne la couleur en fonction de l'albédo WSA"""
    if wsa > 0.7:
        return '#ffffff'  # Blanc - Neige/Glace
    elif wsa > 0.5:
        return '#87ceeb'  # Bleu clair
    elif wsa > 0.3:
        return '#90ee90'  # Vert clair - Végétation
    elif wsa > 0.2:
        return '#f0e68c'  # Jaune - Sol sombre
    else:
        return '#8b4513'  # Marron - Très sombre

def create_leaflet_map(data, band=6, sample_rate=15, output_file='leaflet_map.html'):
    """
    Crée une carte Leaflet avec les pixels
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    bounds = data['bounds']
    transform = data['transform']
    
    # Calculer le centre de la carte
    center_lat = (bounds.bottom + bounds.top) / 2
    center_lon = (bounds.left + bounds.right) / 2
    
    # Échantillonner les pixels
    rows, cols = f_iso.shape
    pixels_data = []
    
    for i in range(0, rows, sample_rate):
        for j in range(0, cols, sample_rate):
            if not np.isnan(f_iso[i, j]):
                # Convertir indices pixel en coordonnées
                lon, lat = transform * (j, i)
                
                # Calculer les albédos
                bsa, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                
                # Déterminer le type de surface
                if wsa > 0.7:
                    surface_type = "Neige/Glace"
                elif wsa > 0.5:
                    surface_type = "Sol clair"
                elif wsa > 0.3:
                    surface_type = "Végétation"
                elif wsa > 0.2:
                    surface_type = "Sol sombre"
                else:
                    surface_type = "Très sombre"
                
                pixels_data.append({
                    'lat': lat,
                    'lon': lon,
                    'f_iso': f_iso[i, j],
                    'f_vol': f_vol[i, j],
                    'f_geo': f_geo[i, j],
                    'bsa': bsa,
                    'wsa': wsa,
                    'surface_type': surface_type,
                    'color': get_pixel_color(wsa),
                    'row': i,
                    'col': j
                })
                
                if len(pixels_data) > 3000:  # Limiter pour performance
                    break
        if len(pixels_data) > 3000:
            break
    
    # Statistiques
    valid_pixels = np.sum(~np.isnan(f_iso))
    
    # Générer le HTML avec Leaflet
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Carte des Pixels MCD43A1 - Bande {band}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        #map {{
            height: 100vh;
            width: 100%;
        }}
        .info {{
            padding: 6px 8px;
            font: 14px/16px Arial, Helvetica, sans-serif;
            background: white;
            background: rgba(255,255,255,0.9);
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            border-radius: 5px;
            max-width: 200px;
        }}
        .legend {{
            background: white;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            line-height: 18px;
            color: #555;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.8;
        }}
        .controls {{
            position: absolute;
            top: 10px;
            left: 60px;
            z-index: 1000;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
        }}
        select, input {{
            margin: 5px;
            padding: 5px;
        }}
    </style>
</head>
<body>
    <div class="controls">
        <h4>Filtres</h4>
        <select id="surfaceFilter" onchange="filterPixels()">
            <option value="">Tous les types</option>
            <option value="Neige/Glace">Neige/Glace</option>
            <option value="Sol clair">Sol clair</option>
            <option value="Végétation">Végétation</option>
            <option value="Sol sombre">Sol sombre</option>
            <option value="Très sombre">Très sombre</option>
        </select>
        <br>
        <label>WSA min: <input type="number" id="wsaMin" step="0.1" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <label>WSA max: <input type="number" id="wsaMax" step="0.1" min="0" max="1" onchange="filterPixels()"></label>
    </div>
    
    <div id="map"></div>

    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    
    <script>
        // Initialiser la carte
        var map = L.map('map').setView([{center_lat}, {center_lon}], 8);
        
        // Ajouter les couches de base
        var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Tiles © Esri'
        }});
        
        var terrainLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenTopoMap contributors'
        }});
        
        // Contrôle des couches
        var baseMaps = {{
            "OpenStreetMap": osmLayer,
            "Satellite": satelliteLayer,
            "Terrain": terrainLayer
        }};
        
        L.control.layers(baseMaps).addTo(map);
        
        // Données des pixels
        var pixelsData = {json.dumps(pixels_data, indent=8)};
        
        // Groupes de marqueurs pour filtrage
        var allMarkers = [];
        
        // Ajouter les pixels à la carte
        pixelsData.forEach(function(pixel) {{
            var marker = L.circleMarker([pixel.lat, pixel.lon], {{
                radius: 4,
                fillColor: pixel.color,
                color: '#000',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.8
            }});
            
            // Popup avec informations du pixel
            var popupContent = `
                <div style="font-family: monospace;">
                    <h4>Pixel [${{pixel.row}}, ${{pixel.col}}]</h4>
                    <b>Position:</b><br>
                    Lat: ${{pixel.lat.toFixed(6)}}<br>
                    Lon: ${{pixel.lon.toFixed(6)}}<br><br>
                    
                    <b>Paramètres BRDF:</b><br>
                    f_iso: ${{pixel.f_iso.toFixed(4)}}<br>
                    f_vol: ${{pixel.f_vol.toFixed(4)}}<br>
                    f_geo: ${{pixel.f_geo.toFixed(4)}}<br><br>
                    
                    <b>Albédos:</b><br>
                    BSA: ${{pixel.bsa.toFixed(4)}}<br>
                    WSA: ${{pixel.wsa.toFixed(4)}}<br><br>
                    
                    <b>Type:</b> ${{pixel.surface_type}}
                </div>
            `;
            
            marker.bindPopup(popupContent);
            marker.addTo(map);
            
            // Stocker les données pour le filtrage
            marker.pixelData = pixel;
            allMarkers.push(marker);
        }});
        
        // Fonction de filtrage
        function filterPixels() {{
            var surfaceFilter = document.getElementById('surfaceFilter').value;
            var wsaMin = parseFloat(document.getElementById('wsaMin').value) || 0;
            var wsaMax = parseFloat(document.getElementById('wsaMax').value) || 1;
            
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
                }} else {{
                    map.removeLayer(marker);
                }}
            }});
        }}
        
        // Ajouter une légende
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = `
                <h4>Albédo WSA</h4>
                <i style="background: #ffffff; border: 1px solid #000;"></i> > 0.7 Neige/Glace<br>
                <i style="background: #87ceeb;"></i> 0.5 - 0.7 Sol clair<br>
                <i style="background: #90ee90;"></i> 0.3 - 0.5 Végétation<br>
                <i style="background: #f0e68c;"></i> 0.2 - 0.3 Sol sombre<br>
                <i style="background: #8b4513;"></i> < 0.2 Très sombre<br>
            `;
            return div;
        }};
        legend.addTo(map);
        
        // Ajouter les statistiques
        var info = L.control({{position: 'bottomleft'}});
        info.onAdd = function(map) {{
            var div = L.DomUtil.create('div', 'info');
            div.innerHTML = `
                <h4>MCD43A1 Bande {band}</h4>
                <b>Dimensions:</b> {rows} × {cols}<br>
                <b>Pixels valides:</b> {valid_pixels:,}<br>
                <b>Pixels affichés:</b> {len(pixels_data)}<br>
                <b>Échantillonnage:</b> 1/{sample_rate}
            `;
            return div;
        }};
        info.addTo(map);
        
    </script>
</body>
</html>
    """
    
    # Sauvegarder le fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Carte Leaflet sauvegardée: {output_file}")
    print(f"Pixels affichés: {len(pixels_data)}")
    
    return pixels_data

def main():
    parser = argparse.ArgumentParser(description='Carte Leaflet des pixels MCD43A1')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--sample-rate', type=int, default=15, 
                       help='Échantillonner 1 pixel sur N (défaut: 15)')
    parser.add_argument('--output', default='carte_leaflet.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print(f"Extraction et reprojection de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    
    print(f"Dimensions: {data['shape']}")
    print(f"Bounds: {data['bounds']}")
    print(f"Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    print(f"\nCréation de la carte Leaflet...")
    create_leaflet_map(data, args.band, args.sample_rate, args.output)
    
    print(f"\n✅ Carte créée avec succès!")
    print(f"Ouvrez '{args.output}' dans votre navigateur")

if __name__ == "__main__":
    main()