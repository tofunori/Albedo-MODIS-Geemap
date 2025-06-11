#!/usr/bin/env python3
"""
Carte avec TOUS les pixels MODIS en grille 500m x 500m
Affiche la grille complète sans filtrage géographique
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

def is_in_columbia_icefield_region(lat, lon):
    """
    Vérifie si un point est dans la région du Columbia Icefield
    Zone élargie incluant Athabasca, Saskatchewan, Columbia glaciers
    """
    # Coordonnées du Columbia Icefield et environs
    # Centre approximatif: 52.2°N, 117.2°W
    # Zone élargie pour inclure tous les glaciers de la région
    return (51.9 <= lat <= 52.6 and  # Latitude: ~70km Nord-Sud
            -117.8 <= lon <= -116.5)  # Longitude: ~130km Est-Ouest

def create_full_pixel_grid(data, band=6, sample_rate=1):
    """
    Crée la grille complète de TOUS les pixels dans la région Columbia Icefield
    sample_rate=1 signifie tous les pixels, =2 signifie 1 pixel sur 2, etc.
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    transform = data['transform']
    
    all_pixels = []
    rows, cols = f_iso.shape
    
    print(f"Recherche des pixels dans la région Columbia Icefield...")
    print(f"Zone ciblée: 51.9°-52.6°N, 117.8°-116.5°W")
    print(f"Dimensions image: {rows} x {cols} pixels")
    print(f"Échantillonnage: 1 pixel sur {sample_rate}")
    
    pixel_count = 0
    valid_count = 0
    region_count = 0
    
    for i in range(0, rows, sample_rate):
        for j in range(0, cols, sample_rate):
            # Convertir indices pixel en coordonnées
            lon, lat = transform * (j, i)
            
            # Vérifier si le pixel est dans la région Columbia Icefield
            if is_in_columbia_icefield_region(lat, lon):
                region_count += 1
                
                # Traiter TOUS les pixels de la région (valides et invalides)
                if not np.isnan(f_iso[i, j]):
                    valid_count += 1
                    # Calculer les albédos
                    bsa, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                    
                    # Couleur basée directement sur la valeur WSA (0.0 à 1.0)
                    # Gradient: bleu foncé (0) → vert → jaune → blanc (1)
                    if wsa >= 0.8:
                        color = '#ffffff'  # Blanc
                    elif wsa >= 0.6:
                        color = '#f0f8ff'  # Blanc cassé
                    elif wsa >= 0.4:
                        color = '#add8e6'  # Bleu clair
                    elif wsa >= 0.2:
                        color = '#90ee90'  # Vert clair
                    else:
                        color = '#4169e1'  # Bleu royal
                    
                    # Pas de classification artificielle - juste les valeurs mesurées
                    surface_type = f"WSA: {wsa:.3f}"
                    
                    all_pixels.append({
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
                        'col': j,
                        'valid': True
                    })
                else:
                    # Pixel invalide dans la région (nuages, erreur de mesure, etc.)
                    all_pixels.append({
                        'lat': lat,
                        'lon': lon,
                        'f_iso': np.nan,
                        'f_vol': np.nan,
                        'f_geo': np.nan,
                        'bsa': np.nan,
                        'wsa': np.nan,
                        'surface_type': "Pas de données",
                        'color': '#ff0000',
                        'row': i,
                        'col': j,
                        'valid': False
                    })
                
                pixel_count += 1
                
                if pixel_count % 100 == 0:
                    print(f"  Trouvé {pixel_count} pixels dans la région...")
    
    print(f"✅ Grille Columbia Icefield créée:")
    print(f"   • Pixels dans la région: {region_count}")
    print(f"   • Pixels valides: {valid_count}")
    print(f"   • Pixels invalides: {region_count - valid_count}")
    print(f"   • Pourcentage de données: {(valid_count/region_count*100):.1f}%")
    
    return all_pixels

