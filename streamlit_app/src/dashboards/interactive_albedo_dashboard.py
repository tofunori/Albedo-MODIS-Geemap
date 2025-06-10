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
    st.subheader("🎨 Interactive Albedo Map")
    st.markdown("*Real-time MODIS pixel visualization on satellite imagery*")
    
    
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
        selected_product, qa_threshold, qa_option, use_advanced_qa, algorithm_flags, selected_band, diffuse_fraction = _create_sidebar_controls(qa_config, qa_level)
        
        # Get all available dates and handle pixel analysis
        all_available_dates = sorted(df_data_copy['date_str'].unique())
        available_dates, use_pixel_analysis = _handle_pixel_analysis(
            all_available_dates, selected_product, qa_threshold, use_advanced_qa, algorithm_flags
        )
        
        # Date selection interface
        selected_date = _create_date_selection_interface(available_dates, use_pixel_analysis)
        
        # Create and display the map
        map_data = _create_and_display_map(
            df_data_copy, selected_date, selected_product, qa_threshold, 
            use_pixel_analysis, available_dates, all_available_dates,
            use_advanced_qa, algorithm_flags, selected_band, diffuse_fraction
        )
        
        # Show summary statistics
        _show_summary_statistics(df_data_copy, selected_date, selected_product, qa_threshold, use_advanced_qa, algorithm_flags)
    
    else:
        st.error("No albedo data available for visualization")
        st.info("Please ensure hypsometric analysis has been run and data is available.")


