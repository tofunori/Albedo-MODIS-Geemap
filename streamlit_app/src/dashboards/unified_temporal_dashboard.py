"""
Unified Temporal Dashboard for MODIS Products
Comparative analysis interface for MOD10A1 and MCD43A3 temporal evolution
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta


def create_unified_temporal_dashboard():
    """
    Create unified temporal analysis dashboard for both MOD10A1 and MCD43A3
    """
    st.title("🕰️ Unified MODIS Temporal Analysis")
    st.markdown("*Comparative temporal evolution analysis between MOD10A1 and MCD43A3*")
    
    # Main analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Product Comparison",
        "⏰ Temporal Evolution", 
        "🎯 Synchronous Analysis",
        "📈 Statistical Comparison"
    ])
    
    with tab1:
        _create_product_comparison_tab()
        
    with tab2:
        _create_temporal_evolution_tab()
        
    with tab3:
        _create_synchronous_analysis_tab()
        
    with tab4:
        _create_statistical_comparison_tab()


def _create_product_comparison_tab():
    """Create product comparison tab"""
    st.subheader("📊 MOD10A1 vs MCD43A3 Product Comparison")
    st.markdown("*Side-by-side comparison of daily snow albedo vs broadband albedo*")
    
    # Add CSV Import functionality for both products
    imported_data = _add_unified_csv_import_interface()
    
    # Product selection and parameters
    with st.sidebar:
        st.markdown("### 🎛️ Comparison Controls")
        
        # Product selection
        products_to_compare = st.multiselect(
            "Select Products",
            ["MOD10A1 (Daily Snow)", "MCD43A3 (Broadband)"],
            default=["MOD10A1 (Daily Snow)", "MCD43A3 (Broadband)"],
            key="comparison_products"
        )
        
        # Melt Season Period Selection (standardized)
        st.markdown("**📅 Melt Season Period**")
        st.caption("*Standardized: June 1 - September 30 following glaciology literature*")
        
        # Year selection for melt season comparison
        available_years = list(range(2010, 2025))
        
        comparison_mode = st.radio(
            "Comparison Period",
            ["Single Melt Season", "Multi-Year Comparison"],
            key="unified_comparison_mode"
        )
        
        if comparison_mode == "Single Melt Season":
            selected_year = st.selectbox(
                "Melt Season Year",
                available_years,
                index=available_years.index(2023),
                key="unified_single_year"
            )
            start_date = datetime(selected_year, 6, 1)
            end_date = datetime(selected_year, 9, 30)
            
        else:  # Multi-Year Comparison
            col1, col2 = st.columns(2)
            with col1:
                start_year = st.selectbox(
                    "Start Year",
                    available_years,
                    index=available_years.index(2020),
                    key="unified_start_year"
                )
            with col2:
                end_year = st.selectbox(
                    "End Year",
                    available_years,
                    index=available_years.index(2023),
                    key="unified_end_year"
                )
            
            if start_year > end_year:
                st.error("Start year must be ≤ end year")
                start_year, end_year = end_year, start_year
            
            start_date = datetime(start_year, 6, 1)
            end_date = datetime(end_year, 9, 30)
        
        # Display selected melt season period
        years_span = end_date.year - start_date.year + 1
        st.info(f"📊 **Melt Season(s)**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({years_span} season{'s' if years_span > 1 else ''})")
        
        # QA settings
        st.markdown("**🔍 Quality Settings**")
        qa_level_display = st.selectbox(
            "Quality Level",
            ["strict", "standard", "relaxed"],
            index=1,
            key="comparison_qa"
        )
        
        # Map display names to internal QA system names
        qa_mapping = {
            "strict": "strict",      # Use direct mapping for extraction function
            "standard": "standard",  # Use direct mapping for extraction function  
            "relaxed": "relaxed"     # Use direct mapping for extraction function
        }
        qa_level = qa_mapping[qa_level_display]
        
        # Extract comparison data
        extract_comparison = st.button(
            "🚀 Extract Comparison Data",
            type="primary",
            key="extract_comparison"
        )
    
    # Main comparison interface
    if extract_comparison and products_to_compare:
        # Add information about the extraction process
        st.info(f"🔄 Starting extraction for {len(products_to_compare)} product(s) from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        _perform_product_comparison(products_to_compare, start_date, end_date, qa_level)
    elif 'comparison_data' in st.session_state:
        _display_comparison_results(st.session_state['comparison_data'])
    else:
        _display_comparison_placeholder()


def _create_temporal_evolution_tab():
    """Create temporal evolution tab"""
    st.subheader("⏰ Temporal Evolution Analysis")
    st.markdown("*Long-term temporal trends for both products*")
    
    # Check if we have comparison data
    if 'comparison_data' in st.session_state:
        comparison_data = st.session_state['comparison_data']
        
        # Evolution analysis controls
        evolution_type = st.selectbox(
            "Evolution Analysis",
            ["Annual Trends", "Seasonal Patterns", "Monthly Comparison", "Detailed Timeline"],
            key="evolution_type"
        )
        
        if evolution_type == "Annual Trends":
            _create_annual_trends_comparison(comparison_data)
        elif evolution_type == "Seasonal Patterns":
            _create_seasonal_patterns_comparison(comparison_data)
        elif evolution_type == "Monthly Comparison":
            _create_monthly_comparison(comparison_data)
        elif evolution_type == "Detailed Timeline":
            _create_detailed_timeline_comparison(comparison_data)
    else:
        st.info("📊 Please extract comparison data in the Product Comparison tab first")


def _create_synchronous_analysis_tab():
    """Create synchronous analysis tab"""
    st.subheader("🎯 Synchronous Analysis")
    st.markdown("*Pixel-level and date-matched analysis between products*")
    
    if 'comparison_data' in st.session_state:
        comparison_data = st.session_state['comparison_data']
        
        # Synchronous analysis options
        sync_analysis = st.selectbox(
            "Synchronous Analysis Type",
            ["Direct Correlation", "Difference Analysis", "Bias Assessment", "Temporal Alignment"],
            key="sync_analysis"
        )
        
        if sync_analysis == "Direct Correlation":
            _create_direct_correlation_analysis(comparison_data)
        elif sync_analysis == "Difference Analysis":
            _create_difference_analysis(comparison_data)
        elif sync_analysis == "Bias Assessment":
            _create_bias_assessment(comparison_data)
        elif sync_analysis == "Temporal Alignment":
            _create_temporal_alignment_analysis(comparison_data)
    else:
        st.info("📊 Please extract comparison data in the Product Comparison tab first")


def _create_statistical_comparison_tab():
    """Create statistical comparison tab"""
    st.subheader("📈 Statistical Comparison")
    st.markdown("*Advanced statistical analysis between products*")
    
    if 'comparison_data' in st.session_state:
        comparison_data = st.session_state['comparison_data']
        
        # Statistical analysis options
        stat_analysis = st.selectbox(
            "Statistical Analysis",
            ["Descriptive Statistics", "Distribution Comparison", "Trend Analysis", "Anomaly Detection"],
            key="stat_analysis"
        )
        
        if stat_analysis == "Descriptive Statistics":
            _create_descriptive_statistics_comparison(comparison_data)
        elif stat_analysis == "Distribution Comparison":
            _create_distribution_comparison(comparison_data)
        elif stat_analysis == "Trend Analysis":
            _create_trend_analysis_comparison(comparison_data)
        elif stat_analysis == "Anomaly Detection":
            _create_anomaly_detection_comparison(comparison_data)
    else:
        st.info("📊 Please extract comparison data in the Product Comparison tab first")


def _perform_product_comparison(products_to_compare, start_date, end_date, qa_level):
    """Perform real-time product comparison extraction"""
    
    # Check if imported data is available
    if 'imported_comparison_data' in st.session_state:
        imported_data = st.session_state['imported_comparison_data']
        st.info("📁 Using imported CSV data for comparison")
        
        comparison_data = {}
        
        # Use imported data if products match
        if "MOD10A1 (Daily Snow)" in products_to_compare and 'MOD10A1' in imported_data:
            comparison_data['MOD10A1'] = imported_data['MOD10A1']
            st.success("✅ Using imported MOD10A1 data")
        
        if "MCD43A3 (Broadband)" in products_to_compare and 'MCD43A3' in imported_data:
            comparison_data['MCD43A3'] = imported_data['MCD43A3']
            st.success("✅ Using imported MCD43A3 data")
        
        # If we have imported data, use it and skip real-time extraction
        if comparison_data:
            st.session_state['comparison_data'] = comparison_data
            _display_comparison_results(comparison_data)
            _add_comparison_csv_downloads(comparison_data, start_date, end_date, qa_level)
            return
    
    # Fall back to real-time extraction if no imported data
    comparison_data = {}
    
    with st.spinner("Extracting comparison data..."):
        progress_bar = st.progress(0)
        
        # Extract MOD10A1 data if selected
        if "MOD10A1 (Daily Snow)" in products_to_compare:
            try:
                st.info("🛰️ Extracting MOD10A1 data...")
                
                # Import the MOD10A1 extraction function  
                import sys
                sys.path.append('/mnt/d/UQTR/Maitrîse/Code/Albedo MODIS Geemap/src')
                from data.extraction import extract_time_series_fast
                
                # Convert datetime objects to string format if needed
                start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
                end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
                
                # Extract MOD10A1 data using the existing extraction function
                # Use basic QA filtering to avoid potential QA level conflicts
                mod10a1_data = extract_time_series_fast(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    use_broadband=False,  # Use snow albedo (MOD10A1)
                    scale=500,
                    use_advanced_qa=False,  # Use simple QA to avoid conflicts
                    qa_level=qa_level
                )
                
                # Add metadata for tracking
                if not mod10a1_data.empty:
                    mod10a1_data['product_type'] = 'MOD10A1'
                    mod10a1_data['extraction_source'] = 'unified_temporal_dashboard'
                
                comparison_data['MOD10A1'] = mod10a1_data
                progress_bar.progress(0.5)
                
            except Exception as e:
                st.error(f"Error extracting MOD10A1 data: {e}")
                st.error(f"Error details: {type(e).__name__}: {str(e)}")
                # Continue with other products even if one fails
        
        # Extract MCD43A3 data if selected
        if "MCD43A3 (Broadband)" in products_to_compare:
            try:
                st.info("🌈 Extracting MCD43A3 data...")
                
                # Import the MCD43A3 extraction function
                from ..analysis.mcd43a3_temporal import extract_mcd43a3_time_series_realtime
                
                # Convert datetime objects to string format if needed
                start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
                end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
                
                mcd43a3_data = extract_mcd43a3_time_series_realtime(
                    start_date=start_date_str,
                    end_date=end_date_str,
                    qa_level=qa_level,
                    band_selection='shortwave',
                    diffuse_fraction=0.2,
                    max_observations=150
                )
                
                # Add metadata for tracking
                if not mcd43a3_data.empty:
                    mcd43a3_data['product_type'] = 'MCD43A3'
                    mcd43a3_data['extraction_source'] = 'unified_temporal_dashboard'
                
                comparison_data['MCD43A3'] = mcd43a3_data
                progress_bar.progress(1.0)
                
            except Exception as e:
                st.error(f"Error extracting MCD43A3 data: {e}")
                st.error(f"Error details: {type(e).__name__}: {str(e)}")
                # Continue even if extraction fails
        
        progress_bar.empty()
    
    # Store comparison data in session state
    st.session_state['comparison_data'] = comparison_data
    
    # Display results
    _display_comparison_results(comparison_data)
    
    # Add download functionality
    if comparison_data:
        _add_comparison_csv_downloads(comparison_data, start_date, end_date, qa_level)


def _display_comparison_results(comparison_data):
    """Display comparison results"""
    
    if not comparison_data:
        st.warning("No comparison data available")
        return
    
    # Summary statistics
    st.markdown("### 📊 Extraction Summary")
    
    col1, col2 = st.columns(2)
    
    if 'MOD10A1' in comparison_data:
        with col1:
            mod10a1_data = comparison_data['MOD10A1']
            st.metric("MOD10A1 Observations", len(mod10a1_data))
            if not mod10a1_data.empty:
                st.metric("MOD10A1 Mean Albedo", f"{mod10a1_data['albedo_mean'].mean():.3f}")
                st.metric("MOD10A1 Date Range", 
                         f"{mod10a1_data['date'].min().strftime('%Y-%m-%d')} to {mod10a1_data['date'].max().strftime('%Y-%m-%d')}")
    
    if 'MCD43A3' in comparison_data:
        with col2:
            mcd43a3_data = comparison_data['MCD43A3']
            st.metric("MCD43A3 Observations", len(mcd43a3_data))
            if not mcd43a3_data.empty:
                st.metric("MCD43A3 Mean Albedo", f"{mcd43a3_data['albedo_mean'].mean():.3f}")
                st.metric("MCD43A3 Date Range",
                         f"{mcd43a3_data['date'].min().strftime('%Y-%m-%d')} to {mcd43a3_data['date'].max().strftime('%Y-%m-%d')}")
    
    # Quick comparison plot
    fig = go.Figure()
    
    if 'MOD10A1' in comparison_data and not comparison_data['MOD10A1'].empty:
        mod10a1_data = comparison_data['MOD10A1']
        fig.add_trace(go.Scatter(
            x=mod10a1_data['date'],
            y=mod10a1_data['albedo_mean'],
            mode='markers+lines',
            name='MOD10A1 (Snow)',
            marker=dict(color='blue', size=6),
            line=dict(color='blue', width=2)
        ))
    
    if 'MCD43A3' in comparison_data and not comparison_data['MCD43A3'].empty:
        mcd43a3_data = comparison_data['MCD43A3']
        fig.add_trace(go.Scatter(
            x=mcd43a3_data['date'],
            y=mcd43a3_data['albedo_mean'],
            mode='markers+lines',
            name='MCD43A3 (Broadband)',
            marker=dict(color='red', size=6),
            line=dict(color='red', width=2)
        ))
    
    fig.update_layout(
        title="MODIS Products Comparison - Temporal Evolution",
        xaxis_title="Date",
        yaxis_title="Albedo",
        height=600,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _display_comparison_placeholder():
    """Display placeholder when no comparison data"""
    st.info("📋 **Getting Started with Product Comparison**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🛰️ MOD10A1 (Daily Snow Albedo)
        - **Temporal Resolution**: Daily
        - **Spatial Resolution**: 500m
        - **Coverage**: Terra & Aqua satellites
        - **Best For**: Daily monitoring, melt season analysis
        - **Methodology**: Williamson & Menounos (2021)
        """)
        
    with col2:
        st.markdown("""
        ### 🌈 MCD43A3 (Broadband Albedo)
        - **Temporal Resolution**: Daily (16-day window)
        - **Spatial Resolution**: 500m  
        - **Coverage**: Terra & Aqua combined
        - **Best For**: Spectral analysis, BRDF modeling
        - **Methodology**: MODIS BRDF/Albedo algorithm
        """)
    
    st.markdown("---")
    st.markdown("**👈 Use the sidebar controls to configure and extract comparison data**")


