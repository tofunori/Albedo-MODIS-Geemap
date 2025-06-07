"""
Streamlit Web Dashboard for Athabasca Glacier Albedo Analysis
Live online dashboard that reads CSV data from web sources
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import time
import requests
from io import StringIO
import folium
from streamlit_folium import st_folium
import json

# Page configuration
st.set_page_config(
    page_title="Athabasca Glacier Albedo Dashboard",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration for data sources
DATA_SOURCES = {
    'mcd43a3': {
        'url': 'https://raw.githubusercontent.com/tofunori/Albedo-MODIS-Geemap/main/outputs/csv/athabasca_mcd43a3_spectral_data.csv',
        'local_fallback': '../outputs/csv/athabasca_mcd43a3_spectral_data.csv',
        'description': 'MCD43A3 Spectral Time Series Data'
    },
    'melt_season': {
        'url': 'https://raw.githubusercontent.com/tofunori/Albedo-MODIS-Geemap/main/outputs/csv/athabasca_melt_season_data.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_data.csv',
        'description': 'MOD10A1/MYD10A1 Daily Snow Albedo Time Series'
    },
    'melt_season_results': {
        'url': 'https://raw.githubusercontent.com/tofunori/Albedo-MODIS-Geemap/main/outputs/csv/athabasca_melt_season_results.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_results.csv',
        'description': 'MOD10A1/MYD10A1 Statistical Trend Analysis'
    },
    'melt_season_focused': {
        'url': 'https://raw.githubusercontent.com/tofunori/Albedo-MODIS-Geemap/main/outputs/csv/athabasca_melt_season_focused_data.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_focused_data.csv',
        'description': 'MOD10A1/MYD10A1 Focused Quality Data'
    },
    'hypsometric': {
        'url': 'https://raw.githubusercontent.com/tofunori/Albedo-MODIS-Geemap/main/outputs/csv/athabasca_hypsometric_results.csv',
        'local_fallback': '../outputs/csv/athabasca_hypsometric_results.csv',
        'description': 'Hypsometric Analysis Results'
    }
}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def initialize_earth_engine():
    """
    Initialize Earth Engine with proper authentication
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import ee
        
        # Try to initialize (may work if already authenticated)
        try:
            ee.Initialize()
            return True
        except:
            # Try service account authentication
            try:
                import os
                
                # Check for service account key file
                possible_paths = [
                    os.path.expanduser('~/.config/earthengine/credentials'),
                    os.path.join(os.getcwd(), 'ee-service-account.json'),
                    os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
                ]
                
                for key_path in possible_paths:
                    if os.path.exists(key_path):
                        ee.Initialize()
                        return True
                
                # If no service account, try interactive auth
                st.info("🔐 Earth Engine authentication required for pixel visualization")
                st.info("💡 Please run 'earthengine authenticate' in your terminal")
                return False
                
            except Exception as e:
                st.warning(f"Earth Engine initialization failed: {e}")
                return False
                
    except ImportError:
        st.error("Earth Engine library not installed. Install with: pip install earthengine-api")
        return False

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_url(url, fallback_path=None):
    """
    Load CSV data from URL with local fallback
    """
    try:
        # Try to load from URL first
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse CSV from response
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        st.success(f"✅ Data loaded from online source: {len(df)} records")
        return df, "online"
        
    except Exception as e:
        st.warning(f"⚠️ Could not load from URL: {str(e)}")
        
        # Fallback to local file if available
        if fallback_path:
            try:
                df = pd.read_csv(fallback_path)
                st.info(f"📁 Using local fallback data: {len(df)} records")
                return df, "local"
            except Exception as local_e:
                st.error(f"❌ Local fallback also failed: {str(local_e)}")
                return pd.DataFrame(), "failed"
        
        return pd.DataFrame(), "failed"

def create_mcd43a3_dashboard(df):
    """
    Create MCD43A3 spectral analysis dashboard
    """
    if df.empty:
        st.error("No MCD43A3 data available")
        return
    
    # Prepare data
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['doy'] = df['date'].dt.dayofyear
    
    # Sidebar controls
    st.sidebar.header("🌈 MCD43A3 Controls")
    
    # Year selection
    years = sorted(df['year'].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years", 
        years, 
        default=years[-3:] if len(years) >= 3 else years
    )
    
    # View type selection
    view_type = st.sidebar.selectbox(
        "Dashboard View",
        ["Seasonal Evolution", "Visible vs NIR", "Spectral Bands", "Vis/NIR Ratio"]
    )
    
    # Filter data
    filtered_df = df[df['year'].isin(selected_years)]
    
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
        fig = go.Figure()
        
        for year in selected_years:
            year_data = filtered_df[filtered_df['year'] == year]
            
            if not year_data.empty and 'Albedo_BSA_vis' in year_data.columns:
                fig.add_trace(go.Scatter(
                    x=year_data['doy'],
                    y=year_data['Albedo_BSA_vis'],
                    mode='markers',
                    name=f'{year} Visible',
                    marker=dict(color=colors['Albedo_BSA_vis'], size=6),
                    hovertemplate=f'<b>{year} Visible</b><br>DOY: %{{x}}<br>Albedo: %{{y:.3f}}<extra></extra>'
                ))
                
            if not year_data.empty and 'Albedo_BSA_nir' in year_data.columns:
                fig.add_trace(go.Scatter(
                    x=year_data['doy'],
                    y=year_data['Albedo_BSA_nir'],
                    mode='markers',
                    name=f'{year} NIR',
                    marker=dict(color=colors['Albedo_BSA_nir'], size=6, symbol='square'),
                    hovertemplate=f'<b>{year} NIR</b><br>DOY: %{{x}}<br>Albedo: %{{y:.3f}}<extra></extra>'
                ))
        
        fig.update_layout(
            title="MCD43A3 Seasonal Evolution - Daily Albedo",
            xaxis_title="Day of Year",
            yaxis_title="Albedo",
            height=600,
            hovermode='closest'
        )
        
    elif view_type == "Visible vs NIR":
        # Annual means
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
            hovertemplate='<b>Year %{text}</b><br>Visible: %{x:.3f}<br>NIR: %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Annual Visible vs NIR Albedo Comparison",
            xaxis_title="Visible Albedo",
            yaxis_title="NIR Albedo",
            height=600
        )
        
    elif view_type == "Spectral Bands":
        recent_year = selected_years[-1] if selected_years else years[-1]
        recent_data = df[df['year'] == recent_year]
        
        fig = go.Figure()
        
        for band, color in colors.items():
            if band in recent_data.columns:
                fig.add_trace(go.Scatter(
                    x=recent_data['doy'],
                    y=recent_data[band],
                    mode='markers',
                    name=band.replace('Albedo_BSA_', ''),
                    marker=dict(color=color, size=6),
                    hovertemplate=f'<b>{band.replace("Albedo_BSA_", "")}</b><br>DOY: %{{x}}<br>Albedo: %{{y:.3f}}<extra></extra>'
                ))
        
        fig.update_layout(
            title=f"All Spectral Bands - {recent_year}",
            xaxis_title="Day of Year",
            yaxis_title="Albedo",
            height=600
        )
        
    elif view_type == "Vis/NIR Ratio":
        if 'Albedo_BSA_vis' in filtered_df.columns and 'Albedo_BSA_nir' in filtered_df.columns:
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
                hovertemplate='<b>Vis/NIR Ratio</b><br>Year: %{x}<br>Ratio: %{y:.3f}<extra></extra>'
            ))
            
            fig.update_layout(
                title="Visible/NIR Ratio Trends Over Time",
                xaxis_title="Year",
                yaxis_title="Vis/NIR Ratio",
                height=600
            )
        else:
            st.error("Visible and NIR data not available for ratio calculation")
            return
    
    # Display plot
    st.plotly_chart(fig, use_container_width=True)
    
    # Data statistics
    st.subheader("📊 Data Statistics")
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

