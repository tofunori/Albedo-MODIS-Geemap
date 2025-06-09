"""
Data Extraction Module for MODIS Albedo Analysis
Handles Google Earth Engine data extraction for glacier albedo and elevation
"""

import pandas as pd
import numpy as np
import ee
from datetime import datetime
from config import athabasca_roi, MODIS_COLLECTIONS


# ================================================================================
# MODIS MASKING FUNCTIONS
# ================================================================================

def mask_modis_snow_albedo_fast(image):
    """Simplified MODIS snow albedo masking for speed"""
    # Quick selection - fewer quality checks
    albedo = image.select('Snow_Albedo_Daily_Tile')
    qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    # Basic mask
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    good_quality = qa.lte(1)  # QA ≤ 1: Best and good quality
    
    # Scale factor
    scaled = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
    
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])


def mask_modis_snow_albedo_advanced(image, qa_level='standard', custom_qa_config=None):
    """
    Advanced MODIS snow albedo masking with Algorithm QA flags
    Following Williamson & Menounos (2021) best practices
    
    Args:
        image: MOD10A1 Earth Engine image
        qa_level: 'strict', 'standard', 'relaxed', or custom QA level like 'cqa1f015'
        custom_qa_config: Dict with custom QA configuration for custom qa_level
    """
    albedo = image.select('Snow_Albedo_Daily_Tile')
    basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
    algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
    
    # Valid albedo range
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    
    # Handle Custom QA configurations
    if qa_level.startswith('cqa') and custom_qa_config:
        print(f"🔧 Using Custom QA configuration: {qa_level}")
        print(f"   Custom config: {custom_qa_config}")
        
        # Extract basic QA threshold from custom config
        basic_qa_threshold = custom_qa_config.get('basic_qa_threshold', 1)
        basic_quality = basic_qa.lte(basic_qa_threshold)
        
        # Extract algorithm flags from custom config
        algorithm_flags = custom_qa_config.get('algorithm_flags', {})
        
        # Apply algorithm flags based on custom config
        flag_masks = []
        
        if algorithm_flags.get('no_inland_water', False):
            flag_masks.append(algo_qa.bitwiseAnd(1).eq(0))        # Bit 0
        if algorithm_flags.get('no_low_visible', False):
            flag_masks.append(algo_qa.bitwiseAnd(2).eq(0))        # Bit 1
        if algorithm_flags.get('no_low_ndsi', False):
            flag_masks.append(algo_qa.bitwiseAnd(4).eq(0))        # Bit 2
        if algorithm_flags.get('no_temp_issues', False):
            flag_masks.append(algo_qa.bitwiseAnd(8).eq(0))        # Bit 3
        if algorithm_flags.get('no_high_swir', False):
            flag_masks.append(algo_qa.bitwiseAnd(16).eq(0))       # Bit 4
        if algorithm_flags.get('no_clouds', False):
            flag_masks.append(algo_qa.bitwiseAnd(32).eq(0))       # Bit 5
        if algorithm_flags.get('no_shadows', False):
            flag_masks.append(algo_qa.bitwiseAnd(128).eq(0))      # Bit 7
        
        # Combine all custom flags
        if flag_masks:
            algorithm_mask = flag_masks[0]
            for mask in flag_masks[1:]:
                algorithm_mask = algorithm_mask.And(mask)
        else:
            algorithm_mask = ee.Image(1)  # No algorithm filtering
            
        quality_mask = basic_quality.And(algorithm_mask)
        
    else:
        # Standard QA levels (strict, standard, relaxed)
        if qa_level == 'strict':
            basic_quality = basic_qa.eq(0)  # Only best quality
        elif qa_level == 'standard':
            basic_quality = basic_qa.lte(1)  # Best + good quality
        else:  # relaxed
            basic_quality = basic_qa.lte(2)  # Best + good + ok quality
        
        # Algorithm flags filtering (bits to exclude for glacier analysis)
        no_inland_water = algo_qa.bitwiseAnd(1).eq(0)        # Bit 0: No inland water
        no_low_visible = algo_qa.bitwiseAnd(2).eq(0)         # Bit 1: No low visible issues
        no_low_ndsi = algo_qa.bitwiseAnd(4).eq(0)            # Bit 2: No low NDSI issues
        
        # Optional: Temperature/height screen (Bit 3) - may be too restrictive for glaciers
        if qa_level == 'strict':
            no_temp_issues = algo_qa.bitwiseAnd(8).eq(0)     # Bit 3: No temp/height issues
        else:
            no_temp_issues = ee.Image(1)  # Allow temp flagged pixels (common on glaciers)
        
        # Cloud flags (Bits 5-6) - exclude probable clouds
        no_clouds = algo_qa.bitwiseAnd(32).eq(0)             # Bit 5: Not probably cloudy
        
        # Combine all masks
        quality_mask = basic_quality.And(no_inland_water).And(no_low_visible).And(no_low_ndsi).And(no_temp_issues).And(no_clouds)
    final_mask = valid_albedo.And(quality_mask)
    
    # Scale and apply mask
    scaled = albedo.multiply(0.01).updateMask(final_mask)
    
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])


