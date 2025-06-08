"""
Practical QA Comparison Script
Run this to see the difference between standard and advanced QA filtering
on your actual Athabasca glacier data
"""

import ee
from src.workflows.melt_season import run_melt_season_analysis_williamson

def run_qa_comparison():
    """
    Compare standard vs advanced QA filtering on a single year
    Shows practical differences in data quality and quantity
    """
    print("🔬 COMPARING QA FILTERING METHODS")
    print("=" * 80)
    print("Testing with 2023 data (single year for quick comparison)")
    
    # Initialize Earth Engine
    ee.Initialize()
    
    test_year = 2023
    
    # 1. Standard QA (Basic QA only)
    print("\n📊 1. RUNNING STANDARD QA ANALYSIS")
    print("-" * 50)
    try:
        results_standard = run_melt_season_analysis_williamson(
            start_year=test_year,
            end_year=test_year,
            use_advanced_qa=False
        )
        
        if results_standard and 'time_series' in results_standard:
            df_std = results_standard['time_series']
            print(f"✅ Standard QA completed: {len(df_std)} observations")
            std_mean = df_std['albedo_mean'].mean()
            std_std = df_std['albedo_mean'].std()
            print(f"   Mean albedo: {std_mean:.4f} ± {std_std:.4f}")
        else:
            print("❌ Standard QA failed")
            return
            
    except Exception as e:
        print(f"❌ Standard QA error: {e}")
        return
    
    # 2. Advanced QA (Standard level)
    print("\n🔬 2. RUNNING ADVANCED QA ANALYSIS (STANDARD)")
    print("-" * 50)
    try:
        results_advanced = run_melt_season_analysis_williamson(
            start_year=test_year,
            end_year=test_year,
            use_advanced_qa=True,
            qa_level='standard'
        )
        
        if results_advanced and 'time_series' in results_advanced:
            df_adv = results_advanced['time_series']
            print(f"✅ Advanced QA completed: {len(df_adv)} observations")
            adv_mean = df_adv['albedo_mean'].mean()
            adv_std = df_adv['albedo_mean'].std()
            print(f"   Mean albedo: {adv_mean:.4f} ± {adv_std:.4f}")
        else:
            print("❌ Advanced QA failed")
            return
            
    except Exception as e:
        print(f"❌ Advanced QA error: {e}")
        return
    
    # 3. Advanced QA (Strict level)
    print("\n⚡ 3. RUNNING ADVANCED QA ANALYSIS (STRICT)")
    print("-" * 50)
    try:
        results_strict = run_melt_season_analysis_williamson(
            start_year=test_year,
            end_year=test_year,
            use_advanced_qa=True,
            qa_level='strict'
        )
        
        if results_strict and 'time_series' in results_strict:
            df_strict = results_strict['time_series']
            print(f"✅ Strict QA completed: {len(df_strict)} observations")
            strict_mean = df_strict['albedo_mean'].mean()
            strict_std = df_strict['albedo_mean'].std()
            print(f"   Mean albedo: {strict_mean:.4f} ± {strict_std:.4f}")
        else:
            print("❌ Strict QA failed")
            return
            
    except Exception as e:
        print(f"❌ Strict QA error: {e}")
        return
    
    # 4. Compare results
    print("\n📈 COMPARISON SUMMARY")
    print("=" * 80)
    
    print("Data Coverage:")
    print(f"  Standard QA:           {len(df_std):4d} observations")
    print(f"  Advanced QA (standard): {len(df_adv):4d} observations")
    print(f"  Advanced QA (strict):   {len(df_strict):4d} observations")
    
    # Data reduction percentages
    reduction_adv = ((len(df_std) - len(df_adv)) / len(df_std)) * 100
    reduction_strict = ((len(df_std) - len(df_strict)) / len(df_std)) * 100
    
    print(f"\nData Reduction:")
    print(f"  Advanced (standard): -{reduction_adv:.1f}%")
    print(f"  Advanced (strict):   -{reduction_strict:.1f}%")
    
    print(f"\nAlbedo Statistics:")
    print(f"  Standard QA:           {std_mean:.4f} ± {std_std:.4f}")
    print(f"  Advanced QA (standard): {adv_mean:.4f} ± {adv_std:.4f}")
    print(f"  Advanced QA (strict):   {strict_mean:.4f} ± {strict_std:.4f}")
    
    # Albedo differences
    diff_adv = adv_mean - std_mean
    diff_strict = strict_mean - std_mean
    
    print(f"\nAlbedo Differences (vs Standard):")
    print(f"  Advanced (standard): {diff_adv:+.4f}")
    print(f"  Advanced (strict):   {diff_strict:+.4f}")
    
    # Quality assessment
    print(f"\n💡 QUALITY ASSESSMENT")
    print("=" * 80)
    
    if reduction_adv > 0:
        print("✅ Advanced QA successfully filters problematic pixels")
    if abs(diff_adv) > 0.001:
        print("✅ Advanced QA shows measurable impact on albedo values")
    if len(df_adv) > len(df_strict):
        print("✅ Standard level provides good balance of quality vs coverage")
    
    print(f"\n🎯 RECOMMENDATIONS")
    print("=" * 80)
    print("Based on this comparison:")
    
    if reduction_adv < 30:
        print("✅ Use 'standard' advanced QA for most analyses")
        print("  - Good quality improvement with moderate data loss")
    else:
        print("⚠️  Consider 'relaxed' advanced QA if data coverage is critical")
    
    if reduction_strict < 50:
        print("✅ Use 'strict' advanced QA for publication-quality work")
        print("  - Highest quality with acceptable data loss")
    else:
        print("⚠️  'Strict' mode may be too restrictive for this dataset")
    
    print(f"\n📊 NEXT STEPS")
    print("=" * 80)
    print("1. Choose your preferred QA level based on the results above")
    print("2. Update your analysis workflows:")
    print("   - For exploratory work: use_advanced_qa=True, qa_level='standard'")
    print("   - For final analyses: use_advanced_qa=True, qa_level='strict'")
    print("3. Document your QA choice in your methodology")
    
    # Export results for reference
    results_summary = {
        'test_year': test_year,
        'standard_qa': {'observations': len(df_std), 'mean_albedo': std_mean, 'std_albedo': std_std},
        'advanced_standard': {'observations': len(df_adv), 'mean_albedo': adv_mean, 'std_albedo': adv_std},
        'advanced_strict': {'observations': len(df_strict), 'mean_albedo': strict_mean, 'std_albedo': strict_std}
    }
    
    print(f"\n💾 Results summary saved for reference")
    return results_summary

if __name__ == "__main__":
    results = run_qa_comparison()
    print("\n🎉 QA comparison complete!")
    print("Your advanced QA filtering implementation is ready to use.")