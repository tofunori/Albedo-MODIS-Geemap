#!/usr/bin/env python3
"""
Test script pour vérifier que le système MCD43A1 fonctionne
Lance des tests sans authentification pour valider les scripts
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and show results"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"COMMAND: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"RETURN CODE: {result.returncode}")
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run system tests"""
    print("MCD43A1 System Test Suite")
    print("Vérification que tous les scripts fonctionnent correctement")
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    tests = []
    
    # Detect Python executable
    python_exe = sys.executable
    print(f"Using Python: {python_exe}")
    
    # Test 1: Downloader help
    tests.append((
        [python_exe, "mcd43a1_downloader.py", "--help"],
        "Downloader help message"
    ))
    
    # Test 2: Processor help
    tests.append((
        [python_exe, "mcd43a1_processor.py", "--help"],
        "Processor help message"
    ))
    
    # Test 3: List available files (no download)
    tests.append((
        [python_exe, "mcd43a1_downloader.py", 
         "--year", "2024", "--doy", "243", "--tiles", "h10v03", "--list-only"],
        "List available files (no authentication needed)"
    ))
    
    # Test 4: Check if GDAL tools are available
    tests.append((
        ["gdalinfo", "--version"],
        "GDAL availability check"
    ))
    
    # Test 5: Python imports test
    import_test_script = """
import sys
try:
    import numpy
    print("OK numpy available")
except ImportError as e:
    print(f"FAIL numpy missing: {e}")
    sys.exit(1)

try:
    import rasterio
    print("OK rasterio available")
except ImportError as e:
    print(f"FAIL rasterio missing: {e}")
    sys.exit(1)

try:
    import requests
    print("OK requests available")
except ImportError as e:
    print(f"FAIL requests missing: {e}")
    sys.exit(1)

print("OK All required Python packages available")
"""
    
    with open("temp_import_test.py", "w", encoding='utf-8') as f:
        f.write(import_test_script)
    
    tests.append((
        [python_exe, "temp_import_test.py"],
        "Python dependencies check"
    ))
    
    # Run all tests
    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Clean up
    if os.path.exists("temp_import_test.py"):
        os.remove("temp_import_test.py")
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = 0
    for description, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{status} {description}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\nSUCCESS: All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Set up NASA Earthdata authentication")
        print("2. Run: python3 mcd43a1_downloader.py --year 2024 --doy 243 --tiles h10v03 --max-files 1")
        print("3. Process: python3 mcd43a1_processor.py --input data/2024/243/*.hdf")
    else:
        print(f"\nWARNING: {len(results) - passed} tests failed. Check dependencies.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())