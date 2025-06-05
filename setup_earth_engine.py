"""
Configuration et authentification Google Earth Engine
pour l'analyse MODIS Albedo - Glacier Athabasca
"""

import ee

def setup_earth_engine():
    """
    Configurer Google Earth Engine pour la première fois
    """
    print("🌍 CONFIGURATION GOOGLE EARTH ENGINE")
    print("="*50)
    
    try:
        # Tentative d'initialisation directe
        ee.Initialize()
        print("✅ Earth Engine déjà configuré et prêt!")
        return True
        
    except Exception as e:
        print("⚠️  Earth Engine non configuré. Configuration requise...")
        print(f"Erreur: {e}")
        
        # Guide d'authentification
        print("\n🔧 ÉTAPES DE CONFIGURATION:")
        print("1️⃣ Authentification Google:")
        print("   Exécutez: ee.Authenticate()")
        print("   Suivez les instructions dans le navigateur")
        print("")
        print("2️⃣ Initialisation:")
        print("   Exécutez: ee.Initialize()")
        print("")
        print("3️⃣ Relancez votre script")
        
        # Tentative d'authentification automatique
        try:
            print("\n🔐 Tentative d'authentification automatique...")
            ee.Authenticate()
            print("✅ Authentification réussie!")
            
            print("🔄 Initialisation...")
            ee.Initialize()
            print("✅ Earth Engine initialisé avec succès!")
            return True
            
        except Exception as auth_error:
            print(f"❌ Erreur d'authentification: {auth_error}")
            print("\n📋 INSTRUCTIONS MANUELLES:")
            print("Ouvrez un terminal Python et exécutez:")
            print("```python")
            print("import ee")
            print("ee.Authenticate()  # Suivez les instructions")
            print("ee.Initialize()    # Confirmer l'initialisation")
            print("```")
            return False

def test_earth_engine():
    """
    Tester la configuration Earth Engine
    """
    print("\n🧪 TEST CONFIGURATION EARTH ENGINE")
    print("="*40)
    
    try:
        ee.Initialize()
        
        # Test simple - créer une géométrie
        test_point = ee.Geometry.Point([-117.245, 52.214])
        print("✅ Création géométrie: OK")
        
        # Test collection MODIS
        modis_collection = ee.ImageCollection('MODIS/061/MOD10A1').limit(1)
        count = modis_collection.size().getInfo()
        print(f"✅ Accès collection MODIS: OK ({count} image testée)")
        
        # Test région Athabasca
        athabasca_test = ee.Geometry.Rectangle([-117.270, 52.198, -117.220, 52.230])
        print("✅ Région Athabasca: OK")
        
        print("\n🎉 Earth Engine configuré correctement!")
        print("✅ Vous pouvez maintenant exécuter votre analyse MODIS")
        return True
        
    except Exception as e:
        print(f"❌ Test échoué: {e}")
        return False

def quick_auth_fix():
    """
    Solution rapide pour l'authentification
    """
    print("🚀 SOLUTION RAPIDE")
    print("="*30)
    print("Exécutez ces commandes dans votre terminal Python:")
    print("")
    print(">>> import ee")
    print(">>> ee.Authenticate()")
    print(">>> ee.Initialize()")
    print("")
    print("Puis relancez votre script MODIS_Albedo+Athasbaca.py")

if __name__ == "__main__":
    print("🎯 CONFIGURATION EARTH ENGINE - GLACIER ATHABASCA")
    print("="*60)
    
    # Tentative de configuration
    success = setup_earth_engine()
    
    if success:
        # Test de la configuration
        test_success = test_earth_engine()
        
        if test_success:
            print("\n✅ CONFIGURATION TERMINÉE!")
            print("🏔️ Vous pouvez maintenant analyser le glacier Athabasca")
            print("\nPour lancer l'analyse:")
            print("python MODIS_Albedo+Athasbaca.py")
        else:
            quick_auth_fix()
    else:
        quick_auth_fix() 