# Comparison analysis functions
def _create_annual_trends_comparison(comparison_data):
    """Create annual trends comparison"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Annual Mean Albedo Trends', 'Annual Data Coverage'),
        vertical_spacing=0.12
    )
    
    colors = {'MOD10A1': 'blue', 'MCD43A3': 'red'}
    
    for product, data in comparison_data.items():
        if not data.empty:
            # Annual statistics
            annual_stats = data.groupby('year').agg({
                'albedo_mean': ['mean', 'std', 'count']
            }).round(4)
            
            annual_stats.columns = ['mean_albedo', 'std_albedo', 'count']
            annual_stats = annual_stats.reset_index()
            
            # Trends
            fig.add_trace(
                go.Scatter(
                    x=annual_stats['year'],
                    y=annual_stats['mean_albedo'],
                    mode='markers+lines',
                    name=f'{product} Mean',
                    marker=dict(color=colors[product], size=8),
                    line=dict(color=colors[product], width=2),
                    error_y=dict(
                        type='data',
                        array=annual_stats['std_albedo'],
                        visible=True
                    )
                ),
                row=1, col=1
            )
            
            # Coverage
            fig.add_trace(
                go.Bar(
                    x=annual_stats['year'],
                    y=annual_stats['count'],
                    name=f'{product} Count',
                    marker=dict(color=colors[product], opacity=0.7)
                ),
                row=2, col=1
            )
    
    fig.update_layout(height=800, title_text="Annual Trends Comparison")
    st.plotly_chart(fig, use_container_width=True)


def _create_seasonal_patterns_comparison(comparison_data):
    """Create seasonal patterns comparison optimized for melt season data"""
    fig = go.Figure()
    
    colors = {'MOD10A1': 'blue', 'MCD43A3': 'red'}
    symbols = {'MOD10A1': 'circle', 'MCD43A3': 'square'}
    
    all_doys = []
    
    for product, data in comparison_data.items():
        if not data.empty:
            all_doys.extend(data['doy'].tolist())
            
            fig.add_trace(go.Scatter(
                x=data['doy'],
                y=data['albedo_mean'],
                mode='markers',
                name=product,
                marker=dict(
                    color=colors[product],
                    size=8,
                    symbol=symbols[product],
                    opacity=0.7
                ),
                hovertemplate=f'<b>{product}</b><br>DOY: %{{x}}<br>Albedo: %{{y:.3f}}<br>Date: %{{customdata}}<extra></extra>',
                customdata=data['date'].dt.strftime('%Y-%m-%d') if 'date' in data.columns else None
            ))
    
    # Determine if this is melt season focused data
    if all_doys:
        min_doy = min(all_doys)
        max_doy = max(all_doys)
        doy_span = max_doy - min_doy
        
        # Check if data is primarily in melt season range (DOY 152-273 = June 1 - Sept 30)
        melt_season_focused = min_doy >= 140 and max_doy <= 290  # Allow some buffer
        
        if melt_season_focused:
            title_suffix = " (Melt Season DOY)"
            
            # Add melt season period markers
            fig.add_vrect(
                x0=152, x1=181,  # June (DOY 152-181)
                annotation_text="June", annotation_position="top",
                fillcolor="lightblue", opacity=0.2,
                line_width=0
            )
            fig.add_vrect(
                x0=182, x1=212,  # July (DOY 182-212)
                annotation_text="July", annotation_position="top",
                fillcolor="orange", opacity=0.2,
                line_width=0
            )
            fig.add_vrect(
                x0=213, x1=243,  # August (DOY 213-243)
                annotation_text="August", annotation_position="top",
                fillcolor="red", opacity=0.2,
                line_width=0
            )
            fig.add_vrect(
                x0=244, x1=273,  # September (DOY 244-273)
                annotation_text="September", annotation_position="top",
                fillcolor="purple", opacity=0.2,
                line_width=0
            )
            
            # Set x-axis range with some padding for melt season
            x_range = [max(140, min_doy - 10), min(290, max_doy + 10)]
            
        else:
            title_suffix = " (Full Year DOY)"
            x_range = None  # Let plotly auto-scale
    else:
        title_suffix = " (Day of Year)"
        x_range = None
    
    fig.update_layout(
        title=f"Seasonal Patterns Comparison{title_suffix}",
        xaxis_title="Day of Year",
        yaxis_title="Albedo",
        height=600,
        xaxis=dict(range=x_range) if x_range else {}
    )
    
    # Add seasonal context information
    if all_doys and melt_season_focused:
        st.info("📊 **Melt Season Patterns**: June (blue) - early melt, July-August (orange/red) - peak melt, September (purple) - late season")
    
    st.plotly_chart(fig, use_container_width=True)


def _create_monthly_comparison(comparison_data):
    """Create monthly comparison optimized for melt season data"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Monthly Mean Albedo', 'Monthly Data Availability'),
        specs=[[{}, {}]]
    )
    
    colors = {'MOD10A1': 'blue', 'MCD43A3': 'red'}
    all_months = []
    
    for product, data in comparison_data.items():
        if not data.empty:
            all_months.extend(data['month'].unique())
            
            monthly_stats = data.groupby('month').agg({
                'albedo_mean': ['mean', 'std', 'count']
            }).round(4)
            
            monthly_stats.columns = ['mean_albedo', 'std_albedo', 'count']
            monthly_stats = monthly_stats.reset_index()
            
            # Monthly means
            fig.add_trace(
                go.Bar(
                    x=monthly_stats['month'],
                    y=monthly_stats['mean_albedo'],
                    name=f'{product} Mean',
                    marker=dict(color=colors[product]),
                    error_y=dict(
                        type='data',
                        array=monthly_stats['std_albedo'],
                        visible=True
                    ),
                    hovertemplate=f'<b>{product}</b><br>Month: %{{x}}<br>Mean Albedo: %{{y:.3f}}<br>Std: %{{error_y.array:.3f}}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Monthly counts
            fig.add_trace(
                go.Bar(
                    x=monthly_stats['month'],
                    y=monthly_stats['count'],
                    name=f'{product} Count',
                    marker=dict(color=colors[product], opacity=0.7),
                    hovertemplate=f'<b>{product}</b><br>Month: %{{x}}<br>Observations: %{{y}}<extra></extra>'
                ),
                row=1, col=2
            )
    
    # Check if data is melt season focused
    unique_months = set(all_months)
    melt_season_months = {6, 7, 8, 9}  # June, July, August, September
    is_melt_season_focused = unique_months.issubset(melt_season_months)
    
    if is_melt_season_focused:
        title_suffix = " (Melt Season Months)"
        
        # Set month labels for melt season
        month_labels = {6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep'}
        
        # Update x-axis to show only melt season months
        fig.update_xaxes(
            tickmode='array',
            tickvals=list(unique_months),
            ticktext=[month_labels.get(m, str(m)) for m in sorted(unique_months)],
            row=1, col=1
        )
        fig.update_xaxes(
            tickmode='array',
            tickvals=list(unique_months),
            ticktext=[month_labels.get(m, str(m)) for m in sorted(unique_months)],
            row=1, col=2
        )
        
        # Add context information
        st.info("📊 **Melt Season Monthly Analysis**: Comparing June (early), July-August (peak), and September (late) periods")
        
    else:
        title_suffix = " (All Available Months)"
        
        # Standard month labels for full year data
        month_labels = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                       7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        
        fig.update_xaxes(
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=[month_labels[m] for m in range(1, 13)],
            row=1, col=1
        )
        fig.update_xaxes(
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=[month_labels[m] for m in range(1, 13)],
            row=1, col=2
        )
    
    fig.update_layout(
        height=600, 
        title_text=f"Monthly Comparison Analysis{title_suffix}",
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show monthly statistics summary
    if all_months:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Months Covered", len(unique_months))
        
        with col2:
            if is_melt_season_focused:
                st.metric("Season Type", "Melt Season")
            else:
                st.metric("Season Type", "Multi-Season")
        
        with col3:
            month_names = {6: 'June', 7: 'July', 8: 'August', 9: 'September',
                          1: 'January', 2: 'February', 3: 'March', 4: 'April', 
                          5: 'May', 10: 'October', 11: 'November', 12: 'December'}
            month_list = [month_names.get(m, str(m)) for m in sorted(unique_months)]
            st.metric("Period", f"{month_list[0]} - {month_list[-1]}" if len(month_list) > 1 else month_list[0])


def _create_detailed_timeline_comparison(comparison_data):
    """Create detailed timeline comparison optimized for melt season data"""
    fig = go.Figure()
    
    colors = {'MOD10A1': 'blue', 'MCD43A3': 'red'}
    all_dates = []
    
    # Collect all dates to determine the actual date range
    for product, data in comparison_data.items():
        if not data.empty:
            all_dates.extend(data['date'].tolist())
    
    if not all_dates:
        st.warning("No data available for timeline comparison")
        return
    
    # Determine actual date range from available data
    min_date = min(all_dates)
    max_date = max(all_dates)
    date_span = (max_date - min_date).days
    
    # Create traces for each product
    for product, data in comparison_data.items():
        if not data.empty:
            # Add error bars if standard deviation is available
            error_y = None
            if 'albedo_std' in data.columns:
                error_y = dict(
                    type='data',
                    array=data['albedo_std'],
                    visible=True,
                    width=2
                )
            
            fig.add_trace(go.Scatter(
                x=data['date'],
                y=data['albedo_mean'],
                mode='markers+lines',
                name=product,
                marker=dict(color=colors[product], size=6),
                line=dict(color=colors[product], width=2),
                error_y=error_y,
                hovertemplate=f'<b>{product}</b><br>' +
                            'Date: %{x}<br>' +
                            'Albedo: %{y:.3f}<br>' +
                            '<extra></extra>'
            ))
    
    # Adaptive layout based on data span
    if date_span <= 180:  # 6 months or less (typical melt season)
        # Optimize for melt season display
        title_suffix = " (Melt Season Focus)"
        rangeslider_visible = False  # Less useful for short periods
        
        # Set appropriate x-axis tick spacing for melt season
        dtick = "M1" if date_span > 90 else "M0.5"  # Monthly or bi-weekly ticks
        
    else:  # Multi-year data
        title_suffix = " (Multi-Year)"
        rangeslider_visible = True
        dtick = "M3"  # Quarterly ticks for longer periods
    
    # Update layout with adaptive settings
    fig.update_layout(
        title=f"Detailed Timeline Comparison{title_suffix}",
        xaxis_title="Date",
        yaxis_title="Albedo", 
        height=600,
        hovermode='x unified',
        xaxis=dict(
            rangeslider=dict(visible=rangeslider_visible),
            type="date",
            dtick=dtick,
            # Set appropriate range with some padding
            range=[
                min_date - timedelta(days=max(7, date_span * 0.05)),  # 5% padding or 1 week minimum
                max_date + timedelta(days=max(7, date_span * 0.05))
            ]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add annotations for melt season context
    if date_span <= 180:
        # Check if data spans multiple years
        years_covered = set(d.year for d in all_dates)
        if len(years_covered) > 1:
            years_str = f"{min(years_covered)}-{max(years_covered)}"
        else:
            years_str = str(list(years_covered)[0])
        
        fig.add_annotation(
            text=f"Melt Season Data ({years_str})<br>June-September Period",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10, color="gray"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="gray",
            borderwidth=1
        )
    
    # Display data summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Date Range", f"{date_span} days")
    
    with col2:
        if comparison_data:
            total_obs = sum(len(data) for data in comparison_data.values() if not data.empty)
            st.metric("Total Observations", total_obs)
    
    with col3:
        years_covered = set(d.year for d in all_dates)
        st.metric("Years Covered", len(years_covered))
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add interpretation help for melt season data
    if date_span <= 180:
        with st.expander("📚 Melt Season Timeline Interpretation", expanded=False):
            st.markdown("""
            **Understanding Melt Season Timeline Patterns:**
            
            - **June (Early Season)**: Transition from snow to ice albedo
            - **July-August (Peak Melt)**: Lowest albedo values, maximum melt
            - **September (Late Season)**: Potential albedo recovery with fresh snow
            
            **Product Differences:**
            - **MOD10A1**: Daily observations, sensitive to weather conditions
            - **MCD43A3**: 16-day moving window, smoother temporal patterns
            
            **Analysis Tips:**
            - Look for seasonal trends within the melt season
            - Compare inter-annual variability if multiple years shown
            - Note data gaps due to cloud cover or quality filtering
            """)


def _create_direct_correlation_analysis(comparison_data):
    """Create direct correlation analysis"""
    if 'MOD10A1' in comparison_data and 'MCD43A3' in comparison_data:
        mod10a1_data = comparison_data['MOD10A1']
        mcd43a3_data = comparison_data['MCD43A3']
        
        if not mod10a1_data.empty and not mcd43a3_data.empty:
            # Merge on date for direct comparison
            merged_data = pd.merge(
                mod10a1_data[['date', 'albedo_mean']].rename(columns={'albedo_mean': 'mod10a1_albedo'}),
                mcd43a3_data[['date', 'albedo_mean']].rename(columns={'albedo_mean': 'mcd43a3_albedo'}),
                on='date',
                how='inner'
            )
            
            if not merged_data.empty:
                # Correlation coefficient
                correlation = merged_data['mod10a1_albedo'].corr(merged_data['mcd43a3_albedo'])
                
                # Scatter plot
                fig = px.scatter(
                    merged_data,
                    x='mod10a1_albedo',
                    y='mcd43a3_albedo',
                    title=f"Direct Correlation Analysis (r = {correlation:.3f})",
                    labels={'mod10a1_albedo': 'MOD10A1 Albedo', 'mcd43a3_albedo': 'MCD43A3 Albedo'},
                    trendline="ols"
                )
                
                # Add 1:1 line
                min_val = min(merged_data['mod10a1_albedo'].min(), merged_data['mcd43a3_albedo'].min())
                max_val = max(merged_data['mod10a1_albedo'].max(), merged_data['mcd43a3_albedo'].max())
                
                fig.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='1:1 Line',
                    line=dict(dash='dash', color='gray')
                ))
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Correlation", f"{correlation:.3f}")
                with col2:
                    bias = merged_data['mcd43a3_albedo'].mean() - merged_data['mod10a1_albedo'].mean()
                    st.metric("Mean Bias", f"{bias:.3f}")
                with col3:
                    rmse = ((merged_data['mcd43a3_albedo'] - merged_data['mod10a1_albedo']) ** 2).mean() ** 0.5
                    st.metric("RMSE", f"{rmse:.3f}")
            else:
                st.warning("No overlapping dates found for correlation analysis")
    else:
        st.warning("Both MOD10A1 and MCD43A3 data required for correlation analysis")


def _create_difference_analysis(comparison_data):
    """Create difference analysis"""
    if 'MOD10A1' in comparison_data and 'MCD43A3' in comparison_data:
        mod10a1_data = comparison_data['MOD10A1']
        mcd43a3_data = comparison_data['MCD43A3']
        
        if not mod10a1_data.empty and not mcd43a3_data.empty:
            # Merge on date
            merged_data = pd.merge(
                mod10a1_data[['date', 'albedo_mean']].rename(columns={'albedo_mean': 'mod10a1_albedo'}),
                mcd43a3_data[['date', 'albedo_mean']].rename(columns={'albedo_mean': 'mcd43a3_albedo'}),
                on='date',
                how='inner'
            )
            
            if not merged_data.empty:
                # Calculate differences
                merged_data['difference'] = merged_data['mcd43a3_albedo'] - merged_data['mod10a1_albedo']
                merged_data['abs_difference'] = abs(merged_data['difference'])
                
                # Difference time series plot
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=merged_data['date'],
                    y=merged_data['difference'],
                    mode='markers+lines',
                    name='MCD43A3 - MOD10A1',
                    marker=dict(color='purple', size=6),
                    line=dict(color='purple', width=2)
                ))
                
                # Add zero line
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                
                fig.update_layout(
                    title="Albedo Difference Analysis (MCD43A3 - MOD10A1)",
                    xaxis_title="Date",
                    yaxis_title="Albedo Difference",
                    height=600
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Difference statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Mean Difference", f"{merged_data['difference'].mean():.3f}")
                with col2:
                    st.metric("Std Difference", f"{merged_data['difference'].std():.3f}")
                with col3:
                    st.metric("Mean Abs Difference", f"{merged_data['abs_difference'].mean():.3f}")
                with col4:
                    st.metric("Max Abs Difference", f"{merged_data['abs_difference'].max():.3f}")


def _create_bias_assessment(comparison_data):
    """Create bias assessment"""
    st.markdown("### 📊 Bias Assessment Analysis")
    st.info("📋 Comprehensive bias analysis between MOD10A1 and MCD43A3 products")
    
    # This would implement detailed bias assessment
    # For now, show placeholder
    st.markdown("""
    **Bias Assessment Features:**
    - Seasonal bias patterns
    - Elevation-dependent bias
    - Temporal bias evolution
    - Statistical significance testing
    """)


def _create_temporal_alignment_analysis(comparison_data):
    """Create temporal alignment analysis"""
    st.markdown("### 🕰️ Temporal Alignment Analysis")
    st.info("📋 Analysis of temporal sampling differences between products")
    
    # This would implement temporal alignment analysis
    # For now, show placeholder
    st.markdown("""
    **Temporal Alignment Features:**
    - Sampling frequency comparison
    - Temporal offset analysis
    - Data availability patterns
    - Synchronization assessment
    """)


def _create_descriptive_statistics_comparison(comparison_data):
    """Create descriptive statistics comparison"""
    st.markdown("### 📊 Descriptive Statistics Comparison")
    
    stats_data = []
    
    for product, data in comparison_data.items():
        if not data.empty:
            stats = {
                'Product': product,
                'Count': len(data),
                'Mean': data['albedo_mean'].mean(),
                'Std': data['albedo_mean'].std(),
                'Min': data['albedo_mean'].min(),
                'Max': data['albedo_mean'].max(),
                'Median': data['albedo_mean'].median(),
                'Skewness': data['albedo_mean'].skew(),
                'Kurtosis': data['albedo_mean'].kurtosis()
            }
            stats_data.append(stats)
    
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)


def _create_distribution_comparison(comparison_data):
    """Create distribution comparison"""
    fig = go.Figure()
    
    colors = {'MOD10A1': 'blue', 'MCD43A3': 'red'}
    
    for product, data in comparison_data.items():
        if not data.empty:
            fig.add_trace(go.Histogram(
                x=data['albedo_mean'],
                name=f'{product} Distribution',
                opacity=0.7,
                marker=dict(color=colors[product]),
                nbinsx=30
            ))
    
    fig.update_layout(
        title="Albedo Distribution Comparison",
        xaxis_title="Albedo",
        yaxis_title="Frequency",
        height=600,
        barmode='overlay'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _create_trend_analysis_comparison(comparison_data):
    """Create trend analysis comparison"""
    st.markdown("### 📈 Trend Analysis Comparison")
    
    # Implementation placeholder
    st.info("📋 Advanced trend analysis comparing long-term patterns between products")


def _create_anomaly_detection_comparison(comparison_data):
    """Create anomaly detection comparison"""
    st.markdown("### 🚨 Anomaly Detection Comparison")
    
    # Implementation placeholder
    st.info("📋 Comparative anomaly detection across both products")


def _add_comparison_csv_downloads(comparison_data, start_date, end_date, qa_level):
    """Add CSV download buttons for comparison data"""
    import io
    from datetime import datetime
    
    st.markdown("---")
    st.markdown("### 📥 Download Comparison Data")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Handle date formatting safely
    start_date_str = start_date.strftime('%Y%m%d') if hasattr(start_date, 'strftime') else str(start_date).replace('-', '')
    end_date_str = end_date.strftime('%Y%m%d') if hasattr(end_date, 'strftime') else str(end_date).replace('-', '')
    
    base_filename = f"modis_comparison_{qa_level}_{start_date_str}_to_{end_date_str}_{timestamp}"
    
    # Individual product downloads
    col1, col2, col3 = st.columns(3)
    
    if 'MOD10A1' in comparison_data and not comparison_data['MOD10A1'].empty:
        with col1:
            mod10a1_df = comparison_data['MOD10A1']
            csv_buffer = io.StringIO()
            mod10a1_df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="❄️ Download MOD10A1 Data",
                data=csv_data,
                file_name=f"{base_filename}_MOD10A1.csv",
                mime="text/csv",
                help=f"Download MOD10A1 data ({len(mod10a1_df)} observations)"
            )
    
    if 'MCD43A3' in comparison_data and not comparison_data['MCD43A3'].empty:
        with col2:
            mcd43a3_df = comparison_data['MCD43A3']
            csv_buffer = io.StringIO()
            mcd43a3_df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="🌈 Download MCD43A3 Data",
                data=csv_data,
                file_name=f"{base_filename}_MCD43A3.csv",
                mime="text/csv",
                help=f"Download MCD43A3 data ({len(mcd43a3_df)} observations)"
            )
    
    # Combined comparison download
    if len(comparison_data) >= 2:
        with col3:
            # Create merged dataset for direct comparison
            if 'MOD10A1' in comparison_data and 'MCD43A3' in comparison_data:
                mod10a1_df = comparison_data['MOD10A1'][['date', 'albedo_mean', 'pixel_count']].copy()
                mcd43a3_df = comparison_data['MCD43A3'][['date', 'albedo_mean', 'pixel_count']].copy()
                
                # Rename columns for clarity
                mod10a1_df.columns = ['date', 'mod10a1_albedo', 'mod10a1_pixels']
                mcd43a3_df.columns = ['date', 'mcd43a3_albedo', 'mcd43a3_pixels']
                
                # Merge on date
                merged_df = pd.merge(mod10a1_df, mcd43a3_df, on='date', how='outer', suffixes=('_mod10a1', '_mcd43a3'))
                merged_df = merged_df.sort_values('date')
                
                # Calculate differences where both products have data
                mask = merged_df['mod10a1_albedo'].notna() & merged_df['mcd43a3_albedo'].notna()
                merged_df.loc[mask, 'albedo_difference'] = merged_df.loc[mask, 'mcd43a3_albedo'] - merged_df.loc[mask, 'mod10a1_albedo']
                
                csv_buffer = io.StringIO()
                merged_df.to_csv(csv_buffer, index=False, encoding='utf-8')
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="🔄 Download Merged Comparison",
                    data=csv_data,
                    file_name=f"{base_filename}_merged.csv",
                    mime="text/csv",
                    help="Download merged dataset with both products for direct comparison"
                )
    
    # Summary statistics download
    st.markdown("#### 📊 Summary Statistics")
    
    summary_data = []
    for product, data in comparison_data.items():
        if not data.empty:
            summary = {
                'Product': product,
                'Start_Date': data['date'].min(),
                'End_Date': data['date'].max(),
                'Total_Observations': len(data),
                'Mean_Albedo': data['albedo_mean'].mean(),
                'Std_Albedo': data['albedo_mean'].std(),
                'Min_Albedo': data['albedo_mean'].min(),
                'Max_Albedo': data['albedo_mean'].max(),
                'Mean_Pixel_Count': data['pixel_count'].mean() if 'pixel_count' in data.columns else None,
                'Years_Covered': len(data['year'].unique()) if 'year' in data.columns else None
            }
            summary_data.append(summary)
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        
        summary_buffer = io.StringIO()
        summary_df.to_csv(summary_buffer, index=False, encoding='utf-8')
        summary_csv = summary_buffer.getvalue()
        
        st.download_button(
            label="📈 Download Summary Statistics",
            data=summary_csv,
            file_name=f"{base_filename}_summary.csv",
            mime="text/csv",
            help="Download comparative summary statistics"
        )
        
        # Display summary table
        st.dataframe(summary_df, use_container_width=True)


