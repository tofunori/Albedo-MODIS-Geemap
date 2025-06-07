"""
Interactive Plotly Plots for MCD43A3 Spectral Analysis
Creates interactive dashboards for MCD43A3 spectral analysis
Following Williamson & Menounos (2021) methodology
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.offline as pyo


def create_interactive_seasonal_evolution(df, output_file='interactive_seasonal_evolution.html'):
    """
    Create interactive plotly dashboard for MCD43A3 seasonal evolution
    
    Args:
        df: DataFrame with MCD43A3 spectral data
        output_file: Output HTML filename
    """
    if df.empty:
        print("❌ No data to plot")
        return
    
    # Prepare data
    df_copy = df.copy()
    df_copy['date'] = pd.to_datetime(df_copy['date'])
    
    # Get unique years for dropdown
    years = sorted(df_copy['year'].unique())
    
    # Create single plot layout - will use tabs/menus to switch between different views
    fig = go.Figure()
    
    # Color scheme
    colors = {
        'Albedo_BSA_vis': '#1f77b4',      # Blue
        'Albedo_BSA_nir': '#d62728',      # Red
        'Albedo_BSA_Band1': '#ff7f0e',    # Orange (Red band)
        'Albedo_BSA_Band2': '#2ca02c',    # Green (NIR band)
        'Albedo_BSA_Band3': '#9467bd',    # Purple (Blue band)
        'Albedo_BSA_Band4': '#8c564b'     # Brown (Green band)
    }
    
    # Create different view datasets
    
    # View 1: Seasonal Evolution (all years) - DEFAULT VIEW
    seasonal_traces = []
    for year in years:
        year_data = df_copy[df_copy['year'] == year]
        
        if len(year_data) > 0:
            # Visible band
            if 'Albedo_BSA_vis' in year_data.columns:
                seasonal_traces.append(
                    go.Scatter(
                        x=year_data['doy'],
                        y=year_data['Albedo_BSA_vis'],
                        mode='markers',
                        name=f'{year} Visible',
                        marker=dict(
                            color=colors['Albedo_BSA_vis'],
                            size=6,
                            opacity=0.7,
                            line=dict(width=1, color='white')
                        ),
                        hovertemplate=f'<b>{year} Visible</b><br>' +
                                     'DOY: %{x}<br>' +
                                     'Albedo: %{y:.3f}<br>' +
                                     '<extra></extra>',
                        visible=True,
                        legendgroup='seasonal',
                        showlegend=bool(year == years[0])
                    )
                )
            
            # NIR band
            if 'Albedo_BSA_nir' in year_data.columns:
                seasonal_traces.append(
                    go.Scatter(
                        x=year_data['doy'],
                        y=year_data['Albedo_BSA_nir'],
                        mode='markers',
                        name=f'{year} NIR',
                        marker=dict(
                            color=colors['Albedo_BSA_nir'],
                            size=6,
                            opacity=0.7,
                            symbol='square',
                            line=dict(width=1, color='white')
                        ),
                        hovertemplate=f'<b>{year} NIR</b><br>' +
                                     'DOY: %{x}<br>' +
                                     'Albedo: %{y:.3f}<br>' +
                                     '<extra></extra>',
                        visible=True,
                        legendgroup='seasonal',
                        showlegend=bool(year == years[0])
                    )
                )
    
    # View 2: Visible vs NIR scatter (annual means)
    vis_nir_traces = []
    annual_data = df_copy.groupby('year').agg({
        'Albedo_BSA_vis': 'mean',
        'Albedo_BSA_nir': 'mean'
    }).reset_index()
    
    if not annual_data.empty:
        vis_nir_traces.append(
            go.Scatter(
                x=annual_data['Albedo_BSA_vis'],
                y=annual_data['Albedo_BSA_nir'],
                mode='markers+text',
                text=annual_data['year'],
                textposition='top center',
                marker=dict(
                    size=12,
                    color=annual_data['year'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Year")
                ),
                hovertemplate='<b>Year %{text}</b><br>' +
                             'Visible: %{x:.3f}<br>' +
                             'NIR: %{y:.3f}<br>' +
                             '<extra></extra>',
                name='Annual Means',
                visible=False,
                legendgroup='vis_nir'
            )
        )
    
    # View 3: All spectral bands overview (recent year)
    spectral_traces = []
    recent_year = years[-1] if years else None
    if recent_year:
        recent_data = df_copy[df_copy['year'] == recent_year]
        
        for band, color in colors.items():
            if band in recent_data.columns:
                spectral_traces.append(
                    go.Scatter(
                        x=recent_data['doy'],
                        y=recent_data[band],
                        mode='markers',
                        name=band.replace('Albedo_BSA_', ''),
                        marker=dict(color=color, size=6, opacity=0.7),
                        hovertemplate=f'<b>{band.replace("Albedo_BSA_", "")}</b><br>' +
                                     'DOY: %{x}<br>' +
                                     'Albedo: %{y:.3f}<br>' +
                                     '<extra></extra>',
                        visible=False,
                        legendgroup='spectral'
                    )
                )
    
    # View 4: Vis/NIR ratio over time
    ratio_traces = []
    if 'Albedo_BSA_vis' in df_copy.columns and 'Albedo_BSA_nir' in df_copy.columns:
        df_copy['vis_nir_ratio'] = df_copy['Albedo_BSA_vis'] / df_copy['Albedo_BSA_nir']
        
        # Annual averages
        ratio_annual = df_copy.groupby('year')['vis_nir_ratio'].mean().reset_index()
        
        ratio_traces.append(
            go.Scatter(
                x=ratio_annual['year'],
                y=ratio_annual['vis_nir_ratio'],
                mode='markers+lines',
                name='Vis/NIR Ratio',
                marker=dict(size=8, color='purple'),
                line=dict(color='purple', width=2),
                hovertemplate='<b>Vis/NIR Ratio</b><br>' +
                             'Year: %{x}<br>' +
                             'Ratio: %{y:.3f}<br>' +
                             '<extra></extra>',
                visible=False,
                legendgroup='ratio'
            )
        )
    
    # Add all traces to figure
    for trace in seasonal_traces + vis_nir_traces + spectral_traces + ratio_traces:
        fig.add_trace(trace)
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'MCD43A3 Interactive Seasonal Evolution Dashboard<br>' +
                   '<sub>Athabasca Glacier - Daily Albedo Analysis</sub>',
            'x': 0.5,
            'font': {'size': 20}
        },
        height=700,
        width=1200,
        hovermode='closest',
        template='plotly_white',
        font=dict(size=12),
        xaxis_title="Variable X-axis (depends on view)",
        yaxis_title="Variable Y-axis (depends on view)"
    )
    
    # Create button menu for different views
    view_buttons = [
        dict(
            label="🌊 Seasonal Evolution",
            method="update",
            args=[
                {
                    "visible": [trace.legendgroup == 'seasonal' for trace in fig.data] + 
                               [False] * (len(vis_nir_traces) + len(spectral_traces) + len(ratio_traces))
                },
                {
                    "title": "Seasonal Evolution - Daily Albedo Patterns",
                    "xaxis": {"title": "Day of Year", "tickvals": [152, 182, 213, 244], "ticktext": ["Jun", "Jul", "Aug", "Sep"]},
                    "yaxis": {"title": "Albedo"}
                }
            ]
        ),
        dict(
            label="📊 Visible vs NIR",
            method="update",
            args=[
                {
                    "visible": [False] * len(seasonal_traces) + 
                               [trace.legendgroup == 'vis_nir' for trace in vis_nir_traces] +
                               [False] * (len(spectral_traces) + len(ratio_traces))
                },
                {
                    "title": "Annual Visible vs NIR Comparison",
                    "xaxis": {"title": "Visible Albedo"},
                    "yaxis": {"title": "NIR Albedo"}
                }
            ]
        ),
        dict(
            label="🌈 Spectral Bands",
            method="update", 
            args=[
                {
                    "visible": [False] * (len(seasonal_traces) + len(vis_nir_traces)) +
                               [trace.legendgroup == 'spectral' for trace in spectral_traces] +
                               [False] * len(ratio_traces)
                },
                {
                    "title": f"All Spectral Bands - {recent_year}",
                    "xaxis": {"title": "Day of Year", "tickvals": [152, 182, 213, 244], "ticktext": ["Jun", "Jul", "Aug", "Sep"]},
                    "yaxis": {"title": "Albedo"}
                }
            ]
        ),
        dict(
            label="📈 Vis/NIR Ratio",
            method="update",
            args=[
                {
                    "visible": [False] * (len(seasonal_traces) + len(vis_nir_traces) + len(spectral_traces)) +
                               [trace.legendgroup == 'ratio' for trace in ratio_traces]
                },
                {
                    "title": "Visible/NIR Ratio Trends Over Time",
                    "xaxis": {"title": "Year"},
                    "yaxis": {"title": "Vis/NIR Ratio"}
                }
            ]
        )
    ]
    
    # Add year selection dropdown (only affects seasonal view)
    year_buttons = []
    
    # Add "All Years" option for seasonal view
    year_buttons.append(
        dict(
            label="All Years",
            method="update",
            args=[{
                "visible": [True if trace.legendgroup == 'seasonal' else False for trace in fig.data]
            }]
        )
    )
    
    # Add individual year options for seasonal view
    for year in years:
        visibility = []
        for trace in fig.data:
            if trace.legendgroup == 'seasonal' and str(year) in trace.name:
                visibility.append(True)
            else:
                visibility.append(False)
        
        year_buttons.append(
            dict(
                label=f"Year {year}",
                method="update",
                args=[{"visible": visibility}]
            )
        )
    
    # Update layout with multiple menus
    fig.update_layout(
        updatemenus=[
            # View selection menu (main)
            dict(
                buttons=view_buttons,
                direction="down",
                showactive=True,
                x=0.02,
                xanchor="left",
                y=1.02,
                yanchor="top",
                bgcolor="lightblue",
                bordercolor="darkblue",
                borderwidth=1
            ),
            # Year selection menu (only for seasonal view)
            dict(
                buttons=year_buttons,
                direction="down",
                showactive=True,
                x=0.25,
                xanchor="left", 
                y=1.02,
                yanchor="top",
                bgcolor="lightgreen",
                bordercolor="darkgreen",
                borderwidth=1
            )
        ]
    )
    
    # Add annotations
    fig.add_annotation(
        text="View Type:",
        xref="paper", yref="paper",
        x=0.01, y=1.05,
        showarrow=False,
        font=dict(size=14, weight="bold")
    )
    
    fig.add_annotation(
        text="Year Filter:",
        xref="paper", yref="paper",
        x=0.24, y=1.05,
        showarrow=False,
        font=dict(size=14, weight="bold")
    )
    
    fig.add_annotation(
        text="Daily values (16-day moving window)",
        xref="paper", yref="paper",
        x=0.99, y=0.01,
        showarrow=False,
        font=dict(size=10, style="italic"),
        xanchor="right"
    )
    
    # Save interactive plot
    from src.paths import get_map_path
    output_path = get_map_path(output_file, 'interactive')
    
    # Save as HTML
    fig.write_html(str(output_path))
    
    print(f"🌐 Interactive seasonal evolution dashboard saved: {output_path}")
    print("📂 Open the HTML file in your web browser to explore the data")
    
    return fig