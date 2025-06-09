#!/usr/bin/env python3
"""
Compare Terra-Aqua Fusion vs Simple Merge
Shows albedo differences between methodologies
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import ee

try:
    from data.extraction import combine_terra_aqua_literature_method
    from config import athabasca_roi, MODIS_COLLECTIONS
    print("✅ Successfully imported functions")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def mask_modis_simple(image):
    """Simple masking for comparison"""
    albedo = image.select('Snow_Albedo_Daily_Tile')
    qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    good_quality = qa.lte(1)
    
    scaled = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])

def extract_with_simple_merge(start_date, end_date):
    """Extract using simple merge (old method)"""
    print("🔄 Extracting with SIMPLE MERGE...")
    
    mod_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(mask_modis_simple)
    
    myd_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(mask_modis_simple)
    
    # Simple merge (old method)
    collection = mod_col.merge(myd_col).sort('system:time_start')
    
    terra_count = mod_col.size().getInfo()
    aqua_count = myd_col.size().getInfo()
    merged_count = collection.size().getInfo()
    
    print(f"   📊 Simple Merge Statistics:")
    print(f"      - Terra: {terra_count} observations")
    print(f"      - Aqua: {aqua_count} observations")
    print(f"      - Merged total: {merged_count} observations")
    
    return collection, merged_count

def extract_with_literature_fusion(start_date, end_date):
    """Extract using literature-based fusion (new method)"""
    print("🔬 Extracting with LITERATURE FUSION...")
    
    mod_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(mask_modis_simple)
    
    myd_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(mask_modis_simple)
    
    # Literature-based fusion (new method)
    collection = combine_terra_aqua_literature_method(mod_col, myd_col)
    
    terra_count = mod_col.size().getInfo()
    aqua_count = myd_col.size().getInfo()
    fused_count = collection.size().getInfo()
    
    print(f"   📊 Literature Fusion Statistics:")
    print(f"      - Terra: {terra_count} observations")
    print(f"      - Aqua: {aqua_count} observations")
    print(f"      - Fused daily: {fused_count} composites")
    print(f"      - Eliminated: {terra_count + aqua_count - fused_count} duplicates")
    
    return collection, fused_count

def extract_statistics(collection, method_name):
    """Extract albedo statistics from collection"""
    def extract_stats(image):
        albedo = image.select('albedo_daily')
        stats = albedo.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=500,
            maxPixels=1e6
        )
        
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'timestamp': image.date().millis(),
            'albedo_mean': stats.get('albedo_daily_mean'),
            'pixel_count': stats.get('albedo_daily_count'),
            'method': method_name
        })
    
    time_series = collection.map(extract_stats)
    data_list = time_series.getInfo()['features']
    
    records = []
    for feature in data_list:
        props = feature['properties']
        if props.get('albedo_mean') is not None and props.get('pixel_count', 0) > 0:
            records.append(props)
    
    return pd.DataFrame(records)

def compare_methods():
    """Compare both extraction methods"""
    print("🆚 COMPARING TERRA-AQUA FUSION vs SIMPLE MERGE")
    print("=" * 60)
    
    # Initialize Earth Engine
    try:
        ee.Initialize()
        print("✅ Earth Engine initialized")
    except Exception as e:
        print(f"❌ EE initialization failed: {e}")
        return
    
    # Test period - longer for better comparison
    test_start = '2023-07-01'
    test_end = '2023-08-31'  # 2 months
    
    print(f"\n📅 Comparison period: {test_start} to {test_end}")
    print("🎯 Extracting with both methods...\n")
    
    try:
        # Method 1: Simple Merge
        collection_merge, count_merge = extract_with_simple_merge(test_start, test_end)
        df_merge = extract_statistics(collection_merge, 'Simple Merge')
        
        print(f"   ✅ Simple merge: {len(df_merge)} valid observations\n")
        
        # Method 2: Literature Fusion
        collection_fusion, count_fusion = extract_with_literature_fusion(test_start, test_end)
        df_fusion = extract_statistics(collection_fusion, 'Literature Fusion')
        
        print(f"   ✅ Literature fusion: {len(df_fusion)} valid observations\n")
        
        # Compare results
        print("📊 COMPARISON RESULTS:")
        print("=" * 40)
        
        if not df_merge.empty and not df_fusion.empty:
            # Overall statistics
            merge_mean = df_merge['albedo_mean'].mean()
            fusion_mean = df_fusion['albedo_mean'].mean()
            
            merge_std = df_merge['albedo_mean'].std()
            fusion_std = df_fusion['albedo_mean'].std()
            
            print(f"📈 ALBEDO STATISTICS:")
            print(f"   Simple Merge   : Mean = {merge_mean:.4f} ± {merge_std:.4f}")
            print(f"   Literature Fusion: Mean = {fusion_mean:.4f} ± {fusion_std:.4f}")
            print(f"   Difference     : {fusion_mean - merge_mean:+.4f}")
            
            print(f"\n📊 OBSERVATION COUNT:")
            print(f"   Simple Merge   : {len(df_merge)} observations")
            print(f"   Literature Fusion: {len(df_fusion)} observations")
            print(f"   Difference     : {len(df_fusion) - len(df_merge):+d}")
            
            # Daily comparison for overlapping dates
            df_merge['date'] = pd.to_datetime(df_merge['date'])
            df_fusion['date'] = pd.to_datetime(df_fusion['date'])
            
            # Find common dates
            common_dates = set(df_merge['date']).intersection(set(df_fusion['date']))
            
            if common_dates:
                print(f"\n🗓️ DAILY COMPARISON ({len(common_dates)} common dates):")
                
                merge_common = df_merge[df_merge['date'].isin(common_dates)].sort_values('date')
                fusion_common = df_fusion[df_fusion['date'].isin(common_dates)].sort_values('date')
                
                # Merge for comparison
                comparison = pd.merge(
                    merge_common[['date', 'albedo_mean']], 
                    fusion_common[['date', 'albedo_mean']], 
                    on='date', 
                    suffixes=('_merge', '_fusion')
                )
                
                comparison['difference'] = comparison['albedo_mean_fusion'] - comparison['albedo_mean_merge']
                
                print(f"   Average daily difference: {comparison['difference'].mean():+.4f}")
                print(f"   Max positive difference : {comparison['difference'].max():+.4f}")
                print(f"   Max negative difference : {comparison['difference'].min():+.4f}")
                
                # Show some examples
                print(f"\n📋 SAMPLE DAILY COMPARISONS:")
                sample = comparison.head(10)
                for _, row in sample.iterrows():
                    print(f"   {row['date'].strftime('%Y-%m-%d')}: "
                          f"Merge={row['albedo_mean_merge']:.3f}, "
                          f"Fusion={row['albedo_mean_fusion']:.3f}, "
                          f"Diff={row['difference']:+.3f}")
            
            # Save results
            df_merge.to_csv('outputs/csv/comparison_simple_merge.csv', index=False)
            df_fusion.to_csv('outputs/csv/comparison_literature_fusion.csv', index=False)
            
            print(f"\n💾 Results saved:")
            print(f"   outputs/csv/comparison_simple_merge.csv")
            print(f"   outputs/csv/comparison_literature_fusion.csv")
            
        else:
            print("❌ No valid data extracted for comparison")
            
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_methods()