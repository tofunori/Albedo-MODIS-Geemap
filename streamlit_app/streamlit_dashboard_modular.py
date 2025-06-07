"""
Modular Streamlit Web Dashboard for Athabasca Glacier Albedo Analysis
Refactored version with separated modules for better maintainability
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Import our modular components
from src.utils.data_loader import (
    load_dataset, 
    load_all_melt_season_data, 
    load_hypsometric_data,
    get_data_source_info
)
from src.dashboards.mcd43a3_dashboard import create_mcd43a3_dashboard
from src.utils.maps import create_albedo_map

# Page configuration
st.set_page_config(
    page_title="Athabasca Glacier Albedo Dashboard",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def create_williamson_menounos_dashboard(df_data, df_results, df_focused):
    """
    Create comprehensive MOD10A1/MYD10A1 melt season analysis dashboard
    Following Williamson & Menounos 2021 methodology
    
    Note: This is a simplified version. Full implementation would be moved 
    to src/dashboards/melt_season_dashboard.py
    """
    st.subheader("🌊 MOD10A1/MYD10A1 Daily Snow Albedo Analysis")
    st.markdown("*Following Williamson & Menounos (2021) methodology*")
    
    # For now, show basic info - full implementation would be in separate module
    if not df_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Observations", len(df_data))
        with col2:
            st.metric("Years of Data", df_data['year'].nunique())
        with col3:
            st.metric("Mean Albedo", f"{df_data['albedo_mean'].mean():.3f}")
        
        # Show sample data with error handling
        if not df_results.empty:
            st.subheader("📊 Trend Analysis Results")
            try:
                st.dataframe(df_results.head(10), use_container_width=True)
            except ImportError as e:
                if "pyarrow" in str(e):
                    st.error("PyArrow DLL issue. Using alternative display.")
                    st.write("**Trend Results (first 10 rows):**")
                    st.write(df_results.head(10).to_string())
                else:
                    st.error(f"Error displaying results: {e}")
            
        st.info("📝 Full melt season dashboard implementation would be in src/dashboards/melt_season_dashboard.py")
    
    else:
        st.error("No melt season data available")


def create_hypsometric_dashboard(df_results, df_data):
    """
    Create comprehensive hypsometric analysis dashboard
    Following Williamson & Menounos 2021 methodology
    
    Note: This is a simplified version. Full implementation would be moved 
    to src/dashboards/hypsometric_dashboard.py
    """
    st.subheader("🏔️ Hypsometric Analysis - Elevation Band Albedo Trends")
    st.markdown("*Elevation-based albedo analysis following Williamson & Menounos (2021)*")
    
    # Create tabs for different analyses
    tab1, tab2 = st.tabs(["📊 Elevation Bands", "🎨 Albedo Visualization"])
    
    with tab1:
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
    
    with tab2:
        st.markdown("### 🎨 Interactive Albedo Visualization")
        st.markdown("**Explore albedo data as colored pixels within the glacier boundary**")
        
        if not df_data.empty:
            # Prepare date data
            df_data_copy = df_data.copy()
            df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
            df_data_copy['date_str'] = df_data_copy['date'].dt.strftime('%Y-%m-%d')
            
            # Sidebar controls for albedo visualization
            st.sidebar.header("🎨 Albedo Visualization")
            
            # Date selection
            available_dates = sorted(df_data_copy['date_str'].unique())
            
            # Show options
            visualization_mode = st.sidebar.radio(
                "Visualization Mode:",
                ["All Data", "Specific Date", "Recent Data"],
                key="viz_mode"
            )
            
            selected_date = None
            if visualization_mode == "Specific Date":
                selected_date = st.sidebar.selectbox(
                    "Select Date",
                    available_dates,
                    index=len(available_dates)-1 if available_dates else 0,
                    key="date_selector"
                )
            elif visualization_mode == "Recent Data":
                # Use last 30 days of data
                recent_date = df_data_copy['date'].max()
                cutoff_date = recent_date - pd.Timedelta(days=30)
                df_data_copy = df_data_copy[df_data_copy['date'] >= cutoff_date]
                st.sidebar.info(f"Showing data from {cutoff_date.strftime('%Y-%m-%d')} to {recent_date.strftime('%Y-%m-%d')}")
            
            # Create albedo map
            if visualization_mode == "Specific Date" and selected_date:
                # Filter for specific date
                date_data = df_data_copy[df_data_copy['date_str'] == selected_date]
                albedo_map = create_albedo_map(date_data, selected_date)
                st.markdown(f"**Showing data for: {selected_date}**")
            else:
                # Show all or recent data
                albedo_map = create_albedo_map(df_data_copy)
                if visualization_mode == "All Data":
                    st.markdown(f"**Showing all available data ({len(df_data_copy)} observations)**")
                else:
                    st.markdown(f"**Showing recent data ({len(df_data_copy)} observations)**")
            
            # Display map
            st.markdown("**Interactive Features:**")
            st.markdown("- 🗺️ **Multiple layers**: Switch between Satellite, Terrain, OpenStreetMap")
            st.markdown("- 🎨 **Color-coded pixels**: Each point colored by albedo value")
            st.markdown("- 📍 **Click for details**: Click any point to see albedo, date, elevation")
            st.markdown("- 🏔️ **Glacier boundary**: Red outline shows glacier extent")
            
            # Display the map
            from streamlit_folium import st_folium
            map_data = st_folium(albedo_map, width=700, height=500)
        
        else:
            st.error("No albedo data available for visualization")


def main():
    """
    Main Streamlit dashboard
    """
    # Header
    st.title("🏔️ Athabasca Glacier Albedo Analysis Dashboard")
    st.markdown("**Live Interactive Dashboard** - Updates automatically when analysis is rerun")
    
    # Sidebar configuration
    st.sidebar.title("⚙️ Dashboard Settings")
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh every 5 minutes", value=False)
    
    if auto_refresh:
        time.sleep(300)  # Wait 5 minutes
        st.rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data Now"):
        st.cache_data.clear()
        st.rerun()
    
    # Data source selection
    selected_dataset = st.sidebar.selectbox(
        "Select Dataset",
        ["MCD43A3 Spectral", "MOD10A1/MYD10A1 Melt Season", "Hypsometric"]
    )
    
    # Load data based on selection
    if selected_dataset == "MCD43A3 Spectral":
        df, source = load_dataset('mcd43a3')
        
        if not df.empty:
            create_mcd43a3_dashboard(df)
    
    elif selected_dataset == "MOD10A1/MYD10A1 Melt Season":
        # Load all three datasets for comprehensive analysis
        melt_data = load_all_melt_season_data()
        
        # Create comprehensive dashboard
        create_williamson_menounos_dashboard(
            melt_data['time_series'], 
            melt_data['results'], 
            melt_data['focused']
        )
            
    elif selected_dataset == "Hypsometric":
        # Load both results and data for comprehensive analysis
        hyps_data = load_hypsometric_data()
        
        # Create comprehensive hypsometric dashboard
        create_hypsometric_dashboard(hyps_data['results'], hyps_data['time_series'])
    
    # Footer information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    data_sources = get_data_source_info()
    for key, config in data_sources.items():
        st.sidebar.markdown(f"• {config['description']}")
    
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()