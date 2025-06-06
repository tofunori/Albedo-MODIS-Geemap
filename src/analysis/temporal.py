"""
Temporal Analysis Module for MODIS Albedo Data
Handles monthly, annual, and fire impact analyses
"""

import pandas as pd
import numpy as np
from .statistics import mann_kendall_test, sens_slope_estimate, calculate_trend_statistics


def analyze_annual_trends(df, value_column='albedo_mean', min_obs_per_year=5):
    """
    Perform comprehensive annual trend analysis
    
    Args:
        df: DataFrame with date, year, and albedo data
        value_column: Column name for values to analyze
        min_obs_per_year: Minimum observations required per year
    
    Returns:
        dict: Complete trend analysis results
    """
    if df.empty:
        return None
    
    print(f"\n🔍 ANNUAL TREND ANALYSIS")
    print("=" * 50)
    
    # Calculate annual means
    annual_data = df.groupby('year')[value_column].agg(['mean', 'std', 'count']).reset_index()
    annual_data = annual_data[annual_data['count'] >= min_obs_per_year]
    
    if len(annual_data) < 4:
        print(f"❌ Insufficient years for trend analysis (need ≥4, have {len(annual_data)})")
        return None
    
    years = annual_data['year'].values
    values = annual_data['mean'].values
    
    print(f"📊 Analysis period: {years.min()}-{years.max()} ({len(years)} years)")
    print(f"📊 Mean value: {values.mean():.3f} ± {values.std():.3f}")
    
    # Calculate comprehensive statistics
    results = calculate_trend_statistics(values, years)
    results['annual_data'] = annual_data
    
    # Print results
    print(f"\n📈 TREND RESULTS:")
    print(f"   Trend direction: {results['mann_kendall']['trend'].replace('_', ' ').title()}")
    print(f"   Mann-Kendall p-value: {results['mann_kendall']['p_value']:.4f}")
    print(f"   Kendall's tau: {results['mann_kendall']['tau']:.3f}")
    print(f"   Sen's slope: {results['change_per_year']:.4f}/year ({results['change_percent_per_year']:.2f}%/year)")
    print(f"   Total change ({results['period']}): {results['total_change']:.3f} ({results['total_percent_change']:.1f}%)")
    
    # Statistical significance
    if results['mann_kendall']['p_value'] < 0.05:
        print(f"   ✅ STATISTICALLY SIGNIFICANT trend detected!")
    else:
        print(f"   ⚠️  Trend not statistically significant (p > 0.05)")
    
    return results


def analyze_monthly_trends(df, months=[6, 7, 8, 9], value_column='albedo_mean'):
    """
    Analyze trends for specific months separately
    
    Args:
        df: DataFrame with month, year, and value data
        months: List of months to analyze (default: melt season)
        value_column: Column name for values
    
    Returns:
        dict: Monthly trend results
    """
    if df.empty:
        return {}
    
    print(f"\n📅 MONTHLY TREND ANALYSIS")
    print("=" * 40)
    
    month_names = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                   5: 'May', 6: 'June', 7: 'July', 8: 'August',
                   9: 'September', 10: 'October', 11: 'November', 12: 'December'}
    
    monthly_results = {}
    
    for month in months:
        month_data = df[df['month'] == month]
        if month_data.empty:
            continue
        
        print(f"\n🗓️  {month_names[month]} Analysis:")
        
        # Annual means for this month
        annual_monthly = month_data.groupby('year')[value_column].agg(['mean', 'count']).reset_index()
        annual_monthly = annual_monthly[annual_monthly['count'] >= 3]  # At least 3 obs per month
        
        if len(annual_monthly) < 4:
            print(f"   ⚠️ Insufficient data (need ≥4 years, have {len(annual_monthly)})")
            continue
        
        years = annual_monthly['year'].values
        values = annual_monthly['mean'].values
        
        # Calculate trend statistics
        stats = calculate_trend_statistics(values, years)
        stats['month_name'] = month_names[month]
        stats['annual_data'] = annual_monthly
        
        print(f"   📊 Period: {stats['period']} ({stats['n_years']} years)")
        print(f"   📈 Trend: {stats['mann_kendall']['trend'].replace('_', ' ')}")
        print(f"   📉 Change: {stats['change_percent_per_year']:.2f}%/year (p={stats['mann_kendall']['p_value']:.3f})")
        
        if stats['mann_kendall']['p_value'] < 0.05:
            print(f"   ✅ Statistically significant!")
        else:
            print(f"   ⚠️  Not significant")
        
        monthly_results[month] = stats
    
    return monthly_results