def create_williamson_menounos_dashboard(df_data, df_results, df_focused):
    """
    Create comprehensive MOD10A1/MYD10A1 melt season analysis dashboard
    Following Williamson & Menounos 2021 methodology
    """
    st.subheader("🌊 MOD10A1/MYD10A1 Daily Snow Albedo Analysis")
    st.markdown("*Following Williamson & Menounos (2021) methodology*")
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Trend Analysis", "📊 Time Series", "🔍 Focused Analysis", "🏆 Extreme Values", "📋 Statistical Summary"])
    
    with tab1:
        st.markdown("### Statistical Trend Analysis Results")
        
        if not df_results.empty:
            # Display results as metrics
            col1, col2, col3 = st.columns(3)
            
            # Annual analysis
            annual_row = df_results[df_results['analysis_type'] == 'Annual Melt Season']
            if not annual_row.empty:
                with col1:
                    trend = annual_row.iloc[0]['trend']
                    p_val = annual_row.iloc[0]['p_value']
                    pct_change = annual_row.iloc[0]['percent_change_per_year']
                    significance = annual_row.iloc[0]['significance']
                    
                    st.metric(
                        "Annual Melt Season Trend",
                        f"{pct_change:.2f}% per year",
                        delta=f"p={p_val:.4f} ({significance})"
                    )
            
            # Create trend visualization
            fig_trends = go.Figure()
            
            # Filter out annual for monthly comparison
            monthly_data = df_results[df_results['analysis_type'] != 'Annual Melt Season']
            
            if not monthly_data.empty:
                months = monthly_data['analysis_type'].str.replace(' Only', '')
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']  # Blue, orange, green, red
                
                fig_trends.add_trace(go.Bar(
                    x=months,
                    y=monthly_data['percent_change_per_year'],
                    marker_color=[colors[i % len(colors)] for i in range(len(months))],
                    text=[f"{val:.2f}%" for val in monthly_data['percent_change_per_year']],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Change: %{y:.2f}% per year<br>' +
                                 'P-value: %{customdata:.4f}<br>' +
                                 '<extra></extra>',
                    customdata=monthly_data['p_value']
                ))
                
                fig_trends.update_layout(
                    title="Monthly Albedo Trends (% Change per Year)",
                    xaxis_title="Month",
                    yaxis_title="Percent Change per Year (%)",
                    height=500,
                    showlegend=False
                )
                
                # Add significance line
                fig_trends.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
                
                st.plotly_chart(fig_trends, use_container_width=True)
            
            # Display detailed results table
            st.markdown("### Detailed Statistical Results")
            st.dataframe(df_results, use_container_width=True)
    
    with tab2:
        st.markdown("### Time Series Analysis")
        
        if not df_data.empty:
            # Prepare data
            df_data_copy = df_data.copy()
            df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
            
            # Sidebar controls for time series
            st.sidebar.header("🌊 Time Series Controls")
            
            # Year selection
            years = sorted(df_data_copy['year'].unique())
            selected_years = st.sidebar.multiselect(
                "Select Years", 
                years, 
                default=years[-5:] if len(years) >= 5 else years,
                key="williamson_years"
            )
            
            # Month selection
            months = sorted(df_data_copy['month'].unique())
            selected_months = st.sidebar.multiselect(
                "Select Months",
                months,
                default=months,
                key="williamson_months"
            )
            
            # Filter data
            filtered_df = df_data_copy[
                (df_data_copy['year'].isin(selected_years)) & 
                (df_data_copy['month'].isin(selected_months))
            ]
            
            if not filtered_df.empty:
                # Create view selection for time series
                view_option = st.radio(
                    "Time Series View:",
                    ["Seasonal Overlay (Same Timeframe)", "Chronological (Side by Side)"],
                    horizontal=True
                )
                
                # Time series plot
                fig_ts = go.Figure()
                
                if view_option == "Seasonal Overlay (Same Timeframe)":
                    # Calculate day of year for seasonal overlay
                    filtered_df_copy = filtered_df.copy()
                    filtered_df_copy['doy'] = pd.to_datetime(filtered_df_copy['date']).dt.dayofyear
                    
                    for year in selected_years:
                        year_data = filtered_df_copy[filtered_df_copy['year'] == year]
                        
                        if not year_data.empty:
                            fig_ts.add_trace(go.Scatter(
                                x=year_data['doy'],
                                y=year_data['albedo_mean'],
                                mode='markers',
                                name=f'{year}',
                                marker=dict(
                                    size=6,
                                    opacity=0.7,
                                    line=dict(width=1, color='white')
                                ),
                                hovertemplate=f'<b>{year}</b><br>' +
                                             'Date: %{customdata[0]}<br>' +
                                             'DOY: %{x}<br>' +
                                             'Mean Albedo: %{y:.3f}<br>' +
                                             'Pixel Count: %{customdata[1]}<br>' +
                                             '<extra></extra>',
                                customdata=list(zip(
                                    year_data['date'].dt.strftime('%Y-%m-%d'),
                                    year_data['pixel_count']
                                ))
                            ))
                    
                    fig_ts.update_layout(
                        title="Seasonal Albedo Evolution - All Years Overlaid",
                        xaxis_title="Day of Year",
                        yaxis_title="Mean Albedo",
                        height=600,
                        hovermode='closest',
                        xaxis=dict(
                            tickvals=[152, 182, 213, 244, 274],
                            ticktext=["Jun 1", "Jul 1", "Aug 1", "Sep 1", "Oct 1"]
                        ),
                        yaxis=dict(
                            dtick=0.05,  # Increment of 0.05
                            tickformat=".2f"  # Two decimal places
                        )
                    )
                
                else:  # Chronological view
                    for year in selected_years:
                        year_data = filtered_df[filtered_df['year'] == year]
                        
                        if not year_data.empty:
                            fig_ts.add_trace(go.Scatter(
                                x=year_data['date'],
                                y=year_data['albedo_mean'],
                                mode='markers',
                                name=f'{year}',
                                marker=dict(
                                    size=6,
                                    opacity=0.7,
                                    line=dict(width=1, color='white')
                                ),
                                hovertemplate=f'<b>{year}</b><br>' +
                                             'Date: %{x}<br>' +
                                             'Mean Albedo: %{y:.3f}<br>' +
                                             'Pixel Count: %{customdata}<br>' +
                                             '<extra></extra>',
                                customdata=year_data['pixel_count']
                            ))
                    
                    fig_ts.update_layout(
                        title="Daily Albedo Evolution During Melt Season",
                        xaxis_title="Date",
                        yaxis_title="Mean Albedo",
                        height=600,
                        hovermode='closest',
                        yaxis=dict(
                            dtick=0.05,  # Increment of 0.05
                            tickformat=".2f"  # Two decimal places
                        )
                    )
                
                st.plotly_chart(fig_ts, use_container_width=True)
                
                # Monthly box plot
                fig_box = go.Figure()
                
                month_names = {6: 'June', 7: 'July', 8: 'August', 9: 'September'}
                
                for month in selected_months:
                    month_data = filtered_df[filtered_df['month'] == month]
                    
                    if not month_data.empty:
                        fig_box.add_trace(go.Box(
                            y=month_data['albedo_mean'],
                            name=month_names.get(month, f'Month {month}'),
                            boxpoints='outliers'
                        ))
                
                fig_box.update_layout(
                    title="Monthly Albedo Distribution",
                    xaxis_title="Month",
                    yaxis_title="Mean Albedo",
                    height=400,
                    yaxis=dict(
                        dtick=0.05,  # Increment of 0.05
                        tickformat=".2f"  # Two decimal places
                    )
                )
                
                st.plotly_chart(fig_box, use_container_width=True)
    
    with tab3:
        st.markdown("### Focused Analysis Data")
        
        if not df_focused.empty:
            # Prepare focused data
            df_focused_copy = df_focused.copy()
            df_focused_copy['date'] = pd.to_datetime(df_focused_copy['date'])
            
            # Show data summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", len(df_focused_copy))
            with col2:
                st.metric("Years Covered", df_focused_copy['year'].nunique())
            with col3:
                st.metric("Mean Albedo", f"{df_focused_copy['albedo_mean'].mean():.3f}")
            with col4:
                st.metric("Mean Pixels", f"{df_focused_copy['pixel_count'].mean():.0f}")
            
            # Focused time series
            fig_focused = go.Figure()
            
            years_focused = sorted(df_focused_copy['year'].unique())
            
            for year in years_focused:
                year_data = df_focused_copy[df_focused_copy['year'] == year]
                
                fig_focused.add_trace(go.Scatter(
                    x=year_data['date'],
                    y=year_data['albedo_mean'],
                    mode='markers',
                    name=f'{year}',
                    marker=dict(
                        size=8,
                        opacity=0.7,
                        line=dict(width=1, color='white')
                    ),
                    hovertemplate=f'<b>{year}</b><br>' +
                                 'Date: %{customdata[3]}<br>' +
                                 'Mean: %{y:.3f}<br>' +
                                 'Range: %{customdata[0]:.3f} - %{customdata[1]:.3f}<br>' +
                                 'Pixels: %{customdata[2]}<br>' +
                                 '<extra></extra>',
                    customdata=list(zip(
                        year_data['albedo_min'], 
                        year_data['albedo_max'], 
                        year_data['pixel_count'],
                        year_data['date'].dt.strftime('%Y-%m-%d')
                    ))
                ))
            
            fig_focused.update_layout(
                title="Focused Melt Season Analysis",
                xaxis_title="Date",
                yaxis_title="Mean Albedo",
                height=600,
                yaxis=dict(
                    dtick=0.05,  # Increment of 0.05
                    tickformat=".2f"  # Two decimal places
                )
            )
            
            st.plotly_chart(fig_focused, use_container_width=True)
            
            # Show sample data
            st.markdown("### Sample Focused Data")
            st.dataframe(df_focused_copy.head(20), use_container_width=True)
    
    with tab4:
        st.markdown("### 🏆 Extreme Albedo Values by Year")
        
        if not df_data.empty:
            # Prepare data
            df_data_copy = df_data.copy()
            df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
            
            # Sidebar controls for extreme values
            st.sidebar.header("🏆 Extreme Values Controls")
            
            # Number of extreme values to show
            n_extreme = st.sidebar.selectbox(
                "Number of extreme values per year",
                [3, 5, 10],
                index=1,  # Default to 5
                key="n_extreme"
            )
            
            # Year selection for extreme values
            years_extreme = sorted(df_data_copy['year'].unique())
            selected_years_extreme = st.sidebar.multiselect(
                "Select Years for Extreme Analysis", 
                years_extreme, 
                default=years_extreme[-3:] if len(years_extreme) >= 3 else years_extreme,
                key="extreme_years"
            )
            
            if selected_years_extreme:
                # Create two columns for lowest and highest
                col_low, col_high = st.columns(2)
                
                with col_low:
                    st.markdown(f"#### ❄️ {n_extreme} Lowest Albedo Days per Year")
                    
                    # Get lowest values for each year
                    lowest_by_year = []
                    for year in selected_years_extreme:
                        year_data = df_data_copy[df_data_copy['year'] == year]
                        if not year_data.empty:
                            lowest = year_data.nsmallest(n_extreme, 'albedo_mean')[
                                ['date', 'albedo_mean', 'pixel_count', 'year']
                            ].copy()
                            lowest['rank'] = range(1, len(lowest) + 1)
                            lowest_by_year.append(lowest)
                    
                    if lowest_by_year:
                        all_lowest = pd.concat(lowest_by_year, ignore_index=True)
                        
                        # Create visualization for lowest values
                        fig_low = go.Figure()
                        
                        for year in selected_years_extreme:
                            year_lowest = all_lowest[all_lowest['year'] == year]
                            if not year_lowest.empty:
                                fig_low.add_trace(go.Scatter(
                                    x=year_lowest['date'],
                                    y=year_lowest['albedo_mean'],
                                    mode='markers',
                                    name=f'{year} Lowest',
                                    marker=dict(
                                        size=10,
                                        opacity=0.8,
                                        line=dict(width=2, color='white'),
                                        symbol='triangle-down'
                                    ),
                                    hovertemplate=f'<b>{year} - Rank %{{customdata[0]}}</b><br>' +
                                                 'Date: %{customdata[1]}<br>' +
                                                 'Albedo: %{y:.3f}<br>' +
                                                 'Pixels: %{customdata[2]}<br>' +
                                                 '<extra></extra>',
                                    customdata=list(zip(
                                        year_lowest['rank'],
                                        year_lowest['date'].dt.strftime('%Y-%m-%d'),
                                        year_lowest['pixel_count']
                                    ))
                                ))
                        
                        fig_low.update_layout(
                            title=f"Lowest {n_extreme} Albedo Values by Year",
                            xaxis_title="Date",
                            yaxis_title="Mean Albedo",
                            height=400,
                            yaxis=dict(
                                dtick=0.05,
                                tickformat=".2f"
                            )
                        )
                        
                        st.plotly_chart(fig_low, use_container_width=True)
                        
                        # Show table of lowest values
                        st.markdown(f"##### 📊 Lowest {n_extreme} Values Table")
                        display_lowest = all_lowest[['year', 'date', 'albedo_mean', 'pixel_count', 'rank']].copy()
                        display_lowest['date'] = display_lowest['date'].dt.strftime('%Y-%m-%d')
                        display_lowest.columns = ['Year', 'Date', 'Albedo', 'Pixels', 'Rank']
                        st.dataframe(display_lowest, use_container_width=True)
                
                with col_high:
                    st.markdown(f"#### ☀️ {n_extreme} Highest Albedo Days per Year")
                    
                    # Get highest values for each year
                    highest_by_year = []
                    for year in selected_years_extreme:
                        year_data = df_data_copy[df_data_copy['year'] == year]
                        if not year_data.empty:
                            highest = year_data.nlargest(n_extreme, 'albedo_mean')[
                                ['date', 'albedo_mean', 'pixel_count', 'year']
                            ].copy()
                            highest['rank'] = range(1, len(highest) + 1)
                            highest_by_year.append(highest)
                    
                    if highest_by_year:
                        all_highest = pd.concat(highest_by_year, ignore_index=True)
                        
                        # Create visualization for highest values
                        fig_high = go.Figure()
                        
                        for year in selected_years_extreme:
                            year_highest = all_highest[all_highest['year'] == year]
                            if not year_highest.empty:
                                fig_high.add_trace(go.Scatter(
                                    x=year_highest['date'],
                                    y=year_highest['albedo_mean'],
                                    mode='markers',
                                    name=f'{year} Highest',
                                    marker=dict(
                                        size=10,
                                        opacity=0.8,
                                        line=dict(width=2, color='white'),
                                        symbol='triangle-up'
                                    ),
                                    hovertemplate=f'<b>{year} - Rank %{{customdata[0]}}</b><br>' +
                                                 'Date: %{customdata[1]}<br>' +
                                                 'Albedo: %{y:.3f}<br>' +
                                                 'Pixels: %{customdata[2]}<br>' +
                                                 '<extra></extra>',
                                    customdata=list(zip(
                                        year_highest['rank'],
                                        year_highest['date'].dt.strftime('%Y-%m-%d'),
                                        year_highest['pixel_count']
                                    ))
                                ))
                        
                        fig_high.update_layout(
                            title=f"Highest {n_extreme} Albedo Values by Year",
                            xaxis_title="Date",
                            yaxis_title="Mean Albedo",
                            height=400,
                            yaxis=dict(
                                dtick=0.05,
                                tickformat=".2f"
                            )
                        )
                        
                        st.plotly_chart(fig_high, use_container_width=True)
                        
                        # Show table of highest values
                        st.markdown(f"##### 📊 Highest {n_extreme} Values Table")
                        display_highest = all_highest[['year', 'date', 'albedo_mean', 'pixel_count', 'rank']].copy()
                        display_highest['date'] = display_highest['date'].dt.strftime('%Y-%m-%d')
                        display_highest.columns = ['Year', 'Date', 'Albedo', 'Pixels', 'Rank']
                        st.dataframe(display_highest, use_container_width=True)
                
                # Combined extreme values comparison
                st.markdown("### 📈 Extreme Values Comparison")
                
                if lowest_by_year and highest_by_year:
                    # Create combined plot
                    fig_combined = go.Figure()
                    
                    # Add lowest values
                    for year in selected_years_extreme:
                        year_lowest = all_lowest[all_lowest['year'] == year]
                        year_highest = all_highest[all_highest['year'] == year]
                        
                        if not year_lowest.empty:
                            fig_combined.add_trace(go.Scatter(
                                x=year_lowest['date'],
                                y=year_lowest['albedo_mean'],
                                mode='markers',
                                name=f'{year} Lowest',
                                marker=dict(
                                    size=8,
                                    opacity=0.7,
                                    symbol='triangle-down',
                                    line=dict(width=1, color='white')
                                ),
                                legendgroup=f'{year}',
                                hovertemplate=f'<b>{year} Lowest</b><br>Date: %{{x}}<br>Albedo: %{{y:.3f}}<extra></extra>'
                            ))
                        
                        if not year_highest.empty:
                            fig_combined.add_trace(go.Scatter(
                                x=year_highest['date'],
                                y=year_highest['albedo_mean'],
                                mode='markers',
                                name=f'{year} Highest',
                                marker=dict(
                                    size=8,
                                    opacity=0.7,
                                    symbol='triangle-up',
                                    line=dict(width=1, color='white')
                                ),
                                legendgroup=f'{year}',
                                hovertemplate=f'<b>{year} Highest</b><br>Date: %{{x}}<br>Albedo: %{{y:.3f}}<extra></extra>'
                            ))
                    
                    fig_combined.update_layout(
                        title=f"Extreme Values Comparison - Top/Bottom {n_extreme} per Year",
                        xaxis_title="Date",
                        yaxis_title="Mean Albedo",
                        height=500,
                        yaxis=dict(
                            dtick=0.05,
                            tickformat=".2f"
                        )
                    )
                    
                    st.plotly_chart(fig_combined, use_container_width=True)
                    
                    # Summary statistics
                    st.markdown("### 📊 Extreme Values Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        overall_min = all_lowest['albedo_mean'].min()
                        st.metric("Overall Minimum", f"{overall_min:.3f}")
                    
                    with col2:
                        overall_max = all_highest['albedo_mean'].max()
                        st.metric("Overall Maximum", f"{overall_max:.3f}")
                    
                    with col3:
                        range_val = overall_max - overall_min
                        st.metric("Albedo Range", f"{range_val:.3f}")
                    
                    with col4:
                        avg_extreme_diff = (all_highest.groupby('year')['albedo_mean'].mean() - 
                                          all_lowest.groupby('year')['albedo_mean'].mean()).mean()
                        st.metric("Avg Annual Range", f"{avg_extreme_diff:.3f}")
        
        else:
            st.error("No data available for extreme values analysis")

    with tab5:
        st.markdown("### Statistical Summary")
        
        # Combine statistics from all datasets
        if not df_data.empty:
            st.markdown("#### Time Series Statistics")
            
            stats_dict = {
                'Metric': ['Total Observations', 'Years of Data', 'Mean Albedo', 'Std Albedo', 'Min Albedo', 'Max Albedo', 'Mean Pixel Count'],
                'Value': [
                    len(df_data),
                    df_data['year'].nunique(),
                    f"{df_data['albedo_mean'].mean():.4f}",
                    f"{df_data['albedo_mean'].std():.4f}",
                    f"{df_data['albedo_mean'].min():.4f}",
                    f"{df_data['albedo_mean'].max():.4f}",
                    f"{df_data['pixel_count'].mean():.0f}"
                ]
            }
            
            stats_df = pd.DataFrame(stats_dict)
            st.table(stats_df)
        
        if not df_results.empty:
            st.markdown("#### Trend Analysis Summary")
            
            # Summary of significant trends
            significant_trends = df_results[df_results['significance'] == 'significant']
            
            if not significant_trends.empty:
                st.success(f"📈 {len(significant_trends)} out of {len(df_results)} analyses show significant trends")
                
                for _, row in significant_trends.iterrows():
                    trend_icon = "📉" if row['trend'] == 'decreasing' else "📈"
                    st.write(f"{trend_icon} **{row['analysis_type']}**: {row['percent_change_per_year']:.2f}% per year (p={row['p_value']:.4f})")
            else:
                st.info("No significant trends detected in the analysis periods.")

def create_melt_season_dashboard(df):
    """
    Create melt season analysis dashboard
    """
    if df.empty:
        st.error("No melt season data available")
        return
    
    st.subheader("🌊 Melt Season Analysis")
    
    # Prepare data
    df['date'] = pd.to_datetime(df['date'])
    
    # Sidebar controls
    st.sidebar.header("🌊 Melt Season Controls")
    
    # Year selection
    years = sorted(df['year'].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years", 
        years, 
        default=years[-3:] if len(years) >= 3 else years
    )
    
    # Filter data
    filtered_df = df[df['year'].isin(selected_years)]
    
    # Basic time series plot
    fig = go.Figure()
    
    for year in selected_years:
        year_data = filtered_df[filtered_df['year'] == year]
        
        fig.add_trace(go.Scatter(
            x=year_data['date'],
            y=year_data['albedo_mean'],
            mode='markers',
            name=f'{year} Mean Albedo',
            marker=dict(size=4, opacity=0.7),
            hovertemplate=f'<b>{year}</b><br>Date: %{{x}}<br>Albedo: %{{y:.3f}}<br>Pixels: %{{customdata}}<extra></extra>',
            customdata=year_data['pixel_count']
        ))
    
    fig.update_layout(
        title="Daily Snow Albedo - Melt Season",
        xaxis_title="Date",
        yaxis_title="Mean Snow Albedo",
        height=600,
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Data statistics
    st.subheader("📊 Data Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Observations", len(filtered_df))
    with col2:
        st.metric("Years of Data", len(selected_years))
    with col3:
        st.metric("Mean Albedo", f"{filtered_df['albedo_mean'].mean():.3f}")
    with col4:
        st.metric("Mean Pixel Count", f"{filtered_df['pixel_count'].mean():.0f}")

def create_albedo_map(df_data, selected_date=None):
    """
    Create interactive Folium map showing MODIS albedo pixels within glacier mask
    Shows actual MODIS 500m pixel grid with real albedo values from Earth Engine
    
    Args:
        df_data: DataFrame with albedo observations (used for date filtering)
        selected_date: Specific date to show MODIS pixels for (YYYY-MM-DD format)
    
    Returns:
        folium.Map: Interactive map with real MODIS pixel visualization
    """
    # Glacier coordinates (Athabasca)
    center_lat = 52.2
    center_lon = -117.25
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add satellite imagery
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add terrain layer  
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', 
        name='Terrain',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Load glacier boundary
    glacier_geojson = None
    try:
        glacier_geojson_path = '../Athabasca_mask_2023_cut.geojson'
        
        with open(glacier_geojson_path, 'r') as f:
            glacier_geojson = json.load(f)
        
        # Add glacier boundary
        folium.GeoJson(
            glacier_geojson,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'red',
                'weight': 3,
                'fillOpacity': 0.1
            },
            popup=folium.Popup("Athabasca Glacier Boundary", parse_html=True),
            tooltip="Athabasca Glacier Boundary"
        ).add_to(m)
        
    except Exception as e:
        st.warning(f"Could not load glacier boundary: {e}")
    
    # Add MODIS pixel visualization if we have a specific date
    if selected_date:
        # Check if Earth Engine is available and initialized
        if not initialize_earth_engine():
            st.info("🗺️ Showing basic map without MODIS pixels due to Earth Engine authentication issue")
            return m
            
        try:
            import ee
            
            # Define Athabasca ROI from the geojson if available
            if glacier_geojson:
                # Convert geojson to Earth Engine geometry
                coords = glacier_geojson['features'][0]['geometry']['coordinates'][0]
                athabasca_roi = ee.Geometry.Polygon(coords)
            else:
                # Fallback to approximate coordinates
                athabasca_roi = ee.Geometry.Polygon([
                    [[-117.3, 52.15], [-117.15, 52.15], [-117.15, 52.25], [-117.3, 52.25]]
                ])
            
            # Get MODIS data for the selected date
            modis_pixels = get_modis_pixels_for_date(selected_date, athabasca_roi)
            
            if modis_pixels and 'features' in modis_pixels:
                pixel_count = len(modis_pixels['features'])
                st.info(f"Found {pixel_count} MODIS pixels with data for {selected_date}")
                
                # Add each MODIS pixel as a colored polygon
                for feature in modis_pixels['features']:
                    if 'properties' in feature and 'albedo_value' in feature['properties']:
                        albedo_value = feature['properties']['albedo_value']
                        
                        # Skip invalid values
                        if albedo_value is None or albedo_value < 0 or albedo_value > 1:
                            continue
                            
                        # Get color based on albedo value
                        color = get_albedo_color_palette(albedo_value)
                        
                        # Create popup with pixel info
                        popup_text = f"""
                        <b>MODIS Pixel</b><br>
                        Date: {selected_date}<br>
                        Albedo: {albedo_value:.3f}<br>
                        Pixel Area: ~500m x 500m<br>
                        Product: MOD10A1/MYD10A1
                        """
                        
                        # Add pixel polygon to map
                        folium.GeoJson(
                            feature,
                            style_function=lambda x, color=color: {
                                'fillColor': color,
                                'color': 'white',
                                'weight': 1,
                                'fillOpacity': 0.8,
                                'opacity': 1.0
                            },
                            popup=folium.Popup(popup_text, parse_html=True),
                            tooltip=f"Albedo: {albedo_value:.3f}"
                        ).add_to(m)
                
                # Create detailed color legend
                create_albedo_legend(m, selected_date)
                
            else:
                st.warning(f"No valid MODIS pixels found for {selected_date}")
                
        except Exception as e:
            st.error(f"Error loading MODIS pixels: {e}")
            st.info("Falling back to basic map view")
    
    else:
        st.info("Select a specific date to view MODIS pixel data")
        
        # Show fallback visualization with available data
        if not df_data.empty:
            # Create representative points from actual data
            create_fallback_albedo_visualization(m, df_data)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m


def get_modis_pixels_for_date(date, roi):
    """
    Get MODIS pixel boundaries with albedo values for a specific date
    Uses the same quality filtering as the main analysis (QA ≤ 1)
    
    Args:
        date: Date string (YYYY-MM-DD)
        roi: Earth Engine geometry for glacier boundary
        
    Returns:
        dict: GeoJSON with MODIS pixel features and albedo values
    """
    try:
        import ee
        
        # MODIS collections (same as used in main analysis)
        mod10a1 = ee.ImageCollection('MODIS/061/MOD10A1')
        myd10a1 = ee.ImageCollection('MODIS/061/MYD10A1')
        
        # Filter by date (±1 day for better coverage)
        start_date = ee.Date(date).advance(-1, 'day')
        end_date = ee.Date(date).advance(1, 'day')
        
        # Get images for the date with boundary filter
        terra_imgs = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
        aqua_imgs = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
        
        # Check if we have data
        terra_count = terra_imgs.size().getInfo()
        aqua_count = aqua_imgs.size().getInfo()
        
        st.info(f"Found {terra_count} Terra and {aqua_count} Aqua images for {date}")
        
        if terra_count == 0 and aqua_count == 0:
            return None
            
        # Apply the same masking function as used in main analysis
        def mask_modis_snow_albedo(image):
            """Apply the same quality filtering as main analysis"""
            albedo = image.select('Snow_Albedo_Daily_Tile')
            qa = image.select('NDSI_Snow_Cover_Basic_QA')
            
            # Same filtering as in your extraction.py: QA ≤ 1 and valid albedo range
            valid_albedo = albedo.gte(5).And(albedo.lte(99))  # 5-99 range before scaling
            good_quality = qa.lte(1)  # QA ≤ 1: Best and good quality (not just 0)
            
            # Apply masks and scale
            masked = albedo.updateMask(valid_albedo.And(good_quality)).multiply(0.01)
            
            return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
        
        # Process Terra and Aqua separately
        processed_images = []
        
        if terra_count > 0:
            terra_processed = terra_imgs.map(mask_modis_snow_albedo)
            processed_images.append(terra_processed)
            
        if aqua_count > 0:
            aqua_processed = aqua_imgs.map(mask_modis_snow_albedo)
            processed_images.append(aqua_processed)
        
        # Combine all processed images
        if len(processed_images) == 1:
            combined_collection = processed_images[0]
        else:
            combined_collection = processed_images[0].merge(processed_images[1])
            
        # Create mosaic (Terra has priority if both available on same time)
        combined_image = combined_collection.mosaic()
        
        # Clip to glacier boundary
        albedo_clipped = combined_image.select('albedo_daily').clip(roi)
        
        # Check if we have any valid pixels
        pixel_count = albedo_clipped.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=500,
            maxPixels=1e6
        ).get('albedo_daily').getInfo()
        
        if pixel_count == 0:
            st.warning(f"No valid pixels found after quality filtering for {date}")
            return None
            
        st.info(f"Found {pixel_count} valid pixels after quality filtering")
        
        # Convert to integer for reduceToVectors (multiply by 1000 to preserve precision)
        albedo_int = albedo_clipped.multiply(1000).int()
        
        # Convert pixels to vectors (this creates polygon boundaries for each pixel)
        pixel_vectors = albedo_int.reduceToVectors(
            geometry=roi,
            crs=albedo_int.projection(),
            scale=500,  # MODIS 500m resolution
            geometryType='polygon',
            eightConnected=False,
            maxPixels=1e6,
            bestEffort=True,
            labelProperty='albedo_int'
        )
        
        # Add detailed properties to each pixel
        def add_pixel_properties(feature):
            # Get the integer albedo value from the feature properties
            albedo_int_value = feature.get('albedo_int')
            
            # Convert back to original albedo scale (divide by 1000)
            pixel_albedo = ee.Number(albedo_int_value).divide(1000)
            
            # Also get the exact value from the original image for verification
            pixel_albedo_exact = albedo_clipped.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=feature.geometry(),
                scale=500,
                maxPixels=1
            ).get('albedo_daily')
            
            # Get pixel area
            pixel_area = feature.geometry().area()
            
            return feature.set({
                'albedo_value': pixel_albedo,
                'albedo_exact': pixel_albedo_exact,
                'date': date,
                'pixel_area_m2': pixel_area,
                'product': 'MOD10A1/MYD10A1',
                'quality_filter': 'QA ≤ 1, range 0.05-0.99'
            })
        
        # Apply properties to all pixels
        pixels_with_data = pixel_vectors.map(add_pixel_properties)
        
        # Limit pixels for performance (but allow more than before)
        pixels_limited = pixels_with_data.limit(200)  # Increased from 100
        
        # Export as GeoJSON
        geojson = pixels_limited.getInfo()
        
        return geojson
        
    except Exception as e:
        print(f"Error getting MODIS pixels: {e}")
        st.error(f"Detailed error: {str(e)}")
        return None


