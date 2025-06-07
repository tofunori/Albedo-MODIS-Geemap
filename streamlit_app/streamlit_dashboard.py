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
        'url': 'https://raw.githubusercontent.com/YOUR-GITHUB-USERNAME/YOUR-REPO-NAME/main/outputs/csv/athabasca_mcd43a3_spectral_data.csv',
        'local_fallback': '../outputs/csv/athabasca_mcd43a3_spectral_data.csv',
        'description': 'MCD43A3 Spectral Time Series Data'
    },
    'melt_season': {
        'url': 'https://raw.githubusercontent.com/YOUR-ACTUAL-USERNAME/YOUR-ACTUAL-REPO/main/outputs/csv/athabasca_melt_season_data.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_data.csv',
        'description': 'Melt Season Time Series Data'
    },
    'melt_season_results': {
        'url': 'https://raw.githubusercontent.com/YOUR-ACTUAL-USERNAME/YOUR-ACTUAL-REPO/main/outputs/csv/athabasca_melt_season_results.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_results.csv',
        'description': 'Williamson & Menounos 2021 Trend Analysis'
    },
    'melt_season_focused': {
        'url': 'https://raw.githubusercontent.com/YOUR-ACTUAL-USERNAME/YOUR-ACTUAL-REPO/main/outputs/csv/athabasca_melt_season_focused_data.csv',
        'local_fallback': '../outputs/csv/athabasca_melt_season_focused_data.csv',
        'description': 'Focused Melt Season Data'
    },
    'hypsometric': {
        'url': 'https://raw.githubusercontent.com/YOUR-ACTUAL-USERNAME/YOUR-ACTUAL-REPO/main/outputs/csv/athabasca_hypsometric_results.csv',
        'local_fallback': '../outputs/csv/athabasca_hypsometric_results.csv',
        'description': 'Hypsometric Analysis Results'
    }
}

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
    Create comprehensive Williamson & Menounos 2021 melt season analysis dashboard
    """
    st.subheader("🌊 Melt Season Analysis (Williamson & Menounos 2021)")
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Trend Analysis", "📊 Time Series", "🔍 Focused Analysis", "📋 Statistical Summary"])
    
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
                # Time series plot
                fig_ts = go.Figure()
                
                for year in selected_years:
                    year_data = filtered_df[filtered_df['year'] == year]
                    
                    if not year_data.empty:
                        fig_ts.add_trace(go.Scatter(
                            x=year_data['date'],
                            y=year_data['albedo_mean'],
                            mode='markers+lines',
                            name=f'{year}',
                            line=dict(width=2),
                            marker=dict(size=6),
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
                    hovermode='closest'
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
                    height=400
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
                                 'Date: %{x}<br>' +
                                 'Mean: %{y:.3f}<br>' +
                                 'Range: %{customdata[0]:.3f} - %{customdata[1]:.3f}<br>' +
                                 'Pixels: %{customdata[2]}<br>' +
                                 '<extra></extra>',
                    customdata=list(zip(year_data['albedo_min'], year_data['albedo_max'], year_data['pixel_count']))
                ))
            
            fig_focused.update_layout(
                title="Focused Melt Season Analysis",
                xaxis_title="Date",
                yaxis_title="Mean Albedo",
                height=600
            )
            
            st.plotly_chart(fig_focused, use_container_width=True)
            
            # Show sample data
            st.markdown("### Sample Focused Data")
            st.dataframe(df_focused_copy.head(20), use_container_width=True)
    
    with tab4:
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
        ["MCD43A3 Spectral", "Williamson & Menounos 2021", "Melt Season (Simple)", "Hypsometric"]
    )
    
    # Load data based on selection
    if selected_dataset == "MCD43A3 Spectral":
        data_config = DATA_SOURCES['mcd43a3']
        df, source = load_data_from_url(data_config['url'], data_config['local_fallback'])
        
        if not df.empty:
            create_mcd43a3_dashboard(df)
    
    elif selected_dataset == "Williamson & Menounos 2021":
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
        
    elif selected_dataset == "Melt Season (Simple)":
        data_config = DATA_SOURCES['melt_season']
        df, source = load_data_from_url(data_config['url'], data_config['local_fallback'])
        
        if not df.empty:
            create_melt_season_dashboard(df)
            
    elif selected_dataset == "Hypsometric":
        data_config = DATA_SOURCES['hypsometric']
        df, source = load_data_from_url(data_config['url'], data_config['local_fallback'])
        
        if not df.empty:
            st.subheader("📈 Hypsometric Analysis")
            st.dataframe(df.head(10))
    
    # Footer information
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Sources:**")
    for key, config in DATA_SOURCES.items():
        st.sidebar.markdown(f"• {config['description']}")
    
    st.sidebar.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()