"""
Pixel Processing Module
Handles conversion of MODIS images to GeoJSON pixel features
"""

import streamlit as st


def _process_pixels_to_geojson(combined_image, roi, date, product_name, quality_description, silent):
    """Convert MODIS image to GeoJSON pixel features with detailed properties"""
    import ee
    
    # Clip to glacier boundary (including satellite source band if present)
    albedo_clipped = combined_image.select('albedo_daily').clip(roi)
    
    # Check if satellite source band exists (for MOD10A1/MYD10A1)
    band_names = combined_image.bandNames().getInfo()
    has_satellite_source = 'satellite_source' in band_names
    
    if has_satellite_source:
        satellite_source_clipped = combined_image.select('satellite_source').clip(roi)
    
    # Check if we have any valid pixels
    pixel_count = albedo_clipped.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=roi,
        scale=500,
        maxPixels=1e6
    ).get('albedo_daily').getInfo()
    
    if pixel_count == 0:
        if not silent:
            with st.sidebar:
                st.warning(f"❌ No valid pixels found after quality filtering for {date}")
        return None
    
    # Convert to integer for reduceToVectors (multiply by 1000 to preserve precision)
    albedo_int = albedo_clipped.multiply(1000).int()
    
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
        
        # Convert back to original albedo scale (divide by 1000) - ensure EE type
        pixel_albedo = ee.Number(albedo_int_value).divide(1000)
        
        # Get exact value with more flexible parameters
        try:
            pixel_albedo_exact = albedo_clipped.reduceRegion(
                reducer=ee.Reducer.mean(),  # Use mean instead of first
                geometry=feature.geometry(),
                scale=500,
                maxPixels=10,  # Allow more pixels
                bestEffort=True  # Use best effort approach
            ).get('albedo_daily')
            # Ensure it's an EE Number
            pixel_albedo_exact = ee.Number(pixel_albedo_exact)
        except:
            # If exact extraction fails, use the converted value
            pixel_albedo_exact = pixel_albedo
        
        # Get satellite source for this pixel (if available)
        if has_satellite_source:
            try:
                satellite_value = satellite_source_clipped.reduceRegion(
                    reducer=ee.Reducer.mode(),  # Most common value in pixel
                    geometry=feature.geometry(),
                    scale=500,
                    maxPixels=10,
                    bestEffort=True
                ).get('satellite_source')
                
                # Convert satellite code to name (1=Terra, 2=Aqua) - ensure string type
                satellite_name = ee.Algorithms.If(
                    ee.Number(satellite_value).eq(1), 
                    ee.String('Terra'), 
                    ee.String('Aqua')
                )
            except:
                # Fallback if satellite extraction fails
                satellite_name = ee.String('Unknown')
        else:
            satellite_name = None
        
        # Get pixel area with error margin for geometry operations
        try:
            pixel_area = feature.geometry().area(maxError=1)  # 1 meter error margin
        except:
            # Fallback to approximate area (500m x 500m for MODIS)
            pixel_area = ee.Number(250000)  # 500m * 500m = 250,000 m²
        
        # Set properties individually with proper EE types
        property_dict = {
            'albedo_value': pixel_albedo,
            'albedo_exact': pixel_albedo_exact,
            'date': ee.String(date),
            'product': ee.String(product_name),
            'quality_filter': ee.String(quality_description),
            'pixel_area_m2': pixel_area
        }
        
        # Add satellite info if available
        if satellite_name is not None:
            property_dict['satellite'] = satellite_name
        
        # Set all properties at once to avoid type conflicts
        result = feature.set(property_dict)
        
        return result
    
    # Apply properties to all pixels with error handling
    try:
        pixels_with_data = pixel_vectors.map(add_pixel_properties)
        
        # Limit pixels for performance (reasonable default)
        pixels_limited = pixels_with_data.limit(200)
        
        # Export as GeoJSON
        geojson = pixels_limited.getInfo()
        
        # Analyze satellite source distribution and display results
        if not silent:
            _display_pixel_statistics(geojson, date, has_satellite_source)
        
        return geojson
        
    except Exception as map_error:
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
    
    if has_satellite_source:
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


def count_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1):
    """
    Fast pixel count for a specific date (no detailed extraction)
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        product: 'MOD10A1' for daily snow albedo or 'MCD43A3' for broadband albedo
        qa_threshold: Quality threshold (0=strict, 1=standard, 2=relaxed)
        
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
            
            if images.size().getInfo() == 0:
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
            
            if terra_imgs.size().getInfo() == 0 and aqua_imgs.size().getInfo() == 0:
                return 0
            
            # Simple masking function
            def mask_snow_albedo(image):
                albedo = image.select('Snow_Albedo_Daily_Tile')
                qa = image.select('NDSI_Snow_Cover_Basic_QA')
                valid_albedo = albedo.gte(5).And(albedo.lte(99))
                good_quality = qa.lte(qa_threshold)
                return albedo.updateMask(valid_albedo.And(good_quality)).multiply(0.01)
            
            # Combine Terra and Aqua
            all_images = terra_imgs.merge(aqua_imgs)
            processed = all_images.map(mask_snow_albedo).mosaic()
        
        # Count valid pixels - FIXED: properly handle the result
        count_result = processed.clip(roi).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=500,
            maxPixels=1e6
        )
        
        # Get the count value more safely
        count_dict = count_result.getInfo()
        
        # The dictionary might have different keys depending on the band name
        # Try to get the first value regardless of the key
        if isinstance(count_dict, dict) and count_dict:
            # Get the first value from the dictionary
            pixel_count = list(count_dict.values())[0]
            
            # If the value is a list (which can happen with multi-band images),
            # take the first element
            if isinstance(pixel_count, list):
                pixel_count = pixel_count[0] if pixel_count else 0
                
            return int(pixel_count) if pixel_count is not None else 0
        else:
            return 0
        
    except Exception as e:
        print(f"Error counting pixels: {e}")
        return 0
