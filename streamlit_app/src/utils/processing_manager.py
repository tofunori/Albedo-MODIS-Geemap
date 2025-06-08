"""
Processing Manager
Handles execution of MODIS data processing workflows with custom parameters
"""

import streamlit as st
import pandas as pd
import sys
import os
import importlib
from datetime import datetime
import json
import traceback

# Add parent directories to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'src'))

from src.config.processing_presets import get_analysis_config, validate_parameters


class ProcessingManager:
    """Manages MODIS data processing workflows"""
    
    def __init__(self):
        self.processing_status = {
            'running': False,
            'progress': 0,
            'current_step': '',
            'error': None,
            'results': None
        }
    
    def run_analysis(self, analysis_type, parameters, progress_callback=None):
        """
        Run analysis with custom parameters
        
        Args:
            analysis_type: Type of analysis to run
            parameters: Dictionary of parameters
            progress_callback: Function to call with progress updates
            
        Returns:
            dict: Results including output files and metadata
        """
        try:
            # Reset status
            self.processing_status = {
                'running': True,
                'progress': 0,
                'current_step': 'Initializing...',
                'error': None,
                'results': None
            }
            
            if progress_callback:
                progress_callback(0, "Initializing processing...")
            
            # Validate parameters
            valid, errors = validate_parameters(analysis_type, parameters)
            if not valid:
                raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")
            
            # Get analysis configuration
            config = get_analysis_config(analysis_type)
            if not config:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            if progress_callback:
                progress_callback(10, "Loading workflow module...")
            
            # Import and execute workflow
            workflow_module = config['workflow_module']
            workflow_function = config['workflow_function']
            
            # Dynamic import of the workflow module
            try:
                module = importlib.import_module(workflow_module)
                func = getattr(module, workflow_function)
            except ImportError as e:
                raise ImportError(f"Could not import {workflow_module}: {e}")
            except AttributeError as e:
                raise AttributeError(f"Function {workflow_function} not found in {workflow_module}: {e}")
            
            if progress_callback:
                progress_callback(20, "Starting data extraction...")
            
            # Handle custom QA config if present
            if 'custom_qa_config' in parameters and parameters.get('qa_level') == 'custom':
                # Extract custom QA settings
                custom_config = parameters.pop('custom_qa_config')
                
                # Apply custom QA settings to parameters
                parameters['use_advanced_qa'] = True
                parameters['qa_level'] = 'custom'
                
                # Pass custom config as additional parameter if workflow supports it
                # For now, we'll use the closest standard QA level
                # In the future, workflows can be updated to accept custom configs
                if custom_config['basic_qa_threshold'] == 0:
                    parameters['qa_level'] = 'strict'
                elif custom_config['basic_qa_threshold'] == 2:
                    parameters['qa_level'] = 'relaxed'
                else:
                    parameters['qa_level'] = 'standard'
            
            # Execute the workflow with parameters
            try:
                # Check if the workflow function accepts a progress_callback parameter
                import inspect
                func_signature = inspect.signature(func)
                
                if 'progress_callback' in func_signature.parameters:
                    # Pass the progress callback to the workflow
                    results = func(progress_callback=progress_callback, **parameters)
                else:
                    # Workflow doesn't support progress callback
                    results = func(**parameters)
            except Exception as e:
                # Capture full traceback for debugging
                import traceback
                full_traceback = traceback.format_exc()
                
                # Log the error but don't let it crash the app
                error_msg = f"Workflow execution failed: {str(e)}"
                print(f"❌ {error_msg}")
                print(f"📋 Full traceback:\n{full_traceback}")
                
                # Return error information instead of raising
                return {
                    'success': False,
                    'error': error_msg,
                    'traceback': full_traceback,
                    'analysis_type': analysis_type,
                    'parameters': parameters
                }
            
            if progress_callback:
                progress_callback(90, "Finalizing results...")
            
            # Check if results contain an error
            if isinstance(results, dict) and results.get('success') == False:
                # Processing failed but didn't crash - return the error info
                self.processing_status.update({
                    'running': False,
                    'error': results.get('error', 'Unknown error'),
                    'current_step': 'Failed'
                })
                return results
            
            # Process results and add metadata
            processed_results = self._process_results(
                results, analysis_type, parameters, config
            )
            
            if progress_callback:
                progress_callback(100, "Processing complete!")
            
            self.processing_status.update({
                'running': False,
                'progress': 100,
                'current_step': 'Complete',
                'results': processed_results
            })
            
            return processed_results
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            
            # Capture full traceback for debugging
            import traceback
            full_traceback = traceback.format_exc()
            
            self.processing_status.update({
                'running': False,
                'error': error_msg,
                'current_step': 'Failed'
            })
            
            if progress_callback:
                progress_callback(0, f"Error: {error_msg}")
            
            # Return error information instead of raising
            return {
                'success': False,
                'error': error_msg,
                'traceback': full_traceback,
                'analysis_type': analysis_type,
                'parameters': parameters
            }
    
    def _process_results(self, results, analysis_type, parameters, config):
        """Process and enhance results with metadata"""
        processed = {
            'analysis_type': analysis_type,
            'parameters': parameters,
            'config': config,
            'processing_timestamp': datetime.now().isoformat(),
            'workflow_results': results,
            'output_files': [],
            'metadata': {}
        }
        
        # Add expected output files (including QA-specific files)
        expected_files = config.get('output_files', [])
        
        # Find project root by going up from current location
        current_dir = os.path.abspath(os.path.dirname(__file__))
        project_root = current_dir
        
        # Go up until we find the project root (contains outputs folder)
        max_levels = 10
        for level in range(max_levels):
            if os.path.exists(os.path.join(project_root, 'outputs', 'csv')):
                break
            project_root = os.path.dirname(project_root)
        
        csv_dir = os.path.join(project_root, 'outputs', 'csv')
        
        # For each expected file, look for QA-specific versions
        for filename in expected_files:
            try:
                # First try to find QA-specific files
                import glob
                base_name = filename.replace('.csv', '')
                qa_pattern = os.path.join(csv_dir, f"{base_name}_*.csv")
                qa_files = glob.glob(qa_pattern)
                
                if qa_files:
                    # Use the most recent QA file
                    most_recent = max(qa_files, key=os.path.getmtime)
                    file_path = most_recent
                else:
                    # Fall back to original filename
                    file_path = os.path.normpath(os.path.join(csv_dir, filename))
                
                if os.path.exists(file_path):
                    try:
                        # Try to get file info safely
                        file_size = os.path.getsize(file_path)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        
                        processed['output_files'].append({
                            'filename': filename,
                            'path': file_path,
                            'size': file_size,
                            'modified': file_mtime
                        })
                    except (OSError, PermissionError) as e:
                        # Skip files that can't be accessed
                        st.warning(f"Could not access file {filename}: {e}")
                        continue
                else:
                    st.info(f"Expected output file not found: {filename}")
                    
            except Exception as e:
                st.warning(f"Could not resolve path for {filename}: {e}")
                continue
        
        # Add analysis metadata
        if results and isinstance(results, dict):
            if 'dataset_info' in results:
                processed['metadata']['dataset_info'] = results['dataset_info']
            if 'processing_info' in results:
                processed['metadata']['processing_info'] = results['processing_info']
        
        return processed
    
    def get_status(self):
        """Get current processing status"""
        return self.processing_status.copy()
    
    def is_running(self):
        """Check if processing is currently running"""
        return self.processing_status.get('running', False)


