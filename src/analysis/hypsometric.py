"""
Hypsometric Analysis Module (Elevation-based Analysis)
Following Williamson & Menounos (2021) methodology
Analyzes albedo trends by elevation bands (±100m around median elevation)
"""

import pandas as pd
import numpy as np
from .statistics import mann_kendall_test, sens_slope_estimate, calculate_trend_statistics


def classify_elevation_bands(df, elevation_column='elevation', median_elevation=None):
    """
    Classify data into elevation bands relative to glacier median elevation
    Following Williamson & Menounos (2021): ±100m bands around median elevation
    
    Args:
        df: DataFrame with elevation data
        elevation_column: Column name for elevation data
        median_elevation: Median elevation of glacier (if None, calculated from data)
    
    Returns:
        DataFrame with added 'elevation_band' column
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Calculate median elevation if not provided
    if median_elevation is None:
        median_elevation = df[elevation_column].median()
    
    print(f"📏 Glacier median elevation: {median_elevation:.0f} m")
    
    # Define elevation bands (following Williamson methodology)
    def assign_elevation_band(elevation):
        """Assign elevation band based on distance from median"""
        diff = elevation - median_elevation
        
        if diff > 100:
            return 'above_median'  # > 100m above median
        elif diff < -100:
            return 'below_median'  # > 100m below median
        else:
            return 'near_median'   # ±100m of median
    
    # Apply classification
    df['elevation_band'] = df[elevation_column].apply(assign_elevation_band)
    
    # Count pixels in each band
    band_counts = df['elevation_band'].value_counts()
    print(f"📊 Elevation band distribution:")
    print(f"   Above median (>{median_elevation+100:.0f}m): {band_counts.get('above_median', 0)} pixels")
    print(f"   Near median ({median_elevation-100:.0f}-{median_elevation+100:.0f}m): {band_counts.get('near_median', 0)} pixels")
    print(f"   Below median (<{median_elevation-100:.0f}m): {band_counts.get('below_median', 0)} pixels")
    
    return df


def get_elevation_range(df, elevation_column):
    """Get elevation range for a dataset"""
    if df.empty:
        return None
    return {
        'min': df[elevation_column].min(),
        'max': df[elevation_column].max(),
        'mean': df[elevation_column].mean(),
        'median': df[elevation_column].median()
    }


def analyze_elevation_band_trends(band_data, value_column='albedo_mean', min_obs_per_year=5):
    """
    Analyze annual trends for a specific elevation band
    
    Args:
        band_data: DataFrame for one elevation band
        value_column: Column name for values to analyze
        min_obs_per_year: Minimum observations required per year
    
    Returns:
        dict: Trend analysis results for the band
    """
    if band_data.empty:
        return None
    
    # Calculate annual means
    annual_data = band_data.groupby('year')[value_column].agg(['mean', 'std', 'count']).reset_index()
    annual_data = annual_data[annual_data['count'] >= min_obs_per_year]
    
    if len(annual_data) < 4:
        return None
    
    years = annual_data['year'].values
    values = annual_data['mean'].values
    
    # Calculate trend statistics
    trend_stats = calculate_trend_statistics(values, years)
    
    # Add annual data to results
    if trend_stats:
        trend_stats['annual_data'] = annual_data
    
    return trend_stats


def analyze_hypsometric_trends(df, elevation_column='elevation', value_column='albedo_mean', 
                             median_elevation=None, min_obs_per_year=5):
    """
    Perform comprehensive hypsometric (elevation-based) trend analysis
    Following Williamson & Menounos (2021) methodology
    
    Args:
        df: DataFrame with elevation, year, and albedo data
        elevation_column: Column name for elevation
        value_column: Column name for values to analyze
        median_elevation: Glacier median elevation (calculated if None)
        min_obs_per_year: Minimum observations per year
    
    Returns:
        dict: Hypsometric trend analysis results by elevation band
    """
    if df.empty:
        print("❌ Empty dataset for hypsometric analysis")
        return {}
    
    print(f"\n🏔️  HYPSOMETRIC TREND ANALYSIS")
    print("=" * 60)
    print("Following Williamson & Menounos (2021) methodology")
    print("Elevation bands: ±100m around glacier median elevation")
    
    # Classify into elevation bands
    df_classified = classify_elevation_bands(df, elevation_column, median_elevation)
    
    # Analyze trends for each elevation band
    band_results = {}
    band_names = {
        'above_median': 'Above Median (>100m)',
        'near_median': 'Near Median (±100m)', 
        'below_median': 'Below Median (>100m)'
    }
    
    for band, band_name in band_names.items():
        band_data = df_classified[df_classified['elevation_band'] == band]
        
        if band_data.empty:
            print(f"\n⚠️  No data for {band_name} elevation band")
            continue
        
        print(f"\n🎯 Analyzing {band_name} elevation band:")
        print(f"   📊 {len(band_data)} total observations")
        
        # Perform annual trend analysis for this band
        band_trends = analyze_elevation_band_trends(band_data, value_column, min_obs_per_year)
        
        if band_trends:
            band_results[band] = {
                'band_name': band_name,
                'elevation_range': get_elevation_range(band_data, elevation_column),
                'n_observations': len(band_data),
                'trend_analysis': band_trends
            }
            
            # Print band-specific summary
            trend_info = band_trends['mann_kendall']
            sens_info = band_trends['sens_slope']
            
            print(f"   📈 Trend: {trend_info['trend'].replace('_', ' ').title()}")
            print(f"   📊 Sen's slope: {sens_info['slope_per_year']:.4f}/year")
            print(f"   🎯 P-value: {trend_info['p_value']:.4f}")
            
            if trend_info['p_value'] < 0.05:
                print(f"   ✅ SIGNIFICANT trend in {band_name}")
            else:
                print(f"   ⚠️  Non-significant trend in {band_name}")
        else:
            print(f"   ❌ Insufficient data for trend analysis in {band_name}")
    
    return band_results


def compare_elevation_bands(hypsometric_results):
    """
    Compare trends between elevation bands
    Following Williamson & Menounos findings on transient snowline
    
    Args:
        hypsometric_results: Results from analyze_hypsometric_trends()
    
    Returns:
        dict: Comparison analysis
    """
    if not hypsometric_results:
        return {}
    
    print(f"\n🔍 ELEVATION BAND COMPARISON")
    print("=" * 50)
    
    # Extract slopes for comparison
    slopes = {}
    significance = {}
    
    for band, results in hypsometric_results.items():
        if 'trend_analysis' in results:
            slopes[band] = results['trend_analysis']['sens_slope']['slope_per_year']
            significance[band] = results['trend_analysis']['mann_kendall']['p_value'] < 0.05
    
    if len(slopes) < 2:
        print("⚠️  Need at least 2 elevation bands for comparison")
        return {}
    
    # Find most negative trends (strongest declines)
    most_negative_band = min(slopes.keys(), key=lambda x: slopes[x])
    strongest_decline = slopes[most_negative_band]
    
    print(f"📉 Strongest albedo decline in: {hypsometric_results[most_negative_band]['band_name']}")
    print(f"   Slope: {strongest_decline:.4f}/year")
    
    # Check for "transient snowline" pattern (strongest decline near median)
    near_median_slope = slopes.get('near_median', 0)
    above_median_slope = slopes.get('above_median', 0)
    below_median_slope = slopes.get('below_median', 0)
    
    transient_snowline_pattern = False
    elevation_gradient_pattern = False
    
    if 'near_median' in slopes:
        # Classic transient snowline: strongest decline near median elevation
        if (near_median_slope < above_median_slope and 
            near_median_slope < below_median_slope):
            transient_snowline_pattern = True
    
    # Alternative pattern: elevation-dependent gradient
    # Stronger decline at lower elevations (more common in recent warming)
    if ('below_median' in slopes and 'above_median' in slopes and 
        below_median_slope < above_median_slope):
        elevation_gradient_pattern = True
    
    print(f"\n🎯 WILLIAMSON & MENOUNOS PATTERN CHECK:")
    
    if transient_snowline_pattern:
        print("✅ TRANSIENT SNOWLINE PATTERN DETECTED!")
        print("   Strongest decline near median elevation suggests rising snowline")
        print("   This matches Williamson & Menounos (2021) findings")
    elif elevation_gradient_pattern:
        print("🌡️ ELEVATION-DEPENDENT WARMING PATTERN DETECTED!")
        print("   Stronger decline at lower elevations")
        print("   Consistent with enhanced warming at lower glacier elevations")
        print("   This is also documented in recent climate change studies")
    else:
        print("❓ Pattern differs from typical hypsometric signatures")
    
    # Summary statistics
    comparison = {
        'slopes_by_band': slopes,
        'significance_by_band': significance,
        'strongest_decline_band': most_negative_band,
        'strongest_decline_value': strongest_decline,
        'transient_snowline_pattern': transient_snowline_pattern,
        'elevation_gradient_pattern': elevation_gradient_pattern,
        'interpretation': interpret_elevation_pattern(slopes)
    }
    
    return comparison


def interpret_elevation_pattern(slopes):
    """Interpret the elevation-based trend pattern"""
    if not slopes:
        return "Insufficient data for interpretation"
    
    # Get slopes for each band
    above = slopes.get('above_median', 0)
    near = slopes.get('near_median', 0)  
    below = slopes.get('below_median', 0)
    
    # Sort by magnitude of decline (most negative first)
    sorted_slopes = sorted([(band, slope) for band, slope in slopes.items()], key=lambda x: x[1])
    strongest_decline_band = sorted_slopes[0][0]
    
    if near < above and near < below:
        return "Transient snowline rise (strongest decline near median elevation)"
    elif below < near and below < above:
        return "Enhanced lower-elevation warming (strongest decline in ablation zone)"
    elif above < near and above < below:
        return "High-elevation sensitivity (strongest decline in accumulation zone)"
    elif abs(above - near) < 0.0005 and abs(near - below) < 0.0005:
        return "Uniform glacier-wide decline (similar trends across elevation)"
    else:
        return f"Complex pattern (strongest decline: {strongest_decline_band.replace('_', ' ')})" 