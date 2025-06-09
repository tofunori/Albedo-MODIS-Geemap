#!/usr/bin/env python3
"""
Quick test to see Terra-Aqua fusion statistics
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

def test_fusion_stats():
    """Quick test to see fusion statistics"""
    print("🧪 Testing Terra-Aqua Fusion Statistics")
    print("=" * 50)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Test with a medium period
    test_start = '2023-07-01'
    test_end = '2023-07-31'  # 1 month
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    print("🎯 Looking for Terra-Aqua fusion statistics...")
    
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
            print("📊 Check the console output above for Terra-Aqua statistics!")
        else:
            print("⚠️ No data extracted")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_fusion_stats()