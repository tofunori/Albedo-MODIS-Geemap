#!/usr/bin/env python3
"""
Test script for new Terra-Aqua fusion methodology
Tests the literature-based approach vs simple merge
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import ee

# Import with proper path handling
try:
    # Try importing the function directly without going through src.__init__
    sys.path.insert(0, os.path.join(project_root, 'src'))
    from data.extraction import extract_time_series_fast
    print("✅ Successfully imported extraction function")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("💡 Make sure you're in the project root directory")
    sys.exit(1)

def test_terra_aqua_fusion():
    """
    Quick test of the new Terra-Aqua fusion method
    """
    print("🧪 Testing Terra-Aqua Literature-Based Fusion")
    print("=" * 50)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Test with a short period to avoid timeouts
    test_start = '2023-07-01'
    test_end = '2023-07-15'
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    print("🎯 Using standard QA filtering for speed")
    
    try:
        # Test the new method
        print("\n🚀 Running extraction with new Terra-Aqua fusion...")
        
        data = extract_time_series_fast(
            start_date=test_start,
            end_date=test_end,
            scale=500,
            use_advanced_qa=False,  # Use fast QA for testing
            sampling_days=None
        )
        
        if not data.empty:
            print(f"\n✅ SUCCESS! Extracted {len(data)} observations")
            print(f"📊 Date range: {data['date'].min()} to {data['date'].max()}")
            print(f"📈 Albedo range: {data['albedo_mean'].min():.3f} - {data['albedo_mean'].max():.3f}")
            print(f"🔍 Average pixel count: {data['pixel_count'].mean():.1f}")
            
            # Show some sample data
            print(f"\n📋 Sample data:")
            print(data[['date', 'albedo_mean', 'pixel_count']].head())
            
        else:
            print("⚠️ No data extracted - check date range or region")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_terra_aqua_fusion()