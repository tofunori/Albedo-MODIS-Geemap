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
        
        # Only try if we have secrets configured
        if 'gee_service_account' in st.secrets:
            try:
                # Simple service account setup
                credentials = ee.ServiceAccountCredentials(
                    st.secrets['gee_service_account']['client_email'],
                    key_data=dict(st.secrets['gee_service_account'])
                )
                ee.Initialize(credentials)
                return True
            except Exception as e:
                st.sidebar.error(f"Earth Engine auth failed: {str(e)[:50]}...")
                return False
        
        # Try simple project auth if available
        if 'gee_project' in st.secrets:
            try:
                ee.Initialize(project=st.secrets['gee_project'])
                return True
            except:
                return False
        
        # For local development only
        try:
            ee.Initialize()
            return True
        except:
            return False
            
    except ImportError:
        return False
    except Exception:
        return False


def get_modis_pixels_for_date(date, roi):
    """
    Get MODIS pixel boundaries with albedo values for a specific date
    Uses the same quality filtering as the main analysis (QA ≤ 1)
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        
    Returns:
        dict: GeoJSON with MODIS pixel features and albedo values
    """
    try:
        import ee
        
        # MODIS collections (same as used in main analysis)
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
        
        # Display in sidebar instead of main area
        with st.sidebar:
            st.markdown("**🛰️ Processing Status:**")
            st.write(f"📡 Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
        
        if terra_count == 0 and aqua_count == 0:
            return None
            
        # Apply the same masking function as used in main analysis
        def mask_modis_snow_albedo(image):
            """Apply the same quality filtering as main analysis"""
            albedo = image.select('Snow_Albedo_Daily_Tile')
            qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            # Same filtering as in your extraction.py: QA ≤ 1 and valid albedo range
            valid_albedo = albedo.gte(5).And(albedo.lte(99))  # 5-99 range before scaling
            good_quality = qa.lte(1)  # QA ≤ 1: Best and good quality (not just 0)
            
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
                'product': 'MOD10A1/MYD10A1',
                'quality_filter': 'QA ≤ 1, range 0.05-0.99'
            })
        
        # Apply properties to all pixels with error handling
        try:
            pixels_with_data = pixel_vectors.map(add_pixel_properties)
            
            # Limit pixels for performance (but allow more than before)
            pixels_limited = pixels_with_data.limit(200)  # Increased from 100
            
            # Export as GeoJSON
            geojson = pixels_limited.getInfo()
            
            return geojson
            
        except Exception as map_error:
            # If mapping fails, try simpler approach without additional properties
            st.warning(f"Advanced pixel properties failed: {map_error}")
            st.info("Falling back to basic pixel visualization...")
            
            try:
                # Simplified approach - just convert to vectors without complex properties
                simple_pixels = pixel_vectors.limit(50)  # Fewer pixels for stability
                
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
                        'product': 'MOD10A1/MYD10A1',
                        'processing': 'simplified'
                    })
                
                simple_pixels_with_data = simple_pixels.map(add_basic_properties)
                geojson = simple_pixels_with_data.getInfo()
                
                with st.sidebar:
                    st.write(f"📊 Using simplified visualization with {len(geojson.get('features', []))} pixels")
                return geojson
                
            except Exception as simple_error:
                st.error(f"Both advanced and simple pixel extraction failed: {simple_error}")
                return None
        
    except Exception as e:
        print(f"Error getting MODIS pixels: {e}")
        st.error(f"Detailed error: {str(e)}")
        return None


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