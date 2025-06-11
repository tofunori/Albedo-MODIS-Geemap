#!/usr/bin/env python3
"""
Setup script for Earthdata authentication
Creates .netrc file for NASA Earthdata access
"""

import os
import sys
from pathlib import Path
import getpass
import stat

def setup_netrc():
    """
    Setup .netrc file for NASA Earthdata authentication
    This is the most reliable method for LAADS DAAC access
    """
    print("Setting up NASA Earthdata authentication...")
    print("This will create/update your .netrc file for automatic authentication")
    print()
    
    # Get credentials
    username = input("NASA Earthdata username: ")
    password = getpass.getpass("NASA Earthdata password: ")
    
    if not username or not password:
        print("Error: Username and password are required")
        return False
    
    # Path to .netrc file
    netrc_path = Path.home() / '.netrc'
    
    # Prepare netrc entry
    netrc_entry = f"""
# NASA Earthdata Login
machine urs.earthdata.nasa.gov
    login {username}
    password {password}

# LAADS DAAC
machine ladsweb.modaps.eosdis.nasa.gov
    login {username}
    password {password}

# LP DAAC
machine e4ftl01.cr.usgs.gov
    login {username}
    password {password}
"""
    
    try:
        # Check if .netrc already exists
        if netrc_path.exists():
            print(f".netrc file already exists at {netrc_path}")
            response = input("Do you want to overwrite it? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled")
                return False
            
            # Backup existing file
            backup_path = netrc_path.with_suffix('.netrc.backup')
            netrc_path.rename(backup_path)
            print(f"Backup created: {backup_path}")
        
        # Write new .netrc file
        with open(netrc_path, 'w') as f:
            f.write(netrc_entry.strip())
        
        # Set correct permissions (600 - owner read/write only)
        os.chmod(netrc_path, stat.S_IRUSR | stat.S_IWUSR)
        
        print(f"✅ .netrc file created successfully at {netrc_path}")
        print("Authentication is now configured for NASA Earthdata services")
        
        return True
        
    except Exception as e:
        print(f"Error creating .netrc file: {e}")
        return False

def test_authentication():
    """
    Test authentication by trying to access NASA Earthdata
    """
    print("\nTesting authentication...")
    
    try:
        import requests
        
        # Test URL - this should redirect and require authentication
        test_url = "https://urs.earthdata.nasa.gov/profile"
        
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Authentication test successful")
            return True
        else:
            print(f"⚠️ Authentication test returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️ Could not test authentication: {e}")
        print("This doesn't necessarily mean authentication won't work")
        return None

def create_earthdata_config():
    """
    Create a JSON config file as alternative to .netrc
    """
    print("\nCreating JSON config file as alternative...")
    
    username = input("NASA Earthdata username: ")
    password = getpass.getpass("NASA Earthdata password: ")
    
    if not username or not password:
        print("Error: Username and password are required")
        return False
    
    config = {
        "username": username,
        "password": password,
        "note": "Alternative authentication method for MCD43A1 downloader"
    }
    
    config_path = Path("earthdata_credentials.json")
    
    try:
        import json
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
        
        print(f"✅ Config file created: {config_path}")
        print("⚠️ Keep this file secure and don't commit it to version control")
        
        return True
        
    except Exception as e:
        print(f"Error creating config file: {e}")
        return False

def main():
    """Main setup function"""
    print("NASA Earthdata Authentication Setup")
    print("=" * 40)
    print()
    print("This script will help you set up authentication for NASA Earthdata services")
    print("Required for downloading MODIS MCD43A1 data from LAADS DAAC")
    print()
    
    if not Path.home().exists():
        print("Error: Could not determine home directory")
        return
    
    print("Choose authentication method:")
    print("1. .netrc file (recommended)")
    print("2. JSON config file")
    print("3. Both")
    
    choice = input("\nChoice (1-3): ").strip()
    
    success = False
    
    if choice in ['1', '3']:
        print("\n--- Setting up .netrc authentication ---")
        success = setup_netrc()
        
        if success:
            test_result = test_authentication()
    
    if choice in ['2', '3']:
        print("\n--- Creating JSON config file ---")
        config_success = create_earthdata_config()
        success = success or config_success
    
    if success:
        print("\n✅ Authentication setup completed!")
        print("\nNext steps:")
        print("1. Test the downloader script:")
        print("   python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --list-only")
        print("2. Download some data:")
        print("   python mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03")
        print("3. Process the data:")
        print("   python mcd43a1_processor.py --input data/2024/243/*.hdf")
    else:
        print("\n❌ Setup failed. Please check your credentials and try again.")

if __name__ == "__main__":
    main()