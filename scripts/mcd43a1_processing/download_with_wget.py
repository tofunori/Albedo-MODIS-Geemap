#!/usr/bin/env python3
"""
Téléchargeur alternatif utilisant wget pour LAADS DAAC
"""

import os
import subprocess
import sys
from pathlib import Path

def download_with_wget(year=2024, doy=243, tile="h10v03"):
    """
    Télécharge MCD43A1 avec wget et authentification Earthdata
    """
    # URL du fichier
    filename = f"MCD43A1.A{year}{doy:03d}.{tile}.061.2024252033649.hdf"
    url = f"https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCD43A1/{year}/{doy:03d}/{filename}"
    
    # Créer le répertoire de sortie
    output_dir = Path(f"data/{year}/{doy:03d}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / filename
    
    # Supprimer le fichier existant s'il est trop petit
    if output_file.exists() and output_file.stat().st_size < 1000000:  # < 1MB
        print(f"Suppression du fichier incomplet: {output_file}")
        output_file.unlink()
    
    print(f"Téléchargement de {filename}...")
    print(f"URL: {url}")
    print(f"Destination: {output_file}")
    
    # Méthode 1: wget avec cookies
    print("\nEssai avec wget et authentification par cookies...")
    
    # D'abord, créer un fichier de cookies
    cookie_file = Path("earthdata_cookies.txt")
    
    # Commande pour se connecter et sauvegarder les cookies
    login_cmd = [
        "wget",
        "--save-cookies", str(cookie_file),
        "--keep-session-cookies",
        "--no-check-certificate",
        "--user", "tofunori",
        "--password", "ASDqwe1234567890!",
        "--post-data", "username=tofunori&password=ASDqwe1234567890!",
        "-O", "-",
        "https://urs.earthdata.nasa.gov/login"
    ]
    
    try:
        print("Connexion à Earthdata...")
        subprocess.run(login_cmd, capture_output=True)
        
        # Télécharger avec les cookies
        download_cmd = [
            "wget",
            "--load-cookies", str(cookie_file),
            "--no-check-certificate",
            "-O", str(output_file),
            url
        ]
        
        print("Téléchargement du fichier...")
        result = subprocess.run(download_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"\n✅ Téléchargement réussi: {output_file}")
            print(f"Taille: {size_mb:.2f} MB")
            
            if size_mb < 50:
                print("⚠️ ATTENTION: Le fichier semble trop petit. Vérifiez l'authentification.")
        else:
            print(f"\n❌ Échec du téléchargement")
            if result.stderr:
                print(f"Erreur: {result.stderr}")
                
    except Exception as e:
        print(f"Erreur: {e}")
    
    finally:
        # Nettoyer le fichier de cookies
        if cookie_file.exists():
            cookie_file.unlink()
    
    # Si wget n'est pas disponible, essayer avec curl
    if not output_file.exists() or output_file.stat().st_size < 1000000:
        print("\n\nEssai avec curl et token Bearer...")
        
        # Cette méthode nécessite un token d'accès
        # Pour obtenir le token, il faut faire une requête OAuth
        print("Pour cette méthode, vous devez:")
        print("1. Aller sur https://urs.earthdata.nasa.gov/profile")
        print("2. Générer un token d'accès dans 'My Applications'")
        print("3. Utiliser ce token avec curl:")
        print(f"\ncurl -H 'Authorization: Bearer YOUR_TOKEN' -L -o {output_file} '{url}'")

if __name__ == "__main__":
    # Vérifier si wget est disponible
    try:
        subprocess.run(["wget", "--version"], capture_output=True, check=True)
        print("wget est disponible")
    except:
        print("⚠️ wget n'est pas installé. Installation recommandée:")
        print("Windows: Télécharger depuis https://eternallybored.org/misc/wget/")
        print("Ou utiliser: choco install wget")
        sys.exit(1)
    
    download_with_wget()