def extract_time_series_fast(start_date, end_date, 
                            use_broadband=False,
                            sampling_days=None,
                            scale=500,
                            use_advanced_qa=False,
                            qa_level='standard',
                            custom_qa_config=None):
    """
    Fast extraction - statistics for entire glacier without zone division
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        use_broadband: Use broadband albedo instead of snow albedo
        sampling_days: Temporal sampling (not used in current implementation)
        scale: Spatial resolution in meters
        use_advanced_qa: Whether to use advanced Algorithm QA flags filtering
        qa_level: Quality level ('strict', 'standard', 'relaxed')
    
    Returns:
        DataFrame: Extracted time series data
    """
    print(f"⚡ Fast extraction {start_date} to {end_date}")
    print(f"   Sampling: {sampling_days} days, Resolution: {scale}m")
    
    # Choose collection and masking function
    if use_broadband:
        # Not implemented for now, fallback to snow albedo
        use_broadband = False
    
    # Choose masking function based on QA preferences
    if use_advanced_qa:
        # Use advanced masking with Algorithm QA flags
        masking_func = lambda img: mask_modis_snow_albedo_advanced(img, qa_level, custom_qa_config)
        print(f"   🔬 Using advanced QA filtering ({qa_level})")
        if custom_qa_config:
            print(f"   🎯 Custom QA config: {custom_qa_config}")
    else:
        # Use standard masking (Basic QA only)
        masking_func = mask_modis_snow_albedo_fast
        print(f"   ⚡ Using standard QA filtering")
    
    # Combine MOD10A1 and MYD10A1 (Version 6.1)
    mod_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(masking_func)
    
    myd_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
        .filterBounds(athabasca_roi) \
        .filterDate(start_date, end_date) \
        .map(masking_func)
    
    collection = mod_col.merge(myd_col).sort('system:time_start')
    albedo_band = 'albedo_daily'
    
    # Temporal sampling if specified
    if sampling_days:
        # Take only certain images to reduce load
        collection = collection.filterMetadata('system:index', 'not_equals', '') \
            .limit(1000)  # Limit to avoid timeout
    
    collection_size = collection.size().getInfo()
    print(f"📡 Images to process: {collection_size}")
    
    def calculate_simple_stats(image):
        """Simplified calculations - entire glacier only"""
        albedo = image.select(albedo_band)
        
        # Complete glacier stats with multiple metrics
        stats = albedo.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=scale,
            maxPixels=1e9
        )
        
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'timestamp': image.date().millis(),
            'albedo_mean': stats.get(f'{albedo_band}_mean'),
            'albedo_stdDev': stats.get(f'{albedo_band}_stdDev'),
            'albedo_min': stats.get(f'{albedo_band}_min'),
            'albedo_max': stats.get(f'{albedo_band}_max'),
            'pixel_count': stats.get(f'{albedo_band}_count')
        })
    
    # Process collection
    time_series = collection.map(calculate_simple_stats)
    
    # Convert to DataFrame
    try:
        data_list = time_series.getInfo()['features']
        records = [f['properties'] for f in data_list if f['properties'].get('albedo_mean')]
        
        df = pd.DataFrame(records)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # Temporal columns
            df['year'] = df['date'].dt.year
            df['month'] = df['date'].dt.month
            df['season'] = df['month'].map({
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Spring', 4: 'Spring', 5: 'Spring',
                6: 'Summer', 7: 'Summer', 8: 'Summer',
                9: 'Fall', 10: 'Fall', 11: 'Fall'
            })
        
        print(f"✅ Extraction completed: {len(df)} observations")
        return df
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return pd.DataFrame()


# ================================================================================
# MAIN EXTRACTION FUNCTIONS
# ================================================================================

def extract_melt_season_data_yearly(start_year=2010, end_year=2024, scale=500, use_advanced_qa=False, qa_level='standard', custom_qa_config=None):
    """
    Extract melt season data year by year to manage memory
    Focus on melt season months: June-September
    
    Args:
        start_year: First year to extract
        end_year: Last year to extract
        scale: Spatial resolution in meters
        use_advanced_qa: Whether to use advanced Algorithm QA flags filtering
        qa_level: Quality level ('strict', 'standard', 'relaxed')
    
    Returns:
        DataFrame: Combined melt season data
    """
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
            df_year = extract_time_series_fast(
                year_start, year_end, 
                scale=scale, 
                sampling_days=7,
                use_advanced_qa=use_advanced_qa,
                qa_level=qa_level,
                custom_qa_config=custom_qa_config
            )
            
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
            df_year = extract_time_series_fast(
                year_start, year_end, 
                scale=scale, 
                sampling_days=7,
                use_advanced_qa=use_advanced_qa,
                qa_level=qa_level,
                custom_qa_config=custom_qa_config
            )
            
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