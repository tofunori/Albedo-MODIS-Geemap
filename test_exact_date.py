#!/usr/bin/env python3
"""
Test with the exact same date and method as your original test
"""

import ee
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Initialize Earth Engine
ee.Initialize()

print("🔍 TESTING WITH EXACT SAME CONDITIONS AS YOUR ORIGINAL TEST")
print("=" * 60)

# Use the exact same extraction function
try:
    from data.extraction import extract_time_series_fast
    print("✅ Successfully imported extraction function")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test with your exact date range
test_start = '2024-08-01'
test_end = '2024-08-07'

print(f"📅 Testing period: {test_start} to {test_end}")
print(f"🎯 Using your exact extraction function...")

# Run the exact same extraction as your test
try:
    data = extract_time_series_fast(
        start_date=test_start,
        end_date=test_end,
        scale=500,
        use_advanced_qa=False,  # Same as your test
        sampling_days=None      # Same as your test
    )
    
    if not data.empty:
        print(f"\n✅ SUCCESS! Extracted {len(data)} observations")
        
        # Show the results
        min_pixels = data['pixel_count'].min()
        max_pixels = data['pixel_count'].max()
        mean_pixels = data['pixel_count'].mean()
        
        print(f"\n🧮 PIXEL COUNT RESULTS:")
        print(f"   Minimum pixels: {min_pixels}")
        print(f"   Maximum pixels: {max_pixels}")
        print(f"   Average pixels: {mean_pixels:.1f}")
        
        # Show sample data
        print(f"\n📋 SAMPLE DATA:")
        sample = data[['date', 'albedo_mean', 'pixel_count', 'satellite_source']].head()
        print(sample.to_string(index=False))
        
        # Calculate areas
        estimated_areas = data['pixel_count'] * 0.25
        print(f"\n📏 ESTIMATED AREAS:")
        print(f"   Min area: {estimated_areas.min():.2f} km²")
        print(f"   Max area: {estimated_areas.max():.2f} km²")
        print(f"   Avg area: {estimated_areas.mean():.2f} km²")
        
        # Identify which mask was used
        from config import use_shapefile, mask_path
        print(f"\n🗂️ MASK USED:")
        print(f"   Use shapefile: {use_shapefile}")
        print(f"   Mask path: {os.path.basename(mask_path)}")
        
    else:
        print("⚠️ No data extracted")
        
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

print(f"\n💡 DIAGNOSIS:")
print(f"   If this gives 36 pixels: The mask is working correctly")
print(f"   If this gives 1 pixel: There's a date/QA filtering issue")
print(f"   If this gives 40 pixels: The old (larger) mask is still being used")