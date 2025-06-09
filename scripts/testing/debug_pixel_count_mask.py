#!/usr/bin/env python3
"""
Debug Pixel Count with Mask Analysis
Investigates why we're getting ~40 pixels instead of ~20 pixels

This script will:
1. Test different mask configurations
2. Check actual pixel coverage area
3. Compare with/without mask
4. Validate mask geometry
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee
import pandas as pd
from config import athabasca_roi, MODIS_COLLECTIONS

def debug_mask_geometry():
    """Debug the glacier mask geometry"""
    print("🔍 DEBUGGING GLACIER MASK GEOMETRY")
    print("=" * 50)
    
    try:
        # Get mask area
        mask_area_m2 = athabasca_roi.area().getInfo()
        mask_area_km2 = mask_area_m2 / 1e6
        print(f"📏 Actual mask area: {mask_area_km2:.2f} km²")
        
        # Calculate theoretical pixel count at 500m resolution
        pixel_area_m2 = 500 * 500  # 500m x 500m = 250,000 m²
        theoretical_pixels = mask_area_m2 / pixel_area_m2
        print(f"🧮 Theoretical pixel count (500m): {theoretical_pixels:.1f} pixels")
        
        # Get mask bounds
        bounds = athabasca_roi.bounds().getInfo()
        print(f"📍 Mask bounds: {bounds}")
        
        return mask_area_km2, theoretical_pixels
        
    except Exception as e:
        print(f"❌ Error getting mask info: {e}")
        return None, None

def test_pixel_count_with_different_methods():
    """Test pixel counting with different methods"""
    print("\n🧪 TESTING PIXEL COUNT METHODS")
    print("=" * 50)
    
    try:
        # Create a simple test image (MODIS snow albedo for one day)
        test_date = '2023-07-15'
        
        # Get a Terra image for testing
        terra_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
            .filterBounds(athabasca_roi) \
            .filterDate(test_date, test_date) \
            .limit(1)
        
        if terra_col.size().getInfo() == 0:
            print("❌ No Terra images found for test date")
            return
            
        test_image = terra_col.first()
        albedo = test_image.select('Snow_Albedo_Daily_Tile')
        qa = test_image.select('NDSI_Snow_Cover_Basic_QA')
        
        print(f"📅 Test date: {test_date}")
        print(f"🛰️ Using Terra image")
        
        # Method 1: Count all pixels (no mask, no QA filtering)
        stats1 = albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        count1 = stats1.get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"📊 Method 1 - All pixels in mask: {count1}")
        
        # Method 2: Count valid albedo pixels (5-99 range, no QA)
        valid_albedo = albedo.gte(5).And(albedo.lte(99))
        masked_albedo = albedo.updateMask(valid_albedo)
        
        stats2 = masked_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        count2 = stats2.get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"📊 Method 2 - Valid albedo range (5-99): {count2}")
        
        # Method 3: Count with QA=0 (best quality only)
        qa_mask = qa.eq(0)
        quality_albedo = albedo.updateMask(valid_albedo.And(qa_mask))
        
        stats3 = quality_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        count3 = stats3.get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"📊 Method 3 - QA=0 + valid range: {count3}")
        
        # Method 4: Count with QA≤1 (best + good quality)
        qa_mask_relaxed = qa.lte(1)
        quality_albedo_relaxed = albedo.updateMask(valid_albedo.And(qa_mask_relaxed))
        
        stats4 = quality_albedo_relaxed.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        count4 = stats4.get('Snow_Albedo_Daily_Tile').getInfo()
        print(f"📊 Method 4 - QA≤1 + valid range: {count4}")
        
        return count1, count2, count3, count4
        
    except Exception as e:
        print(f"❌ Error in pixel count test: {e}")
        return None, None, None, None

def test_without_mask():
    """Test pixel count without any mask to see total coverage"""
    print("\n🌍 TESTING WITHOUT GLACIER MASK")
    print("=" * 50)
    
    try:
        # Create a larger area around the glacier for comparison
        # Approximate bounds around Athabasca Glacier
        large_area = ee.Geometry.Rectangle([-117.3, 52.15, -117.15, 52.25])
        
        test_date = '2023-07-15'
        terra_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
            .filterBounds(large_area) \
            .filterDate(test_date, test_date) \
            .limit(1)
        
        if terra_col.size().getInfo() == 0:
            print("❌ No images found")
            return
            
        test_image = terra_col.first()
        albedo = test_image.select('Snow_Albedo_Daily_Tile')
        qa = test_image.select('NDSI_Snow_Cover_Basic_QA')
        
        # Count pixels in larger area
        valid_albedo = albedo.gte(5).And(albedo.lte(99))
        qa_mask = qa.lte(1)
        masked_albedo = albedo.updateMask(valid_albedo.And(qa_mask))
        
        stats_large = masked_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=large_area,
            scale=500,
            maxPixels=1e9
        )
        
        stats_glacier = masked_albedo.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        
        count_large = stats_large.get('Snow_Albedo_Daily_Tile').getInfo()
        count_glacier = stats_glacier.get('Snow_Albedo_Daily_Tile').getInfo()
        
        print(f"📊 Large area pixels: {count_large}")
        print(f"📊 Glacier mask pixels: {count_glacier}")
        print(f"📊 Reduction factor: {count_large/count_glacier:.1f}x")
        
        # Calculate areas
        large_area_km2 = large_area.area().getInfo() / 1e6
        glacier_area_km2 = athabasca_roi.area().getInfo() / 1e6
        
        print(f"📏 Large area: {large_area_km2:.2f} km²")
        print(f"📏 Glacier area: {glacier_area_km2:.2f} km²")
        print(f"📏 Area ratio: {large_area_km2/glacier_area_km2:.1f}x")
        
    except Exception as e:
        print(f"❌ Error in no-mask test: {e}")

def main():
    """Main debugging function"""
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Run all tests
    mask_area, theoretical_pixels = debug_mask_geometry()
    
    if mask_area and theoretical_pixels:
        print(f"\n🎯 EXPECTED RESULTS:")
        print(f"   - Theoretical max pixels: {theoretical_pixels:.0f}")
        print(f"   - Your manual count: ~20 pixels")
        print(f"   - Current extraction: ~40 pixels")
    
    counts = test_pixel_count_with_different_methods()
    
    test_without_mask()
    
    print(f"\n📋 SUMMARY:")
    print(f"   If Method 1 ≈ theoretical pixels: Mask is correct")
    print(f"   If Method 2-4 << Method 1: QA filtering is working")
    print(f"   If all methods >> 20: Mask might be too large")
    print(f"   Compare current extraction (~40) with Method 4 results")

if __name__ == "__main__":
    main()