#!/usr/bin/env python3
"""
Diagnostic script to check glacier mask pixel count across multiple dates
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee
from config import athabasca_roi

def check_date(start_date, end_date, description=""):
    """Check pixel count for a specific date"""
    try:
        modis = ee.ImageCollection('MODIS/061/MOD10A1') \
                  .filterDate(start_date, end_date) \
                  .first()
        
        if not modis:
            print(f"   ❌ Aucune image trouvée")
            return None
            
        # Count pixels within glacier mask
        albedo = modis.select('Snow_Albedo_Daily_Tile')
        
        # Count total pixels in mask (including invalid ones)
        total_pixels = albedo.reduceRegion(
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
        
        # Apply same masking as in your extraction code
        basic_qa = modis.select('NDSI_Snow_Cover_Basic_QA').lte(1)
        valid_with_qa = albedo.gte(5).And(albedo.lte(99)).And(basic_qa)
        
        qa_pixels = valid_with_qa.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        ).get('Snow_Albedo_Daily_Tile')
        
        qa_count = qa_pixels.getInfo() if qa_pixels else 0
        
        print(f"   📦 Total pixels: {total_count}")
        print(f"   ✅ Albedo valide (5-99): {valid_count}")
        print(f"   🔬 Avec QA ≤1: {qa_count}")
        
        return total_count, valid_count, qa_count
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def main():
    """Main diagnostic function"""
    print("🔍 Diagnostic Multi-Dates du Masque Glacier")
    print("=" * 55)
    
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        # Test multiple dates
        dates_to_test = [
            ('2023-07-01', '2023-07-02', 'Test original (1 pixel)'),
            ('2023-07-04', '2023-07-05', 'Test Terra-Aqua (40 pixels)'),
            ('2024-08-02', '2024-08-03', 'Carte interactive (25 pixels)'),
            ('2023-08-15', '2023-08-16', 'Période claire été'),
            ('2024-07-15', '2024-07-16', 'Période récente'),
        ]
        
        # Get glacier theoretical stats
        area_m2 = athabasca_roi.area().getInfo()
        area_km2 = area_m2 / 1e6
        theoretical_pixels = area_m2 / (500 * 500)
        
        print(f"\n🏔️ Glacier Athabasca:")
        print(f"   Surface: {area_km2:.2f} km²")
        print(f"   Pixels théoriques max: {theoretical_pixels:.1f}")
        
        print(f"\n📅 Test de différentes dates:")
        
        results = []
        for start_date, end_date, description in dates_to_test:
            print(f"\n📊 {start_date} - {description}:")
            result = check_date(start_date, end_date, description)
            if result:
                results.append((start_date, description, result))
        
        # Summary analysis
        print(f"\n🔍 Analyse Comparative:")
        print(f"   {'Date':<12} {'Description':<20} {'Total':<8} {'Valide':<8} {'QA≤1':<8}")
        print(f"   {'-'*12} {'-'*20} {'-'*8} {'-'*8} {'-'*8}")
        
        for date, desc, (total, valid, qa) in results:
            print(f"   {date:<12} {desc[:20]:<20} {total:<8} {valid:<8.0f} {qa:<8.0f}")
        
        # Conclusions
        print(f"\n💡 Conclusions:")
        max_pixels = max([qa for _, _, (_, _, qa) in results])
        min_pixels = min([qa for _, _, (_, _, qa) in results])
        
        print(f"   🎯 Variation: {min_pixels:.0f} - {max_pixels:.0f} pixels selon conditions")
        print(f"   🌤️ Couverture nuageuse très variable")
        
        if max_pixels > theoretical_pixels * 2:
            print(f"   ⚠️ Maximum ({max_pixels:.0f}) dépasse largement théorique ({theoretical_pixels:.1f})")
            print(f"   🎯 Possibles causes: masque trop large ou agrégation Terra+Aqua")
        else:
            print(f"   ✅ Maximum dans la plage acceptable")
        
        print(f"\n🔧 Recommandations:")
        print(f"   1. Les variations sont normales (nuages/saisons)")
        print(f"   2. Vos 40 pixels étaient probablement conditions très claires")
        print(f"   3. Le masque semble correct (pas de débordement systématique)")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()