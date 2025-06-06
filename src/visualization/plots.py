"""
Visualization Module for MODIS Albedo Analysis
Creates comprehensive plots for trend analysis results
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from paths import get_figure_path


def create_hypsometric_plot(hypsometric_results, comparison_results, df, output_file='athabasca_hypsometric_analysis.png'):
    """
    Create comprehensive hypsometric analysis visualization
    
    Args:
        hypsometric_results: Results from analyze_hypsometric_trends()
        comparison_results: Results from compare_elevation_bands()
        df: Original dataframe with elevation data
        output_file: Output filename
    """
    if not hypsometric_results:
        print("❌ No hypsometric results to plot")
        return
    
    # Import needed function
    from analysis.hypsometric import classify_elevation_bands
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Hypsometric Analysis - Elevation Band Trends\n(Following Williamson & Menounos 2021)', 
                 fontsize=16, fontweight='bold')
    
    # Color scheme for elevation bands
    colors = {
        'above_median': '#2E8B57',  # Sea Green (high elevation)
        'near_median': '#FF6B35',   # Orange Red (transition zone)
        'below_median': '#4682B4'   # Steel Blue (low elevation)
    }
    
    # Plot 1: Annual trends by elevation band
    ax1 = axes[0, 0]
    for band, results in hypsometric_results.items():
        if 'trend_analysis' in results:
            annual_data = results['trend_analysis']['annual_data']
            years = annual_data['year'].values
            means = annual_data['mean'].values
            
            # Plot data points and trend line
            ax1.plot(years, means, 'o-', color=colors[band], alpha=0.7, 
                    linewidth=2, markersize=6, label=results['band_name'])
            
            # Add trend line
            slope = results['trend_analysis']['sens_slope']['slope_per_year']
            intercept = results['trend_analysis']['sens_slope']['intercept']
            trend_line = slope * np.arange(len(years)) + intercept
            ax1.plot(years, trend_line, '--', color=colors[band], linewidth=2, alpha=0.8)
    
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Albedo')
    ax1.set_title('Annual Albedo Trends by Elevation Band')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Sen's slope comparison
    ax2 = axes[0, 1]
    if comparison_results and 'slopes_by_band' in comparison_results:
        slopes = comparison_results['slopes_by_band']
        significance = comparison_results['significance_by_band']
        
        bands = list(slopes.keys())
        slope_values = [slopes[band] for band in bands]
        band_names = [hypsometric_results[band]['band_name'] for band in bands]
        bar_colors = [colors[band] for band in bands]
        
        bars = ax2.bar(band_names, slope_values, color=bar_colors, alpha=0.7, edgecolor='black')
        
        # Mark significant trends
        for i, (band, slope_val) in enumerate(zip(bands, slope_values)):
            if significance.get(band, False):
                ax2.text(i, slope_val + (0.001 if slope_val > 0 else -0.001), 
                        '***', ha='center', va='bottom' if slope_val > 0 else 'top', 
                        fontsize=14, fontweight='bold')
        
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax2.set_ylabel('Sen\'s Slope (per year)')
        ax2.set_title('Trend Magnitude by Elevation Band')
        ax2.tick_params(axis='x', rotation=45)
    
    # Plot 3: Elevation distribution
    ax3 = axes[1, 0]
    if not df.empty and 'elevation' in df.columns:
        # First classify the data into elevation bands if not already done
        if 'elevation_band' not in df.columns:
            df_temp = classify_elevation_bands(df.copy(), 'elevation')
        else:
            df_temp = df.copy()
        
        # Plot histogram for each elevation band
        bands_plotted = False
        for band in ['above_median', 'near_median', 'below_median']:
            band_data = df_temp[df_temp['elevation_band'] == band]
            if not band_data.empty:
                ax3.hist(band_data['elevation'], bins=20, alpha=0.6, 
                        color=colors[band], 
                        label=hypsometric_results[band]['band_name'] if band in hypsometric_results else band,
                        edgecolor='black', linewidth=0.5)
                bands_plotted = True
        
        # If no bands were plotted, plot all elevation data
        if not bands_plotted:
            ax3.hist(df['elevation'], bins=30, alpha=0.7, color='gray', 
                    edgecolor='black', linewidth=0.5)
            ax3.set_title('Elevation Distribution (All Data)')
        else:
            ax3.set_title('Elevation Distribution by Band')
            ax3.legend()
        
        ax3.set_xlabel('Elevation (m)')
        ax3.set_ylabel('Frequency')
        ax3.grid(True, alpha=0.3)
        
        # Add median elevation line
        if 'glacier_median_elevation' in df.columns:
            median_elev = df['glacier_median_elevation'].iloc[0]
        else:
            median_elev = df['elevation'].median()
        
        ax3.axvline(median_elev, color='red', linestyle='--', linewidth=2, 
                   label=f'Glacier Median: {median_elev:.0f}m')
        ax3.legend()
    
    # Plot 4: Summary text
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Create summary text
    summary_text = "HYPSOMETRIC ANALYSIS SUMMARY\n\n"
    
    if comparison_results:
        summary_text += f"Pattern: {comparison_results.get('interpretation', 'Unknown')}\n\n"
        
        if comparison_results.get('transient_snowline_pattern', False):
            summary_text += "✅ TRANSIENT SNOWLINE DETECTED\n"
            summary_text += "Strongest decline near median elevation\n"
            summary_text += "Consistent with Williamson & Menounos (2021)\n\n"
        elif comparison_results.get('elevation_gradient_pattern', False):
            summary_text += "🌡️ ELEVATION-DEPENDENT WARMING\n"
            summary_text += "Stronger decline at lower elevations\n"
            summary_text += "Enhanced warming in ablation zone\n\n"
        
        if 'slopes_by_band' in comparison_results:
            summary_text += "SEN'S SLOPES BY BAND:\n"
            for band, slope in comparison_results['slopes_by_band'].items():
                sig_marker = "***" if comparison_results['significance_by_band'].get(band, False) else ""
                band_name = hypsometric_results[band]['band_name'] if band in hypsometric_results else band
                summary_text += f"{band_name}: {slope:.4f}/yr {sig_marker}\n"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    fig_path = get_figure_path(output_file, category='trends')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f"📊 Hypsometric analysis plot saved: {fig_path}")
    plt.show()


def create_melt_season_plot(results, monthly_results, df, output_file='athabasca_melt_season_analysis.png'):
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
    
    # Plot data with explicit labels for legend
    line1 = ax1.plot(years, albedo_means, 'o-', color='orange', alpha=0.8, linewidth=2, markersize=8, label='Melt Season Mean')
    
    # Trend line
    slope = results['sens_slope']['slope_per_year']
    intercept = results['sens_slope']['intercept']
    trend_line = slope * np.arange(len(years)) + intercept
    line2 = ax1.plot(years, trend_line, '--', color='red', linewidth=2, label="Sen's Slope Trend")
    
    # Highlight fire years - only add one to legend
    fire_years = [2017, 2018, 2021, 2023]
    fire_legend_added = False
    for fire_year in fire_years:
        if fire_year in years:
            fire_idx = np.where(years == fire_year)[0]
            if len(fire_idx) > 0:
                if not fire_legend_added:
                    ax1.scatter(fire_year, albedo_means[fire_idx[0]], color='darkred', s=150, marker='*', 
                               zorder=5, alpha=0.9, edgecolor='black', label='Fire Years')
                    fire_legend_added = True
                else:
                    ax1.scatter(fire_year, albedo_means[fire_idx[0]], color='darkred', s=150, marker='*', 
                               zorder=5, alpha=0.9, edgecolor='black')
    
    ax1.set_title(f'Melt Season Albedo Trend\n({results["period"]}, p={results["mann_kendall"]["p_value"]:.3f})')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Albedo')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best')
    
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
    
    # Save figure
    plt.tight_layout()
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📊 Plot saved: {fig_path}")


def create_melt_season_plot_with_elevation(annual_trends, df, filename='athabasca_melt_season_with_elevation.png'):
    """
    Create a melt season plot with elevation band indicators
    
    Args:
        annual_trends: Annual trend analysis results
        df: DataFrame with elevation band information
        filename: Output filename
    """
    plt.figure(figsize=(14, 10))
    
    # Extract data
    years = annual_trends['years']
    albedo_values = annual_trends['values']
    
    # Calculate annual means for each elevation band if available
    elevation_bands = None
    if 'elevation_band' in df.columns:
        elevation_bands = {}
        for band in ['above_median', 'near_median', 'below_median']:
            band_data = df[df['elevation_band'] == band]
            if not band_data.empty:
                band_annual = band_data.groupby('year')['albedo_mean'].mean()
                elevation_bands[band] = band_annual
    
    # Main plot - overall trend
    ax = plt.subplot(2, 1, 1)
    ax.plot(years, albedo_values, 'ko-', linewidth=2, markersize=8, label='Overall')
    
    # Add elevation band trends if available
    colors = {'above_median': '#2166ac', 'near_median': '#fee090', 'below_median': '#d73027'}
    labels = {'above_median': 'Above Median (>100m)', 'near_median': 'Near Median (±100m)', 
              'below_median': 'Below Median (>100m)'}
    
    if elevation_bands:
        for band, band_data in elevation_bands.items():
            ax.plot(band_data.index, band_data.values, 
                   color=colors.get(band, 'gray'), alpha=0.7, linewidth=1.5,
                   marker='o', markersize=4, label=labels.get(band, band))
    
    # Add trend line
    z = np.polyfit(years, albedo_values, 1)
    p = np.poly1d(z)
    ax.plot(years, p(years), "r--", alpha=0.8, linewidth=2, 
            label=f"Trend: {annual_trends['change_per_year']:.4f}/year")
    
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Mean Albedo', fontsize=12)
    ax.set_title('Athabasca Glacier Melt Season Albedo by Elevation Band', fontsize=14, fontweight='bold')
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    # Second subplot - elevation distribution
    ax2 = plt.subplot(2, 1, 2)
    
    if 'elevation' in df.columns:
        # Calculate median elevation
        median_elev = df['elevation'].median()
        
        # Create histogram
        n, bins, patches = ax2.hist(df['elevation'], bins=50, alpha=0.7, color='gray', edgecolor='black')
        
        # Color bins by elevation band
        for i, patch in enumerate(patches):
            bin_center = (bins[i] + bins[i+1]) / 2
            if bin_center > median_elev + 100:
                patch.set_facecolor(colors['above_median'])
            elif bin_center < median_elev - 100:
                patch.set_facecolor(colors['below_median'])
            else:
                patch.set_facecolor(colors['near_median'])
        
        # Add median line
        ax2.axvline(median_elev, color='black', linestyle='--', linewidth=2, 
                   label=f'Median: {median_elev:.0f}m')
        ax2.axvline(median_elev + 100, color='gray', linestyle=':', alpha=0.5)
        ax2.axvline(median_elev - 100, color='gray', linestyle=':', alpha=0.5)
        
        ax2.set_xlabel('Elevation (m)', fontsize=12)
        ax2.set_ylabel('Pixel Count', fontsize=12)
        ax2.set_title('Elevation Distribution with Williamson & Menounos Bands', fontsize=12)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_path = get_figure_path(filename, category='evolution')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"💾 Elevation-based melt season plot saved: {output_path}") 