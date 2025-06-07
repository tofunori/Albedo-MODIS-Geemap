"""
Static Matplotlib Plots for MCD43A3 Spectral Analysis
Creates comprehensive static plots for MCD43A3 spectral analysis
Following Williamson & Menounos (2021) methodology
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def create_spectral_plot_fixed(df, spectral_results, output_file='athabasca_mcd43a3_spectral_analysis.png'):
    """
    Create comprehensive spectral albedo analysis plot - FIXED VERSION
    
    Args:
        df: Original MCD43A3 dataframe
        spectral_results: Results from analyze_spectral_trends()
        output_file: Output filename
    """
    if df.empty or not spectral_results:
        print("❌ No data to plot")
        return
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('MCD43A3 Spectral Albedo Analysis - Athabasca Glacier\n(Following Williamson & Menounos 2021)', 
                 fontsize=16, fontweight='bold')
    
    # Check available data
    print(f"📊 Plotting data: {len(df)} observations from {df['year'].min()} to {df['year'].max()}")
    
    # Calculate annual means with more robust aggregation
    albedo_columns = [col for col in df.columns if 'Albedo_BSA' in col and '_count' not in col]
    print(f"📈 Available albedo bands: {albedo_columns}")
    
    # Calculate both annual means and show individual points
    annual_data = df.groupby('year').agg({
        band: ['mean', 'count'] for band in albedo_columns if band in df.columns
    }).reset_index()
    
    # Flatten column names
    annual_data.columns = ['year'] + [f"{band}_{stat}" for band in albedo_columns for stat in ['mean', 'count']]
    
    # Also use raw data for scatter plots
    years = annual_data['year'].values
    all_years = df['year'].values
    
    # Plot 1: Visible vs NIR trends - IMPROVED
    ax1 = axes[0, 0]
    
    # Plot raw data points first (smaller, transparent)
    if 'Albedo_BSA_vis' in df.columns:
        ax1.scatter(df['year'], df['Albedo_BSA_vis'], color='blue', alpha=0.3, s=20, label='Visible (raw)')
    if 'Albedo_BSA_nir' in df.columns:
        ax1.scatter(df['year'], df['Albedo_BSA_nir'], color='red', alpha=0.3, s=20, label='NIR (raw)')
    
    # Plot annual means (larger, more visible)
    if 'Albedo_BSA_vis_mean' in annual_data.columns:
        vis_values = annual_data['Albedo_BSA_vis_mean'].values
        ax1.plot(years, vis_values, 'o-', color='blue', linewidth=3, markersize=8, 
                label='Visible (annual)', alpha=0.9)
        
        # Add trend line if available
        if 'visible' in spectral_results and 'Albedo_BSA_vis' in spectral_results['visible']:
            slope_data = spectral_results['visible']['Albedo_BSA_vis']['sens_slope']
            slope = slope_data['slope_per_year']
            intercept = slope_data['intercept']
            trend_x = np.array([years.min(), years.max()])
            trend_y = slope * (trend_x - years.min()) + vis_values[0]
            ax1.plot(trend_x, trend_y, '--', color='blue', linewidth=2, alpha=0.8, label='Visible trend')
    
    # Plot NIR bands  
    if 'Albedo_BSA_nir_mean' in annual_data.columns:
        nir_values = annual_data['Albedo_BSA_nir_mean'].values
        ax1.plot(years, nir_values, 'o-', color='red', linewidth=3, markersize=8,
                label='Near-Infrared (annual)', alpha=0.9)
        
        # Add trend line if available
        if 'near_infrared' in spectral_results and 'Albedo_BSA_nir' in spectral_results['near_infrared']:
            slope_data = spectral_results['near_infrared']['Albedo_BSA_nir']['sens_slope']
            slope = slope_data['slope_per_year']
            intercept = slope_data['intercept']
            trend_x = np.array([years.min(), years.max()])
            trend_y = slope * (trend_x - years.min()) + nir_values[0]
            ax1.plot(trend_x, trend_y, '--', color='red', linewidth=2, alpha=0.8, label='NIR trend')
    
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Albedo')
    ax1.set_title('Visible vs Near-Infrared Albedo Trends')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)  # Set proper albedo range
    
    # Plot 2: Individual spectral bands - IMPROVED
    ax2 = axes[0, 1]
    
    colors = ['red', 'green', 'blue', 'orange']
    band_labels = {
        'Albedo_BSA_Band1': 'Red (620-670nm)',
        'Albedo_BSA_Band2': 'NIR (841-876nm)', 
        'Albedo_BSA_Band3': 'Blue (459-479nm)',
        'Albedo_BSA_Band4': 'Green (545-565nm)'
    }
    
    for i, (band, label) in enumerate(band_labels.items()):
        annual_band = f'{band}_mean'
        if annual_band in annual_data.columns:
            values = annual_data[annual_band].values
            # Remove any NaN values
            valid_mask = ~np.isnan(values)
            if np.any(valid_mask):
                ax2.plot(years[valid_mask], values[valid_mask], 'o-', color=colors[i], 
                        linewidth=2, markersize=5, label=label, alpha=0.8)
        
        # Also plot raw data as scatter
        if band in df.columns:
            ax2.scatter(df['year'], df[band], color=colors[i], alpha=0.2, s=15)
    
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Albedo')
    ax2.set_title('Individual Spectral Bands')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)  # Set proper albedo range
    
    # Plot 3: Trend magnitude comparison - IMPROVED
    ax3 = axes[1, 0]
    
    trend_data = []
    trend_labels = []
    trend_colors = []
    
    for group_name, group_results in spectral_results.items():
        if group_name == 'spectral_comparison':
            continue
            
        for band, band_results in group_results.items():
            if 'change_percent_per_year' in band_results:
                trend_data.append(band_results['change_percent_per_year'])
                trend_labels.append(band.replace('Albedo_BSA_', '').replace('_', ' ').title())
                
                # Color by significance
                if band_results.get('significance') == '***':
                    trend_colors.append('darkred')
                elif band_results.get('significance') == '**':
                    trend_colors.append('orange')
                elif band_results.get('significance') == '*':
                    trend_colors.append('yellow')
                else:
                    trend_colors.append('lightcoral')
    
    if trend_data:
        bars = ax3.bar(range(len(trend_data)), trend_data, color=trend_colors, alpha=0.7, edgecolor='black')
        ax3.set_xticks(range(len(trend_labels)))
        ax3.set_xticklabels(trend_labels, rotation=45, ha='right')
        ax3.set_ylabel('Change (%/year)')
        ax3.set_title('Spectral Trend Magnitudes')
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax3.grid(True, alpha=0.3)
        
        # Add significance markers
        for i, (bar, change) in enumerate(zip(bars, trend_data)):
            if trend_colors[i] in ['darkred', 'orange', 'yellow']:  # Significant
                height = bar.get_height()
                marker = '***' if trend_colors[i] == 'darkred' else ('**' if trend_colors[i] == 'orange' else '*')
                ax3.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height > 0 else -0.1),
                        marker, ha='center', va='bottom' if height > 0 else 'top', 
                        fontweight='bold', fontsize=12)
    else:
        ax3.text(0.5, 0.5, 'No trend data available\n(insufficient observations)', 
                transform=ax3.transAxes, ha='center', va='center', fontsize=12)
        ax3.set_title('Spectral Trend Magnitudes')
    
    # Plot 4: Summary text - IMPROVED
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Create summary text
    summary_text = "MCD43A3 SPECTRAL ANALYSIS SUMMARY\n\n"
    
    # Data info
    summary_text += f"DATASET INFO:\n"
    summary_text += f"• Observations: {len(df)}\n"
    summary_text += f"• Period: {df['year'].min()}-{df['year'].max()}\n"
    summary_text += f"• Years with data: {len(df['year'].unique())}\n\n"
    
    if 'spectral_comparison' in spectral_results:
        comp = spectral_results['spectral_comparison']
        summary_text += f"VISIBLE vs NIR COMPARISON:\n"
        summary_text += f"• Visible change: {comp['visible_avg_change']:.2f}%/yr\n"
        summary_text += f"• NIR change: {comp['nir_avg_change']:.2f}%/yr\n\n"
        
        if comp['interpretation'] == 'visible_dominant':
            summary_text += "TARGET: VISIBLE-DOMINANT DECLINE\n"
            summary_text += "Consistent with light-absorbing\n"
            summary_text += "particle deposition (dust/soot)\n\n"
        elif comp['interpretation'] == 'nir_dominant':
            summary_text += "TARGET: NIR-DOMINANT DECLINE\n"
            summary_text += "May indicate snow grain\n"
            summary_text += "size effects from warming\n\n"
        else:
            summary_text += "TARGET: MIXED PATTERN\n"
            summary_text += "Both visible and NIR affected\n\n"
    else:
        summary_text += "WARNING: LIMITED DATA:\n"
        summary_text += "Insufficient observations for\n"
        summary_text += "robust trend analysis\n\n"
    
    summary_text += "WILLIAMSON & MENOUNOS PATTERN:\n"
    summary_text += "• Stronger visible decline suggests\n"
    summary_text += "  surface contamination effects\n"
    summary_text += "• MCD43A3 complements MOD10A1\n"
    summary_text += "  daily albedo analysis\n\n"
    
    summary_text += "*** = Statistically significant (p<0.05)"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='sans-serif',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    plt.tight_layout()
    
    # Save plot
    from src.paths import get_figure_path
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory and prevent display
    
    print(f"📊 Spectral analysis plot saved: {fig_path}")


def create_spectral_ratio_plot(df, output_file='athabasca_spectral_ratios.png'):
    """
    Create spectral ratio analysis plot for contamination detection
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        output_file: Output filename
    """
    if df.empty:
        print("❌ No data to plot")
        return
    
    # Import spectral analysis functions
    from src.analysis.spectral_analysis import calculate_spectral_ratios
    
    # Calculate spectral ratios
    df_ratios = calculate_spectral_ratios(df)
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Spectral Ratio Analysis - Contamination Detection\nAthabasca Glacier', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Visible/NIR ratio over time
    ax1 = axes[0, 0]
    if 'vis_nir_ratio' in df_ratios.columns:
        ax1.scatter(df_ratios['year'], df_ratios['vis_nir_ratio'], alpha=0.6, s=30)
        
        # Add trend line
        annual_ratios = df_ratios.groupby('year')['vis_nir_ratio'].mean()
        ax1.plot(annual_ratios.index, annual_ratios.values, 'r-', linewidth=2, 
                label='Annual mean')
        
        # Add contamination threshold
        threshold = np.percentile(df_ratios['vis_nir_ratio'].dropna(), 10)
        ax1.axhline(y=threshold, color='red', linestyle='--', alpha=0.7, 
                   label=f'10th percentile ({threshold:.3f})')
    
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Visible/NIR Ratio')
    ax1.set_title('Visible/NIR Spectral Ratio')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Red/NIR ratio (NDVI-like)
    ax2 = axes[0, 1]
    if 'red_nir_ratio' in df_ratios.columns:
        ax2.scatter(df_ratios['year'], df_ratios['red_nir_ratio'], alpha=0.6, s=30, color='green')
        
        annual_ratios = df_ratios.groupby('year')['red_nir_ratio'].mean()
        ax2.plot(annual_ratios.index, annual_ratios.values, 'g-', linewidth=2, 
                label='Annual mean')
    
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Red/NIR Ratio')
    ax2.set_title('Red/NIR Spectral Ratio')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Seasonal patterns in ratios
    ax3 = axes[1, 0]
    if 'vis_nir_ratio' in df_ratios.columns and 'month' in df_ratios.columns:
        monthly_ratios = df_ratios.groupby('month')['vis_nir_ratio'].agg(['mean', 'std'])
        
        ax3.errorbar(monthly_ratios.index, monthly_ratios['mean'], 
                    yerr=monthly_ratios['std'], marker='o', capsize=5)
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Visible/NIR Ratio')
        ax3.set_title('Seasonal Pattern in Vis/NIR Ratio')
        ax3.set_xticks(range(6, 10))
        ax3.set_xticklabels(['Jun', 'Jul', 'Aug', 'Sep'])
        ax3.grid(True, alpha=0.3)
    
    # Plot 4: Contamination events histogram
    ax4 = axes[1, 1]
    if 'vis_nir_ratio' in df_ratios.columns:
        ax4.hist(df_ratios['vis_nir_ratio'].dropna(), bins=30, alpha=0.7, 
                edgecolor='black')
        
        # Mark contamination threshold
        threshold = np.percentile(df_ratios['vis_nir_ratio'].dropna(), 10)
        ax4.axvline(x=threshold, color='red', linestyle='--', linewidth=2,
                   label=f'Contamination threshold')
        
        ax4.set_xlabel('Visible/NIR Ratio')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Distribution of Vis/NIR Ratios')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    from src.paths import get_figure_path
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory and prevent display
    
    print(f"📊 Spectral ratio plot saved: {fig_path}")


def create_multi_year_seasonal_evolution(df, output_file='mcd43a3_seasonal_evolution_grid.png'):
    """
    Create multi-panel plot showing seasonal evolution for each year
    Daily MCD43A3 data visualization with visible and NIR bands
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        output_file: Output filename
    """
    if df.empty:
        print("❌ No data to plot")
        return
    
    # Get unique years and determine grid layout
    years = sorted(df['year'].unique())
    n_years = len(years)
    
    # Calculate grid dimensions (aim for square-ish layout)
    n_cols = 4
    n_rows = int(np.ceil(n_years / n_cols))
    
    # Create figure with subplots - increased size and spacing
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(24, 6*n_rows))
    fig.suptitle('MCD43A3 Daily Albedo - Seasonal Evolution by Year\nAthabasca Glacier (Visible vs NIR)', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Flatten axes array for easier iteration
    axes_flat = axes.flatten() if n_years > 1 else [axes]
    
    # Color scheme
    vis_color = '#1f77b4'  # Blue for visible
    nir_color = '#d62728'  # Red for NIR
    band_colors = {
        'Albedo_BSA_Band1': '#ff7f0e',  # Orange (Red band)
        'Albedo_BSA_Band2': '#2ca02c',  # Green (NIR band)
        'Albedo_BSA_Band3': '#9467bd',  # Purple (Blue band)
        'Albedo_BSA_Band4': '#8c564b'   # Brown (Green band)
    }
    
    # Common y-axis limits for consistency
    y_min, y_max = 0.0, 1.0
    
    # Process each year
    for idx, year in enumerate(years):
        ax = axes_flat[idx]
        
        # Filter data for current year
        year_data = df[df['year'] == year].copy()
        
        if len(year_data) == 0:
            ax.text(0.5, 0.5, f'{year}\nNo Data', transform=ax.transAxes,
                   ha='center', va='center', fontsize=14)
            ax.set_xlim(152, 273)
            ax.set_ylim(y_min, y_max)
            continue
        
        # Sort by day of year
        year_data = year_data.sort_values('doy')
        
        # Plot main bands (Visible and NIR) as scatter plots
        if 'Albedo_BSA_vis' in year_data.columns:
            ax.scatter(year_data['doy'], year_data['Albedo_BSA_vis'], 
                      c=vis_color, s=25, alpha=0.7, edgecolors='white', linewidth=0.5,
                      label='Visible')
        
        if 'Albedo_BSA_nir' in year_data.columns:
            ax.scatter(year_data['doy'], year_data['Albedo_BSA_nir'], 
                      c=nir_color, s=25, alpha=0.7, marker='s', edgecolors='white', linewidth=0.5,
                      label='NIR')
        
        # Optionally add individual spectral bands as smaller scatter points
        for band, color in band_colors.items():
            if band in year_data.columns:
                ax.scatter(year_data['doy'], year_data[band], 
                          c=color, s=12, alpha=0.4, marker='.',
                          label=band.replace('Albedo_BSA_', '').replace('Band', 'B'))
        
        # Add title with year and data count
        ax.set_title(f'{year} (n={len(year_data)})', fontsize=12, fontweight='bold')
        
        # Set axis properties
        ax.set_xlim(152, 273)
        ax.set_ylim(y_min, y_max)
        ax.grid(True, alpha=0.3)
        
        # Add month labels on x-axis
        month_positions = [152, 182, 213, 244]  # Approximate DOY for start of each month
        month_labels = ['Jun', 'Jul', 'Aug', 'Sep']
        ax.set_xticks(month_positions)
        ax.set_xticklabels(month_labels)
        
        # Add axis labels for edge plots only
        if idx >= (n_rows - 1) * n_cols:
            ax.set_xlabel('Month')
        if idx % n_cols == 0:
            ax.set_ylabel('Albedo')
        
        # Add legend to first panel only
        if idx == 0:
            ax.legend(loc='upper right', fontsize=10, frameon=True, fancybox=True, 
                     shadow=True, framealpha=0.9)
        
        # Mark data gaps (if gap > 10 days)
        if len(year_data) > 1:
            doy_diff = year_data['doy'].diff()
            gap_indices = doy_diff[doy_diff > 10].index
            for gap_idx in gap_indices:
                gap_start = year_data.loc[gap_idx - 1, 'doy'] if gap_idx > 0 else year_data['doy'].iloc[0]
                gap_end = year_data.loc[gap_idx, 'doy']
                ax.axvspan(gap_start, gap_end, alpha=0.2, color='gray')
    
    # Remove empty subplots
    for idx in range(n_years, len(axes_flat)):
        fig.delaxes(axes_flat[idx])
    
    # Add common color bar or legend
    fig.text(0.02, 0.5, 'Albedo', va='center', rotation='vertical', fontsize=14)
    fig.text(0.5, 0.01, 'Melt Season Progress', ha='center', fontsize=14)
    
    # Add note about temporal resolution
    fig.text(0.98, 0.02, 'Daily values (16-day moving window)', 
             ha='right', fontsize=10, style='italic', color='gray')
    
    # Adjust layout with more spacing
    plt.tight_layout(rect=[0.03, 0.03, 0.97, 0.95], pad=2.0, h_pad=3.0, w_pad=2.0)
    
    # Save plot
    from src.paths import get_figure_path
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory and prevent display
    
    print(f"📊 Multi-year seasonal evolution plot saved: {fig_path}")


def create_seasonal_spectral_plot(df, output_file='athabasca_seasonal_spectral.png'):
    """
    Create seasonal spectral analysis plot
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        output_file: Output filename
    """
    if df.empty:
        print("❌ No data to plot")
        return
    
    # Import analysis functions
    from src.analysis.spectral_analysis import analyze_seasonal_patterns
    
    # Analyze seasonal patterns
    seasonal_results = analyze_seasonal_patterns(df)
    
    if not seasonal_results:
        print("❌ No seasonal data to plot")
        return
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Seasonal Spectral Analysis - Melt Season Patterns\nAthabasca Glacier', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Monthly averages for key bands
    ax1 = axes[0, 0]
    
    key_bands = ['Albedo_BSA_vis', 'Albedo_BSA_nir', 'Albedo_BSA_shortwave']
    colors = ['blue', 'red', 'green']
    
    for band, color in zip(key_bands, colors):
        if band in seasonal_results.get('monthly_statistics', {}):
            monthly_data = pd.DataFrame(seasonal_results['monthly_statistics'][band])
            ax1.errorbar(monthly_data['month'], monthly_data['mean'], 
                        yerr=monthly_data['std'], marker='o', color=color,
                        label=band.replace('Albedo_BSA_', '').title(), capsize=5)
    
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Albedo')
    ax1.set_title('Monthly Spectral Albedo Averages')
    ax1.set_xticks([6, 7, 8, 9])
    ax1.set_xticklabels(['Jun', 'Jul', 'Aug', 'Sep'])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Early vs Late season comparison
    ax2 = axes[0, 1]
    
    if 'seasonal_trends' in seasonal_results:
        bands = list(seasonal_results['seasonal_trends'].keys())
        early_values = [seasonal_results['seasonal_trends'][band]['early_season_mean'] 
                       for band in bands]
        late_values = [seasonal_results['seasonal_trends'][band]['late_season_mean'] 
                      for band in bands]
        
        x = np.arange(len(bands))
        width = 0.35
        
        ax2.bar(x - width/2, early_values, width, label='Early season (Jun-Jul)', alpha=0.8)
        ax2.bar(x + width/2, late_values, width, label='Late season (Aug-Sep)', alpha=0.8)
        
        ax2.set_xlabel('Spectral Band')
        ax2.set_ylabel('Albedo')
        ax2.set_title('Early vs Late Season Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels([band.replace('Albedo_BSA_', '') for band in bands], 
                           rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # Plot 3: Seasonal change percentages
    ax3 = axes[1, 0]
    
    if 'seasonal_trends' in seasonal_results:
        bands = list(seasonal_results['seasonal_trends'].keys())
        changes = [seasonal_results['seasonal_trends'][band]['seasonal_change_percent'] 
                  for band in bands]
        
        colors = ['red' if change < 0 else 'green' for change in changes]
        bars = ax3.bar(range(len(bands)), changes, color=colors, alpha=0.7, 
                      edgecolor='black')
        
        ax3.set_xlabel('Spectral Band')
        ax3.set_ylabel('Seasonal Change (%)')
        ax3.set_title('Seasonal Change (Late - Early)')
        ax3.set_xticks(range(len(bands)))
        ax3.set_xticklabels([band.replace('Albedo_BSA_', '') for band in bands], 
                           rotation=45)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax3.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, change in zip(bars, changes):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height > 0 else -0.5),
                    f'{change:.1f}%', ha='center', va='bottom' if height > 0 else 'top')
    
    # Plot 4: Summary statistics
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Create summary text
    summary_text = "SEASONAL PATTERN SUMMARY\n\n"
    summary_text += f"Analysis Period: {seasonal_results.get('analysis_period', 'N/A')}\n"
    summary_text += f"Total Observations: {seasonal_results.get('total_observations', 0)}\n\n"
    
    if 'seasonal_trends' in seasonal_results:
        summary_text += "SEASONAL TRENDS:\n"
        for band, trend_data in seasonal_results['seasonal_trends'].items():
            band_name = band.replace('Albedo_BSA_', '')
            change = trend_data['seasonal_change_percent']
            summary_text += f"• {band_name}: {change:+.1f}% change\n"
        
        summary_text += "\nINTERPRETATION:\n"
        summary_text += "• Negative values indicate decline\n"
        summary_text += "  from early to late season\n"
        summary_text += "• Greater visible decline suggests\n"
        summary_text += "  contamination accumulation\n"
        summary_text += "• Uniform decline may indicate\n"
        summary_text += "  grain size effects"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='sans-serif',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    plt.tight_layout()
    
    # Save plot
    from src.paths import get_figure_path
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory and prevent display
    
    print(f"📊 Seasonal spectral plot saved: {fig_path}")