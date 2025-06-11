#!/usr/bin/env python3
"""
Example workflow for MCD43A1 processing
Demonstrates complete pipeline from download to albedo calculation
"""

import os
import sys
import json
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcd43a1_downloader import MCD43A1Downloader
from mcd43a1_processor import MCD43A1Processor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def athabasca_glacier_workflow():
    """
    Example workflow for Athabasca Glacier albedo analysis
    """
    logger.info("Starting Athabasca Glacier MCD43A1 workflow")
    
    # Configuration
    config = {
        'year': 2024,
        'doy_range': (152, 273),  # Melt season: June 1 - September 30
        'tiles': ['h10v03'],      # Athabasca Glacier tile
        'bands': [1, 2, 6, 7],    # Red, NIR, SWIR1, SWIR2
        'output_dir': 'athabasca_workflow',
        'max_files': 20,          # Limit for testing
        'target_crs': 'EPSG:32612'  # UTM Zone 12N for Canadian Rockies
    }
    
    # Create output directories
    data_dir = Path(config['output_dir']) / 'data'
    processed_dir = Path(config['output_dir']) / 'processed'
    
    # Step 1: Download MCD43A1 data
    logger.info("Step 1: Downloading MCD43A1 data")
    
    downloader = MCD43A1Downloader(base_dir=str(data_dir))
    
    # Download melt season data
    downloaded_files = downloader.download_batch(
        year=config['year'],
        doy_range=config['doy_range'],
        tiles=config['tiles'],
        max_files=config['max_files']
    )
    
    if not any(downloaded_files.values()):
        logger.error("No files downloaded. Check authentication and availability.")
        return False
    
    total_downloaded = sum(len(files) for files in downloaded_files.values())
    logger.info(f"Downloaded {total_downloaded} files")
    
    # Step 2: Process BRDF parameters to calculate albedo
    logger.info("Step 2: Processing BRDF parameters")
    
    processor = MCD43A1Processor(output_dir=str(processed_dir))
    
    # Process all downloaded files
    all_hdf_files = []
    for tile, files in downloaded_files.items():
        all_hdf_files.extend(files)
    
    results = {}
    for hdf_file in all_hdf_files:
        try:
            output_files = processor.process_file(hdf_file, bands=config['bands'])
            results[hdf_file] = output_files
            
            # Reproject to target CRS
            for output_type, output_path in output_files.items():
                reprojected = processor.reproject_file(output_path, config['target_crs'])
                if reprojected:
                    logger.info(f"Reprojected {output_type}")
                    
        except Exception as e:
            logger.error(f"Error processing {hdf_file}: {e}")
            results[hdf_file] = {}
    
    # Step 3: Generate summary report
    logger.info("Step 3: Generating summary report")
    
    summary_path = processor.create_summary_report(results)
    
    # Step 4: Create analysis summary
    logger.info("Step 4: Creating analysis summary")
    
    analysis_summary = {
        'workflow': 'Athabasca Glacier MCD43A1 Analysis',
        'date_processed': datetime.now().isoformat(),
        'configuration': config,
        'download_summary': {
            'total_files_downloaded': total_downloaded,
            'files_by_tile': {tile: len(files) for tile, files in downloaded_files.items()}
        },
        'processing_summary': {
            'total_files_processed': len(results),
            'successful_files': len([r for r in results.values() if r]),
            'total_output_products': sum(len(outputs) for outputs in results.values())
        },
        'output_directories': {
            'raw_data': str(data_dir),
            'processed_data': str(processed_dir),
            'summary_report': summary_path
        }
    }
    
    # Save analysis summary
    analysis_path = Path(config['output_dir']) / 'analysis_summary.json'
    with open(analysis_path, 'w') as f:
        json.dump(analysis_summary, f, indent=2)
    
    logger.info(f"Analysis summary saved to {analysis_path}")
    
    # Print final summary
    print("\n" + "="*50)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("="*50)
    print(f"Downloaded files: {total_downloaded}")
    print(f"Processed files: {len(results)}")
    print(f"Output directory: {config['output_dir']}")
    print(f"Target CRS: {config['target_crs']}")
    print(f"Summary report: {summary_path}")
    print("="*50)
    
    return True