def create_full_grid_map(all_pixels, data, band=6, output_file='full_grid.html'):
    """
    Crée une carte avec TOUS les pixels en grille
    """
    bounds = data['bounds']
    center_lat = (bounds.bottom + bounds.top) / 2
    center_lon = (bounds.left + bounds.right) / 2
    
    # Statistiques
    valid_pixels = [p for p in all_pixels if p['valid']]
    invalid_pixels = [p for p in all_pixels if not p['valid']]
    
    if valid_pixels:
        wsas = [p['wsa'] for p in valid_pixels]
        bsas = [p['bsa'] for p in valid_pixels]
        wsa_mean = np.mean(wsas)
        wsa_std = np.std(wsas)
    else:
        wsas = []
        bsas = []
        wsa_mean = 0
        wsa_std = 0
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🏔️ Columbia Icefield - Grille MODIS MCD43A1 - Bande {band}</title>
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
        .info-panel {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            max-width: 350px;
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
        .grid-info {{
            background: #e8f4fd;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border-left: 3px solid #2196F3;
        }}
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>🏔️ Columbia Icefield</h3>
        <div class="grid-info">
            <strong>🔢 Résolution:</strong> 500m x 500m<br>
            <strong>📐 Dimensions:</strong> {data['shape'][0]} x {data['shape'][1]}<br>
            <strong>🌍 Système:</strong> WGS84 (EPSG:4326)
        </div>
        <div class="stat"><strong>📊 Total pixels:</strong> {len(all_pixels):,}</div>
        <div class="stat"><strong>✅ Pixels valides:</strong> {len(valid_pixels):,}</div>
        <div class="stat"><strong>❌ Pixels invalides:</strong> {len(invalid_pixels):,}</div>
        <div class="stat"><strong>📈 Couverture:</strong> {(len(valid_pixels)/len(all_pixels)*100):.1f}%</div>
        {f'<div class="stat"><strong>🌟 WSA moyen:</strong> {wsa_mean:.3f} ± {wsa_std:.3f}</div>' if valid_pixels else ''}
        <div class="stat"><strong>📡 Bande:</strong> {band} (SWIR 1.6μm)</div>
        <div class="stat"><strong>🛰️ Produit:</strong> MCD43A1 BRDF</div>
        
        <div class="grid-info">
            <strong>🏔️ Columbia Icefield Region:</strong><br>
            Lat: 51.9° à 52.6° N<br>
            Lon: 117.8° à 116.5° W<br>
            <strong>🧊 Glaciers inclus:</strong><br>
            • Athabasca Glacier<br>
            • Saskatchewan Glacier<br>
            • Columbia Glacier<br>
            • Castleguard Glacier
        </div>
    </div>
    
    <div class="controls">
        <h4>🎛️ Contrôles de visualisation</h4>
        <label>
            <input type="checkbox" id="showValid" checked onchange="togglePixels()"> 
            ✅ Pixels valides ({len(valid_pixels):,})
        </label><br>
        <label>
            <input type="checkbox" id="showInvalid" onchange="togglePixels()"> 
            ❌ Pixels invalides ({len(invalid_pixels):,})
        </label><br>
        
        <label>📊 Filtrer par valeur WSA:</label>
        <br>
        <label>🌟 WSA min: <input type="number" id="wsaMin" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <label>🌟 WSA max: <input type="number" id="wsaMax" step="0.01" min="0" max="1" onchange="filterPixels()"></label>
        <br>
        <button onclick="showAll()">🌍 Tout afficher</button>
        <button onclick="showOnlyValid()">✅ Valides seulement</button>
        <button onclick="showHighAlbedo()">✨ Albédo élevé</button>
    </div>
    
    <div class="legend">
        <h4>📊 Échelle WSA (Albédo)</h4>
        <i style="background: #ffffff;"></i> 0.8 - 1.0 (Très réfléchissant)<br>
        <i style="background: #f0f8ff;"></i> 0.6 - 0.8 (Réfléchissant)<br>
        <i style="background: #add8e6;"></i> 0.4 - 0.6 (Modérément réfléchissant)<br>
        <i style="background: #90ee90;"></i> 0.2 - 0.4 (Peu réfléchissant)<br>
        <i style="background: #4169e1;"></i> 0.0 - 0.2 (Très peu réfléchissant)<br>
        <i style="background: #ff0000;"></i> ❌ Pas de données<br>
    </div>
    
    <div id="map"></div>

    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    
    <script>
        // Initialiser la carte centrée sur Columbia Icefield
        var map = L.map('map').setView([52.25, -117.15], 11);
        
        // Couches de base
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: 'Tiles © Esri'
        }}).addTo(map);
        
        var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }});
        
        var topoLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenTopoMap'
        }});
        
        L.control.layers({{
            "🛰️ Satellite": satelliteLayer,
            "🗺️ OpenStreetMap": osmLayer,
            "🏔️ Topographique": topoLayer
        }}).addTo(map);
        
        // Données de TOUS les pixels
        var allPixelsData = {json.dumps(all_pixels[:5000] if len(all_pixels) > 5000 else all_pixels, indent=8)};
        console.log(`Chargé ${{allPixelsData.length}} pixels`);
        
        // Groupes de marqueurs
        var validMarkers = [];
        var invalidMarkers = [];
        
        // Créer les marqueurs pour tous les pixels
        allPixelsData.forEach(function(pixel, index) {{
            var markerOptions = {{
                radius: 3,
                fillColor: pixel.color,
                color: '#000',
                weight: 0.5,
                opacity: 0.8,
                fillOpacity: 0.8
            }};
            
            var marker = L.circleMarker([pixel.lat, pixel.lon], markerOptions);
            
            // Popup détaillé
            var popupContent = `
                <div style="font-family: monospace; max-width: 300px; font-size: 12px;">
                    <h4>🗺️ Pixel MODIS [${{pixel.row}}, ${{pixel.col}}]</h4>
                    
                    <div style="background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 5px;">
                        <strong>📍 Coordonnées:</strong><br>
                        Lat: ${{pixel.lat.toFixed(6)}}°<br>
                        Lon: ${{pixel.lon.toFixed(6)}}°<br>
                        <strong>🔢 Grille:</strong> Ligne ${{pixel.row}}, Colonne ${{pixel.col}}
                    </div>
            `;
            
            if (pixel.valid) {{
                popupContent += `
                    <div style="background: #e3f2fd; padding: 8px; margin: 5px 0; border-radius: 5px;">
                        <strong>🔬 Paramètres BRDF:</strong><br>
                        f_iso: ${{pixel.f_iso.toFixed(4)}}<br>
                        f_vol: ${{pixel.f_vol.toFixed(4)}}<br>
                        f_geo: ${{pixel.f_geo.toFixed(4)}}
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 8px; margin: 5px 0; border-radius: 5px;">
                        <strong>☀️ Albédos:</strong><br>
                        BSA: ${{pixel.bsa.toFixed(4)}}<br>
                        WSA: ${{pixel.wsa.toFixed(4)}}<br>
                        Réflectivité: ${{(pixel.wsa * 100).toFixed(1)}}%
                    </div>
                    
                    <div style="background: #fff3e0; padding: 8px; margin: 5px 0; border-radius: 5px;">
                        <strong>📊 Mesure:</strong> ${{pixel.surface_type}}
                    </div>
                `;
            }} else {{
                popupContent += `
                    <div style="background: #ffebee; padding: 8px; margin: 5px 0; border-radius: 5px; border-left: 3px solid #f44336;">
                        <strong>❌ Pixel invalide</strong><br>
                        Raisons possibles: nuages, eau, ombre, erreur de mesure
                    </div>
                `;
            }}
            
            popupContent += `</div>`;
            
            marker.bindPopup(popupContent, {{maxWidth: 320}});
            marker.pixelData = pixel;
            
            // Séparer valides et invalides
            if (pixel.valid) {{
                validMarkers.push(marker);
                marker.addTo(map);
            }} else {{
                invalidMarkers.push(marker);
            }}
        }});
        
        // Fonctions de contrôle
        function togglePixels() {{
            var showValid = document.getElementById('showValid').checked;
            var showInvalid = document.getElementById('showInvalid').checked;
            
            validMarkers.forEach(function(marker) {{
                if (showValid) {{
                    marker.addTo(map);
                }} else {{
                    map.removeLayer(marker);
                }}
            }});
            
            invalidMarkers.forEach(function(marker) {{
                if (showInvalid) {{
                    marker.addTo(map);
                }} else {{
                    map.removeLayer(marker);
                }}
            }});
        }}
        
        function filterPixels() {{
            var wsaMin = parseFloat(document.getElementById('wsaMin').value) || 0;
            var wsaMax = parseFloat(document.getElementById('wsaMax').value) || 1;
            var showValid = document.getElementById('showValid').checked;
            var showInvalid = document.getElementById('showInvalid').checked;
            
            var visibleCount = 0;
            
            // Filtrer les pixels valides
            if (showValid) {{
                validMarkers.forEach(function(marker) {{
                    var pixel = marker.pixelData;
                    var show = true;
                    
                    if (pixel.wsa < wsaMin || pixel.wsa > wsaMax) {{
                        show = false;
                    }}
                    
                    if (show) {{
                        marker.addTo(map);
                        visibleCount++;
                    }} else {{
                        map.removeLayer(marker);
                    }}
                }});
            }}
            
            // Filtrer les pixels invalides
            if (showInvalid) {{
                invalidMarkers.forEach(function(marker) {{
                    var pixel = marker.pixelData;
                    var show = true;
                    
                    if (show) {{
                        marker.addTo(map);
                        visibleCount++;
                    }} else {{
                        map.removeLayer(marker);
                    }}
                }});
            }}
            
            console.log(`Pixels visibles: ${{visibleCount}}`);
        }}
        
        function showAll() {{
            document.getElementById('showValid').checked = true;
            document.getElementById('showInvalid').checked = true;
            document.getElementById('wsaMin').value = '';
            document.getElementById('wsaMax').value = '';
            togglePixels();
        }}
        
        function showOnlyValid() {{
            document.getElementById('showValid').checked = true;
            document.getElementById('showInvalid').checked = false;
            togglePixels();
        }}
        
        function showHighAlbedo() {{
            document.getElementById('showValid').checked = true;
            document.getElementById('showInvalid').checked = false;
            document.getElementById('wsaMin').value = '0.6';
            document.getElementById('wsaMax').value = '1.0';
            filterPixels();
        }}
        
    </script>
