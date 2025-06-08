"""
Pre-generate MODIS pixel GeoJSON files for specific dates
This script should be run locally where Earth Engine authentication works
The generated files can then be used by the Streamlit app without authentication
"""

import ee
import json
import os
from datetime import datetime, timedelta
import pandas as pd

# Initialize Earth Engine (requires local authentication)
ee.Initialize()

def get_modis_pixels_for_date(date_str, roi):
    """Extract MODIS pixels for a specific date"""
    
    # MODIS collections
    mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
    myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
    
    # Filter by date
    date = ee.Date(date_str)
    start_date = date.advance(-1, 'day')
    end_date = date.advance(1, 'day')
    
    # Get images for the date
    terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
    aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
    
    # Apply quality filtering
    def mask_modis_snow_albedo(image):
        albedo = image.select('Snow_Albedo_Daily_Tile')
        qa = image.select('NDSI_Snow_Cover_Basic_QA')
        
        valid_albedo = albedo.gte(5).And(albedo.lte(99))
        good_quality = qa.lte(1)  # QA = 1 by default (best + good quality)
        
        masked = albedo.updateMask(valid_albedo.And(good_quality)).multiply(0.01)
        return masked.rename('albedo_daily')
    
    # Process images
    all_images = terra_imgs.merge(aqua_imgs)
    processed = all_images.map(mask_modis_snow_albedo)
    
    if processed.size().getInfo() == 0:
        return None
        
    # Create mosaic
    mosaic = processed.mosaic().clip(roi)
    
    # Convert to vectors
    albedo_int = mosaic.multiply(1000).int()
    
    try:
        vectors = albedo_int.reduceToVectors(
            geometry=roi,
            crs=albedo_int.projection(),
            scale=500,
            geometryType='polygon',
            eightConnected=False,
            maxPixels=1e6,
            bestEffort=True,
            labelProperty='albedo_int'
        )
        
        # Clip to glacier and add properties
        def process_pixel(feature):
            # Clip to glacier boundary
            clipped_geom = feature.geometry().intersection(roi, maxError=1)
            pixel_area = clipped_geom.area(maxError=1)
            
            # Get albedo value
            albedo_int_val = feature.get('albedo_int')
            albedo_val = ee.Number(albedo_int_val).divide(1000)
            
            return ee.Feature(clipped_geom, {
                'albedo_value': albedo_val,
                'date': date_str,
                'pixel_area_m2': pixel_area,
                'product': 'MOD10A1/MYD10A1'
            })
        
        processed_vectors = vectors.map(process_pixel)
        
        # Convert to GeoJSON
        geojson = processed_vectors.getInfo()
        return geojson
        
    except Exception as e:
        print(f"Error processing {date_str}: {e}")
        return None


def main():
    """Generate pixel data for key dates"""
    
    # Load glacier boundary
    with open('Athabasca_mask_2023_cut.geojson', 'r') as f:
        glacier_geojson = json.load(f)
    
    # Convert to Earth Engine geometry
    coords = glacier_geojson['features'][0]['geometry']['coordinates'][0]
    roi = ee.Geometry.Polygon(coords)
    
    # Key dates to generate (you can modify this list)
    dates_to_generate = [
        '2023-08-15',
        '2023-08-17',
        '2023-07-20',
        '2023-06-15',
        '2023-09-15',
        '2022-08-15',
        '2021-08-15',
        '2020-08-15',
        '2019-08-15',
        '2018-08-15',
        '2017-08-15',
        '2016-08-15',
        '2015-08-15',
    ]
    
    # Create output directory
    output_dir = 'modis_pixels'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate pixel data for each date
    for date_str in dates_to_generate:
        print(f"Processing {date_str}...")
        
        pixel_data = get_modis_pixels_for_date(date_str, roi)
        
        if pixel_data:
            # Save to file
            output_file = os.path.join(output_dir, f'modis_pixels_{date_str}.geojson')
            with open(output_file, 'w') as f:
                json.dump(pixel_data, f, indent=2)
            print(f"✅ Saved {output_file}")
        else:
            print(f"❌ No data for {date_str}")
    
    # Create an index file
    index = {
        'generated_date': datetime.now().isoformat(),
        'available_dates': [d for d in dates_to_generate if os.path.exists(
            os.path.join(output_dir, f'modis_pixels_{d}.geojson')
        )]
    }
    
    with open(os.path.join(output_dir, 'index.json'), 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"\n✅ Generated pixel data for {len(index['available_dates'])} dates")
    print("📁 Upload the 'modis_pixels' folder to your GitHub repository")


if __name__ == "__main__":
    main()