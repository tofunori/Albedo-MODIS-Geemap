#!/usr/bin/env python3
"""
MCD43A1 BRDF/Albedo Parameters Downloader and Processor
Handles downloading, processing, and calculating albedo from MODIS MCD43A1 data

Usage:
    python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 h09v03
    python mcd43a1_downloader.py --config config.json
"""

import os
import sys
import json
import argparse
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Tuple, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCD43A1Downloader:
    """
    MCD43A1 BRDF Parameters Downloader and Manager
    """
    
    def __init__(self, base_dir: str = "data", earthdata_config: Optional[str] = None):
        """
        Initialize the downloader
        
        Args:
            base_dir: Base directory for data storage
            earthdata_config: Path to Earthdata authentication config
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # LAADS DAAC base URL for MCD43A1 Collection 6.1
        self.base_url = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCD43A1"
        
        # Setup authentication
        self.earthdata_config = earthdata_config
        self._setup_authentication()
        
        # MODIS tile grid for reference
        self.tile_grid = self._load_tile_grid()
        
    def _setup_authentication(self):
        """Setup Earthdata authentication"""
        if self.earthdata_config and os.path.exists(self.earthdata_config):
            with open(self.earthdata_config, 'r') as f:
                config = json.load(f)
                self.username = config.get('username')
                self.password = config.get('password')
        else:
            # Check for .netrc file (curl -n option)
            netrc_path = Path.home() / '.netrc'
            if netrc_path.exists():
                logger.info("Using .netrc file for authentication")
                self.auth_method = 'netrc'
            else:
                logger.warning("No authentication configured. Please set up .netrc or provide earthdata config")
                self.auth_method = 'none'
    
    def _load_tile_grid(self) -> Dict[str, Dict]:
        """Load MODIS tile grid information"""
        # Simplified tile grid for common regions
        # For complete grid, see: https://modis-land.gsfc.nasa.gov/MODLAND_grid.html
        return {
            'h10v03': {'lat_center': 60.0, 'lon_center': -100.0, 'region': 'Canada_North'},
            'h09v03': {'lat_center': 60.0, 'lon_center': -110.0, 'region': 'Canada_NorthWest'},
            'h10v04': {'lat_center': 50.0, 'lon_center': -100.0, 'region': 'Canada_Central'},
            'h09v04': {'lat_center': 50.0, 'lon_center': -110.0, 'region': 'Canada_West'},
            'h11v03': {'lat_center': 60.0, 'lon_center': -90.0, 'region': 'Canada_Northeast'},
            'h11v04': {'lat_center': 50.0, 'lon_center': -90.0, 'region': 'Canada_East'},
        }
    
    def get_available_files(self, year: int, doy: int, tiles: List[str]) -> Dict[str, List[str]]:
        """
        Get list of available MCD43A1 files for given parameters
        
        Args:
            year: Year (e.g., 2024)
            doy: Day of year (1-366)
            tiles: List of MODIS tiles (e.g., ['h10v03', 'h09v03'])
            
        Returns:
            Dictionary mapping tile to list of available files
        """
        available_files = {}
        
        for tile in tiles:
            # Construct directory URL
            dir_url = f"{self.base_url}/{year}/{doy:03d}/"
            
            try:
                # Get directory listing
                response = requests.get(dir_url, timeout=30)
                if response.status_code == 200:
                    # Parse HTML to find .hdf files for this tile
                    import re
                    pattern = rf'(MCD43A1\.A{year}{doy:03d}\.{tile}\.061\.\d+\.hdf)'
                    matches = re.findall(pattern, response.text)
                    available_files[tile] = matches
                    logger.info(f"Found {len(matches)} files for tile {tile}")
                else:
                    logger.warning(f"Could not access directory for {year}/{doy:03d}")
                    available_files[tile] = []
                    
            except Exception as e:
                logger.error(f"Error checking availability for tile {tile}: {e}")
                available_files[tile] = []
        
        return available_files
    
    def download_file(self, year: int, doy: int, filename: str, 
                     output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download a specific MCD43A1 file
        
        Args:
            year: Year
            doy: Day of year
            filename: MCD43A1 filename
            output_dir: Output directory (defaults to base_dir/year/doy)
            
        Returns:
            Path to downloaded file or None if failed
        """
        if output_dir is None:
            output_dir = self.base_dir / str(year) / f"{doy:03d}"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        # Skip if file already exists
        if output_path.exists():
            logger.info(f"File already exists: {output_path}")
            return str(output_path)
        
        # Construct download URL
        download_url = f"{self.base_url}/{year}/{doy:03d}/{filename}"
        
        try:
            # Use curl with Bearer token (NASA Earthdata token)
            token = "eyJ0eXAiOiJKV1QiLCJvcmlnaW4iOiJFYXJ0aGRhdGEgTG9naW4iLCJzaWciOiJlZGxqd3RwdWJrZXlfb3BzIiwiYWxnIjoiUlMyNTYifQ.eyJ0eXBlIjoiVXNlciIsInVpZCI6InRvZnVub3JpIiwiZXhwIjoxNzU0Nzc3NDc3LCJpYXQiOjE3NDk1OTM0NzcsImlzcyI6Imh0dHBzOi8vdXJzLmVhcnRoZGF0YS5uYXNhLmdvdiIsImlkZW50aXR5X3Byb3ZpZGVyIjoiZWRsX29wcyIsImFjciI6ImVkbCIsImFzc3VyYW5jZV9sZXZlbCI6M30.pgidFr8TtaF1FXmwbIEaa1WIA_S_g0EtZh5--_pnzBigWGIsrIrmJM8Y7DdvwyXXmbA40Yp6m9tiWEDq0zLQSohKqy3PD37UGshqerAQFHe_1ce4RzLPk93rcQH8PzIhgIk1TLo953in5oDNhma1Y6cSSDf1kAJsu5PL8OYWKUfjFrPHRB5tYGp69IApe4-Ib97ixnPCQnS6I-zMjUu5TdaaJZCULRwsPNGg6jSpzTojWNn03_cce2bSH0oTdOqSAjddd4JoNodPE65SPSNRBIOYbl6pcM0Y_ZMuyiMEUh9eAV3DmaEDj-w6UbiDvTMshD1bihciM1WbO6Ime5hxyA"
            cmd = [
                'curl', '-H', f'Authorization: Bearer {token}', '-L', '-o', str(output_path),
                '--fail',  # Fail on HTTP errors
                '--silent', '--show-error',  # Less verbose but show errors
                '--connect-timeout', '30',
                '--max-time', '300',  # 5 minute timeout
                download_url
            ]
            
            logger.info(f"Downloading {filename}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully downloaded: {output_path}")
                return str(output_path)
            else:
                logger.error(f"Download failed: {result.stderr}")
                # Clean up partial file
                if output_path.exists():
                    output_path.unlink()
                return None
                
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            return None
    
    def download_batch(self, year: int, doy_range: Tuple[int, int], 
                      tiles: List[str], max_files: int = 50) -> Dict[str, List[str]]:
        """
        Download multiple files for a range of days
        
        Args:
            year: Year
            doy_range: Tuple of (start_doy, end_doy)
            tiles: List of tiles to download
            max_files: Maximum number of files to download
            
        Returns:
            Dictionary of successfully downloaded files by tile
        """
        downloaded_files = {tile: [] for tile in tiles}
        total_downloaded = 0
        
        start_doy, end_doy = doy_range
        
        for doy in range(start_doy, end_doy + 1):
            if total_downloaded >= max_files:
                logger.info(f"Reached maximum file limit ({max_files})")
                break
                
            logger.info(f"Processing DOY {doy:03d}/{year}")
            
            # Get available files for this day
            available = self.get_available_files(year, doy, tiles)
            
            for tile in tiles:
                if total_downloaded >= max_files:
                    break
                    
                for filename in available.get(tile, []):
                    if total_downloaded >= max_files:
                        break
                        
                    downloaded_path = self.download_file(year, doy, filename)
                    if downloaded_path:
                        downloaded_files[tile].append(downloaded_path)
                        total_downloaded += 1
        
        return downloaded_files
    
    def list_local_files(self, pattern: str = "**/*.hdf") -> List[str]:
        """
        List locally downloaded MCD43A1 files
        
        Args:
            pattern: Glob pattern for file search
            
        Returns:
            List of local file paths
        """
        return [str(p) for p in self.base_dir.glob(pattern)]
    
    def get_file_info(self, filepath: str) -> Dict:
        """
        Extract information from MCD43A1 filename
        
        Args:
            filepath: Path to MCD43A1 file
            
        Returns:
            Dictionary with file information
        """
        filename = Path(filepath).name
        
        # Parse MCD43A1.AYYDDD.hXXvYY.CCC.YYYYDDDHHMMSS.hdf
        pattern = r'MCD43A1\.A(\d{4})(\d{3})\.([hv]\d{2}[hv]\d{2})\.(\d{3})\.(\d{13})\.hdf'
        match = re.match(pattern, filename)
        
        if match:
            year = int(match.group(1))
            doy = int(match.group(2))
            tile = match.group(3)
            collection = match.group(4)
            timestamp = match.group(5)
            
            # Convert DOY to date
            date = datetime(year, 1, 1) + timedelta(days=doy - 1)
            
            return {
                'filename': filename,
                'filepath': filepath,
                'year': year,
                'doy': doy,
                'date': date.strftime('%Y-%m-%d'),
                'tile': tile,
                'collection': collection,
                'timestamp': timestamp,
                'region': self.tile_grid.get(tile, {}).get('region', 'Unknown')
            }
        else:
            return {'filename': filename, 'filepath': filepath, 'error': 'Invalid filename format'}