</body>
</html>
    """
    
    # Sauvegarder
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Carte de grille complète sauvegardée: {output_file}")
    print(f"🗺️ {len(all_pixels)} pixels au total affichés")
    
    return all_pixels

def main():
    parser = argparse.ArgumentParser(description='Grille complète des pixels MODIS')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--sample-rate', type=int, default=1, 
                       help='Échantillonnage: 1=tous les pixels, 2=1 sur 2, etc.')
    parser.add_argument('--output', default='full_grid.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print("🏔️ Grille Columbia Icefield - MODIS MCD43A1")
    print("=" * 50)
    
    # Extraire les données
    print(f"🔬 Extraction de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    print(f"✅ Dimensions originales: {data['shape']}")
    print(f"✅ Zone couverte: {data['bounds']}")
    
    # Créer la grille complète
    print(f"\n🎯 Création de la grille complète...")
    all_pixels = create_full_pixel_grid(data, args.band, args.sample_rate)
    
    # Créer la carte
    print(f"\n🗺️ Génération de la carte interactive...")
    create_full_grid_map(all_pixels, data, args.band, args.output)
    
    print(f"\n✅ Grille complète créée avec succès!")
    print(f"🌐 Ouvrez '{args.output}' dans votre navigateur")
    print(f"\n📊 Résumé:")
    print(f"   • Résolution: 500m x 500m par pixel")
    print(f"   • Grille: {data['shape'][0]} x {data['shape'][1]} pixels")
    print(f"   • Total affiché: {len(all_pixels)} pixels")
    print(f"   • Échantillonnage: 1 pixel sur {args.sample_rate}")

if __name__ == "__main__":
    main()