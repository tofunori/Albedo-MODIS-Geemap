"""
MCD43A3 Broadband Albedo Analysis Workflow
Following Williamson & Menounos (2021) methodology

This module provides complementary analysis to MOD10A1 using:
- MCD43A3 16-day broadband albedo composites  
- Spectral albedo analysis (visible vs near-infrared)
- Black-sky and white-sky albedo products
- Better debris/contamination detection
- Comprehensive quality assessment filtering

Quality Assessment Features:
- Uses BRDF_Albedo_Band_Mandatory_Quality bands for each spectral band
- Filters for best quality full BRDF inversions only (QA = 0)
- Matches MOD10A1 strict quality filtering approach (QA = 0 only)
- Tracks pixel counts and quality statistics per band
- Ensures minimum pixel coverage (≥5 pixels) for reliable statistics
- Rejects magnitude inversions (QA = 1) for consistency with MOD10A1

PERFORMANCE OPTIMIZATIONS:
- Vectorized processing using Earth Engine map() functions
- Reduced API calls by combining operations
- Bulk band processing instead of sequential loops
- Following MOD10A1 fast extraction pattern
"""

import ee
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

def initialize_earth_engine():
    """Initialize Google Earth Engine"""
    try:
        ee.Initialize()
        print("✅ Google Earth Engine initialized")
    except Exception as e:
        print(f"❌ Error initializing Google Earth Engine: {e}")
        raise

def mask_mcd43a3_spectral_fast(image):
    """
    Fast vectorized masking for MCD43A3 spectral bands
    Optimized version following MOD10A1 fast approach
    """
    # Define all spectral bands and their corresponding quality bands
    spectral_bands = [
        'Albedo_BSA_Band1',     # Red (620-670 nm)
        'Albedo_BSA_Band2',     # NIR (841-876 nm) 
        'Albedo_BSA_Band3',     # Blue (459-479 nm)
        'Albedo_BSA_Band4',     # Green (545-565 nm)
        'Albedo_BSA_vis',       # Visible broadband
        'Albedo_BSA_nir',       # Near-infrared broadband
        'Albedo_BSA_shortwave'  # Shortwave broadband
    ]
    
    quality_bands = [
        'BRDF_Albedo_Band_Mandatory_Quality_Band1',
        'BRDF_Albedo_Band_Mandatory_Quality_Band2', 
        'BRDF_Albedo_Band_Mandatory_Quality_Band3',
        'BRDF_Albedo_Band_Mandatory_Quality_Band4',
        'BRDF_Albedo_Band_Mandatory_Quality_vis',
        'BRDF_Albedo_Band_Mandatory_Quality_nir',
        'BRDF_Albedo_Band_Mandatory_Quality_shortwave'
    ]
    
    # Select all spectral and quality bands at once
    spectral_image = image.select(spectral_bands)
    quality_image = image.select(quality_bands)
    
    # Apply vectorized quality filtering (QA = 0 for all bands)
    # Create quality masks for all bands at once
    quality_masks = quality_image.eq(0)  # All quality bands must equal 0
    
    # Apply quality masks to corresponding spectral bands
    masked_bands = []
    for i, band in enumerate(spectral_bands):
        # Get the corresponding quality mask
        quality_mask = quality_masks.select(quality_bands[i])
        
        # Apply mask and scale factor in one operation
        masked_band = spectral_image.select(band) \
            .updateMask(quality_mask) \
            .multiply(0.001) \
            .rename(f'{band}_masked')
        
        masked_bands.append(masked_band)
    
    # Combine all masked bands into a single image
    combined_image = ee.Image.cat(masked_bands)
    
    # Also include quality bands for statistics
    quality_renamed = quality_image.rename([f'{band}_quality' for band in spectral_bands])
    
    # Combine spectral and quality data
    final_image = combined_image.addBands(quality_renamed)
    
    return final_image.copyProperties(image, ['system:time_start'])

