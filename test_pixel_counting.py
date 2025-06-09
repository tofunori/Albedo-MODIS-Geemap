#!/usr/bin/env python3
"""
Test Pixel Counting Fix
Validates that pixel counts now reflect only valid (non-masked) pixels
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee

try:
    from data.extraction import extract_time_series_fast
    print("✅ Successfully imported extraction function")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def test_pixel_counting():
    """Test that pixel counting now works correctly"""
    print("🧮 Testing Corrected Pixel Counting")
    print("=" * 50)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Test with a short period
    test_start = '2023-07-01'
    test_end = '2023-07-10'
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    print("🎯 Testing corrected pixel counting...")
    
    try:
        data = extract_time_series_fast(
            start_date=test_start,
            end_date=test_end,
            scale=500,
            use_advanced_qa=False,
            sampling_days=None
        )
        
        if not data.empty:
            print(f"\n✅ SUCCESS! Extracted {len(data)} observations")
            
            # Analyze pixel counts
            min_pixels = data['pixel_count'].min()
            max_pixels = data['pixel_count'].max()
            mean_pixels = data['pixel_count'].mean()
            
            print(f"\n🧮 PIXEL COUNT ANALYSIS:")
            print(f"   Minimum pixels: {min_pixels}")
            print(f"   Maximum pixels: {max_pixels}")
            print(f"   Average pixels: {mean_pixels:.1f}")
            
            # Check if we're still getting unreasonably high counts
            if max_pixels > 100:
                print(f"\n⚠️  WARNING: Still getting high pixel counts ({max_pixels})")
                print("   This suggests the glacier area might be larger than expected")
                print("   OR there might still be an issue with pixel counting")
                
                # Calculate expected pixel count for glacier area
                glacier_area_km2 = 3.63  # From your CLAUDE.md
                pixel_size_m = 500
                pixel_area_km2 = (pixel_size_m * pixel_size_m) / 1e6  # Convert to km²
                expected_pixels = glacier_area_km2 / pixel_area_km2
                
                print(f"\n📏 THEORETICAL CALCULATION:")
                print(f"   Glacier area: {glacier_area_km2} km²")
                print(f"   Pixel size: {pixel_size_m}m x {pixel_size_m}m")
                print(f"   Pixel area: {pixel_area_km2} km²")
                print(f"   Expected total pixels: {expected_pixels:.0f}")
                print(f"   Observed max pixels: {max_pixels}")
                
                if max_pixels > expected_pixels * 1.5:
                    print(f"   🚨 ISSUE: Observed > 150% of expected!")
                elif max_pixels < expected_pixels * 0.1:
                    print(f"   🚨 ISSUE: Observed < 10% of expected!")
                else:
                    print(f"   ✅ REASONABLE: Within expected range")
            else:
                print(f"\n✅ GOOD: Pixel counts seem reasonable ({max_pixels} max)")
            
            # Show sample data
            print(f"\n📋 SAMPLE PIXEL COUNTS:")
            sample = data[['date', 'albedo_mean', 'pixel_count', 'satellite_source']].head(10)
            print(sample.to_string(index=False))
            
            # Check minimum pixel threshold
            below_threshold = data[data['pixel_count'] < 5]
            if len(below_threshold) > 0:
                print(f"\n⚠️  Found {len(below_threshold)} observations below 5-pixel threshold")
                print("   These should have been filtered out!")
            else:
                print(f"\n✅ All observations meet ≥5 pixel threshold")
            
            return True
            
        else:
            print("⚠️ No data extracted")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pixel_counting()
    if success:
        print(f"\n🎉 PIXEL COUNTING TEST COMPLETE!")
        print("✅ Check the results above to see if pixel counts make sense")
        print("📊 Compare with theoretical expected values")
    else:
        print(f"\n❌ PIXEL COUNTING TEST FAILED")
        print("💡 Check error messages above")