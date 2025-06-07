"""
Modular Streamlit Web Dashboard for Athabasca Glacier Albedo Analysis
Refactored version with separated modules for better maintainability
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Import our modular components with better path handling
import sys
import os

# Add current directory and src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

# Now import the modules
from src.utils.data_loader import (
    load_dataset, 
    load_all_melt_season_data, 
    load_hypsometric_data,
    get_data_source_info
)
from src.dashboards.mcd43a3_dashboard import create_mcd43a3_dashboard
from src.dashboards.melt_season_dashboard import create_melt_season_dashboard
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
    
    Now using the full implementation from src/dashboards/melt_season_dashboard.py
    """
    # Use the complete melt season dashboard
    create_melt_season_dashboard(df_data, df_results, df_focused)


def create_interactive_albedo_dashboard():
    """
    Create dedicated interactive albedo visualization dashboard
    Top-level visualization showing MODIS pixels on satellite imagery
    """
    st.subheader("🎨 Interactive MODIS Albedo Visualization")
    st.markdown("*Real-time MODIS pixel visualization on satellite imagery*")
    
    # Load hypsometric data for the albedo visualization (suppress main area status messages)
    with st.spinner("Loading albedo data..."):
        hyps_data = load_hypsometric_data(show_status=False)
        df_data = hyps_data['time_series']
    
    if not df_data.empty:
        # Prepare date data
        df_data_copy = df_data.copy()
        df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
        df_data_copy['date_str'] = df_data_copy['date'].dt.strftime('%Y-%m-%d')
        
        # Sidebar controls for albedo visualization
        st.sidebar.header("🎨 Albedo Visualization Controls")
        
        # Date selection
        available_dates = sorted(df_data_copy['date_str'].unique())
        
        
        # Default to Specific Date mode
        visualization_mode = "Specific Date"
        
        selected_date = None
        if visualization_mode == "Specific Date":
            # Show date selection method choice
            date_method = st.sidebar.radio(
                "Date Selection Method:",
                ["📅 Calendar Picker", "📋 List of Available Dates"],
                key="date_method"
            )
            
            if date_method == "📅 Calendar Picker":
                # Convert available dates to datetime objects for calendar widget
                available_datetime_dates = [pd.to_datetime(date).date() for date in available_dates]
                
                # Use date_input for calendar selection
                selected_date_obj = st.sidebar.date_input(
                    "Select Date",
                    value=available_datetime_dates[-1] if available_datetime_dates else pd.to_datetime('2023-08-15').date(),
                    min_value=min(available_datetime_dates) if available_datetime_dates else pd.to_datetime('2015-01-01').date(),
                    max_value=max(available_datetime_dates) if available_datetime_dates else pd.to_datetime('2023-12-31').date(),
                    key="date_calendar",
                    help="⚠️ Not all dates have MODIS data. Check the data availability info above!"
                )
                
                # Convert back to string format
                selected_date = selected_date_obj.strftime('%Y-%m-%d')
                
                # Check if selected date has data
                if selected_date not in available_dates:
                    st.sidebar.warning(f"⚠️ No data available for {selected_date}")
                    
                    # Show data availability pattern for the selected month
                    selected_month = selected_date_obj.strftime('%Y-%m')
                    monthly_dates = [d for d in available_dates if d.startswith(selected_month)]
                    
                    if monthly_dates:
                        st.sidebar.success(f"✅ {len(monthly_dates)} days with data in {selected_month}:")
                        # Show available dates in selected month
                        month_display = ", ".join([d.split('-')[2] for d in monthly_dates[:10]])
                        if len(monthly_dates) > 10:
                            month_display += f"... (+{len(monthly_dates)-10} more)"
                        st.sidebar.write(f"📅 Days: {month_display}")
                    
                    # Fallback: show closest available dates
                    closest_dates = sorted(available_dates, key=lambda x: abs(pd.to_datetime(x) - pd.to_datetime(selected_date)))[:5]
                    fallback_date = st.sidebar.selectbox(
                        "🎯 Closest available dates:",
                        closest_dates,
                        key="fallback_date_selector",
                        help="These dates have confirmed MODIS data"
                    )
                    selected_date = fallback_date
                else:
                    st.sidebar.success(f"✅ Data available for {selected_date}")
                    
            else:  # List of Available Dates
                # Group dates by year-month for better organization
                dates_by_month = {}
                for date in available_dates:
                    year_month = date[:7]  # YYYY-MM
                    if year_month not in dates_by_month:
                        dates_by_month[year_month] = []
                    dates_by_month[year_month].append(date)
                
                # Show month selector first
                available_months = sorted(dates_by_month.keys(), reverse=True)
                selected_month = st.sidebar.selectbox(
                    "📅 Select Month:",
                    available_months,
                    index=0,
                    key="month_selector",
                    help=f"Shows months with available data ({len(available_months)} months total)"
                )
                
                # Show dates for selected month
                month_dates = dates_by_month[selected_month]
                selected_date = st.sidebar.selectbox(
                    f"📊 Select Date in {selected_month}:",
                    month_dates,
                    index=len(month_dates)-1,
                    key="date_from_list",
                    help=f"{len(month_dates)} dates available in this month"
                )
        elif visualization_mode == "Recent Data":
            # Use last 30 days of data
            recent_date = df_data_copy['date'].max()
            cutoff_date = recent_date - pd.Timedelta(days=30)
            df_data_copy = df_data_copy[df_data_copy['date'] >= cutoff_date]
            st.sidebar.info(f"Showing data from {cutoff_date.strftime('%Y-%m-%d')} to {recent_date.strftime('%Y-%m-%d')}")
        
        # Create and display the map at the top
        from streamlit_folium import st_folium
        
        # Create albedo map
        if visualization_mode == "Specific Date" and selected_date:
            # Filter for specific date
            date_data = df_data_copy[df_data_copy['date_str'] == selected_date]
            albedo_map = create_albedo_map(date_data, selected_date)
        else:
            # Show all or recent data
            albedo_map = create_albedo_map(df_data_copy)
        
        # Display the map prominently at the top
        map_data = st_folium(albedo_map, width=900, height=600)
        
        # Show data description below the map
        if visualization_mode == "Specific Date" and selected_date:
            st.markdown(f"**Showing MODIS pixels for: {selected_date}**")
        else:
            if visualization_mode == "All Data":
                st.markdown(f"**Showing representative visualization ({len(df_data_copy)} observations)**")
            else:
                st.markdown(f"**Showing recent data visualization ({len(df_data_copy)} observations)**")
        
        # Show summary statistics below the description
        if visualization_mode == "Specific Date" and selected_date:
            display_data = df_data_copy[df_data_copy['date_str'] == selected_date]
        else:
            display_data = df_data_copy
        
        if not display_data.empty:
            st.markdown("### 📊 Data Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Observations", len(display_data))
            with col2:
                st.metric("Mean Albedo", f"{display_data['albedo_mean'].mean():.3f}")
            with col3:
                st.metric("Albedo Range", f"{display_data['albedo_mean'].min():.3f} - {display_data['albedo_mean'].max():.3f}")
            with col4:
                unique_dates = display_data['date_str'].nunique() if 'date_str' in display_data.columns else 1
                st.metric("Unique Dates", unique_dates)
    
    else:
        st.error("No albedo data available for visualization")
        st.info("Please ensure hypsometric analysis has been run and data is available.")


