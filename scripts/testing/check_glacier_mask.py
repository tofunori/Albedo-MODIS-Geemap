#!/usr/bin/env python3
"""
Diagnostic script to check glacier mask pixel count
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee
from config import athabasca_roi

def check_glacier_mask():
    """Check if glacier mask has correct pixel count"""
    print("🔍 Diagnostic du Masque Glacier Athabasca")
    print("=" * 50)
    
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        # Test multiple dates to see variations
        dates_to_test = [
            ('2023-07-01', '2023-07-02'),  # Date du test original
            ('2024-08-02', '2024-08-03'),  # Date de votre carte interactive
            ('2023-07-04', '2023-07-05'),  # Une des dates de votre test avec 40 pixels
        ]
        
        print("\n🕐 Test de plusieurs dates:")
        
        for start_date, end_date in dates_to_test:
            print(f"\n📅 Date: {start_date}")
            
            modis = ee.ImageCollection('MODIS/061/MOD10A1') \
                      .filterDate(start_date, end_date) \
                      .first()
            
            if not modis:
                print("   ❌ Aucune image trouvée pour cette date")
                continue
        
            # Count pixels for this date
            # Count pixels within glacier mask
            albedo = modis.select('Snow_Albedo_Daily_Tile')
            
            # Count total pixels in mask (including invalid ones)
            total_pixels = albedo.select('Snow_Albedo_Daily_Tile') \
                                .reduceRegion(
                                    reducer=ee.Reducer.count(),
                                    geometry=athabasca_roi,
                                    scale=500,
                                    maxPixels=1e9
                                ).get('Snow_Albedo_Daily_Tile')
            
            total_count = total_pixels.getInfo()
            
            # Count valid albedo pixels (5-99 range)
            valid_albedo = albedo.gte(5).And(albedo.lte(99))
            valid_pixels = valid_albedo.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=athabasca_roi,
                scale=500,
                maxPixels=1e9
            ).get('Snow_Albedo_Daily_Tile')
            
            valid_count = valid_pixels.getInfo() if valid_pixels else 0
            
            # Get glacier area
            area_m2 = athabasca_roi.area().getInfo()
            area_km2 = area_m2 / 1e6
            theoretical_pixels = area_m2 / (500 * 500)
            
            print(f"\n📊 Résultats du Diagnostic:")
            print(f"   🏔️ Surface glacier: {area_km2:.2f} km²")
            print(f"   🎯 Pixels théoriques max: {theoretical_pixels:.1f}")
            print(f"   📦 Pixels totaux dans masque: {total_count}")
            print(f"   ✅ Pixels albedo valides: {valid_count}")
            
            # Analysis
            print(f"\n🔍 Analyse:")
            if total_count > theoretical_pixels * 1.5:
                print(f"   ⚠️ PROBLÈME: Trop de pixels dans le masque!")
                print(f"   📈 Ratio: {total_count/theoretical_pixels:.1f}x théorique")
                print(f"   💡 Le masque déborde probablement du glacier")
            elif total_count <= theoretical_pixels * 1.2:
                print(f"   ✅ Nombre de pixels cohérent")
                print(f"   📈 Ratio: {total_count/theoretical_pixels:.1f}x théorique")
            else:
                print(f"   🤔 Légèrement élevé mais acceptable")
                print(f"   📈 Ratio: {total_count/theoretical_pixels:.1f}x théorique")
            
            if valid_count > 20:
                print(f"   ⚠️ ATTENTION: {valid_count} pixels avec albédo valide semble élevé")
                print(f"   🎯 Attendu: 8-15 pixels max pour ce glacier")
            
            return total_count, valid_count, theoretical_pixels
            
        else:
            print("❌ Aucune image MODIS trouvée pour la date test")
            return None, None, None
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def suggest_solutions():
    """Suggest solutions if mask is too big"""
    print(f"\n🛠️ Solutions Possibles:")
    print(f"1. 📏 Vérifier le GeoJSON source:")
    print(f"   - Ouvrir Athabasca_mask_2023_cut.geojson dans QGIS")
    print(f"   - Vérifier que seul le glacier est inclus")
    print(f"2. 🎯 Restreindre le masque:")
    print(f"   - Exclure la zone périglaciaire")
    print(f"   - Utiliser seulement la glace propre")
    print(f"3. ✂️ Buffer négatif:")
    print(f"   - Appliquer un buffer -50m pour réduire les bordures")

if __name__ == "__main__":
    total, valid, theoretical = check_glacier_mask()
    
    if total and total > theoretical * 1.5:
        suggest_solutions()
    
    print(f"\n💡 Pour comparer avec vos résultats de test:")
    print(f"   Vos 40 pixels dépassent largement le théorique de ~15")
    print(f"   Cela confirme un problème de masque trop large")