def _add_unified_csv_import_interface():
    """Add CSV import interface for unified temporal analysis"""
    with st.expander("📁 Import Custom CSV Data for Comparison", expanded=False):
        st.markdown("*Upload your own MODIS temporal data for comparative analysis*")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 MOD10A1/MYD10A1 Data**")
            mod10a1_file = st.file_uploader(
                "MOD10A1 CSV file",
                type=['csv'],
                help="Upload CSV with MOD10A1/MYD10A1 daily snow albedo data",
                key="csv_import_mod10a1_unified"
            )
        
        with col2:
            st.markdown("**🌈 MCD43A3 Data**")
            mcd43a3_file = st.file_uploader(
                "MCD43A3 CSV file",
                type=['csv'],
                help="Upload CSV with MCD43A3 broadband albedo data",
                key="csv_import_mcd43a3_unified"
            )
        
        imported_datasets = {}
        
        # Process MOD10A1 file
        if mod10a1_file is not None:
            mod10a1_data = _process_unified_csv_import(mod10a1_file, "MOD10A1")
            if mod10a1_data is not None:
                imported_datasets['MOD10A1'] = mod10a1_data
                st.success(f"✅ MOD10A1 data loaded: {len(mod10a1_data)} observations")
        
        # Process MCD43A3 file
        if mcd43a3_file is not None:
            mcd43a3_data = _process_unified_csv_import(mcd43a3_file, "MCD43A3")
            if mcd43a3_data is not None:
                imported_datasets['MCD43A3'] = mcd43a3_data
                st.success(f"✅ MCD43A3 data loaded: {len(mcd43a3_data)} observations")
        
        # Store in session state for unified analysis
        if imported_datasets:
            st.session_state['imported_comparison_data'] = imported_datasets
            
            # Show quick comparison summary
            st.markdown("### 📊 Imported Data Summary")
            for product, data in imported_datasets.items():
                date_range = data['date'].max() - data['date'].min()
                mean_albedo = data['albedo_mean'].mean()
                st.markdown(f"**{product}**: {len(data)} obs, {date_range.days} days, mean albedo = {mean_albedo:.3f}")
            
            return imported_datasets
    
    # Check for existing imported data in session state
    if 'imported_comparison_data' in st.session_state:
        existing_data = st.session_state['imported_comparison_data']
        st.info(f"📊 Using previously imported data: {list(existing_data.keys())}")
        return existing_data
    
    return None


