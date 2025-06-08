"""
CSV Manager
Handles import/export and integration of custom CSV data with analysis menus
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json


def get_uploaded_data():
    """Get currently uploaded data from session state"""
    return st.session_state.get('uploaded_data', None)


def has_uploaded_data(data_type=None):
    """Check if uploaded data is available"""
    uploaded_data = get_uploaded_data()
    if not uploaded_data:
        return False
    
    if data_type and uploaded_data.get('type') != data_type:
        return False
    
    return True


def load_uploaded_or_default_data(data_type, default_loader, show_status=True):
    """
    Load uploaded data if available, otherwise use default loader
    
    Args:
        data_type: Expected data type ('melt_season', 'mcd43a3', 'hypsometric')
        default_loader: Function to load default data
        show_status: Whether to show status messages
        
    Returns:
        DataFrame or dict with DataFrames
    """
    uploaded_data = get_uploaded_data()
    
    # Check if we have compatible uploaded data
    if uploaded_data and uploaded_data.get('type') == data_type:
        if show_status:
            st.info(f"📁 Using uploaded data: {uploaded_data['filename']}")
        
        df = uploaded_data['dataframe']
        
        # For melt_season, return dict structure to match expected format
        if data_type == 'melt_season':
            return {
                'time_series': df,
                'results': pd.DataFrame(),  # Empty results - will need to be generated
                'focused': df  # Use same data for focused analysis
            }
        else:
            return df
    
    else:
        # Use default loader
        if show_status and uploaded_data:
            st.warning(f"⚠️ Uploaded data is {uploaded_data.get('type', 'unknown')} type, but {data_type} is required. Using default data.")
        
        return default_loader(show_status=show_status)


def show_data_source_indicator():
    """Show indicator of current data source in sidebar"""
    uploaded_data = get_uploaded_data()
    
    if uploaded_data:
        with st.sidebar:
            st.markdown("---")
            st.markdown("#### 📊 Data Source")
            st.success(f"📁 Custom: {uploaded_data['filename']}")
            st.caption(f"Type: {uploaded_data['type']}")
            st.caption(f"Rows: {len(uploaded_data['dataframe'])}")
            
            if st.button("🔄 Switch to Default Data", help="Use default CSV data instead"):
                st.session_state.uploaded_data = None
                st.rerun()
    else:
        with st.sidebar:
            st.markdown("---")
            st.markdown("#### 📊 Data Source")
            st.info("📂 Default CSV data")
            
            if st.button("📁 Import Custom Data", help="Go to processing dashboard to import data"):
                st.info("💡 Use 'Data Processing & Configuration' menu to import custom CSV files")


def prepare_data_for_analysis(df, analysis_type):
    """
    Prepare uploaded data for specific analysis type
    
    Args:
        df: Raw DataFrame
        analysis_type: Type of analysis
        
    Returns:
        DataFrame prepared for analysis
    """
    df_clean = df.copy()
    
    # Ensure date column is datetime
    if 'date' in df_clean.columns:
        df_clean['date'] = pd.to_datetime(df_clean['date'])
    elif 'date_str' in df_clean.columns:
        df_clean['date'] = pd.to_datetime(df_clean['date_str'])
    
    # Sort by date
    if 'date' in df_clean.columns:
        df_clean = df_clean.sort_values('date').reset_index(drop=True)
    
    # Add derived columns based on analysis type
    if analysis_type == 'melt_season':
        # Add time-based columns if missing
        if 'date' in df_clean.columns and 'year' not in df_clean.columns:
            df_clean['year'] = df_clean['date'].dt.year
        if 'date' in df_clean.columns and 'month' not in df_clean.columns:
            df_clean['month'] = df_clean['date'].dt.month
        if 'date' in df_clean.columns and 'season' not in df_clean.columns:
            # Define seasons (focus on melt season: June-September)
            df_clean['season'] = df_clean['month'].apply(lambda x: 
                'Spring' if x in [3, 4, 5] else
                'Melt Season' if x in [6, 7, 8, 9] else
                'Fall' if x in [10, 11] else 'Winter'
            )
    
    elif analysis_type == 'mcd43a3':
        # Add day of year if missing
        if 'date' in df_clean.columns and 'doy' not in df_clean.columns:
            df_clean['doy'] = df_clean['date'].dt.dayofyear
    
    elif analysis_type == 'hypsometric':
        # Ensure elevation data is present
        if 'elevation' not in df_clean.columns:
            st.warning("⚠️ Elevation data not found in uploaded CSV. Hypsometric analysis may not work properly.")
    
    return df_clean


def export_analysis_results(results, analysis_type, custom_name=None):
    """
    Export analysis results as CSV with metadata
    
    Args:
        results: Analysis results (DataFrame or dict)
        analysis_type: Type of analysis
        custom_name: Custom filename (optional)
        
    Returns:
        Downloadable CSV content
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if custom_name:
        filename = f"{custom_name}_{timestamp}.csv"
    else:
        filename = f"custom_{analysis_type}_results_{timestamp}.csv"
    
    # Handle different result types
    if isinstance(results, dict):
        # Multiple DataFrames - create a summary export
        main_df = None
        
        if 'time_series' in results and not results['time_series'].empty:
            main_df = results['time_series']
        elif 'data' in results and not results['data'].empty:
            main_df = results['data']
        else:
            # Use first non-empty DataFrame
            for key, value in results.items():
                if isinstance(value, pd.DataFrame) and not value.empty:
                    main_df = value
                    break
        
        if main_df is not None:
            export_df = main_df
        else:
            st.error("No data available for export")
            return None, None
    
    elif isinstance(results, pd.DataFrame):
        export_df = results
    else:
        st.error("Invalid results format for export")
        return None, None
    
    # Add metadata as comments in CSV
    metadata = {
        'export_timestamp': timestamp,
        'analysis_type': analysis_type,
        'data_source': 'custom_processing',
        'rows': len(export_df),
        'columns': len(export_df.columns)
    }
    
    # Create CSV content
    csv_content = export_df.to_csv(index=False)
    
    # Add metadata header
    metadata_header = f"# Analysis Results Export\n"
    metadata_header += f"# Type: {analysis_type}\n"
    metadata_header += f"# Generated: {timestamp}\n"
    metadata_header += f"# Rows: {len(export_df)}, Columns: {len(export_df.columns)}\n"
    metadata_header += "#\n"
    
    final_content = metadata_header + csv_content
    
    return final_content, filename