def analyze_fire_impact(df, fire_years=[2017, 2018, 2021, 2023], value_column='albedo_mean'):
    """
    Analyze the impact of fire years on albedo values
    
    Args:
        df: DataFrame with year and albedo data
        fire_years: List of years with major fires
        value_column: Column name for values
    
    Returns:
        dict: Fire impact analysis results
    """
    if df.empty:
        return {}
    
    print(f"\n🔥 FIRE IMPACT ANALYSIS")
    print("=" * 40)
    print(f"Fire years: {', '.join(map(str, fire_years))}")
    
    # Separate fire and non-fire years
    fire_data = df[df['year'].isin(fire_years)]
    non_fire_data = df[~df['year'].isin(fire_years)]
    
    if fire_data.empty or non_fire_data.empty:
        print("❌ Insufficient data for fire impact analysis")
        return {}
    
    # Calculate statistics for each group
    fire_mean = fire_data[value_column].mean()
    fire_std = fire_data[value_column].std()
    non_fire_mean = non_fire_data[value_column].mean()
    non_fire_std = non_fire_data[value_column].std()
    
    # Calculate difference
    difference = fire_mean - non_fire_mean
    percent_difference = (difference / non_fire_mean) * 100
    
    print(f"\n📊 STATISTICS:")
    print(f"   Fire years mean: {fire_mean:.3f} ± {fire_std:.3f}")
    print(f"   Non-fire years mean: {non_fire_mean:.3f} ± {non_fire_std:.3f}")
    print(f"   Difference: {difference:.3f} ({percent_difference:.1f}%)")
    
    # Statistical test (t-test)
    from scipy.stats import ttest_ind
    t_stat, p_value = ttest_ind(fire_data[value_column], non_fire_data[value_column])
    
    print(f"\n📈 T-TEST RESULTS:")
    print(f"   T-statistic: {t_stat:.3f}")
    print(f"   P-value: {p_value:.4f}")
    
    if p_value < 0.05:
        print(f"   ✅ SIGNIFICANT difference between fire and non-fire years!")
    else:
        print(f"   ⚠️  No significant difference detected")
    
    # Analyze individual fire years
    fire_year_stats = {}
    for year in fire_years:
        year_data = df[df['year'] == year]
        if not year_data.empty:
            fire_year_stats[year] = {
                'mean': year_data[value_column].mean(),
                'std': year_data[value_column].std(),
                'count': len(year_data)
            }
    
    results = {
        'fire_years': fire_years,
        'fire_mean': fire_mean,
        'fire_std': fire_std,
        'non_fire_mean': non_fire_mean,
        'non_fire_std': non_fire_std,
        'difference': difference,
        'percent_difference': percent_difference,
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'fire_year_stats': fire_year_stats
    }
    
    return results


def analyze_melt_season_trends(df):
    """
    Comprehensive melt season trend analysis
    Combines annual, monthly, and fire impact analyses
    
    Args:
        df: DataFrame with complete melt season data
    
    Returns:
        dict: Combined analysis results
    """
    if df.empty:
        print("❌ Empty dataset for analysis")
        return {}
    
    print(f"\n🏔️ MELT SEASON COMPREHENSIVE ANALYSIS")
    print("=" * 60)
    print(f"Dataset period: {df['year'].min()}-{df['year'].max()}")
    print(f"Total observations: {len(df)}")
    
    # Annual trends
    annual_results = analyze_annual_trends(df)
    
    # Monthly breakdown
    monthly_results = analyze_monthly_trends(df, months=[6, 7, 8, 9])
    
    # Fire impact analysis
    fire_results = analyze_fire_impact(df, fire_years=[2017, 2018, 2021, 2023])
    
    # Summary statistics
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   Overall albedo mean: {df['albedo_mean'].mean():.3f}")
    print(f"   Overall albedo std: {df['albedo_mean'].std():.3f}")
    print(f"   Data completeness: {len(df) / (len(df['year'].unique()) * 122):.1%}")
    
    return {
        'annual_trends': annual_results,
        'monthly_trends': monthly_results,
        'fire_impact': fire_results,
        'summary_stats': {
            'mean_albedo': df['albedo_mean'].mean(),
            'std_albedo': df['albedo_mean'].std(),
            'n_observations': len(df),
            'years_covered': sorted(df['year'].unique()),
            'period': f"{df['year'].min()}-{df['year'].max()}"
        }
    } 