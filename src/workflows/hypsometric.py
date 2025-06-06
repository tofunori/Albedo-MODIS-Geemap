"""
Hypsometric Analysis Workflow
Complete workflow for elevation-based glacier albedo analysis
Following Williamson & Menounos (2021) methodology
"""

import pandas as pd
import numpy as np
import ee
from datetime import datetime
from config import athabasca_roi
from paths import get_output_path

# Import analysis modules
from analysis.hypsometric import analyze_hypsometric_trends, compare_elevation_bands
from analysis.temporal import analyze_annual_trends
from visualization.plots import create_hypsometric_plot
from data.extraction import extract_melt_season_data_yearly_with_elevation

def run_hypsometric_analysis_williamson(start_year=2015, end_year=2024, scale=500):
    """
    Complete hypsometric analysis workflow following Williamson & Menounos (2021)
    Analyzes albedo trends by elevation bands (±100m around median elevation)
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
        scale: Spatial resolution in meters
    
    Returns:
        dict: Complete hypsometric analysis results
    """
    print("🏔️  ATHABASCA GLACIER HYPSOMETRIC ANALYSIS")
    print("=" * 80)
    print(f"📊 Using Williamson & Menounos (2021) methodology")
    print(f"🗓️  Period: {start_year}-{end_year}")
    print(f"📏 Resolution: {scale}m")
    print(f"🎯 Method: ±100m elevation bands around glacier median")
    
    # Initialize Earth Engine
    ee.Initialize()
    
    # Extract data with elevation
    print(f"\n⏳ Extracting MODIS albedo data with elevation...")
    print(f"🏔️  Including SRTM elevation data for each pixel")
    
    df = extract_melt_season_data_yearly_with_elevation(
        start_year=start_year, 
        end_year=end_year, 
        scale=scale
    )
    
    if df.empty:
        print("❌ No data extracted. Check your date range and region.")
        return None
    
    # Export raw data with elevation
    csv_path = get_output_path('athabasca_hypsometric_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Raw data with elevation exported: {csv_path}")
    
    # Calculate glacier-wide median elevation
    median_elevation = df['elevation'].median()
    print(f"\n📏 Glacier median elevation: {median_elevation:.0f} m")
    
    # Perform hypsometric analysis
    print(f"\n🔍 Analyzing trends by elevation band...")
    hypsometric_results = analyze_hypsometric_trends(
        df, 
        elevation_column='elevation',
        value_column='albedo_mean',
        median_elevation=median_elevation
    )
    
    if not hypsometric_results:
        print("❌ Hypsometric analysis failed.")
        return None
    
    # Compare elevation bands
    elevation_comparison = compare_elevation_bands(hypsometric_results)
    
    # Create visualization
    create_hypsometric_plot(hypsometric_results, elevation_comparison, df)
    
    # Export results summary
    summary_path = get_output_path('athabasca_hypsometric_results.csv')
    
    # Create summary dataframe
    summary_data = []
    for band, results in hypsometric_results.items():
        if 'trend_analysis' in results:
            trend = results['trend_analysis']
            summary_data.append({
                'elevation_band': results['band_name'],
                'elevation_range_min': results['elevation_range']['min'],
                'elevation_range_max': results['elevation_range']['max'],
                'n_observations': results['n_observations'],
                'trend': trend['mann_kendall']['trend'],
                'p_value': trend['mann_kendall']['p_value'],
                'sens_slope_per_year': trend['sens_slope']['slope_per_year'],
                'percent_change_per_year': trend['annual_change']['percent_per_year'],
                'total_change': trend['total_change']['absolute'],
                'significance': 'SIGNIFICANT' if trend['mann_kendall']['p_value'] < 0.05 else 'Not significant'
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_path, index=False)
    print(f"💾 Hypsometric results exported: {summary_path}")
    
    # Also create overall temporal plot with elevation bands
    overall_trends = analyze_annual_trends(df, 'albedo_mean')
    if overall_trends:
        from visualization.plots import create_melt_season_plot_with_elevation
        create_melt_season_plot_with_elevation(
            overall_trends, 
            df, 
            'athabasca_melt_season_with_elevation.png'
        )
    
    # Print key findings
    print_hypsometric_findings(hypsometric_results, elevation_comparison)
    
    print(f"\n🎉 HYPSOMETRIC ANALYSIS COMPLETE!")
    print(f"Files generated:")
    print(f"   📊 Hypsometric visualization: figures/athabasca_hypsometric_analysis.png")
    print(f"   📊 Temporal with elevation: figures/athabasca_melt_season_with_elevation.png")
    print(f"   💾 Raw data: {csv_path}")
    print(f"   💾 Results summary: {summary_path}")
    
    return {
        'hypsometric_results': hypsometric_results,
        'elevation_comparison': elevation_comparison,
        'median_elevation': median_elevation,
        'overall_trends': overall_trends
    }

def print_hypsometric_findings(hypsometric_results, elevation_comparison):
    """Print key hypsometric findings"""
    print(f"\n🎯 KEY HYPSOMETRIC FINDINGS:")
    print("=" * 50)
    
    # Trend by elevation band
    print(f"\n📊 TRENDS BY ELEVATION BAND:")
    for band, results in hypsometric_results.items():
        if 'trend_analysis' in results:
            trend = results['trend_analysis']
            print(f"\n   {results['band_name']}:")
            print(f"   Elevation range: {results['elevation_range']['min']:.0f}-{results['elevation_range']['max']:.0f} m")
            print(f"   Trend: {trend['sens_slope']['slope_per_year']:.4f}/year")
            print(f"   Significance: {'YES' if trend['mann_kendall']['p_value'] < 0.05 else 'NO'} (p={trend['mann_kendall']['p_value']:.3f})")
    
    # Pattern interpretation
    if elevation_comparison:
        print(f"\n🏔️  ELEVATION PATTERN INTERPRETATION:")
        print(f"   {elevation_comparison['interpretation']}")
        
        if elevation_comparison['transient_snowline_pattern']:
            print(f"\n   ✅ WILLIAMSON & MENOUNOS PATTERN CONFIRMED!")
            print(f"   The strongest albedo decline occurs near the median elevation,")
            print(f"   indicating a rising transient snowline during the melt season.")
        elif elevation_comparison['elevation_gradient_pattern']:
            print(f"\n   🌡️  ELEVATION-DEPENDENT WARMING DETECTED!")
            print(f"   Stronger decline at lower elevations suggests")
            print(f"   enhanced warming in the ablation zone.") 