def load_csv_with_metadata(file_path):
    """
    Load CSV file and extract processing metadata if available
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        tuple: (DataFrame, metadata_dict)
    """
    try:
        # Try to read the CSV
        df = pd.read_csv(file_path)
        
        # Look for metadata file
        metadata_path = file_path.replace('.csv', '_metadata.json')
        metadata = {}
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except:
                pass
        
        # Try to infer metadata from filename and content
        if not metadata:
            metadata = _infer_metadata_from_csv(file_path, df)
        
        return df, metadata
        
    except Exception as e:
        raise ValueError(f"Failed to load CSV: {e}")


def save_csv_with_metadata(df, file_path, metadata):
    """
    Save CSV file with associated metadata
    
    Args:
        df: DataFrame to save
        file_path: Path for CSV file
        metadata: Metadata dictionary
    """
    import time
    import tempfile
    
    try:
        # Use normalized path
        file_path = os.path.normpath(file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Try to save CSV with retry mechanism for Windows file locking
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Save to temporary file first, then move
                temp_file = file_path + '.tmp'
                df.to_csv(temp_file, index=False)
                
                # On Windows, need to handle file replacement carefully
                if os.path.exists(file_path):
                    backup_file = file_path + '.bak'
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(file_path, backup_file)
                
                os.rename(temp_file, file_path)
                
                # Clean up backup
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                break
                
            except (PermissionError, OSError) as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Wait before retry
                    continue
                else:
                    raise e
        
        # Save metadata
        metadata_path = file_path.replace('.csv', '_metadata.json')
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Metadata save failure shouldn't break the main save
            pass
            
    except Exception as e:
        raise ValueError(f"Failed to save CSV with metadata: {e}")


def _infer_metadata_from_csv(file_path, df):
    """Infer metadata from CSV filename and content"""
    filename = os.path.basename(file_path)
    metadata = {
        'filename': filename,
        'inferred': True,
        'shape': df.shape,
        'columns': list(df.columns)
    }
    
    # Infer analysis type from filename
    if 'melt_season' in filename:
        metadata['analysis_type'] = 'melt_season'
    elif 'mcd43a3' in filename:
        metadata['analysis_type'] = 'mcd43a3'
    elif 'hypsometric' in filename:
        metadata['analysis_type'] = 'hypsometric'
    
    # Infer date range if date column exists
    date_columns = [col for col in df.columns if 'date' in col.lower()]
    if date_columns and not df.empty:
        try:
            dates = pd.to_datetime(df[date_columns[0]])
            metadata['date_range'] = {
                'start': dates.min().strftime('%Y-%m-%d'),
                'end': dates.max().strftime('%Y-%m-%d')
            }
        except:
            pass
    
    return metadata


def get_processing_summary(results):
    """Generate a summary of processing results"""
    if not results:
        return "No results available"
    
    summary = []
    
    # Basic info
    analysis_type = results.get('analysis_type', 'Unknown')
    summary.append(f"**Analysis Type:** {analysis_type}")
    
    # Parameters
    parameters = results.get('parameters', {})
    if parameters:
        summary.append("**Parameters:**")
        for key, value in parameters.items():
            summary.append(f"  • {key}: {value}")
    
    # Output files
    output_files = results.get('output_files', [])
    if output_files:
        summary.append("**Generated Files:**")
        for file_info in output_files:
            size_mb = file_info['size'] / (1024 * 1024)
            summary.append(f"  • {file_info['filename']} ({size_mb:.2f} MB)")
    
    # Metadata
    metadata = results.get('metadata', {})
    if 'dataset_info' in metadata:
        dataset_info = metadata['dataset_info']
        summary.append("**Dataset Info:**")
        for key, value in dataset_info.items():
            summary.append(f"  • {key}: {value}")
    
    return "\n".join(summary)


def validate_uploaded_csv(df, expected_analysis_type=None):
    """
    Validate uploaded CSV for compatibility with analysis menus
    
    Args:
        df: Uploaded DataFrame
        expected_analysis_type: Expected analysis type (optional)
        
    Returns:
        tuple: (is_valid, error_messages, detected_type)
    """
    errors = []
    detected_type = None
    
    if df.empty:
        errors.append("CSV file is empty")
        return False, errors, None
    
    # Check for required columns based on analysis type
    if 'albedo_mean' in df.columns and 'date' in df.columns:
        if 'elevation' in df.columns:
            detected_type = 'hypsometric'
            required_cols = ['date', 'albedo_mean', 'elevation']
        elif any('Band' in col for col in df.columns):
            detected_type = 'mcd43a3'
            required_cols = ['date', 'Albedo_BSA_vis', 'Albedo_BSA_nir']
        else:
            detected_type = 'melt_season'
            required_cols = ['date', 'albedo_mean']
    else:
        errors.append("CSV must contain at least 'date' and 'albedo_mean' columns")
        return False, errors, None
    
    # Check for required columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
    
    # Validate date column
    try:
        pd.to_datetime(df['date'])
    except:
        errors.append("'date' column contains invalid dates")
    
    # Validate albedo values
    if 'albedo_mean' in df.columns:
        albedo_values = df['albedo_mean'].dropna()
        if not albedo_values.empty:
            if albedo_values.min() < 0 or albedo_values.max() > 1:
                errors.append("Albedo values must be between 0 and 1")
    
    # Check expected type
    if expected_analysis_type and detected_type != expected_analysis_type:
        errors.append(f"CSV appears to be {detected_type} data, expected {expected_analysis_type}")
    
    return len(errors) == 0, errors, detected_type