def _create_sidebar_controls(qa_config, qa_level):
    """Create clean, academic sidebar controls"""
    st.sidebar.header("📊 Analysis Parameters")
    
    # 1. MODIS Product Selection
    st.sidebar.subheader("Data Source")
    product_options = {
        "MOD10A1 (Daily Snow)": "MOD10A1",
        "MCD43A3 (Broadband)": "MCD43A3"
    }
    
    selected_product_name = st.sidebar.radio(
        "MODIS Product:",
        list(product_options.keys()),
        index=1,  # Default to MCD43A3 (Broadband)
        key="product_selector"
    )
    selected_product = product_options[selected_product_name]
    
    # Band selection for MCD43A3
    selected_band = None  # Initialize for all products
    if selected_product == "MCD43A3":
        st.sidebar.subheader("Band Selection")
        
        band_options = {
            "Shortwave (0.3-5.0 μm)": "shortwave",
            "Visible (0.3-0.7 μm)": "vis",
            "Near-Infrared (0.7-5.0 μm)": "nir"
        }
        
        selected_band_name = st.sidebar.radio(
            "Spectral Band:",
            list(band_options.keys()),
            index=0,
            help="Shortwave: Full spectrum (recommended)\nVisible: Sensitive to contamination\nNIR: Less affected by impurities",
            key="mcd43a3_band_selector"
        )
        selected_band = band_options[selected_band_name]
        
        # Diffuse fraction control for Blue-Sky albedo calculation
        st.sidebar.markdown("**Atmospheric Conditions:**")
        diffuse_fraction = st.sidebar.slider(
            "Diffuse Fraction:",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            help="0.0 = Pure direct (clear sky)\n0.2 = Typical glacier (default)\n0.5 = Mixed conditions\n1.0 = Pure diffuse (overcast)",
            key="diffuse_fraction_slider"
        )
        
        # Show interpretation
        if diffuse_fraction <= 0.15:
            condition = "☀️ Clear sky conditions"
        elif diffuse_fraction <= 0.35:
            condition = "🌤️ Typical glacier conditions"
        elif diffuse_fraction <= 0.65:
            condition = "⛅ Mixed sky conditions"
        else:
            condition = "☁️ Overcast conditions"
        
        st.sidebar.caption(f"{condition} (BSA: {(1-diffuse_fraction)*100:.0f}%, WSA: {diffuse_fraction*100:.0f}%)")
    else:
        diffuse_fraction = None
    
    # 2. Quality Level (simplified)
    st.sidebar.subheader("Quality Control")
    
    if selected_product == "MOD10A1":
        qa_levels = ["Strict (QA=0)", "Standard (QA≤1)", "Relaxed (QA≤2)"]
        qa_values = [0, 1, 2]
        default_idx = 1  # Standard
        
        selected_qa_idx = st.sidebar.selectbox(
            "Quality Level:",
            range(len(qa_levels)),
            index=default_idx,
            format_func=lambda x: qa_levels[x],
            key="qa_level_selector"
        )
        
        qa_threshold = qa_values[selected_qa_idx]
        qa_option = qa_levels[selected_qa_idx]
        
        # Advanced options (collapsible)
        with st.sidebar.expander("⚙️ Advanced Filters", expanded=False):
            use_advanced_qa = st.checkbox("Enable Algorithm Flags", key="advanced_qa_toggle")
            
            algorithm_flags = {}
            if use_advanced_qa:
                # All flags in simple list with detailed help tooltips
                algorithm_flags['no_inland_water'] = st.checkbox(
                    "🌊 Inland Water", value=False,
                    help="Bit 0: Excludes pixels flagged as inland water bodies. Recommended for glacier analysis."
                )
                algorithm_flags['no_low_visible'] = st.checkbox(
                    "📉 Low Visible Reflectance", value=False,
                    help="Bit 1: Excludes pixels with low visible band reflectance. May indicate poor illumination or sensor issues."
                )
                algorithm_flags['no_low_ndsi'] = st.checkbox(
                    "❄️ Low NDSI", value=False,
                    help="Bit 2: Excludes pixels with low NDSI (Normalized Difference Snow Index). NDSI < 0.4 indicates non-snow surfaces."
                )
                algorithm_flags['no_temp_issues'] = st.checkbox(
                    "🌡️ Temperature/Height Screen", value=False,
                    help="Bit 3: Excludes pixels failing temperature or elevation tests. Filters unrealistic snow conditions."
                )
                algorithm_flags['no_high_swir'] = st.checkbox(
                    "🔆 High SWIR Reflectance", value=False,
                    help="Bit 4: Excludes pixels with high short-wave infrared reflectance. May indicate non-snow surfaces or ice."
                )
                algorithm_flags['no_clouds'] = st.checkbox(
                    "☁️ Cloud Detected", value=True,
                    help="Bit 5: Excludes pixels flagged as cloudy. Essential for accurate albedo measurements."
                )
                algorithm_flags['no_cloud_clear'] = st.checkbox(
                    "🌤️ Cloud/Clear Confidence", value=False,
                    help="Bit 6: Excludes pixels with low cloud/clear confidence. Additional cloud screening beyond basic detection."
                )
                algorithm_flags['no_shadows'] = st.checkbox(
                    "🌑 Low Illumination/Shadows", value=True,
                    help="Bit 7: Excludes pixels with poor illumination or shadowing effects. Critical for albedo accuracy."
                )
                
                # Count active filters
                active_count = sum(algorithm_flags.values())
                if active_count > 0:
                    st.info(f"✓ {active_count} filters active")
    else:
        # MCD43A3
        qa_levels = ["Full BRDF (QA=0)", "Include Magnitude (QA≤1)"]
        qa_values = [0, 1]
        
        selected_qa_idx = st.sidebar.selectbox(
            "Quality Level:",
            range(len(qa_levels)),
            index=1,  # Default to QA≤1 (Include Magnitude)
            format_func=lambda x: qa_levels[x],
            key="qa_level_mcd43a3"
        )
        
        qa_threshold = qa_values[selected_qa_idx]
        qa_option = qa_levels[selected_qa_idx]
        use_advanced_qa = False
        algorithm_flags = {}
    
    # 3. Current Configuration (minimal)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Current Setup:**")
    st.sidebar.text(f"Product: {selected_product}")
    st.sidebar.text(f"Quality: {qa_option}")
    
    return selected_product, qa_threshold, qa_option, use_advanced_qa, algorithm_flags, selected_band, diffuse_fraction


def _handle_pixel_analysis(all_available_dates, selected_product, qa_threshold, use_advanced_qa=False, algorithm_flags={}):
    """Handle pixel count analysis (simplified)"""
    # Simplified pixel analysis in expander
    with st.sidebar.expander("🔍 Pixel Analysis", expanded=False):
        use_pixel_analysis = st.checkbox(
            "Filter by pixel availability",
            value=False,
            key="use_pixel_analysis"
        )
    
        if use_pixel_analysis:
            # Create unique key based on QA settings to detect changes
            qa_key = f"{selected_product}_{qa_threshold}_{use_advanced_qa}_{hash(str(sorted(algorithm_flags.items())))}"
            
            # Check if QA settings have changed
            if 'previous_qa_key' not in st.session_state or st.session_state.previous_qa_key != qa_key:
                st.session_state.pixel_analysis_data = None  # Clear old analysis
                st.session_state.previous_qa_key = qa_key
                st.info("⚠️ QA settings changed - analysis needs to be updated")
            
            analyze_pixels = st.button("Analyze Dates", key="analyze_pixels_btn")
            
            if analyze_pixels:
                available_dates = _perform_pixel_analysis(all_available_dates, selected_product, qa_threshold, use_advanced_qa, algorithm_flags)
            else:
                available_dates = _get_filtered_dates_from_analysis(all_available_dates)
        else:
            available_dates = all_available_dates
    
    if not use_pixel_analysis:
        # Clear previous analysis if disabled
        if 'pixel_analysis_data' in st.session_state:
            st.session_state.pixel_analysis_data = None
        available_dates = all_available_dates
    
    return available_dates, use_pixel_analysis


