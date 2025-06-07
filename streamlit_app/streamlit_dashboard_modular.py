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
from src.dashboards.statistical_analysis_dashboard import create_statistical_analysis_dashboard
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
        
        # Product selection for Earth Engine visualization
        product_type = st.sidebar.selectbox(
            "🛰️ MODIS Product:",
            ["MOD10A1/MYD10A1 (Daily Snow Albedo)", "MCD43A3 (Broadband Albedo)"],
            key="product_selector",
            help="MOD10A1/MYD10A1: Daily snow albedo (Terra+Aqua)\nMCD43A3: 16-day broadband albedo composite"
        )
        
        # Convert selection to product code
        selected_product = "MOD10A1" if "MOD10A1" in product_type else "MCD43A3"
        
        # Quality filtering options based on selected product
        st.sidebar.subheader("⚙️ Quality Filtering")
        
        if selected_product == "MOD10A1":
            qa_option = st.sidebar.selectbox(
                "QA Level for MOD10A1/MYD10A1:",
                ["Strict (QA = 0)", "Standard (QA ≤ 1)", "Relaxed (QA ≤ 2)"],
                index=1,  # Default to Standard
                key="qa_mod10a1",
                help="QA = 0: Best quality only\nQA ≤ 1: Best + good quality\nQA ≤ 2: Include fair quality"
            )
            
            # Convert to QA threshold
            if "QA = 0" in qa_option:
                qa_threshold = 0
            elif "QA ≤ 1" in qa_option:
                qa_threshold = 1
            else:  # QA ≤ 2
                qa_threshold = 2
                
        else:  # MCD43A3
            qa_option = st.sidebar.selectbox(
                "QA Level for MCD43A3:",
                ["Strict (QA = 0)", "Relaxed (QA ≤ 1)"],
                index=0,  # Default to Strict for MCD43A3
                key="qa_mcd43a3",
                help="QA = 0: Full BRDF inversions only\nQA ≤ 1: Include magnitude inversions"
            )
            
            # Convert to QA threshold
            if "QA = 0" in qa_option:
                qa_threshold = 0
            else:  # QA ≤ 1
                qa_threshold = 1
        
        # Get all available dates first
        all_available_dates = sorted(df_data_copy['date_str'].unique())
        
        # Pixel analysis and filtering
        st.sidebar.subheader("🔢 Pixel Count Analysis")
        
        analyze_pixels = st.sidebar.button(
            "🔍 Analyze Pixel Counts",
            key="analyze_pixels_btn",
            help="Check how many pixels are available for each date"
        )
        
        # Initialize session state for pixel data
        if 'pixel_analysis_data' not in st.session_state:
            st.session_state.pixel_analysis_data = None
        
        if analyze_pixels:
            with st.spinner("Analyzing pixel counts for dates..."):
                from src.utils.ee_utils import initialize_earth_engine, count_modis_pixels_for_date, get_roi_from_geojson
                
                ee_available = initialize_earth_engine()
                
                if ee_available:
                    # Load glacier boundary for pixel counting
                    import json
                    import os
                    
                    try:
                        # Load glacier boundary directly
                        
                        # Try to load glacier boundary file
                        possible_paths = [
                            '../Athabasca_mask_2023_cut.geojson',
                            '../../Athabasca_mask_2023_cut.geojson', 
                            'Athabasca_mask_2023_cut.geojson'
                        ]
                        
                        glacier_geojson = None
                        for path in possible_paths:
                            try:
                                with open(path, 'r') as f:
                                    glacier_geojson = json.load(f)
                                break
                            except:
                                continue
                        
                        if glacier_geojson:
                            athabasca_roi = get_roi_from_geojson(glacier_geojson)
                            
                            # Sample dates for analysis - ensure we cover all years
                            # Group dates by year to ensure good coverage
                            dates_by_year = {}
                            for date in all_available_dates:
                                year = date[:4]  # Extract year (YYYY)
                                if year not in dates_by_year:
                                    dates_by_year[year] = []
                                dates_by_year[year].append(date)
                            
                            # Sample dates from each year (5-10 dates per year)
                            sample_dates = []
                            for year, year_dates in dates_by_year.items():
                                # Take every Nth date to get good coverage, aim for 8 dates per year
                                step = max(1, len(year_dates) // 8)
                                year_sample = year_dates[::step][:10]  # Max 10 dates per year
                                sample_dates.extend(year_sample)
                            
                            # Limit total for performance but ensure good year coverage
                            sample_dates = sample_dates[:80]  # Increased from 30 to 80
                            
                            # Show analysis info
                            analyzed_years = sorted(list(dates_by_year.keys()))
                            st.info(f"🔍 Analyzing {len(sample_dates)} dates across {len(analyzed_years)} years: {', '.join(analyzed_years)}")
                            
                            pixel_analysis = {}
                            
                            progress_bar = st.progress(0)
                            for i, date in enumerate(sample_dates):
                                try:
                                    pixel_count = count_modis_pixels_for_date(date, athabasca_roi, selected_product, qa_threshold)
                                    pixel_analysis[date] = pixel_count
                                    progress_bar.progress((i + 1) / len(sample_dates))
                                except Exception as e:
                                    pixel_analysis[date] = 0
                            
                            progress_bar.empty()
                            st.session_state.pixel_analysis_data = pixel_analysis
                            
                        else:
                            st.error("Could not load glacier boundary")
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                else:
                    st.error("Earth Engine not available")
        
        # Display pixel analysis results and filtering options
        if st.session_state.pixel_analysis_data:
            pixel_data = st.session_state.pixel_analysis_data
            
            # Show detailed pixel count list
            st.sidebar.markdown("**📊 Detailed Pixel Counts:**")
            
            # Sort by pixel count (descending) for better visibility
            sorted_pixel_data = sorted(pixel_data.items(), key=lambda x: x[1], reverse=True)
            
            # Display each date with its pixel count and month
            pixel_display = {}
            for date, count in sorted_pixel_data:
                try:
                    import datetime
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    month_name = date_obj.strftime('%B')  # Full month name
                    month_year = date_obj.strftime('%B %Y')  # Month Year
                    
                    display_text = f"{date} ({month_name}) - {count} pixels"
                    pixel_display[display_text] = date
                    
                    # Color coding for sidebar display
                    if count == 0:
                        st.sidebar.write(f"🔴 {display_text}")
                    elif count <= 5:
                        st.sidebar.write(f"🟡 {display_text}")
                    elif count <= 15:
                        st.sidebar.write(f"🟠 {display_text}")
                    elif count <= 30:
                        st.sidebar.write(f"🟢 {display_text}")
                    else:
                        st.sidebar.write(f"🔵 {display_text}")
                except:
                    st.sidebar.write(f"• {date} - {count} pixels")
            
            st.sidebar.markdown("---")
            
            # Pixel count filter options
            st.sidebar.markdown("**🎯 Filter Options:**")
            
            # Year selector
            available_years = set()
            for date in pixel_data.keys():
                try:
                    import datetime
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    available_years.add(date_obj.year)
                except:
                    pass
            
            selected_years = st.sidebar.multiselect(
                "Select Years:",
                sorted(list(available_years)),
                default=sorted(list(available_years))[-3:] if len(available_years) >= 3 else sorted(list(available_years)),  # Default to last 3 years
                key="year_filter"
            )
            
            # Pixel count filter type
            filter_type = st.sidebar.radio(
                "Pixel count filter:",
                ["Exactly X pixels", "X pixels or less", "X pixels or more"],
                index=1,  # Default to "or less"
                key="filter_type"
            )
            
            # Pixel count value
            if filter_type == "Exactly X pixels":
                pixel_threshold = st.sidebar.number_input(
                    "Number of pixels:",
                    min_value=0, 
                    max_value=100, 
                    value=5,
                    key="exact_pixels"
                )
            elif filter_type == "X pixels or less":
                pixel_threshold = st.sidebar.number_input(
                    "Maximum pixels:",
                    min_value=0, 
                    max_value=100, 
                    value=5,
                    key="max_pixels"
                )
            else:  # "X pixels or more"
                pixel_threshold = st.sidebar.number_input(
                    "Minimum pixels:",
                    min_value=0, 
                    max_value=100, 
                    value=10,
                    key="min_pixels"
                )
            
            # Month filter
            available_months = set()
            for date in pixel_data.keys():
                try:
                    import datetime
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    month_year = date_obj.strftime('%B %Y')
                    available_months.add(month_year)
                except:
                    pass
            
            month_filter = st.sidebar.selectbox(
                "Filter by month:",
                ["All months"] + sorted(list(available_months)),
                key="month_filter"
            )
            
            # Apply filters
            filtered_dates = []
            for date, count in pixel_data.items():
                # Check year filter first
                year_match = True
                if selected_years:
                    try:
                        import datetime
                        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                        year_match = date_obj.year in selected_years
                    except:
                        year_match = False
                
                # Check pixel count filter
                if filter_type == "Exactly X pixels":
                    pixel_match = (pixel_threshold == 0) or (count == pixel_threshold)
                elif filter_type == "X pixels or less":
                    pixel_match = count <= pixel_threshold
                else:  # "X pixels or more"
                    pixel_match = count >= pixel_threshold
                
                # Check month filter
                month_match = True
                if month_filter != "All months":
                    try:
                        import datetime
                        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                        date_month_year = date_obj.strftime('%B %Y')
                        month_match = (date_month_year == month_filter)
                    except:
                        month_match = False
                
                if year_match and pixel_match and month_match:
                    filtered_dates.append(date)
            
            available_dates = filtered_dates
            
            # Show filter results
            years_text = f"({', '.join(map(str, sorted(selected_years)))})" if selected_years else "(no years selected)"
            
            if filter_type == "Exactly X pixels":
                filter_desc = f"exactly {pixel_threshold} pixels"
            elif filter_type == "X pixels or less":
                filter_desc = f"{pixel_threshold} pixels or less"
            else:
                filter_desc = f"{pixel_threshold} pixels or more"
            
            if selected_years and month_filter != "All months":
                st.sidebar.success(f"✅ {len(available_dates)} dates with {filter_desc} in {month_filter} {years_text}")
            elif selected_years:
                st.sidebar.success(f"✅ {len(available_dates)} dates with {filter_desc} {years_text}")
            elif month_filter != "All months":
                st.sidebar.success(f"✅ {len(available_dates)} dates with {filter_desc} in {month_filter}")
            else:
                st.sidebar.info(f"📊 Showing {len(available_dates)} dates with {filter_desc}")
            
            # Show example of filtered dates
            if available_dates and len(available_dates) <= 10:
                st.sidebar.markdown("**🗓️ Matching dates:**")
                for date in sorted(available_dates):
                    count = pixel_data[date]
                    try:
                        import datetime
                        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                        month_name = date_obj.strftime('%b')
                        st.sidebar.write(f"• {date} ({month_name}) - {count}px")
                    except:
                        st.sidebar.write(f"• {date} - {count}px")
        else:
            available_dates = all_available_dates
            st.sidebar.info("💡 Click 'Analyze Pixel Counts' to filter dates by pixel availability")
        
        # Show current quality settings
        with st.sidebar:
            filter_status = "None" if not st.session_state.pixel_analysis_data else filter_option if 'filter_option' in locals() else "Analysis completed"
            st.info(f"📊 **Current Settings:**\n- Product: {selected_product}\n- Quality: {qa_option}\n- Filter: {filter_status}")
        
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
            albedo_map = create_albedo_map(date_data, selected_date, product=selected_product, qa_threshold=qa_threshold)
        else:
            # Show all or recent data
            albedo_map = create_albedo_map(df_data_copy, product=selected_product, qa_threshold=qa_threshold)
        
        # Display the map prominently at the top
        # Note: Browser security warnings for streamlit-folium are normal and can be ignored
        try:
            map_data = st_folium(albedo_map, width=900, height=600, returned_objects=["last_object_clicked"])
        except Exception as e:
            st.error(f"Map display error: {e}")
            st.info("This is likely a temporary issue. Try refreshing the page.")
        
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
        ["MCD43A3 Spectral", "MOD10A1/MYD10A1 Melt Season", "Hypsometric", "📊 Statistical Analysis", "🎨 Interactive Albedo Map"]
    )
    
    # Load data based on selection
    if selected_dataset == "MCD43A3 Spectral":
        with st.spinner("Loading MCD43A3 data..."):
            config = get_data_source_info()['mcd43a3']
            from src.utils.data_loader import load_data_from_url
            df, source = load_data_from_url(config['url'], config['local_fallback'], show_status=False)
        
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
    
    elif selected_dataset == "📊 Statistical Analysis":
        # Load melt season data for statistical analysis
        with st.spinner("Loading data for statistical analysis..."):
            melt_data = load_all_melt_season_data(show_status=False)
            hyps_data = load_hypsometric_data(show_status=False)
        
        # Create statistical analysis dashboard
        create_statistical_analysis_dashboard(
            melt_data['time_series'], 
            melt_data['results'], 
            hyps_data['time_series'] if hyps_data else None
        )
    
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