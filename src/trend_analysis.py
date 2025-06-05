"""
Advanced Statistical Trend Analysis Module for MODIS Albedo Data
Following Williamson & Menounos (2021) methodology
- Mann-Kendall trend tests
- Sen's slope estimates
- Monthly breakdown analysis
- Fire impact analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import kendalltau, ttest_ind

# ================================================================================
# STATISTICAL TREND TESTS
# ================================================================================

def mann_kendall_test(data):
    """
    Perform Mann-Kendall trend test
    
    Args:
        data: Time series data (array-like)
    
    Returns:
        dict: Results with trend direction, p-value, and tau
    """
    n = len(data)
    if n < 4:
        return {'trend': 'no_trend', 'p_value': 1.0, 'tau': 0.0}
    
    # Create sequence
    x = np.arange(n)
    
    # Calculate Kendall's tau and p-value
    tau, p_value = kendalltau(x, data)
    
    # Determine trend
    if p_value < 0.05:
        if tau > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
    else:
        trend = 'no_trend'
    
    return {
        'trend': trend,
        'p_value': p_value,
        'tau': tau
    }

def sens_slope_estimate(data):
    """
    Calculate Sen's slope estimate (robust trend estimator)
    
    Args:
        data: Time series data (array-like)
    
    Returns:
        dict: Slope per year and intercept
    """
    n = len(data)
    if n < 4:
        return {'slope_per_year': 0.0, 'intercept': np.mean(data)}
    
    slopes = []
    for i in range(n):
        for j in range(i+1, n):
            if j != i:
                slope = (data[j] - data[i]) / (j - i)
                slopes.append(slope)
    
    if slopes:
        slope_per_year = np.median(slopes)
        intercept = np.median(data) - slope_per_year * np.median(np.arange(n))
    else:
        slope_per_year = 0.0
        intercept = np.mean(data)
    
    return {
        'slope_per_year': slope_per_year,
        'intercept': intercept
    }

# ================================================================================
# COMPREHENSIVE TREND ANALYSIS
# ================================================================================

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
    
    # Mann-Kendall trend test
    mk_result = mann_kendall_test(values)
    
    # Sen's slope estimate
    sens_result = sens_slope_estimate(values)
    
    # Calculate change statistics
    first_year_value = values[0]
    last_year_value = values[-1]
    total_change = last_year_value - first_year_value
    total_percent_change = (total_change / first_year_value) * 100
    change_per_year = sens_result['slope_per_year']
    change_percent_per_year = (change_per_year / first_year_value) * 100
    
    print(f"\n📈 TREND RESULTS:")
    print(f"   Trend direction: {mk_result['trend'].replace('_', ' ').title()}")
    print(f"   Mann-Kendall p-value: {mk_result['p_value']:.4f}")
    print(f"   Kendall's tau: {mk_result['tau']:.3f}")
    print(f"   Sen's slope: {change_per_year:.4f}/year ({change_percent_per_year:.2f}%/year)")
    print(f"   Total change ({years.min()}-{years.max()}): {total_change:.3f} ({total_percent_change:.1f}%)")
    
    # Statistical significance
    if mk_result['p_value'] < 0.05:
        print(f"   ✅ STATISTICALLY SIGNIFICANT trend detected!")
        significance = "significant"
    else:
        print(f"   ⚠️  Trend not statistically significant (p > 0.05)")
        significance = "not significant"
    
    # Compile results
    results = {
        'annual_data': annual_data,
        'mann_kendall': mk_result,
        'sens_slope': sens_result,
        'n_years': len(years),
        'change_per_year': change_per_year,
        'change_percent_per_year': change_percent_per_year,
        'total_change': total_change,
        'total_percent_change': total_percent_change,
        'significance': significance,
        'period': f"{years.min()}-{years.max()}"
    }
    
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
        
        # Statistical tests
        mk_result = mann_kendall_test(values)
        sens_result = sens_slope_estimate(values)
        
        # Calculate changes
        first_value = values[0]
        change_per_year = sens_result['slope_per_year']
        change_percent_per_year = (change_per_year / first_value) * 100
        
        print(f"   📊 Period: {years.min()}-{years.max()} ({len(years)} years)")
        print(f"   📈 Trend: {mk_result['trend'].replace('_', ' ')}")
        print(f"   📉 Change: {change_percent_per_year:.2f}%/year (p={mk_result['p_value']:.3f})")
        
        if mk_result['p_value'] < 0.05:
            print(f"   ✅ Statistically significant!")
        else:
            print(f"   ⚠️  Not significant")
        
        monthly_results[month] = {
            'month_name': month_names[month],
            'annual_data': annual_monthly,
            'mann_kendall': mk_result,
            'sens_slope': sens_result,
            'change_per_year': change_per_year,
            'change_percent_per_year': change_percent_per_year,
            'n_years': len(years),
            'period': f"{years.min()}-{years.max()}"
        }
    
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
    
    # Identify available fire years in the dataset
    available_years = set(df['year'].unique())
    available_fire_years = [year for year in fire_years if year in available_years]
    
    if not available_fire_years:
        print(f"   ⚠️ No fire years found in dataset")
        return {}
    
    print(f"   🔥 Fire years in dataset: {available_fire_years}")
    
    # Split data
    fire_data = df[df['year'].isin(available_fire_years)]
    normal_data = df[~df['year'].isin(available_fire_years)]
    
    if fire_data.empty or normal_data.empty:
        print(f"   ⚠️ Insufficient data for comparison")
        return {}
    
    # Calculate means
    fire_mean = fire_data[value_column].mean()
    normal_mean = normal_data[value_column].mean()
    difference = fire_mean - normal_mean
    percent_diff = (difference / normal_mean) * 100
    
    print(f"   🔥 Fire years mean: {fire_mean:.3f} ({len(fire_data)} obs)")
    print(f"   🌱 Normal years mean: {normal_mean:.3f} ({len(normal_data)} obs)")
    print(f"   📊 Difference: {difference:.3f} ({percent_diff:.1f}%)")
    
    if difference < 0:
        print(f"   ⚠️  Fire years show {abs(percent_diff):.1f}% LOWER values")
        impact_direction = "lower"
    else:
        print(f"   ✅ Fire years show {percent_diff:.1f}% higher values")
        impact_direction = "higher"
    
    # Statistical test if enough data
    p_val = None
    if len(fire_data) > 10 and len(normal_data) > 10:
        t_stat, p_val = ttest_ind(fire_data[value_column], normal_data[value_column])
        print(f"   📊 T-test p-value: {p_val:.4f}")
        if p_val < 0.05:
            print(f"   ✅ Difference is statistically significant!")
        else:
            print(f"   ⚠️  Difference not statistically significant")
    
    return {
        'fire_years': available_fire_years,
        'fire_mean': fire_mean,
        'normal_mean': normal_mean,
        'difference': difference,
        'percent_difference': percent_diff,
        'impact_direction': impact_direction,
        'p_value': p_val,
        'n_fire_obs': len(fire_data),
        'n_normal_obs': len(normal_data)
    }

# ================================================================================
# MELT SEASON SPECIFIC ANALYSIS
# ================================================================================

def extract_melt_season_data_yearly(start_year=2010, end_year=2024, scale=500):
    """
    Extract melt season data year by year to avoid timeout
    Following Williamson & Menounos (2021) approach
    
    Args:
        start_year: First year to extract
        end_year: Last year to extract
        scale: Spatial resolution in meters
    
    Returns:
        DataFrame: Combined melt season data
    """
    from data_processing import extract_time_series_fast
    import ee
    
    print(f"🌡️ EXTRACTING MELT SEASON DATA ({start_year}-{end_year})")
    print("=" * 60)
    
    all_data = []
    successful_years = []
    failed_years = []
    
    for year in range(start_year, end_year + 1):
        print(f"\n📡 Extracting data for {year} melt season...")
        
        # Extract melt season for this year (June-September)
        year_start = f'{year}-06-01'
        year_end = f'{year}-09-30'
        
        try:
            df_year = extract_time_series_fast(year_start, year_end, scale=scale, sampling_days=7)
            
            if not df_year.empty:
                # Filter to melt season months only
                melt_data = df_year[df_year['month'].isin([6, 7, 8, 9])].copy()
                
                if not melt_data.empty:
                    all_data.append(melt_data)
                    successful_years.append(year)
                    print(f"   ✅ {year}: {len(melt_data)} observations")
                else:
                    failed_years.append(year)
                    print(f"   ❌ {year}: No melt season data")
            else:
                failed_years.append(year)
                print(f"   ❌ {year}: No data extracted")
                
        except Exception as e:
            failed_years.append(year)
            print(f"   ❌ {year}: Error - {str(e)[:50]}...")
            continue
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n✅ EXTRACTION COMPLETE")
        print(f"   Successful years: {len(successful_years)} ({successful_years})")
        print(f"   Failed years: {len(failed_years)} ({failed_years})")
        print(f"   Total observations: {len(combined_df)}")
        return combined_df
    else:
        print(f"\n❌ NO DATA EXTRACTED")
        return pd.DataFrame()

def analyze_melt_season_trends(df):
    """
    Perform comprehensive melt season trend analysis
    Following Williamson & Menounos (2021) methodology
    
    Args:
        df: DataFrame with melt season data
    
    Returns:
        dict: Complete trend analysis results
    """
    if df.empty:
        return None
    
    print(f"\n🔍 MELT SEASON TREND ANALYSIS")
    print("=" * 50)
    
    # Calculate annual melt season means
    annual_data = df.groupby('year')['albedo_mean'].agg(['mean', 'std', 'count']).reset_index()
    annual_data = annual_data[annual_data['count'] >= 5]  # Need at least 5 observations per year
    
    if len(annual_data) < 4:
        print(f"❌ Insufficient years for trend analysis (need ≥4, have {len(annual_data)})")
        return None
    
    years = annual_data['year'].values
    albedo_means = annual_data['mean'].values
    
    print(f"📊 Analysis period: {years.min()}-{years.max()} ({len(years)} years)")
    print(f"📊 Mean melt season albedo: {albedo_means.mean():.3f} ± {albedo_means.std():.3f}")
    
    # Mann-Kendall trend test
    mk_result = mann_kendall_test(albedo_means)
    
    # Sen's slope estimate
    sens_result = sens_slope_estimate(albedo_means)
    
    # Calculate change statistics
    first_year_albedo = albedo_means[0]
    last_year_albedo = albedo_means[-1]
    total_change = last_year_albedo - first_year_albedo
    total_percent_change = (total_change / first_year_albedo) * 100
    change_per_year = sens_result['slope_per_year']
    change_percent_per_year = (change_per_year / first_year_albedo) * 100
    
    print(f"\n📈 TREND RESULTS:")
    print(f"   Trend direction: {mk_result['trend'].replace('_', ' ').title()}")
    print(f"   Mann-Kendall p-value: {mk_result['p_value']:.4f}")
    print(f"   Kendall's tau: {mk_result['tau']:.3f}")
    print(f"   Sen's slope: {change_per_year:.4f}/year ({change_percent_per_year:.2f}%/year)")
    print(f"   Total change ({years.min()}-{years.max()}): {total_change:.3f} ({total_percent_change:.1f}%)")
    
    # Statistical significance
    if mk_result['p_value'] < 0.05:
        print(f"   ✅ STATISTICALLY SIGNIFICANT trend detected!")
        significance = "significant"
    else:
        print(f"   ⚠️  Trend not statistically significant (p > 0.05)")
        significance = "not significant"
    
    # Compile results
    results = {
        'annual_data': annual_data,
        'mann_kendall': mk_result,
        'sens_slope': sens_result,
        'n_years': len(years),
        'change_per_year': change_per_year,
        'change_percent_per_year': change_percent_per_year,
        'total_change': total_change,
        'total_percent_change': total_percent_change,
        'significance': significance,
        'period': f"{years.min()}-{years.max()}"
    }
    
    return results

def analyze_melt_season_comprehensive(df, start_year=2010, end_year=2024):
    """
    Comprehensive melt season analysis following Williamson & Menounos (2021)
    
    Args:
        df: DataFrame with complete albedo data
        start_year: Start year for analysis
        end_year: End year for analysis
    
    Returns:
        dict: Complete melt season analysis results
    """
    if df.empty:
        return None
    
    print(f"\n🌡️ COMPREHENSIVE MELT SEASON ANALYSIS ({start_year}-{end_year})")
    print("=" * 70)
    print("📚 Following Williamson & Menounos (2021) methodology")
    
    # Filter to melt season (June-September)
    melt_df = df[df['month'].isin([6, 7, 8, 9])].copy()
    
    if melt_df.empty:
        print("❌ No melt season data found")
        return None
    
    # Filter to analysis period
    melt_df = melt_df[(melt_df['year'] >= start_year) & (melt_df['year'] <= end_year)]
    
    print(f"📊 Melt season observations: {len(melt_df)}")
    print(f"📅 Years covered: {sorted(melt_df['year'].unique())}")
    
    # 1. Overall melt season trend
    print(f"\n1️⃣ OVERALL MELT SEASON TREND")
    overall_results = analyze_annual_trends(melt_df, min_obs_per_year=5)
    
    # 2. Monthly breakdown
    print(f"\n2️⃣ MONTHLY BREAKDOWN")
    monthly_results = analyze_monthly_trends(melt_df, months=[6, 7, 8, 9])
    
    # 3. Fire impact analysis
    print(f"\n3️⃣ FIRE IMPACT ANALYSIS")
    fire_results = analyze_fire_impact(melt_df)
    
    # Compile comprehensive results
    comprehensive_results = {
        'overall_trends': overall_results,
        'monthly_trends': monthly_results,
        'fire_impact': fire_results,
        'dataset_info': {
            'total_observations': len(melt_df),
            'years_analyzed': sorted(melt_df['year'].unique()),
            'period': f"{start_year}-{end_year}",
            'method': "Williamson & Menounos (2021)"
        }
    }
    
    return comprehensive_results

def create_melt_season_plot(results, monthly_results, df, output_file='athabasca_melt_season_comprehensive_analysis.png'):
    """
    Create comprehensive melt season analysis plot
    
    Args:
        results: Main trend analysis results
        monthly_results: Monthly breakdown results
        df: Original dataframe with all data
        output_file: Output filename for the plot
    """
    if not results:
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Athabasca Glacier Melt Season Albedo Trends', fontsize=16, fontweight='bold')
    
    # Plot 1: Annual melt season trend
    annual_data = results['annual_data']
    years = annual_data['year'].values
    albedo_means = annual_data['mean'].values
    albedo_std = annual_data['std'].values
    
    ax1.errorbar(years, albedo_means, yerr=albedo_std, fmt='o-', color='orange', alpha=0.8, capsize=3)
    
    # Trend line
    slope = results['sens_slope']['slope_per_year']
    intercept = results['sens_slope']['intercept']
    trend_line = slope * np.arange(len(years)) + intercept
    ax1.plot(years, trend_line, '--', color='red', linewidth=2)
    
    # Highlight fire years
    fire_years = [2017, 2018, 2021, 2023]
    for fire_year in fire_years:
        if fire_year in years:
            fire_idx = np.where(years == fire_year)[0]
            if len(fire_idx) > 0:
                ax1.scatter(fire_year, albedo_means[fire_idx[0]], color='red', s=150, marker='*', 
                           zorder=5, alpha=0.9, edgecolor='black')
    
    ax1.set_title(f'Melt Season Albedo Trend\n({results["period"]}, p={results["mann_kendall"]["p_value"]:.3f})')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Albedo')
    ax1.grid(True, alpha=0.3)
    ax1.legend(['Melt Season Mean', 'Sen\'s Slope Trend', 'Fire Years'], loc='best')
    
    # Plot 2: Monthly breakdown
    if monthly_results:
        months = list(monthly_results.keys())
        month_changes = [monthly_results[m]['change_percent_per_year'] for m in months]
        month_names = [monthly_results[m]['month_name'] for m in months]
        colors = ['lightcoral' if monthly_results[m]['mann_kendall']['p_value'] < 0.05 else 'lightblue' 
                 for m in months]
        
        bars = ax2.bar(month_names, month_changes, color=colors, alpha=0.7, edgecolor='black')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.set_title('Monthly Trend Breakdown')
        ax2.set_ylabel('Change (%/year)')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add significance markers
        for bar, month in zip(bars, months):
            if monthly_results[month]['mann_kendall']['p_value'] < 0.05:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1*abs(height),
                        '**', ha='center', va='bottom', fontweight='bold')
    
    # Plot 3: Time series by month
    month_colors = {6: 'green', 7: 'orange', 8: 'red', 9: 'brown'}
    month_names_short = {6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep'}
    
    for month in [6, 7, 8, 9]:
        month_data = df[df['month'] == month]
        if not month_data.empty:
            ax3.scatter(month_data['year'], month_data['albedo_mean'], 
                       alpha=0.6, color=month_colors[month], label=month_names_short[month], s=30)
    
    ax3.set_title('Melt Season Data by Month')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('Albedo')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Summary statistics
    ax4.axis('off')
    summary_text = f"""MELT SEASON ANALYSIS SUMMARY
{'='*35}