def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(description='MCD43A1 BRDF Parameters Downloader')
    
    parser.add_argument('--year', type=int, required=True,
                       help='Year to download (e.g., 2024)')
    parser.add_argument('--doy', type=int,
                       help='Specific day of year to download')
    parser.add_argument('--doy-range', nargs=2, type=int, metavar=('START', 'END'),
                       help='Range of days of year (e.g., 150 250)')
    parser.add_argument('--tiles', nargs='+', required=True,
                       help='MODIS tiles to download (e.g., h10v03 h09v03)')
    parser.add_argument('--output-dir', type=str, default='data',
                       help='Output directory for downloaded files')
    parser.add_argument('--max-files', type=int, default=50,
                       help='Maximum number of files to download')
    parser.add_argument('--list-only', action='store_true',
                       help='Only list available files, do not download')
    parser.add_argument('--earthdata-config', type=str,
                       help='Path to Earthdata authentication config JSON')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize downloader
    downloader = MCD43A1Downloader(
        base_dir=args.output_dir,
        earthdata_config=args.earthdata_config
    )
    
    # Determine DOY range
    if args.doy:
        doy_range = (args.doy, args.doy)
    elif args.doy_range:
        doy_range = tuple(args.doy_range)
    else:
        # Default to summer/melt season
        doy_range = (152, 273)  # June 1 - September 30
        logger.info(f"No DOY specified, using melt season: {doy_range}")
    
    # Check available files
    logger.info(f"Checking availability for {args.year}, DOY {doy_range[0]}-{doy_range[1]}, tiles: {args.tiles}")
    
    if args.list_only:
        # Just list available files
        for doy in range(doy_range[0], doy_range[1] + 1):
            available = downloader.get_available_files(args.year, doy, args.tiles)
            for tile, files in available.items():
                if files:
                    print(f"\nDOY {doy:03d}, Tile {tile}:")
                    for filename in files:
                        print(f"  {filename}")
    else:
        # Download files
        downloaded = downloader.download_batch(
            year=args.year,
            doy_range=doy_range,
            tiles=args.tiles,
            max_files=args.max_files
        )
        
        # Summary
        total_files = sum(len(files) for files in downloaded.values())
        logger.info(f"\nDownload Summary:")
        logger.info(f"Total files downloaded: {total_files}")
        for tile, files in downloaded.items():
            logger.info(f"  {tile}: {len(files)} files")


if __name__ == "__main__":
    main()