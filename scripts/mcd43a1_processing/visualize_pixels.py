#!/usr/bin/env python3
"""
Visualiseur de pixels MCD43A1
Affiche chaque pixel avec ses valeurs BRDF et albédo calculé
"""

import numpy as np
import rasterio
from osgeo import gdal
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import argparse
import json

def extract_brdf_parameters(hdf_file, band=6):
    """
    Extrait les paramètres BRDF d'un fichier MCD43A1
    """
    # Ouvrir le fichier HDF
    dataset = gdal.Open(hdf_file)
    if not dataset:
        raise ValueError(f"Impossible d'ouvrir {hdf_file}")
    
    # Les sous-datasets pour MCD43A1
    # Format: BRDF_Albedo_Parameters_Band{band}
    subdatasets = dataset.GetSubDatasets()
    
    # Trouver le subdataset pour la bande demandée
    param_subdataset = None
    for sds_name, sds_desc in subdatasets:
        if f"BRDF_Albedo_Parameters_Band{band}" in sds_desc:
            param_subdataset = sds_name
            break
    
    if not param_subdataset:
        raise ValueError(f"Pas de paramètres BRDF pour la bande {band}")
    
    # Ouvrir le subdataset
    param_ds = gdal.Open(param_subdataset)
    
    # Les 3 paramètres sont stockés dans les 3 premières bandes
    f_iso = param_ds.GetRasterBand(1).ReadAsArray()
    f_vol = param_ds.GetRasterBand(2).ReadAsArray()
    f_geo = param_ds.GetRasterBand(3).ReadAsArray()
    
    # Facteur d'échelle
    scale_factor = 0.001
    
    # Appliquer le facteur d'échelle et masquer les valeurs invalides
    f_iso = np.where(f_iso == 32767, np.nan, f_iso * scale_factor)
    f_vol = np.where(f_vol == 32767, np.nan, f_vol * scale_factor)
    f_geo = np.where(f_geo == 32767, np.nan, f_geo * scale_factor)
    
    # Obtenir les métadonnées géospatiales
    geotransform = param_ds.GetGeoTransform()
    projection = param_ds.GetProjection()
    
    return {
        'f_iso': f_iso,
        'f_vol': f_vol,
        'f_geo': f_geo,
        'geotransform': geotransform,
        'projection': projection,
        'shape': f_iso.shape
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
    cell_text = []
    for i in range(nrows):
        for j in range(ncols):
            if not np.isnan(region_iso[i, j]):
                text = f'Pixel [{row_start+i},{col_start+j}]\n'
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
                        ha='center', va='center', color='white' if wsa_grid[i, j] < 0.5 else 'black')
    
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
                        ha='center', va='center', color='white' if bsa_grid[i, j] < 0.5 else 'black')
    
    # 4. Statistiques
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Calculer les statistiques
    valid_pixels = np.sum(~np.isnan(region_iso))
    stats_text = f"Statistiques de la région [{row_start}:{row_end}, {col_start}:{col_end}]\n\n"
    stats_text += f"Pixels valides: {valid_pixels}/{nrows*ncols}\n\n"
    
    if valid_pixels > 0:
        stats_text += "f_iso: {:.3f} ± {:.3f} [{:.3f}, {:.3f}]\n".format(
            np.nanmean(region_iso), np.nanstd(region_iso), 
            np.nanmin(region_iso), np.nanmax(region_iso))
        stats_text += "f_vol: {:.3f} ± {:.3f} [{:.3f}, {:.3f}]\n".format(
            np.nanmean(region_vol), np.nanstd(region_vol), 
            np.nanmin(region_vol), np.nanmax(region_vol))
        stats_text += "f_geo: {:.3f} ± {:.3f} [{:.3f}, {:.3f}]\n\n".format(
            np.nanmean(region_geo), np.nanstd(region_geo), 
            np.nanmin(region_geo), np.nanmax(region_geo))
        stats_text += "WSA: {:.3f} ± {:.3f} [{:.3f}, {:.3f}]\n".format(
            np.nanmean(wsa_grid), np.nanstd(wsa_grid), 
            np.nanmin(wsa_grid), np.nanmax(wsa_grid))
        stats_text += "BSA: {:.3f} ± {:.3f} [{:.3f}, {:.3f}]\n".format(
            np.nanmean(bsa_grid), np.nanstd(bsa_grid), 
            np.nanmin(bsa_grid), np.nanmax(bsa_grid))
    
    ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes, fontsize=12, 
             verticalalignment='center', family='monospace')
    
    plt.tight_layout()
    return fig

def create_pixel_report(hdf_file, band=6, output_json=None):
    """
    Crée un rapport JSON avec les valeurs de chaque pixel
    """
    data = extract_brdf_parameters(hdf_file, band)
    
    f_iso = data['f_iso']
    f_vol = data['f_vol']
    f_geo = data['f_geo']
    
    pixel_data = []
    
    # Parcourir tous les pixels
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
    
    report = {
        'file': str(hdf_file),
        'band': band,
        'shape': list(f_iso.shape),
        'total_pixels': int(f_iso.shape[0] * f_iso.shape[1]),
        'valid_pixels': len(pixel_data),
        'pixels': pixel_data
    }
    
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Rapport sauvegardé: {output_json}")
    
    return report

def main():
    parser = argparse.ArgumentParser(description='Visualiseur de pixels MCD43A1')
    parser.add_argument('--input', required=True, help='Fichier MCD43A1 HDF')
    parser.add_argument('--band', type=int, default=6, help='Bande MODIS (1-7)')
    parser.add_argument('--region', nargs=4, type=int, metavar=('ROW_START', 'ROW_END', 'COL_START', 'COL_END'),
                       help='Région à visualiser')
    parser.add_argument('--save-plot', help='Sauvegarder la figure')
    parser.add_argument('--save-json', help='Sauvegarder les données en JSON')
    parser.add_argument('--show-all', action='store_true', help='Afficher tous les pixels (attention si grande image!)')
    
    args = parser.parse_args()
    
    # Extraire les données
    print(f"Extraction des paramètres BRDF de la bande {args.band}...")
    data = extract_brdf_parameters(args.input, args.band)
    
    print(f"Dimensions de l'image: {data['shape']}")
    print(f"Pixels valides: {np.sum(~np.isnan(data['f_iso']))}")
    
    # Créer le rapport JSON si demandé
    if args.save_json:
        create_pixel_report(args.input, args.band, args.save_json)
    
    # Visualiser
    if args.show_all:
        # Attention: peut être très grand!
        region = [0, data['shape'][0], 0, data['shape'][1]]
    else:
        region = args.region
    
    fig = visualize_pixel_grid(data, args.band, region)
    
    if args.save_plot:
        fig.savefig(args.save_plot, dpi=150, bbox_inches='tight')
        print(f"Figure sauvegardée: {args.save_plot}")
    
    plt.show()

if __name__ == "__main__":
    main()