def multi_year_glacier_analysis():
    """
    Example workflow for multi-year glacier analysis
    """
    logger.info("Starting multi-year glacier analysis workflow")
    
    # Configuration for multi-year analysis
    config = {
        'years': [2020, 2021, 2022, 2023, 2024],
        'doy_range': (152, 273),  # Melt season
        'tiles': ['h10v03'],
        'bands': [1, 2, 6, 7],
        'output_dir': 'multi_year_analysis',
        'max_files_per_year': 10,
        'sample_interval': 16  # Every 16 days
    }
    
    base_dir = Path(config['output_dir'])
    
    downloader = MCD43A1Downloader(base_dir=str(base_dir / 'data'))
    processor = MCD43A1Processor(output_dir=str(base_dir / 'processed'))
    
    yearly_results = {}
    
    for year in config['years']:
        logger.info(f"Processing year {year}")
        
        # Download data for this year
        downloaded = downloader.download_batch(
            year=year,
            doy_range=config['doy_range'],
            tiles=config['tiles'],
            max_files=config['max_files_per_year']
        )
        
        # Process downloaded files
        year_results = {}
        for tile, files in downloaded.items():
            for hdf_file in files:
                try:
                    outputs = processor.process_file(hdf_file, bands=config['bands'])
                    year_results[hdf_file] = outputs
                except Exception as e:
                    logger.error(f"Error processing {hdf_file}: {e}")
                    year_results[hdf_file] = {}
        
        yearly_results[year] = year_results
        
        logger.info(f"Year {year}: {len(year_results)} files processed")
    
    # Create multi-year summary
    summary = {
        'workflow': 'Multi-Year Glacier Analysis',
        'configuration': config,
        'results_by_year': {
            str(year): {
                'files_processed': len(results),
                'successful_files': len([r for r in results.values() if r])
            }
            for year, results in yearly_results.items()
        },
        'total_files_processed': sum(len(results) for results in yearly_results.values())
    }
    
    summary_path = base_dir / 'multi_year_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Multi-year analysis completed. Summary: {summary_path}")
    
    return True

def quick_test_workflow():
    """
    Quick test workflow for verifying setup
    """
    logger.info("Running quick test workflow")
    
    # Test configuration - single file
    config = {
        'year': 2024,
        'doy': 243,  # August 30, 2024
        'tiles': ['h10v03'],
        'bands': [6, 7],  # Just SWIR bands for quick test
        'output_dir': 'test_workflow'
    }
    
    base_dir = Path(config['output_dir'])
    
    # Step 1: Check file availability
    downloader = MCD43A1Downloader(base_dir=str(base_dir / 'data'))
    
    available = downloader.get_available_files(
        config['year'], 
        config['doy'], 
        config['tiles']
    )
    
    if not any(available.values()):
        logger.error("No files available for test date")
        return False
    
    logger.info(f"Available files: {available}")
    
    # Step 2: Download one file
    for tile, files in available.items():
        if files:
            first_file = files[0]
            downloaded_path = downloader.download_file(
                config['year'], 
                config['doy'], 
                first_file
            )
            
            if downloaded_path:
                logger.info(f"Downloaded test file: {downloaded_path}")
                
                # Step 3: Process the file
                processor = MCD43A1Processor(output_dir=str(base_dir / 'processed'))
                
                try:
                    outputs = processor.process_file(downloaded_path, bands=config['bands'])
                    logger.info(f"Processing successful. Outputs: {list(outputs.keys())}")
                    
                    # Step 4: Check outputs
                    for output_type, output_path in outputs.items():
                        if os.path.exists(output_path):
                            size = os.path.getsize(output_path)
                            logger.info(f"  {output_type}: {output_path} ({size} bytes)")
                        else:
                            logger.error(f"  {output_type}: File not found at {output_path}")
                    
                    logger.info("Quick test completed successfully!")
                    return True
                    
                except Exception as e:
                    logger.error(f"Processing failed: {e}")
                    return False
            
            break
    
    logger.error("Could not download test file")
    return False

def main():
    """Main function to run example workflows"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCD43A1 Example Workflows')
    parser.add_argument('--workflow', choices=['test', 'athabasca', 'multi-year'], 
                       default='test',
                       help='Workflow to run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"Running {args.workflow} workflow...")
    print()
    
    # Check authentication
    netrc_path = Path.home() / '.netrc'
    if not netrc_path.exists():
        print("⚠️ No .netrc file found. Please run setup_earthdata_auth.py first")
        print("   python setup_earthdata_auth.py")
        return
    
    # Run selected workflow
    if args.workflow == 'test':
        success = quick_test_workflow()
    elif args.workflow == 'athabasca':
        success = athabasca_glacier_workflow()
    elif args.workflow == 'multi-year':
        success = multi_year_glacier_analysis()
    
    if success:
        print("\n✅ Workflow completed successfully!")
    else:
        print("\n❌ Workflow failed. Check logs for details.")

if __name__ == "__main__":
    main()