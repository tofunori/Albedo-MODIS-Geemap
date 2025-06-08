"""
Quality Assessment (QA) Configuration Module for MODIS Albedo Analysis
Provides configurable QA filtering levels for different analysis requirements
"""

import streamlit as st
import pandas as pd


# QA Level Configurations
QA_LEVELS = {
    "Standard QA": {
        "description": "Balanced quality filtering (recommended for most analyses)",
        "modis_snow": {
            "qa_threshold": 1,
            "description": "QA ≤ 1 (best + good quality)",
            "expected_coverage": "~70-80% of potential observations"
        },
        "mcd43a3": {
            "qa_threshold": 0,
            "description": "QA = 0 (full BRDF inversions only)",
            "expected_coverage": "~60-70% of potential observations"
        }
    },
    "Advanced Relaxed": {
        "description": "Maximum data coverage (includes lower quality data)",
        "modis_snow": {
            "qa_threshold": 2,
            "description": "QA ≤ 2 (includes fair quality)",
            "expected_coverage": "~85-95% of potential observations"
        },
        "mcd43a3": {
            "qa_threshold": 1,
            "description": "QA ≤ 1 (includes magnitude inversions)",
            "expected_coverage": "~80-90% of potential observations"
        }
    },
    "Advanced Standard": {
        "description": "Standard research-grade filtering",
        "modis_snow": {
            "qa_threshold": 1,
            "description": "QA ≤ 1 (best + good quality)",
            "expected_coverage": "~70-80% of potential observations"
        },
        "mcd43a3": {
            "qa_threshold": 0,
            "description": "QA = 0 (full BRDF inversions only)",
            "expected_coverage": "~60-70% of potential observations"
        }
    },
    "Advanced Strict": {
        "description": "Highest quality data only (reduced coverage)",
        "modis_snow": {
            "qa_threshold": 0,
            "description": "QA = 0 (best quality only)",
            "expected_coverage": "~50-60% of potential observations"
        },
        "mcd43a3": {
            "qa_threshold": 0,
            "description": "QA = 0 (full BRDF inversions only)",
            "expected_coverage": "~60-70% of potential observations"
        }
    }
}


