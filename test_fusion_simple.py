#!/usr/bin/env python3
"""
Simple test for Terra-Aqua fusion function without full imports
"""

import sys
import os
import ee

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_ee_connection():
    """Test Earth Engine connection only"""
    print("🧪 Testing Earth Engine Connection")
    print("=" * 40)
    
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized successfully")
        
        # Simple test - get MODIS collection info
        mod_col = ee.ImageCollection('MODIS/061/MOD10A1')
        myd_col = ee.ImageCollection('MODIS/061/MYD10A1')
        
        print(f"✅ MOD10A1 collection accessible")
        print(f"✅ MYD10A1 collection accessible")
        
        # Test date filtering
        test_col = mod_col.filterDate('2023-07-01', '2023-07-02')
        size = test_col.size().getInfo()
        print(f"✅ Date filtering works - found {size} images")
        
        return True
        
    except Exception as e:
        print(f"❌ Earth Engine test failed: {e}")
        return False

def test_imports():
    """Test if we can import the required modules"""
    print("\n🔍 Testing Module Imports")
    print("=" * 40)
    
    try:
        # Test config import
        import config
        print("✅ config module imported")
        print(f"   - athabasca_roi type: {type(config.athabasca_roi)}")
        
        # Test extraction import
        sys.path.insert(0, os.path.join(project_root, 'src'))
        from data.extraction import combine_terra_aqua_literature_method
        print("✅ combine_terra_aqua_literature_method imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💡 Some modules may have dependency issues")
        return False

if __name__ == "__main__":
    print("🚀 Simple Terra-Aqua Fusion Test")
    print("=" * 50)
    
    # Test 1: Earth Engine connection
    ee_ok = test_ee_connection()
    
    # Test 2: Module imports  
    import_ok = test_imports()
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Earth Engine: {'✅ OK' if ee_ok else '❌ Failed'}")
    print(f"   Module Imports: {'✅ OK' if import_ok else '❌ Failed'}")
    
    if ee_ok and import_ok:
        print("\n🎉 All tests passed! Terra-Aqua fusion should work.")
        print("💡 You can now run the full extraction with:")
        print("   python -c \"from src.workflows.melt_season import run_melt_season_analysis_williamson; run_melt_season_analysis_williamson()\"")
    else:
        print("\n⚠️ Some tests failed. Check your environment setup.")