"""
MODIS Data Extraction Module
Handles pixel extraction and Terra-Aqua fusion for MODIS products
"""

import streamlit as st
from .pixel_processing import _process_pixels_to_geojson, safe_int_conversion


def get_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1, use_advanced_qa=False, algorithm_flags={}, silent=False, selected_band=None, diffuse_fraction=None):
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
            return _extract_mcd43a3_pixels(date, roi, qa_threshold, silent, selected_band, diffuse_fraction)
        else:
            return _extract_mod10a1_pixels(date, roi, qa_threshold, use_advanced_qa, algorithm_flags, silent)
            
    except Exception as e:
        if not silent:
            st.error(f"Error in MODIS extraction: {e}")
        return None


def _extract_mcd43a3_pixels(date, roi, qa_threshold, silent, selected_band=None, diffuse_fraction=None):
    """Extract MCD43A3 broadband albedo pixels"""
    import ee
    
    # MCD43A3 (Broadband Albedo) handling
    mcd43a3 = ee.ImageCollection('MODIS/061/MCD43A3')
    
    # Filter by date (±1 day for better coverage)
    start_date = ee.Date(date).advance(-1, 'day')
    end_date = ee.Date(date).advance(1, 'day')
    
    # Get images for the date with boundary filter
    images = mcd43a3.filterDate(start_date, end_date).filterBounds(roi)
    
    # Check if we have data - safe handling of getInfo() result
    image_count_raw = images.size().getInfo()
    image_count = int(image_count_raw) if image_count_raw is not None else 0
    
    if image_count == 0:
        return None
        
    # Set diffuse fraction with default fallback
    if diffuse_fraction is None:
        diffuse_fraction = 0.2
        
    # Apply quality filtering for MCD43A3 with proper BSA/WSA handling
    def mask_mcd43a3_albedo(image):
        """
        Apply configurable quality filtering for MCD43A3 with Blue-Sky albedo calculation
        Following best practices for glacier albedo monitoring
        """
        # Get both Black-Sky (BSA) and White-Sky (WSA) albedo bands
        bsa_shortwave = image.select('Albedo_BSA_shortwave')
        wsa_shortwave = image.select('Albedo_WSA_shortwave')
        
        # Also get spectral bands for analysis
        bsa_vis = image.select('Albedo_BSA_vis')
        bsa_nir = image.select('Albedo_BSA_nir')
        
        # Use shortwave quality band as primary QA
        qa_shortwave = image.select('BRDF_Albedo_Band_Mandatory_Quality_shortwave')
        
        # Apply quality threshold: 0=full BRDF only, 1=include magnitude inversions
        good_quality = qa_shortwave.lte(qa_threshold)
        
        # Apply quality mask and scale (MCD43A3 uses 0.001 scale factor)
        bsa_masked = bsa_shortwave.updateMask(good_quality).multiply(0.001)
        wsa_masked = wsa_shortwave.updateMask(good_quality).multiply(0.001)
        
        # Calculate Blue-Sky Albedo (actual albedo under real conditions)
        # For glaciers at high elevation, we typically have:
        # - Clear skies predominant (high direct radiation)
        # - Diffuse fraction ~0.15-0.25 depending on conditions
        # Calculate Blue-Sky Albedo using the specified diffuse fraction
        blue_sky_shortwave = bsa_masked.multiply(1 - diffuse_fraction).add(
            wsa_masked.multiply(diffuse_fraction)
        )
        
        # Apply Williamson & Menounos (2021) range filter
        # Exclude shadows (<0.05) and unrealistic values (>0.99)
        range_mask = blue_sky_shortwave.gte(0.05).And(blue_sky_shortwave.lte(0.99))
        
        # Process spectral bands with same quality mask
        vis_masked = bsa_vis.updateMask(good_quality).multiply(0.001)
        nir_masked = bsa_nir.updateMask(good_quality).multiply(0.001)
        
        # Determine which band to use as primary based on selection
        if selected_band == 'vis':
            primary_albedo = vis_masked.updateMask(range_mask)
        elif selected_band == 'nir':
            primary_albedo = nir_masked.updateMask(range_mask)
        else:  # Default to shortwave (blue-sky)
            primary_albedo = blue_sky_shortwave.updateMask(range_mask)
        
        # Return multi-band image with selected band as primary
        return primary_albedo.rename('albedo_daily').addBands([
            blue_sky_shortwave.updateMask(range_mask).rename('blue_sky_shortwave'),
            bsa_masked.rename('bsa_shortwave'),
            wsa_masked.rename('wsa_shortwave'),
            vis_masked.updateMask(range_mask).rename('albedo_vis'),
            nir_masked.updateMask(range_mask).rename('albedo_nir')
        ]).copyProperties(image, ['system:time_start'])
    
    # Process and combine multiple dates
    processed_images = images.map(mask_mcd43a3_albedo)
    
    # Use mean composite for multiple dates
    combined_image = processed_images.mean()
    
    # Product identification
    if selected_band == 'vis':
        product_name = 'MCD43A3 Visible'
        band_desc = 'Visible (0.3-0.7 μm) BSA'
    elif selected_band == 'nir':
        product_name = 'MCD43A3 NIR'
        band_desc = 'NIR (0.7-5.0 μm) BSA'
    else:
        product_name = 'MCD43A3'
        band_desc = f'Blue-Sky albedo ({diffuse_fraction*100:.0f}% diffuse)'
    
    if qa_threshold == 0:
        quality_description = f'QA = 0 (full BRDF only), {band_desc}'
    else:
        quality_description = f'QA ≤ {qa_threshold} (BRDF+magnitude), {band_desc}'
    
    return _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent, diffuse_fraction)