def validate_data_compatibility(df, analysis_type):
    """
    Validate that uploaded data is compatible with specific analysis type
    
    Args:
        df: DataFrame to validate
        analysis_type: Target analysis type
        
    Returns:
        tuple: (is_compatible, warnings, suggestions)
    """
    warnings = []
    suggestions = []
    is_compatible = True
    
    # Common requirements
    if 'date' not in df.columns and 'date_str' not in df.columns:
        warnings.append("No date column found")
        suggestions.append("Add a 'date' or 'date_str' column")
        is_compatible = False
    
    if 'albedo_mean' not in df.columns:
        warnings.append("No 'albedo_mean' column found")
        suggestions.append("Add an 'albedo_mean' column with albedo values")
        is_compatible = False
    
    # Type-specific requirements
    if analysis_type == 'mcd43a3':
        spectral_cols = ['Albedo_BSA_vis', 'Albedo_BSA_nir', 'Albedo_BSA_shortwave']
        missing_spectral = [col for col in spectral_cols if col not in df.columns]
        
        if missing_spectral:
            warnings.append(f"Missing MCD43A3 spectral columns: {missing_spectral}")
            suggestions.append("Ensure MCD43A3 spectral bands are included")
    
    elif analysis_type == 'hypsometric':
        if 'elevation' not in df.columns:
            warnings.append("No elevation data found")
            suggestions.append("Add 'elevation' column for hypsometric analysis")
    
    # Data quality checks
    if 'albedo_mean' in df.columns:
        albedo_values = df['albedo_mean'].dropna()
        if not albedo_values.empty:
            if albedo_values.min() < 0 or albedo_values.max() > 1:
                warnings.append("Albedo values outside valid range (0-1)")
                suggestions.append("Check albedo values are properly scaled")
    
    # Date range check
    if 'date' in df.columns or 'date_str' in df.columns:
        try:
            date_col = 'date' if 'date' in df.columns else 'date_str'
            dates = pd.to_datetime(df[date_col])
            date_range = dates.max() - dates.min()
            
            if date_range.days < 30:
                warnings.append("Very short time series (< 30 days)")
                suggestions.append("Consider longer time series for better trend analysis")
        except:
            warnings.append("Could not parse dates")
            suggestions.append("Ensure dates are in YYYY-MM-DD format")
    
    return is_compatible, warnings, suggestions


def create_data_summary_widget(df, data_type=None):
    """Create a summary widget for uploaded data"""
    if df is None or df.empty:
        st.warning("No data available")
        return
    
    st.markdown("#### 📊 Data Summary")
    
    # Basic metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Rows", len(df))
    
    with col2:
        st.metric("Columns", len(df.columns))
    
    with col3:
        if 'date' in df.columns:
            try:
                dates = pd.to_datetime(df['date'])
                years = dates.max().year - dates.min().year + 1
                st.metric("Years", years)
            except:
                st.metric("Years", "Unknown")
        else:
            st.metric("Years", "No dates")
    
    with col4:
        if 'albedo_mean' in df.columns:
            mean_albedo = df['albedo_mean'].mean()
            st.metric("Mean Albedo", f"{mean_albedo:.3f}")
        else:
            st.metric("Mean Albedo", "N/A")
    
    # Data quality indicators
    if 'albedo_mean' in df.columns:
        missing_albedo = df['albedo_mean'].isnull().sum()
        missing_pct = (missing_albedo / len(df)) * 100
        
        if missing_pct > 0:
            st.warning(f"⚠️ {missing_albedo} missing albedo values ({missing_pct:.1f}%)")
    
    # Quick data preview
    with st.expander("👁️ Data Preview", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)