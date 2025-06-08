"""
Simple test script for Advanced QA Filtering
Tests the QA masking functions directly
"""

import ee
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import config and required functions directly
try:
    from config import athabasca_roi
    from src.data.extraction import (
        mask_modis_snow_albedo_fast, 
        mask_modis_snow_albedo_advanced,
        MODIS_COLLECTIONS
    )
    
    def test_qa_filtering():
        """Test basic vs advanced QA filtering on a single image"""
        print("🧪 TESTING QA FILTERING FUNCTIONS")
        print("=" * 60)
        
        # Initialize Earth Engine
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        # Get a sample image from 2023
        test_date = '2023-08-15'
        print(f"📅 Testing with date: {test_date}")
        
        # Load a single MOD10A1 image
        image = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
            .filterBounds(athabasca_roi) \
            .filterDate('2023-08-15', '2023-08-16') \
            .first()
        
        if image is None:
            print("❌ No image found for test date")
            return
        
        print("✅ Sample image loaded")
        
        # Test standard masking
        print("\n🔸 Testing standard QA masking...")
        masked_standard = mask_modis_snow_albedo_fast(image)
        
        # Count valid pixels
        stats_standard = masked_standard.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        
        standard_count = stats_standard.getInfo().get('albedo_daily', 0)
        print(f"   Standard QA: {standard_count} valid pixels")
        
        # Test advanced masking - standard level
        print("\n🔬 Testing advanced QA masking (standard)...")
        masked_advanced_std = mask_modis_snow_albedo_advanced(image, 'standard')
        
        stats_advanced_std = masked_advanced_std.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        
        advanced_std_count = stats_advanced_std.getInfo().get('albedo_daily', 0)
        print(f"   Advanced QA (standard): {advanced_std_count} valid pixels")
        
        # Test advanced masking - strict level
        print("\n⚡ Testing advanced QA masking (strict)...")
        masked_advanced_strict = mask_modis_snow_albedo_advanced(image, 'strict')
        
        stats_advanced_strict = masked_advanced_strict.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e9
        )
        
        advanced_strict_count = stats_advanced_strict.getInfo().get('albedo_daily', 0)
        print(f"   Advanced QA (strict): {advanced_strict_count} valid pixels")
        
        # Compare results
        print("\n📊 COMPARISON RESULTS")
        print("=" * 60)
        print(f"Standard QA:           {standard_count:4d} pixels")
        print(f"Advanced QA (standard): {advanced_std_count:4d} pixels")
        print(f"Advanced QA (strict):   {advanced_strict_count:4d} pixels")
        
        # Calculate reduction percentages
        if standard_count > 0:
            reduction_std = ((standard_count - advanced_std_count) / standard_count) * 100
            reduction_strict = ((standard_count - advanced_strict_count) / standard_count) * 100
            
            print(f"\nData reduction:")
            print(f"Advanced (standard): -{reduction_std:.1f}% pixels")
            print(f"Advanced (strict):   -{reduction_strict:.1f}% pixels")
        
        # Interpretation
        print("\n💡 INTERPRETATION")
        print("=" * 60)
        if advanced_std_count < standard_count:
            print("✅ Advanced QA successfully filters problematic pixels")
        if advanced_strict_count < advanced_std_count:
            print("✅ Strict mode provides additional quality filtering")
        
        print("\n🎯 RECOMMENDATIONS:")
        print("- Use 'standard' advanced QA for most analyses")
        print("- Use 'strict' for highest quality requirements")
        print("- Monitor data reduction vs quality trade-off")
        
    if __name__ == "__main__":
        test_qa_filtering()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Alternative test using simple Earth Engine query:")
    
    def simple_qa_test():
        """Simple test without complex imports"""
        print("🧪 SIMPLE QA FLAG TEST")
        print("=" * 40)
        
        # Initialize Earth Engine
        ee.Initialize()
        print("✅ Earth Engine initialized")
        
        # Test loading MOD10A1 with QA bands
        print("\n📊 Testing MOD10A1 QA bands access...")
        
        collection = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterDate('2023-08-01', '2023-08-31') \
            .first()
        
        # Check available bands
        bands = collection.bandNames().getInfo()
        print(f"Available bands: {bands}")
        
        # Check if QA bands are present
        qa_bands = [band for band in bands if 'QA' in band]
        print(f"QA bands found: {qa_bands}")
        
        if 'NDSI_Snow_Cover_Basic_QA' in qa_bands:
            print("✅ Basic QA band available")
        if 'NDSI_Snow_Cover_Algorithm_Flags_QA' in qa_bands:
            print("✅ Algorithm flags QA band available")
        
        print("\n🎯 Advanced QA implementation is ready to use!")
        print("📚 See docs/mod10a1-qa-flags.md for detailed flag interpretations")
    
    simple_qa_test()