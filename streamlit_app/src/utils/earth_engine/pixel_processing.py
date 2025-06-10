"""
Pixel Processing Module
Handles conversion of MODIS images to GeoJSON pixel features
"""

import streamlit as st


def safe_int_conversion(value):
    """
    Safely convert getInfo() result to integer, handling lists and None
    
    Earth Engine getInfo() can sometimes return lists instead of single values,
    especially in complex queries or when collections have multiple elements.
    This function handles all cases safely.
    """
    if value is None:
        return 0
    elif isinstance(value, list):
        # If it's a list, take the first element or return 0 if empty
        return int(value[0]) if value and len(value) > 0 else 0
    else:
        # Single value conversion
        return int(value)


def _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent):
    """Convert MODIS image to GeoJSON pixel features with detailed properties"""
    import ee
    
    # Clip to glacier boundary (including satellite source band if present)
    albedo_clipped = combined_image.select('albedo_daily').clip(roi)
    
    # Check if satellite source band exists
    band_names = combined_image.bandNames().getInfo()
    has_satellite_source = 'satellite_source' in band_names
    
    if has_satellite_source:
        satellite_clipped = combined_image.select('satellite_source').clip(roi)
    
    # Check if we have any valid pixels
    pixel_count_raw = albedo_clipped.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=roi,
        scale=500,
        maxPixels=1e6
    ).get('albedo_daily').getInfo()
    
    # ROBUST handling of getInfo() result - can be list or single value
    pixel_count = safe_int_conversion(pixel_count_raw)
    
    if pixel_count == 0:
        if not silent:
            with st.sidebar:
                st.warning(f"❌ No valid pixels found after quality filtering for {date}")
        return None
    
    # Convert to integer for reduceToVectors (multiply by 100 to preserve precision)
    # Note: albedo_clipped is already 0-1 scale from MODIS processing
    albedo_int = albedo_clipped.multiply(100).int()
    
    # Convert pixels to vectors with error handling for geometry operations
    try:
        # Standard approach - convert pixels to vectors
        pixel_vectors = albedo_int.reduceToVectors(
            geometry=roi,
            crs=albedo_int.projection(),
            scale=500,  # MODIS 500m resolution
            geometryType='polygon',
            eightConnected=False,
            maxPixels=1e6,
            bestEffort=True,
            labelProperty='albedo_int'
        )
        
        # IMPORTANT: Clip pixel polygons to exact glacier boundary
        def clip_pixel_to_glacier(feature):
            # Clip the pixel polygon to the glacier boundary
            clipped_geom = feature.geometry().intersection(roi, maxError=10)
            # Calculate intersection area to filter out tiny slivers
            intersect_area = clipped_geom.area(maxError=1)
            return ee.Feature(clipped_geom, feature.toDictionary()).set('intersect_area', intersect_area)
        
        clipped_pixels = pixel_vectors.map(clip_pixel_to_glacier)
        
        # Filter out pixels with very small intersections
        pixel_vectors = clipped_pixels.filter(ee.Filter.gte('intersect_area', 25000))
        
    except Exception as vector_error:
        if not silent:
            st.warning(f"Standard vector conversion failed: {vector_error}")
        
        # Fallback approach - use simpler parameters
        try:
            pixel_vectors = albedo_int.reduceToVectors(
                geometry=roi,
                scale=500,
                geometryType='polygon',
                eightConnected=False,
                maxPixels=100000,  # Reduced max pixels
                bestEffort=True,
                labelProperty='albedo_int'
            )
            
            # Even in fallback, try to clip to glacier
            try:
                def simple_clip(feature):
                    clipped_geom = feature.geometry().intersection(roi, maxError=10)
                    return ee.Feature(clipped_geom, feature.toDictionary())
                
                pixel_vectors = pixel_vectors.map(simple_clip)
                if not silent:
                    st.info("Using fallback vector conversion with basic glacier clipping")
            except:
                if not silent:
                    st.info("Using fallback vector conversion without clipping")
                    
        except Exception as fallback_error:
            if not silent:
                st.error(f"Both standard and fallback vector conversion failed: {fallback_error}")
            return None
    
    # Add detailed properties to each pixel including satellite source
    def add_pixel_properties(feature):
        # Get the integer albedo value from the feature properties
        albedo_int_value = feature.get('albedo_int')
        
        # Convert back to original albedo scale (divide by 100)
        # Use server-side safe conversion to handle any data type
        pixel_albedo = ee.Number(albedo_int_value).divide(100)
        
        # Get satellite source if available
        properties = {
            'albedo_value': pixel_albedo,
            'date': date,
            'product': product_name,
            'quality_filter': quality_description
        }
        
        if has_satellite_source:
            # Sample the satellite source at the pixel center
            pixel_center = feature.geometry().centroid()
            satellite_value = satellite_clipped.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=pixel_center,
                scale=10  # Small scale for point sampling
            ).get('satellite_source')
            
            # Convert satellite value to name
            satellite_name = ee.Algorithms.If(
                ee.Number(satellite_value).eq(1),
                'Terra',
                'Aqua'
            )
            properties['satellite'] = satellite_name
        
        return feature.set(properties)
    
    # Apply properties to all pixels with error handling
    try:
        # Apply the property function with comprehensive error catching
        pixels_with_data = pixel_vectors.map(add_pixel_properties)
        
        # Limit pixels for performance (reasonable default)
        pixels_limited = pixels_with_data.limit(200)
        
        # Export as GeoJSON - this is where the error likely occurs
        print(f"DEBUG: About to convert pixels to GeoJSON for {date}")
        geojson = pixels_limited.getInfo()
        print(f"DEBUG: Successfully converted {len(geojson.get('features', []))} pixels for {date}")
        
        # DEBUG: Check BOTH raw and converted albedo values
        if not silent and geojson and 'features' in geojson:
            features = geojson['features']
            if features:
                albedo_values = []
                raw_values = []
                for f in features[:5]:  # Check first 5 pixels
                    if 'properties' in f:
                        if 'albedo_value' in f['properties']:
                            albedo_values.append(f['properties']['albedo_value'])
                        if 'albedo_int' in f['properties']:
                            raw_values.append(f['properties']['albedo_int'])
                
                if albedo_values:
                    with st.sidebar:
                        st.write(f"🔍 Final albedo: {[f'{v:.3f}' for v in albedo_values[:3]]}")
                        st.write(f"📊 Range: {min(albedo_values):.3f} - {max(albedo_values):.3f}")
        
        # Analyze satellite source distribution and display results
        if not silent:
            _display_pixel_statistics(geojson, date, has_satellite_source)
        
        return geojson
        
    except Exception as map_error:
        # Detailed error logging
        print(f"ERROR in _process_pixels_to_geojson for {date}: {map_error}")
        print(f"ERROR TYPE: {type(map_error)}")
        print(f"ERROR STR: {str(map_error)}")
        
        # If mapping fails, try simpler approach without additional properties
        if not silent:
            st.warning(f"Advanced pixel properties failed: {map_error}")
            st.info("Falling back to basic pixel visualization...")
        
        try:
            # Simplified approach - just convert to vectors without complex properties
            simple_pixels = pixel_vectors.limit(50)  # Conservative limit for stability in fallback
            
            # Add only basic properties - no complex geometry operations
            def add_basic_properties(feature):
                # Get albedo value from the labelProperty created by reduceToVectors
                albedo_int_value = feature.get('albedo_int')
                
                # Convert back to original scale, with safety check
                pixel_albedo = ee.Algorithms.If(
                    ee.Algorithms.IsEqual(albedo_int_value, None),
                    ee.Number(0.5),  # Default value if null
                    ee.Number(albedo_int_value).divide(1000)
                )
                
                # Use proper EE types for all properties
                return feature.set({
                    'albedo_value': pixel_albedo,
                    'date': ee.String(date),
                    'product': ee.String(product_name),
                    'quality_filter': ee.String(quality_description)
                })
            
            basic_pixels = simple_pixels.map(add_basic_properties)
            geojson = basic_pixels.getInfo()
            
            if not silent:
                actual_count = len(geojson.get('features', []))
                with st.sidebar:
                    st.write(f"🗺️ Displaying {actual_count} MODIS pixels for {date} (basic mode)")
            
            return geojson
            
        except Exception as basic_error:
            if not silent:
                st.error(f"Even basic pixel visualization failed: {basic_error}")
            return None