def _perform_pixel_analysis(all_available_dates, selected_product, qa_threshold, use_advanced_qa=False, algorithm_flags={}):
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
                            pixel_count = count_modis_pixels_for_date(date, athabasca_roi, selected_product, qa_threshold, use_advanced_qa, algorithm_flags)
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
    """Load glacier boundary from shapefile (preferred) or GeoJSON file"""
    import json
    
    # PRIORITY 1: Try to load from shapefile (most accurate)
    shapefile_paths = [
        '../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # New organized path
        '../../data/geospatial/shapefiles/Masque_athabasca_2023_Arcgis.shp',  # Alternative organized path
    ]
    
    for shp_path in shapefile_paths:
        try:
            import geopandas as gpd
            
            # Load shapefile with geopandas
            gdf = gpd.read_file(shp_path)
            
            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            
            # Convert to GeoJSON for compatibility
            glacier_geojson = json.loads(gdf.to_json())
            
            return glacier_geojson
            
        except ImportError:
            # Geopandas not available, continue to GeoJSON fallback
            continue
        except Exception:
            # Shapefile loading failed, continue to GeoJSON fallback
            continue
    
    # PRIORITY 2: Fallback to GeoJSON files
    geojson_paths = [
        '../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # New organized path
        '../../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',  # Alternative organized path
        '../Athabasca_mask_2023_cut.geojson',  # Legacy fallback
        '../../Athabasca_mask_2023_cut.geojson',  # Legacy fallback
        'Athabasca_mask_2023_cut.geojson'  # Same directory fallback
    ]
    
    for path in geojson_paths:
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
    """Create simplified date selection"""
    st.sidebar.subheader("Date Selection")
    
    # Default to list picker (more reliable)
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
                           use_pixel_analysis, available_dates, all_available_dates,
                           use_advanced_qa=False, algorithm_flags={}, selected_band=None, diffuse_fraction=None):
    """Create and display the albedo map"""
    from src.utils.maps import create_albedo_map
    
    # Create albedo map
    if selected_date:
        # Filter for specific date
        date_data = df_data_copy[df_data_copy['date_str'] == selected_date]
        albedo_map = create_albedo_map(
            date_data, selected_date, 
            product=selected_product, 
            qa_threshold=qa_threshold,
            use_advanced_qa=use_advanced_qa,
            algorithm_flags=algorithm_flags,
            selected_band=selected_band,
            diffuse_fraction=diffuse_fraction
        )
    else:
        # When pixel filtering is active, don't show fallback points
        # Show only glacier boundary instead of confusing representative points
        albedo_map = create_albedo_map(
            pd.DataFrame(), None, 
            product=selected_product, 
            qa_threshold=qa_threshold,
            use_advanced_qa=use_advanced_qa,
            algorithm_flags=algorithm_flags,
            diffuse_fraction=diffuse_fraction
        )
    
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


