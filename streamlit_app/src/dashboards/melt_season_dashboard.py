"""
MOD10A1/MYD10A1 Melt Season Analysis Dashboard
Creates interactive visualizations for MODIS daily snow albedo data
Following Williamson & Menounos (2021) methodology
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np


def create_melt_season_dashboard(df_data, df_results, df_focused):
    """
    Create comprehensive MOD10A1/MYD10A1 melt season analysis dashboard
    Following Williamson & Menounos 2021 methodology
    
    Args:
        df_data: Time series data DataFrame
        df_results: Trend analysis results DataFrame  
        df_focused: Focused melt season data DataFrame
    """
    st.subheader("🌊 Daily Snow Albedo Analysis")
    
    if df_data.empty:
        st.error("No melt season data available")
        return
    
    # Prepare data
    df_data = df_data.copy()
    df_data['date'] = pd.to_datetime(df_data['date'])
    df_data['year'] = df_data['date'].dt.year
    df_data['doy'] = df_data['date'].dt.dayofyear
    df_data['month'] = df_data['date'].dt.month
    
    # Sidebar controls
    st.sidebar.header("🌊 Melt Season Controls")
    
    # Year selection
    years = sorted(df_data['year'].unique())
    selected_years = st.sidebar.multiselect(
        "Select Years", 
        years, 
        default=years[-5:] if len(years) >= 5 else years
    )
    
    # Month filter for melt season focus
    months = sorted(df_data['month'].unique())
    selected_months = st.sidebar.multiselect(
        "Select Months (Melt Season)", 
        months,
        default=[6, 7, 8, 9],  # June-September melt season
        help="Default: June-September melt season"
    )
    
    # View type selection
    view_type = st.sidebar.selectbox(
        "Dashboard View",
        [
            "Seasonal Evolution", 
            "Annual Trends", 
            "Melt Season Analysis",
            "Daily Variability",
            "Terra vs Aqua Comparison",
            "Statistical Summary"
        ]
    )
    
    # Filter data
    filtered_df = df_data[
        (df_data['year'].isin(selected_years)) & 
        (df_data['month'].isin(selected_months))
    ]
    
    # Create plots based on view type
    if view_type == "Seasonal Evolution":
        create_seasonal_evolution_view(filtered_df, selected_years)
        
    elif view_type == "Annual Trends":
        create_annual_trends_view(df_data, df_results, selected_years)
        
    elif view_type == "Melt Season Analysis":
        create_melt_season_analysis_view(df_focused, filtered_df)
        
    elif view_type == "Daily Variability":
        create_daily_variability_view(filtered_df)
        
    elif view_type == "Terra vs Aqua Comparison":
        create_terra_aqua_comparison_view(filtered_df)
        
    elif view_type == "Statistical Summary":
        create_statistical_summary_view(df_data, df_results, filtered_df)
    
    # Display data summary at bottom
    display_melt_season_statistics(filtered_df, selected_years, selected_months)


def create_seasonal_evolution_view(filtered_df, selected_years):
    """Create seasonal evolution visualization"""
    
    fig = go.Figure()
    
    # Color palette for years
    colors = px.colors.qualitative.Set1
    
    for i, year in enumerate(selected_years):
        year_data = filtered_df[filtered_df['year'] == year]
        
        if not year_data.empty:
            color = colors[i % len(colors)]
            
            # Main albedo points
            fig.add_trace(go.Scatter(
                x=year_data['doy'],
                y=year_data['albedo_mean'],
                mode='markers',
                name=f'{year}',
                marker=dict(color=color, size=6),
                hovertemplate=f'<b>{year}</b><br>DOY: %{{x}}<br>Albedo: %{{y:.3f}}<br>Date: %{{customdata}}<extra></extra>',
                customdata=year_data['date'].dt.strftime('%Y-%m-%d')
            ))
    
    fig.update_layout(
        title="Daily Snow Albedo Evolution During Melt Season",
        xaxis_title="Day of Year",
        yaxis_title="Snow Albedo",
        height=600,
        hovermode='closest',
        showlegend=True
    )
    
    # Add melt season annotation
    fig.add_vrect(
        x0=152, x1=273,  # June 1 to Sept 30 (approximately)
        annotation_text="Melt Season", 
        annotation_position="top left",
        fillcolor="lightblue", 
        opacity=0.1
    )
    
    st.plotly_chart(fig, use_container_width=True)


def create_annual_trends_view(df_data, df_results, selected_years):
    """Create annual trends analysis"""
    st.subheader("📈 Long-term Albedo Trends")
    
    # Annual statistics
    annual_stats = df_data.groupby('year').agg({
        'albedo_mean': ['mean', 'std', 'min', 'max', 'count']
    }).round(3)
    annual_stats.columns = ['Mean_Albedo', 'Std_Albedo', 'Min_Albedo', 'Max_Albedo', 'Observations']
    annual_stats = annual_stats.reset_index()
    
    # Filter for selected years
    annual_stats_filtered = annual_stats[annual_stats['year'].isin(selected_years)]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Annual Mean Albedo', 'Annual Variability (Std Dev)', 
                       'Observation Count', 'Min-Max Range'),
        vertical_spacing=0.1
    )
    
    # Mean albedo trend
    fig.add_trace(
        go.Scatter(
            x=annual_stats_filtered['year'],
            y=annual_stats_filtered['Mean_Albedo'],
            mode='markers',
            name='Mean Albedo',
            marker=dict(color='blue', size=8)
        ),
        row=1, col=1
    )
    
    # Standard deviation
    fig.add_trace(
        go.Scatter(
            x=annual_stats_filtered['year'],
            y=annual_stats_filtered['Std_Albedo'],
            mode='markers',
            name='Std Dev',
            marker=dict(color='red', size=8)
        ),
        row=1, col=2
    )
    
    # Observation count
    fig.add_trace(
        go.Bar(
            x=annual_stats_filtered['year'],
            y=annual_stats_filtered['Observations'],
            name='Observations',
            marker_color='green'
        ),
        row=2, col=1
    )
    
    # Min-Max range
    fig.add_trace(
        go.Scatter(
            x=annual_stats_filtered['year'],
            y=annual_stats_filtered['Max_Albedo'],
            mode='lines',
            name='Max',
            line=dict(color='orange'),
            fill=None
        ),
        row=2, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=annual_stats_filtered['year'],
            y=annual_stats_filtered['Min_Albedo'],
            mode='lines',
            name='Min',
            line=dict(color='orange'),
            fill='tonexty',
            fillcolor='rgba(255,165,0,0.2)'
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=700,
        title_text="Annual Albedo Trends and Variability",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show trend results if available
    if not df_results.empty:
        st.subheader("📊 Trend Analysis Results")
        try:
            st.dataframe(df_results, use_container_width=True)
        except ImportError as e:
            if "pyarrow" in str(e):
                st.error("PyArrow DLL issue. Using alternative display.")
                st.write("**Trend Results:**")
                st.text(df_results.to_string())
            else:
                st.error(f"Error displaying results: {e}")


def create_melt_season_analysis_view(df_focused, filtered_df):
    """Create focused melt season analysis"""
    st.subheader("🏔️ Focused Melt Season Analysis")
    
    if df_focused.empty:
        st.warning("No focused melt season data available. Showing filtered data instead.")
        analysis_df = filtered_df
    else:
        analysis_df = df_focused.copy()
        analysis_df['date'] = pd.to_datetime(analysis_df['date'])
        analysis_df['year'] = analysis_df['date'].dt.year
        analysis_df['doy'] = analysis_df['date'].dt.dayofyear
    
    if analysis_df.empty:
        st.error("No data available for melt season analysis")
        return
    
    # Monthly analysis
    analysis_df['month'] = analysis_df['date'].dt.month
    monthly_stats = analysis_df.groupby(['year', 'month']).agg({
        'albedo_mean': ['mean', 'std', 'count']
    }).round(3)
    monthly_stats.columns = ['Mean_Albedo', 'Std_Albedo', 'Count']
    monthly_stats = monthly_stats.reset_index()
    
    # Create monthly heatmap
    pivot_data = monthly_stats.pivot(index='year', columns='month', values='Mean_Albedo')
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=[f'Month {int(col)}' for col in pivot_data.columns],
        y=pivot_data.index,
        colorscale='RdYlBu_r',
        text=np.round(pivot_data.values, 3),
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False,
        hovertemplate='Year: %{y}<br>%{x}<br>Albedo: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Monthly Mean Albedo Heatmap (Melt Season)",
        xaxis_title="Month",
        yaxis_title="Year",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Seasonal progression within year
    st.subheader("📅 Intra-seasonal Albedo Patterns")
    
    # Group by day of year for pattern analysis
    doy_stats = analysis_df.groupby('doy').agg({
        'albedo_mean': ['mean', 'std', 'count']
    }).round(3)
    doy_stats.columns = ['Mean_Albedo', 'Std_Albedo', 'Count']
    doy_stats = doy_stats.reset_index()
    
    fig2 = go.Figure()
    
    # Mean points with error bars
    fig2.add_trace(go.Scatter(
        x=doy_stats['doy'],
        y=doy_stats['Mean_Albedo'],
        mode='markers',
        name='Mean Albedo',
        marker=dict(color='blue', size=6),
        error_y=dict(
            type='data',
            array=doy_stats['Std_Albedo'],
            visible=True,
            color='lightblue'
        ),
        hovertemplate='DOY: %{x}<br>Mean Albedo: %{y:.3f}<br>Std Dev: %{error_y.array:.3f}<extra></extra>'
    ))
    
    fig2.update_layout(
        title="Average Seasonal Pattern (All Years Combined)",
        xaxis_title="Day of Year",
        yaxis_title="Mean Albedo ± Std Dev",
        height=400
    )
    
    st.plotly_chart(fig2, use_container_width=True)


def create_daily_variability_view(filtered_df):
    """Create daily variability analysis"""
    st.subheader("📊 Daily Albedo Variability Analysis")
    
    if filtered_df.empty:
        st.error("No data available for variability analysis")
        return
    
    # Calculate daily statistics if multiple pixels per day
    if 'albedo_std' in filtered_df.columns:
        daily_var = filtered_df.groupby(['year', 'doy']).agg({
            'albedo_mean': 'mean',
            'albedo_std': 'mean',
            'pixel_count': 'mean'
        }).reset_index()
    else:
        daily_var = filtered_df.groupby(['year', 'doy']).agg({
            'albedo_mean': ['mean', 'std', 'count']
        }).reset_index()
        daily_var.columns = ['year', 'doy', 'albedo_mean', 'albedo_std', 'pixel_count']
    
    # Box plot by year
    fig1 = go.Figure()
    
    years = sorted(daily_var['year'].unique())
    for year in years:
        year_data = daily_var[daily_var['year'] == year]
        fig1.add_trace(go.Box(
            y=year_data['albedo_mean'],
            name=str(year),
            boxpoints='outliers',
            hovertemplate=f'Year: {year}<br>Albedo: %{{y:.3f}}<extra></extra>'
        ))
    
    fig1.update_layout(
        title="Annual Albedo Distribution (Box Plots)",
        xaxis_title="Year",
        yaxis_title="Albedo",
        height=400
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Variability vs time
    fig2 = go.Figure()
    
    # Scatter plot of standard deviation over time
    if 'albedo_std' in daily_var.columns:
        fig2.add_trace(go.Scatter(
            x=daily_var['doy'],
            y=daily_var['albedo_std'],
            mode='markers',
            marker=dict(
                color=daily_var['year'],
                colorscale='Viridis',
                size=daily_var['pixel_count'],
                sizemode='diameter',
                sizeref=2.*max(daily_var['pixel_count'])/(40.**2),
                sizemin=4,
                colorbar=dict(title="Year")
            ),
            hovertemplate='DOY: %{x}<br>Std Dev: %{y:.3f}<br>Year: %{marker.color}<br>Pixels: %{marker.size}<extra></extra>'
        ))
        
        fig2.update_layout(
            title="Daily Albedo Variability (Standard Deviation)",
            xaxis_title="Day of Year",
            yaxis_title="Albedo Standard Deviation",
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)


def create_terra_aqua_comparison_view(filtered_df):
    """Create Terra vs Aqua satellite comparison"""
    st.subheader("🛰️ Terra vs Aqua Satellite Comparison")
    
    # Check if satellite info is available
    if 'satellite' not in filtered_df.columns:
        st.info("Satellite information not available in current dataset. Showing combined Terra+Aqua data.")
        
        # Show temporal distribution instead
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=filtered_df['doy'],
            name='All Observations',
            nbinsx=50,
            marker_color='skyblue'
        ))
        
        fig.update_layout(
            title="Temporal Distribution of All MODIS Observations",
            xaxis_title="Day of Year",
            yaxis_title="Number of Observations",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        return
    
    # Separate Terra and Aqua data
    terra_data = filtered_df[filtered_df['satellite'].str.contains('Terra|MOD', na=False)]
    aqua_data = filtered_df[filtered_df['satellite'].str.contains('Aqua|MYD', na=False)]
    
    if terra_data.empty and aqua_data.empty:
        st.warning("No Terra or Aqua satellite data identified")
        return
    
    # Comparison plot
    fig = go.Figure()
    
    if not terra_data.empty:
        fig.add_trace(go.Scatter(
            x=terra_data['doy'],
            y=terra_data['albedo_mean'],
            mode='markers',
            name='Terra (MOD10A1)',
            marker=dict(color='red', size=6, symbol='circle'),
            hovertemplate='<b>Terra</b><br>DOY: %{x}<br>Albedo: %{y:.3f}<extra></extra>'
        ))
    
    if not aqua_data.empty:
        fig.add_trace(go.Scatter(
            x=aqua_data['doy'],
            y=aqua_data['albedo_mean'],
            mode='markers',
            name='Aqua (MYD10A1)',
            marker=dict(color='blue', size=6, symbol='square'),
            hovertemplate='<b>Aqua</b><br>DOY: %{x}<br>Albedo: %{y:.3f}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Terra vs Aqua Satellite Comparison",
        xaxis_title="Day of Year",
        yaxis_title="Snow Albedo",
        height=500,
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics comparison
    col1, col2 = st.columns(2)
    
    with col1:
        if not terra_data.empty:
            st.subheader("🔴 Terra Statistics")
            st.metric("Observations", len(terra_data))
            st.metric("Mean Albedo", f"{terra_data['albedo_mean'].mean():.3f}")
            st.metric("Std Dev", f"{terra_data['albedo_mean'].std():.3f}")
    
    with col2:
        if not aqua_data.empty:
            st.subheader("🔵 Aqua Statistics")
            st.metric("Observations", len(aqua_data))
            st.metric("Mean Albedo", f"{aqua_data['albedo_mean'].mean():.3f}")
            st.metric("Std Dev", f"{aqua_data['albedo_mean'].std():.3f}")


def create_statistical_summary_view(df_data, df_results, filtered_df):
    """Create comprehensive statistical summary"""
    st.subheader("📈 Statistical Summary and Quality Metrics")
    
    # Overall statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Observations", len(df_data))
        st.metric("Filtered Observations", len(filtered_df))
    
    with col2:
        st.metric("Years Span", f"{df_data['year'].min()}-{df_data['year'].max()}")
        st.metric("Mean Albedo (All)", f"{df_data['albedo_mean'].mean():.3f}")
    
    with col3:
        st.metric("Std Dev (All)", f"{df_data['albedo_mean'].std():.3f}")
        if filtered_df.empty:
            st.metric("Mean Albedo (Filtered)", "N/A")
        else:
            st.metric("Mean Albedo (Filtered)", f"{filtered_df['albedo_mean'].mean():.3f}")
    
    with col4:
        st.metric("Min Albedo", f"{df_data['albedo_mean'].min():.3f}")
        st.metric("Max Albedo", f"{df_data['albedo_mean'].max():.3f}")
    
    # Quality metrics if available
    if 'pixel_count' in df_data.columns:
        st.subheader("🔍 Data Quality Metrics")
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=df_data['pixel_count'],
            name='Pixel Count Distribution',
            nbinsx=30,
            marker_color='lightgreen'
        ))
        
        fig.update_layout(
            title="Distribution of Valid Pixels per Observation",
            xaxis_title="Number of Valid Pixels",
            yaxis_title="Frequency",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Temporal coverage
    st.subheader("📅 Temporal Coverage Analysis")
    
    monthly_coverage = df_data.groupby(['year', 'month']).size().reset_index(name='observations')
    coverage_pivot = monthly_coverage.pivot(index='year', columns='month', values='observations').fillna(0)
    
    fig = go.Figure(data=go.Heatmap(
        z=coverage_pivot.values,
        x=[f'Month {int(col)}' for col in coverage_pivot.columns],
        y=coverage_pivot.index,
        colorscale='Blues',
        text=coverage_pivot.values.astype(int),
        texttemplate='%{text}',
        textfont={"size": 8},
        hovertemplate='Year: %{y}<br>%{x}<br>Observations: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Temporal Coverage (Observations per Month)",
        xaxis_title="Month",
        yaxis_title="Year", 
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_melt_season_statistics(filtered_df, selected_years, selected_months):
    """Display summary statistics for the melt season dashboard"""
    st.subheader("📊 Current Selection Summary")
    
    if filtered_df.empty:
        st.error("No data available for current selection")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Observations", len(filtered_df))
    with col2:
        st.metric("Years Selected", len(selected_years))
    with col3:
        st.metric("Months Selected", len(selected_months))
    with col4:
        st.metric("Mean Albedo", f"{filtered_df['albedo_mean'].mean():.3f}")
    
    # Additional statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Std Deviation", f"{filtered_df['albedo_mean'].std():.3f}")
    with col2:
        st.metric("Min Albedo", f"{filtered_df['albedo_mean'].min():.3f}")
    with col3:
        st.metric("Max Albedo", f"{filtered_df['albedo_mean'].max():.3f}")
    with col4:
        unique_dates = filtered_df['date'].nunique() if 'date' in filtered_df.columns else len(filtered_df)
        st.metric("Unique Dates", unique_dates)