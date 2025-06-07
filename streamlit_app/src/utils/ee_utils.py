"""
Earth Engine Utilities for Streamlit Dashboard
Handles Earth Engine initialization and MODIS pixel extraction
"""

import streamlit as st
import json


@st.cache_data(ttl=300)  # Cache for 5 minutes
def initialize_earth_engine():
    """
    Initialize Earth Engine with proper authentication
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import ee
        
        # Try to initialize (may work if already authenticated)
        try:
            ee.Initialize()
            return True
        except:
            # Try service account authentication
            try:
                import os
                
                # Check for service account key file
                possible_paths = [
                    os.path.expanduser('~/.config/earthengine/credentials'),
                    os.path.join(os.getcwd(), 'ee-service-account.json'),
                    os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
                ]
                
                for key_path in possible_paths:
                    if os.path.exists(key_path):
                        ee.Initialize()
                        return True
                
                # If no service account, try interactive auth
                st.info("🔐 Earth Engine authentication required for pixel visualization")
                st.info("💡 Please run 'earthengine authenticate' in your terminal")
                return False
                
            except Exception as e:
                st.warning(f"Earth Engine initialization failed: {e}")
                return False
                
    except ImportError:
        st.error("Earth Engine library not installed. Install with: pip install earthengine-api")
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
        
        st.info(f"Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
        
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
            st.warning(f"No valid pixels found after quality filtering for {date}")
            return None
            
        st.info(f"Found {pixel_count} valid pixels after quality filtering")
        
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
                st.info("Using fallback vector conversion with reduced complexity")
            except Exception as fallback_error:
                st.error(f"Both standard and fallback vector conversion failed: {fallback_error}")
                return None
        
        # Add detailed properties to each pixel
        def add_pixel_properties(feature):
            # Get the integer albedo value from the feature properties
            albedo_int_value = feature.get('albedo_int')
            
            # Convert back to original albedo scale (divide by 1000)
            pixel_albedo = ee.Number(albedo_int_value).divide(1000)
            
            # Also get the exact value from the original image for verification
            pixel_albedo_exact = albedo_clipped.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=feature.geometry(),
                scale=500,
                maxPixels=1
            ).get('albedo_daily')
            
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
                
                # Add only basic properties
                def add_basic_properties(feature):
                    albedo_int_value = feature.get('albedo_int')
                    pixel_albedo = ee.Number(albedo_int_value).divide(1000)
                    
                    return feature.set({
                        'albedo_value': pixel_albedo,
                        'date': date,
                        'pixel_area_m2': 250000,  # Fixed MODIS pixel size
                        'product': 'MOD10A1/MYD10A1'
                    })
                
                simple_pixels_with_data = simple_pixels.map(add_basic_properties)
                geojson = simple_pixels_with_data.getInfo()
                
                st.info(f"Using simplified visualization with {len(geojson.get('features', []))} pixels")
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