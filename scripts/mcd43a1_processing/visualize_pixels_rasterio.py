#!/usr/bin/env python3
"""
Visualiseur de pixels MCD43A1 utilisant rasterio (alternative à GDAL)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import argparse
import json
import subprocess
import tempfile
import os

def extract_subdataset_with_gdal_translate(hdf_file, band=6):
    """
    Utilise gdal_translate pour extraire un subdataset en GeoTIFF temporaire
    """
    # D'abord, obtenir la liste des subdatasets
    cmd_info = ['gdalinfo', str(hdf_file)]
    result = subprocess.run(cmd_info, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise ValueError(f"Impossible de lire {hdf_file}")
    
    # Parser la sortie pour trouver le subdataset de la bande
    lines = result.stdout.split('\n')
    subdataset_name = None
    
    for line in lines:
        if f'BRDF_Albedo_Parameters_Band{band}' in line and 'SUBDATASET' in line and '_NAME=' in line:
            # Extraire le nom du subdataset
            subdataset_name = line.split('=', 1)[1].strip()
            break
    
    if not subdataset_name:
        raise ValueError(f"Pas de subdataset trouvé pour la bande {band}")
    
    # Créer un fichier temporaire pour stocker l'extraction
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, f'band{band}_params.tif')
    
    # Utiliser gdal_translate pour extraire le subdataset
    cmd_translate = [
        'gdal_translate',
        '-of', 'GTiff',
        subdataset_name,
        temp_file
    ]
    
    print(f"Extraction du subdataset avec gdal_translate...")
    result = subprocess.run(cmd_translate, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise ValueError(f"Erreur gdal_translate: {result.stderr}")
    
    return temp_file, temp_dir

def read_geotiff_params(tif_file):
    """
    Lit les paramètres BRDF depuis le GeoTIFF extrait
    """
    import rasterio
    
    with rasterio.open(tif_file) as src:
        # Les 3 bandes contiennent f_iso, f_vol, f_geo
        f_iso = src.read(1)
        f_vol = src.read(2) 
        f_geo = src.read(3)
        
        # Métadonnées
        transform = src.transform
        crs = src.crs
        shape = f_iso.shape
    
    # Facteur d'échelle et masquage
    scale_factor = 0.001
    f_iso = np.where(f_iso == 32767, np.nan, f_iso * scale_factor)
    f_vol = np.where(f_vol == 32767, np.nan, f_vol * scale_factor)
    f_geo = np.where(f_geo == 32767, np.nan, f_geo * scale_factor)
    
    return {
        'f_iso': f_iso,
        'f_vol': f_vol,
        'f_geo': f_geo,
        'transform': transform,
        'crs': crs,
        'shape': shape
    }

def calculate_albedo_pixel(f_iso, f_vol, f_geo, solar_zenith=0.0):
    """
    Calcule BSA et WSA pour un pixel
    """
    # White-Sky Albedo
    wsa = f_iso + 0.189 * f_vol + 1.377 * f_geo
    
    # Black-Sky Albedo (simplifié pour angle zénithal 0)
    if solar_zenith == 0.0:
        bsa = f_iso
    else:
        # Calcul plus complexe pour autres angles
        bsa = f_iso  # Simplification
    
    return bsa, wsa

def visualize_pixel_grid(data, band=6, zoom_region=None):
    """
    Visualise chaque pixel dans une grille avec ses valeurs
    """
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    
    # Région à visualiser
    if zoom_region:
        row_start, row_end, col_start, col_end = zoom_region
    else:
        # Prendre une petite région au centre (10x10 pixels)
        center_row, center_col = f_iso.shape[0] // 2, f_iso.shape[1] // 2
        row_start = max(0, center_row - 5)
        row_end = min(f_iso.shape[0], center_row + 5)
        col_start = max(0, center_col - 5)
        col_end = min(f_iso.shape[1], center_col + 5)
    
    # Extraire la région
    region_iso = f_iso[row_start:row_end, col_start:col_end]
    region_vol = f_vol[row_start:row_end, col_start:col_end]
    region_geo = f_geo[row_start:row_end, col_start:col_end]
    
    nrows, ncols = region_iso.shape
    
    # Calculer BSA et WSA pour chaque pixel
    bsa_grid = np.zeros_like(region_iso)
    wsa_grid = np.zeros_like(region_iso)
    
    for i in range(nrows):
        for j in range(ncols):
            if not np.isnan(region_iso[i, j]):
                bsa_grid[i, j], wsa_grid[i, j] = calculate_albedo_pixel(
                    region_iso[i, j], region_vol[i, j], region_geo[i, j]
                )
            else:
                bsa_grid[i, j] = np.nan
                wsa_grid[i, j] = np.nan
    
    # Créer la figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    fig.suptitle(f'MCD43A1 - Analyse Pixel par Pixel - Bande {band}', fontsize=16)
    
    # 1. Paramètres BRDF
    ax1 = axes[0, 0]
    ax1.set_title('Paramètres BRDF par Pixel')
    ax1.axis('off')
    
    # Tableau des valeurs
    for i in range(nrows):
        for j in range(ncols):
            if not np.isnan(region_iso[i, j]):
                text = f'[{row_start+i},{col_start+j}]\n'
                text += f'f_iso: {region_iso[i, j]:.3f}\n'
                text += f'f_vol: {region_vol[i, j]:.3f}\n'
                text += f'f_geo: {region_geo[i, j]:.3f}'
                
                # Dessiner le pixel
                rect = patches.Rectangle((j*100, (nrows-i-1)*80), 95, 75, 
                                       linewidth=1, edgecolor='black', 
                                       facecolor='lightblue')
                ax1.add_patch(rect)
                ax1.text(j*100 + 47.5, (nrows-i-1)*80 + 37.5, text, 
                        ha='center', va='center', fontsize=8)
    
    ax1.set_xlim(0, ncols*100)
    ax1.set_ylim(0, nrows*80)
    
    # 2. WSA (White-Sky Albedo)
    ax2 = axes[0, 1]
    im2 = ax2.imshow(wsa_grid, cmap='viridis', vmin=0, vmax=1)
    ax2.set_title('White-Sky Albedo (WSA)')
    plt.colorbar(im2, ax=ax2, label='Albédo')
    
    # Ajouter les valeurs sur chaque pixel
    for i in range(nrows):
        for j in range(ncols):
            if not np.isnan(wsa_grid[i, j]):
                ax2.text(j, i, f'{wsa_grid[i, j]:.3f}', 
                        ha='center', va='center', 
                        color='white' if wsa_grid[i, j] < 0.5 else 'black',
                        fontsize=10)
    
    # 3. BSA (Black-Sky Albedo)
    ax3 = axes[1, 0]
    im3 = ax3.imshow(bsa_grid, cmap='viridis', vmin=0, vmax=1)
    ax3.set_title('Black-Sky Albedo (BSA)')
    plt.colorbar(im3, ax=ax3, label='Albédo')
    
    # Ajouter les valeurs sur chaque pixel
    for i in range(nrows):
        for j in range(ncols):
            if not np.isnan(bsa_grid[i, j]):
                ax3.text(j, i, f'{bsa_grid[i, j]:.3f}', 
                        ha='center', va='center',
                        color='white' if bsa_grid[i, j] < 0.5 else 'black',
                        fontsize=10)
    
    # 4. Statistiques
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Calculer les statistiques
    valid_pixels = np.sum(~np.isnan(region_iso))
    stats_text = f"Statistiques de la région [{row_start}:{row_end}, {col_start}:{col_end}]\n\n"
    stats_text += f"Pixels valides: {valid_pixels}/{nrows*ncols}\n\n"
    
    if valid_pixels > 0:
        stats_text += "Paramètres BRDF:\n"
        stats_text += f"  f_iso: {np.nanmean(region_iso):.3f} ± {np.nanstd(region_iso):.3f}\n"
        stats_text += f"  f_vol: {np.nanmean(region_vol):.3f} ± {np.nanstd(region_vol):.3f}\n"
        stats_text += f"  f_geo: {np.nanmean(region_geo):.3f} ± {np.nanstd(region_geo):.3f}\n\n"
        stats_text += "Albédos calculés:\n"
        stats_text += f"  WSA: {np.nanmean(wsa_grid):.3f} ± {np.nanstd(wsa_grid):.3f}\n"
        stats_text += f"  BSA: {np.nanmean(bsa_grid):.3f} ± {np.nanstd(bsa_grid):.3f}\n"
    
    ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=12, 
             verticalalignment='center', family='monospace')
    
    plt.tight_layout()
    return fig

def create_pixel_report(hdf_file, band=6, output_json=None):
    """
    Crée un rapport JSON avec les valeurs de chaque pixel
    """
    # Extraire en GeoTIFF temporaire
    temp_file, temp_dir = extract_subdataset_with_gdal_translate(hdf_file, band)
    
    try:
        # Lire les données
        data = read_geotiff_params(temp_file)
        
        f_iso = data['f_iso']
        f_vol = data['f_vol']
        f_geo = data['f_geo']
        
        pixel_data = []
        
        # Parcourir tous les pixels (limiter pour éviter fichiers trop gros)
        max_pixels = 10000  # Limite pour éviter JSON énorme
        pixel_count = 0
        
        for i in range(f_iso.shape[0]):
            for j in range(f_iso.shape[1]):
                if not np.isnan(f_iso[i, j]):
                    bsa, wsa = calculate_albedo_pixel(f_iso[i, j], f_vol[i, j], f_geo[i, j])
                    
                    pixel_info = {
                        'row': int(i),
                        'col': int(j),
                        'f_iso': float(f_iso[i, j]),
                        'f_vol': float(f_vol[i, j]),
                        'f_geo': float(f_geo[i, j]),
                        'bsa': float(bsa),
                        'wsa': float(wsa)
                    }
                    pixel_data.append(pixel_info)
                    
                    pixel_count += 1
                    if pixel_count >= max_pixels:
                        print(f"Limite de {max_pixels} pixels atteinte")
                        break
            if pixel_count >= max_pixels:
                break
        
        report = {
            'file': str(hdf_file),
            'band': band,
            'shape': list(f_iso.shape),
            'total_pixels': int(f_iso.shape[0] * f_iso.shape[1]),
            'valid_pixels': int(np.sum(~np.isnan(f_iso))),
            'pixels_in_report': len(pixel_data),
            'pixels': pixel_data
        }
        
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Rapport sauvegardé: {output_json}")
        
        return report
        
    finally:
        # Nettoyer les fichiers temporaires
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description='Visualiseur de pixels MCD43A1 (rasterio)')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--region', nargs=4, type=int, 
                       metavar=('ROW_START', 'ROW_END', 'COL_START', 'COL_END'),
                       help='Région à visualiser')
    parser.add_argument('--save-plot', help='Sauvegarder la figure')
    parser.add_argument('--save-json', help='Sauvegarder les données en JSON')
    
    args = parser.parse_args()
    
    print(f"Extraction des paramètres BRDF de la bande {args.band}...")
    
    # Extraire en GeoTIFF temporaire
    temp_file, temp_dir = extract_subdataset_with_gdal_translate(args.input, args.band)
    
    try:
        # Lire les données
        data = read_geotiff_params(temp_file)
        
        print(f"Dimensions de l'image: {data['shape']}")
        print(f"Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
        
        # Créer le rapport JSON si demandé
        if args.save_json:
            create_pixel_report(args.input, args.band, args.save_json)
        
        # Visualiser
        region = args.region
        fig = visualize_pixel_grid(data, args.band, region)
        
        if args.save_plot:
            fig.savefig(args.save_plot, dpi=150, bbox_inches='tight')
            print(f"Figure sauvegardée: {args.save_plot}")
        
        plt.show()
        
    finally:
        # Nettoyer les fichiers temporaires
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()