def extract_mcd43a3_data_fixed(start_year=2015, end_year=2024, glacier_mask=None):
    """
    FIXED MCD43A3 extraction with simplified, robust processing
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis  
        glacier_mask: Glacier boundary mask (if None, uses config)
    
    Returns:
        DataFrame: MCD43A3 albedo data with spectral bands
    """
    from src.config import athabasca_roi
    
    if glacier_mask is None:
        glacier_mask = athabasca_roi
    
    print(f"🌈 EXTRACTING MCD43A3 DATA - FIXED VERSION ({start_year}-{end_year})")
    print("=" * 70)
    print("📡 Product: MODIS/061/MCD43A3 (16-day broadband albedo)")
    print("🔬 Following Williamson & Menounos (2021) spectral methodology")
    print("✅ FIXED: Simplified robust processing")
    
    # MCD43A3 collection
    mcd43a3 = ee.ImageCollection("MODIS/061/MCD43A3")
    
    # Filter to melt season for all years at once
    start_date = f"{start_year}-06-01"
    end_date = f"{end_year}-09-30"
    
    # Apply filtering
    collection = mcd43a3.filterDate(start_date, end_date).filterBounds(glacier_mask)
    
    collection_size = collection.size().getInfo()
    
    if collection_size == 0:
        print("❌ No MCD43A3 data available for the specified period")
        return pd.DataFrame()
    
    print(f"📊 Found {collection_size} MCD43A3 composites")
    
    def process_image_simple(image):
        """
        Simplified image processing for better reliability
        """
        # Define the key spectral bands we need
        spectral_bands = {
            'Albedo_BSA_vis': 'BRDF_Albedo_Band_Mandatory_Quality_vis',
            'Albedo_BSA_nir': 'BRDF_Albedo_Band_Mandatory_Quality_nir',
            'Albedo_BSA_Band1': 'BRDF_Albedo_Band_Mandatory_Quality_Band1',  # Red
            'Albedo_BSA_Band2': 'BRDF_Albedo_Band_Mandatory_Quality_Band2',  # NIR
            'Albedo_BSA_Band3': 'BRDF_Albedo_Band_Mandatory_Quality_Band3',  # Blue
            'Albedo_BSA_Band4': 'BRDF_Albedo_Band_Mandatory_Quality_Band4'   # Green
        }
        
        # Extract date information
        date = ee.Date(image.get('system:time_start'))
        
        # Process each band individually and combine results
        band_stats = {}
        
        for albedo_band, quality_band in spectral_bands.items():
            # Apply quality mask (QA = 0 only)
            quality_mask = image.select(quality_band).eq(0)
            
            # Apply mask and scale
            masked_albedo = image.select(albedo_band).updateMask(quality_mask).multiply(0.001)
            
            # Calculate statistics
            stats = masked_albedo.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
                geometry=glacier_mask,
                scale=500,
                maxPixels=1e9
            )
            
            # Extract mean and count
            mean_val = stats.get(f'{albedo_band}_mean')
            count_val = stats.get(f'{albedo_band}_count')
            
            band_stats[albedo_band] = mean_val
            band_stats[f'{albedo_band}_count'] = count_val
        
        # Combine all statistics
        all_properties = {
            'date': date.format('YYYY-MM-dd'),
            'year': date.get('year'),
            'month': date.get('month'),
            'doy': date.getRelative('day', 'year')
        }
        all_properties.update(band_stats)
        
        return ee.Feature(None, all_properties)
    
    # Process all images
    print("⚡ Processing all images...")
    processed_collection = collection.map(process_image_simple)
    
    # Convert to DataFrame
    try:
        print("📥 Downloading results...")
        data_list = processed_collection.getInfo()['features']
        
        if not data_list:
            print("❌ No valid data extracted")
            return pd.DataFrame()
        
        # Process results into DataFrame
        records = []
        
        print(f"🔍 Processing {len(data_list)} features...")
        
        for feature in data_list:
            props = feature['properties']
            
            # Check if we have valid data (at least 5 pixels for key bands)
            vis_count = props.get('Albedo_BSA_vis_count', 0)
            nir_count = props.get('Albedo_BSA_nir_count', 0)
            
            if vis_count >= 5 and nir_count >= 5:
                # Clean the record - only keep valid (non-null) values
                record = {}
                for key, value in props.items():
                    if value is not None:
                        record[key] = value
                
                # Ensure we have the minimum required fields
                if 'date' in record and 'Albedo_BSA_vis' in record and 'Albedo_BSA_nir' in record:
                    records.append(record)
        
        if not records:
            print("❌ No records passed quality filtering")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"✅ Successfully extracted {len(df)} valid observations")
        print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"📊 Years covered: {sorted(df['year'].unique())}")
        
        # Show some sample data
        print("\n📋 Sample of extracted data:")
        sample_cols = ['date', 'year', 'Albedo_BSA_vis', 'Albedo_BSA_nir']
        available_cols = [col for col in sample_cols if col in df.columns]
        print(df[available_cols].head(10).to_string(index=False))
        
        return df
        
    except Exception as e:
        print(f"❌ Error during data extraction: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def analyze_data_quality(df):
    """
    Analyze MCD43A3 data quality statistics
    
    Args:
        df: DataFrame with MCD43A3 spectral albedo data
    
    Returns:
        dict: Quality analysis results
    """
    if df.empty:
        return {}
    
    print(f"\n🔍 MCD43A3 DATA QUALITY ASSESSMENT")
    print("=" * 50)
    
    quality_results = {}
    
    # Spectral bands to analyze
    spectral_bands = [
        'Albedo_BSA_Band1', 'Albedo_BSA_Band2', 'Albedo_BSA_Band3', 'Albedo_BSA_Band4',
        'Albedo_BSA_vis', 'Albedo_BSA_nir', 'Albedo_BSA_shortwave'
    ]
    
    for band in spectral_bands:
        if band in df.columns:
            # Data availability
            total_obs = len(df)
            valid_obs = df[band].notna().sum()
            availability = (valid_obs / total_obs) * 100 if total_obs > 0 else 0
            
            # Quality statistics (if available)
            quality_col = f"{band}_quality"
            pixels_col = f"{band}_pixels"
            
            if quality_col in df.columns:
                avg_quality = df[quality_col].mean()
                good_quality = (df[quality_col] <= 0).sum()  # Full BRDF inversions (best quality)
                moderate_quality = (df[quality_col] == 1).sum()  # Magnitude inversions (now rejected)
            else:
                avg_quality = None
                good_quality = None
                moderate_quality = None
            
            if pixels_col in df.columns:
                avg_pixels = df[pixels_col].mean()
                min_pixels = df[pixels_col].min()
                max_pixels = df[pixels_col].max()
            else:
                avg_pixels = min_pixels = max_pixels = None
            
            quality_results[band] = {
                'total_observations': total_obs,
                'valid_observations': valid_obs,
                'data_availability': availability,
                'average_quality': avg_quality,
                'full_inversions': good_quality,
                'magnitude_inversions': moderate_quality,
                'average_pixels': avg_pixels,
                'min_pixels': min_pixels,
                'max_pixels': max_pixels
            }
            
            print(f"📊 {band}:")
            print(f"   Data availability: {availability:.1f}% ({valid_obs}/{total_obs})")
            if avg_quality is not None:
                print(f"   Average quality: {avg_quality:.2f}")
                print(f"   Best quality (QA=0): {good_quality}, Lower quality (QA=1, rejected): {moderate_quality}")
            if avg_pixels is not None:
                print(f"   Pixel coverage: {avg_pixels:.1f} avg, {min_pixels}-{max_pixels} range")
    
    return quality_results

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
    summary_text += f"📊 DATASET INFO:\n"
    summary_text += f"• Observations: {len(df)}\n"
    summary_text += f"• Period: {df['year'].min()}-{df['year'].max()}\n"
    summary_text += f"• Years with data: {len(df['year'].unique())}\n\n"
    
    if 'spectral_comparison' in spectral_results:
        comp = spectral_results['spectral_comparison']
        summary_text += f"VISIBLE vs NIR COMPARISON:\n"
        summary_text += f"• Visible change: {comp['visible_avg_change']:.2f}%/yr\n"
        summary_text += f"• NIR change: {comp['nir_avg_change']:.2f}%/yr\n\n"
        
        if comp['interpretation'] == 'visible_dominant':
            summary_text += "🎯 VISIBLE-DOMINANT DECLINE\n"
            summary_text += "Consistent with light-absorbing\n"
            summary_text += "particle deposition (dust/soot)\n\n"
        elif comp['interpretation'] == 'nir_dominant':
            summary_text += "🎯 NIR-DOMINANT DECLINE\n"
            summary_text += "May indicate snow grain\n"
            summary_text += "size effects from warming\n\n"
        else:
            summary_text += "🎯 MIXED PATTERN\n"
            summary_text += "Both visible and NIR affected\n\n"
    else:
        summary_text += "⚠️ LIMITED DATA:\n"
        summary_text += "Insufficient observations for\n"
        summary_text += "robust trend analysis\n\n"
    
    summary_text += "WILLIAMSON & MENOUNOS PATTERN:\n"
    summary_text += "• Stronger visible decline suggests\n"
    summary_text += "  surface contamination effects\n"
    summary_text += "• MCD43A3 complements MOD10A1\n"
    summary_text += "  daily albedo analysis\n\n"
    
    summary_text += "*** = Statistically significant (p<0.05)"
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    plt.tight_layout()
    
    # Save plot
    from src.paths import get_figure_path
    fig_path = get_figure_path(output_file, category='melt_season')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📊 Spectral analysis plot saved: {fig_path}")

def run_mcd43a3_analysis(start_year=2015, end_year=2024):
    """
    Complete MCD43A3 broadband albedo analysis workflow
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
    
    Returns:
        dict: Complete MCD43A3 analysis results
    """
    print("🌈 ATHABASCA GLACIER MCD43A3 BROADBAND ALBEDO ANALYSIS")
    print("=" * 80)
    print("📡 Product: MODIS MCD43A3 16-day broadband albedo composites")
    print("📚 Method: Following Williamson & Menounos (2021) spectral methodology")
    print("🎯 Focus: Spectral albedo analysis for contamination detection")
    
    # Initialize Earth Engine
    initialize_earth_engine()
    
    # Extract MCD43A3 data
    df = extract_mcd43a3_data_fixed(start_year=start_year, end_year=end_year)
    
    if df.empty:
        print("❌ No MCD43A3 data extracted. Analysis cannot proceed.")
        return None
    
    # Export raw data
    from src.paths import get_output_path
    
    csv_path = get_output_path('athabasca_mcd43a3_spectral_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Raw MCD43A3 data exported: {csv_path}")
    
    # Analyze data quality
    quality_results = analyze_data_quality(df)
    
    # Perform spectral trend analysis
    spectral_results = analyze_spectral_trends(df)
    
    if not spectral_results:
        print("❌ Spectral trend analysis failed.")
        return None
    
    # Create visualization
    create_spectral_plot_fixed(df, spectral_results)
    
    # Export results summary
    results_path = get_output_path('athabasca_mcd43a3_results.csv')
    
    # Create summary DataFrame for export
    summary_data = []
    for group_name, group_results in spectral_results.items():
        if group_name == 'spectral_comparison':
            continue
            
        for band, band_results in group_results.items():
            if 'change_percent_per_year' in band_results:
                summary_data.append({
                    'spectral_group': group_name,
                    'band': band,
                    'change_percent_per_year': band_results['change_percent_per_year'],
                    'mann_kendall_p_value': band_results['mann_kendall']['p_value'],
                    'trend_direction': band_results['mann_kendall']['trend'],
                    'significance': band_results['significance'],
                    'n_years': band_results['n_years']
                })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(results_path, index=False)
        print(f"💾 MCD43A3 results exported: {results_path}")
    
    # Final summary
    print(f"\n🎉 MCD43A3 SPECTRAL ANALYSIS COMPLETE!")
    print("=" * 60)
    print(f"📊 Period analyzed: {start_year}-{end_year}")
    print(f"📈 Total observations: {len(df)}")
    
    if 'spectral_comparison' in spectral_results:
        comp = spectral_results['spectral_comparison']
        print(f"🔍 Key finding: {comp['interpretation'].replace('_', ' ').title()} decline pattern")
        print(f"📊 Visible change: {comp['visible_avg_change']:.2f}%/year")
        print(f"📊 NIR change: {comp['nir_avg_change']:.2f}%/year")
    
    print(f"💾 Files generated:")
    print(f"   📊 Spectral plot: figures/melt_season/athabasca_mcd43a3_spectral_analysis.png")
    print(f"   💾 Raw data: outputs/csv/athabasca_mcd43a3_spectral_data.csv")
    print(f"   💾 Results: outputs/csv/athabasca_mcd43a3_results.csv")
    
    # Compile comprehensive results
    comprehensive_results = {
        'spectral_analysis': spectral_results,
        'quality_analysis': quality_results,
        'raw_data': df,
        'dataset_info': {
            'total_observations': len(df),
            'years_analyzed': sorted(df['year'].unique()),
            'period': f"{start_year}-{end_year}",
            'product': "MODIS MCD43A3 16-day broadband albedo",
            'method': "Williamson & Menounos (2021) Spectral Analysis",
            'quality_filtering': "BRDF_Albedo_Band_Mandatory_Quality (QA=0 only, matching MOD10A1)"
        }
    }
    
    return comprehensive_results 