def _process_unified_csv_import(uploaded_file, product_type):
    """Process uploaded CSV for unified comparison"""
    try:
        # Load CSV with different encodings
        df_imported = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df_imported = pd.read_csv(uploaded_file, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if df_imported is None:
            st.error(f"❌ Could not read {product_type} CSV file with any encoding")
            return None
        
        # Validate and process the data
        validated_df = _validate_unified_csv(df_imported, product_type)
        
        if validated_df is not None:
            return validated_df
        else:
            return None
            
    except Exception as e:
        st.error(f"❌ Error processing {product_type} CSV file: {e}")
        return None


def _validate_unified_csv(df, product_type):
    """Validate CSV data for unified comparison"""
    required_cols = ['date', 'albedo_mean']
    
    # Check for required columns (case-insensitive)
    df_cols_lower = [col.lower() for col in df.columns]
    missing_required = []
    
    for req_col in required_cols:
        if req_col.lower() not in df_cols_lower:
            # Try alternative names
            alternatives = {
                'date': ['date_str', 'observation_date', 'time', 'datetime'],
                'albedo_mean': ['albedo', 'mean_albedo', 'albedo_avg', 'avg_albedo']
            }
            
            found_alternative = False
            if req_col in alternatives:
                for alt_name in alternatives[req_col]:
                    if alt_name.lower() in df_cols_lower:
                        # Rename column to standard name
                        original_name = df.columns[df_cols_lower.index(alt_name.lower())]
                        df = df.rename(columns={original_name: req_col})
                        found_alternative = True
                        break
            
            if not found_alternative:
                missing_required.append(req_col)
    
    if missing_required:
        st.error(f"❌ {product_type} file missing required columns: {missing_required}")
        st.markdown(f"**Required columns for {product_type}:**")
        st.markdown("- `date` (or date_str, observation_date, time, datetime)")
        st.markdown("- `albedo_mean` (or albedo, mean_albedo, albedo_avg)")
        return None
    
    # Convert date column to datetime
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        st.error(f"❌ Could not parse dates in {product_type} file: {e}")
        return None
    
    # Add derived temporal columns if missing
    if 'year' not in df.columns:
        df['year'] = df['date'].dt.year
    if 'month' not in df.columns:
        df['month'] = df['date'].dt.month
    if 'doy' not in df.columns:
        df['doy'] = df['date'].dt.dayofyear
    
    # Add pixel_count if missing (for compatibility)
    if 'pixel_count' not in df.columns:
        df['pixel_count'] = 20  # Default value
    
    # Validate albedo values
    if 'albedo_mean' in df.columns:
        albedo_values = df['albedo_mean'].dropna()
        if not albedo_values.empty:
            min_albedo = albedo_values.min()
            max_albedo = albedo_values.max()
            
            if min_albedo < 0 or max_albedo > 1:
                st.warning(f"⚠️ {product_type} albedo values outside normal range (0-1): {min_albedo:.3f} to {max_albedo:.3f}")
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    return df