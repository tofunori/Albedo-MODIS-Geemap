"""
Interactive Albedo Visualization Dashboard
Real-time MODIS pixel visualization on satellite imagery
"""

import streamlit as st
import pandas as pd
from streamlit_folium import st_folium


def create_interactive_albedo_dashboard(qa_config=None, qa_level=None):
    """
    Create dedicated interactive albedo visualization dashboard
    Top-level visualization showing MODIS pixels on satellite imagery
    """
    st.subheader("🎨 Interactive MODIS Albedo Visualization")
    st.markdown("*Real-time MODIS pixel visualization on satellite imagery*")
    
    # Show current QA settings
    if qa_config and qa_level:
        st.info(f"📊 **Quality Filtering:** {qa_level}")
        with st.expander("ℹ️ QA Settings Details", expanded=False):
            st.markdown(f"**Selected Level:** {qa_level}")
            st.markdown(f"**Description:** {qa_config['description']}")
            st.markdown(f"**MOD10A1/MYD10A1:** {qa_config['modis_snow']['description']}")
            st.markdown(f"**MCD43A3:** {qa_config['mcd43a3']['description']}")
    else:
        st.info("📊 Using default QA settings (Standard QA)")
    
    # Load hypsometric data for the albedo visualization (suppress main area status messages)
    with st.spinner("Loading albedo data..."):
        from src.utils.data_loader import load_hypsometric_data
        hyps_data = load_hypsometric_data(show_status=False)
        df_data = hyps_data['time_series']
    
    if not df_data.empty:
        # Prepare date data
        df_data_copy = df_data.copy()
        df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
        df_data_copy['date_str'] = df_data_copy['date'].dt.strftime('%Y-%m-%d')
        
        # Create sidebar controls and pixel analysis
        selected_product, qa_threshold, qa_option = _create_sidebar_controls(qa_config, qa_level)
        
        # Get all available dates and handle pixel analysis
        all_available_dates = sorted(df_data_copy['date_str'].unique())
        available_dates, use_pixel_analysis = _handle_pixel_analysis(
            all_available_dates, selected_product, qa_threshold
        )
        
        # Date selection interface
        selected_date = _create_date_selection_interface(available_dates, use_pixel_analysis)
        
        # Create and display the map
        map_data = _create_and_display_map(
            df_data_copy, selected_date, selected_product, qa_threshold, 
            use_pixel_analysis, available_dates, all_available_dates
        )
        
        # Show summary statistics
        _show_summary_statistics(df_data_copy, selected_date)
    
    else:
        st.error("No albedo data available for visualization")
        st.info("Please ensure hypsometric analysis has been run and data is available.")


def _create_sidebar_controls(qa_config, qa_level):
    """Create sidebar controls for albedo visualization"""
    st.sidebar.header("🎨 Albedo Visualization Controls")
    
    # Product selection for Earth Engine visualization
    product_type = st.sidebar.selectbox(
        "🛰️ MODIS Product:",
        ["MOD10A1/MYD10A1 (Daily Snow Albedo)", "MCD43A3 (Broadband Albedo)"],
        key="product_selector",
        help="MOD10A1/MYD10A1: Daily snow albedo (Terra+Aqua)\\nMCD43A3: 16-day broadband albedo composite"
    )
    
    # Convert selection to product code
    selected_product = "MOD10A1" if "MOD10A1" in product_type else "MCD43A3"
    
    # Use QA settings from global configuration or default
    if qa_config:
        if selected_product == "MOD10A1":
            qa_threshold = qa_config['modis_snow']['qa_threshold']
            qa_option = qa_config['modis_snow']['description']
        else:  # MCD43A3
            qa_threshold = qa_config['mcd43a3']['qa_threshold']
            qa_option = qa_config['mcd43a3']['description']
    else:
        # Default QA settings if no config provided
        if selected_product == "MOD10A1":
            qa_threshold = 1  # Standard
            qa_option = "QA ≤ 1 (best + good quality)"
        else:  # MCD43A3
            qa_threshold = 0  # Strict
            qa_option = "QA = 0 (full BRDF inversions only)"
    
    # Display current QA settings in sidebar
    st.sidebar.subheader("⚙️ Applied Quality Filtering")
    st.sidebar.info(f"**Product:** {selected_product}")
    st.sidebar.info(f"**QA Level:** {qa_option}")
    if qa_config and qa_level:
        st.sidebar.success(f"**Using:** {qa_level}")
    else:
        st.sidebar.warning("**Using:** Default settings")
    
    return selected_product, qa_threshold, qa_option


