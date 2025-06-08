"""
CSV Import Functionality for MOD10A1/MYD10A1 Analysis
Handles uploaded CSV files with validation and error handling
"""

import streamlit as st
import pandas as pd
import os
import glob


def create_csv_import_interface():
    """
    Create CSV import interface for MOD10A1 analysis
    Returns the loaded melt_data dictionary or None if no data loaded
    """
    st.markdown("### 📁 Data Source Options")
    
    data_source_option = st.radio(
        "Choose data source:",
        ["Use Default Data", "Import Processed CSV"],
        horizontal=True,
        help="Import your own processed MOD10A1 CSV files or use default data"
    )
    
    if data_source_option == "Import Processed CSV":
        return _handle_csv_import()
    else:
        return None


def _handle_csv_import():
    """Handle the CSV import process"""
    st.markdown("#### 📤 Import Your Processed MOD10A1 Data")
    st.markdown("*Upload your own melt season CSV files with QA settings*")
    
    # Try to show quick select for generated files
    melt_data = _show_quick_file_selector()
    if melt_data is not None:
        return melt_data
    
    # Show file upload interface
    return _show_file_upload_interface()


def _show_quick_file_selector():
    """Show quick selector for generated QA files"""
    try:
        # Look for generated QA files
        csv_pattern = os.path.join("outputs", "csv", "athabasca_melt_season_data_*.csv")
        qa_files = glob.glob(csv_pattern)
        
        if qa_files:
            st.markdown("##### 🚀 Quick Select Generated Files")
            qa_filenames = [os.path.basename(f) for f in qa_files]
            
            selected_file = st.selectbox(
                "Choose from your generated files:",
                [""] + qa_filenames,
                help="Select a previously generated file with QA settings"
            )
            
            if selected_file:
                return _load_quick_selected_file(selected_file)
            else:
                st.markdown("---")
                st.markdown("##### 📁 Or Upload Custom Files")
        
        return None
    except Exception:
        return None


def _load_quick_selected_file(selected_file):
    """Load a quick-selected file with validation"""
    try:
        file_path = os.path.join("outputs", "csv", selected_file)
        
        # Try multiple encodings for CSV reading
        quick_df = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                quick_df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if quick_df is None:
            st.error(f"Could not read {selected_file} with any encoding")
            return None
        
        # Show file info
        st.success(f"✅ Selected: {selected_file}")
        st.write(f"📋 **Shape**: {quick_df.shape[0]} rows, {quick_df.shape[1]} columns")
        st.write(f"🏷️ **Columns**: {list(quick_df.columns)}")
        
        # Show QA info if available
        if 'qa_description' in quick_df.columns:
            qa_info = quick_df['qa_description'].iloc[0]
            st.info(f"🔬 QA Settings: {qa_info}")
        
        # Validate the loaded data
        if not _validate_csv_data(quick_df):
            return None
        
        # Create melt_data structure
        melt_data = {
            'time_series': quick_df,
            'results': pd.DataFrame(),
            'focused': quick_df
        }
        
        # Try to load corresponding results file
        results_file = selected_file.replace('_data_', '_results_')
        results_path = os.path.join("outputs", "csv", results_file)
        if os.path.exists(results_path):
            try:
                results_df = pd.read_csv(results_path)
                melt_data['results'] = results_df
                st.success(f"✅ Also loaded results: {results_file}")
            except Exception as e:
                st.warning(f"Could not load results file: {e}")
        
        st.info("💡 Using selected generated file for analysis")
        return melt_data
        
    except Exception as e:
        st.error(f"Error loading selected file: {e}")
        st.write("Please try uploading the file manually or check file permissions")
        return None


def _show_file_upload_interface():
    """Show file upload interface"""
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_data_file = st.file_uploader(
            "📊 Data File (CSV)",
            type=['csv'],
            help="Upload your processed melt season data CSV",
            key="melt_data_upload"
        )
        
    with col2:
        uploaded_results_file = st.file_uploader(
            "📈 Results File (CSV)", 
            type=['csv'],
            help="Upload your melt season results CSV (optional)",
            key="melt_results_upload"
        )
    
    # Process uploaded files
    if uploaded_data_file is not None:
        return _process_uploaded_files(uploaded_data_file, uploaded_results_file)
    else:
        st.info("📁 Please upload a CSV file to proceed with custom data analysis")
        return None


