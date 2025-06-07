"""
MCD43A3 Data Extraction Module
Handles extraction of MODIS MCD43A3 16-day broadband albedo data
Following Williamson & Menounos (2021) methodology
"""

import ee
import pandas as pd
from datetime import datetime, timedelta


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
    UPDATED: Now includes Williamson & Menounos (2021) albedo range filters (0.05-0.99)
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
    
    # Apply vectorized quality filtering (QA ≤ 1: Full + magnitude inversions)
    quality_masks = quality_image.lte(1)
    
    # Apply quality masks and albedo range filters to corresponding spectral bands
    masked_bands = []
    for i, band in enumerate(spectral_bands):
        # Get the corresponding quality mask
        quality_mask = quality_masks.select(quality_bands[i])
        
        # Apply scaling first
        scaled_band = spectral_image.select(band).multiply(0.001)
        
        # Apply Williamson & Menounos (2021) albedo range filters
        # Exclude shadow-affected pixels (<0.05) and unrealistic values (>0.99)
        albedo_range_mask = scaled_band.gte(0.05).And(scaled_band.lte(0.99))
        
        # Combine quality and albedo range masks
        combined_mask = quality_mask.And(albedo_range_mask)
        
        # Apply combined mask
        masked_band = scaled_band.updateMask(combined_mask).rename(f'{band}_masked')
        
        masked_bands.append(masked_band)
    
    # Combine all masked bands into a single image
    combined_image = ee.Image.cat(masked_bands)
    
    # Also include quality bands for statistics
    quality_renamed = quality_image.rename([f'{band}_quality' for band in spectral_bands])
    
    # Combine spectral and quality data
    final_image = combined_image.addBands(quality_renamed)
    
    return final_image.copyProperties(image, ['system:time_start'])


def extract_mcd43a3_data_fixed(start_year=2010, end_year=2024, glacier_mask=None):
    """
    FIXED MCD43A3 extraction with simplified, robust processing
    WARNING: Limited to smaller datasets to avoid 5000-element limit
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis  
        glacier_mask: Glacier boundary mask (if None, uses config)
    
    Returns:
        DataFrame: MCD43A3 albedo data with spectral bands
    """
    # For large datasets, redirect to yearly processing
    if (end_year - start_year + 1) > 8:
        print("⚠️ Large dataset detected, using yearly processing...")
        return extract_mcd43a3_data_yearly(start_year, end_year, glacier_mask)
    
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
    
    if collection_size > 4000:
        print("⚠️ Large collection detected, using yearly processing instead...")
        return extract_mcd43a3_data_yearly(start_year, end_year, glacier_mask)
    
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
            # Apply quality mask (QA ≤ 1: full + magnitude inversions)
            quality_mask = image.select(quality_band).lte(1)
            
            # Apply scaling first
            scaled_albedo = image.select(albedo_band).multiply(0.001)
            
            # Apply Williamson & Menounos (2021) albedo range filters
            # Exclude shadow-affected pixels (<0.05) and unrealistic values (>0.99)
            albedo_range_mask = scaled_albedo.gte(0.05).And(scaled_albedo.lte(0.99))
            
            # Combine quality and albedo range masks
            combined_mask = quality_mask.And(albedo_range_mask)
            
            # Apply combined mask
            masked_albedo = scaled_albedo.updateMask(combined_mask)
            
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


def extract_mcd43a3_data_yearly(start_year=2010, end_year=2024, glacier_mask=None):
    """
    YEARLY MCD43A3 extraction to avoid 5000-element limit
    Processes data year by year to manage large datasets
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis  
        glacier_mask: Glacier boundary mask (if None, uses config)
    
    Returns:
        DataFrame: Combined MCD43A3 albedo data with spectral bands
    """
    from src.config import athabasca_roi
    
    if glacier_mask is None:
        glacier_mask = athabasca_roi
    
    print(f"🌈 EXTRACTING MCD43A3 DATA YEARLY ({start_year}-{end_year})")
    print("=" * 70)
    print("📡 Product: MODIS/061/MCD43A3 (16-day broadband albedo)")
    print("🔬 Following Williamson & Menounos (2021) spectral methodology")
    print("⚡ YEARLY processing to avoid 5000-element limit")
    
    all_data = []
    successful_years = []
    failed_years = []
    
    for year in range(start_year, end_year + 1):
        print(f"\n📡 Extracting MCD43A3 data for {year} melt season...")
        
        try:
            # Extract melt season for this year (June-September)
            year_start = f'{year}-06-01'
            year_end = f'{year}-09-30'
            
            # MCD43A3 collection for this year only
            mcd43a3 = ee.ImageCollection("MODIS/061/MCD43A3")
            collection = mcd43a3.filterDate(year_start, year_end).filterBounds(glacier_mask)
            
            collection_size = collection.size().getInfo()
            
            if collection_size == 0:
                failed_years.append(year)
                print(f"   ❌ {year}: No MCD43A3 data available")
                continue
            
            print(f"   📊 Found {collection_size} MCD43A3 composites for {year}")
            
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
                    # Apply quality mask (QA ≤ 1: full + magnitude inversions)
                    quality_mask = image.select(quality_band).lte(1)
                    
                    # Apply scaling first
                    scaled_albedo = image.select(albedo_band).multiply(0.001)
                    
                    # Apply Williamson & Menounos (2021) albedo range filters
                    # Exclude shadow-affected pixels (<0.05) and unrealistic values (>0.99)
                    albedo_range_mask = scaled_albedo.gte(0.05).And(scaled_albedo.lte(0.99))
                    
                    # Combine quality and albedo range masks
                    combined_mask = quality_mask.And(albedo_range_mask)
                    
                    # Apply combined mask
                    masked_albedo = scaled_albedo.updateMask(combined_mask)
                    
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
            
            # Process all images for this year
            processed_collection = collection.map(process_image_simple)
            
            # Convert to DataFrame for this year
            print(f"   📥 Downloading {year} results...")
            data_list = processed_collection.getInfo()['features']
            
            if not data_list:
                failed_years.append(year)
                print(f"   ❌ {year}: No valid data extracted")
                continue
            
            # Process results into records
            year_records = []
            
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
                        year_records.append(record)
            
            if year_records:
                all_data.extend(year_records)
                successful_years.append(year)
                print(f"   ✅ {year}: {len(year_records)} valid observations")
            else:
                failed_years.append(year)
                print(f"   ❌ {year}: No records passed quality filtering")
            
        except Exception as e:
            failed_years.append(year)
            print(f"   ❌ {year}: Error - {str(e)[:50]}...")
            continue
    
    if not all_data:
        print(f"\n❌ NO DATA EXTRACTED FROM ANY YEAR")
        return pd.DataFrame()
    
    # Create combined DataFrame
    df = pd.DataFrame(all_data)
    
    # Convert date column
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"\n✅ YEARLY EXTRACTION COMPLETE")
    print(f"   Successful years: {len(successful_years)} ({successful_years})")
    print(f"   Failed years: {len(failed_years)} ({failed_years})")
    print(f"   Total observations: {len(df)}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Years covered: {sorted(df['year'].unique())}")
    
    # Show some sample data
    print(f"\n📋 Sample of extracted data:")
    sample_cols = ['date', 'year', 'Albedo_BSA_vis', 'Albedo_BSA_nir']
    available_cols = [col for col in sample_cols if col in df.columns]
    print(df[available_cols].head(10).to_string(index=False))
    
    return df


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