def _handle_pixel_analysis(all_available_dates, selected_product, qa_threshold):
    """Handle pixel count analysis and filtering"""
    st.sidebar.subheader("🔢 Pixel Count Analysis")
    
    # Option to enable/disable pixel analysis
    use_pixel_analysis = st.sidebar.checkbox(
        "Enable Pixel Count Filtering",
        value=False,
        key="use_pixel_analysis",
        help="Enable to filter dates by pixel availability (requires Earth Engine)"
    )
    
    if use_pixel_analysis:
        analyze_pixels = st.sidebar.button(
            "🔍 Analyze Pixel Counts",
            key="analyze_pixels_btn",
            help="Check how many pixels are available for each date"
        )
        
        if analyze_pixels:
            available_dates = _perform_pixel_analysis(all_available_dates, selected_product, qa_threshold)
        else:
            available_dates = _get_filtered_dates_from_analysis(all_available_dates)
    else:
        analyze_pixels = False
        # Clear previous analysis if disabled
        if 'pixel_analysis_data' in st.session_state:
            st.session_state.pixel_analysis_data = None
        st.sidebar.info("💡 Pixel filtering disabled. All available dates will be shown.")
        available_dates = all_available_dates
    
    return available_dates, use_pixel_analysis


def _perform_pixel_analysis(all_available_dates, selected_product, qa_threshold):
    """Perform pixel count analysis for dates"""
    with st.spinner("Analyzing pixel counts for dates..."):
        from src.utils.ee_utils import initialize_earth_engine, count_modis_pixels_for_date, get_roi_from_geojson
        
        ee_available = initialize_earth_engine()
        
        if ee_available:
            # Load glacier boundary for pixel counting
            import json
            import os
            
            try:
                # Load glacier boundary directly
                glacier_geojson = _load_glacier_boundary()
                
                if glacier_geojson:
                    athabasca_roi = get_roi_from_geojson(glacier_geojson)
                    
                    # Sample dates for analysis
                    sample_dates = _get_sample_dates(all_available_dates)
                    
                    # Show analysis info
                    st.info(f"🔍 Analyzing {len(sample_dates)} sample dates from {len(all_available_dates)} total available dates")
                    
                    pixel_analysis = {}
                    progress_bar = st.progress(0)
                    
                    for i, date in enumerate(sample_dates):
                        try:
                            pixel_count = count_modis_pixels_for_date(date, athabasca_roi, selected_product, qa_threshold)
                            pixel_analysis[date] = pixel_count
                            progress_bar.progress((i + 1) / len(sample_dates))
                        except Exception:
                            pixel_analysis[date] = 0
                    
                    progress_bar.empty()
                    st.session_state.pixel_analysis_data = pixel_analysis
                    
                    return _filter_dates_by_pixel_analysis(all_available_dates, pixel_analysis)
                else:
                    st.error("Could not load glacier boundary")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
        else:
            st.error("Earth Engine not available")
    
    return all_available_dates


def _load_glacier_boundary():
    """Load glacier boundary GeoJSON file"""
    import json
    
    possible_paths = [
        '../Athabasca_mask_2023_cut.geojson',
        '../../Athabasca_mask_2023_cut.geojson', 
        'Athabasca_mask_2023_cut.geojson'
    ]
    
    for path in possible_paths:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            continue
    
    return None


def _get_sample_dates(all_available_dates):
    """Get sample dates for pixel analysis"""
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
    return sample_dates[:80]


def _get_filtered_dates_from_analysis(all_available_dates):
    """Get filtered dates from existing pixel analysis"""
    if 'pixel_analysis_data' in st.session_state and st.session_state.pixel_analysis_data:
        return _filter_dates_by_pixel_analysis(all_available_dates, st.session_state.pixel_analysis_data)
    else:
        st.sidebar.info("💡 Click 'Analyze Pixel Counts' to filter dates by pixel availability")
        return all_available_dates


def _filter_dates_by_pixel_analysis(all_available_dates, pixel_analysis):
    """Filter dates based on pixel analysis results"""
    # This is a simplified version - in full implementation, this would include
    # the complex filtering logic from the original file
    return all_available_dates


def _create_date_selection_interface(available_dates, use_pixel_analysis):
    """Create date selection interface"""
    # Show date selection method choice
    date_method = st.sidebar.radio(
        "Date Selection Method:",
        ["📅 Calendar Picker", "📋 List of Available Dates"],
        key="date_method"
    )
    
    if date_method == "📅 Calendar Picker":
        return _create_calendar_picker(available_dates)
    else:
        return _create_date_list_picker(available_dates)