def _display_pixel_statistics(geojson, date, has_satellite_source):
    """Display pixel statistics in sidebar with satellite breakdown"""
    actual_count = len(geojson.get('features', []))
    
    if has_satellite_source and actual_count > 0:
        # Analyze satellite source distribution
        terra_count = 0
        aqua_count = 0
        unknown_count = 0
        
        for feature in geojson.get('features', []):
            satellite = feature.get('properties', {}).get('satellite', 'Unknown')
            if satellite == 'Terra':
                terra_count += 1
            elif satellite == 'Aqua':
                aqua_count += 1
            else:
                unknown_count += 1
        
        # Display consolidated status with satellite breakdown
        with st.sidebar:
            st.write(f"🗺️ Displaying {actual_count} MODIS pixels for {date}")
            if terra_count > 0 or aqua_count > 0:
                st.write(f"   └ 🛰️ Terra: {terra_count} pixels, Aqua: {aqua_count} pixels")
                if terra_count > 0 and aqua_count > 0:
                    terra_pct = (terra_count / actual_count) * 100
                    st.write(f"   └ 📊 Terra priority: {terra_pct:.1f}% coverage")
            if unknown_count > 0:
                st.write(f"   └ ❓ Unknown source: {unknown_count} pixels")
    else:
        # Simple display for MCD43A3
        with st.sidebar:
            st.write(f"🗺️ Displaying {actual_count} MODIS pixels for {date}")


