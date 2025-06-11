#!/usr/bin/env python3
"""
Visualiseur simple des pixels MCD43A1 
Génère une table HTML interactive avec les valeurs de pixels
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

def create_pixel_table(data, band=6, sample_rate=20, output_file='pixels_table.html'):
    """
    Crée une table HTML interactive avec les pixels
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    bounds = data['bounds']
    transform = data['transform']
    
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
                    color_class = "snow"
                elif wsa > 0.5:
                    surface_type = "Sol clair"
                    color_class = "bright"
                elif wsa > 0.3:
                    surface_type = "Végétation"
                    color_class = "vegetation"
                elif wsa > 0.2:
                    surface_type = "Sol sombre"
                    color_class = "dark"
                else:
                    surface_type = "Très sombre"
                    color_class = "very-dark"
                
                pixels_data.append({
                    'row': i,
                    'col': j,
                    'lat': lat,
                    'lon': lon,
                    'f_iso': f_iso[i, j],
                    'f_vol': f_vol[i, j],
                    'f_geo': f_geo[i, j],
                    'bsa': bsa,
                    'wsa': wsa,
                    'surface_type': surface_type,
                    'color_class': color_class
                })
                
                if len(pixels_data) > 2000:  # Limiter pour performance
                    break
        if len(pixels_data) > 2000:
            break
    
    # Statistiques
    valid_pixels = np.sum(~np.isnan(f_iso))
    
    # Génerer le HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pixels MCD43A1 - Bande {band}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .controls {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .table-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #34495e;
            color: white;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .snow {{ background-color: #ffffff; }}
        .bright {{ background-color: #e3f2fd; }}
        .vegetation {{ background-color: #e8f5e8; }}
        .dark {{ background-color: #f3e5ab; }}
        .very-dark {{ background-color: #d7ccc8; }}
        
        .filter-input {{
            padding: 8px;
            margin: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .legend {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin: 10px 0;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #ccc;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Analyse des Pixels MCD43A1 - Bande {band}</h1>
        <p>Visualisation des paramètres BRDF et albédos calculés</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Informations générales</h3>
            <p><strong>Dimensions:</strong> {rows} × {cols} pixels</p>
            <p><strong>Pixels valides:</strong> {valid_pixels:,}</p>
            <p><strong>Pixels affichés:</strong> {len(pixels_data)}</p>
        </div>
        <div class="stat-card">
            <h3>Zone géographique</h3>
            <p><strong>Latitude:</strong> {bounds.bottom:.3f}° à {bounds.top:.3f}°</p>
            <p><strong>Longitude:</strong> {bounds.left:.3f}° à {bounds.right:.3f}°</p>
        </div>
        <div class="stat-card">
            <h3>Statistiques Albédo</h3>
            <p><strong>WSA moyen:</strong> {np.nanmean([p['wsa'] for p in pixels_data]):.3f}</p>
            <p><strong>BSA moyen:</strong> {np.nanmean([p['bsa'] for p in pixels_data]):.3f}</p>
        </div>
    </div>
    
    <div class="controls">
        <h3>Filtres</h3>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color snow"></div>
                <span>Neige/Glace (WSA > 0.7)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color bright"></div>
                <span>Sol clair (0.5-0.7)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color vegetation"></div>
                <span>Végétation (0.3-0.5)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color dark"></div>
                <span>Sol sombre (0.2-0.3)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color very-dark"></div>
                <span>Très sombre (< 0.2)</span>
            </div>
        </div>
        <input type="text" id="filterInput" class="filter-input" placeholder="Filtrer par type de surface..." onkeyup="filterTable()">
        <input type="number" id="wsaMin" class="filter-input" placeholder="WSA min" step="0.01" onchange="filterTable()">
        <input type="number" id="wsaMax" class="filter-input" placeholder="WSA max" step="0.01" onchange="filterTable()">
    </div>
    
    <div class="table-container">
        <table id="pixelTable">
            <thead>
                <tr>
                    <th>Pixel [i,j]</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                    <th>f_iso</th>
                    <th>f_vol</th>
                    <th>f_geo</th>
                    <th>BSA</th>
                    <th>WSA</th>
                    <th>Type de surface</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Ajouter les lignes de données
    for pixel in pixels_data:
        html_content += f"""
                <tr class="{pixel['color_class']}">
                    <td>[{pixel['row']}, {pixel['col']}]</td>
                    <td>{pixel['lat']:.6f}</td>
                    <td>{pixel['lon']:.6f}</td>
                    <td>{pixel['f_iso']:.4f}</td>
                    <td>{pixel['f_vol']:.4f}</td>
                    <td>{pixel['f_geo']:.4f}</td>
                    <td>{pixel['bsa']:.4f}</td>
                    <td>{pixel['wsa']:.4f}</td>
                    <td>{pixel['surface_type']}</td>
                </tr>
        """
    
    # Fermer le HTML et ajouter le JavaScript
    html_content += """
            </tbody>
        </table>
    </div>
    
    <script>
        function filterTable() {
            var input = document.getElementById("filterInput");
            var wsaMin = document.getElementById("wsaMin");
            var wsaMax = document.getElementById("wsaMax");
            var filter = input.value.toUpperCase();
            var table = document.getElementById("pixelTable");
            var tr = table.getElementsByTagName("tr");
            
            for (var i = 1; i < tr.length; i++) {
                var surfaceType = tr[i].getElementsByTagName("td")[8];
                var wsaCell = tr[i].getElementsByTagName("td")[7];
                
                if (surfaceType && wsaCell) {
                    var surfaceText = surfaceType.textContent || surfaceType.innerText;
                    var wsaValue = parseFloat(wsaCell.textContent || wsaCell.innerText);
                    
                    var showRow = true;
                    
                    // Filtre par texte
                    if (filter && surfaceText.toUpperCase().indexOf(filter) === -1) {
                        showRow = false;
                    }
                    
                    // Filtre par WSA min
                    if (wsaMin.value && wsaValue < parseFloat(wsaMin.value)) {
                        showRow = false;
                    }
                    
                    // Filtre par WSA max
                    if (wsaMax.value && wsaValue > parseFloat(wsaMax.value)) {
                        showRow = false;
                    }
                    
                    tr[i].style.display = showRow ? "" : "none";
                }
            }
        }
    </script>
</body>
</html>
    """
    
    # Sauvegarder le fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Table HTML sauvegardée: {output_file}")
    print(f"Pixels affichés: {len(pixels_data)}")
    
    return pixels_data

def main():
    parser = argparse.ArgumentParser(description='Table interactive des pixels MCD43A1')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--sample-rate', type=int, default=20, 
                       help='Échantillonner 1 pixel sur N (défaut: 20)')
    parser.add_argument('--output', default='pixels_table.html',
                       help='Fichier HTML de sortie')
    
    args = parser.parse_args()
    
    print(f"Extraction et reprojection de la bande {args.band}...")
    data = extract_and_reproject_band(args.input, args.band)
    
    print(f"Dimensions: {data['shape']}")
    print(f"Bounds: {data['bounds']}")
    print(f"Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    print(f"\nCréation de la table interactive...")
    create_pixel_table(data, args.band, args.sample_rate, args.output)
    
    print(f"\n✅ Table créée avec succès!")
    print(f"Ouvrez '{args.output}' dans votre navigateur")

if __name__ == "__main__":
    main()