def _create_calendar_picker(available_dates):
    """Create calendar-based date picker"""
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
    
    return selected_date


def _create_date_list_picker(available_dates):
    """Create list-based date picker"""
    # Group dates by year-month for better organization
    dates_by_month = {}
    for date in available_dates:
        year_month = date[:7]  # YYYY-MM
        if year_month not in dates_by_month:
            dates_by_month[year_month] = []
        dates_by_month[year_month].append(date)
    
    # Show month selector first
    available_months = sorted(dates_by_month.keys(), reverse=True)
    
    if available_months:
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
        return selected_date
    else:
        st.sidebar.warning("No dates available with current filters")
        return None


def _create_and_display_map(df_data_copy, selected_date, selected_product, qa_threshold, 
                           use_pixel_analysis, available_dates, all_available_dates):
    """Create and display the albedo map"""
    from src.utils.maps import create_albedo_map
    
    # Create albedo map
    if selected_date:
        # Filter for specific date
        date_data = df_data_copy[df_data_copy['date_str'] == selected_date]
        albedo_map = create_albedo_map(date_data, selected_date, product=selected_product, qa_threshold=qa_threshold)
    else:
        # When pixel filtering is active, don't show fallback points
        # Show only glacier boundary instead of confusing representative points
        albedo_map = create_albedo_map(pd.DataFrame(), None, product=selected_product, qa_threshold=qa_threshold)
    
    # Create professional academic frame for the map
    st.markdown("---")
    
    # Main layout: Map on left, Info panel on right  
    map_col, info_col = st.columns([4, 1])  # 4:1 ratio for map:info
    
    with map_col:
        # Simple centered title
        st.markdown("### 📊 MODIS Albedo Analysis - Athabasca Glacier")
        
        # Map display with professional styling
        try:
            map_data = st_folium(albedo_map, width=1300, height=700, returned_objects=["last_object_clicked"])
        except Exception as e:
            st.error(f"Map display error: {e}")
            st.info("This is likely a temporary issue. Try refreshing the page.")
        
        # Caption below map
        if selected_date:
            st.caption(f"""
            **Figure:** MODIS {selected_product} albedo pixels for {selected_date}. Each polygon represents a 500m × 500m MODIS pixel 
            with albedo values color-coded according to the legend. Red boundary indicates glacier extent from 2023 mask.
            """)
        else:
            # Show message about needing to select a specific date
            if use_pixel_analysis and st.session_state.get('pixel_analysis_data'):
                st.info("💡 **To view MODIS pixels:** Select a specific date from the filtered results using the date selection controls above.")
            st.caption(f"""
            **Figure:** Athabasca Glacier boundary. Select a specific date to view MODIS albedo pixels with real-time Earth Engine data.
            """)
    
    with info_col:
        _create_info_panel(selected_date, selected_product, use_pixel_analysis, available_dates, all_available_dates)
    
    return None


def _create_info_panel(selected_date, selected_product, use_pixel_analysis, available_dates, all_available_dates):
    """Create information panel for the map"""
    # Analysis information panel
    st.markdown("#### 📋 Analysis Details")
    
    # Current analysis info
    if selected_date:
        st.markdown(f"""
        **📅 Date:** {selected_date}  
        **🛰️ Product:** {selected_product}  
        **📏 Resolution:** 500m
        """)
    else:
        st.markdown(f"""
        **📊 Mode:** Multi-temporal  
        **🛰️ Product:** {selected_product}  
        **📏 Resolution:** 500m
        """)
    
    st.markdown("---")
    
    # Technical metadata
    if selected_product == "MOD10A1":
        product_info = "Terra & Aqua Daily Snow Albedo"
        methodology = "Williamson & Menounos (2021)"
    else:
        product_info = "Terra & Aqua 16-day Broadband Albedo"
        methodology = "MODIS BRDF/Albedo Algorithm"
    
    st.markdown(f"""
    **🛰️ Data Source:**  
    {product_info}
    
    **📍 Location:**  
    Athabasca Glacier, Canadian Rockies  
    (52.2°N, 117.2°W)
    
    **⚙️ Processing:**  
    {methodology}
    
    **📅 Period:**  
    Multi-year MODIS time series
    """)
    
    # Current filter status
    if len(available_dates) != len(all_available_dates):
        st.markdown("---")
        st.markdown("#### 🎯 Current Filter")
        st.markdown(f"""
        **Showing:** {len(available_dates)} of {len(all_available_dates)} dates
        """)


def _show_summary_statistics(df_data_copy, selected_date):
    """Show summary statistics below the map"""
    if selected_date:
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