def get_albedo_color_palette(albedo_value):
    """
    Convert albedo value to color using MODIS-style palette
    
    Args:
        albedo_value: Albedo value (0.0 - 1.0)
        
    Returns:
        str: Hex color code
    """
    # Normalize albedo value (0-1)
    normalized = max(0, min(1, albedo_value))
    
    # MODIS-style color palette (dark to bright)
    if normalized < 0.1:
        return '#440154'    # Dark purple (very low albedo)
    elif normalized < 0.3:
        return '#31688e'    # Blue (low albedo)
    elif normalized < 0.5:
        return '#35b779'    # Green (medium-low albedo)
    elif normalized < 0.7:
        return '#fde725'    # Yellow (medium-high albedo)
    elif normalized < 0.85:
        return '#ffffff'    # White (high albedo)
    else:
        return '#f0f0f0'    # Light gray (very high albedo)


def create_albedo_legend(map_obj, date):
    """
    Create detailed albedo legend for the map
    
    Args:
        map_obj: Folium map object
        date: Date string for the legend
    """
    legend_html = f'''
    <div style="position: fixed; 
               bottom: 50px; left: 50px; width: 200px; height: 180px; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-size:12px; padding: 10px">
    <h4>MODIS Albedo - {date}</h4>
    <hr>
    <p><span style="color:#440154; font-size:16px;">●</span> Very Low (0.0-0.1)</p>
    <p><span style="color:#31688e; font-size:16px;">●</span> Low (0.1-0.3)</p>
    <p><span style="color:#35b779; font-size:16px;">●</span> Medium (0.3-0.5)</p>
    <p><span style="color:#fde725; font-size:16px;">●</span> High (0.5-0.7)</p>
    <p><span style="color:#ffffff; font-size:16px; text-shadow: 1px 1px 1px #000000;">●</span> Very High (0.7+)</p>
    <hr>
    <small>Each polygon = 500m MODIS pixel</small>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))


def create_fallback_albedo_visualization(map_obj, df_data):
    """
    Create fallback albedo visualization when Earth Engine is not available
    Uses representative points based on actual albedo data
    
    Args:
        map_obj: Folium map object
        df_data: DataFrame with albedo data
    """
    if df_data.empty:
        return
        
    # Use a sample of recent data
    sample_size = min(30, len(df_data))
    sample_data = df_data.sample(n=sample_size) if len(df_data) > sample_size else df_data
    
    # Glacier center
    center_lat = 52.2
    center_lon = -117.25
    
    # Calculate albedo range for color mapping
    min_albedo = sample_data['albedo_mean'].min()
    max_albedo = sample_data['albedo_mean'].max()
    
    # Create representative points within glacier area
    import random
    random.seed(42)  # Reproducible pattern
    
    for idx, row in sample_data.iterrows():
        # Create coordinates within glacier area
        lat_offset = random.uniform(-0.015, 0.015)
        lon_offset = random.uniform(-0.015, 0.015) 
        point_lat = center_lat + lat_offset
        point_lon = center_lon + lon_offset
        
        # Get color based on albedo value
        color = get_albedo_color_palette(row['albedo_mean'])
        
        # Create popup
        popup_text = f"""
        <b>Albedo Observation</b><br>
        Date: {row['date']}<br>
        Albedo: {row['albedo_mean']:.3f}<br>
        Elevation: {row.get('elevation', 'N/A')}<br>
        <i>Representative visualization</i>
        """
        
        # Add point to map
        folium.CircleMarker(
            location=[point_lat, point_lon],
            radius=6,
            popup=folium.Popup(popup_text, parse_html=True),
            color='white',
            weight=1,
            fillColor=color,
            fillOpacity=0.7,
            tooltip=f"Albedo: {row['albedo_mean']:.3f}"
        ).add_to(map_obj)
    
    # Add simple legend
    legend_html = f'''
    <div style="position: fixed; 
               bottom: 50px; left: 50px; width: 180px; height: 140px; 
               background-color: white; border:2px solid grey; z-index:9999; 
               font-size:12px; padding: 10px">
    <h4>Albedo Data</h4>
    <hr>
    <p><span style="color:#440154;">●</span> Low ({min_albedo:.2f})</p>
    <p><span style="color:#31688e;">●</span> Medium-Low</p>
    <p><span style="color:#35b779;">●</span> Medium</p>
    <p><span style="color:#fde725;">●</span> High</p>
    <p><span style="color:#ffffff; text-shadow: 1px 1px 1px #000000;">●</span> Very High ({max_albedo:.2f})</p>
    <hr>
    <small>Representative data points</small>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))

