"""
MODIS Data Extraction Module
Handles pixel extraction and Terra-Aqua fusion for MODIS products
"""

import streamlit as st
from .pixel_processing import _process_pixels_to_geojson


def get_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1, use_advanced_qa=False, algorithm_flags={}, silent=False):
    """
    Get MODIS pixel boundaries with albedo values for a specific date
    Uses configurable quality filtering
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        product: 'MOD10A1' for daily snow albedo or 'MCD43A3' for broadband albedo
        qa_threshold: Quality threshold (0=strict, 1=standard, 2=relaxed for MOD10A1)
        use_advanced_qa: Enable advanced algorithm flags (MOD10A1 only)
        algorithm_flags: Dictionary of algorithm flags to apply
        silent: If True, suppress sidebar messages
        
    Returns:
        dict: GeoJSON with MODIS pixel features and albedo values
    """
    try:
        import ee
        
        if product == 'MCD43A3':
            return _extract_mcd43a3_pixels(date, roi, qa_threshold, silent)
        else:
            return _extract_mod10a1_pixels(date, roi, qa_threshold, use_advanced_qa, algorithm_flags, silent)
            
    except Exception as e:
        if not silent:
            st.error(f"Error in MODIS extraction: {e}")
        return None


def _extract_mcd43a3_pixels(date, roi, qa_threshold, silent):
    """Extract MCD43A3 broadband albedo pixels"""
    import ee
    
    # MCD43A3 (Broadband Albedo) handling
    mcd43a3 = ee.ImageCollection('MODIS/061/MCD43A3')
    
    # Filter by date (±1 day for better coverage)
    start_date = ee.Date(date).advance(-1, 'day')
    end_date = ee.Date(date).advance(1, 'day')
    
    # Get images for the date with boundary filter
    images = mcd43a3.filterDate(start_date, end_date).filterBounds(roi)
    
    # Check if we have data
    image_count = images.size().getInfo()
    
    if image_count == 0:
        return None
        
    # Apply quality filtering for MCD43A3
    def mask_mcd43a3_albedo(image):
        """Apply configurable quality filtering for MCD43A3"""
        albedo = image.select('Albedo_BSA_shortwave')
        qa_band1 = image.select('BRDF_Albedo_Band_Mandatory_Quality_Band1')
        
        # Apply quality threshold: 0=full BRDF only, 1=include magnitude inversions
        good_quality = qa_band1.lte(qa_threshold)
        
        # Apply quality mask and scale (MCD43A3 uses 0.001 scale factor)
        masked = albedo.updateMask(good_quality).multiply(0.001)
        
        # Additional range filter (0.0 to 1.0 for albedo)
        range_mask = masked.gte(0.0).And(masked.lte(1.0))
        final_masked = masked.updateMask(range_mask)
        
        return final_masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
    
    # Process and combine multiple dates
    processed_images = images.map(mask_mcd43a3_albedo)
    
    # Use mean composite for multiple dates
    combined_image = processed_images.mean()
    
    # Product identification
    product_name = 'MCD43A3'
    if qa_threshold == 0:
        quality_description = 'QA = 0 (full BRDF inversions only)'
    else:
        quality_description = f'QA ≤ {qa_threshold} (includes magnitude inversions)'
    
    return _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent)


def _extract_mod10a1_pixels(date, roi, qa_threshold, use_advanced_qa, algorithm_flags, silent):
    """Extract MOD10A1/MYD10A1 snow albedo pixels with Terra-Aqua fusion"""
    import ee
    
    # MOD10A1/MYD10A1 (Daily Snow Albedo) handling with Terra-Aqua fusion
    mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')  # Terra
    myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')  # Aqua
    
    # Filter by exact date (no ±1 day window per user request)
    start_date = ee.Date(date)
    end_date = ee.Date(date).advance(1, 'day')
    
    # Get images for both satellites
    terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
    aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
    
    # Check if we have data
    terra_count = terra_imgs.size().getInfo()
    aqua_count = aqua_imgs.size().getInfo()
    
    # Display processing status (unless silent mode)
    if not silent:
        with st.sidebar:
            st.markdown("**🛰️ Processing Status:**")
            st.write(f"📡 Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
    
    if terra_count == 0 and aqua_count == 0:
        return None
        
    # Apply Terra-Aqua fusion with satellite tracking
    combined_image = _apply_terra_aqua_fusion(terra_imgs, aqua_imgs, qa_threshold, use_advanced_qa, algorithm_flags)
    
    if combined_image is None:
        return None
    
    # Product identification
    product_name = 'MOD10A1/MYD10A1'
    if qa_threshold == 0:
        quality_description = 'QA = 0 (best quality), range 0.05-0.99'
    elif qa_threshold == 1:
        quality_description = 'QA ≤ 1 (best+good), range 0.05-0.99'
    else:
        quality_description = f'QA ≤ {qa_threshold} (includes fair), range 0.05-0.99'
    
    return _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent)


