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
from src.utils.realtime_extraction import (
    extract_modis_time_series_realtime, 
    compare_qa_levels_realtime,
    get_qa_level_info
)
from src.dashboards.mcd43a3_dashboard import create_mcd43a3_dashboard
from src.dashboards.melt_season_dashboard import create_melt_season_dashboard
from src.dashboards.statistical_analysis_dashboard import create_statistical_analysis_dashboard
from src.dashboards.realtime_qa_dashboard import create_realtime_qa_dashboard
from src.utils.maps import create_albedo_map
from src.utils.qa_config import (
    create_qa_selector, 
    apply_qa_filtering, 
    create_qa_comparison_widget,
    display_qa_comparison_stats,
    create_qa_impact_visualization,
    QA_LEVELS
)

# Page configuration
st.set_page_config(
    page_title="Athabasca Glacier Albedo Dashboard",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def create_interactive_data_table_dashboard(df_data):
    """
    Create interactive data table with search, filter, and export capabilities
    """
    st.markdown("#### 📋 Interactive Data Table")
    st.markdown("*Excel-style data exploration and analysis*")
    
    if df_data.empty:
        st.warning("No data available for the table")
        return
    
    # Prepare data for the table
    table_data = df_data.copy()
    
    # Check available columns and determine date column
    available_columns = table_data.columns.tolist()
    
    # Debug: Show available columns
    with st.expander("🔍 Debug: Available Data Columns", expanded=False):
        st.write("Available columns:", available_columns)
        st.write("Data shape:", table_data.shape)
        if not table_data.empty:
            st.write("First few rows:")
            st.dataframe(table_data.head())
    
    # Find the date column (could be 'date', 'date_str', etc.)
    date_column = None
    for col in ['date_str', 'date', 'observation_date']:
        if col in available_columns:
            date_column = col
            break
    
    if date_column is None:
        st.error(f"No date column found in the data. Available columns: {available_columns}")
        return
    
    # Create date_str column if it doesn't exist
    if 'date_str' not in available_columns:
        if 'date' in available_columns:
            # Convert date to string format
            table_data['date_str'] = pd.to_datetime(table_data['date']).dt.strftime('%Y-%m-%d')
        else:
            st.error("Unable to create date string column")
            return
    
    # Count observations per date (this is what we have in the data)
    pixel_counts_per_date = table_data.groupby('date_str').size().reset_index(name='observations_count')
    table_data = table_data.merge(pixel_counts_per_date, on='date_str', how='left')
    
    # Select relevant columns that exist in the data
    columns_to_show = ['date_str', 'albedo_mean']
    
    # Add optional columns if they exist
    if 'albedo_std' in available_columns:
        columns_to_show.append('albedo_std')
    if 'elevation' in available_columns:
        columns_to_show.append('elevation')
    
    # Always add observations count
    columns_to_show.append('observations_count')
    
    # Create display dataframe
    display_df = table_data[columns_to_show].copy()
    
    # Rename columns for clarity
    column_names = ['Date', 'Mean Albedo']
    if 'albedo_std' in columns_to_show:
        column_names.append('Std Dev')
    if 'elevation' in columns_to_show:
        column_names.append('Elevation (m)')
    column_names.append('Observations')
    
    display_df.columns = column_names
    
    # Round numeric columns
    if 'Mean Albedo' in display_df.columns:
        display_df['Mean Albedo'] = display_df['Mean Albedo'].round(4)
    if 'Std Dev' in display_df.columns:
        display_df['Std Dev'] = display_df['Std Dev'].round(4)
    if 'Elevation (m)' in display_df.columns:
        display_df['Elevation (m)'] = display_df['Elevation (m)'].round(1)
    
    # Add year and month columns for easier filtering
    display_df['Year'] = pd.to_datetime(display_df['Date']).dt.year
    display_df['Month'] = pd.to_datetime(display_df['Date']).dt.strftime('%b')  # Abbreviated month names
    
    # Reorder columns
    col_order = ['Date', 'Year', 'Month', 'Mean Albedo']
    if 'Std Dev' in display_df.columns:
        col_order.append('Std Dev')
    if 'Elevation (m)' in display_df.columns:
        col_order.append('Elevation (m)')
    col_order.append('Observations')
    display_df = display_df[col_order]
    
    # Table options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        show_full_data = st.checkbox("Show all rows", value=False, help="Display all data (may be slow for large datasets)")
    with col2:
        enable_download = st.checkbox("Enable CSV download", value=True)
    with col3:
        search_term = st.text_input("🔍 Search table:", placeholder="Type to search...")
    
    # Apply search filter
    if search_term:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = display_df[mask]
        st.info(f"Found {len(filtered_df)} matching rows")
    else:
        filtered_df = display_df
    
    # Display the interactive table
    if show_full_data:
        # Show all data with advanced features
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=600,
            column_config={
                "Date": st.column_config.DateColumn(
                    "Date",
                    help="Observation date",
                    format="YYYY-MM-DD",
                    width=90,
                ),
                "Year": st.column_config.NumberColumn(
                    "Year",
                    help="Year",
                    width=50,
                ),
                "Month": st.column_config.TextColumn(
                    "Month",
                    help="Month name",
                    width=60,
                ),
                "Mean Albedo": st.column_config.NumberColumn(
                    "Mean Albedo",
                    help="Average albedo value",
                    format="%.3f",
                    min_value=0,
                    max_value=1,
                    width=70,
                ),
                "Std Dev": st.column_config.NumberColumn(
                    "Std Dev",
                    help="Standard deviation",
                    format="%.3f",
                    width=60,
                ) if 'Std Dev' in filtered_df.columns else None,
                "Elevation (m)": st.column_config.NumberColumn(
                    "Elevation (m)",
                    help="Elevation in meters",
                    format="%.0f",
                    width=60,
                ) if 'Elevation (m)' in filtered_df.columns else None,
                "Observations": st.column_config.NumberColumn(
                    "Observations",
                    help="Number of observations for this date",
                    width=70,
                ),
            },
            hide_index=True,
        )
    else:
        # Show paginated data
        rows_per_page = 50
        total_pages = len(filtered_df) // rows_per_page + (1 if len(filtered_df) % rows_per_page > 0 else 0)
        
        page = st.number_input(
            f"Page (1-{total_pages})", 
            min_value=1, 
            max_value=max(1, total_pages), 
            value=1
        )
        
        start_idx = (page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        
        st.dataframe(
            filtered_df.iloc[start_idx:end_idx],
            use_container_width=True,
            height=400,
            column_config={
                "Date": st.column_config.DateColumn(
                    "Date",
                    help="Observation date",
                    format="YYYY-MM-DD",
                    width=90,
                ),
                "Year": st.column_config.NumberColumn(
                    "Year",
                    help="Year",
                    width=50,
                ),
                "Month": st.column_config.TextColumn(
                    "Month",
                    help="Month name",
                    width=60,
                ),
                "Mean Albedo": st.column_config.NumberColumn(
                    "Mean Albedo",
                    help="Average albedo value",
                    format="%.3f",
                    min_value=0,
                    max_value=1,
                    width=70,
                ),
                "Std Dev": st.column_config.NumberColumn(
                    "Std Dev",
                    help="Standard deviation",
                    format="%.3f",
                    width=60,
                ) if 'Std Dev' in filtered_df.columns else None,
                "Elevation (m)": st.column_config.NumberColumn(
                    "Elevation (m)",
                    help="Elevation in meters",
                    format="%.0f",
                    width=60,
                ) if 'Elevation (m)' in filtered_df.columns else None,
                "Observations": st.column_config.NumberColumn(
                    "Observations",
                    help="Number of observations for this date",
                    width=70,
                ),
            },
            hide_index=True,
        )
        
        st.caption(f"Showing rows {start_idx + 1} to {min(end_idx, len(filtered_df))} of {len(filtered_df)} total rows")
    
    # Download button
    if enable_download:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download filtered data as CSV",
            data=csv,
            file_name=f"athabasca_albedo_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def create_williamson_menounos_dashboard(df_data, df_results, df_focused, qa_config=None, qa_level=None):
    """
    Create comprehensive MOD10A1/MYD10A1 melt season analysis dashboard
    Following Williamson & Menounos 2021 methodology
    
    Now using the full implementation from src/dashboards/melt_season_dashboard.py
    """
    # Show QA info if provided
    if qa_config and qa_level:
        st.info(f"📊 **Quality Filtering:** {qa_level} - {qa_config['modis_snow']['description']}")
    
    # Use the complete melt season dashboard
    create_melt_season_dashboard(df_data, df_results, df_focused)
    
    # Add interactive data table as a sub-section
    st.markdown("---")
    create_interactive_data_table_dashboard(df_data)


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
        
        # Get all available dates first
        all_available_dates = sorted(df_data_copy['date_str'].unique())
        
        # Pixel analysis and filtering
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
        else:
            analyze_pixels = False
            # Clear previous analysis if disabled
            if 'pixel_analysis_data' in st.session_state:
                st.session_state.pixel_analysis_data = None
            st.sidebar.info("💡 Pixel filtering disabled. All available dates will be shown.")
        
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
                            total_dates = len(all_available_dates)
                            st.info(f"🔍 Analyzing {len(sample_dates)} sample dates from {total_dates} total available dates across {len(analyzed_years)} years")
                            
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
        if use_pixel_analysis and st.session_state.pixel_analysis_data:
            pixel_data = st.session_state.pixel_analysis_data
            
            # Show compact pixel analysis summary
            st.sidebar.markdown("**📊 Pixel Analysis Summary:**")
            
            # Calculate statistics
            pixel_counts = list(pixel_data.values())
            analyzed_dates = len(pixel_data)
            total_available = len(all_available_dates)
            avg_pixels = sum(pixel_counts) / len(pixel_counts) if pixel_counts else 0
            max_pixels = max(pixel_counts) if pixel_counts else 0
            min_pixels = min(pixel_counts) if pixel_counts else 0
            
            # Count dates by pixel ranges
            zero_pixels = sum(1 for count in pixel_counts if count == 0)
            low_pixels = sum(1 for count in pixel_counts if 1 <= count <= 5)
            med_pixels = sum(1 for count in pixel_counts if 6 <= count <= 15)
            high_pixels = sum(1 for count in pixel_counts if count > 15)
            
            # Compact summary display
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Analyzed", f"{analyzed_dates}/{total_available}")
                st.metric("Avg Pixels", f"{avg_pixels:.1f}")
            with col2:
                st.metric("Max Pixels", max_pixels)
                st.metric("Min Pixels", min_pixels)
            
            # Note about sampling
            st.sidebar.caption(f"*Note: Analyzed {analyzed_dates} sample dates from {total_available} total dates for performance*")
            
            # Distribution summary
            st.sidebar.markdown("**🎯 Distribution:**")
            st.sidebar.write(f"🔴 0 pixels: {zero_pixels} dates")
            st.sidebar.write(f"🟡 1-5 pixels: {low_pixels} dates") 
            st.sidebar.write(f"🟠 6-15 pixels: {med_pixels} dates")
            st.sidebar.write(f"🟢 15+ pixels: {high_pixels} dates")
            
            # Optional detailed view
            with st.sidebar.expander("📋 View All Dates (Optional)", expanded=False):
                sorted_pixel_data = sorted(pixel_data.items(), key=lambda x: x[1], reverse=True)
                for date, count in sorted_pixel_data[:20]:  # Limit to first 20
                    try:
                        import datetime
                        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                        month_name = date_obj.strftime('%b')
                        
                        if count == 0:
                            st.write(f"🔴 {date} ({month_name}) - {count}px")
                        elif count <= 5:
                            st.write(f"🟡 {date} ({month_name}) - {count}px")
                        elif count <= 15:
                            st.write(f"🟠 {date} ({month_name}) - {count}px")
                        else:
                            st.write(f"🟢 {date} ({month_name}) - {count}px")
                    except:
                        st.write(f"• {date} - {count}px")
                
                if len(sorted_pixel_data) > 20:
                    st.write(f"... and {len(sorted_pixel_data) - 20} more dates")
            
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
            
            # Show compact filter results
            if available_dates:
                if len(available_dates) <= 5:
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
                elif len(available_dates) <= 15:
                    with st.sidebar.expander(f"🗓️ View {len(available_dates)} matching dates", expanded=False):
                        for date in sorted(available_dates):
                            count = pixel_data[date]
                            try:
                                import datetime
                                date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                                month_name = date_obj.strftime('%b')
                                st.write(f"• {date} ({month_name}) - {count}px")
                            except:
                                st.write(f"• {date} - {count}px")
                else:
                    st.sidebar.info(f"📅 {len(available_dates)} matching dates found. Use date selectors below to choose.")
        else:
            available_dates = all_available_dates
            if use_pixel_analysis:
                st.sidebar.info("💡 Click 'Analyze Pixel Counts' to filter dates by pixel availability")
            else:
                st.sidebar.info(f"📅 Showing all {len(available_dates)} available dates")
        
        # Show current quality settings
        with st.sidebar:
            filter_status = "None" if not st.session_state.pixel_analysis_data else "Analysis completed"
            current_qa = qa_level if qa_level else "Default"
            st.info(f"📊 **Current Settings:**\n- Product: {selected_product}\n- QA Level: {current_qa}\n- Quality: {qa_option}\n- Filter: {filter_status}")
        
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
                else:
                    st.sidebar.warning("No dates available with current filters")
                    selected_date = None
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
            if visualization_mode == "Specific Date" and selected_date:
                st.caption(f"""
                **Figure:** MODIS {selected_product} albedo pixels for {selected_date}. Each polygon represents a 500m × 500m MODIS pixel 
                with albedo values color-coded according to the legend. Red boundary indicates glacier extent from 2023 mask.
                """)
            else:
                # Show message about needing to select a specific date
                if use_pixel_analysis and st.session_state.pixel_analysis_data:
                    st.info("💡 **To view MODIS pixels:** Select a specific date from the filtered results using the date selection controls above.")
                st.caption(f"""
                **Figure:** Athabasca Glacier boundary. Select a specific date to view MODIS albedo pixels with real-time Earth Engine data.
                """)
        
        with info_col:
            # Analysis information panel
            st.markdown("#### 📋 Analysis Details")
            
            # Current analysis info
            if visualization_mode == "Specific Date" and selected_date:
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
            
            **🔧 Quality:**  
            {qa_option}
            
            **📅 Period:**  
            Multi-year MODIS time series
            """)
            
            # Additional analysis info if pixel filtering is active
            if use_pixel_analysis and st.session_state.pixel_analysis_data:
                st.markdown("---")
                st.markdown("#### 📊 Pixel Analysis")
                
                pixel_data = st.session_state.pixel_analysis_data
                pixel_counts = list(pixel_data.values())
                total_dates = len(pixel_data)
                avg_pixels = sum(pixel_counts) / len(pixel_counts) if pixel_counts else 0
                
                st.markdown(f"""
                **Total Analyzed:** {total_dates} dates  
                **Average Pixels:** {avg_pixels:.1f}  
                **Range:** {min(pixel_counts) if pixel_counts else 0} - {max(pixel_counts) if pixel_counts else 0}
                """)
            
            # Current filter status
            if len(available_dates) != len(all_available_dates):
                st.markdown("---")
                st.markdown("#### 🎯 Current Filter")
                st.markdown(f"""
                **Showing:** {len(available_dates)} of {len(all_available_dates)} dates
                """)
                if use_pixel_analysis and 'filter_desc' in locals():
                    st.markdown(f"**Criteria:** {filter_desc}")
                if 'selected_years' in locals() and selected_years:
                    years_text = ', '.join(map(str, sorted(selected_years)))
                    st.markdown(f"**Years:** {years_text}")
                if 'month_filter' in locals() and month_filter != "All months":
                    st.markdown(f"**Month:** {month_filter}")
        
        st.markdown("---")
        
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
    
    # QA Level Selection - DISABLED FOR NOW
    # selected_qa_level, qa_config = create_qa_selector()
    # Use default QA settings
    selected_qa_level = "Standard QA"
    qa_config = {
        "description": "Default QA settings",
        "modis_snow": {"qa_threshold": 1, "description": "QA ≤ 1 (best + good quality)"},
        "mcd43a3": {"qa_threshold": 0, "description": "QA = 0 (full BRDF inversions only)"}
    }
    
    # QA Comparison option - DISABLED FOR NOW
    # comparison_levels = create_qa_comparison_widget()
    # show_qa_comparison = len(comparison_levels) > 0
    comparison_levels = []
    show_qa_comparison = False
    
    # Data source selection
    selected_dataset = st.sidebar.selectbox(
        "Analysis Type",
        [
            "MCD43A3 Broadband Albedo",
            "MOD10A1/MYD10A1 Daily Snow Albedo", 
            "Hypsometric Analysis",
            "Statistical Analysis",
            "Interactive Albedo Visualization",
            "Real-time QA Comparison"
        ]
    )
    
    # Load data based on selection
    if selected_dataset == "MCD43A3 Broadband Albedo":
        with st.spinner("Loading MCD43A3 data..."):
            config = get_data_source_info()['mcd43a3']
            from src.utils.data_loader import load_data_from_url
            df, source = load_data_from_url(config['url'], config['local_fallback'], show_status=False)
        
        if not df.empty:
            # Apply QA filtering for MCD43A3 - DISABLED FOR NOW
            # filtered_df, filtering_stats = apply_qa_filtering(df, 'mcd43a3', qa_config)
            filtered_df = df  # Use original data without QA filtering
            
            # QA comparison disabled for now
            # Show QA comparison if requested
            # if show_qa_comparison:
            #     st.markdown("### 🔧 QA Level Comparison - MCD43A3 Spectral Data")
            #     
            #     # Load data for each comparison level
            #     comparison_data = {}
            #     for comp_level in comparison_levels:
            #         comp_config = QA_LEVELS[comp_level]
            #         comp_df, _ = apply_qa_filtering(df, 'mcd43a3', comp_config, show_stats=False)
            #         comparison_data[comp_level] = comp_df
            #     
            #     # Display comparison
            #     display_qa_comparison_stats(comparison_data, 'mcd43a3')
            #     
            #     # Create visualization
            #     qa_viz = create_qa_impact_visualization(comparison_data, 'mcd43a3')
            #     if qa_viz:
            #         st.plotly_chart(qa_viz, use_container_width=True)
            #     
            #     st.markdown("---")
            
            # Show main dashboard with filtered data
            create_mcd43a3_dashboard(filtered_df, qa_config, selected_qa_level)
    
    elif selected_dataset == "MOD10A1/MYD10A1 Daily Snow Albedo":
        # Load all three datasets for comprehensive analysis (suppress status messages)
        with st.spinner("Loading melt season data..."):
            melt_data = load_all_melt_season_data(show_status=False)
        
        # Apply QA filtering for melt season data - DISABLED FOR NOW
        # if not melt_data['time_series'].empty:
        #     filtered_time_series, filtering_stats = apply_qa_filtering(
        #         melt_data['time_series'], 'modis_snow', qa_config
        #     )
        # else:
        #     filtered_time_series = melt_data['time_series']
        #     
        # if not melt_data['focused'].empty:
        #     filtered_focused, _ = apply_qa_filtering(
        #         melt_data['focused'], 'modis_snow', qa_config, show_stats=False
        #     )
        # else:
        #     filtered_focused = melt_data['focused']
        
        # Use original data without QA filtering
        filtered_time_series = melt_data['time_series']
        filtered_focused = melt_data['focused']
        
        # QA comparison disabled for now
        # Show QA comparison if requested
        # if show_qa_comparison:
        #     st.markdown("### 🔧 QA Level Comparison - MOD10A1/MYD10A1 Melt Season Data")
        #     
        #     # Load data for each comparison level
        #     comparison_data = {}
        #     for comp_level in comparison_levels:
        #         comp_config = QA_LEVELS[comp_level]
        #         comp_df, _ = apply_qa_filtering(
        #             melt_data['time_series'], 'modis_snow', comp_config, show_stats=False
        #         )
        #         comparison_data[comp_level] = comp_df
        #     
        #     # Display comparison
        #     display_qa_comparison_stats(comparison_data, 'modis_snow')
        #     
        #     # Create visualization
        #     qa_viz = create_qa_impact_visualization(comparison_data, 'modis_snow')
        #     if qa_viz:
        #         st.plotly_chart(qa_viz, use_container_width=True)
        #     
        #     st.markdown("---")
        
        # Create comprehensive dashboard with filtered data
        create_williamson_menounos_dashboard(
            filtered_time_series, 
            melt_data['results'], 
            filtered_focused,
            qa_config,
            selected_qa_level
        )
            
    elif selected_dataset == "Hypsometric Analysis":
        # Load both results and data for comprehensive analysis
        hyps_data = load_hypsometric_data()
        
        # Create comprehensive hypsometric dashboard
        create_hypsometric_dashboard(hyps_data['results'], hyps_data['time_series'])
    
    elif selected_dataset == "Statistical Analysis":
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