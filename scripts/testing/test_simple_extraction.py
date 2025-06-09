#!/usr/bin/env python3
"""
Simple test to validate basic extraction without complex metadata
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

def test_simple_extraction():
    """Test basic extraction functionality"""
    print("🔍 Testing Simple Extraction")
    print("=" * 40)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Very short test period
    test_start = '2023-07-01'
    test_end = '2023-07-03'  # Just 3 days
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    
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
            
            # Show basic info
            if 'pixel_count' in data.columns:
                print(f"\n📊 Pixel Count Info:")
                print(f"   Min: {data['pixel_count'].min()}")
                print(f"   Max: {data['pixel_count'].max()}")
                print(f"   Mean: {data['pixel_count'].mean():.1f}")
            
            # Show first few rows
            print(f"\n📋 Sample Data:")
            display_cols = ['date', 'albedo_mean', 'pixel_count']
            if all(col in data.columns for col in display_cols):
                print(data[display_cols].head().to_string(index=False))
            
            return True
        else:
            print("⚠️ No data extracted")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 SIMPLE EXTRACTION TEST")
    print("=" * 40)
    
    success = test_simple_extraction()
    
    if success:
        print(f"\n🎉 BASIC EXTRACTION WORKS!")
        print("✅ The Terra-Aqua fusion and pixel counting seem functional")
    else:
        print(f"\n❌ BASIC EXTRACTION FAILED")
        print("💡 Check the error details above")