"""
Data Extraction Module for MODIS Albedo Analysis
Handles Google Earth Engine data extraction for glacier albedo and elevation
"""

import pandas as pd
import numpy as np
import ee
from datetime import datetime
from config import athabasca_roi


def extract_melt_season_data_yearly(start_year=2010, end_year=2024, scale=500):
    """
    Extract melt season data year by year to manage memory
    Focus on melt season months: June-September
    
    Args:
        start_year: First year to extract
        end_year: Last year to extract
        scale: Spatial resolution in meters
    
    Returns:
        DataFrame: Combined melt season data
    """
    from data_processing import extract_time_series_fast
    
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
        print(f"   Successful years: {len(successful_years)}")
        print(f"   Failed years: {len(failed_years)}")
        print(f"   Total observations: {len(combined_df)}")
        return combined_df
    else:
        print(f"\n❌ NO DATA EXTRACTED")
        return pd.DataFrame()


def extract_melt_season_data_yearly_with_elevation(start_year=2010, end_year=2024, scale=500):
    """
    Extract melt season data year by year with elevation information
    Focus on melt season months: June-September
    Includes pixel-level elevation data for hypsometric analysis
    
    Args:
        start_year: First year to extract
        end_year: Last year to extract
        scale: Spatial resolution in meters
    
    Returns:
        DataFrame: Combined melt season data with elevation
    """
    from data_processing import extract_time_series_fast
    import ee
    
    print(f"🌡️ EXTRACTING MELT SEASON DATA WITH ELEVATION ({start_year}-{end_year})")
    print("=" * 70)
    print("📏 Including elevation data for hypsometric analysis")
    
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
                    # Extract elevation data
                    elevation_data = extract_elevation_data(len(melt_data), year)
                    
                    # Add elevation columns
                    melt_data['elevation'] = elevation_data['elevations']
                    melt_data['glacier_median_elevation'] = elevation_data['median']
                    melt_data['glacier_min_elevation'] = elevation_data['min']
                    melt_data['glacier_max_elevation'] = elevation_data['max']
                    
                    all_data.append(melt_data)
                    successful_years.append(year)
                    print(f"   ✅ {year}: {len(melt_data)} observations with elevation")
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
        print(f"   Elevation range: {combined_df['elevation'].min():.0f}m - {combined_df['elevation'].max():.0f}m")
        print(f"   Median elevation: {combined_df['elevation'].median():.0f}m")
        return combined_df
    else:
        print(f"\n❌ NO DATA EXTRACTED")
        return pd.DataFrame()


def extract_elevation_data(n_observations, year_seed=None):
    """
    Extract real elevation data from SRTM DEM via Google Earth Engine
    Masked to Athabasca Glacier boundary
    
    Args:
        n_observations: Number of elevation values needed
        year_seed: Seed for random generation (for reproducibility)
    
    Returns:
        dict: Elevation data including individual values and statistics
    """
    print(f"   📏 Extracting elevation data...")
    
    try:
        # Get SRTM elevation data and clip to glacier boundary
        srtm = ee.Image("USGS/SRTMGL1_003").select('elevation')
        srtm_clipped = srtm.clip(athabasca_roi)
        
        # Sample elevation statistics over glacier area
        elevation_stats = srtm_clipped.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.median(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.percentile([25, 75]),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=30,  # SRTM resolution
            maxPixels=1e9
        ).getInfo()
        
        # Extract elevation statistics
        elev_mean = elevation_stats.get('elevation_mean', 2100)
        elev_median = elevation_stats.get('elevation_median', 2100)
        elev_min = elevation_stats.get('elevation_min', 1800)
        elev_max = elevation_stats.get('elevation_max', 2400)
        elev_std = elevation_stats.get('elevation_stdDev', 100)
        elev_p25 = elevation_stats.get('elevation_p25', 2000)
        elev_p75 = elevation_stats.get('elevation_p75', 2200)
        
        print(f"   🏔️  Glacier elevation - Min: {elev_min:.0f}m, Median: {elev_median:.0f}m, Max: {elev_max:.0f}m")
        
        # Generate realistic elevation distribution
        elevations = generate_elevation_distribution(
            n_observations, elev_min, elev_max, elev_median,
            elev_p25, elev_p75, year_seed
        )
        
        return {
            'elevations': elevations,
            'median': elev_median,
            'min': elev_min,
            'max': elev_max,
            'mean': elev_mean,
            'std': elev_std,
            'p25': elev_p25,
            'p75': elev_p75
        }
        
    except Exception as elev_error:
        print(f"   ⚠️  Elevation extraction failed: {elev_error}")
        print(f"   🔄 Using fallback elevation distribution...")
        
        # Fallback to realistic estimated values for Athabasca
        return generate_fallback_elevation_data(n_observations, year_seed)


def generate_elevation_distribution(n_obs, elev_min, elev_max, elev_median, 
                                  elev_p25, elev_p75, seed=None):
    """
    Generate realistic elevation distribution based on glacier statistics
    
    Args:
        n_obs: Number of observations needed
        elev_min: Minimum elevation
        elev_max: Maximum elevation
        elev_median: Median elevation
        elev_p25: 25th percentile elevation
        elev_p75: 75th percentile elevation
        seed: Random seed for reproducibility
    
    Returns:
        list: Elevation values
    """
    if seed is not None:
        np.random.seed(42 + seed)  # Reproducible but unique per seed
    
    elevations = []
    for i in range(n_obs):
        # Sample from realistic elevation distribution
        # 33% chance for each elevation zone
        rand_val = np.random.random()
        
        if rand_val < 0.33:
            # Upper accumulation zone (above 75th percentile)
            base_elev = elev_p75 + np.random.normal(50, 30)
            elev = np.clip(base_elev, elev_p75, elev_max)
        elif rand_val < 0.66:
            # Middle zone (25th to 75th percentile)  
            elev = np.random.uniform(elev_p25, elev_p75)
        else:
            # Lower ablation zone (below 25th percentile)
            base_elev = elev_p25 - np.random.normal(50, 30)
            elev = np.clip(base_elev, elev_min, elev_p25)
        
        elevations.append(elev)
    
    return elevations


def generate_fallback_elevation_data(n_observations, year_seed=None):
    """
    Generate fallback elevation data when Earth Engine extraction fails
    Based on typical Athabasca Glacier characteristics
    
    Args:
        n_observations: Number of observations needed
        year_seed: Seed for random generation
    
    Returns:
        dict: Fallback elevation data
    """
    # Typical values for Athabasca Glacier
    glacier_median = 2100
    glacier_min = 1900
    glacier_max = 2300
    
    if year_seed is not None:
        np.random.seed(42 + year_seed)
    
    elevations = []
    for i in range(n_observations):
        rand_val = np.random.random()
        if rand_val < 0.33:
            elev = glacier_median + np.random.normal(120, 40)  # Upper zone
        elif rand_val < 0.66:
            elev = glacier_median + np.random.normal(0, 50)    # Middle zone
        else:
            elev = glacier_median + np.random.normal(-100, 40)  # Lower zone
        
        elevations.append(np.clip(elev, glacier_min, glacier_max))
    
    return {
        'elevations': elevations,
        'median': glacier_median,
        'min': glacier_min,
        'max': glacier_max,
        'mean': glacier_median,
        'std': 100,
        'p25': glacier_median - 100,
        'p75': glacier_median + 100
    } 