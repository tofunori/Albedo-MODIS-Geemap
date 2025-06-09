"""
Streamlit Main Dashboard for Athabasca Glacier Albedo Analysis
Modular and organized main entry point for the web application
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Import our modular components with better path handling
import sys
import os

# Add current directory and src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

# Import dashboard modules
from src.utils.data_loader import (
    load_all_melt_season_data, 
    load_hypsometric_data,
    get_data_source_info
)
from src.dashboards.mcd43a3_dashboard import create_mcd43a3_dashboard
from src.dashboards.melt_season_dashboard import create_melt_season_dashboard
from src.dashboards.statistical_analysis_dashboard import create_statistical_analysis_dashboard
from src.dashboards.realtime_qa_dashboard import create_realtime_qa_dashboard
from src.dashboards.interactive_data_dashboard import create_interactive_data_table_dashboard
from src.dashboards.interactive_albedo_dashboard import create_interactive_albedo_dashboard
from src.utils.csv_import import create_csv_import_interface
from src.utils.qa_config import QA_LEVELS

# Page configuration
st.set_page_config(
    page_title="Athabasca Glacier Albedo Dashboard",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def create_williamson_menounos_dashboard(df_data, df_results, df_focused, qa_config=None, qa_level=None):
    """
    Create comprehensive MOD10A1/MYD10A1 melt season analysis dashboard
    Following Williamson & Menounos 2021 methodology
    """
    # Show QA info if provided
    if qa_config and qa_level:
        st.info(f"📊 **Quality Filtering:** {qa_level} - {qa_config['modis_snow']['description']}")
    
    # Use the complete melt season dashboard
    create_melt_season_dashboard(df_data, df_results, df_focused)
    
    # Add interactive data table as a sub-section
    st.markdown("---")
    create_interactive_data_table_dashboard(df_data)


def create_hypsometric_dashboard(df_results, df_data):
    """
    Create comprehensive hypsometric analysis dashboard
    Following Williamson & Menounos 2021 methodology
    """
    st.subheader("🏔️ Hypsometric Analysis - Elevation Band Albedo Trends")
    st.markdown("*Elevation-based albedo analysis following Williamson & Menounos (2021)*")
    
    # Just show the elevation bands analysis (albedo visualization moved to separate menu)
    if not df_results.empty:
        try:
            st.dataframe(df_results, use_container_width=True)
        except ImportError as e:
            if "pyarrow" in str(e):
                st.error("PyArrow DLL loading issue detected. Using alternative display method.")
                st.write("**Hypsometric Results:**")
                st.write(df_results.to_string())
                st.info("💡 To fix PyArrow issues on Windows: `conda install pyarrow` or `pip install --force-reinstall pyarrow`")
            else:
                st.error(f"Error displaying dataframe: {e}")
                st.write(df_results.to_string())
    else:
        st.error("No hypsometric results available")
        
    st.info("📝 Full hypsometric dashboard implementation would be in src/dashboards/hypsometric_dashboard.py")
    st.info("💡 For interactive albedo visualization, select '🎨 Interactive Albedo Map' from the main menu")


def create_qa_comparison_dashboard():
    """
    Create dedicated QA level comparison dashboard
    """
    st.subheader("🔧 MODIS Quality Assessment (QA) Level Comparison")
    st.markdown("*Compare data coverage and statistics across different QA filtering levels*")
    
    # Load all datasets for comparison
    with st.spinner("Loading datasets for QA comparison..."):
        # Load MCD43A3 data
        config_mcd43a3 = get_data_source_info()['mcd43a3']
        from src.utils.data_loader import load_data_from_url
        df_mcd43a3, _ = load_data_from_url(config_mcd43a3['url'], config_mcd43a3['local_fallback'], show_status=False)
        
        # Load melt season data
        melt_data = load_all_melt_season_data(show_status=False)
        df_modis_snow = melt_data['time_series']
    
    # Dataset selector
    dataset_for_comparison = st.selectbox(
        "Select dataset for QA comparison:",
        ["MCD43A3 (Broadband Albedo)", "MOD10A1/MYD10A1 (Snow Albedo)"],
        key="qa_comparison_dataset"
    )
    
    # Select appropriate dataset and product type
    if dataset_for_comparison == "MCD43A3 (Broadband Albedo)":
        comparison_df = df_mcd43a3
        product_type = 'mcd43a3'
    else:
        comparison_df = df_modis_snow
        product_type = 'modis_snow'
    
    if comparison_df.empty:
        st.error(f"No data available for {dataset_for_comparison}")
        return
    
    st.info(f"📊 **Dataset:** {dataset_for_comparison} ({len(comparison_df):,} total records)")
    
    # QA level selector for comparison
    selected_qa_levels = st.multiselect(
        "Select QA levels to compare:",
        list(QA_LEVELS.keys()),
        default=list(QA_LEVELS.keys()),  # Select all by default
        key="qa_levels_for_comparison"
    )
    
    if not selected_qa_levels:
        st.warning("Please select at least one QA level for comparison")
        return
    
    # Apply filtering for each selected QA level
    comparison_data = {}
    filtering_results = {}
    
    from src.utils.qa_config import apply_qa_filtering, display_qa_comparison_stats, create_qa_impact_visualization
    
    for qa_level in selected_qa_levels:
        qa_config = QA_LEVELS[qa_level]
        filtered_df, stats = apply_qa_filtering(comparison_df, product_type, qa_config, show_stats=False)
        comparison_data[qa_level] = filtered_df
        filtering_results[qa_level] = stats
    
    # Display comparison statistics
    st.markdown("### 📊 QA Level Impact Summary")
    display_qa_comparison_stats(comparison_data, product_type)
    
    # Create impact visualization
    st.markdown("### 📈 QA Level Impact Visualization")
    qa_viz = create_qa_impact_visualization(comparison_data, product_type)
    if qa_viz:
        st.plotly_chart(qa_viz, use_container_width=True)
    
    # Detailed breakdown
    st.markdown("### 📋 Detailed QA Level Breakdown")
    
    # Create tabs for each QA level
    if len(selected_qa_levels) > 1:
        tabs = st.tabs([f"{qa_level}" for qa_level in selected_qa_levels])
        
        for i, qa_level in enumerate(selected_qa_levels):
            with tabs[i]:
                qa_config = QA_LEVELS[qa_level]
                filtered_df = comparison_data[qa_level]
                stats = filtering_results[qa_level]
                
                # QA level description
                st.markdown(f"**{qa_level}**")
                st.markdown(qa_config["description"])
                
                # Product-specific details
                if product_type == 'mcd43a3':
                    st.markdown(f"**MCD43A3 Filter:** {qa_config['mcd43a3']['description']}")
                    st.markdown(f"**Expected Coverage:** {qa_config['mcd43a3']['expected_coverage']}")
                else:
                    st.markdown(f"**MOD10A1/MYD10A1 Filter:** {qa_config['modis_snow']['description']}")
                    st.markdown(f"**Expected Coverage:** {qa_config['modis_snow']['expected_coverage']}")
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Records", f"{stats['filtered_count']:,}")
                with col2:
                    st.metric("Retention Rate", f"{stats['retention_rate']:.1f}%")
                with col3:
                    if not filtered_df.empty and 'albedo_mean' in filtered_df.columns:
                        st.metric("Mean Albedo", f"{filtered_df['albedo_mean'].mean():.3f}")
                    else:
                        st.metric("Mean Albedo", "N/A")
                with col4:
                    if not filtered_df.empty and 'date_str' in filtered_df.columns:
                        unique_dates = filtered_df['date_str'].nunique()
                        st.metric("Unique Dates", f"{unique_dates:,}")
                    else:
                        st.metric("Unique Dates", "N/A")
                
                # Data sample
                if not filtered_df.empty:
                    st.markdown("**Sample Data (first 10 records):**")
                    display_cols = ['date_str', 'albedo_mean'] if 'date_str' in filtered_df.columns else list(filtered_df.columns)[:5]
                    st.dataframe(filtered_df[display_cols].head(10), use_container_width=True)
    
    # Recommendations
    st.markdown("### 💡 QA Level Recommendations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 Choose 'Standard QA' if:**")
        st.markdown("• You need balanced quality vs coverage")
        st.markdown("• This is your first analysis")
        st.markdown("• You want reliable results for publications")
        
        st.markdown("**🔬 Choose 'Advanced Strict' if:**")
        st.markdown("• Data quality is critical")
        st.markdown("• You can accept reduced coverage")
        st.markdown("• Working with climate trend analysis")
    
    with col2:
        st.markdown("**📊 Choose 'Advanced Relaxed' if:**")
        st.markdown("• You need maximum data coverage")
        st.markdown("• Working with data-sparse regions")
        st.markdown("• Doing exploratory analysis")
        
        st.markdown("**⚖️ Choose 'Advanced Standard' if:**")
        st.markdown("• You need research-grade quality")
        st.markdown("• Balancing coverage and reliability")
        st.markdown("• Following established protocols")


def initialize_data_cache():
    """Initialize global data cache in session state"""
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {
            'melt_season': None,
            'mcd43a3': None,
            'hypsometric': None,
            'last_loaded': {}
        }

def cache_data(data_type, data):
    """Cache data in session state"""
    if 'data_cache' not in st.session_state:
        initialize_data_cache()
    
    st.session_state.data_cache[data_type] = data
    st.session_state.data_cache['last_loaded'][data_type] = datetime.now()

def get_cached_data(data_type):
    """Get cached data from session state"""
    if 'data_cache' not in st.session_state:
        initialize_data_cache()
    
    return st.session_state.data_cache.get(data_type)

def main():
    """
    Main Streamlit dashboard
    """
    # Initialize data cache
    initialize_data_cache()
    
    # Header
    st.title("🏔️ Athabasca Glacier Albedo Analysis")
    
    # Sidebar configuration
    st.sidebar.title("⚙️ Dashboard Settings")
    
    # Data cache management
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Data Cache")
    
    # Show cached data status
    cached_datasets = []
    if get_cached_data('melt_season'):
        cached_datasets.append("MOD10A1")
    if get_cached_data('mcd43a3'):
        cached_datasets.append("MCD43A3")
    if get_cached_data('hypsometric'):
        cached_datasets.append("Hypsometric")
    
    if cached_datasets:
        st.sidebar.success(f"Cached: {', '.join(cached_datasets)}")
        if st.sidebar.button("🗑️ Clear Cache"):
            st.session_state.data_cache = {
                'melt_season': None,
                'mcd43a3': None,
                'hypsometric': None,
                'last_loaded': {}
            }
            st.rerun()
    else:
        st.sidebar.info("No data cached yet")
    
    
    # Use default QA settings (QA level selection disabled for now)
    selected_qa_level = "Standard QA"
    qa_config = {
        "description": "Default QA settings",
        "modis_snow": {"qa_threshold": 1, "description": "QA ≤ 1 (best + good quality)"},
        "mcd43a3": {"qa_threshold": 0, "description": "QA = 0 (full BRDF inversions only)"}
    }
    
    # Data source selection
    selected_dataset = st.sidebar.selectbox(
        "Analysis Type",
        [
            "Data Processing & Configuration",
            "MCD43A3 Broadband Albedo",
            "MOD10A1/MYD10A1 Daily Snow Albedo", 
            "Hypsometric Analysis",
            "Statistical Analysis",
            "Interactive Albedo Visualization",
            "Real-time QA Comparison"
        ]
    )
    
    # Load data based on selection
    if selected_dataset == "Data Processing & Configuration":
        # Create data processing and configuration dashboard
        from src.dashboards.processing_dashboard import create_processing_dashboard
        create_processing_dashboard()
    
    elif selected_dataset == "MCD43A3 Broadband Albedo":
        # Check for custom uploaded data first
        from src.utils.csv_manager import load_uploaded_or_default_data, show_data_source_indicator
        show_data_source_indicator()
        
        # Load data (uploaded or default)
        with st.spinner("Loading MCD43A3 data..."):
            def load_default_mcd43a3(show_status):
                config = get_data_source_info()['mcd43a3']
                from src.utils.data_loader import load_data_from_url
                df, source = load_data_from_url(config['url'], config['local_fallback'], show_status=show_status)
                return df
            
            df = load_uploaded_or_default_data(
                'mcd43a3',
                load_default_mcd43a3,
                show_status=False
            )
        
        if not df.empty:
            # Use original data without QA filtering (QA filtering disabled for now)
            filtered_df = df
            
            # Show main dashboard with filtered data
            create_mcd43a3_dashboard(filtered_df, qa_config, selected_qa_level)
    
    elif selected_dataset == "MOD10A1/MYD10A1 Daily Snow Albedo":
        # Try CSV import first
        melt_data = create_csv_import_interface()
        
        if melt_data is None:
            # Check for custom uploaded data first  
            from src.utils.csv_manager import load_uploaded_or_default_data, show_data_source_indicator
            show_data_source_indicator()
            
            # Load data (uploaded or default)
            with st.spinner("Loading melt season data..."):
                melt_data = load_uploaded_or_default_data(
                    'melt_season', 
                    lambda show_status: load_all_melt_season_data(show_status=show_status),
                    show_status=False
                )
        
        # Cache the loaded data
        if melt_data:
            cache_data('melt_season', melt_data)
            
            # Store source information if this came from CSV import
            if hasattr(st.session_state, 'uploaded_csv_info'):
                st.session_state.last_uploaded_file = st.session_state.uploaded_csv_info
        
        # Use original data without QA filtering (QA filtering disabled for now)
        filtered_time_series = melt_data['time_series']
        filtered_focused = melt_data['focused']
        
        # Create comprehensive dashboard with filtered data
        create_williamson_menounos_dashboard(
            filtered_time_series, 
            melt_data['results'], 
            filtered_focused,
            qa_config,
            selected_qa_level
        )
            
    elif selected_dataset == "Hypsometric Analysis":
        # Check for custom uploaded data first
        from src.utils.csv_manager import load_uploaded_or_default_data, show_data_source_indicator
        show_data_source_indicator()
        
        # Load data (uploaded or default)
        hyps_data = load_uploaded_or_default_data(
            'hypsometric',
            load_hypsometric_data,
            show_status=True
        )
        
        # Create comprehensive hypsometric dashboard
        create_hypsometric_dashboard(hyps_data['results'], hyps_data['time_series'])
    
    elif selected_dataset == "Statistical Analysis":
        # Check if we have cached data first
        cached_melt_data = get_cached_data('melt_season')
        cached_hyps_data = get_cached_data('hypsometric')
        
        melt_data = cached_melt_data
        hyps_data = cached_hyps_data
        
        # Show detailed data source information
        st.markdown("### 📊 Data Source Information")
        
        if cached_melt_data:
            last_loaded = st.session_state.data_cache['last_loaded'].get('melt_season')
            
            # Create an info box with detailed CSV information
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.success("✅ **Using cached MOD10A1 data from previous section**")
                    
                    # Show data details
                    if melt_data and 'time_series' in melt_data:
                        df = melt_data['time_series']
                        
                        # Extract QA information if available
                        qa_info = "Unknown"
                        if 'qa_level' in df.columns:
                            qa_levels = df['qa_level'].unique()
                            if len(qa_levels) == 1:
                                qa_info = qa_levels[0]
                            else:
                                qa_info = f"Mixed: {', '.join(qa_levels[:3])}..."
                        elif 'qa_description' in df.columns:
                            qa_desc = df['qa_description'].unique()
                            if len(qa_desc) == 1:
                                qa_info = qa_desc[0]
                        
                        st.markdown(f"""
                        **Dataset Details:**
                        - **Rows:** {len(df):,} observations
                        - **Date Range:** {df['date'].min()} to {df['date'].max()}
                        - **QA Configuration:** {qa_info}
                        - **Loaded:** {last_loaded.strftime('%Y-%m-%d %H:%M:%S') if last_loaded else 'Unknown'}
                        """)
                        
                        # Show column info
                        data_cols = [col for col in df.columns if col not in ['date', 'qa_level', 'qa_description', 'qa_advanced']]
                        st.markdown(f"- **Data Columns:** {', '.join(data_cols)}")
                        
                        # Show source file information if available
                        if hasattr(st.session_state, 'last_uploaded_file'):
                            file_info = st.session_state.last_uploaded_file
                            st.markdown(f"- **Source File:** {file_info.get('name', 'Unknown')}")
                            if 'size' in file_info:
                                st.markdown(f"- **File Size:** {file_info['size']:,} bytes")
                        
                        # Show data quality summary
                        if 'albedo' in df.columns:
                            albedo_stats = df['albedo'].describe()
                            st.markdown(f"- **Albedo Range:** {albedo_stats['min']:.3f} - {albedo_stats['max']:.3f}")
                            st.markdown(f"- **Mean Albedo:** {albedo_stats['mean']:.3f}")
                
                with col2:
                    if st.button("🔄 Reload Fresh Data"):
                        # Clear cache and reload
                        st.session_state.data_cache['melt_season'] = None
                        st.rerun()
            
            # Show data preview
            with st.expander("🔍 Preview Data (First 10 Rows)", expanded=False):
                if melt_data and 'time_series' in melt_data:
                    df_preview = melt_data['time_series'].head(10)
                    st.dataframe(df_preview, use_container_width=True)
                    
                    # Show data summary
                    st.markdown("**Quick Stats:**")
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("Total Rows", f"{len(melt_data['time_series']):,}")
                    with col_b:
                        if 'albedo' in df_preview.columns:
                            st.metric("Avg Albedo", f"{melt_data['time_series']['albedo'].mean():.3f}")
                    with col_c:
                        unique_dates = melt_data['time_series']['date'].nunique()
                        st.metric("Unique Dates", f"{unique_dates:,}")
        else:
            st.info("ℹ️ Loading fresh MOD10A1 data for statistical analysis...")
        
        # Load missing data if needed
        if melt_data is None:
            with st.spinner("Loading melt season data for statistical analysis..."):
                melt_data = load_all_melt_season_data(show_status=False)
                cache_data('melt_season', melt_data)
        
        if hyps_data is None:
            with st.spinner("Loading hypsometric data for statistical analysis..."):
                hyps_data = load_hypsometric_data(show_status=False)
                cache_data('hypsometric', hyps_data)
        
        # Create statistical analysis dashboard
        create_statistical_analysis_dashboard(
            melt_data['time_series'], 
            melt_data['results'], 
            hyps_data['time_series'] if hyps_data else None
        )
    
    elif selected_dataset == "Interactive Albedo Visualization":
        # Create dedicated interactive albedo visualization
        create_interactive_albedo_dashboard(qa_config, selected_qa_level)
    
    elif selected_dataset == "Real-time QA Comparison":
        # Create real-time QA comparison dashboard
        create_realtime_qa_dashboard()
    
    # Footer information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    data_sources = get_data_source_info()
    for key, config in data_sources.items():
        st.sidebar.markdown(f"• {config['description']}")
    
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()