def _extract_mod10a1_pixels(date, roi, qa_threshold, use_advanced_qa, algorithm_flags, silent):
    """Extract MOD10A1/MYD10A1 snow albedo pixels with Terra-Aqua fusion"""
    try:
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
        
        # Check if we have data - ROBUST handling of getInfo() results
        terra_count_raw = terra_imgs.size().getInfo()
        aqua_count_raw = aqua_imgs.size().getInfo()
        terra_count = safe_int_conversion(terra_count_raw)
        aqua_count = safe_int_conversion(aqua_count_raw)
        
        # Display processing status (unless silent mode)
        if not silent:
            with st.sidebar:
                st.markdown("**🛰️ Processing Status:**")
                if terra_count > 0 or aqua_count > 0:
                    st.write(f"📡 Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
                else:
                    st.write(f"📡 Processing MOD10A1 data for {date}")
        
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
        
        return _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent, None)
        
    except Exception as e:
        if not silent:
            st.error(f"Error in MOD10A1 extraction for {date}: {str(e)}")
        return None


def _apply_terra_aqua_fusion(terra_imgs, aqua_imgs, qa_threshold, use_advanced_qa, algorithm_flags):
    """Apply enhanced Terra-Aqua fusion with satellite source tracking"""
    try:
        import ee
        
        def mask_modis_snow_albedo(image):
            """Apply configurable quality filtering for MOD10A1/MYD10A1 with defensive programming"""
            try:
                albedo = image.select('Snow_Albedo_Daily_Tile')
                qa = image.select('NDSI_Snow_Cover_Basic_QA')
                
                # Apply configurable quality threshold - use plain numbers
                valid_albedo = albedo.gte(5).And(albedo.lte(99))  # 5-99 range before scaling
                good_quality = qa.lte(qa_threshold)  # Use configurable threshold
                
                # Apply advanced algorithm flags if enabled
                if use_advanced_qa and algorithm_flags:
                    try:
                        algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
                        
                        # Apply algorithm flags based on user selection
                        flag_masks = []
                        
                        if algorithm_flags.get('no_inland_water', False):
                            mask = algo_qa.bitwiseAnd(1).eq(0)
                            flag_masks.append(mask)        # Bit 0
                        if algorithm_flags.get('no_low_visible', False):
                            mask = algo_qa.bitwiseAnd(2).eq(0)
                            flag_masks.append(mask)        # Bit 1
                        if algorithm_flags.get('no_low_ndsi', False):
                            mask = algo_qa.bitwiseAnd(4).eq(0)
                            flag_masks.append(mask)        # Bit 2
                        if algorithm_flags.get('no_temp_issues', False):
                            mask = algo_qa.bitwiseAnd(8).eq(0)
                            flag_masks.append(mask)        # Bit 3
                        if algorithm_flags.get('no_high_swir', False):
                            mask = algo_qa.bitwiseAnd(16).eq(0)
                            flag_masks.append(mask)       # Bit 4
                        if algorithm_flags.get('no_clouds', False):
                            mask = algo_qa.bitwiseAnd(32).eq(0)
                            flag_masks.append(mask)       # Bit 5
                        if algorithm_flags.get('no_cloud_clear', False):
                            mask = algo_qa.bitwiseAnd(64).eq(0)
                            flag_masks.append(mask)       # Bit 6
                        if algorithm_flags.get('no_shadows', False):
                            mask = algo_qa.bitwiseAnd(128).eq(0)
                            flag_masks.append(mask)      # Bit 7
                        
                        # Combine all algorithm flags with basic quality
                        if flag_masks:
                            algorithm_mask = flag_masks[0]
                            for mask in flag_masks[1:]:
                                algorithm_mask = algorithm_mask.And(mask)
                            final_quality = good_quality.And(algorithm_mask)
                        else:
                            final_quality = good_quality
                    except:
                        # Fallback if algorithm QA fails
                        final_quality = good_quality
                else:
                    final_quality = good_quality
                
                # Apply masks and scale - use plain number for multiply
                masked = albedo.updateMask(valid_albedo.And(final_quality)).multiply(0.01)
                
                # Simply return the masked albedo without satellite band to avoid type conflicts
                # We'll track satellite source differently
                return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
                
            except Exception:
                # Return a masked image if processing fails
                return ee.Image.constant(0).rename('albedo_daily').updateMask(ee.Image.constant(0))
        
        # Simple approach - process and combine without satellite tracking to avoid type errors
        # Use the same safe conversion function as above
        terra_count_raw = terra_imgs.size().getInfo()
        aqua_count_raw = aqua_imgs.size().getInfo()
        terra_count = safe_int_conversion(terra_count_raw)
        aqua_count = safe_int_conversion(aqua_count_raw)
        
        if terra_count > 0 and aqua_count > 0:
            # Both available - process both and combine with Terra priority
            terra_processed = terra_imgs.map(mask_modis_snow_albedo)
            aqua_processed = aqua_imgs.map(mask_modis_snow_albedo)
            
            # Create satellite source bands
            terra_mosaic = terra_processed.mosaic()
            aqua_mosaic = aqua_processed.mosaic()
            
            # Use Terra with priority, fill gaps with Aqua
            combined_albedo = terra_mosaic.unmask(aqua_mosaic)
            
            # Create a satellite source mask (1=Terra, 2=Aqua)
            terra_mask = terra_mosaic.mask()
            satellite_source = terra_mask.multiply(1).unmask(2).rename('satellite_source')
            
            return combined_albedo.addBands(satellite_source)
            
        elif terra_count > 0:
            # Only Terra available
            terra_processed = terra_imgs.map(mask_modis_snow_albedo)
            terra_mosaic = terra_processed.mosaic()
            # Add satellite source band (1=Terra)
            satellite_source = ee.Image.constant(1).rename('satellite_source').clip(roi)
            return terra_mosaic.addBands(satellite_source)
            
        elif aqua_count > 0:
            # Only Aqua available
            aqua_processed = aqua_imgs.map(mask_modis_snow_albedo)
            aqua_mosaic = aqua_processed.mosaic()
            # Add satellite source band (2=Aqua)
            satellite_source = ee.Image.constant(2).rename('satellite_source').clip(roi)
            return aqua_mosaic.addBands(satellite_source)
            
        else:
            return None
            
    except Exception as e:
        # Return None on any error during fusion
        return None