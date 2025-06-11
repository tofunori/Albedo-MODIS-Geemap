#!/usr/bin/env python3
"""
Carte interactive des pixels MCD43A1 avec Folium
Affiche les valeurs BRDF et albédo pour chaque pixel sur une carte
"""

import numpy as np
import folium
from folium import plugins
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import tempfile
import subprocess
import os
import json
from pathlib import Path
import argparse
from pyproj import Transformer

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

def create_interactive_map(data, band=6, sample_rate=10, output_file='pixel_map.html'):
    """
    Crée une carte interactive avec les valeurs de pixels
    
    Args:
        data: Données extraites
        band: Numéro de bande
        sample_rate: Échantillonner 1 pixel sur N (pour réduire la taille)
        output_file: Fichier HTML de sortie
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    bounds = data['bounds']
    transform = data['transform']
    
    # Calculer le centre de la carte
    center_lat = (bounds.bottom + bounds.top) / 2
    center_lon = (bounds.left + bounds.right) / 2
    
    # Créer la carte
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Ajouter différentes couches de base
    folium.TileLayer(
        tiles='https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg',
        attr='Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors',
        name='Terrain',
        subdomains='abcd'
    ).add_to(m)
    
    folium.TileLayer(
        tiles='CartoDB positron',
        name='CartoDB Light',
        attr='© OpenStreetMap contributors © CARTO'
    ).add_to(m)
    
    # Créer des groupes de features
    param_group = folium.FeatureGroup(name='Paramètres BRDF')
    albedo_group = folium.FeatureGroup(name='Albédos')
    
    # Échantillonner les pixels pour éviter trop de marqueurs
    rows, cols = f_iso.shape
    pixel_count = 0
    
    for i in range(0, rows, sample_rate):
        for j in range(0, cols, sample_rate):
            if not np.isnan(f_iso[i, j]):
                # Convertir indices pixel en coordonnées
                lon, lat = transform * (j, i)
                
                # Calculer les albédos
                bsa, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                
                # Créer le popup avec toutes les infos
                popup_html = f"""
                <div style="font-family: monospace; width: 200px;">
                    <h4>Pixel [{i}, {j}]</h4>
                    <b>Coordonnées:</b><br>
                    Lat: {lat:.6f}<br>
                    Lon: {lon:.6f}<br>
                    <br>
                    <b>Paramètres BRDF:</b><br>
                    f_iso: {f_iso[i, j]:.4f}<br>
                    f_vol: {f_vol[i, j]:.4f}<br>
                    f_geo: {f_geo[i, j]:.4f}<br>
                    <br>
                    <b>Albédos calculés:</b><br>
                    BSA: {bsa:.4f}<br>
                    WSA: {wsa:.4f}<br>
                </div>
                """
                
                # Couleur basée sur WSA
                if wsa > 0.7:
                    color = 'white'  # Neige/glace
                elif wsa > 0.5:
                    color = 'lightblue'
                elif wsa > 0.3:
                    color = 'blue'
                elif wsa > 0.2:
                    color = 'darkblue'
                else:
                    color = 'black'
                
                # Ajouter le marqueur
                marker = folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    popup=folium.Popup(popup_html, max_width=250),
                    color=color,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=1
                )
                
                # Ajouter aux groupes appropriés
                marker.add_to(param_group)
                
                pixel_count += 1
                
                # Limiter le nombre de pixels pour performance
                if pixel_count > 5000:
                    print(f"Limite de 5000 pixels atteinte (échantillonnage 1/{sample_rate})")
                    break
        
        if pixel_count > 5000:
            break
    
    # Ajouter les groupes à la carte
    param_group.add_to(m)
    albedo_group.add_to(m)
    
    # Ajouter une heatmap pour WSA
    heat_data = []
    for i in range(0, rows, sample_rate*2):  # Échantillonnage plus grossier pour heatmap
        for j in range(0, cols, sample_rate*2):
            if not np.isnan(f_iso[i, j]):
                lon, lat = transform * (j, i)
                _, wsa = calculate_albedo(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                heat_data.append([lat, lon, float(wsa)])
    
    if heat_data:
        plugins.HeatMap(
            heat_data,
            name='Heatmap WSA',
            min_opacity=0.3,
            radius=15,
            blur=10,
            gradient={
                0.0: 'black',
                0.2: 'darkblue',
                0.4: 'blue',
                0.6: 'lightblue',
                0.8: 'white',
                1.0: 'white'
            }
        ).add_to(m)
    
    # Ajouter les contrôles
    folium.LayerControl().add_to(m)
    
    # Ajouter une échelle
    m.add_child(folium.LatLngPopup())
    
    # Ajouter la légende
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 150px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
        <p style="margin: 0; padding: 0;"><b>Albédo WSA</b></p>
        <p style="margin: 5px 0;">
            <span style="background-color: white; padding: 0 10px;">⬤</span> > 0.7 (Neige/Glace)<br>
            <span style="background-color: lightblue; padding: 0 10px;">⬤</span> 0.5 - 0.7<br>
            <span style="background-color: blue; padding: 0 10px;">⬤</span> 0.3 - 0.5<br>
            <span style="background-color: darkblue; padding: 0 10px;">⬤</span> 0.2 - 0.3<br>
            <span style="background-color: black; color: white; padding: 0 10px;">⬤</span> < 0.2<br>
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Statistiques
    valid_pixels = np.sum(~np.isnan(f_iso))
    stats_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 250px;
                background-color: white; z-index:9999; font-size:12px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
        <b>MCD43A1 Bande {band}</b><br>
        Pixels totaux: {rows * cols:,}<br>
        Pixels valides: {valid_pixels:,}<br>
        Pixels affichés: {pixel_count}<br>
        Échantillonnage: 1/{sample_rate}<br>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(stats_html))
    
    # Sauvegarder la carte
    m.save(output_file)
    print(f"Carte sauvegardée: {output_file}")
    print(f"Pixels affichés: {pixel_count}")
    
    return m

def main():
    parser = argparse.ArgumentParser(description='Carte interactive des pixels MCD43A1')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--sample-rate', type=int, default=10, 
                       help='Échantillonner 1 pixel sur N (défaut: 10)')
    parser.add_argument('--output', default='mcd43a1_pixel_map.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print(f"Extraction et reprojection de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    
    print(f"Dimensions: {data['shape']}")
    print(f"Bounds: {data['bounds']}")
    print(f"Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    print(f"\nCréation de la carte interactive...")
    create_interactive_map(data, args.band, args.sample_rate, args.output)
    
    print(f"\n✅ Carte créée avec succès!")
    print(f"Ouvrez '{args.output}' dans votre navigateur")

if __name__ == "__main__":
    main()