def create_hypsometric_dashboard(df_results, df_data):
    """
    Create comprehensive hypsometric analysis dashboard
    Following Williamson & Menounos 2021 methodology
    """
    st.subheader("🏔️ Hypsometric Analysis - Elevation Band Albedo Trends")
    st.markdown("*Elevation-based albedo analysis following Williamson & Menounos (2021)*")
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Elevation Bands", "🗺️ Interactive Map", "🎨 Albedo Visualization", "📅 Temporal Evolution", "📈 Elevation Profiles", "📋 Summary"])
    
    with tab1:
        st.markdown("### 📊 Elevation Band Trend Analysis")
        
        if not df_results.empty:
            # Create trend visualization
            fig_trends = go.Figure()
            
            # Color scheme for elevation bands
            colors = {
                'above_median': '#d62728',    # Red for above median
                'near_median': '#ff7f0e',     # Orange for near median  
                'below_median': '#1f77b4'     # Blue for below median
            }
            
            symbols = {
                'above_median': 'triangle-up',
                'near_median': 'circle',
                'below_median': 'triangle-down'
            }
            
            # Add data points
            for _, row in df_results.iterrows():
                elevation_code = row['elevation_code']
                
                fig_trends.add_trace(go.Scatter(
                    x=[row['elevation_band']],
                    y=[row['sens_slope_per_year'] * 100],  # Convert to percentage
                    mode='markers',
                    name=row['elevation_band'],
                    marker=dict(
                        size=15,
                        color=colors.get(elevation_code, '#2ca02c'),
                        symbol=symbols.get(elevation_code, 'circle'),
                        opacity=0.8,
                        line=dict(width=2, color='white')
                    ),
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Trend: %{y:.3f}% per year<br>' +
                                 'P-value: %{customdata[0]:.4f}<br>' +
                                 'Significance: %{customdata[1]}<br>' +
                                 'Observations: %{customdata[2]}<br>' +
                                 '<extra></extra>',
                    customdata=[[row['mann_kendall_p_value'], row['significance'], row['n_observations']]]
                ))
            
            fig_trends.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
            
            fig_trends.update_layout(
                title="Albedo Trends by Elevation Band",
                xaxis_title="Elevation Band",
                yaxis_title="Albedo Change (% per year)",
                height=500,
                showlegend=False,
                yaxis=dict(
                    tickformat=".2f"
                )
            )
            
            st.plotly_chart(fig_trends, use_container_width=True)
            
            # Results table
            st.markdown("### 📋 Statistical Results")
            display_results = df_results.copy()
            display_results['sens_slope_per_year'] = display_results['sens_slope_per_year'].round(6)
            display_results['mann_kendall_p_value'] = display_results['mann_kendall_p_value'].round(4)
            display_results.columns = ['Elevation Band', 'Code', 'Observations', 'Slope (per year)', 'P-value', 'Trend', 'Significance']
            st.dataframe(display_results, use_container_width=True)
            
            # Key insights
            st.markdown("### 🔍 Key Insights")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_obs = df_results['n_observations'].sum()
                st.metric("Total Observations", f"{total_obs:,}")
            
            with col2:
                significant_trends = len(df_results[df_results['significance'] == 'significant'])
                st.metric("Significant Trends", f"{significant_trends}/3")
            
            with col3:
                strongest_trend = df_results.loc[df_results['sens_slope_per_year'].abs().idxmax()]
                st.metric("Strongest Trend", f"{strongest_trend['elevation_band']}")
            
            # Significance analysis
            if significant_trends > 0:
                st.success(f"📈 {significant_trends} elevation band(s) show significant albedo trends")
                sig_data = df_results[df_results['significance'] == 'significant']
                for _, row in sig_data.iterrows():
                    trend_icon = "📉" if row['sens_slope_per_year'] < 0 else "📈"
                    st.write(f"{trend_icon} **{row['elevation_band']}**: {row['sens_slope_per_year']*100:.3f}% per year (p={row['mann_kendall_p_value']:.4f})")
            else:
                st.info("ℹ️ No statistically significant trends detected across elevation bands")
    
    with tab2:
        st.markdown("### 🗺️ Interactive Elevation Map")
        
        # Create Folium map
        if not df_data.empty:
            # Calculate center of glacier (approximate Athabasca coordinates)
            center_lat = 52.2
            center_lon = -117.25
            
            # Create base map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=13,
                tiles='OpenStreetMap'
            )
            
            # Add satellite imagery
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satellite',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Add terrain layer
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Terrain',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Add elevation analysis
            if not df_data.empty:
                # Get elevation statistics
                median_elevation = df_data['glacier_median_elevation'].iloc[0]
                min_elevation = df_data['glacier_min_elevation'].iloc[0]
                max_elevation = df_data['glacier_max_elevation'].iloc[0]
                
                # Create elevation bands legend
                legend_html = f"""
                <div style="position: fixed; 
                           top: 10px; right: 10px; width: 200px; height: 120px; 
                           background-color: white; border:2px solid grey; z-index:9999; 
                           font-size:14px; padding: 10px">
                <h4>Elevation Bands</h4>
                <p><span style="color:#d62728;">▲</span> Above Median (>{median_elevation:.0f}m)</p>
                <p><span style="color:#ff7f0e;">●</span> Near Median (±100m)</p>
                <p><span style="color:#1f77b4;">▼</span> Below Median (<{median_elevation:.0f}m)</p>
                <p><strong>Range:</strong> {min_elevation:.0f}m - {max_elevation:.0f}m</p>
                </div>
                """
                m.get_root().html.add_child(folium.Element(legend_html))
            
            # Try to load glacier boundary if available
            try:
                # Load glacier boundary from geojson
                glacier_geojson_path = '../Athabasca_mask_2023_cut.geojson'
                
                # Add glacier boundary
                folium.GeoJson(
                    glacier_geojson_path,
                    style_function=lambda x: {
                        'fillColor': 'lightblue',
                        'color': 'blue',
                        'weight': 2,
                        'fillOpacity': 0.3
                    },
                    popup=folium.Popup("Athabasca Glacier Boundary", parse_html=True),
                    tooltip="Athabasca Glacier"
                ).add_to(m)
                
            except Exception as e:
                st.warning(f"Could not load glacier boundary: {e}")
            
            # Add layer control
            folium.LayerControl().add_to(m)
            
            # Display map
            st.markdown("**Interactive Features:**")
            st.markdown("- 🗺️ **Switch layers**: Satellite, Terrain, OpenStreetMap")
            st.markdown("- 🔍 **Zoom/Pan**: Explore different areas of the glacier")
            st.markdown("- 📍 **Elevation context**: See spatial distribution of elevation bands")
            
            map_data = st_folium(m, width=700, height=500)
            
            # Show elevation statistics
            if not df_data.empty:
                st.markdown("### 📊 Elevation Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Median Elevation", f"{median_elevation:.0f}m")
                with col2:
                    st.metric("Min Elevation", f"{min_elevation:.0f}m")  
                with col3:
                    st.metric("Max Elevation", f"{max_elevation:.0f}m")
                with col4:
                    elevation_range = max_elevation - min_elevation
                    st.metric("Elevation Range", f"{elevation_range:.0f}m")
        
        else:
            st.error("No elevation data available for mapping")
    
    with tab3:
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
            map_data = st_folium(albedo_map, width=700, height=500)
            
            # Show data statistics for selected visualization
            st.markdown("### 📊 Visualization Statistics")
            
            if visualization_mode == "Specific Date" and selected_date:
                display_data = df_data_copy[df_data_copy['date_str'] == selected_date]
            else:
                display_data = df_data_copy
            
            if not display_data.empty:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Observations", len(display_data))
                with col2:
                    st.metric("Mean Albedo", f"{display_data['albedo_mean'].mean():.3f}")
                with col3:
                    st.metric("Albedo Range", f"{display_data['albedo_mean'].min():.3f} - {display_data['albedo_mean'].max():.3f}")
                with col4:
                    unique_dates = display_data['date_str'].nunique()
                    st.metric("Unique Dates", unique_dates)
                
                # Show sample data
                st.markdown("### 📋 Sample Data")
                sample_size = min(10, len(display_data))
                sample_display = display_data[['date_str', 'albedo_mean', 'elevation', 'pixel_count']].head(sample_size)
                sample_display.columns = ['Date', 'Albedo', 'Elevation (m)', 'Pixel Count']
                st.dataframe(sample_display, use_container_width=True)
                
                # Color scale explanation
                st.markdown("### 🎨 Color Scale")
                st.markdown("""
                **Albedo Color Mapping:**
                - 🟣 **Dark Purple**: Very low albedo (dark surfaces)
                - 🔵 **Blue**: Low albedo 
                - 🟢 **Green**: Medium albedo
                - 🟡 **Yellow**: High albedo
                - ⚪ **Light Yellow/White**: Very high albedo (bright snow/ice)
                
                *Each point represents an averaged observation within the glacier boundary*
                """)
        
        else:
            st.error("No albedo data available for visualization")

    with tab4:
        st.markdown("### 📅 Temporal Evolution by Elevation")
        
        if not df_data.empty:
            # Prepare data
            df_data_copy = df_data.copy()
            df_data_copy['date'] = pd.to_datetime(df_data_copy['date'])
            
            # Sidebar controls
            st.sidebar.header("📅 Temporal Controls")
            
            # Year selection
            years = sorted(df_data_copy['year'].unique())
            selected_years = st.sidebar.multiselect(
                "Select Years", 
                years, 
                default=years[-3:] if len(years) >= 3 else years,
                key="hypsometric_years"
            )
            
            # Create elevation bands
            median_elev = df_data_copy['glacier_median_elevation'].iloc[0]
            df_data_copy['elevation_band'] = df_data_copy['elevation'].apply(
                lambda x: 'Above Median' if x > median_elev + 100 
                         else 'Below Median' if x < median_elev - 100 
                         else 'Near Median'
            )
            
            # Filter data
            filtered_df = df_data_copy[df_data_copy['year'].isin(selected_years)]
            
            if not filtered_df.empty:
                # Time series by elevation band
                fig_temporal = go.Figure()
                
                band_colors = {
                    'Above Median': '#d62728',
                    'Near Median': '#ff7f0e', 
                    'Below Median': '#1f77b4'
                }
                
                for band in ['Above Median', 'Near Median', 'Below Median']:
                    band_data = filtered_df[filtered_df['elevation_band'] == band]
                    
                    if not band_data.empty:
                        fig_temporal.add_trace(go.Scatter(
                            x=band_data['date'],
                            y=band_data['albedo_mean'],
                            mode='markers',
                            name=band,
                            marker=dict(
                                color=band_colors[band],
                                size=6,
                                opacity=0.7,
                                line=dict(width=1, color='white')
                            ),
                            hovertemplate=f'<b>{band}</b><br>' +
                                         'Date: %{x}<br>' +
                                         'Albedo: %{y:.3f}<br>' +
                                         'Elevation: %{customdata:.0f}m<br>' +
                                         '<extra></extra>',
                            customdata=band_data['elevation']
                        ))
                
                fig_temporal.update_layout(
                    title="Albedo Evolution by Elevation Band",
                    xaxis_title="Date",
                    yaxis_title="Mean Albedo",
                    height=600,
                    hovermode='closest',
                    yaxis=dict(
                        dtick=0.05,
                        tickformat=".2f"
                    )
                )
                
                st.plotly_chart(fig_temporal, use_container_width=True)
                
                # Monthly patterns
                if len(selected_years) > 1:
                    st.markdown("### 📊 Monthly Patterns by Elevation")
                    
                    monthly_stats = filtered_df.groupby(['month', 'elevation_band'])['albedo_mean'].agg(['mean', 'std', 'count']).reset_index()
                    
                    fig_monthly = go.Figure()
                    
                    for band in ['Above Median', 'Near Median', 'Below Median']:
                        band_monthly = monthly_stats[monthly_stats['elevation_band'] == band]
                        
                        if not band_monthly.empty:
                            fig_monthly.add_trace(go.Scatter(
                                x=band_monthly['month'],
                                y=band_monthly['mean'],
                                mode='markers+lines',
                                name=band,
                                line=dict(color=band_colors[band], width=2),
                                marker=dict(size=8),
                                error_y=dict(
                                    type='data',
                                    array=band_monthly['std'],
                                    visible=True
                                ),
                                hovertemplate=f'<b>{band}</b><br>' +
                                             'Month: %{x}<br>' +
                                             'Mean Albedo: %{y:.3f}<br>' +
                                             'Std Dev: %{error_y.array:.3f}<br>' +
                                             '<extra></extra>'
                            ))
                    
                    fig_monthly.update_layout(
                        title="Monthly Albedo Patterns by Elevation Band",
                        xaxis_title="Month",
                        yaxis_title="Mean Albedo",
                        height=400,
                        xaxis=dict(
                            tickvals=[6, 7, 8, 9],
                            ticktext=['June', 'July', 'August', 'September']
                        ),
                        yaxis=dict(
                            dtick=0.05,
                            tickformat=".2f"
                        )
                    )
                    
                    st.plotly_chart(fig_monthly, use_container_width=True)
        
        else:
            st.error("No temporal data available for elevation analysis")
    
    with tab4:
        st.markdown("### 📈 Elevation Profile Analysis")
        
        if not df_data.empty:
            # Elevation vs Albedo relationship
            fig_profile = go.Figure()
            
            # Scatter plot of elevation vs albedo
            fig_profile.add_trace(go.Scatter(
                x=df_data['elevation'],
                y=df_data['albedo_mean'],
                mode='markers',
                name='Observations',
                marker=dict(
                    size=4,
                    opacity=0.6,
                    color=df_data['albedo_mean'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Albedo")
                ),
                hovertemplate='<b>Elevation vs Albedo</b><br>' +
                             'Elevation: %{x:.0f}m<br>' +
                             'Albedo: %{y:.3f}<br>' +
                             'Date: %{customdata}<br>' +
                             '<extra></extra>',
                customdata=df_data['date']
            ))
            
            # Add median elevation line
            median_elev = df_data['glacier_median_elevation'].iloc[0]
            fig_profile.add_vline(
                x=median_elev, 
                line_dash="dash", 
                line_color="red", 
                annotation_text=f"Median Elevation ({median_elev:.0f}m)"
            )
            
            fig_profile.update_layout(
                title="Albedo vs Elevation Relationship",
                xaxis_title="Elevation (m)",
                yaxis_title="Albedo",
                height=500,
                yaxis=dict(
                    dtick=0.05,
                    tickformat=".2f"
                )
            )
            
            st.plotly_chart(fig_profile, use_container_width=True)
            
            # Elevation distribution
            st.markdown("### 📊 Elevation Distribution")
            
            fig_hist = go.Figure()
            
            fig_hist.add_trace(go.Histogram(
                x=df_data['elevation'],
                nbinsx=30,
                name='Elevation Distribution',
                marker_color='lightblue',
                opacity=0.7
            ))
            
            fig_hist.add_vline(
                x=median_elev,
                line_dash="dash",
                line_color="red",
                annotation_text="Median"
            )
            
            fig_hist.update_layout(
                title="Distribution of Observation Elevations",
                xaxis_title="Elevation (m)",
                yaxis_title="Number of Observations",
                height=400
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Statistical summary by elevation
            st.markdown("### 📊 Statistics by Elevation")
            
            # Create elevation bins for analysis
            df_copy = df_data.copy()
            df_copy['elev_bin'] = pd.cut(df_copy['elevation'], bins=5, precision=0)
            elev_stats = df_copy.groupby('elev_bin')['albedo_mean'].agg(['count', 'mean', 'std', 'min', 'max']).round(3)
            elev_stats.columns = ['Observations', 'Mean Albedo', 'Std Dev', 'Min Albedo', 'Max Albedo']
            
            st.dataframe(elev_stats, use_container_width=True)
        
        else:
            st.error("No elevation profile data available")
    
    with tab6:
        st.markdown("### 📋 Comprehensive Summary")
        
        # Summary statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏔️ Elevation Analysis")
            if not df_data.empty:
                st.write(f"**Total Observations:** {len(df_data):,}")
                st.write(f"**Elevation Range:** {df_data['glacier_min_elevation'].iloc[0]:.0f}m - {df_data['glacier_max_elevation'].iloc[0]:.0f}m")
                st.write(f"**Median Elevation:** {df_data['glacier_median_elevation'].iloc[0]:.0f}m")
                st.write(f"**Time Period:** {df_data['year'].min()} - {df_data['year'].max()}")
                
                # Albedo statistics by elevation band
                if 'elevation_band' in df_data.columns:
                    median_elev = df_data['glacier_median_elevation'].iloc[0]
                    df_data['elevation_band'] = df_data['elevation'].apply(
                        lambda x: 'Above Median' if x > median_elev + 100 
                                 else 'Below Median' if x < median_elev - 100 
                                 else 'Near Median'
                    )
                    
                    band_stats = df_data.groupby('elevation_band')['albedo_mean'].agg(['count', 'mean', 'std']).round(3)
                    st.dataframe(band_stats)
        
        with col2:
            st.markdown("#### 📈 Trend Analysis")
            if not df_results.empty:
                for _, row in df_results.iterrows():
                    trend_icon = "📉" if row['sens_slope_per_year'] < 0 else "📈" if row['sens_slope_per_year'] > 0 else "➡️"
                    significance_icon = "⭐" if row['significance'] == 'significant' else "○"
                    
                    st.write(f"{significance_icon} {trend_icon} **{row['elevation_band']}**")
                    st.write(f"   Trend: {row['sens_slope_per_year']*100:.3f}% per year")
                    st.write(f"   P-value: {row['mann_kendall_p_value']:.4f} ({row['significance']})")
                    st.write(f"   Observations: {row['n_observations']:,}")
                    st.write("")
        
        # Methodology note
        st.markdown("---")
        st.markdown("#### 📚 Methodology")
        st.markdown("""
        **Hypsometric Analysis Following Williamson & Menounos (2021):**
        - **Elevation Bands**: Above Median (>100m), Near Median (±100m), Below Median (>100m)
        - **Statistical Testing**: Mann-Kendall trend test with Sen's slope estimator
        - **Significance Level**: p < 0.05
        - **Data Source**: MOD10A1/MYD10A1 daily snow albedo with SRTM elevation data
        - **Quality Control**: Strict QA filtering (QA = 0 only)
        """)

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
        data_config = DATA_SOURCES['mcd43a3']
        df, source = load_data_from_url(data_config['url'], data_config['local_fallback'])
        
        if not df.empty:
            create_mcd43a3_dashboard(df)
    
    elif selected_dataset == "MOD10A1/MYD10A1 Melt Season":
        # Load all three datasets for comprehensive analysis
        df_data, _ = load_data_from_url(
            DATA_SOURCES['melt_season']['url'], 
            DATA_SOURCES['melt_season']['local_fallback']
        )
        df_results, _ = load_data_from_url(
            DATA_SOURCES['melt_season_results']['url'], 
            DATA_SOURCES['melt_season_results']['local_fallback']
        )
        df_focused, _ = load_data_from_url(
            DATA_SOURCES['melt_season_focused']['url'], 
            DATA_SOURCES['melt_season_focused']['local_fallback']
        )
        
        # Create comprehensive dashboard
        create_williamson_menounos_dashboard(df_data, df_results, df_focused)
            
    elif selected_dataset == "Hypsometric":
        # Load both results and data for comprehensive analysis
        df_results, _ = load_data_from_url(
            DATA_SOURCES['hypsometric']['url'], 
            DATA_SOURCES['hypsometric']['local_fallback']
        )
        df_data, _ = load_data_from_url(
            '../outputs/csv/athabasca_hypsometric_data.csv',
            '../outputs/csv/athabasca_hypsometric_data.csv'
        )
        
        # Create comprehensive hypsometric dashboard
        create_hypsometric_dashboard(df_results, df_data)
    
    # Footer information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    for key, config in DATA_SOURCES.items():
        st.sidebar.markdown(f"• {config['description']}")
    
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()