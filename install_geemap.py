#!/usr/bin/env python3
"""
Script d'installation et configuration de geemap pour Earth Engine
"""

import subprocess
import sys
import os

def install_package(package):
    """Installer un package Python via pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_earth_engine_auth():
    """Vérifier l'authentification Earth Engine"""
    try:
        import ee
        ee.Initialize()
        print("✅ Earth Engine déjà authentifié et configuré!")
        return True
    except:
        return False

def setup_geemap():
    """Configuration complète de geemap et Earth Engine"""
    print("🌍 INSTALLATION ET CONFIGURATION DE GEEMAP")
    print("=" * 60)
    
    # 1. Installer geemap
    print("\n📦 Installation de geemap...")
    if install_package("geemap"):
        print("✅ geemap installé avec succès!")
    else:
        print("❌ Erreur lors de l'installation de geemap")
        return False
    
    # 2. Installer les dépendances optionnelles
    print("\n📦 Installation des dépendances optionnelles...")
    optional_packages = ["geopandas", "localtileserver", "ipyleaflet"]
    for pkg in optional_packages:
        print(f"  • Installation de {pkg}...")
        install_package(pkg)
    
    # 3. Vérifier l'authentification Earth Engine
    print("\n🔐 Vérification de l'authentification Earth Engine...")
    
    if check_earth_engine_auth():
        return True
    
    # 4. Guide d'authentification
    print("\n⚠️  Earth Engine nécessite une authentification")
    print("\n📋 ÉTAPES D'AUTHENTIFICATION:")
    print("1. Exécutez le code suivant dans Python:")
    print("\n" + "-" * 40)
    print("import ee")
    print("ee.Authenticate()")
    print("ee.Initialize()")
    print("-" * 40)
    print("\n2. Suivez les instructions dans le navigateur")
    print("3. Copiez le code d'autorisation")
    print("4. Collez-le dans le terminal")
    
    # 5. Tentative d'authentification automatique
    try:
        import ee
        print("\n🚀 Lancement de l'authentification...")
        ee.Authenticate()
        ee.Initialize()
        print("✅ Authentification réussie!")
        return True
    except Exception as e:
        print(f"\n❌ Authentification échouée: {e}")
        print("\n💡 Solution: Exécutez manuellement les commandes ci-dessus")
        return False

def test_geemap_earth_engine():
    """Tester que tout fonctionne correctement"""
    print("\n🧪 TEST DE CONFIGURATION")
    print("=" * 40)
    
    try:
        import geemap
        import ee
        
        # Test 1: Initialisation via geemap
        print("• Test geemap.ee_initialize()... ", end="")
        geemap.ee_initialize()
        print("✅")
        
        # Test 2: Création d'une géométrie
        print("• Test création géométrie... ", end="")
        point = ee.Geometry.Point([-117.245, 52.214])
        print("✅")
        
        # Test 3: Accès à une collection
        print("• Test accès collection MODIS... ", end="")
        collection = ee.ImageCollection('MODIS/061/MOD10A1').limit(1)
        count = collection.size().getInfo()
        print(f"✅ ({count} image)")
        
        print("\n🎉 Tout fonctionne correctement!")
        print("✅ Vous pouvez maintenant exécuter MODIS_Albedo+Athasbaca.py")
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        return False

def main():
    """Fonction principale"""
    print("🎯 CONFIGURATION POUR L'ANALYSE MODIS - GLACIER ATHABASCA")
    print("=" * 70)
    
    # Installation et configuration
    if setup_geemap():
        # Test final
        test_geemap_earth_engine()
    
    print("\n📌 PROCHAINE ÉTAPE:")
    print("Exécutez: python MODIS_Albedo+Athasbaca.py")

if __name__ == "__main__":
    main()