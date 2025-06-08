"""
Data Processing & Configuration Dashboard
Complete interface for custom MODIS data processing with parameter control
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
import time

from src.config.processing_presets import (
    ANALYSIS_TYPES, QA_LEVELS, PROCESSING_PRESETS, 
    SPATIAL_RESOLUTIONS, TEMPORAL_RANGES, CUSTOM_QA_PRESETS,
    get_analysis_config, get_qa_config, get_preset_config, get_default_parameters
)
from src.utils.processing_manager import (
    ProcessingManager, load_csv_with_metadata, save_csv_with_metadata,
    get_processing_summary, validate_uploaded_csv
)


def create_processing_dashboard():
    """Main processing dashboard interface"""
    st.subheader("⚙️ Data Processing & Configuration")
    st.markdown("*Configure all parameters manually and generate custom datasets*")
    
    # Initialize session state
    if 'processing_manager' not in st.session_state:
        st.session_state.processing_manager = ProcessingManager()
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = None
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🎛️ Configure & Process", "📊 Results & Export", "📁 Import Data"])
    
    with tab1:
        create_configuration_interface()
    
    with tab2:
        create_results_interface()
    
    with tab3:
        create_import_interface()


def create_configuration_interface():
    """Configuration and processing interface"""
    st.markdown("### 🎛️ Analysis Configuration")
    
    # Check Earth Engine status (but don't display)
    from src.utils.ee_utils import initialize_earth_engine
    ee_available = initialize_earth_engine()
    
    # Main configuration section
    st.markdown("#### ⚙️ Configuration")
    
    # Analysis type selection
    analysis_options = list(ANALYSIS_TYPES.keys())
    analysis_labels = [ANALYSIS_TYPES[key]['name'] for key in analysis_options]
    
    selected_analysis = st.selectbox(
        "🔬 Analysis Type:",
        analysis_options,
        format_func=lambda x: ANALYSIS_TYPES[x]['name'],
        index=0,
        help="Select the type of MODIS analysis to perform"
    )
    
    # Show analysis description
    analysis_config = get_analysis_config(selected_analysis)
    st.info(f"📖 **{analysis_config['name']}**\n\n{analysis_config['description']}")
    
    # Parameter configuration based on analysis type
    parameters = configure_analysis_parameters(selected_analysis)
    
    # Processing controls
    st.markdown("---")
    st.markdown("#### 🚀 Processing Controls")
    
    # Validation
    from src.config.processing_presets import validate_parameters
    is_valid, errors = validate_parameters(selected_analysis, parameters)
    
    if not is_valid:
        st.error("❌ **Parameter Validation Errors:**")
        for error in errors:
            st.write(f"• {error}")
    
    # Show Earth Engine status if not available
    if not ee_available:
        st.error("🔴 Earth Engine is not available - processing will fail")
        st.info("Please check authentication and refresh the page")
    
    # Processing button
    col1, col2 = st.columns([2, 1])
    
    with col1:
        process_button = st.button(
            "🚀 Start Processing",
            type="primary",
            disabled=not is_valid or not ee_available,
            help="Run data extraction with current parameters"
        )
    
    with col2:
        if st.button("💾 Save Config", help="Save current configuration"):
            save_configuration(selected_analysis, parameters)
    
    # Processing execution
    if process_button:
        execute_processing(selected_analysis, parameters)


def configure_analysis_parameters(analysis_type):
    """Configure parameters for specific analysis type"""
    config = get_analysis_config(analysis_type)
    param_config = config.get('parameters', {})
    default_params = get_default_parameters(analysis_type)
    
    parameters = {}
    
    st.markdown("##### 📅 Temporal Settings")
    
    # Temporal range
    if 'start_year' in param_config and 'end_year' in param_config:
        temporal_col1, temporal_col2 = st.columns(2)
        
        with temporal_col1:
            parameters['start_year'] = st.number_input(
                "Start Year",
                min_value=param_config['start_year']['min'],
                max_value=param_config['start_year']['max'],
                value=default_params.get('start_year', param_config['start_year']['default']),
                help="First year to include in analysis"
            )
        
        with temporal_col2:
            parameters['end_year'] = st.number_input(
                "End Year",
                min_value=param_config['end_year']['min'],
                max_value=param_config['end_year']['max'],
                value=default_params.get('end_year', param_config['end_year']['default']),
                help="Last year to include in analysis"
            )
        
        # Show date range summary
        n_years = parameters['end_year'] - parameters['start_year'] + 1
        st.caption(f"📊 Analysis period: {n_years} years ({parameters['start_year']}-{parameters['end_year']})")
    
    # Spatial settings - Use fixed resolution of 500m
    if 'scale' in param_config:
        # Fixed scale of 500m - no user selection
        parameters['scale'] = 500
        st.caption("📏 Using standard MODIS resolution: 500m")
    
    # Quality settings (for analyses that support it)
    if 'use_advanced_qa' in param_config and 'qa_level' in param_config:
        st.markdown("##### 🔧 Quality Assessment Settings")
        
        # QA level selection
        qa_options = param_config['qa_level']['options']
        current_qa = default_params.get('qa_level', param_config['qa_level']['default'])
        qa_index = qa_options.index(current_qa) if current_qa in qa_options else 0
        
        parameters['qa_level'] = st.selectbox(
            "Quality Level",
            qa_options,
            index=qa_index,
            format_func=lambda x: f"{QA_LEVELS[x]['name']} - {QA_LEVELS[x]['expected_coverage']} coverage",
            help="Quality filtering strictness level"
        )
        
        # Advanced QA toggle
        current_advanced = default_params.get('use_advanced_qa', param_config['use_advanced_qa']['default'])
        parameters['use_advanced_qa'] = st.checkbox(
            "Use Advanced Algorithm QA Flags",
            value=current_advanced,
            help="Enable detailed algorithm quality flags filtering"
        )
        
        # Show QA level details
        qa_config = get_qa_config(parameters['qa_level'])
        
        # Handle custom QA level
        if parameters['qa_level'] == 'custom':
            st.markdown("##### 🎯 Custom QA Configuration")
            
            # Option to use preset or manual configuration
            custom_mode = st.radio(
                "Configuration Mode:",
                ["Use Preset", "Manual Configuration"],
                horizontal=True,
                help="Choose to use a preset or configure manually"
            )
            
            if custom_mode == "Use Preset":
                # Custom QA preset selection
                custom_preset_options = list(CUSTOM_QA_PRESETS.keys())
                
                selected_custom_preset = st.selectbox(
                    "Choose Custom QA Preset:",
                    custom_preset_options,
                    format_func=lambda x: CUSTOM_QA_PRESETS[x]['name'],
                    help="Select a predefined custom QA configuration"
                )
                
                # Get custom preset config
                custom_config = CUSTOM_QA_PRESETS[selected_custom_preset].copy()
                
                # Show preset info
                st.info(f"**{custom_config['name']}**: {custom_config['description']}")
                
            else:
                # Manual configuration
                st.markdown("##### 🔧 Manual QA Flag Configuration")
                
                # Basic QA threshold
                basic_qa_threshold = st.select_slider(
                    "Basic QA Threshold:",
                    options=[0, 1, 2],
                    value=1,
                    format_func=lambda x: {0: "0 - Best only", 1: "≤1 - Best + Good", 2: "≤2 - Best + Good + OK"}[x],
                    help="Basic quality threshold for pixel selection"
                )
                
                st.markdown("##### Algorithm Quality Flags")
                st.caption("Select which quality issues to filter out:")
                
                # Create columns for flags
                col1, col2 = st.columns(2)
                
                algorithm_flags = {}
                
                with col1:
                    algorithm_flags['no_inland_water'] = st.checkbox(
                        "🌊 Filter Inland Water",
                        value=True,
                        help="Remove pixels flagged as inland water"
                    )
                    
                    algorithm_flags['no_low_visible'] = st.checkbox(
                        "👁️ Filter Low Visible Reflectance",
                        value=True,
                        help="Remove pixels with low visible reflectance issues"
                    )
                    
                    algorithm_flags['no_low_ndsi'] = st.checkbox(
                        "❄️ Filter Low NDSI",
                        value=False,
                        help="Remove pixels with low snow index (often keep for glaciers)"
                    )
                
                with col2:
                    algorithm_flags['no_temp_issues'] = st.checkbox(
                        "🌡️ Filter Temperature Issues",
                        value=False,
                        help="Remove temperature flagged pixels (often keep for glaciers)"
                    )
                    
                    algorithm_flags['no_clouds'] = st.checkbox(
                        "☁️ Filter Clouds",
                        value=True,
                        help="Remove cloudy pixels"
                    )
                    
                    algorithm_flags['no_shadows'] = st.checkbox(
                        "🌑 Filter Shadows (Enhanced)",
                        value=False,
                        help="Apply enhanced shadow filtering"
                    )
                
                # Create custom config
                custom_config = {
                    "name": "Manual Configuration",
                    "description": "User-defined QA settings",
                    "basic_qa_threshold": basic_qa_threshold,
                    "algorithm_flags": algorithm_flags,
                    "expected_coverage": "Variable"
                }
            
            # Show current configuration summary
            with st.expander("📋 Current QA Configuration", expanded=True):
                st.markdown(f"**Basic QA Threshold:** ≤ {custom_config['basic_qa_threshold']}")
                st.markdown("**Algorithm Flags:**")
                
                active_flags = [flag for flag, enabled in custom_config['algorithm_flags'].items() if enabled]
                inactive_flags = [flag for flag, enabled in custom_config['algorithm_flags'].items() if not enabled]
                
                if active_flags:
                    st.markdown("✅ **Active Filters:**")
                    for flag in active_flags:
                        st.markdown(f"  • {flag.replace('no_', 'Filter ').replace('_', ' ').title()}")
                
                if inactive_flags:
                    st.markdown("❌ **Inactive Filters:**")
                    for flag in inactive_flags:
                        st.markdown(f"  • {flag.replace('no_', 'Filter ').replace('_', ' ').title()}")
                
                # Estimate coverage based on flags
                coverage_reduction = 1.0
                if custom_config['basic_qa_threshold'] == 0:
                    coverage_reduction *= 0.6
                elif custom_config['basic_qa_threshold'] == 1:
                    coverage_reduction *= 0.8
                
                for flag, enabled in custom_config['algorithm_flags'].items():
                    if enabled:
                        if flag == 'no_clouds':
                            coverage_reduction *= 0.85
                        elif flag == 'no_temp_issues':
                            coverage_reduction *= 0.9
                        elif flag == 'no_shadows':
                            coverage_reduction *= 0.95
                        else:
                            coverage_reduction *= 0.97
                
                estimated_coverage = int(coverage_reduction * 100)
                st.markdown(f"**Estimated Coverage:** ~{estimated_coverage-5}-{estimated_coverage+5}%")
            
            # Update parameters with custom config
            parameters['custom_qa_config'] = custom_config
            
        else:
            # Show standard QA level details
            with st.expander(f"ℹ️ {qa_config['name']} Details", expanded=False):
                st.markdown(f"**Description:** {qa_config['description']}")
                st.markdown(f"**Expected Coverage:** {qa_config['expected_coverage']}")
                st.markdown(f"**Recommended For:** {qa_config['recommended_for']}")
                
                if parameters['use_advanced_qa'] and qa_config.get('algorithm_flags'):
                    st.markdown("**Algorithm Flags:**")
                    for flag, enabled in qa_config['algorithm_flags'].items():
                        status = "✅" if enabled else "❌"
                        st.markdown(f"• {flag.replace('_', ' ').title()}: {status}")
    
    return parameters


def execute_processing(analysis_type, parameters):
    """Execute the processing workflow"""
    # Initialize progress tracking
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    completion_placeholder = st.empty()
    
    def update_progress(progress, message):
        progress_placeholder.progress(progress / 100)
        if progress < 100:
            status_placeholder.info(f"🔄 {message}")
        else:
            status_placeholder.success(f"✅ {message}")
    
    try:
        # Show initial status
        update_progress(0, "Initializing processing...")
        
        # Execute processing
        results = st.session_state.processing_manager.run_analysis(
            analysis_type, parameters, update_progress
        )
        
        # Check if processing succeeded or failed
        if isinstance(results, dict) and results.get('success') == False:
            # Processing failed but didn't crash the app
            progress_placeholder.empty()
            status_placeholder.error(f"❌ Processing failed: {results.get('error', 'Unknown error')}")
            
            st.error("🚨 **Processing Error**")
            st.write(f"**Error:** {results.get('error', 'Unknown error')}")
            
            # Show traceback if available (in expander for brevity)
            if results.get('traceback'):
                with st.expander("🔍 Technical Details (for debugging)", expanded=False):
                    st.code(results['traceback'], language='text')
            
            # Show troubleshooting tips
            with st.expander("🔧 Troubleshooting Tips", expanded=True):
                st.markdown("""
                **Common issues and solutions:**
                
                1. **Earth Engine Authentication Error**
                   - Check that Earth Engine is properly authenticated
                   - Try refreshing the page and reconnecting
                
                2. **Memory/Timeout Error**
                   - Try reducing the date range (fewer years)
                   - Use coarser spatial resolution (1000m instead of 500m)
                   - Use relaxed QA settings for faster processing
                
                3. **No Data Found**
                   - Check date range is within MODIS data availability (2000+)
                   - Try relaxed QA settings to increase data coverage
                   - Verify glacier boundary is correct
                
                4. **Parameter Validation Error**
                   - Check that start year ≤ end year
                   - Ensure all required parameters are set
                   - Verify parameter values are within valid ranges
                """)
            
            # Don't store failed results
            return
        
        # Store successful results
        st.session_state.processing_results = results
        
        # Keep the final success status visible
        # progress_placeholder shows 100%, status shows success message
        
        # Show completion summary
        completion_placeholder.success("🎉 **Processing Complete!**")
        
        # Show quick summary
        output_files = results.get('output_files', [])
        if output_files:
            st.write(f"📁 Generated {len(output_files)} output files:")
            for file_info in output_files:
                size_mb = file_info['size'] / (1024 * 1024)
                st.write(f"• {file_info['filename']} ({size_mb:.2f} MB)")
        
        # Switch to results tab
        st.info("💡 Check the **Results & Export** tab to download your data!")
        
    except Exception as e:
        # This should rarely happen now since we catch exceptions in the processing manager
        # But keep it as a final safety net
        progress_placeholder.empty()
        status_placeholder.error(f"❌ Unexpected error: {str(e)}")
        
        st.error("🚨 **Unexpected Error**")
        st.write(f"**Error:** {str(e)}")
        st.write("This error was not properly caught by the processing manager.")
        
        # Show full traceback for debugging
        import traceback
        with st.expander("🔍 Technical Details", expanded=False):
            st.code(traceback.format_exc(), language='text')
        
        # Show troubleshooting tips
        with st.expander("🔧 Troubleshooting Tips", expanded=True):
            st.markdown("""
            **Common issues and solutions:**
            
            1. **Earth Engine Authentication Error**
               - Check that Earth Engine is properly authenticated
               - Try refreshing the page and reconnecting
            
            2. **Memory/Timeout Error**
               - Try reducing the date range (fewer years)
               - Use coarser spatial resolution (1000m instead of 500m)
               - Use relaxed QA settings for faster processing
            
            3. **No Data Found**
               - Check date range is within MODIS data availability (2000+)
               - Try relaxed QA settings to increase data coverage
               - Verify glacier boundary is correct
            
            4. **Parameter Validation Error**
               - Check that start year ≤ end year
               - Ensure all required parameters are set
               - Verify parameter values are within valid ranges
            """)


def create_results_interface():
    """Results viewing and export interface"""
    st.markdown("### 📊 Processing Results")
    
    if not st.session_state.processing_results:
        st.info("🔄 No processing results available. Run an analysis in the 'Configure & Process' tab first.")
        return
    
    results = st.session_state.processing_results
    
    # Results summary
    st.markdown("#### 📋 Analysis Summary")
    
    summary_text = get_processing_summary(results)
    st.markdown(summary_text)
    
    # Output files
    output_files = results.get('output_files', [])
    if output_files:
        st.markdown("#### 📁 Generated Files")
        
        for i, file_info in enumerate(output_files):
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{file_info['filename']}**")
                    size_mb = file_info['size'] / (1024 * 1024)
                    st.caption(f"Size: {size_mb:.2f} MB | Modified: {file_info['modified'][:19]}")
                
                with col2:
                    # Preview button
                    if st.button(f"👁️ Preview", key=f"preview_{i}"):
                        preview_csv_file(file_info['path'])
                
                with col3:
                    # Download button
                    try:
                        with open(file_info['path'], 'rb') as f:
                            st.download_button(
                                label="📥 Download",
                                data=f.read(),
                                file_name=file_info['filename'],
                                mime="text/csv",
                                key=f"download_{i}"
                            )
                    except Exception as e:
                        st.error(f"Download error: {e}")
        
        # Bulk download option
        st.markdown("---")
        if st.button("📦 Download All Files as ZIP"):
            create_and_download_zip(output_files)
    
    # Metadata
    metadata = results.get('metadata', {})
    if metadata:
        st.markdown("#### 📊 Analysis Metadata")
        
        with st.expander("📋 View Detailed Metadata", expanded=False):
            st.json(metadata)


def create_import_interface():
    """CSV import and validation interface"""
    st.markdown("### 📁 Import Custom Data")
    st.markdown("*Upload CSV files to use in other analysis menus*")
    
    # File upload
    uploaded_file = st.file_uploader(
        "📤 Choose CSV file",
        type=['csv'],
        help="Upload a CSV file with MODIS albedo data"
    )
    
    if uploaded_file is not None:
        try:
            # Load the CSV
            df = pd.read_csv(uploaded_file)
            
            # Validate the CSV
            is_valid, errors, detected_type = validate_uploaded_csv(df)
            
            # Show validation results
            if is_valid:
                st.success(f"✅ **Valid {detected_type} data detected!**")
                st.write(f"📊 Shape: {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Show preview
                st.markdown("#### 👁️ Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Show data summary
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'date' in df.columns:
                        dates = pd.to_datetime(df['date'])
                        st.metric("Date Range", f"{dates.min().year}-{dates.max().year}")
                
                with col2:
                    if 'albedo_mean' in df.columns:
                        st.metric("Mean Albedo", f"{df['albedo_mean'].mean():.3f}")
                
                with col3:
                    st.metric("Observations", len(df))
                
                # Store in session state
                if st.button("💾 Import for Analysis"):
                    st.session_state.uploaded_data = {
                        'dataframe': df,
                        'type': detected_type,
                        'filename': uploaded_file.name,
                        'upload_timestamp': datetime.now().isoformat()
                    }
                    st.success("🎉 Data imported successfully! You can now use this data in other analysis menus.")
            
            else:
                st.error("❌ **CSV Validation Failed**")
                for error in errors:
                    st.write(f"• {error}")
                
                # Show what we found anyway
                st.markdown("#### 👁️ File Contents (for reference)")
                st.dataframe(df.head(), use_container_width=True)
        
        except Exception as e:
            st.error(f"❌ **Error reading CSV file:** {str(e)}")
    
    # Show current imported data
    if st.session_state.uploaded_data:
        st.markdown("---")
        st.markdown("#### 📊 Currently Imported Data")
        
        data_info = st.session_state.uploaded_data
        st.info(f"📁 **{data_info['filename']}** ({data_info['type']} data)")
        st.caption(f"Imported: {data_info['upload_timestamp'][:19]}")
        
        if st.button("🗑️ Clear Imported Data"):
            st.session_state.uploaded_data = None
            st.rerun()


def preview_csv_file(file_path):
    """Preview a CSV file"""
    try:
        df = pd.read_csv(file_path)
        
        st.markdown(f"#### 📋 Preview: {os.path.basename(file_path)}")
        
        # Basic info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            st.metric("Size", f"{file_size:.2f} MB")
        
        # Data preview
        st.dataframe(df.head(20), use_container_width=True)
        
        # Column info
        with st.expander("📊 Column Information", expanded=False):
            col_info = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                null_count = df[col].isnull().sum()
                col_info.append({
                    'Column': col,
                    'Type': dtype,
                    'Null Count': null_count,
                    'Null %': f"{(null_count/len(df)*100):.1f}%"
                })
            
            st.dataframe(pd.DataFrame(col_info), use_container_width=True)
        
    except Exception as e:
        st.error(f"Preview error: {e}")


def create_and_download_zip(file_list):
    """Create and download a ZIP file with all results"""
    import zipfile
    import io
    
    try:
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in file_list:
                zip_file.write(file_info['path'], file_info['filename'])
        
        # Download
        st.download_button(
            label="📦 Download ZIP Archive",
            data=zip_buffer.getvalue(),
            file_name=f"modis_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"ZIP creation error: {e}")


def save_configuration(analysis_type, parameters):
    """Save current configuration for future use"""
    config_data = {
        'analysis_type': analysis_type,
        'parameters': parameters,
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }
    
    # Save to session state
    if 'saved_configs' not in st.session_state:
        st.session_state.saved_configs = []
    
    config_name = f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config_data['name'] = config_name
    
    st.session_state.saved_configs.append(config_data)
    
    # Also save as JSON download
    config_json = json.dumps(config_data, indent=2)
    st.download_button(
        label="💾 Download Configuration",
        data=config_json,
        file_name=f"{config_name}.json",
        mime="application/json"
    )
    
    st.success(f"💾 Configuration saved as: {config_name}")