def create_hypsometric_dashboard(df_results, df_data):
    """
    Create comprehensive hypsometric analysis dashboard
    Following Williamson & Menounos 2021 methodology
    
    Note: This is a simplified version. Full implementation would be moved 
    to src/dashboards/hypsometric_dashboard.py
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


def main():
    """
    Main Streamlit dashboard
    """
    # Header
    st.title("🏔️ Athabasca Glacier Albedo Analysis")
    
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
        ["MCD43A3 Spectral", "MOD10A1/MYD10A1 Melt Season", "Hypsometric", "🎨 Interactive Albedo Map"]
    )
    
    # Load data based on selection
    if selected_dataset == "MCD43A3 Spectral":
        df, source = load_dataset('mcd43a3')
        
        if not df.empty:
            create_mcd43a3_dashboard(df)
    
    elif selected_dataset == "MOD10A1/MYD10A1 Melt Season":
        # Load all three datasets for comprehensive analysis (suppress status messages)
        with st.spinner("Loading melt season data..."):
            melt_data = load_all_melt_season_data(show_status=False)
        
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
    
    elif selected_dataset == "🎨 Interactive Albedo Map":
        # Create dedicated interactive albedo visualization
        create_interactive_albedo_dashboard()
    
    # Footer information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    data_sources = get_data_source_info()
    for key, config in data_sources.items():
        st.sidebar.markdown(f"• {config['description']}")
    
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()