def _show_summary_statistics(df_data_copy, selected_date, selected_product=None, qa_threshold=1, use_advanced_qa=False, algorithm_flags={}):
    """Show comprehensive summary statistics below the map"""
    
    # If a specific date is selected, get real-time filtered data from Google Earth Engine
    if selected_date and selected_product:
        display_data = _get_realtime_statistics(selected_date, selected_product, qa_threshold, use_advanced_qa, algorithm_flags)
        title_suffix = f"for {selected_date} (Real-time GEE Data)"
        
        # Fallback to CSV data if GEE fails
        if display_data is None or display_data.empty:
            display_data = df_data_copy[df_data_copy['date_str'] == selected_date]
            title_suffix = f"for {selected_date} (CSV Fallback)"
    else:
        display_data = df_data_copy
        title_suffix = "(All CSV Data)"
    
    if not display_data.empty:
        # Enhanced header with status indicator
        if title_suffix and "Real-time" in title_suffix:
            status_indicator = "🟢 Live GEE"
            date_part = title_suffix.split("(")[0].strip()
        else:
            status_indicator = "🟡 Cached"
            date_part = title_suffix.replace("(All CSV Data)", "Multi-temporal")
            
        st.markdown(f"### 📊 **Statistical Summary** {date_part}")
        st.markdown(f"<div style='text-align: center; color: #666; margin-bottom: 15px;'>{status_indicator}</div>", unsafe_allow_html=True)
        
        # Professional statistics layout with better formatting
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown("#### 📈 **Descriptive**")
            n_obs = len(display_data)
            mean_albedo = display_data['albedo_mean'].mean()
            std_albedo = display_data['albedo_mean'].std()
            cv = (std_albedo/mean_albedo)*100
            
            # Enhanced display with better formatting
            st.markdown(f"""
            <div style='font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;'>
            <b>n</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {n_obs:>6}<br>
            <b>μ</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {mean_albedo:>6.4f}<br>
            <b>σ</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {std_albedo:>6.4f}<br>
            <b>CV</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {cv:>6.1f}%
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📊 **Distribution**")
            median_albedo = display_data['albedo_mean'].median()
            q25 = display_data['albedo_mean'].quantile(0.25)
            q75 = display_data['albedo_mean'].quantile(0.75)
            iqr = q75 - q25
            min_albedo = display_data['albedo_mean'].min()
            max_albedo = display_data['albedo_mean'].max()
            
            st.markdown(f"""
            <div style='font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;'>
            <b>Median</b>&nbsp;&nbsp; = {median_albedo:>6.4f}<br>
            <b>IQR</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {iqr:>6.4f}<br>
            <b>Min</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {min_albedo:>6.4f}<br>
            <b>Max</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = {max_albedo:>6.4f}
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("#### 🎯 **Quality**")
            # High albedo percentage (>0.3 for snow/ice)
            high_albedo_pct = (display_data['albedo_mean'] > 0.3).mean() * 100
            # Data completeness
            completeness = (1 - display_data['albedo_mean'].isna().mean()) * 100
            
            if 'pixel_count' in display_data.columns:
                pixels = display_data['pixel_count'].iloc[0] if len(display_data) > 0 else len(display_data)
            else:
                pixels = len(display_data)
            
            # QA status with color coding
            if title_suffix and "Real-time" in title_suffix:
                qa_status = "✅ Applied"
                qa_color = "#28a745"
            else:
                qa_status = "⚠️ Cached"
                qa_color = "#ffc107"
            
            st.markdown(f"""
            <div style='font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;'>
            <b>Pixels</b>&nbsp;&nbsp; = {pixels:>6}<br>
            <b>High α</b>&nbsp;&nbsp; = {high_albedo_pct:>6.1f}%<br>
            <b>Complete</b> = {completeness:>6.1f}%<br>
            <span style='color: {qa_color}; font-weight: bold;'>QA {qa_status}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Enhanced technical footer
        product_display = selected_product if selected_product else 'MOD10A1'
        st.markdown("---")
        st.markdown(f"""
        <div style='text-align: center; color: #666; font-size: 0.9em; font-style: italic;'>
        <b>Technical:</b> {product_display} • 500m resolution • Athabasca Glacier<br>
        {"Real-time Earth Engine processing" if "Real-time" in title_suffix else "Pre-processed CSV data"}
        </div>
        """, unsafe_allow_html=True)


def _get_realtime_statistics(selected_date, selected_product, qa_threshold, use_advanced_qa, algorithm_flags):
    """Get real-time statistics from Google Earth Engine with current QA settings"""
    try:
        from src.utils.ee_utils import initialize_earth_engine, get_modis_pixels_for_date, get_roi_from_geojson
        import pandas as pd
        import json
        
        # Check if Earth Engine is available
        ee_available = initialize_earth_engine()
        if not ee_available:
            return None
            
        # Load glacier boundary
        glacier_geojson = _load_glacier_boundary()
        if not glacier_geojson:
            return None
            
        athabasca_roi = get_roi_from_geojson(glacier_geojson)
        
        # Get MODIS pixels with current QA settings (silent mode for statistics)
        modis_pixels = get_modis_pixels_for_date(
            selected_date, athabasca_roi, selected_product, qa_threshold,
            use_advanced_qa=use_advanced_qa, algorithm_flags=algorithm_flags, silent=True
        )
        
        if modis_pixels and 'features' in modis_pixels:
            # Extract albedo values from GEE response
            albedo_values = []
            for feature in modis_pixels['features']:
                if 'properties' in feature and 'albedo_value' in feature['properties']:
                    albedo_value = feature['properties']['albedo_value']
                    if albedo_value is not None and 0 <= albedo_value <= 1:
                        albedo_values.append(albedo_value)
            
            if albedo_values:
                # Create DataFrame with real-time data
                realtime_data = pd.DataFrame({
                    'albedo_mean': albedo_values,
                    'date_str': [selected_date] * len(albedo_values),
                    'pixel_count': [len(albedo_values)] * len(albedo_values)
                })
                return realtime_data
                
    except Exception as e:
        # Silent fallback - no error message to keep UI clean
        pass
        
    return None