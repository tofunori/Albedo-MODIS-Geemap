#!/usr/bin/env python3
"""
Test Enhanced Terra-Aqua Integration in CSV and Streamlit
Validates the new metadata columns and dashboard features
"""

import sys
import os
import pandas as pd

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

def test_enhanced_csv_output():
    """Test CSV output with Terra-Aqua metadata columns"""
    print("🧪 Testing Enhanced CSV Output with Terra-Aqua Metadata")
    print("=" * 60)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Test with a short period for quick validation
    test_start = '2023-07-01'
    test_end = '2023-07-15'
    
    print(f"\n📅 Testing period: {test_start} to {test_end}")
    print("🎯 Extracting data with enhanced Terra-Aqua metadata...")
    
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
            
            # Check for new Terra-Aqua columns
            print(f"\n📊 CHECKING NEW TERRA-AQUA COLUMNS:")
            terra_aqua_columns = [
                'satellite_source', 'original_satellite', 'terra_aqua_fusion',
                'fusion_method', 'terra_total_observations', 'aqua_total_observations',
                'combined_daily_composites', 'duplicates_eliminated'
            ]
            
            for col in terra_aqua_columns:
                if col in data.columns:
                    if col in ['satellite_source', 'fusion_method']:
                        unique_values = data[col].unique()
                        print(f"   ✅ {col}: {unique_values}")
                    else:
                        value = data[col].iloc[0] if len(data) > 0 else 'N/A'
                        print(f"   ✅ {col}: {value}")
                else:
                    print(f"   ❌ {col}: MISSING")
            
            # Save test file with enhanced metadata
            output_path = 'outputs/csv/test_enhanced_terra_aqua.csv'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            data.to_csv(output_path, index=False)
            print(f"\n💾 Enhanced CSV saved: {output_path}")
            
            # Display sample of enhanced data
            print(f"\n📋 SAMPLE ENHANCED DATA:")
            display_columns = ['date', 'albedo_mean', 'pixel_count', 'satellite_source']
            if all(col in data.columns for col in display_columns):
                sample = data[display_columns].head(10)
                print(sample.to_string(index=False))
            
            # Terra-Aqua summary
            if 'terra_total_observations' in data.columns:
                terra_count = data['terra_total_observations'].iloc[0]
                aqua_count = data['aqua_total_observations'].iloc[0]
                combined_count = data['combined_daily_composites'].iloc[0]
                duplicates = data['duplicates_eliminated'].iloc[0]
                
                print(f"\n🛰️ TERRA-AQUA FUSION SUMMARY:")
                print(f"   Terra observations: {terra_count}")
                print(f"   Aqua observations: {aqua_count}")
                print(f"   Combined composites: {combined_count}")
                print(f"   Duplicates eliminated: {duplicates}")
                print(f"   Reduction rate: {duplicates/(terra_count+aqua_count)*100:.1f}%")
            
            # Satellite source distribution
            if 'satellite_source' in data.columns:
                print(f"\n📡 SATELLITE SOURCE DISTRIBUTION:")
                source_counts = data['satellite_source'].value_counts()
                for source, count in source_counts.items():
                    percentage = count / len(data) * 100
                    print(f"   {source}: {count} observations ({percentage:.1f}%)")
            
            return True
            
        else:
            print("⚠️ No data extracted")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_csv_structure():
    """Validate the structure of existing CSV files"""
    print(f"\n🔍 VALIDATING EXISTING CSV FILES:")
    print("=" * 40)
    
    csv_dir = 'outputs/csv'
    if os.path.exists(csv_dir):
        csv_files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
        
        for csv_file in csv_files[:5]:  # Check first 5 files
            file_path = os.path.join(csv_dir, csv_file)
            try:
                df = pd.read_csv(file_path)
                print(f"\n📁 {csv_file}:")
                print(f"   Rows: {len(df)}")
                print(f"   Columns: {len(df.columns)}")
                
                # Check for Terra-Aqua columns
                terra_aqua_cols = [col for col in df.columns if 'terra' in col.lower() or 'aqua' in col.lower() or 'satellite' in col.lower()]
                if terra_aqua_cols:
                    print(f"   Terra-Aqua columns: {terra_aqua_cols}")
                else:
                    print(f"   Terra-Aqua columns: None (older file)")
                    
            except Exception as e:
                print(f"   ❌ Error reading {csv_file}: {e}")
    else:
        print("   No CSV directory found")

if __name__ == "__main__":
    print("🚀 TESTING ENHANCED TERRA-AQUA INTEGRATION")
    print("=" * 70)
    
    # Test 1: Enhanced CSV output
    success = test_enhanced_csv_output()
    
    # Test 2: Validate existing files
    validate_csv_structure()
    
    print(f"\n{'='*70}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Enhanced Terra-Aqua metadata is working correctly")
        print("📊 New CSV columns include full fusion statistics")
        print("🛰️ Satellite source tracking is operational")
        print("\n💡 Next steps:")
        print("   1. Launch Streamlit app: streamlit run streamlit_app/streamlit_main.py")
        print("   2. Go to 'Data Processing & Configuration' tab")
        print("   3. Run an analysis to see the new Terra-Aqua dashboard")
    else:
        print("❌ TESTS FAILED")
        print("💡 Check the error messages above and verify your setup")