def safe_int_conversion(value):
    """
    Safely convert getInfo() result to integer, handling lists and None
    """
    if value is None:
        return 0
    elif isinstance(value, list):
        return int(value[0]) if value and len(value) > 0 else 0
    else:
        return int(value)

def count_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1, use_advanced_qa=False, algorithm_flags={}):
    print(f"DEBUG COUNT: Starting pixel count for {date} with product {product}")
    """
    Fast pixel count for a specific date (no detailed extraction)
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        product: 'MOD10A1' for daily snow albedo or 'MCD43A3' for broadband albedo
        qa_threshold: Quality threshold (0=strict, 1=standard, 2=relaxed)
        use_advanced_qa: Enable advanced algorithm flags (MOD10A1 only)
        algorithm_flags: Dictionary of algorithm flags to apply
        
    Returns:
        int: Number of valid pixels found
    """
    try:
        import ee
        
        if product == 'MCD43A3':
            # MCD43A3 handling
            mcd43a3 = ee.ImageCollection('MODIS/061/MCD43A3')
            start_date = ee.Date(date).advance(-1, 'day')
            end_date = ee.Date(date).advance(1, 'day')
            
            images = mcd43a3.filterDate(start_date, end_date).filterBounds(roi)
            
            # Safe comparison with getInfo() result - use same robust conversion
            image_size = images.size().getInfo()
            image_count = safe_int_conversion(image_size)
            
            if image_count == 0:
                return 0
            
            # Apply quality mask
            def mask_mcd43a3_albedo(image):
                albedo = image.select('Albedo_BSA_shortwave')
                qa_band1 = image.select('BRDF_Albedo_Band_Mandatory_Quality_Band1')
                good_quality = qa_band1.lte(qa_threshold)
                masked = albedo.updateMask(good_quality).multiply(0.001)
                range_mask = masked.gte(0.0).And(masked.lte(1.0))
                return masked.updateMask(range_mask)
            
            processed = images.map(mask_mcd43a3_albedo).mean()
            
        else:
            # MOD10A1/MYD10A1 handling
            mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
            myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
            
            start_date = ee.Date(date)
            end_date = ee.Date(date).advance(1, 'day')
            
            terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
            aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
            
            # Safe comparison with getInfo() results - use robust conversion
            terra_size = terra_imgs.size().getInfo()
            aqua_size = aqua_imgs.size().getInfo()
            terra_count = safe_int_conversion(terra_size)
            aqua_count = safe_int_conversion(aqua_size)
            
            if terra_count == 0 and aqua_count == 0:
                print(f"No images found for {date}: Terra={terra_count}, Aqua={aqua_count}")
                return 0
            
            print(f"Found images for {date}: Terra={terra_count}, Aqua={aqua_count}")
            
            # Advanced masking function that matches the main extraction
            def mask_snow_albedo(image):
                albedo = image.select('Snow_Albedo_Daily_Tile')
                qa = image.select('NDSI_Snow_Cover_Basic_QA')
                valid_albedo = albedo.gte(5).And(albedo.lte(99))
                good_quality = qa.lte(qa_threshold)
                
                # Apply advanced algorithm flags if enabled
                if use_advanced_qa and algorithm_flags:
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
                else:
                    final_quality = good_quality
                
                return albedo.updateMask(valid_albedo.And(final_quality)).multiply(0.01)
            
            # Combine Terra and Aqua
            all_images = terra_imgs.merge(aqua_imgs)
            processed = all_images.map(mask_snow_albedo).mosaic()
        
        # Count valid pixels
        count_result = processed.clip(roi).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=500,
            maxPixels=1e6
        )
        
        # Get the count value more safely
        count_dict = count_result.getInfo()
        
        # The dictionary might have different keys depending on the band name
        if isinstance(count_dict, dict) and count_dict:
            # Get the first value from the dictionary
            pixel_count_raw = list(count_dict.values())[0]
            
            # Use our robust conversion function
            result = safe_int_conversion(pixel_count_raw)
            print(f"Final pixel count for {date}: {result} (from dict: {count_dict})")
            return result
        else:
            print(f"No count_dict for {date} or empty dict: {count_dict}")
            return 0
        
    except Exception as e:
        print(f"ERROR COUNT: Error counting pixels for {date}: {e}")
        print(f"ERROR COUNT TYPE: {type(e)}")
        print(f"ERROR COUNT STR: {str(e)}")
        return 0