"""
Test script for Advanced QA Filtering Implementation
Compares standard vs advanced QA filtering approaches
"""

import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import ee
from src.workflows.melt_season import run_melt_season_analysis_williamson

def compare_qa_methods():
    """
    Compare standard vs advanced QA filtering for a small test period
    """
    print("🧪 TESTING ADVANCED QA FILTERING")
    print("=" * 80)
    
    # Initialize Earth Engine
    ee.Initialize()
    
    # Test with a small date range for comparison
    test_start_year = 2023
    test_end_year = 2023
    
    print("\n📊 1. RUNNING STANDARD QA ANALYSIS (Basic QA only)")
    print("-" * 60)
    results_standard = run_melt_season_analysis_williamson(
        start_year=test_start_year,
        end_year=test_end_year,
        use_advanced_qa=False
    )
    
    print("\n🔬 2. RUNNING ADVANCED QA ANALYSIS (Standard level)")
    print("-" * 60)
    results_advanced_standard = run_melt_season_analysis_williamson(
        start_year=test_start_year,
        end_year=test_end_year,
        use_advanced_qa=True,
        qa_level='standard'
    )
    
    print("\n⚡ 3. RUNNING ADVANCED QA ANALYSIS (Strict level)")
    print("-" * 60)
    results_advanced_strict = run_melt_season_analysis_williamson(
        start_year=test_start_year,
        end_year=test_end_year,
        use_advanced_qa=True,
        qa_level='strict'
    )
    
    # Compare results
    print("\n📈 COMPARISON RESULTS")
    print("=" * 80)
    
    if results_standard and 'time_series' in results_standard:
        df_standard = results_standard['time_series']
        print(f"Standard QA:       {len(df_standard)} observations")
        print(f"   Mean albedo:    {df_standard['albedo_mean'].mean():.4f}")
        print(f"   Std deviation:  {df_standard['albedo_mean'].std():.4f}")
    
    if results_advanced_standard and 'time_series' in results_advanced_standard:
        df_adv_std = results_advanced_standard['time_series']
        print(f"Advanced Standard: {len(df_adv_std)} observations")
        print(f"   Mean albedo:    {df_adv_std['albedo_mean'].mean():.4f}")
        print(f"   Std deviation:  {df_adv_std['albedo_mean'].std():.4f}")
    
    if results_advanced_strict and 'time_series' in results_advanced_strict:
        df_adv_strict = results_advanced_strict['time_series']
        print(f"Advanced Strict:   {len(df_adv_strict)} observations")
        print(f"   Mean albedo:    {df_adv_strict['albedo_mean'].mean():.4f}")
        print(f"   Std deviation:  {df_adv_strict['albedo_mean'].std():.4f}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 80)
    print("✅ Use 'standard' advanced QA for most analyses")
    print("🎯 Use 'strict' advanced QA for highest quality requirements")
    print("⚡ Use standard QA only for maximum data coverage")
    print("\n📊 Advanced QA filtering should improve:")
    print("   - Statistical robustness of Mann-Kendall tests")
    print("   - Reliability of Sen's slope estimates")
    print("   - Consistency with Williamson & Menounos (2021)")

if __name__ == "__main__":
    compare_qa_methods()