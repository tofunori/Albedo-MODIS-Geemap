#!/usr/bin/env python3
"""
Debug script to check what's happening in Terra-Aqua fusion
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee
from config import athabasca_roi, MODIS_COLLECTIONS
from data.extraction import mask_modis_snow_albedo_fast, combine_terra_aqua_literature_method

def debug_fusion_step_by_step():
    """Debug the Terra-Aqua fusion step by step"""
    print("🐛 Debug Terra-Aqua Fusion - Étape par Étape")
    print("=" * 60)
    
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        # Test the problematic date - SAME as interactive map
        test_date = '2024-07-04'
        start_date = '2024-07-04'
        end_date = '2024-07-05'
        
        print(f"\n📅 Test date: {test_date}")
        print(f"🎯 Expected from diagnostic: ~14 pixels")
        print(f"🚨 Your test showed: 40 pixels")
        
        # Step 1: Get raw collections like in your extraction
        print(f"\n🚀 Étape 1: Collections brutes")
        
        mod_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date)
        
        myd_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date)
        
        terra_count = mod_col.size().getInfo()
        aqua_count = myd_col.size().getInfo()
        
        print(f"   🛰️ Terra images: {terra_count}")
        print(f"   🛰️ Aqua images: {aqua_count}")
        
        # If multiple images, show details
        if terra_count > 1:
            terra_times = mod_col.aggregate_array('system:time_start').getInfo()
            print(f"   🕐 Terra times: {[ee.Date(t).format('HH:mm').getInfo() for t in terra_times]}")
        
        if aqua_count > 1:
            aqua_times = myd_col.aggregate_array('system:time_start').getInfo()
            print(f"   🕐 Aqua times: {[ee.Date(t).format('HH:mm').getInfo() for t in aqua_times]}")
        
        # Step 2: Apply masking like in your extraction
        print(f"\n🚀 Étape 2: Application des masques QA")
        
        mod_masked = mod_col.map(mask_modis_snow_albedo_fast)
        myd_masked = myd_col.map(mask_modis_snow_albedo_fast)
        
        # Step 3: Check pixel counts before fusion
        print(f"\n🚀 Étape 3: Pixels avant fusion")
        
        # Count pixels for each Terra image
        terra_pixels_list = []
        if terra_count > 0:
            for i in range(terra_count):
                terra_img = ee.Image(mod_masked.toList(terra_count).get(i))
                pixels = terra_img.select('albedo_daily').reduceRegion(
                    reducer=ee.Reducer.count(),
                    geometry=athabasca_roi,
                    scale=500,
                    maxPixels=1e9
                ).get('albedo_daily').getInfo()
                terra_pixels_list.append(pixels)
            print(f"   🛰️ Terra pixels par image: {terra_pixels_list}")
            terra_pixels = terra_pixels_list[0] if terra_pixels_list else 0
        else:
            terra_pixels = 0
            print(f"   🛰️ Terra: Pas d'images")
        
        # Count pixels for each Aqua image  
        aqua_pixels_list = []
        if aqua_count > 0:
            for i in range(aqua_count):
                aqua_img = ee.Image(myd_masked.toList(aqua_count).get(i))
                pixels = aqua_img.select('albedo_daily').reduceRegion(
                    reducer=ee.Reducer.count(),
                    geometry=athabasca_roi,
                    scale=500,
                    maxPixels=1e9
                ).get('albedo_daily').getInfo()
                aqua_pixels_list.append(pixels)
            print(f"   🛰️ Aqua pixels par image: {aqua_pixels_list}")
            aqua_pixels = aqua_pixels_list[0] if aqua_pixels_list else 0
        else:
            aqua_pixels = 0
            print(f"   🛰️ Aqua: Pas d'images")
        
        # Step 4: Apply fusion
        print(f"\n🚀 Étape 4: Fusion avec nouvelle méthode")
        
        fused_collection = combine_terra_aqua_literature_method(mod_masked, myd_masked)
        fused_count = fused_collection.size().getInfo()
        
        print(f"   🔗 Images fusionnées: {fused_count}")
        
        if fused_count > 0:
            fused_img = fused_collection.first()
            fused_pixels = fused_img.select('albedo_daily').reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=athabasca_roi,
                scale=500,
                maxPixels=1e9
            ).get('albedo_daily').getInfo()
            
            # Check source
            source = fused_img.get('source').getInfo()
            
            print(f"   🔗 Pixels fusionnés: {fused_pixels}")
            print(f"   🔗 Source utilisée: {source}")
        
        # Step 5: Compare with old method (simple merge)
        print(f"\n🚀 Étape 5: Comparaison méthode ancienne (merge)")
        
        old_collection = mod_masked.merge(myd_masked).sort('system:time_start')
        old_count = old_collection.size().getInfo()
        
        print(f"   🔄 Images merge: {old_count}")
        
        if old_count > 0:
            # Count pixels in all images
            def count_pixels(img):
                count = img.select('albedo_daily').reduceRegion(
                    reducer=ee.Reducer.count(),
                    geometry=athabasca_roi,
                    scale=500,
                    maxPixels=1e9
                ).get('albedo_daily')
                return img.set('pixel_count', count)
            
            old_with_counts = old_collection.map(count_pixels)
            pixel_counts = old_with_counts.aggregate_array('pixel_count').getInfo()
            
            print(f"   🔄 Pixels par image: {pixel_counts}")
            print(f"   🔄 Total si sommé: {sum(pixel_counts)}")
        
        # Summary
        print(f"\n📊 RÉSUMÉ DEBUG:")
        print(f"   Terra seul: {terra_pixels} pixels")
        print(f"   Aqua seul: {aqua_pixels} pixels")
        print(f"   Après fusion: {fused_pixels} pixels")
        print(f"   Ancien merge: {old_count} images avec {pixel_counts if 'pixel_counts' in locals() else 'N/A'}")
        
        # Hypothesis
        print(f"\n💡 HYPOTHÈSE:")
        if terra_pixels + aqua_pixels == 40:
            print(f"   🎯 VOS 40 PIXELS = {terra_pixels} Terra + {aqua_pixels} Aqua")
            print(f"   🚨 L'ancien code comptait Terra ET Aqua séparément!")
            print(f"   ✅ La nouvelle fusion corrige cela: {fused_pixels} pixels")
        else:
            print(f"   🤔 Autre cause possible...")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_fusion_step_by_step()