OVERALL TREND ({results['period']}):
• Change: {results['change_percent_per_year']:.2f}%/year
• Total change: {results['total_percent_change']:.1f}%
• Significance: p = {results['mann_kendall']['p_value']:.4f}
• Status: {results['significance'].upper()}

DATASET:
• Years analyzed: {results['n_years']}
• Total observations: {len(df)}
• Period: {results['period']}

MONTHLY TRENDS:"""

    if monthly_results:
        for month, data in monthly_results.items():
            sig_marker = '**' if data['mann_kendall']['p_value'] < 0.05 else ''
            month_name = data['month_name'][:3]
            summary_text += f"\n• {month_name}: {data['change_percent_per_year']:>6.2f}%/yr {sig_marker}"
    
    summary_text += f"\n\nFIRE YEARS: ★ 2017, 2018, 2021, 2023"
    summary_text += f"\n** = Statistically significant (p<0.05)"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    from paths import get_figure_path
    
    plt.tight_layout()
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📊 Plot saved: {fig_path}")

def run_melt_season_analysis_williamson(start_year=2015, end_year=2024, scale=500):
    """
    Complete melt season analysis workflow following Williamson & Menounos (2021)
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis  
        scale: Spatial resolution in meters
    
    Returns:
        dict: Complete analysis results
    """
    import ee
    
    print("🌡️ ATHABASCA GLACIER MELT SEASON ALBEDO TREND ANALYSIS")
    print("=" * 70)
    print("🎯 Focus: Melt season (June-September) albedo trends")
    print("📚 Method: Following Williamson & Menounos (2021) approach")
    print("⚡ Strategy: Year-by-year extraction to avoid timeout")
    
    # Initialize Earth Engine
    ee.Initialize()
    
    # Extract melt season data
    df = extract_melt_season_data_yearly(start_year=start_year, end_year=end_year, scale=scale)
    
    if df.empty:
        print("❌ No data extracted. Analysis cannot proceed.")
        return None
    
    # Export raw data
    from paths import get_output_path
    
    csv_path = get_output_path('athabasca_melt_season_focused_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Raw data exported: {csv_path}")
    
    # Main trend analysis
    results = analyze_melt_season_trends(df)
    
    if not results:
        print("❌ Trend analysis failed.")
        return None
    
    # Monthly analysis
    monthly_results = analyze_monthly_trends(df, months=[6, 7, 8, 9])
    
    # Fire impact analysis  
    fire_results = analyze_fire_impact(df)
    
    # Create comprehensive plot
    create_melt_season_plot(results, monthly_results, df)
    
    # Final summary
    print(f"\n🎉 MELT SEASON ANALYSIS COMPLETE!")
    print("=" * 50)
    print(f"📊 Period analyzed: {results['period']}")
    print(f"🌡️ Melt season trend: {results['change_percent_per_year']:.2f}%/year")
    print(f"📈 Statistical significance: {results['significance']}")
    print(f"💾 Data and plots saved to current directory")
    
    return {
        'main_results': results,
        'monthly_results': monthly_results,
        'fire_results': fire_results,
        'data': df
    }

# ================================================================================
# VALIDATION AND QUALITY CHECKS
# ================================================================================

def validate_trend_analysis_requirements(df, min_years=4, min_obs_per_year=5):
    """
    Validate that dataset meets requirements for robust trend analysis
    
    Args:
        df: DataFrame to validate
        min_years: Minimum number of years required
        min_obs_per_year: Minimum observations per year
    
    Returns:
        dict: Validation results and recommendations
    """
    if df.empty:
        return {'valid': False, 'reason': 'Empty dataset'}
    
    # Check years coverage
    annual_counts = df.groupby('year').size()
    valid_years = annual_counts[annual_counts >= min_obs_per_year]
    
    validation = {
        'valid': len(valid_years) >= min_years,
        'total_years': len(annual_counts),
        'valid_years': len(valid_years),
        'min_required_years': min_years,
        'total_observations': len(df),
        'years_with_sufficient_data': valid_years.index.tolist(),
        'recommendations': []
    }
    
    if not validation['valid']:
        if len(valid_years) < min_years:
            validation['recommendations'].append(f"Extend time series (need {min_years} years, have {len(valid_years)})")
        
        insufficient_years = annual_counts[annual_counts < min_obs_per_year]
        if not insufficient_years.empty:
            validation['recommendations'].append(f"Years with insufficient data: {insufficient_years.index.tolist()}")
    
    return validation 