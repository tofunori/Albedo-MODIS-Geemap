"""
Enhanced MCD43A3 Spectral and Temporal Analysis Dashboard
Advanced visualizations for MODIS MCD43A3 broadband albedo data with temporal analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def create_mcd43a3_dashboard(df, qa_config=None, qa_level=None):
    """
    Create enhanced MCD43A3 analysis dashboard with temporal capabilities
    
    Args:
        df: DataFrame with MCD43A3 spectral data  
        qa_config: QA configuration dict (optional)
        qa_level: Selected QA level name (optional)
    """
    # Show QA info if provided
    if qa_config and qa_level:
        st.info(f"📊 **Quality Filtering:** {qa_level} - {qa_config['mcd43a3']['description']}")
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Spectral Analysis", 
        "⏰ Temporal Analysis", 
        "🔍 Interactive Exploration",
        "📈 Advanced Analytics"
    ])
    
    with tab1:
        _create_spectral_analysis_tab(df)
        
    with tab2:
        _create_temporal_analysis_tab(df, qa_config, qa_level)
        
    with tab3:
        _create_interactive_exploration_tab(df)
        
    with tab4:
        _create_advanced_analytics_tab(df)


def _create_spectral_analysis_tab(df):
    """Create spectral analysis tab (original functionality enhanced)"""
    st.subheader("🌈 MCD43A3 Spectral Analysis")
    
    if df.empty:
        st.error("No MCD43A3 data available")
        return
    
    # Prepare data
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['doy'] = df['date'].dt.dayofyear
    
    # Sidebar controls for spectral analysis
    with st.sidebar:
        st.markdown("### 🎨 Spectral Controls")
        
        # Year selection
        years = sorted(df['year'].unique())
        selected_years = st.multiselect(
            "Select Years", 
            years, 
            default=years[-3:] if len(years) >= 3 else years,
            key="spectral_years"
        )
        
        # View type selection
        view_type = st.selectbox(
            "Spectral View",
            ["Seasonal Evolution", "Visible vs NIR", "Spectral Bands", "Vis/NIR Ratio"],
            key="spectral_view"
        )
    
    # Filter data
    filtered_df = df[df['year'].isin(selected_years)] if selected_years else df
    
    # Color scheme
    colors = {
        'Albedo_BSA_vis': '#1f77b4',      # Blue
        'Albedo_BSA_nir': '#d62728',      # Red
        'Albedo_BSA_Band1': '#ff7f0e',    # Orange
        'Albedo_BSA_Band2': '#2ca02c',    # Green
        'Albedo_BSA_Band3': '#9467bd',    # Purple
        'Albedo_BSA_Band4': '#8c564b'     # Brown
    }
    
    # Create plots based on view type
    if view_type == "Seasonal Evolution":
        fig = _create_seasonal_evolution_plot(filtered_df, selected_years, colors)
    elif view_type == "Visible vs NIR":
        fig = _create_vis_nir_comparison_plot(filtered_df)
    elif view_type == "Spectral Bands":
        fig = _create_spectral_bands_plot(filtered_df, years, colors)
    elif view_type == "Vis/NIR Ratio":
        fig = _create_vis_nir_ratio_plot(filtered_df)
    
    # Display plot
    st.plotly_chart(fig, use_container_width=True)
    
    # Data statistics
    _display_spectral_statistics(filtered_df, selected_years)


def _create_temporal_analysis_tab(df, qa_config=None, qa_level=None):
    """Create temporal analysis tab with real-time capabilities"""
    st.subheader("⏰ MCD43A3 Temporal Analysis")
    st.markdown("*Real-time temporal evolution analysis similar to interactive map*")
    
    # Add CSV Import functionality
    imported_data = _add_csv_import_interface("MCD43A3")
    if imported_data is not None:
        df = imported_data
        st.success("✅ Using imported CSV data for temporal analysis")
    
    # Temporal analysis controls
    with st.sidebar:
        st.markdown("### ⏰ Temporal Controls")
        
        # Analysis mode selection
        analysis_mode = st.radio(
            "Analysis Mode",
            ["Use Existing Data", "Real-time Extraction"],
            key="temporal_mode"
        )
        
        if analysis_mode == "Real-time Extraction":
            # Real-time extraction parameters
            st.markdown("**📅 Date Range**")
            
            # Melt Season Year Selection (following glaciology literature)
            # Based on research: June-September is the standard melt season period
            # References: Williamson & Menounos (2021), Cogley et al. (2011) - Glossary of Glacier Mass Balance
            st.markdown("**📅 Melt Season Period**")
            st.caption("*Following glaciology literature: June 1 - September 30 (JJAS)*")
            
            # Year range selection for melt seasons
            available_years = list(range(2010, 2025))  # MODIS data availability
            
            year_selection_mode = st.radio(
                "Year Selection",
                ["Single Year", "Year Range", "Multiple Years"],
                key="year_selection_mode"
            )
            
            if year_selection_mode == "Single Year":
                selected_year = st.selectbox(
                    "Melt Season Year",
                    available_years,
                    index=available_years.index(2023),  # Default to 2023
                    key="single_year_select"
                )
                start_date = datetime(selected_year, 6, 1)    # June 1
                end_date = datetime(selected_year, 9, 30)     # September 30
                
            elif year_selection_mode == "Year Range":
                col1, col2 = st.columns(2)
                with col1:
                    start_year = st.selectbox(
                        "Start Year",
                        available_years,
                        index=available_years.index(2020),
                        key="start_year_select"
                    )
                with col2:
                    end_year = st.selectbox(
                        "End Year", 
                        available_years,
                        index=available_years.index(2023),
                        key="end_year_select"
                    )
                
                # Validate year range
                if start_year > end_year:
                    st.error("Start year must be ≤ end year")
                    start_year, end_year = end_year, start_year
                
                start_date = datetime(start_year, 6, 1)
                end_date = datetime(end_year, 9, 30)
                
            else:  # Multiple Years
                selected_years = st.multiselect(
                    "Select Melt Season Years",
                    available_years,
                    default=[2021, 2022, 2023],
                    key="multi_year_select"
                )
                
                if not selected_years:
                    st.warning("Please select at least one year")
                    selected_years = [2023]
                
                start_date = datetime(min(selected_years), 6, 1)
                end_date = datetime(max(selected_years), 9, 30)
            
            # Display selected period
            st.info(f"📊 **Selected Period**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Literature reference
            with st.expander("📚 Melt Season Definition (Literature)", expanded=False):
                st.markdown("""
                **Glaciological Definition of Melt Season:**
                
                - **June-September (JJAS)**: Standard melt season for alpine glaciers
                - **Peak melt**: Typically July-August for most glaciers  
                - **Literature Support**:
                  - Williamson & Menounos (2021): "focus on melt season months (June-September)"
                  - Cogley et al. (2011): Glossary of Glacier Mass Balance
                  - Zemp et al. (2015): Global glacier mass balance  
                  - Huss & Hock (2018): Alpine glacier response to climate change
                
                **Regional Variations:**
                - **Arctic glaciers**: May extend to October
                - **Tropical glaciers**: Year-round melt with seasonal peaks
                - **Athabasca Glacier**: Peak melt June-August, extends through September
                """)
            
            # Override dates to fixed melt season format
            # This ensures consistency with glaciology literature
            
            # Band selection for temporal analysis
            band_selection = st.selectbox(
                "Spectral Band",
                ["shortwave", "vis", "nir"],
                index=0,
                help="Shortwave: Full spectrum (recommended), Visible: 0.3-0.7 μm, NIR: 0.7-5.0 μm",
                key="temporal_band"
            )
            
            # Diffuse fraction for Blue-Sky albedo
            diffuse_fraction = st.slider(
                "Diffuse Fraction",
                min_value=0.0,
                max_value=1.0,
                value=0.2,
                step=0.05,
                help="Atmospheric conditions: 0.0=clear sky, 0.2=typical glacier, 1.0=overcast",
                key="temporal_diffuse"
            )
            
            # QA level
            qa_level_temporal = st.selectbox(
                "Quality Level",
                ["strict", "standard"],
                index=1,
                help="Strict: QA=0 only, Standard: QA≤1",
                key="temporal_qa"
            )
            
            # Extraction button
            extract_temporal = st.button(
                "🚀 Extract Temporal Data",
                type="primary",
                key="extract_temporal_btn"
            )
            
            # Cache management and troubleshooting
            st.markdown("**🔧 Extraction Management**")
            
            # Show current cache status
            cache_keys = [key for key in st.session_state.keys() if 'mcd43a3_extraction_' in key]
            if cache_keys:
                st.info(f"📦 **Cache status**: {len(cache_keys)} extraction session(s) in cache")
                
                # Show cache details
                with st.expander("📋 View Cache Details", expanded=False):
                    for key in cache_keys:
                        cached_data = st.session_state[key]
                        if cached_data:
                            dates = [item['date'] for item in cached_data]
                            date_range = f"{min(dates)} to {max(dates)}" if dates else "No dates"
                            st.markdown(f"**{key}**: {len(cached_data)} observations ({date_range})")
            else:
                st.info("📦 **Cache status**: No cached extractions")
            
            # Cache cleanup button for troubleshooting
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear All Cache", 
                            help="Clear all cached extraction data",
                            key="clear_all_cache_btn"):
                    # Clear MCD43A3 extraction cache
                    keys_to_remove = [key for key in st.session_state.keys() if 'mcd43a3_extraction_' in key]
                    for key in keys_to_remove:
                        del st.session_state[key]
                    st.success(f"✅ Cleared {len(keys_to_remove)} cached session(s)")
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset Session", 
                            help="Clear cache and reset all session data",
                            key="reset_session_btn"):
                    # Clear all session state
                    for key in list(st.session_state.keys()):
                        if key.startswith('mcd43a3_') or key.startswith('temporal_'):
                            del st.session_state[key]
                    st.success("✅ Session reset completed")
                    st.rerun()
            
            if extract_temporal:
                # Perform real-time temporal extraction
                from ..analysis.mcd43a3_temporal import extract_mcd43a3_time_series_realtime
                
                temporal_df = extract_mcd43a3_time_series_realtime(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    qa_level=qa_level_temporal,
                    band_selection=band_selection,
                    diffuse_fraction=diffuse_fraction
                )
                
                # Store in session state for analysis
                st.session_state['temporal_mcd43a3_data'] = temporal_df
        
        # Analysis type selection
        analysis_type = st.selectbox(
            "Temporal Analysis",
            ["seasonal", "annual", "monthly", "detailed"],
            format_func=lambda x: {
                "seasonal": "🌱 Seasonal Evolution",
                "annual": "📅 Annual Trends", 
                "monthly": "🗓️ Monthly Patterns",
                "detailed": "🔍 Detailed Timeline"
            }[x],
            key="temporal_analysis_type"
        )
    
    # Determine which data to use
    if analysis_mode == "Real-time Extraction" and 'temporal_mcd43a3_data' in st.session_state:
        temporal_df = st.session_state['temporal_mcd43a3_data']
        st.success("✅ Using real-time extracted temporal data")
    else:
        # Use existing data (transform to temporal format)
        temporal_df = _transform_existing_to_temporal(df)
        if not temporal_df.empty:
            st.info("📊 Using existing MCD43A3 data for temporal analysis")
    
    # Create temporal analysis
    if not temporal_df.empty:
        from ..analysis.mcd43a3_temporal import create_temporal_evolution_plot
        
        fig = create_temporal_evolution_plot(temporal_df, analysis_type)
        st.plotly_chart(fig, use_container_width=True)
        
        # Temporal statistics
        _display_temporal_statistics(temporal_df, analysis_type)
        
        # Add download functionality for temporal data
        if not temporal_df.empty:
            _add_temporal_csv_download(temporal_df, analysis_type)
    else:
        st.warning("No temporal data available. Try real-time extraction or load existing data.")


def _create_interactive_exploration_tab(df):
    """Create interactive exploration tab"""
    st.subheader("🔍 Interactive Data Exploration")
    st.markdown("*Interactive filtering and exploration of MCD43A3 data*")
    
    if df.empty:
        st.warning("No data available for exploration")
        return
        
    # Prepare data
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['doy'] = df['date'].dt.dayofyear
    
    # Interactive filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        year_filter = st.multiselect(
            "📅 Years",
            sorted(df['year'].unique()),
            default=sorted(df['year'].unique())[-3:],
            key="explore_years"
        )
        
    with col2:
        month_filter = st.multiselect(
            "🗓️ Months", 
            list(range(1, 13)),
            default=list(range(6, 10)),  # Melt season default
            format_func=lambda x: datetime(2020, x, 1).strftime('%B'),
            key="explore_months"
        )
        
    with col3:
        # Albedo range filter
        if 'Albedo_BSA_vis' in df.columns:
            albedo_range = st.slider(
                "📊 Albedo Range",
                min_value=float(df['Albedo_BSA_vis'].min()),
                max_value=float(df['Albedo_BSA_vis'].max()),
                value=(float(df['Albedo_BSA_vis'].min()), float(df['Albedo_BSA_vis'].max())),
                step=0.01,
                key="explore_albedo"
            )
    
    # Apply filters
    filtered_df = df[
        (df['year'].isin(year_filter)) &
        (df['month'].isin(month_filter))
    ]
    
    if 'Albedo_BSA_vis' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['Albedo_BSA_vis'] >= albedo_range[0]) &
            (filtered_df['Albedo_BSA_vis'] <= albedo_range[1])
        ]
    
    # Display filtered data
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if not filtered_df.empty:
            # Create scatter plot with filters applied
            fig = px.scatter(
                filtered_df,
                x='doy',
                y='Albedo_BSA_vis' if 'Albedo_BSA_vis' in filtered_df.columns else filtered_df.columns[1],
                color='year',
                size='Albedo_BSA_nir' if 'Albedo_BSA_nir' in filtered_df.columns else None,
                hover_data=['date'],
                title="Interactive MCD43A3 Data Explorer",
                labels={'doy': 'Day of Year', 'Albedo_BSA_vis': 'Visible Albedo'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data matches the current filters")
    
    with col2:
        # Summary statistics for filtered data
        if not filtered_df.empty:
            st.markdown("### 📊 Filtered Data Summary")
            st.metric("Total Records", len(filtered_df))
            st.metric("Date Range", f"{filtered_df['date'].min().strftime('%Y-%m-%d')} to {filtered_df['date'].max().strftime('%Y-%m-%d')}")
            
            if 'Albedo_BSA_vis' in filtered_df.columns:
                st.metric("Mean Visible Albedo", f"{filtered_df['Albedo_BSA_vis'].mean():.3f}")
                st.metric("Std Visible Albedo", f"{filtered_df['Albedo_BSA_vis'].std():.3f}")
            
            # Data table
            st.markdown("### 📋 Sample Data")
            display_cols = ['date', 'Albedo_BSA_vis', 'Albedo_BSA_nir'] if 'Albedo_BSA_vis' in filtered_df.columns else filtered_df.columns[:3]
            st.dataframe(filtered_df[display_cols].head(10), use_container_width=True)


def _create_advanced_analytics_tab(df):
    """Create advanced analytics tab"""
    st.subheader("📈 Advanced MCD43A3 Analytics")
    st.markdown("*Statistical analysis and trend detection*")
    
    if df.empty:
        st.warning("No data available for advanced analytics")
        return
    
    # Prepare data
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    
    # Analytics options
    analytics_type = st.selectbox(
        "Analytics Type",
        ["Trend Analysis", "Correlation Matrix", "Anomaly Detection", "Statistical Summary"],
        key="analytics_type"
    )
    
    if analytics_type == "Trend Analysis":
        _create_trend_analysis(df)
    elif analytics_type == "Correlation Matrix":
        _create_correlation_analysis(df)
    elif analytics_type == "Anomaly Detection":
        _create_anomaly_analysis(df)
    elif analytics_type == "Statistical Summary":
        _create_statistical_summary(df)


# Helper functions for spectral analysis (original functionality)
def _create_seasonal_evolution_plot(filtered_df, selected_years, colors):
    """Create seasonal evolution plot for MCD43A3 data"""
    fig = go.Figure()
    
    for year in selected_years:
        year_data = filtered_df[filtered_df['year'] == year]
        
        if not year_data.empty and 'Albedo_BSA_vis' in year_data.columns:
            year_data = year_data.copy()
            year_data['date_label'] = year_data['date'].dt.strftime('%B %d, %Y')
            
            fig.add_trace(go.Scatter(
                x=year_data['doy'],
                y=year_data['Albedo_BSA_vis'],
                mode='markers',
                name=f'{year} Visible',
                marker=dict(color=colors['Albedo_BSA_vis'], size=6),
                hovertemplate=f'<b>{year} Visible</b><br>📅 Date: %{{customdata}}<br>📊 Albedo: %{{y:.3f}}<br>📈 DOY: %{{x}}<extra></extra>',
                customdata=year_data['date_label']
            ))
    
    fig.update_layout(
        title="MCD43A3 Seasonal Evolution - Daily Albedo",
        xaxis_title="Day of Year",
        yaxis_title="Albedo",
        height=600,
        hovermode='closest'
    )
    
    return fig


def _create_vis_nir_comparison_plot(filtered_df):
    """Create visible vs NIR comparison plot"""
    if 'Albedo_BSA_vis' not in filtered_df.columns or 'Albedo_BSA_nir' not in filtered_df.columns:
        return go.Figure().add_annotation(text="Visible and NIR data not available")
    
    annual_data = filtered_df.groupby('year').agg({
        'Albedo_BSA_vis': 'mean',
        'Albedo_BSA_nir': 'mean'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annual_data['Albedo_BSA_vis'],
        y=annual_data['Albedo_BSA_nir'],
        mode='markers+text',
        text=annual_data['year'],
        textposition='top center',
        marker=dict(size=12, color=annual_data['year'], colorscale='Viridis'),
        hovertemplate='<b>Year %{text}</b><br>📊 Visible Albedo: %{x:.3f}<br>📊 NIR Albedo: %{y:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Annual Visible vs NIR Albedo Comparison",
        xaxis_title="Visible Albedo",
        yaxis_title="NIR Albedo",
        height=600
    )
    
    return fig


def _create_spectral_bands_plot(filtered_df, years, colors):
    """Create spectral bands plot"""
    recent_year = years[-1] if years else 2023
    recent_data = filtered_df[filtered_df['year'] == recent_year]
    
    fig = go.Figure()
    
    if not recent_data.empty:
        recent_data = recent_data.copy()
        recent_data['date_label'] = recent_data['date'].dt.strftime('%B %d, %Y')
    
    for band, color in colors.items():
        if band in recent_data.columns:
            fig.add_trace(go.Scatter(
                x=recent_data['doy'],
                y=recent_data[band],
                mode='markers',
                name=band.replace('Albedo_BSA_', ''),
                marker=dict(color=color, size=6),
                hovertemplate=f'<b>{band.replace("Albedo_BSA_", "")}</b><br>📅 Date: %{{customdata}}<br>📊 Albedo: %{{y:.3f}}<br>📈 DOY: %{{x}}<extra></extra>',
                customdata=recent_data['date_label'] if not recent_data.empty else []
            ))
    
    fig.update_layout(
        title=f"All Spectral Bands - {recent_year}",
        xaxis_title="Day of Year", 
        yaxis_title="Albedo",
        height=600
    )
    
    return fig


def _create_vis_nir_ratio_plot(filtered_df):
    """Create visible/NIR ratio plot"""
    if 'Albedo_BSA_vis' not in filtered_df.columns or 'Albedo_BSA_nir' not in filtered_df.columns:
        return go.Figure().add_annotation(text="Visible and NIR data not available for ratio calculation")
    
    filtered_df = filtered_df.copy()
    filtered_df['vis_nir_ratio'] = filtered_df['Albedo_BSA_vis'] / filtered_df['Albedo_BSA_nir']
    
    ratio_annual = filtered_df.groupby('year')['vis_nir_ratio'].mean().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ratio_annual['year'],
        y=ratio_annual['vis_nir_ratio'],
        mode='markers+lines',
        name='Vis/NIR Ratio',
        marker=dict(size=8, color='purple'),
        line=dict(color='purple', width=2),
        hovertemplate='<b>Vis/NIR Ratio</b><br>🗓️ Year: %{x}<br>📊 Ratio: %{y:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Visible/NIR Ratio Trends Over Time",
        xaxis_title="Year",
        yaxis_title="Vis/NIR Ratio",
        height=600
    )
    
    return fig


# Helper functions for new functionality
def _transform_existing_to_temporal(df):
    """Transform existing MCD43A3 data to temporal format"""
    if df.empty:
        return pd.DataFrame()
        
    # Assuming main visible albedo column exists
    temporal_df = df.copy()
    if 'Albedo_BSA_vis' in temporal_df.columns:
        temporal_df = temporal_df.rename(columns={'Albedo_BSA_vis': 'albedo_mean'})
        temporal_df['albedo_std'] = 0.0  # No std available from existing data
        temporal_df['pixel_count'] = 20  # Estimated
        temporal_df['band_type'] = 'vis'
        temporal_df['diffuse_fraction'] = 0.2
        temporal_df['qa_level'] = 'standard'
        
        # Ensure required columns
        temporal_df['date'] = pd.to_datetime(temporal_df['date'])
        temporal_df['year'] = temporal_df['date'].dt.year
        temporal_df['doy'] = temporal_df['date'].dt.dayofyear
        temporal_df['month'] = temporal_df['date'].dt.month
        
        return temporal_df[['date', 'albedo_mean', 'albedo_std', 'pixel_count', 
                          'band_type', 'diffuse_fraction', 'qa_level', 'year', 'doy', 'month']]
    
    return pd.DataFrame()


def _display_spectral_statistics(filtered_df, selected_years):
    """Display data statistics for spectral analysis"""
    st.subheader("📊 Spectral Data Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Observations", len(filtered_df))
    with col2:
        st.metric("Years of Data", len(selected_years))
    with col3:
        if 'Albedo_BSA_vis' in filtered_df.columns:
            st.metric("Mean Visible Albedo", f"{filtered_df['Albedo_BSA_vis'].mean():.3f}")
    with col4:
        if 'Albedo_BSA_nir' in filtered_df.columns:
            st.metric("Mean NIR Albedo", f"{filtered_df['Albedo_BSA_nir'].mean():.3f}")


def _display_temporal_statistics(temporal_df, analysis_type):
    """Display temporal statistics"""
    st.subheader("📊 Temporal Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Observations", len(temporal_df))
    with col2:
        date_range = temporal_df['date'].max() - temporal_df['date'].min()
        st.metric("Time Span", f"{date_range.days} days")
    with col3:
        st.metric("Mean Albedo", f"{temporal_df['albedo_mean'].mean():.3f}")
    with col4:
        st.metric("Albedo Std", f"{temporal_df['albedo_mean'].std():.3f}")


def _create_trend_analysis(df):
    """Create trend analysis"""
    st.markdown("### 📈 Trend Analysis")
    
    if 'Albedo_BSA_vis' in df.columns:
        # Annual trends
        annual_means = df.groupby('year')['Albedo_BSA_vis'].mean()
        
        # Simple linear trend
        import numpy as np
        years = annual_means.index.values
        albedos = annual_means.values
        
        # Linear regression
        z = np.polyfit(years, albedos, 1)
        p = np.poly1d(z)
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years,
            y=albedos,
            mode='markers+lines',
            name='Annual Mean',
            marker=dict(size=10)
        ))
        fig.add_trace(go.Scatter(
            x=years,
            y=p(years),
            mode='lines',
            name=f'Trend (slope: {z[0]:.4f}/year)',
            line=dict(dash='dash')
        ))
        
        fig.update_layout(
            title="MCD43A3 Annual Albedo Trends",
            xaxis_title="Year",
            yaxis_title="Mean Albedo",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Trend Slope", f"{z[0]:.6f} per year")
        with col2:
            total_change = z[0] * (years[-1] - years[0])
            st.metric("Total Change", f"{total_change:.4f}")


def _create_correlation_analysis(df):
    """Create correlation analysis"""
    st.markdown("### 🔗 Correlation Analysis")
    
    # Select numeric columns for correlation
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    spectral_cols = [col for col in numeric_cols if 'Albedo_BSA' in col]
    
    if len(spectral_cols) > 1:
        corr_matrix = df[spectral_cols].corr()
        
        fig = px.imshow(
            corr_matrix,
            title="Spectral Band Correlation Matrix",
            color_continuous_scale='RdBu',
            aspect='auto'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display correlation values
        st.dataframe(corr_matrix, use_container_width=True)


def _create_anomaly_analysis(df):
    """Create anomaly detection analysis"""
    st.markdown("### 🚨 Anomaly Detection")
    
    if 'Albedo_BSA_vis' in df.columns:
        # Simple anomaly detection using z-score
        mean_albedo = df['Albedo_BSA_vis'].mean()
        std_albedo = df['Albedo_BSA_vis'].std()
        
        # Calculate z-scores
        df = df.copy()
        df['z_score'] = (df['Albedo_BSA_vis'] - mean_albedo) / std_albedo
        
        # Define anomalies as |z-score| > 2
        anomalies = df[abs(df['z_score']) > 2]
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['Albedo_BSA_vis'],
            mode='markers',
            name='Normal',
            marker=dict(color='blue', size=6)
        ))
        
        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies['date'],
                y=anomalies['Albedo_BSA_vis'],
                mode='markers',
                name='Anomalies',
                marker=dict(color='red', size=10, symbol='x')
            ))
        
        fig.update_layout(
            title="MCD43A3 Anomaly Detection",
            xaxis_title="Date",
            yaxis_title="Visible Albedo",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Anomalies", len(anomalies))
        with col2:
            anomaly_rate = len(anomalies) / len(df) * 100
            st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")


def _create_statistical_summary(df):
    """Create statistical summary"""
    st.markdown("### 📊 Statistical Summary")
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    spectral_cols = [col for col in numeric_cols if 'Albedo_BSA' in col]
    
    if spectral_cols:
        summary_stats = df[spectral_cols].describe()
        st.dataframe(summary_stats, use_container_width=True)
        
        # Additional statistics
        st.markdown("### 📈 Additional Statistics")
        
        for col in spectral_cols:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{col} - Skewness", f"{df[col].skew():.3f}")
            with col2:
                st.metric(f"{col} - Kurtosis", f"{df[col].kurtosis():.3f}")
            with col3:
                st.metric(f"{col} - Range", f"{df[col].max() - df[col].min():.3f}")


def _add_temporal_csv_download(temporal_df, analysis_type):
    """Add CSV download functionality for temporal data"""
    import io
    from datetime import datetime
    
    st.markdown("---")
    st.markdown("### 📥 Download Temporal Data")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"mcd43a3_temporal_{analysis_type}_{timestamp}"
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Full temporal dataset download
        csv_buffer = io.StringIO()
        temporal_df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📊 Download Full Temporal Data",
            data=csv_data,
            file_name=f"{base_filename}_full.csv",
            mime="text/csv",
            help=f"Download complete temporal dataset ({len(temporal_df)} observations)"
        )
    
    with col2:
        # Summary statistics download
        if analysis_type == 'seasonal':
            # Group by year and DOY for seasonal analysis
            summary_stats = temporal_df.groupby(['year', 'doy']).agg({
                'albedo_mean': ['mean', 'std', 'count'],
                'pixel_count': 'mean'
            }).round(4)
        elif analysis_type == 'annual':
            # Group by year for annual analysis
            summary_stats = temporal_df.groupby('year').agg({
                'albedo_mean': ['mean', 'std', 'min', 'max', 'count'],
                'pixel_count': 'mean'
            }).round(4)
        elif analysis_type == 'monthly':
            # Group by year and month for monthly analysis
            summary_stats = temporal_df.groupby(['year', 'month']).agg({
                'albedo_mean': ['mean', 'std', 'count'],
                'pixel_count': 'mean'
            }).round(4)
        else:  # detailed
            # Group by date for detailed analysis
            summary_stats = temporal_df.groupby('date').agg({
                'albedo_mean': ['mean', 'std'],
                'pixel_count': 'mean'
            }).round(4)
        
        # Flatten column names
        summary_stats.columns = ['_'.join(col).strip() for col in summary_stats.columns]
        summary_stats = summary_stats.reset_index()
        
        summary_buffer = io.StringIO()
        summary_stats.to_csv(summary_buffer, index=False, encoding='utf-8')
        summary_data = summary_buffer.getvalue()
        
        st.download_button(
            label="📈 Download Summary Statistics",
            data=summary_data,
            file_name=f"{base_filename}_summary.csv",
            mime="text/csv",
            help=f"Download {analysis_type} summary statistics"
        )
    
    # Dataset information
    st.markdown("**📋 Dataset Information:**")
    st.markdown(f"""
    - **Analysis Type**: {analysis_type.title()}
    - **Observations**: {len(temporal_df)}
    - **Date Range**: {temporal_df['date'].min().strftime('%Y-%m-%d')} to {temporal_df['date'].max().strftime('%Y-%m-%d')}
    - **Years Covered**: {sorted(temporal_df['year'].unique())}
    """)
    
    if 'band_type' in temporal_df.columns:
        st.markdown(f"- **Band Type**: {temporal_df['band_type'].iloc[0]}")
    if 'qa_level' in temporal_df.columns:
        st.markdown(f"- **Quality Level**: {temporal_df['qa_level'].iloc[0]}")
    if 'diffuse_fraction' in temporal_df.columns:
        st.markdown(f"- **Diffuse Fraction**: {temporal_df['diffuse_fraction'].iloc[0]:.2f}")


def _add_csv_import_interface(product_type="MCD43A3"):
    """Add CSV import interface for temporal data"""
    with st.expander("📁 Import Custom CSV Data", expanded=False):
        st.markdown(f"*Upload your own {product_type} temporal data*")
        
        # File upload
        uploaded_file = st.file_uploader(
            f"Choose {product_type} CSV file",
            type=['csv'],
            help=f"Upload CSV with temporal {product_type} data",
            key=f"csv_import_{product_type.lower()}_temporal"
        )
        
        if uploaded_file is not None:
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
                    st.error("❌ Could not read the CSV file with any encoding")
                    return None
                
                # Validate required columns
                required_cols, validated_df = _validate_temporal_csv(df_imported, product_type)
                
                if validated_df is not None:
                    # Show file information
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Observations", len(validated_df))
                    with col2:
                        if 'date' in validated_df.columns:
                            date_range = validated_df['date'].max() - validated_df['date'].min()
                            st.metric("Time Span", f"{date_range.days} days")
                        else:
                            st.metric("Time Span", "Unknown")
                    with col3:
                        if 'albedo_mean' in validated_df.columns:
                            st.metric("Mean Albedo", f"{validated_df['albedo_mean'].mean():.3f}")
                        else:
                            st.metric("Mean Albedo", "N/A")
                    
                    # Option to preview data
                    if st.checkbox("👁️ Preview imported data", key=f"preview_{product_type.lower()}"):
                        st.dataframe(validated_df.head(10), use_container_width=True)
                    
                    st.success(f"✅ {product_type} CSV data loaded successfully!")
                    return validated_df
                else:
                    return None
                    
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {e}")
                return None
    
    return None


def _validate_temporal_csv(df, product_type):
    """Validate CSV data for temporal analysis"""
    required_cols = ['date', 'albedo_mean']
    
    # Product-specific validation
    if product_type == "MCD43A3":
        # Check for spectral columns
        spectral_cols = ['Albedo_BSA_vis', 'Albedo_BSA_nir', 'Albedo_BSA_shortwave']
        optional_cols = spectral_cols + ['band_type', 'diffuse_fraction', 'qa_level']
    else:
        # MOD10A1 or other products
        optional_cols = ['pixel_count', 'satellite_source', 'qa_level']
    
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
                        st.info(f"✅ Using '{original_name}' as '{req_col}' column")
                        found_alternative = True
                        break
            
            if not found_alternative:
                missing_required.append(req_col)
    
    if missing_required:
        st.error(f"❌ Missing required columns: {missing_required}")
        st.markdown("**Required columns for temporal analysis:**")
        st.markdown("- `date` (or date_str, observation_date, time, datetime)")
        st.markdown("- `albedo_mean` (or albedo, mean_albedo, albedo_avg)")
        
        if product_type == "MCD43A3":
            st.markdown("**Optional MCD43A3-specific columns:**")
            st.markdown("- `Albedo_BSA_vis`, `Albedo_BSA_nir`, `Albedo_BSA_shortwave`")
            st.markdown("- `band_type`, `diffuse_fraction`, `qa_level`")
        
        st.markdown("**Available columns in your file:**")
        st.write(list(df.columns))
        return required_cols, None
    
    # Convert date column to datetime
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        st.error(f"❌ Could not parse dates: {e}")
        st.markdown("Make sure dates are in a standard format (YYYY-MM-DD, YYYY/MM/DD, etc.)")
        return required_cols, None
    
    # Add derived temporal columns if missing
    if 'year' not in df.columns:
        df['year'] = df['date'].dt.year
    if 'month' not in df.columns:
        df['month'] = df['date'].dt.month
    if 'doy' not in df.columns:
        df['doy'] = df['date'].dt.dayofyear
    
    # Validate albedo values
    if 'albedo_mean' in df.columns:
        albedo_values = df['albedo_mean'].dropna()
        if not albedo_values.empty:
            min_albedo = albedo_values.min()
            max_albedo = albedo_values.max()
            
            if min_albedo < 0 or max_albedo > 1:
                st.warning(f"⚠️ Albedo values outside normal range (0-1): {min_albedo:.3f} to {max_albedo:.3f}")
                
                # Offer to auto-scale if values look like they need scaling
                if max_albedo > 1 and max_albedo <= 100:
                    if st.button("🔧 Auto-scale albedo values (divide by 100)", key=f"autoscale_{product_type}"):
                        df['albedo_mean'] = df['albedo_mean'] / 100
                        st.success("✅ Albedo values scaled successfully")
                        st.rerun()
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    st.info(f"📊 Data validation complete: {len(df)} observations from {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
    
    return required_cols, df


def _get_melt_season_info():
    """Get standardized melt season information based on glaciology literature"""
    return {
        "period": "June 1 - September 30",
        "abbreviation": "JJAS (June-July-August-September)",
        "rationale": """
        **Glaciological Definition of Melt Season (Literature-Based):**
        
        **Standard Period: June-September (JJAS)**
        - **Primary melt season** for alpine and arctic glaciers
        - **Peak ablation** typically occurs in July-August
        - **Consistent** with international glaciology standards
        
        **Key Literature Support:**
        - **Williamson & Menounos (2021)**: "focus on melt season months (June-September)" for glacier albedo analysis
        - **Cogley et al. (2011)**: Glossary of Glacier Mass Balance - standardized terminology
        - **Zemp et al. (2015)**: Global glacier mass balance seasonal analysis
        - **Huss & Hock (2018)**: Alpine glacier seasonal response patterns
        - **Gardner et al. (2013)**: Arctic glacier mass balance seasonality
        
        **Regional Context:**
        - **Canadian Rockies (Athabasca)**: Peak melt June-August, extends through September
        - **Arctic**: May extend into early October depending on latitude
        - **High altitude sites**: Season may be shorter (July-August core period)
        
        **MODIS Data Considerations:**
        - **Optimal coverage**: Summer months have maximum cloud-free observations
        - **Snow vs ice albedo**: Clear differentiation during melt season
        - **Temporal resolution**: Captures rapid albedo changes during ablation
        """,
        "start_month": 6,
        "start_day": 1,
        "end_month": 9,
        "end_day": 30
    }