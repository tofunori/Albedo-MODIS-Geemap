#!/usr/bin/env python3
"""
Téléchargeur direct pour LAADS DAAC avec App Key
"""

import os
import requests
import subprocess
from pathlib import Path

def download_with_app_key():
    """
    Télécharge depuis LAADS avec une App Key
    
    IMPORTANT: Vous devez obtenir une App Key depuis:
    https://ladsweb.modaps.eosdis.nasa.gov/profile/#app-keys
    """
    
    # Configuration
    year = 2024
    doy = 243
    tile = "h10v03"
    filename = f"MCD43A1.A{year}{doy:03d}.{tile}.061.2024252033649.hdf"
    
    # URL complète
    url = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCD43A1/{year}/{doy:03d}/{filename}"
    
    # Créer le répertoire
    output_dir = Path(f"data/{year}/{doy:03d}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / filename
    
    # Supprimer le fichier HTML existant
    if output_file.exists() and output_file.stat().st_size < 100000:
        print(f"Suppression du fichier invalide: {output_file}")
        output_file.unlink()
    
    print("\n" + "="*60)
    print("TÉLÉCHARGEMENT LAADS DAAC")
    print("="*60)
    print(f"Fichier: {filename}")
    print(f"URL: {url}")
    print()
    
    # Instructions pour obtenir l'App Key
    print("📌 INSTRUCTIONS IMPORTANTES:")
    print("1. Allez sur: https://ladsweb.modaps.eosdis.nasa.gov/")
    print("2. Connectez-vous avec tofunori / ASDqwe1234567890!")
    print("3. Cliquez sur votre nom d'utilisateur en haut à droite")
    print("4. Sélectionnez 'Profile'")
    print("5. Dans la section 'App Keys', cliquez sur 'Generate App Key'")
    print("6. Copiez la clé générée (longue chaîne de caractères)")
    print()
    
    app_key = input("Collez votre App Key LAADS ici: ").strip()
    
    if not app_key:
        print("❌ App Key requise!")
        return
    
    # Méthode 1: curl avec header Authorization
    print("\nTéléchargement avec curl...")
    cmd = [
        'curl',
        '-H', f'Authorization: Bearer {app_key}',
        '-L',
        '-o', str(output_file),
        '--fail',
        '--progress-bar',
        url
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0 and output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"\n✅ Téléchargement terminé: {output_file}")
        print(f"Taille: {size_mb:.2f} MB")
        
        if size_mb < 50:
            print("\n⚠️ Le fichier semble trop petit!")
            print("Vérifiez le contenu avec: type", output_file)
    else:
        print("\n❌ Échec du téléchargement")
        
        # Méthode alternative avec requests
        print("\nEssai avec requests Python...")
        headers = {'Authorization': f'Bearer {app_key}'}
        
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rTéléchargement: {percent:.1f}%", end='')
            
            print(f"\n✅ Téléchargement terminé!")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    download_with_app_key()