def create_qa_selector():
    """
    Create QA level selector widget in sidebar
    
    Returns:
        tuple: (selected_qa_level, qa_config)
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🔧 Quality Assessment Settings")
    
    # QA Level selection
    selected_qa_level = st.sidebar.selectbox(
        "📊 QA Filtering Level:",
        list(QA_LEVELS.keys()),
        index=0,  # Default to "Standard QA"
        key="qa_level_selector",
        help="Choose the quality filtering level for MODIS data analysis"
    )
    
    qa_config = QA_LEVELS[selected_qa_level]
    
    # Display selected QA level info
    with st.sidebar.expander("ℹ️ Selected QA Level Details", expanded=False):
        st.markdown(f"**{selected_qa_level}**")
        st.markdown(qa_config["description"])
        
        st.markdown("**MOD10A1/MYD10A1 (Snow Albedo):**")
        st.markdown(f"• {qa_config['modis_snow']['description']}")
        st.markdown(f"• {qa_config['modis_snow']['expected_coverage']}")
        
        st.markdown("**MCD43A3 (Broadband Albedo):**")
        st.markdown(f"• {qa_config['mcd43a3']['description']}")
        st.markdown(f"• {qa_config['mcd43a3']['expected_coverage']}")
    
    # Show current QA settings summary
    st.sidebar.markdown("**📋 Current QA Settings:**")
    st.sidebar.markdown(f"• **Level:** {selected_qa_level}")
    st.sidebar.markdown(f"• **Snow QA:** ≤ {qa_config['modis_snow']['qa_threshold']}")
    st.sidebar.markdown(f"• **Broadband QA:** ≤ {qa_config['mcd43a3']['qa_threshold']}")
    
    return selected_qa_level, qa_config


def apply_qa_filtering(df, product_type, qa_config, show_stats=True):
    """
    Apply QA filtering to dataframe based on selected configuration
    
    Args:
        df: DataFrame with MODIS data
        product_type: 'modis_snow' or 'mcd43a3'
        qa_config: QA configuration from QA_LEVELS
        show_stats: Whether to show filtering statistics
        
    Returns:
        tuple: (filtered_df, filtering_stats)
    """
    if df.empty:
        return df, {"original_count": 0, "filtered_count": 0, "retention_rate": 0}
    
    original_count = len(df)
    qa_threshold = None  # Initialize to avoid UnboundLocalError
    
    # Apply QA filtering based on product type
    try:
        if product_type == 'modis_snow':
            # Try to get QA threshold from config, with fallback
            if isinstance(qa_config, dict) and 'modis_snow' in qa_config:
                qa_threshold = qa_config['modis_snow']['qa_threshold']
            else:
                qa_threshold = 1  # Default fallback
            
            # Check if QA column exists
            qa_columns = [col for col in df.columns if 'qa' in col.lower() or 'quality' in col.lower()]
            
            if qa_columns:
                qa_column = qa_columns[0]  # Use first QA column found
                filtered_df = df[df[qa_column] <= qa_threshold].copy()
            else:
                # If no QA column, return original data with warning
                if show_stats:
                    st.warning(f"No QA column found for {product_type}. Using unfiltered data.")
                filtered_df = df.copy()
                
        elif product_type == 'mcd43a3':
            # Try to get QA threshold from config, with fallback
            if isinstance(qa_config, dict) and 'mcd43a3' in qa_config:
                qa_threshold = qa_config['mcd43a3']['qa_threshold']
            else:
                qa_threshold = 0  # Default fallback for MCD43A3
            
            # Check for MCD43A3 QA columns
            qa_columns = [col for col in df.columns if 'brdf' in col.lower() and 'quality' in col.lower()]
            
            if qa_columns:
                qa_column = qa_columns[0]  # Use first QA column found
                filtered_df = df[df[qa_column] <= qa_threshold].copy()
            else:
                # If no QA column, return original data with warning
                if show_stats:
                    st.warning(f"No QA column found for {product_type}. Using unfiltered data.")
                filtered_df = df.copy()
        else:
            # Unknown product type, return original data
            if show_stats:
                st.warning(f"Unknown product type: {product_type}. Using unfiltered data.")
            filtered_df = df.copy()
    
    except (KeyError, TypeError) as e:
        # Handle config structure errors gracefully
        if show_stats:
            st.warning(f"QA config error for {product_type}: {e}. Using unfiltered data.")
        filtered_df = df.copy()
    
    filtered_count = len(filtered_df)
    retention_rate = (filtered_count / original_count * 100) if original_count > 0 else 0
    
    filtering_stats = {
        "original_count": original_count,
        "filtered_count": filtered_count,
        "retention_rate": retention_rate,
        "qa_threshold": qa_threshold if 'qa_threshold' in locals() else None,
        "product_type": product_type
    }
    
    if show_stats and qa_threshold is not None:
        st.sidebar.success(f"✅ QA Filtering Applied: {filtered_count:,} of {original_count:,} records retained ({retention_rate:.1f}%)")
    
    return filtered_df, filtering_stats


def create_qa_comparison_widget():
    """
    Create widget to compare different QA levels
    
    Returns:
        list: Selected QA levels for comparison
    """
    st.sidebar.markdown("---")
    st.sidebar.header("📊 QA Level Comparison")
    
    # Multi-select for QA comparison
    comparison_levels = st.sidebar.multiselect(
        "Select QA levels to compare:",
        list(QA_LEVELS.keys()),
        default=[],
        key="qa_comparison_selector",
        help="Compare data coverage and statistics across different QA levels"
    )
    
    return comparison_levels


def display_qa_comparison_stats(df_dict, product_type="modis_snow"):
    """
    Display comparison statistics for different QA levels
    
    Args:
        df_dict: Dictionary with QA level names as keys and DataFrames as values
        product_type: Type of MODIS product for appropriate filtering
    """
    if not df_dict:
        return
    
    st.markdown("### 📊 QA Level Comparison")
    
    # Create comparison table
    comparison_data = []
    
    for qa_level, df in df_dict.items():
        if df.empty:
            continue
            
        qa_config = QA_LEVELS[qa_level]
        
        # Apply filtering to get statistics
        filtered_df, stats = apply_qa_filtering(df, product_type, qa_config, show_stats=False)
        
        # Calculate additional statistics
        if not filtered_df.empty and 'albedo_mean' in filtered_df.columns:
            mean_albedo = filtered_df['albedo_mean'].mean()
            std_albedo = filtered_df['albedo_mean'].std()
            min_albedo = filtered_df['albedo_mean'].min()
            max_albedo = filtered_df['albedo_mean'].max()
            unique_dates = filtered_df['date_str'].nunique() if 'date_str' in filtered_df.columns else len(filtered_df)
        else:
            mean_albedo = std_albedo = min_albedo = max_albedo = unique_dates = 0
        
        comparison_data.append({
            "QA Level": qa_level,
            "Records": f"{stats['filtered_count']:,}",
            "Retention": f"{stats['retention_rate']:.1f}%",
            "Mean Albedo": f"{mean_albedo:.3f}" if mean_albedo > 0 else "N/A",
            "Std Dev": f"{std_albedo:.3f}" if std_albedo > 0 else "N/A",
            "Range": f"{min_albedo:.3f} - {max_albedo:.3f}" if min_albedo > 0 else "N/A",
            "Unique Dates": f"{unique_dates:,}" if unique_dates > 0 else "N/A"
        })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        st.dataframe(
            comparison_df,
            use_container_width=True,
            column_config={
                "QA Level": st.column_config.TextColumn("QA Level", width=120),
                "Records": st.column_config.TextColumn("Records", width=80),
                "Retention": st.column_config.TextColumn("Retention %", width=80),
                "Mean Albedo": st.column_config.TextColumn("Mean Albedo", width=90),
                "Std Dev": st.column_config.TextColumn("Std Dev", width=80),
                "Range": st.column_config.TextColumn("Albedo Range", width=120),
                "Unique Dates": st.column_config.TextColumn("Unique Dates", width=90)
            },
            hide_index=True
        )
        
        # Add interpretation notes
        st.markdown("**📋 Interpretation Notes:**")
        st.markdown("• **Records**: Total observations after QA filtering")
        st.markdown("• **Retention**: Percentage of original data retained after filtering")
        st.markdown("• **Mean Albedo**: Average albedo value across all observations")
        st.markdown("• **Std Dev**: Standard deviation indicating data variability")
        st.markdown("• **Range**: Minimum and maximum albedo values observed")
        st.markdown("• **Unique Dates**: Number of different observation dates")
    else:
        st.info("No data available for comparison")


def get_qa_level_color(qa_level):
    """
    Get consistent color coding for QA levels
    
    Args:
        qa_level: QA level name
        
    Returns:
        str: Color code for the QA level
    """
    colors = {
        "Standard QA": "#1f77b4",      # Blue
        "Advanced Relaxed": "#2ca02c",  # Green  
        "Advanced Standard": "#ff7f0e", # Orange
        "Advanced Strict": "#d62728"    # Red
    }
    
    return colors.get(qa_level, "#7f7f7f")  # Default gray


def create_qa_impact_visualization(df_dict, product_type="modis_snow"):
    """
    Create visualization showing impact of different QA levels
    
    Args:
        df_dict: Dictionary with QA level names as keys and DataFrames as values
        product_type: Type of MODIS product
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    if not df_dict:
        return None
    
    # Prepare data for visualization
    qa_levels = []
    record_counts = []
    retention_rates = []
    mean_albedos = []
    
    for qa_level, df in df_dict.items():
        if df.empty:
            continue
            
        qa_config = QA_LEVELS[qa_level]
        filtered_df, stats = apply_qa_filtering(df, product_type, qa_config, show_stats=False)
        
        qa_levels.append(qa_level)
        record_counts.append(stats['filtered_count'])
        retention_rates.append(stats['retention_rate'])
        
        if not filtered_df.empty and 'albedo_mean' in filtered_df.columns:
            mean_albedos.append(filtered_df['albedo_mean'].mean())
        else:
            mean_albedos.append(0)
    
    if not qa_levels:
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Data Records", "Retention Rate (%)", "Mean Albedo"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Colors for each QA level
    colors = [get_qa_level_color(qa) for qa in qa_levels]
    
    # Record counts
    fig.add_trace(
        go.Bar(x=qa_levels, y=record_counts, name="Records", marker_color=colors),
        row=1, col=1
    )
    
    # Retention rates
    fig.add_trace(
        go.Bar(x=qa_levels, y=retention_rates, name="Retention %", marker_color=colors),
        row=1, col=2
    )
    
    # Mean albedos
    fig.add_trace(
        go.Bar(x=qa_levels, y=mean_albedos, name="Mean Albedo", marker_color=colors),
        row=1, col=3
    )
    
    # Update layout
    fig.update_layout(
        title="QA Level Impact Comparison",
        height=400,
        showlegend=False
    )
    
    # Update x-axes to rotate labels
    for i in range(1, 4):
        fig.update_xaxes(tickangle=45, row=1, col=i)
    
    return fig