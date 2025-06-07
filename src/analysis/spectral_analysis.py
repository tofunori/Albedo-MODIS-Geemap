"""
Spectral Analysis Module for MCD43A3 Data
Following Williamson & Menounos (2021) methodology
Handles trend analysis and spectral band comparisons
"""

import pandas as pd
import numpy as np


def analyze_spectral_trends(df):
    """
    Analyze spectral albedo trends following Williamson & Menounos methodology
    
    Args:
        df: DataFrame with MCD43A3 spectral albedo data
    
    Returns:
        dict: Spectral trend analysis results
    """
    if df.empty:
        return {}
    
    print(f"\n🌈 SPECTRAL ALBEDO TREND ANALYSIS")
    print("=" * 50)
    print("📚 Following Williamson & Menounos (2021) spectral methodology")
    
    # Import statistical functions
    from src.analysis.statistics import mann_kendall_test, sens_slope_estimate
    
    # Define spectral band groups following the paper
    spectral_groups = {
        'visible': ['Albedo_BSA_Band1', 'Albedo_BSA_Band3', 'Albedo_BSA_Band4', 'Albedo_BSA_vis'],
        'near_infrared': ['Albedo_BSA_Band2', 'Albedo_BSA_nir'],
        'broadband': ['Albedo_BSA_shortwave']
    }
    
    results = {}
    
    # Calculate annual means for each spectral band
    albedo_columns = [col for col in df.columns if 'Albedo_BSA' in col]
    if not albedo_columns:
        print("❌ No albedo bands found in data")
        return {}
    
    annual_data = df.groupby('year').agg({
        band: 'mean' for band in albedo_columns
    }).reset_index()
    
    print(f"📊 Analysis period: {annual_data['year'].min()}-{annual_data['year'].max()}")
    print(f"📊 Years analyzed: {len(annual_data)}")
    
    # Analyze trends for each spectral group
    for group_name, bands in spectral_groups.items():
        print(f"\n🔍 Analyzing {group_name.upper()} spectral bands:")
        
        group_results = {}
        
        for band in bands:
            if band in annual_data.columns:
                values = annual_data[band].dropna()
                
                if len(values) >= 4:  # Minimum for trend analysis
                    # Mann-Kendall test
                    mk_result = mann_kendall_test(values.values)
                    
                    # Sen's slope
                    sens_result = sens_slope_estimate(values.values)
                    
                    # Calculate change statistics
                    first_value = values.iloc[0]
                    change_per_year = sens_result['slope_per_year']
                    change_percent_per_year = (change_per_year / first_value) * 100 if first_value > 0 else 0
                    
                    print(f"   📈 {band}:")
                    print(f"      Trend: {mk_result['trend'].replace('_', ' ')}")
                    print(f"      Change: {change_percent_per_year:.2f}%/year")
                    print(f"      P-value: {mk_result['p_value']:.4f}")
                    
                    if mk_result['p_value'] < 0.05:
                        significance = "***"
                        print(f"      ✅ SIGNIFICANT trend")
                    else:
                        significance = "ns"
                        print(f"      ⚠️  Not significant")
                    
                    group_results[band] = {
                        'mann_kendall': mk_result,
                        'sens_slope': sens_result,
                        'change_per_year': change_per_year,
                        'change_percent_per_year': change_percent_per_year,
                        'significance': significance,
                        'n_years': len(values)
                    }
                else:
                    print(f"   ⚠️  {band}: Insufficient data ({len(values)} years)")
        
        results[group_name] = group_results
    
    # Calculate group averages (visible vs NIR comparison)
    if results.get('visible') and results.get('near_infrared'):
        print(f"\n🔍 VISIBLE vs NEAR-INFRARED COMPARISON:")
        
        # Average visible change
        vis_changes = [r['change_percent_per_year'] for r in results['visible'].values() if 'change_percent_per_year' in r]
        nir_changes = [r['change_percent_per_year'] for r in results['near_infrared'].values() if 'change_percent_per_year' in r]
        
        if vis_changes and nir_changes:
            avg_vis_change = np.mean(vis_changes)
            avg_nir_change = np.mean(nir_changes)
            
            print(f"   📊 Average visible change: {avg_vis_change:.2f}%/year")
            print(f"   📊 Average NIR change: {avg_nir_change:.2f}%/year")
            
            if abs(avg_vis_change) > abs(avg_nir_change):
                print(f"   🎯 STRONGER decline in VISIBLE spectrum")
                print(f"   💡 Consistent with light-absorbing particle deposition")
            else:
                print(f"   🎯 Similar or stronger decline in NIR spectrum")
                print(f"   💡 May indicate snow grain size effects")
            
            results['spectral_comparison'] = {
                'visible_avg_change': avg_vis_change,
                'nir_avg_change': avg_nir_change,
                'interpretation': "visible_dominant" if abs(avg_vis_change) > abs(avg_nir_change) else "nir_dominant"
            }
    
    return results