def _process_uploaded_files(uploaded_data_file, uploaded_results_file):
    """Process uploaded CSV files with validation"""
    try:
        # Load the uploaded data with different encodings if needed
        uploaded_df = _load_csv_with_encoding(uploaded_data_file)
        if uploaded_df is None:
            return None
        
        # Show file info for debugging
        st.write(f"📋 **File Info**: {uploaded_data_file.name}")
        st.write(f"📊 **Shape**: {uploaded_df.shape[0]} rows, {uploaded_df.shape[1]} columns")
        st.write(f"🏷️ **Columns found**: {list(uploaded_df.columns)}")
        
        # Validate and fix column names
        uploaded_df = _validate_and_fix_columns(uploaded_df)
        if uploaded_df is None:
            return None
        
        # Success - prepare data for analysis
        st.success(f"✅ Data loaded successfully! {len(uploaded_df)} observations")
        
        # Show QA info if available
        if 'qa_description' in uploaded_df.columns:
            qa_info = uploaded_df['qa_description'].iloc[0] if not uploaded_df['qa_description'].empty else "Unknown"
            st.info(f"🔬 QA Settings: {qa_info}")
        
        # Load results if provided
        uploaded_results = None
        if uploaded_results_file is not None:
            try:
                uploaded_results = pd.read_csv(uploaded_results_file)
                st.success(f"✅ Results loaded! {len(uploaded_results)} trend analyses")
            except Exception as e:
                st.warning(f"⚠️ Could not load results file: {e}")
        
        # Prepare data structure to match expected format
        melt_data = {
            'time_series': uploaded_df,
            'results': uploaded_results if uploaded_results is not None else pd.DataFrame(),
            'focused': uploaded_df  # Use same data for focused analysis
        }
        
        st.info("💡 Using your uploaded data for analysis")
        return melt_data
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None


def _load_csv_with_encoding(uploaded_file):
    """Load CSV with multiple encoding attempts"""
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            return pd.read_csv(uploaded_file, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    
    st.error("Could not read the CSV file with any encoding")
    return None


def _validate_csv_data(df):
    """Validate CSV data for MOD10A1 analysis"""
    required_cols = ['date', 'albedo_mean']
    available_cols_lower = [col.lower().strip() for col in df.columns]
    
    missing_cols = []
    for req_col in required_cols:
        if req_col.lower() not in available_cols_lower:
            missing_cols.append(req_col)
    
    if missing_cols:
        st.error(f"❌ Generated file missing required columns: {missing_cols}")
        st.write("This file may not be compatible with MOD10A1 analysis")
        return False
    
    return True


def _validate_and_fix_columns(uploaded_df):
    """Validate and fix column names for compatibility"""
    required_cols = ['date', 'albedo_mean']
    available_cols = list(uploaded_df.columns)
    available_cols_lower = [col.lower().strip() for col in available_cols]
    
    # Create mapping of required columns to actual columns (case-insensitive)
    column_mapping = {}
    missing_cols = []
    
    for req_col in required_cols:
        found = False
        for i, avail_col_lower in enumerate(available_cols_lower):
            if req_col.lower() == avail_col_lower:
                column_mapping[req_col] = available_cols[i]
                found = True
                break
        
        if not found:
            # Try alternative column names
            alternatives = {
                'date': ['date_str', 'observation_date', 'time', 'datetime'],
                'albedo_mean': ['albedo', 'mean_albedo', 'albedo_avg', 'avg_albedo']
            }
            
            if req_col in alternatives:
                for alt_name in alternatives[req_col]:
                    for i, avail_col_lower in enumerate(available_cols_lower):
                        if alt_name.lower() == avail_col_lower:
                            column_mapping[req_col] = available_cols[i]
                            found = True
                            st.info(f"✅ Using '{available_cols[i]}' as '{req_col}' column")
                            break
                    if found:
                        break
        
        if not found:
            missing_cols.append(req_col)
    
    if missing_cols:
        st.error(f"❌ Missing required columns: {missing_cols}")
        st.write("**Required columns**: date, albedo_mean")
        st.write("**Available columns**: " + ", ".join(uploaded_df.columns))
        
        # Show helpful suggestions
        st.markdown("### 💡 Troubleshooting Tips:")
        st.write("1. Make sure your CSV has columns named 'date' and 'albedo_mean'")
        st.write("2. Check that the first row contains column headers")
        st.write("3. Alternative accepted column names:")
        st.write("   - For date: date_str, observation_date, time, datetime")
        st.write("   - For albedo: albedo, mean_albedo, albedo_avg, avg_albedo")
        st.write("4. Try using one of the generated QA-specific files:")
        st.code("athabasca_melt_season_data_advanced_standard.csv")
        return None
    
    # Rename columns to standard names if needed
    if column_mapping:
        rename_dict = {v: k for k, v in column_mapping.items() if k != v}
        if rename_dict:
            uploaded_df = uploaded_df.rename(columns=rename_dict)
            st.info(f"📝 Renamed columns: {rename_dict}")
    
    return uploaded_df