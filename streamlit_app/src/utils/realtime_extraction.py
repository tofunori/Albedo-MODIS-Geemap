"""
Real-time MODIS Data Extraction with Advanced QA Filtering
Connects to Google Earth Engine to extract live MODIS data with various QA levels
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import ee
from .ee_utils import initialize_earth_engine


# QA Level Configurations for Real-time Extraction (3 Optimal Levels)
QA_CONFIGURATIONS = {
    'standard_qa': {
        'name': 'Standard QA',
        'description': 'Basic QA filtering - Maximum data coverage',
        'mod10a1_basic_qa_threshold': 1,  # QA ≤ 1 (best + good)
        'mod10a1_use_algorithm_flags': False,
        'mcd43a3_qa_threshold': 1,  # Allow magnitude inversions
        'expected_retention': 1.0,  # 100% retention (baseline)
        'use_case': 'Exploratory analysis, maximum temporal coverage'
    },
    'advanced_balanced': {
        'name': 'Advanced QA Balanced',
        'description': 'Optimal balance - Recommended for most research',
        'mod10a1_basic_qa_threshold': 2,  # QA ≤ 2 (best + good + ok)
        'mod10a1_use_algorithm_flags': True,
        'mod10a1_algorithm_strict': False,  # Only critical flags filtered
        'mod10a1_filter_temp_height': False,  # Allow temp/height (common on glaciers)
        'mod10a1_filter_spatial': False,     # Allow spatial flagged pixels
        'mcd43a3_qa_threshold': 1,
        'expected_retention': 0.80,  # ~80% retention (based on your results: 96.6%)
        'use_case': 'Most research analyses, trend studies, routine monitoring'
    },
    'advanced_strict': {
        'name': 'Advanced QA Strict',
        'description': 'High quality filtering - Publication grade',
        'mod10a1_basic_qa_threshold': 1,  # QA ≤ 1 (best + good)
        'mod10a1_use_algorithm_flags': True,
        'mod10a1_algorithm_strict': False,  # Standard algorithm filtering
        'mod10a1_filter_temp_height': True,   # Filter temp/height issues
        'mod10a1_filter_spatial': True,      # Filter spatial issues
        'mcd43a3_qa_threshold': 0,  # Full BRDF inversions only
        'expected_retention': 0.30,  # ~30% retention (based on your results: 27.6%)
        'use_case': 'Publication work, method validation, high-quality case studies'
    }
}


def mask_mod10a1_with_advanced_qa(image, qa_config):
    """
    Apply advanced QA filtering to MOD10A1/MYD10A1 image
    Implements granular QA filtering with configurable algorithm flags
    
    Args:
        image: MOD10A1/MYD10A1 Earth Engine image
        qa_config: QA configuration dictionary
    
    Returns:
        ee.Image: Masked albedo image
    """
    albedo = image.select('Snow_Albedo_Daily_Tile')
    basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    # Valid albedo range (5-99 before scaling)
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    
    # Basic QA filtering
    basic_quality = basic_qa.lte(qa_config['mod10a1_basic_qa_threshold'])
    
    # Initialize mask with basic criteria
    final_mask = valid_albedo.And(basic_quality)
    
    # Apply algorithm flags if requested
    if qa_config['mod10a1_use_algorithm_flags']:
        try:
            algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
            
            # Critical flags (ALWAYS filtered for all advanced levels)
            no_inland_water = algo_qa.bitwiseAnd(1).eq(0)   # Bit 0: No inland water
            no_low_visible = algo_qa.bitwiseAnd(2).eq(0)    # Bit 1: No low visible
            no_low_ndsi = algo_qa.bitwiseAnd(4).eq(0)       # Bit 2: No low NDSI
            no_clouds = algo_qa.bitwiseAnd(32).eq(0)        # Bit 5: No probable clouds
            
            # Start with critical flags
            algorithm_mask = no_inland_water.And(no_low_visible).And(no_low_ndsi).And(no_clouds)
            
            # Configurable: Temperature/height screening (Bit 3)
            if qa_config.get('mod10a1_filter_temp_height', False):
                no_temp_issues = algo_qa.bitwiseAnd(8).eq(0)  # Bit 3: No temp/height issues
                algorithm_mask = algorithm_mask.And(no_temp_issues)
            
            # Configurable: Spatial screening (Bit 4)
            if qa_config.get('mod10a1_filter_spatial', False):
                no_spatial_issues = algo_qa.bitwiseAnd(16).eq(0)  # Bit 4: No spatial issues
                algorithm_mask = algorithm_mask.And(no_spatial_issues)
            
            # Extra strict filtering (all flags) if requested
            if qa_config.get('mod10a1_algorithm_strict', False):
                # Additional flags for maximum strictness
                no_radiometric_issues = algo_qa.bitwiseAnd(64).eq(0)  # Bit 6: No radiometric issues
                algorithm_mask = algorithm_mask.And(no_radiometric_issues)
                
                # Also ensure temp/height and spatial are filtered in strict mode
                if not qa_config.get('mod10a1_filter_temp_height', False):
                    no_temp_issues = algo_qa.bitwiseAnd(8).eq(0)
                    algorithm_mask = algorithm_mask.And(no_temp_issues)
                if not qa_config.get('mod10a1_filter_spatial', False):
                    no_spatial_issues = algo_qa.bitwiseAnd(16).eq(0)
                    algorithm_mask = algorithm_mask.And(no_spatial_issues)
            
            # Combine with basic mask
            final_mask = final_mask.And(algorithm_mask)
            
        except Exception:
            # If algorithm flags not available, continue with basic QA only
            pass
    
    # Apply mask and scale
    scaled = albedo.multiply(0.01).updateMask(final_mask)
    
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])


def mask_mcd43a3_with_qa(image, qa_config):
    """
    Apply QA filtering to MCD43A3 image
    
    Args:
        image: MCD43A3 Earth Engine image
        qa_config: QA configuration dictionary
    
    Returns:
        ee.Image: Masked albedo image
    """
    albedo = image.select('Albedo_BSA_shortwave')
    qa_band1 = image.select('BRDF_Albedo_Band_Mandatory_Quality_Band1')
    
    # Apply quality threshold
    good_quality = qa_band1.lte(qa_config['mcd43a3_qa_threshold'])
    
    # Apply quality mask and scale (MCD43A3 uses 0.001 scale factor)
    masked = albedo.updateMask(good_quality).multiply(0.001)
    
    # Additional range filter (0.0 to 1.0 for albedo)
    valid_range = masked.gte(0.0).And(masked.lte(1.0))
    masked = masked.updateMask(valid_range)
    
    return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])


@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def extract_modis_time_series_realtime(start_date, end_date, qa_level='advanced_standard', 
                                     product='MOD10A1', max_observations=200):
    """
    Extract MODIS time series data in real-time from Google Earth Engine
    Uses actual QA filtering (not simulation)
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        qa_level: QA filtering level
        product: 'MOD10A1' for snow albedo or 'MCD43A3' for broadband albedo
        max_observations: Maximum number of observations to extract
    
    Returns:
        pd.DataFrame: Time series data with real QA filtering applied
    """
    # Initialize Earth Engine
    if not initialize_earth_engine():
        st.error("❌ Earth Engine authentication failed")
        return pd.DataFrame()
    
    # Get QA configuration
    if qa_level not in QA_CONFIGURATIONS:
        st.error(f"Unknown QA level: {qa_level}")
        return pd.DataFrame()
    
    qa_config = QA_CONFIGURATIONS[qa_level]
    
    # Progress tracking
    progress_container = st.container()
    with progress_container:
        st.info(f"🔄 Extracting {product} data from {start_date} to {end_date}")
        st.info(f"⚙️ Using: {qa_config['name']} - {qa_config['description']}")
    
    try:
        # Load glacier boundary (hardcoded for Athabasca for now)
        athabasca_coords = [
            [[-117.2368, 52.1944], [-117.2089, 52.1944], [-117.2089, 52.2167], 
             [-117.2368, 52.2167], [-117.2368, 52.1944]]
        ]
        roi = ee.Geometry.Polygon(athabasca_coords)
        
        if product == 'MCD43A3':
            # MCD43A3 extraction
            collection = ee.ImageCollection('MODIS/061/MCD43A3') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Apply QA masking
            masked_collection = collection.map(lambda img: mask_mcd43a3_with_qa(img, qa_config))
            
        else:
            # MOD10A1/MYD10A1 extraction
            mod_collection = ee.ImageCollection('MODIS/061/MOD10A1') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            myd_collection = ee.ImageCollection('MODIS/061/MYD10A1') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Apply QA masking to both collections
            mod_masked = mod_collection.map(lambda img: mask_mod10a1_with_advanced_qa(img, qa_config))
            myd_masked = myd_collection.map(lambda img: mask_mod10a1_with_advanced_qa(img, qa_config))
            
            # Merge collections
            masked_collection = mod_masked.merge(myd_masked).sort('system:time_start')
        
        # Limit collection size for performance
        masked_collection = masked_collection.limit(max_observations)
        
        # Extract statistics for each image
        def extract_stats(image):
            """Extract albedo statistics for glacier"""
            albedo = image.select('albedo_daily')
            
            # Calculate statistics
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
                geometry=roi,
                scale=500,
                maxPixels=1e6
            )
            
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'timestamp': image.date().millis(),
                'albedo_mean': stats.get('albedo_daily_mean'),
                'albedo_stdDev': stats.get('albedo_daily_stdDev'),
                'albedo_min': stats.get('albedo_daily_min'),
                'albedo_max': stats.get('albedo_daily_max'),
                'pixel_count': stats.get('albedo_daily_count'),
                'qa_level': qa_level,
                'qa_config': QA_CONFIGURATIONS[qa_level]['name'],
                'product': product
            })
        
        # Process collection
        with progress_container:
            st.info("📊 Processing images and extracting statistics...")
        
        time_series = masked_collection.map(extract_stats)
        
        # Convert to DataFrame
        data_list = time_series.getInfo()['features']
        records = []
        
        for feature in data_list:
            props = feature['properties']
            # Only include records with valid albedo data
            if props.get('albedo_mean') is not None and props.get('pixel_count', 0) > 0:
                records.append(props)
        
        if not records:
            with progress_container:
                st.warning(f"❌ No valid data found for {qa_level} filtering")
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Process dates and add temporal columns
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Add temporal columns
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day_of_year'] = df['date'].dt.dayofyear
        df['season'] = df['month'].map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        })
        
        # Add QA metadata
        df['qa_configuration'] = qa_config['name']
        df['expected_retention'] = qa_config['expected_retention']
        
        with progress_container:
            st.success(f"✅ Extracted {len(df)} observations with {qa_level} filtering")
            retention_info = f"📊 Expected retention: {qa_config['expected_retention']*100:.0f}%"
            st.info(retention_info)
        
        return df
        
    except Exception as e:
        with progress_container:
            st.error(f"❌ Extraction failed: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes
def compare_qa_levels_realtime(start_date, end_date, product='MOD10A1'):
    """
    Compare different QA levels using real-time Earth Engine extraction
    
    Args:
        start_date: Start date for comparison
        end_date: End date for comparison
        product: MODIS product to use
    
    Returns:
        dict: Comparison results for all QA levels
    """
    if not initialize_earth_engine():
        st.error("❌ Earth Engine authentication required for real-time comparison")
        return {}
    
    qa_levels = ['standard_qa', 'advanced_balanced', 'advanced_strict']
    results = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, qa_level in enumerate(qa_levels):
        status_text.text(f"Processing {QA_CONFIGURATIONS[qa_level]['name']}...")
        
        # Extract data for this QA level
        df = extract_modis_time_series_realtime(
            start_date, end_date, qa_level, product, max_observations=100
        )
        
        if not df.empty:
            results[qa_level] = {
                'data': df,
                'count': len(df),
                'mean_albedo': df['albedo_mean'].mean(),
                'std_albedo': df['albedo_mean'].std(),
                'min_albedo': df['albedo_mean'].min(),
                'max_albedo': df['albedo_mean'].max(),
                'mean_pixels': df['pixel_count'].mean(),
                'config': QA_CONFIGURATIONS[qa_level]
            }
        else:
            results[qa_level] = {
                'data': df,
                'count': 0,
                'mean_albedo': None,
                'std_albedo': None,
                'min_albedo': None,
                'max_albedo': None,
                'mean_pixels': 0,
                'config': QA_CONFIGURATIONS[qa_level]
            }
        
        progress_bar.progress((i + 1) / len(qa_levels))
    
    status_text.text("✅ Real-time QA comparison complete!")
    progress_bar.empty()
    
    return results


def mask_mod10a1_with_custom_qa(image, qa_config):
    """
    Apply custom QA filtering to MOD10A1/MYD10A1 image
    Allows individual control of each algorithm flag
    
    Args:
        image: MOD10A1/MYD10A1 Earth Engine image
        qa_config: Custom QA configuration dictionary
    
    Returns:
        ee.Image: Masked albedo image
    """
    albedo = image.select('Snow_Albedo_Daily_Tile')
    basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    # Valid albedo range (5-99 before scaling)
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    
    # Basic QA filtering - this is CRITICAL and should always work
    basic_threshold = qa_config.get('mod10a1_basic_qa_threshold', 1)
    basic_quality = basic_qa.lte(basic_threshold)
    
    # Initialize mask with basic criteria
    final_mask = valid_albedo.And(basic_quality)
    
    # Apply algorithm flags ONLY if explicitly requested AND enabled
    use_algo_flags = qa_config.get('mod10a1_use_algorithm_flags', False)
    
    if use_algo_flags:
        try:
            algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
            algorithm_mask = ee.Image(1)  # Start with all pixels allowed
            
            # Apply each flag individually based on configuration
            if qa_config.get('mod10a1_filter_water', False):
                no_water = algo_qa.bitwiseAnd(1).eq(0)   # Bit 0
                algorithm_mask = algorithm_mask.And(no_water)
            
            if qa_config.get('mod10a1_filter_low_visible', False):
                no_low_visible = algo_qa.bitwiseAnd(2).eq(0)   # Bit 1
                algorithm_mask = algorithm_mask.And(no_low_visible)
            
            if qa_config.get('mod10a1_filter_low_ndsi', False):
                no_low_ndsi = algo_qa.bitwiseAnd(4).eq(0)   # Bit 2
                algorithm_mask = algorithm_mask.And(no_low_ndsi)
            
            if qa_config.get('mod10a1_filter_temp_height', False):
                no_temp_issues = algo_qa.bitwiseAnd(8).eq(0)   # Bit 3
                algorithm_mask = algorithm_mask.And(no_temp_issues)
            
            if qa_config.get('mod10a1_filter_spatial', False):
                no_spatial_issues = algo_qa.bitwiseAnd(16).eq(0)   # Bit 4
                algorithm_mask = algorithm_mask.And(no_spatial_issues)
            
            if qa_config.get('mod10a1_filter_clouds', False):
                no_clouds = algo_qa.bitwiseAnd(32).eq(0)   # Bit 5
                algorithm_mask = algorithm_mask.And(no_clouds)
            
            if qa_config.get('mod10a1_filter_radiometric', False):
                no_radiometric = algo_qa.bitwiseAnd(64).eq(0)   # Bit 6
                algorithm_mask = algorithm_mask.And(no_radiometric)
            
            # Combine with basic mask only if algorithm flags were actually applied
            final_mask = final_mask.And(algorithm_mask)
            
        except Exception as e:
            # If algorithm flags not available, continue with basic QA only
            print(f"Algorithm flags not available: {e}")
            pass
    
    # Apply mask and scale
    scaled = albedo.multiply(0.01).updateMask(final_mask)
    
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])


@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def extract_modis_time_series_custom_qa(start_date, end_date, custom_qa_config, 
                                       product='MOD10A1', max_observations=200):
    """
    Extract MODIS time series data with custom QA configuration
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        custom_qa_config: Custom QA configuration dictionary
        product: 'MOD10A1' for snow albedo or 'MCD43A3' for broadband albedo
        max_observations: Maximum number of observations to extract
    
    Returns:
        pd.DataFrame: Time series data with custom QA filtering applied
    """
    # Initialize Earth Engine
    if not initialize_earth_engine():
        st.error("❌ Earth Engine authentication failed")
        return pd.DataFrame()
    
    # Progress tracking
    progress_container = st.container()
    with progress_container:
        st.info(f"🔄 Extracting {product} data with custom QA from {start_date} to {end_date}")
        st.info(f"⚙️ Using: {custom_qa_config['description']}")
    
    try:
        # Load glacier boundary (hardcoded for Athabasca for now)
        athabasca_coords = [
            [[-117.2368, 52.1944], [-117.2089, 52.1944], [-117.2089, 52.2167], 
             [-117.2368, 52.2167], [-117.2368, 52.1944]]
        ]
        roi = ee.Geometry.Polygon(athabasca_coords)
        
        if product == 'MCD43A3':
            # MCD43A3 extraction with custom QA
            collection = ee.ImageCollection('MODIS/061/MCD43A3') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Apply custom QA masking for MCD43A3
            masked_collection = collection.map(lambda img: mask_mcd43a3_with_qa(img, custom_qa_config))
            
        else:
            # MOD10A1/MYD10A1 extraction with custom QA
            mod_collection = ee.ImageCollection('MODIS/061/MOD10A1') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            myd_collection = ee.ImageCollection('MODIS/061/MYD10A1') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date)
            
            # Apply custom QA masking to both collections
            mod_masked = mod_collection.map(lambda img: mask_mod10a1_with_custom_qa(img, custom_qa_config))
            myd_masked = myd_collection.map(lambda img: mask_mod10a1_with_custom_qa(img, custom_qa_config))
            
            # Merge collections
            masked_collection = mod_masked.merge(myd_masked).sort('system:time_start')
        
        # Limit collection size for performance
        masked_collection = masked_collection.limit(max_observations)
        
        # Extract statistics for each image
        def extract_stats(image):
            """Extract albedo statistics for glacier"""
            albedo = image.select('albedo_daily')
            
            # Calculate statistics
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
                geometry=roi,
                scale=500,
                maxPixels=1e6
            )
            
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'timestamp': image.date().millis(),
                'albedo_mean': stats.get('albedo_daily_mean'),
                'albedo_stdDev': stats.get('albedo_daily_stdDev'),
                'albedo_min': stats.get('albedo_daily_min'),
                'albedo_max': stats.get('albedo_daily_max'),
                'pixel_count': stats.get('albedo_daily_count'),
                'qa_config': custom_qa_config['name'],
                'qa_threshold': custom_qa_config['mod10a1_basic_qa_threshold'],
                'product': product
            })
        
        # Process collection
        with progress_container:
            st.info("📊 Processing images with custom QA configuration...")
        
        time_series = masked_collection.map(extract_stats)
        
        # Convert to DataFrame
        data_list = time_series.getInfo()['features']
        records = []
        
        # Debug information
        total_images = len(data_list)
        valid_records = 0
        
        for feature in data_list:
            props = feature['properties']
            # Only include records with valid albedo data
            if props.get('albedo_mean') is not None and props.get('pixel_count', 0) > 0:
                records.append(props)
                valid_records += 1
        
        # Show processing statistics
        with progress_container:
            st.info(f"📊 Processed {total_images} images, {valid_records} with valid data")
            if custom_qa_config.get('mod10a1_basic_qa_threshold') is not None:
                st.info(f"🔧 Using Basic QA threshold: {custom_qa_config['mod10a1_basic_qa_threshold']}")
            if custom_qa_config.get('mod10a1_use_algorithm_flags'):
                active_flags = [k.replace('mod10a1_filter_', '') for k, v in custom_qa_config.items() 
                              if k.startswith('mod10a1_filter_') and v]
                st.info(f"🏁 Active algorithm flags: {active_flags if active_flags else 'None'}")
        
        if not records:
            with progress_container:
                st.warning(f"❌ No valid data found with custom QA configuration")
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Process dates and add temporal columns
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Add temporal columns
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day_of_year'] = df['date'].dt.dayofyear
        df['season'] = df['month'].map({
            12: 'Winter', 1: 'Winter', 2: 'Winter',
            3: 'Spring', 4: 'Spring', 5: 'Spring',
            6: 'Summer', 7: 'Summer', 8: 'Summer',
            9: 'Fall', 10: 'Fall', 11: 'Fall'
        })
        
        with progress_container:
            st.success(f"✅ Extracted {len(df)} observations with custom QA")
        
        return df
        
    except Exception as e:
        with progress_container:
            st.error(f"❌ Custom QA extraction failed: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def diagnose_custom_qa_impact(start_date, end_date, custom_qa_config):
    """
    Diagnose the impact of custom QA configuration on data retention
    Compare with and without the custom settings
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        custom_qa_config: Custom QA configuration
    
    Returns:
        dict: Detailed QA impact analysis
    """
    if not initialize_earth_engine():
        return {}
    
    try:
        # Load glacier boundary
        athabasca_coords = [
            [[-117.2368, 52.1944], [-117.2089, 52.1944], [-117.2089, 52.2167], 
             [-117.2368, 52.2167], [-117.2368, 52.1944]]
        ]
        roi = ee.Geometry.Polygon(athabasca_coords)
        
        # Load a sample of MOD10A1 images
        collection = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .limit(5)  # Limit for diagnostic
        
        def analyze_qa_impact(image):
            """Analyze QA impact for a single image"""
            albedo = image.select('Snow_Albedo_Daily_Tile')
            basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            # Valid albedo pixels (baseline)
            valid_albedo = albedo.gte(5).And(albedo.lte(99))
            baseline_count = valid_albedo.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('Snow_Albedo_Daily_Tile')
            
            # Apply basic QA threshold
            basic_threshold = custom_qa_config.get('mod10a1_basic_qa_threshold', 1)
            basic_quality = basic_qa.lte(basic_threshold)
            basic_filtered = valid_albedo.And(basic_quality)
            basic_count = basic_filtered.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('Snow_Albedo_Daily_Tile')
            
            # Analyze Basic QA distribution
            qa_0_count = basic_qa.eq(0).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            qa_1_count = basic_qa.eq(1).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            qa_2_count = basic_qa.eq(2).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'baseline_pixels': baseline_count,
                'basic_filtered_pixels': basic_count,
                'basic_qa_threshold': basic_threshold,
                'qa_0_pixels': qa_0_count,
                'qa_1_pixels': qa_1_count,
                'qa_2_pixels': qa_2_count
            })
        
        # Analyze QA impact
        qa_analysis = collection.map(analyze_qa_impact)
        
        # Get results
        results = qa_analysis.getInfo()['features']
        
        # Process results
        analysis = {
            'total_images': len(results),
            'dates_analyzed': [],
            'baseline_total': 0,
            'basic_filtered_total': 0,
            'qa_0_total': 0,
            'qa_1_total': 0,
            'qa_2_total': 0,
            'basic_qa_threshold': custom_qa_config.get('mod10a1_basic_qa_threshold', 1),
            'algorithm_flags_enabled': custom_qa_config.get('mod10a1_use_algorithm_flags', False)
        }
        
        for feature in results:
            props = feature['properties']
            analysis['dates_analyzed'].append(props.get('date'))
            analysis['baseline_total'] += props.get('baseline_pixels', 0) or 0
            analysis['basic_filtered_total'] += props.get('basic_filtered_pixels', 0) or 0
            analysis['qa_0_total'] += props.get('qa_0_pixels', 0) or 0
            analysis['qa_1_total'] += props.get('qa_1_pixels', 0) or 0
            analysis['qa_2_total'] += props.get('qa_2_pixels', 0) or 0
        
        # Calculate retention rates
        if analysis['baseline_total'] > 0:
            analysis['basic_retention_rate'] = (analysis['basic_filtered_total'] / analysis['baseline_total']) * 100
            analysis['qa_0_percentage'] = (analysis['qa_0_total'] / analysis['baseline_total']) * 100
            analysis['qa_1_percentage'] = (analysis['qa_1_total'] / analysis['baseline_total']) * 100
            analysis['qa_2_percentage'] = (analysis['qa_2_total'] / analysis['baseline_total']) * 100
        
        return analysis
        
    except Exception as e:
        print(f"Custom QA diagnosis error: {e}")
        return {}


@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes
def diagnose_qa_distribution(start_date, end_date):
    """
    Diagnose the actual QA distribution in MODIS data
    Check what Basic QA values are actually present
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        dict: QA distribution statistics
    """
    if not initialize_earth_engine():
        return {}
    
    try:
        # Load glacier boundary
        athabasca_coords = [
            [[-117.2368, 52.1944], [-117.2089, 52.1944], [-117.2089, 52.2167], 
             [-117.2368, 52.2167], [-117.2368, 52.1944]]
        ]
        roi = ee.Geometry.Polygon(athabasca_coords)
        
        # Load MOD10A1 collection
        collection = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .limit(20)  # Limit for diagnostic
        
        def analyze_qa(image):
            """Analyze QA distribution for a single image"""
            albedo = image.select('Snow_Albedo_Daily_Tile')
            basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            # Valid albedo pixels
            valid_albedo = albedo.gte(5).And(albedo.lte(99))
            
            # Count pixels by QA value
            qa_0_count = basic_qa.eq(0).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            qa_1_count = basic_qa.eq(1).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            qa_2_count = basic_qa.eq(2).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            qa_higher_count = basic_qa.gte(3).And(valid_albedo).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=500,
                maxPixels=1e6
            ).get('NDSI_Snow_Cover_Basic_QA')
            
            return ee.Feature(None, {
                'date': image.date().format('YYYY-MM-dd'),
                'qa_0_pixels': qa_0_count,
                'qa_1_pixels': qa_1_count,
                'qa_2_pixels': qa_2_count,
                'qa_higher_pixels': qa_higher_count
            })
        
        # Analyze QA distribution
        qa_analysis = collection.map(analyze_qa)
        
        # Get results
        results = qa_analysis.getInfo()['features']
        
        # Process results
        qa_stats = {
            'total_images': len(results),
            'qa_0_total': 0,
            'qa_1_total': 0,
            'qa_2_total': 0,
            'qa_higher_total': 0,
            'dates_analyzed': []
        }
        
        for feature in results:
            props = feature['properties']
            qa_stats['qa_0_total'] += props.get('qa_0_pixels', 0) or 0
            qa_stats['qa_1_total'] += props.get('qa_1_pixels', 0) or 0
            qa_stats['qa_2_total'] += props.get('qa_2_pixels', 0) or 0
            qa_stats['qa_higher_total'] += props.get('qa_higher_pixels', 0) or 0
            qa_stats['dates_analyzed'].append(props.get('date'))
        
        # Calculate percentages
        total_pixels = (qa_stats['qa_0_total'] + qa_stats['qa_1_total'] + 
                       qa_stats['qa_2_total'] + qa_stats['qa_higher_total'])
        
        if total_pixels > 0:
            qa_stats['qa_0_percent'] = (qa_stats['qa_0_total'] / total_pixels) * 100
            qa_stats['qa_1_percent'] = (qa_stats['qa_1_total'] / total_pixels) * 100
            qa_stats['qa_2_percent'] = (qa_stats['qa_2_total'] / total_pixels) * 100
            qa_stats['qa_higher_percent'] = (qa_stats['qa_higher_total'] / total_pixels) * 100
        
        return qa_stats
        
    except Exception as e:
        print(f"QA diagnosis error: {e}")
        return {}


def get_qa_level_info():
    """
    Get information about available QA levels
    
    Returns:
        dict: QA level configurations
    """
    return QA_CONFIGURATIONS