def calculate_spectral_ratios(df):
    """
    Calculate spectral ratios for contamination analysis
    
    Args:
        df: DataFrame with MCD43A3 spectral albedo data
    
    Returns:
        DataFrame: Data with added spectral ratio columns
    """
    df_copy = df.copy()
    
    # Calculate key spectral ratios
    if 'Albedo_BSA_vis' in df.columns and 'Albedo_BSA_nir' in df.columns:
        df_copy['vis_nir_ratio'] = df_copy['Albedo_BSA_vis'] / df_copy['Albedo_BSA_nir']
    
    if 'Albedo_BSA_Band1' in df.columns and 'Albedo_BSA_Band2' in df.columns:
        df_copy['red_nir_ratio'] = df_copy['Albedo_BSA_Band1'] / df_copy['Albedo_BSA_Band2']
    
    if 'Albedo_BSA_Band3' in df.columns and 'Albedo_BSA_Band1' in df.columns:
        df_copy['blue_red_ratio'] = df_copy['Albedo_BSA_Band3'] / df_copy['Albedo_BSA_Band1']
    
    return df_copy


def detect_contamination_events(df, threshold_percentile=10):
    """
    Detect potential contamination events using spectral signatures
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        threshold_percentile: Percentile threshold for contamination detection
    
    Returns:
        DataFrame: Contamination events identified
    """
    if df.empty:
        return pd.DataFrame()
    
    # Calculate spectral ratios
    df_ratios = calculate_spectral_ratios(df)
    
    contamination_events = []
    
    # Check for low visible/NIR ratios (indication of light-absorbing particles)
    if 'vis_nir_ratio' in df_ratios.columns:
        threshold = np.percentile(df_ratios['vis_nir_ratio'].dropna(), threshold_percentile)
        contaminated = df_ratios[df_ratios['vis_nir_ratio'] < threshold]
        
        for _, row in contaminated.iterrows():
            contamination_events.append({
                'date': row['date'],
                'type': 'low_vis_nir_ratio',
                'value': row['vis_nir_ratio'],
                'threshold': threshold,
                'severity': 'high' if row['vis_nir_ratio'] < threshold * 0.8 else 'moderate'
            })
    
    # Check for unusual spectral patterns
    if 'Albedo_BSA_vis' in df.columns and 'Albedo_BSA_nir' in df.columns:
        # Abnormally low visible albedo
        vis_threshold = np.percentile(df['Albedo_BSA_vis'].dropna(), threshold_percentile)
        low_vis = df[df['Albedo_BSA_vis'] < vis_threshold]
        
        for _, row in low_vis.iterrows():
            contamination_events.append({
                'date': row['date'],
                'type': 'low_visible_albedo',
                'value': row['Albedo_BSA_vis'],
                'threshold': vis_threshold,
                'severity': 'high' if row['Albedo_BSA_vis'] < vis_threshold * 0.8 else 'moderate'
            })
    
    return pd.DataFrame(contamination_events)


def analyze_seasonal_patterns(df):
    """
    Analyze seasonal patterns in spectral albedo
    
    Args:
        df: DataFrame with MCD43A3 spectral data
    
    Returns:
        dict: Seasonal analysis results
    """
    if df.empty:
        return {}
    
    # Add month information if not present
    if 'month' not in df.columns:
        df['month'] = df['date'].dt.month
    
    # Focus on melt season months (June-September)
    melt_season = df[df['month'].isin([6, 7, 8, 9])].copy()
    
    if melt_season.empty:
        return {}
    
    seasonal_results = {}
    
    # Monthly statistics for key bands
    key_bands = ['Albedo_BSA_vis', 'Albedo_BSA_nir', 'Albedo_BSA_shortwave']
    
    for band in key_bands:
        if band in melt_season.columns:
            monthly_stats = melt_season.groupby('month')[band].agg(['mean', 'std', 'count']).reset_index()
            seasonal_results[band] = monthly_stats.to_dict('records')
    
    # Calculate seasonal trends
    seasonal_trends = {}
    for band in key_bands:
        if band in melt_season.columns:
            # Early vs late season comparison
            early_season = melt_season[melt_season['month'].isin([6, 7])][band].mean()
            late_season = melt_season[melt_season['month'].isin([8, 9])][band].mean()
            
            seasonal_change = late_season - early_season
            seasonal_change_percent = (seasonal_change / early_season) * 100 if early_season > 0 else 0
            
            seasonal_trends[band] = {
                'early_season_mean': early_season,
                'late_season_mean': late_season,
                'seasonal_change': seasonal_change,
                'seasonal_change_percent': seasonal_change_percent
            }
    
    return {
        'monthly_statistics': seasonal_results,
        'seasonal_trends': seasonal_trends,
        'analysis_period': f"{melt_season['year'].min()}-{melt_season['year'].max()}",
        'total_observations': len(melt_season)
    }