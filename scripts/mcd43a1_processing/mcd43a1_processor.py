#!/usr/bin/env python3
"""
MCD43A1 BRDF Parameter Processor and Albedo Calculator
Processes downloaded MCD43A1 files to calculate BSA and WSA albedo

Usage:
    python mcd43a1_processor.py --input data/2024/243/MCD43A1.*.hdf --bands 1 2 6 7
    python mcd43a1_processor.py --process-all --input-dir data/2024
"""

import os
import sys
import argparse
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Optional, Union
import json
from datetime import datetime
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCD43A1Processor:
    """
    MCD43A1 BRDF Parameter Processor and Albedo Calculator
    """
    
    def __init__(self, output_dir: str = "processed"):
        """
        Initialize the processor
        
        Args:
            output_dir: Output directory for processed files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # BRDF parameter scaling factor
        self.scale_factor = 0.001
        
        # Fill values and valid ranges
        self.fill_value = 32767
        self.valid_range = (-100, 16000)  # Before scaling
        
        # MODIS band information
        self.band_info = {
            1: {'name': 'Red', 'wavelength': '620-670 nm', 'center': 645},
            2: {'name': 'NIR', 'wavelength': '841-876 nm', 'center': 858},
            3: {'name': 'Blue', 'wavelength': '459-479 nm', 'center': 469},
            4: {'name': 'Green', 'wavelength': '545-565 nm', 'center': 555},
            5: {'name': 'SWIR1', 'wavelength': '1230-1250 nm', 'center': 1240},
            6: {'name': 'SWIR2', 'wavelength': '1628-1652 nm', 'center': 1640},
            7: {'name': 'SWIR3', 'wavelength': '2105-2155 nm', 'center': 2130}
        }
        
        # Broadband shortwave coefficients (for combining bands to get shortwave albedo)
        # Based on Liang (2001) coefficients for MODIS
        self.shortwave_coeffs = {
            1: 0.3973,  # Red
            2: 0.2382,  # NIR
            3: 0.3489,  # Blue
            4: 0.2578,  # Green
            5: 0.1535,  # SWIR1
            6: 0.0845,  # SWIR2
            7: 0.0639   # SWIR3
        }
    
    def get_subdatasets(self, hdf_path: str) -> Dict[str, str]:
        """
        Get all subdatasets from MCD43A1 HDF file
        
        Args:
            hdf_path: Path to MCD43A1 HDF file
            
        Returns:
            Dictionary mapping subdataset names to paths
        """
        subdatasets = {}
        
        try:
            with rasterio.open(hdf_path) as src:
                for i, (name, desc) in enumerate(src.subdatasets):
                    # Extract parameter type and band from subdataset name
                    # Example: HDF4_EOS:EOS_GRID:"file.hdf":MOD_Grid_BRDF:BRDF_Albedo_Parameters_Band1_ISO
                    parts = name.split(':')
                    if len(parts) >= 5:
                        param_name = parts[-1]  # e.g., BRDF_Albedo_Parameters_Band1_ISO
                        subdatasets[param_name] = name
                        
        except Exception as e:
            logger.error(f"Error reading subdatasets from {hdf_path}: {e}")
            
        return subdatasets
    
    def read_brdf_parameter(self, hdf_path: str, band: int, param_type: str) -> Tuple[np.ndarray, dict]:
        """
        Read a specific BRDF parameter from MCD43A1 file
        
        Args:
            hdf_path: Path to MCD43A1 HDF file
            band: MODIS band number (1-7)
            param_type: Parameter type ('ISO', 'VOL', 'GEO')
            
        Returns:
            Tuple of (data array, rasterio profile)
        """
        # Construct subdataset name
        subdataset_name = f'HDF4_EOS:EOS_GRID:"{hdf_path}":MOD_Grid_BRDF:BRDF_Albedo_Parameters_Band{band}_{param_type}'
        
        try:
            with rasterio.open(subdataset_name) as src:
                data = src.read(1).astype(np.float32)
                profile = src.profile.copy()
                
                # Apply scaling and mask invalid values
                valid_mask = (data != self.fill_value) & (data >= self.valid_range[0]) & (data <= self.valid_range[1])
                data = np.where(valid_mask, data * self.scale_factor, np.nan)
                
                # Update profile for output
                profile.update(dtype=rasterio.float32, nodata=np.nan)
                
                return data, profile
                
        except Exception as e:
            logger.error(f"Error reading {param_type} parameter for band {band} from {hdf_path}: {e}")
            return None, None
    
    def calculate_albedo(self, f_iso: np.ndarray, f_vol: np.ndarray, f_geo: np.ndarray,
                        solar_zenith: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate BSA and WSA albedo from BRDF parameters
        
        Args:
            f_iso: Isotropic parameter
            f_vol: Volumetric scattering parameter
            f_geo: Geometric scattering parameter
            solar_zenith: Solar zenith angle in degrees (for BSA calculation)
            
        Returns:
            Tuple of (BSA albedo, WSA albedo)
        """
        # White-Sky Albedo (hemispheric-directional reflectance)
        # WSA = f_iso + 0.189 * f_vol + 1.377 * f_geo
        wsa = f_iso + 0.189 * f_vol + 1.377 * f_geo
        
        # Black-Sky Albedo (directional-hemispheric reflectance)
        # For nadir view (θ_s = 0°): BSA ≈ f_iso
        # More complex formula for other angles can be implemented
        if solar_zenith == 0.0:
            bsa = f_iso.copy()
        else:
            # Simplified calculation for non-zero solar zenith
            # Full implementation would require Ross-Li kernels
            theta_rad = np.radians(solar_zenith)
            cos_theta = np.cos(theta_rad)
            
            # Simplified Ross-Li kernel approximation
            k_vol = (np.pi/2 - theta_rad) * cos_theta + np.sin(theta_rad)
            k_geo = 1.5 * ((1 + cos_theta) / cos_theta) if cos_theta > 0.1 else 1.5 * 10
            
            bsa = f_iso + f_vol * k_vol + f_geo * k_geo
        
        return bsa, wsa
    
    def process_file(self, hdf_path: str, bands: List[int] = [1, 2, 6, 7],
                    solar_zenith: float = 0.0, output_prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Process a single MCD43A1 file and calculate albedo for specified bands
        
        Args:
            hdf_path: Path to MCD43A1 HDF file
            bands: List of MODIS bands to process
            solar_zenith: Solar zenith angle for BSA calculation
            output_prefix: Custom output filename prefix
            
        Returns:
            Dictionary mapping output types to file paths
        """
        hdf_path = Path(hdf_path)
        output_files = {}
        
        logger.info(f"Processing {hdf_path.name}")
        
        # Extract date and tile from filename
        filename_parts = hdf_path.stem.split('.')
        if len(filename_parts) >= 3:
            date_str = filename_parts[1]  # AYYDDD format
            tile = filename_parts[2]      # hXXvYY format
            
            if output_prefix is None:
                output_prefix = f"{date_str}_{tile}"
        else:
            output_prefix = hdf_path.stem
        
        # Process each band
        for band in bands:
            try:
                # Read BRDF parameters
                f_iso, profile = self.read_brdf_parameter(hdf_path, band, 'ISO')
                f_vol, _ = self.read_brdf_parameter(hdf_path, band, 'VOL')
                f_geo, _ = self.read_brdf_parameter(hdf_path, band, 'GEO')
                
                if f_iso is None or f_vol is None or f_geo is None:
                    logger.warning(f"Could not read BRDF parameters for band {band}")
                    continue
                
                # Calculate albedo
                bsa, wsa = self.calculate_albedo(f_iso, f_vol, f_geo, solar_zenith)
                
                # Save BSA
                bsa_path = self.output_dir / f"BSA_band{band}_{output_prefix}.tif"
                with rasterio.open(bsa_path, 'w', **profile) as dst:
                    dst.write(bsa, 1)
                    dst.set_band_description(1, f"BSA Band {band} ({self.band_info[band]['name']})")
                
                output_files[f'BSA_band{band}'] = str(bsa_path)
                
                # Save WSA
                wsa_path = self.output_dir / f"WSA_band{band}_{output_prefix}.tif"
                with rasterio.open(wsa_path, 'w', **profile) as dst:
                    dst.write(wsa, 1)
                    dst.set_band_description(1, f"WSA Band {band} ({self.band_info[band]['name']})")
                
                output_files[f'WSA_band{band}'] = str(wsa_path)
                
                logger.info(f"  Processed band {band} ({self.band_info[band]['name']})")
                
            except Exception as e:
                logger.error(f"Error processing band {band}: {e}")
                continue
        
        # Calculate broadband shortwave albedo if multiple bands processed
        if len([b for b in bands if b in self.shortwave_coeffs]) >= 3:
            try:
                bsa_sw, wsa_sw = self._calculate_shortwave_albedo(hdf_path, bands, solar_zenith)
                
                if bsa_sw is not None and wsa_sw is not None:
                    # Save shortwave BSA
                    bsa_sw_path = self.output_dir / f"BSA_shortwave_{output_prefix}.tif"
                    with rasterio.open(bsa_sw_path, 'w', **profile) as dst:
                        dst.write(bsa_sw, 1)
                        dst.set_band_description(1, "BSA Shortwave (0.3-3.0 μm)")
                    
                    output_files['BSA_shortwave'] = str(bsa_sw_path)
                    
                    # Save shortwave WSA
                    wsa_sw_path = self.output_dir / f"WSA_shortwave_{output_prefix}.tif"
                    with rasterio.open(wsa_sw_path, 'w', **profile) as dst:
                        dst.write(wsa_sw, 1)
                        dst.set_band_description(1, "WSA Shortwave (0.3-3.0 μm)")
                    
                    output_files['WSA_shortwave'] = str(wsa_sw_path)
                    
                    logger.info("  Calculated broadband shortwave albedo")
                    
            except Exception as e:
                logger.error(f"Error calculating shortwave albedo: {e}")
        
        return output_files
    
    def _calculate_shortwave_albedo(self, hdf_path: str, bands: List[int], 
                                  solar_zenith: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate broadband shortwave albedo using linear combination of bands
        """
        bsa_total = None
        wsa_total = None
        coeff_sum = 0
        
        for band in bands:
            if band not in self.shortwave_coeffs:
                continue
                
            # Read BRDF parameters
            f_iso, _ = self.read_brdf_parameter(hdf_path, band, 'ISO')
            f_vol, _ = self.read_brdf_parameter(hdf_path, band, 'VOL')
            f_geo, _ = self.read_brdf_parameter(hdf_path, band, 'GEO')
            
            if f_iso is None or f_vol is None or f_geo is None:
                continue
            
            # Calculate albedo for this band
            bsa, wsa = self.calculate_albedo(f_iso, f_vol, f_geo, solar_zenith)
            
            # Weight by coefficient
            coeff = self.shortwave_coeffs[band]
            
            if bsa_total is None:
                bsa_total = bsa * coeff
                wsa_total = wsa * coeff
            else:
                bsa_total += bsa * coeff
                wsa_total += wsa * coeff
            
            coeff_sum += coeff
        
        # Normalize if coefficients don't sum to 1
        if coeff_sum > 0 and coeff_sum != 1.0:
            bsa_total /= coeff_sum
            wsa_total /= coeff_sum
        
        return bsa_total, wsa_total
    
    def reproject_file(self, input_path: str, target_crs: str = 'EPSG:4326',
                      resampling_method: str = 'bilinear') -> str:
        """
        Reproject a processed albedo file to target CRS
        
        Args:
            input_path: Path to input GeoTIFF
            target_crs: Target coordinate reference system
            resampling_method: Resampling method for reprojection
            
        Returns:
            Path to reprojected file
        """
        input_path = Path(input_path)
        output_path = input_path.parent / f"{input_path.stem}_reprojected.tif"
        
        # Map string method to rasterio enum
        resampling_map = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'average': Resampling.average
        }
        resampling_enum = resampling_map.get(resampling_method, Resampling.bilinear)
        
        try:
            with rasterio.open(input_path) as src:
                # Calculate transform and dimensions for target CRS
                transform, width, height = calculate_default_transform(
                    src.crs, target_crs, src.width, src.height, *src.bounds
                )
                
                # Update profile
                profile = src.profile.copy()
                profile.update({
                    'crs': target_crs,
                    'transform': transform,
                    'width': width,
                    'height': height
                })
                
                # Reproject
                with rasterio.open(output_path, 'w', **profile) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=resampling_enum
                    )
            
            logger.info(f"Reprojected {input_path.name} to {target_crs}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error reprojecting {input_path}: {e}")
            return None
    
    def process_directory(self, input_dir: str, pattern: str = "MCD43A1.*.hdf",
                         bands: List[int] = [1, 2, 6, 7]) -> Dict[str, List[str]]:
        """
        Process all MCD43A1 files in a directory
        
        Args:
            input_dir: Input directory containing HDF files
            pattern: File pattern to match
            bands: List of bands to process
            
        Returns:
            Dictionary mapping file paths to output files
        """
        input_dir = Path(input_dir)
        results = {}
        
        # Find all matching files
        hdf_files = list(input_dir.rglob(pattern))
        
        if not hdf_files:
            logger.warning(f"No files matching pattern '{pattern}' found in {input_dir}")
            return results
        
        logger.info(f"Found {len(hdf_files)} files to process")
        
        for hdf_file in hdf_files:
            try:
                output_files = self.process_file(hdf_file, bands)
                results[str(hdf_file)] = output_files
                
            except Exception as e:
                logger.error(f"Error processing {hdf_file}: {e}")
                results[str(hdf_file)] = {}
        
        return results
    
    def create_summary_report(self, results: Dict[str, List[str]], 
                            output_path: Optional[str] = None) -> str:
        """
        Create a summary report of processing results
        """
        if output_path is None:
            output_path = self.output_dir / "processing_summary.json"
        
        summary = {
            'processing_date': datetime.now().isoformat(),
            'total_files_processed': len(results),
            'successful_files': len([r for r in results.values() if r]),
            'failed_files': len([r for r in results.values() if not r]),
            'output_directory': str(self.output_dir),
            'results': results
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary report saved to {output_path}")
        return str(output_path)


def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(description='MCD43A1 BRDF Parameter Processor')
    
    parser.add_argument('--input', nargs='+',
                       help='Input MCD43A1 HDF files or patterns')
    parser.add_argument('--input-dir', type=str,
                       help='Input directory containing HDF files')
    parser.add_argument('--output-dir', type=str, default='processed',
                       help='Output directory for processed files')
    parser.add_argument('--bands', nargs='+', type=int, default=[1, 2, 6, 7],
                       help='MODIS bands to process (1-7)')
    parser.add_argument('--solar-zenith', type=float, default=0.0,
                       help='Solar zenith angle for BSA calculation (degrees)')
    parser.add_argument('--reproject', type=str,
                       help='Reproject outputs to target CRS (e.g., EPSG:4326)')
    parser.add_argument('--process-all', action='store_true',
                       help='Process all HDF files in input directory')
    parser.add_argument('--summary-report', action='store_true',
                       help='Generate summary report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize processor
    processor = MCD43A1Processor(output_dir=args.output_dir)
    
    results = {}
    
    if args.process_all and args.input_dir:
        # Process all files in directory
        results = processor.process_directory(args.input_dir, bands=args.bands)
        
    elif args.input:
        # Process specific files
        for file_pattern in args.input:
            # Expand glob patterns
            files = glob.glob(file_pattern)
            if not files:
                logger.warning(f"No files found matching pattern: {file_pattern}")
                continue
                
            for file_path in files:
                try:
                    output_files = processor.process_file(file_path, bands=args.bands, 
                                                        solar_zenith=args.solar_zenith)
                    results[file_path] = output_files
                    
                    # Reproject if requested
                    if args.reproject:
                        for output_type, output_path in output_files.items():
                            reprojected = processor.reproject_file(output_path, args.reproject)
                            if reprojected:
                                logger.info(f"Reprojected {output_type} to {args.reproject}")
                                
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results[file_path] = {}
    else:
        parser.print_help()
        return
    
    # Generate summary report
    if args.summary_report and results:
        processor.create_summary_report(results)
    
    # Print summary
    total_outputs = sum(len(outputs) for outputs in results.values())
    successful_files = len([r for r in results.values() if r])
    
    logger.info(f"\nProcessing Summary:")
    logger.info(f"Files processed: {len(results)}")
    logger.info(f"Successful: {successful_files}")
    logger.info(f"Total outputs: {total_outputs}")
    logger.info(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()