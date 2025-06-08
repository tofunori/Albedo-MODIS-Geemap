"""
MCD43A3 Spectral Analysis Dashboard
Creates interactive visualizations for MODIS MCD43A3 broadband albedo data
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def create_mcd43a3_dashboard(df, qa_config=None, qa_level=None):
    """
    Create MCD43A3 spectral analysis dashboard
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        qa_config: QA configuration dict (optional)
        qa_level: Selected QA level name (optional)
    """
    if df.empty:
        st.error("No MCD43A3 data available")
        return
    
    # Show QA info if provided
    if qa_config and qa_level:
        st.info(f"📊 **Quality Filtering:** {qa_level} - {qa_config['mcd43a3']['description']}")
    
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
        fig = create_seasonal_evolution_plot(filtered_df, selected_years, colors)
        
    elif view_type == "Visible vs NIR":
        fig = create_vis_nir_comparison_plot(filtered_df)
        
    elif view_type == "Spectral Bands":
        fig = create_spectral_bands_plot(filtered_df, years, colors)
        
    elif view_type == "Vis/NIR Ratio":
        fig = create_vis_nir_ratio_plot(filtered_df)
    
    # Display plot
    st.plotly_chart(fig, use_container_width=True)
    
    # Data statistics
    display_data_statistics(filtered_df, selected_years)


def create_seasonal_evolution_plot(filtered_df, selected_years, colors):
    """Create seasonal evolution plot for MCD43A3 data"""
    fig = go.Figure()
    
    for year in selected_years:
        year_data = filtered_df[filtered_df['year'] == year]
        
        if not year_data.empty and 'Albedo_BSA_vis' in year_data.columns:
            # Add date labels for hover
            year_data_vis = year_data.copy()
            year_data_vis['date_label'] = year_data_vis['date'].dt.strftime('%B %d, %Y')
            
            fig.add_trace(go.Scatter(
                x=year_data_vis['doy'],
                y=year_data_vis['Albedo_BSA_vis'],
                mode='markers',
                name=f'{year} Visible',
                marker=dict(color=colors['Albedo_BSA_vis'], size=6),
                hovertemplate=f'<b>{year} Visible</b><br>📅 Date: %{{customdata}}<br>📊 Albedo: %{{y:.3f}}<br>📈 DOY: %{{x}}<extra></extra>',
                customdata=year_data_vis['date_label']
            ))
            
        if not year_data.empty and 'Albedo_BSA_nir' in year_data.columns:
            # Add date labels for hover
            year_data_nir = year_data.copy()
            year_data_nir['date_label'] = year_data_nir['date'].dt.strftime('%B %d, %Y')
            
            fig.add_trace(go.Scatter(
                x=year_data_nir['doy'],
                y=year_data_nir['Albedo_BSA_nir'],
                mode='markers',
                name=f'{year} NIR',
                marker=dict(color=colors['Albedo_BSA_nir'], size=6, symbol='square'),
                hovertemplate=f'<b>{year} NIR</b><br>📅 Date: %{{customdata}}<br>📊 Albedo: %{{y:.3f}}<br>📈 DOY: %{{x}}<extra></extra>',
                customdata=year_data_nir['date_label']
            ))
    
    fig.update_layout(
        title="MCD43A3 Seasonal Evolution - Daily Albedo",
        xaxis_title="Day of Year",
        yaxis_title="Albedo",
        height=600,
        hovermode='closest'
    )
    
    return fig


def create_vis_nir_comparison_plot(filtered_df):
    """Create visible vs NIR comparison plot"""
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
        hovertemplate='<b>Year %{text}</b><br>📊 Visible Albedo: %{x:.3f}<br>📊 NIR Albedo: %{y:.3f}<br>💡 Annual averages<extra></extra>'
    ))
    
    fig.update_layout(
        title="Annual Visible vs NIR Albedo Comparison",
        xaxis_title="Visible Albedo",
        yaxis_title="NIR Albedo",
        height=600
    )
    
    return fig


def create_spectral_bands_plot(filtered_df, years, colors):
    """Create spectral bands plot"""
    recent_year = years[-1] if years else 2023
    recent_data = filtered_df[filtered_df['year'] == recent_year]
    
    fig = go.Figure()
    
    # Add date labels for recent data
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


def create_vis_nir_ratio_plot(filtered_df):
    """Create visible/NIR ratio plot"""
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
            hovertemplate='<b>Vis/NIR Ratio</b><br>🗓️ Year: %{x}<br>📊 Ratio: %{y:.3f}<br>💡 Annual average<extra></extra>'
        ))
        
        fig.update_layout(
            title="Visible/NIR Ratio Trends Over Time",
            xaxis_title="Year",
            yaxis_title="Vis/NIR Ratio",
            height=600
        )
    else:
        st.error("Visible and NIR data not available for ratio calculation")
        return go.Figure()
    
    return fig


def display_data_statistics(filtered_df, selected_years):
    """Display data statistics for MCD43A3 dashboard"""
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