def _apply_terra_aqua_fusion(terra_imgs, aqua_imgs, qa_threshold, use_advanced_qa, algorithm_flags):
    """Apply enhanced Terra-Aqua fusion with satellite source tracking"""
    import ee
    
    def mask_modis_snow_albedo(image):
        """Apply configurable quality filtering for MOD10A1/MYD10A1"""
        albedo = image.select('Snow_Albedo_Daily_Tile')
        qa = image.select('NDSI_Snow_Cover_Basic_QA')
        
        # Apply configurable quality threshold
        valid_albedo = albedo.gte(5).And(albedo.lte(99))  # 5-99 range before scaling
        good_quality = qa.lte(qa_threshold)  # Use configurable threshold
        
        # Apply advanced algorithm flags if enabled
        if use_advanced_qa and algorithm_flags:
            algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
            
            # Apply algorithm flags based on user selection
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
            if algorithm_flags.get('no_cloud_clear', False):
                flag_masks.append(algo_qa.bitwiseAnd(64).eq(0))       # Bit 6
            if algorithm_flags.get('no_shadows', False):
                flag_masks.append(algo_qa.bitwiseAnd(128).eq(0))      # Bit 7
            
            # Combine all algorithm flags with basic quality
            if flag_masks:
                algorithm_mask = flag_masks[0]
                for mask in flag_masks[1:]:
                    algorithm_mask = algorithm_mask.And(mask)
                final_quality = good_quality.And(algorithm_mask)
            else:
                final_quality = good_quality
        else:
            final_quality = good_quality
        
        # Apply masks and scale
        masked = albedo.updateMask(valid_albedo.And(final_quality)).multiply(0.01)
        
        return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
    
    def add_satellite_band(image, satellite_name):
        """Add a band indicating which satellite provided each pixel"""
        # Create a constant band with satellite identifier that matches the image geometry
        satellite_value = 1 if satellite_name == 'Terra' else 2
        # Use the albedo band as a template to ensure compatible geometry
        template_band = image.select('albedo_daily')
        # IMPORTANT: Convert Python int to EE Number to avoid type errors
        satellite_band = template_band.multiply(0).add(ee.Number(satellite_value)).rename('satellite_source').byte()
        return image.addBands(satellite_band)
    
    # Process collections with satellite identification
    processed_images = []
    
    terra_count = terra_imgs.size().getInfo()
    aqua_count = aqua_imgs.size().getInfo()
    
    if terra_count > 0:
        terra_processed = terra_imgs.map(mask_modis_snow_albedo)
        terra_with_source = terra_processed.map(lambda img: add_satellite_band(img, 'Terra'))
        processed_images.append(terra_with_source)
        
    if aqua_count > 0:
        aqua_processed = aqua_imgs.map(mask_modis_snow_albedo)
        aqua_with_source = aqua_processed.map(lambda img: add_satellite_band(img, 'Aqua'))
        processed_images.append(aqua_with_source)
    
    # Create fusion with Terra priority while preserving source info
    if len(processed_images) == 1:
        combined_collection = processed_images[0]
    elif len(processed_images) == 2:
        # Terra first (higher priority in mosaic)
        combined_collection = processed_images[0].merge(processed_images[1])
    else:
        return None
        
    # Create mosaic - first image in collection has priority (Terra)
    # The satellite_source band will also be mosaicked with Terra priority
    return combined_collection.mosaic()