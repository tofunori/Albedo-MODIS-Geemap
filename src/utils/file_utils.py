"""
File Utilities for Safe File Operations
Handles cross-platform file operations with proper locking and error handling
"""

import os
import time
import tempfile
import pandas as pd


def safe_csv_write(df, file_path, index=False, max_retries=3, retry_delay=0.5, timeout_seconds=60):
    """
    Safely write a DataFrame to CSV with retry mechanism and timeout
    
    Args:
        df: DataFrame to save
        file_path: Path where to save the CSV
        index: Whether to include DataFrame index
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        timeout_seconds: Timeout for CSV write operation
        
    Returns:
        bool: True if successful, False otherwise
    """
    import signal
    import threading
    
    def csv_write_with_timeout():
        """Inner function to write CSV"""
        try:
            # Use normalized path for cross-platform compatibility
            file_path_norm = os.path.normpath(file_path)
            # Ensure directory exists
            dir_path = os.path.dirname(file_path_norm)
            os.makedirs(dir_path, exist_ok=True)
            
            print(f"🔍 Writing {len(df)} rows, {len(df.columns)} columns")
            
            # Try to save CSV with retry mechanism for Windows file locking
            for attempt in range(max_retries):
                try:
                    # Save to temporary file first, then move atomically
                    temp_file = file_path_norm + '.tmp'
                    print(f"🔍 Attempt {attempt + 1}: Writing to {temp_file}")
                    
                    # Write CSV with explicit encoding to avoid issues
                    # Use original pandas method to avoid any monkey-patching recursion
                    import pandas as pd
                    original_to_csv = pd.DataFrame.to_csv
                    original_to_csv(df, temp_file, index=index, encoding='utf-8')
                    print(f"🔍 Successfully wrote temp file")
                    
                    # On Windows, need to handle file replacement carefully
                    if os.path.exists(file_path_norm):
                        backup_file = file_path_norm + '.bak'
                        # Remove old backup if it exists
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        # Move current file to backup
                        os.rename(file_path_norm, backup_file)
                    
                    # Move temp file to final location
                    os.rename(temp_file, file_path_norm)
                    print(f"🔍 Successfully moved to final location")
                    
                    # Clean up backup file
                    backup_file = file_path_norm + '.bak'
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    
                    return True
                    
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️  CSV write attempt {attempt + 1} failed: {e}")
                        print(f"🔄 Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"❌ Failed to write CSV after {max_retries} attempts: {e}")
                        raise e
            
            return False
            
        except Exception as e:
            print(f"❌ Critical error writing CSV {file_path}: {e}")
            print(f"❌ Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    # Execute with timeout using threading
    result = [False]  # Mutable container for thread result
    exception = [None]
    
    def target():
        try:
            result[0] = csv_write_with_timeout()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        print(f"❌ CSV write timed out after {timeout_seconds} seconds!")
        print("🔍 This suggests a system-level hang - trying alternative approach...")
        
        # Try a simpler approach
        try:
            import pandas as pd
            original_to_csv = pd.DataFrame.to_csv
            simple_path = file_path + '.simple'
            original_to_csv(df, simple_path, index=index)
            print(f"✅ Simple CSV write succeeded: {simple_path}")
            return True
        except Exception as e:
            print(f"❌ Even simple CSV write failed: {e}")
            return False
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def check_file_lock(file_path):
    """
    Check if a file is locked (being used by another process)
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if file is locked, False if available
    """
    if not os.path.exists(file_path):
        return False
        
    try:
        # Try to open the file in append mode to check if it's locked
        with open(file_path, 'a'):
            pass
        return False
    except (PermissionError, OSError):
        return True


def get_safe_output_path(filename, base_dir=None):
    """
    Get a safe output path, creating unique filename if file is locked
    
    Args:
        filename: Desired filename
        base_dir: Base directory (optional)
        
    Returns:
        str: Safe file path to use
    """
    if base_dir is None:
        # Find the project root directory by looking for key files
        current_dir = os.path.abspath(os.path.dirname(__file__))
        project_root = current_dir
        
        # Go up directories until we find the project root (contains 'outputs' folder)
        max_levels = 10  # Safety limit
        level = 0
        while project_root != os.path.dirname(project_root) and level < max_levels:
            if os.path.exists(os.path.join(project_root, 'outputs', 'csv')):
                break
            project_root = os.path.dirname(project_root)
            level += 1
        
        if level >= max_levels:
            # Fallback: use a fixed path based on known structure
            # Assuming we're in src/utils, go up to project root
            fallback_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
            project_root = fallback_root
        
        # Create outputs/csv path
        csv_dir = os.path.join(project_root, 'outputs', 'csv')
        os.makedirs(csv_dir, exist_ok=True)
        file_path = os.path.join(csv_dir, filename)
    else:
        file_path = os.path.join(base_dir, filename)
    
    # Normalize the path for cross-platform compatibility
    file_path = os.path.normpath(file_path)
    
    # If file is locked, create a unique name
    if check_file_lock(file_path):
        base, ext = os.path.splitext(file_path)
        timestamp = int(time.time())
        file_path = f"{base}_{timestamp}{ext}"
    
    return file_path


def cleanup_temp_files(directory, pattern="*.tmp"):
    """
    Clean up temporary files from a directory
    
    Args:
        directory: Directory to clean
        pattern: File pattern to match
    """
    import glob
    
    temp_files = glob.glob(os.path.join(directory, pattern))
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
            print(f"🧹 Cleaned up temp file: {os.path.basename(temp_file)}")
        except:
            pass