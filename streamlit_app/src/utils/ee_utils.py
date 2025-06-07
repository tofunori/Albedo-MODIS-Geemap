"""
Earth Engine Utilities for Streamlit Dashboard
Handles Earth Engine initialization and MODIS pixel extraction
"""

import streamlit as st
import json


@st.cache_data(ttl=60)  # Cache for 1 minute only
def initialize_earth_engine():
    """
    Initialize Earth Engine - fast fail version
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Quick check - if we're clearly online and have no secrets, fail fast
    import os
    if not st.secrets and ('HOSTNAME' in os.environ or 'STREAMLIT_SHARING_MODE' in os.environ):
        return False
    
    try:
        import ee
        
        # METHOD 1: Try regular service account format
        if 'gee_service_account' in st.secrets:
            try:
                # Get the service account data from Streamlit secrets
                service_account_info = dict(st.secrets['gee_service_account'])
                
                # Debug info removed for cleaner interface
                
                # Ensure all required fields are present
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
                missing_fields = [field for field in required_fields if field not in service_account_info]
                
                if missing_fields:
                    st.sidebar.error(f"Missing required fields: {missing_fields}")
                    return False
                
                # Create credentials with the service account data
                credentials = ee.ServiceAccountCredentials(
                    service_account_info['client_email'],
                    key_data=service_account_info
                )
                ee.Initialize(credentials)
                # st.sidebar.success("✅ Earth Engine authenticated!")  # Removed message
                return True
                
            except Exception as e:
                error_msg = str(e)
                st.sidebar.error(f"Auth failed: {error_msg[:80]}...")
                
                # Give specific help based on error type
                if "JSON object must be str" in error_msg:
                    st.sidebar.warning("⚠️ JSON format issue - try base64 method")
                elif "Invalid service account" in error_msg:
                    st.sidebar.warning("⚠️ Service account not registered")
                    st.sidebar.info("Register at: code.earthengine.google.com/register")
                elif "private_key" in error_msg:
                    st.sidebar.warning("⚠️ Private key format issue")
                    st.sidebar.info("Try using triple quotes: private_key = \"\"\"...\"\"\"")
                
        # METHOD 2: Try base64 encoded service account
        if 'gee_service_account_b64' in st.secrets:
            try:
                import base64
                import json
                
                # Decode base64 service account
                service_account_json = base64.b64decode(st.secrets['gee_service_account_b64']).decode()
                service_account_dict = json.loads(service_account_json)
                
                # Create credentials
                credentials = ee.ServiceAccountCredentials(
                    service_account_dict['client_email'],
                    key_data=service_account_dict
                )
                ee.Initialize(credentials)
                # st.sidebar.success("✅ Earth Engine authenticated (base64)!")  # Removed message
                return True
                
            except Exception as e:
                st.sidebar.error(f"Base64 auth failed: {str(e)[:80]}...")
        
        # METHOD 3: Simple project auth (if available)
        if 'gee_project' in st.secrets:
            try:
                ee.Initialize(project=st.secrets['gee_project'])
                # st.sidebar.success("✅ Earth Engine authenticated (project)!")  # Removed message
                return True
            except Exception as e:
                st.sidebar.error(f"Project auth failed: {str(e)[:50]}...")
        
        # METHOD 4: LOCAL DEVELOPMENT - Simple authentication
        try:
            # This works if you've run 'earthengine authenticate' locally
            ee.Initialize()
            # st.sidebar.success("✅ Earth Engine authenticated (local)!")  # Removed message
            return True
        except Exception as e:
            # Check if we're running locally vs online
            import os
            if 'HOSTNAME' not in os.environ and 'STREAMLIT_SHARING_MODE' not in os.environ:
                # We're likely running locally
                st.sidebar.warning("🔐 Local authentication needed")
                st.sidebar.info("💡 Run in terminal: `earthengine authenticate`")
            
        return False
            
    except ImportError:
        return False
    except Exception:
        return False


def get_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1):
    """
    Get MODIS pixel boundaries with albedo values for a specific date
    Uses configurable quality filtering
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        product: 'MOD10A1' for daily snow albedo or 'MCD43A3' for broadband albedo
        qa_threshold: Quality threshold (0=strict, 1=standard, 2=relaxed for MOD10A1)
        
    Returns:
        dict: GeoJSON with MODIS pixel features and albedo values
    """
    try:
        import ee
        
        if product == 'MCD43A3':
            # MCD43A3 (Broadband Albedo) handling
            mcd43a3 = ee.ImageCollection('MODIS/061/MCD43A3')
            
            # Filter by date (±1 day for better coverage)
            start_date = ee.Date(date).advance(-1, 'day')
            end_date = ee.Date(date).advance(1, 'day')
            
            # Get images for the date with boundary filter
            images = mcd43a3.filterDate(start_date, end_date).filterBounds(roi)
            
            # Check if we have data
            image_count = images.size().getInfo()
            
            # Display in sidebar
            with st.sidebar:
                st.markdown("**🛰️ Processing Status:**")
                st.write(f"📡 Found {image_count} MCD43A3 images for {date}")
            
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
                valid_range = masked.gte(0.0).And(masked.lte(1.0))
                masked = masked.updateMask(valid_range)
                
                return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
            
            # Process images
            processed_images = images.map(mask_mcd43a3_albedo)
            
            # Create mosaic
            combined_image = processed_images.mosaic()
            
            # Product identification for properties
            product_name = 'MCD43A3'
            if qa_threshold == 0:
                quality_description = 'QA = 0 (full BRDF), range 0.0-1.0'
            else:
                quality_description = f'QA ≤ {qa_threshold} (includes magnitude), range 0.0-1.0'
            
        else:
            # MOD10A1/MYD10A1 (Daily Snow Albedo) handling - original code
            mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
            myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
            
            # Filter by date (±1 day for better coverage)
            start_date = ee.Date(date).advance(-1, 'day')
            end_date = ee.Date(date).advance(1, 'day')
            
            # Get images for the date with boundary filter
            terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
            aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
            
            # Check if we have data
            terra_count = terra_imgs.size().getInfo()
            aqua_count = aqua_imgs.size().getInfo()
            
            # Display in sidebar
            with st.sidebar:
                st.markdown("**🛰️ Processing Status:**")
                st.write(f"📡 Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
            
            if terra_count == 0 and aqua_count == 0:
                return None
                
            # Apply configurable masking function for MOD10A1/MYD10A1
            def mask_modis_snow_albedo(image):
                """Apply configurable quality filtering for MOD10A1/MYD10A1"""
                albedo = image.select('Snow_Albedo_Daily_Tile')
                qa = image.select('NDSI_Snow_Cover_Basic_QA')
                
                # Apply configurable quality threshold
                valid_albedo = albedo.gte(5).And(albedo.lte(99))  # 5-99 range before scaling
                good_quality = qa.lte(qa_threshold)  # Use configurable threshold
                
                # Apply masks and scale
                masked = albedo.updateMask(valid_albedo.And(good_quality)).multiply(0.01)
                
                return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
            
            # Process Terra and Aqua separately
            processed_images = []
            
            if terra_count > 0:
                terra_processed = terra_imgs.map(mask_modis_snow_albedo)
                processed_images.append(terra_processed)
                
            if aqua_count > 0:
                aqua_processed = aqua_imgs.map(mask_modis_snow_albedo)
                processed_images.append(aqua_processed)
            
            # Combine all processed images
            if len(processed_images) == 1:
                combined_collection = processed_images[0]
            else:
                combined_collection = processed_images[0].merge(processed_images[1])
                
            # Create mosaic (Terra has priority if both available on same time)
            combined_image = combined_collection.mosaic()
            
            # Product identification for properties
            product_name = 'MOD10A1/MYD10A1'
            if qa_threshold == 0:
                quality_description = 'QA = 0 (best quality), range 0.05-0.99'
            elif qa_threshold == 1:
                quality_description = 'QA ≤ 1 (best+good), range 0.05-0.99'
            else:
                quality_description = f'QA ≤ {qa_threshold} (includes fair), range 0.05-0.99'
        
        # Clip to glacier boundary
        albedo_clipped = combined_image.select('albedo_daily').clip(roi)
        
        # Check if we have any valid pixels
        pixel_count = albedo_clipped.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=500,
            maxPixels=1e6
        ).get('albedo_daily').getInfo()
        
        if pixel_count == 0:
            with st.sidebar:
                st.warning(f"❌ No valid pixels found after quality filtering for {date}")
            return None
            
        # Display in sidebar instead of main area
        with st.sidebar:
            st.write(f"✅ Found {pixel_count} valid pixels after quality filtering")
        
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
                clipped_geom = feature.geometry().intersection(roi, maxError=1)
                
                # Only keep pixels that have significant intersection with glacier
                pixel_area = clipped_geom.area(maxError=1)
                
                # Skip tiny intersections (less than 10% of MODIS pixel = 25,000 m²)
                return ee.Feature(clipped_geom, feature.toDictionary()).set('intersect_area', pixel_area)
            
            # Apply clipping to glacier boundary
            clipped_pixels = pixel_vectors.map(clip_pixel_to_glacier)
            
            # Filter out pixels with very small intersections
            pixel_vectors = clipped_pixels.filter(ee.Filter.gte('intersect_area', 25000))
            
            with st.sidebar:
                st.write("🏔️ Pixels properly clipped to glacier boundary")
            
        except Exception as vector_error:
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
                    st.info("Using fallback vector conversion with basic glacier clipping")
                except:
                    st.info("Using fallback vector conversion without clipping")
                    
            except Exception as fallback_error:
                st.error(f"Both standard and fallback vector conversion failed: {fallback_error}")
                return None
        
        # Add detailed properties to each pixel
        def add_pixel_properties(feature):
            # Get the integer albedo value from the feature properties
            albedo_int_value = feature.get('albedo_int')
            
            # Convert back to original albedo scale (divide by 1000)
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
            except:
                # If exact extraction fails, use the converted value
                pixel_albedo_exact = pixel_albedo
            
            # Get pixel area with error margin for geometry operations
            try:
                pixel_area = feature.geometry().area(maxError=1)  # 1 meter error margin
            except:
                # Fallback to approximate area (500m x 500m for MODIS)
                pixel_area = ee.Number(250000)  # 500m * 500m = 250,000 m²
            
            return feature.set({
                'albedo_value': pixel_albedo,
                'albedo_exact': pixel_albedo_exact,
                'date': date,
                'pixel_area_m2': pixel_area,
                'product': product_name,
                'quality_filter': quality_description
            })
        
        # Apply properties to all pixels with error handling
        try:
            pixels_with_data = pixel_vectors.map(add_pixel_properties)
            
            # Limit pixels for performance (reasonable default)
            pixels_limited = pixels_with_data.limit(200)
            
            # Export as GeoJSON
            geojson = pixels_limited.getInfo()
            
            # Display actual pixel count
            actual_count = len(geojson.get('features', []))
            with st.sidebar:
                st.write(f"📊 Displaying {actual_count} pixels")
            
            return geojson
            
        except Exception as map_error:
            # If mapping fails, try simpler approach without additional properties
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
                        ee.Number(0.5),  # Default value if missing
                        ee.Number(albedo_int_value).divide(1000)
                    )
                    
                    return feature.set({
                        'albedo_value': pixel_albedo,
                        'date': date,
                        'pixel_area_m2': 250000,  # Fixed MODIS pixel size (500m x 500m)
                        'product': product_name,
                        'processing': 'simplified'
                    })
                
                simple_pixels_with_data = simple_pixels.map(add_basic_properties)
                geojson = simple_pixels_with_data.getInfo()
                
                actual_count = len(geojson.get('features', []))
                with st.sidebar:
                    st.write(f"📊 Using simplified visualization with {actual_count} pixels")
                    st.write(f"⚠️ Fallback mode (limited to 50 pixels)")
                return geojson
                
            except Exception as simple_error:
                st.error(f"Both advanced and simple pixel extraction failed: {simple_error}")
                return None
        
    except Exception as e:
        print(f"Error getting MODIS pixels: {e}")
        st.error(f"Detailed error: {str(e)}")
        return None


def count_modis_pixels_for_date(date, roi, product='MOD10A1', qa_threshold=1):
    """
    Count the number of valid MODIS pixels for a specific date (fast operation)
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        product: 'MOD10A1' for daily snow albedo or 'MCD43A3' for broadband albedo
        qa_threshold: Quality threshold for filtering
        
    Returns:
        int: Number of valid pixels (0 if error or no data)
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
            
            # Apply quality filtering
            def mask_mcd43a3_albedo(image):
                albedo = image.select('Albedo_BSA_shortwave')
                qa_band1 = image.select('BRDF_Albedo_Band_Mandatory_Quality_Band1')
                good_quality = qa_band1.lte(qa_threshold)
                masked = albedo.updateMask(good_quality).multiply(0.001)
                valid_range = masked.gte(0.0).And(masked.lte(1.0))
                return masked.updateMask(valid_range).rename('albedo_daily')
            
            processed_images = images.map(mask_mcd43a3_albedo)
            combined_image = processed_images.mosaic()
            
        else:
            # MOD10A1/MYD10A1 handling
            mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
            myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
            start_date = ee.Date(date).advance(-1, 'day')
            end_date = ee.Date(date).advance(1, 'day')
            
            terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
            aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
            
            if terra_imgs.size().getInfo() == 0 and aqua_imgs.size().getInfo() == 0:
                return 0
            
            # Apply quality filtering
            def mask_modis_snow_albedo(image):
                albedo = image.select('Snow_Albedo_Daily_Tile')
                qa = image.select('NDSI_Snow_Cover_Basic_QA')
                valid_albedo = albedo.gte(5).And(albedo.lte(99))
                good_quality = qa.lte(qa_threshold)
                return albedo.updateMask(valid_albedo.And(good_quality)).multiply(0.01).rename('albedo_daily')
            
            processed_images = []
            if terra_imgs.size().getInfo() > 0:
                processed_images.append(terra_imgs.map(mask_modis_snow_albedo))
            if aqua_imgs.size().getInfo() > 0:
                processed_images.append(aqua_imgs.map(mask_modis_snow_albedo))
            
            if len(processed_images) == 1:
                combined_collection = processed_images[0]
            else:
                combined_collection = processed_images[0].merge(processed_images[1])
            
            combined_image = combined_collection.mosaic()
        
        # Clip to glacier boundary and count pixels
        albedo_clipped = combined_image.select('albedo_daily').clip(roi)
        
        # Count valid pixels
        pixel_count = albedo_clipped.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=500,
            maxPixels=1e6
        ).get('albedo_daily').getInfo()
        
        return pixel_count if pixel_count is not None else 0
        
    except Exception as e:
        print(f"Error counting pixels for {date}: {e}")
        return 0


def get_roi_from_geojson(glacier_geojson):
    """
    Convert GeoJSON to Earth Engine geometry
    
    Args:
        glacier_geojson: Loaded GeoJSON data
        
    Returns:
        ee.Geometry: Earth Engine geometry for the glacier
    """
    try:
        import ee
        
        if glacier_geojson:
            # Convert geojson to Earth Engine geometry
            coords = glacier_geojson['features'][0]['geometry']['coordinates'][0]
            return ee.Geometry.Polygon(coords)
        else:
            # Fallback to approximate coordinates
            return ee.Geometry.Polygon([
                [[-117.3, 52.15], [-117.15, 52.15], [-117.15, 52.25], [-117.3, 52.25]]
            ])
    except Exception as e:
        print(f"Error creating ROI: {e}")
        # Fallback geometry
        import ee
        return ee.Geometry.Polygon([
            [[-117.3, 52.15], [-117.15, 52.15], [-117.15, 52.25], [-117.3, 52.25]]
        ])