#!/usr/bin/env python3
"""
Test script to verify path resolution works correctly
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.file_utils import get_safe_output_path, safe_csv_write
import pandas as pd

def test_path_resolution():
    """Test that path resolution works correctly"""
    print("🧪 Testing path resolution...")
    
    # Test path resolution
    test_filename = "test_file.csv"
    safe_path = get_safe_output_path(test_filename)
    
    print(f"📁 Current working directory: {os.getcwd()}")
    print(f"📁 Script directory: {os.path.dirname(__file__)}")
    print(f"📁 Resolved path: {safe_path}")
    print(f"📁 Path exists: {os.path.exists(os.path.dirname(safe_path))}")
    
    # Test CSV writing
    print("\n🧪 Testing CSV writing...")
    test_df = pd.DataFrame({'test': [1, 2, 3], 'data': ['a', 'b', 'c']})
    
    if safe_csv_write(test_df, safe_path):
        print("✅ CSV write test successful!")
        print(f"📁 File created at: {safe_path}")
        print(f"📁 File exists: {os.path.exists(safe_path)}")
        
        # Clean up
        if os.path.exists(safe_path):
            os.remove(safe_path)
            print("🧹 Test file cleaned up")
    else:
        print("❌ CSV write test failed!")

if __name__ == "__main__":
    test_path_resolution()