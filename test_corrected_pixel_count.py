#!/usr/bin/env python3
"""
Test Corrected Pixel Count with Glacier Mask
Validates that pixel counts now reflect only pixels INSIDE the glacier mask
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

def test_glacier_masked_pixel_count():
    """Test that pixel counting now uses glacier mask correctly"""
    print("🎯 Testing Glacier-Masked Pixel Counting")
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
    test_end = '2023-07-05'
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    print("🎯 Now using glacier mask to restrict pixel counting...")
    
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
            
            print(f"\n🧮 CORRECTED PIXEL COUNT ANALYSIS:")
            print(f"   Minimum pixels: {min_pixels}")
            print(f"   Maximum pixels: {max_pixels}")
            print(f"   Average pixels: {mean_pixels:.1f}")
            
            # Check if counts are now closer to your manual count of ~20
            print(f"\n🎯 COMPARISON WITH MANUAL COUNT:")
            manual_count = 20  # Your manual count
            
            if min_pixels <= manual_count <= max_pixels:
                print(f"   ✅ EXCELLENT: Manual count ({manual_count}) is within observed range!")
                print(f"   📊 Variation is normal due to cloud coverage")
            elif max_pixels < manual_count * 0.5:
                print(f"   ❌ TOO LOW: Max observed ({max_pixels}) << manual ({manual_count})")
                print(f"   💡 Might be too much masking or QA filtering")
            elif min_pixels > manual_count * 2:
                print(f"   ❌ STILL TOO HIGH: Min observed ({min_pixels}) >> manual ({manual_count})")
                print(f"   💡 Glacier mask might not be applied correctly")
            else:
                print(f"   ✅ REASONABLE: Close to manual count")
            
            # Show sample data
            print(f"\n📋 SAMPLE DATA WITH CORRECTED PIXEL COUNTS:")
            sample = data[['date', 'albedo_mean', 'pixel_count', 'satellite_source']].head()
            print(sample.to_string(index=False))
            
            # Calculate glacier area from pixel count
            pixel_area_km2 = 0.25  # 500m x 500m = 0.25 km²
            estimated_areas = data['pixel_count'] * pixel_area_km2
            
            print(f"\n🗺️ ESTIMATED GLACIER AREA FROM PIXEL COUNT:")
            print(f"   Min area: {estimated_areas.min():.2f} km²")
            print(f"   Max area: {estimated_areas.max():.2f} km²")
            print(f"   Avg area: {estimated_areas.mean():.2f} km²")
            print(f"   Expected: ~3.63 km² (from documentation)")
            
            if estimated_areas.mean() < 6.0:  # Reasonable upper bound
                print(f"   ✅ REALISTIC: Estimated area seems reasonable")
            else:
                print(f"   ❌ TOO LARGE: Estimated area too high")
            
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
    success = test_glacier_masked_pixel_count()
    if success:
        print(f"\n🎉 GLACIER MASK TEST COMPLETE!")
        print("✅ Check if pixel counts now match your manual count of ~20")
        print("📊 Variation between dates is normal due to cloud coverage")
    else:
        print(f"\n❌ GLACIER MASK TEST FAILED")
        print("💡 Check error messages above")