"""
Real-time QA Comparison Dashboard
Interactive dashboard for comparing different QA filtering levels using live Google Earth Engine data
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

from ..utils.realtime_extraction import (
    extract_modis_time_series_realtime,
    compare_qa_levels_realtime,
    extract_modis_time_series_custom_qa,
    diagnose_qa_distribution,
    diagnose_custom_qa_impact,
    get_qa_level_info
)


def create_realtime_qa_dashboard():
    """
    Create real-time QA comparison dashboard using live Google Earth Engine data
    """
    st.header("🚀 Real-time QA Level Comparison")
    st.markdown("""
    **Compare different QA filtering levels using live Google Earth Engine data**
    
    This dashboard extracts MODIS data in real-time and applies actual QA filtering
    (not simulation) to show the true impact of different quality control levels.
    """)
    
    # Configuration section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📅 Time Period")
        # Default to recent melt season
        current_year = datetime.now().year
        default_start = datetime(current_year - 1, 6, 1)  # Last year's melt season
        default_end = datetime(current_year - 1, 9, 30)
        
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            min_value=datetime(2000, 1, 1),
            max_value=datetime.now()
        )
        
        end_date = st.date_input(
            "End Date", 
            value=default_end,
            min_value=start_date,
            max_value=datetime.now()
        )
    
    with col2:
        st.subheader("🛰️ MODIS Product")
        product = st.selectbox(
            "Select Product",
            ['MOD10A1', 'MCD43A3'],
            help="MOD10A1: Daily snow albedo, MCD43A3: Broadband albedo"
        )
        
        max_obs = st.slider(
            "Max Observations",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
            help="Limit number of observations for faster processing"
        )
    
    with col3:
        st.subheader("⚙️ QA Level Info")
        qa_info = get_qa_level_info()
        
        # Show QA level descriptions
        for qa_level, config in qa_info.items():
            retention = config['expected_retention'] * 100
            st.markdown(f"**{config['name']}**: {retention:.0f}% retention")
    
    # QA Analysis Mode Selection
    st.subheader("🔬 QA Analysis Mode")
    
    analysis_mode = st.radio(
        "Choose Analysis Mode",
        ["Preset QA Levels", "Custom QA Configuration (Expert Mode)"],
        horizontal=True
    )
    
    if analysis_mode == "Custom QA Configuration (Expert Mode)":
        # Custom QA Configuration Section
        st.subheader("⚙️ Custom QA Configuration")
        st.markdown("**Configure your own QA filtering parameters with full control**")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📊 Basic QA Parameters**")
            
            custom_basic_qa = st.selectbox(
                "Basic QA Threshold",
                [0, 1, 2],
                index=1,
                help="0=Best only, 1=Best+Good, 2=Best+Good+OK"
            )
            
            use_algorithm_flags = st.checkbox(
                "Enable Algorithm QA Flags",
                value=True,
                help="Use NDSI_Snow_Cover_Algorithm_Flags_QA band"
            )
            
            if use_algorithm_flags:
                st.markdown("**🏔️ Algorithm QA Flags (Individual Control)**")
                
                filter_water = st.checkbox(
                    "🌊 Filter Inland Water (Bit 0)",
                    value=True,
                    help="Critical: Remove pixels flagged as inland water"
                )
                
                filter_low_visible = st.checkbox(
                    "🔆 Filter Low Visible Reflectance (Bit 1)",
                    value=True,
                    help="Critical: Remove pixels with low visible reflectance"
                )
                
                filter_low_ndsi = st.checkbox(
                    "❄️ Filter Low NDSI (Bit 2)",
                    value=True,
                    help="Critical: Remove pixels with low NDSI (weak snow signal)"
                )
                
                filter_temp_height = st.checkbox(
                    "🌡️ Filter Temperature/Height Issues (Bit 3)",
                    value=False,
                    help="Remove pixels with temperature/height screening issues (common on glaciers)"
                )
                
                filter_spatial = st.checkbox(
                    "🗺️ Filter Spatial Issues (Bit 4)",
                    value=False,
                    help="Remove pixels with spatial processing issues"
                )
                
                filter_clouds = st.checkbox(
                    "☁️ Filter Probable Clouds (Bit 5)",
                    value=True,
                    help="Critical: Remove pixels flagged as probably cloudy"
                )
                
                filter_radiometric = st.checkbox(
                    "📡 Filter Radiometric Issues (Bit 6)",
                    value=False,
                    help="Remove pixels with radiometric processing issues"
                )
        
        with col2:
            st.markdown("**🛰️ MCD43A3 Parameters**")
            
            mcd43a3_qa_threshold = st.selectbox(
                "MCD43A3 QA Threshold",
                [0, 1],
                index=1,
                help="0=Full BRDF inversions only, 1=Include magnitude inversions"
            )
            
            st.markdown("**📈 Expected Impact Preview**")
            
            # Calculate expected retention based on settings
            base_retention = 1.0
            
            if custom_basic_qa == 0:
                base_retention *= 0.7  # Stricter basic QA
            elif custom_basic_qa == 2:
                base_retention *= 1.1  # More lenient (capped at 1.0)
            
            if use_algorithm_flags:
                flags_count = sum([filter_water, filter_low_visible, filter_low_ndsi, 
                                 filter_temp_height, filter_spatial, filter_clouds, filter_radiometric])
                # Each flag reduces retention
                base_retention *= (0.95 ** flags_count)
            
            expected_retention = min(base_retention, 1.0)
            
            st.metric(
                "Expected Data Retention",
                f"{expected_retention*100:.1f}%",
                help="Estimated percentage of data retained with current settings"
            )
            
            # Quality assessment
            if expected_retention > 0.8:
                st.success("🟢 High data retention - Good for temporal coverage")
            elif expected_retention > 0.5:
                st.warning("🟡 Moderate data retention - Balanced approach")
            else:
                st.error("🔴 Low data retention - High quality but limited coverage")
            
            # Create custom configuration
            custom_qa_config = {
                'name': 'Custom QA Configuration',
                'description': f'Custom: Basic QA ≤ {custom_basic_qa}, {flags_count if use_algorithm_flags else 0} algorithm flags',
                'mod10a1_basic_qa_threshold': custom_basic_qa,
                'mod10a1_use_algorithm_flags': use_algorithm_flags,
                'mod10a1_filter_water': filter_water if use_algorithm_flags else False,
                'mod10a1_filter_low_visible': filter_low_visible if use_algorithm_flags else False,
                'mod10a1_filter_low_ndsi': filter_low_ndsi if use_algorithm_flags else False,
                'mod10a1_filter_temp_height': filter_temp_height if use_algorithm_flags else False,
                'mod10a1_filter_spatial': filter_spatial if use_algorithm_flags else False,
                'mod10a1_filter_clouds': filter_clouds if use_algorithm_flags else False,
                'mod10a1_filter_radiometric': filter_radiometric if use_algorithm_flags else False,
                'mcd43a3_qa_threshold': mcd43a3_qa_threshold,
                'expected_retention': expected_retention
            }
            
            # Debug information
            with st.expander("🔍 Debug: Configuration Details", expanded=False):
                st.json(custom_qa_config)
                st.markdown(f"""
                **Key Settings:**
                - Basic QA Threshold: {custom_basic_qa} (should differ between 0 and 1)
                - Algorithm Flags Enabled: {use_algorithm_flags}
                - Active Flags: {[k for k, v in custom_qa_config.items() if k.startswith('mod10a1_filter_') and v]}
                """)
            
            # Store in session state
            st.session_state['custom_qa_config'] = custom_qa_config
        
        # Custom extraction button
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🚀 Extract with Custom QA", type="primary"):
                with st.spinner("Extracting live MODIS data with custom QA configuration..."):
                    df_custom = extract_modis_time_series_custom_qa(
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        custom_qa_config,
                        product=product,
                        max_observations=max_obs
                    )
                    
                    if not df_custom.empty:
                        st.session_state['custom_qa_data'] = df_custom
                        st.success(f"✅ Extracted {len(df_custom)} observations with custom QA")
                    else:
                        st.error("❌ No data found with current custom configuration")
        
        with col2:
            # Diagnose custom QA impact button
            if st.button("🔍 Diagnose QA Impact", type="secondary"):
                with st.spinner("Analyzing custom QA impact on real data..."):
                    qa_impact = diagnose_custom_qa_impact(
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        custom_qa_config
                    )
                    
                    if qa_impact:
                        st.session_state['qa_impact_analysis'] = qa_impact
                        st.success("✅ QA impact analysis complete!")
                    else:
                        st.error("❌ QA impact analysis failed")
        
        # Display QA impact analysis
        if 'qa_impact_analysis' in st.session_state:
            impact = st.session_state['qa_impact_analysis']
            
            with st.expander("📊 Custom QA Impact Analysis", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Images Analyzed", impact['total_images'])
                    st.metric("Basic QA Threshold", impact['basic_qa_threshold'])
                    
                with col2:
                    if impact.get('basic_retention_rate'):
                        st.metric("Basic QA Retention", f"{impact['basic_retention_rate']:.1f}%")
                    if impact.get('qa_0_percentage'):
                        st.metric("QA=0 Pixels", f"{impact['qa_0_percentage']:.1f}%")
                        
                with col3:
                    if impact.get('qa_1_percentage'):
                        st.metric("QA=1 Pixels", f"{impact['qa_1_percentage']:.1f}%")
                    if impact.get('qa_2_percentage'):
                        st.metric("QA=2 Pixels", f"{impact['qa_2_percentage']:.1f}%")
                
                # Interpretation
                st.markdown("**🎯 Analysis Results:**")
                qa_0_pct = impact.get('qa_0_percentage', 0)
                qa_1_pct = impact.get('qa_1_percentage', 0)
                
                if qa_0_pct > 95:
                    st.success("✅ Data is dominated by QA=0 (best quality) pixels")
                    if qa_1_pct < 5:
                        st.warning("⚠️ **This explains why QA threshold 0 vs 1 shows similar results!**")
                        st.info("💡 Very few QA=1 pixels exist, so changing threshold has minimal impact")
                
                if impact.get('algorithm_flags_enabled'):
                    st.info("🏁 Algorithm flags are enabled - these may provide better differentiation")
                else:
                    st.info("🏁 Algorithm flags disabled - only basic QA filtering active")
        
            # Display custom results if available
        if 'custom_qa_data' in st.session_state:
            df_custom = st.session_state['custom_qa_data']
            
            st.subheader("📊 Custom QA Results")
            
            # Statistics summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Observations", len(df_custom))
            with col2:
                st.metric("Mean Albedo", f"{df_custom['albedo_mean'].mean():.3f}")
            with col3:
                st.metric("Std Deviation", f"{df_custom['albedo_mean'].std():.3f}")
            with col4:
                st.metric("Mean Pixels/Day", f"{df_custom['pixel_count'].mean():.0f}")
            
            # Time series plot
            fig_custom = px.scatter(
                df_custom,
                x='date',
                y='albedo_mean',
                title='Custom QA Albedo Time Series',
                hover_data=['pixel_count', 'albedo_stdDev'],
                labels={'albedo_mean': 'Albedo', 'date': 'Date'}
            )
            fig_custom.update_traces(mode='markers')
            fig_custom.update_layout(height=400)
            st.plotly_chart(fig_custom, use_container_width=True)
        
    else:
        # Original preset QA levels interface
        st.subheader("📋 Preset QA Level Analysis")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            selected_qa = st.selectbox(
                "Select QA Level for Detailed Analysis",
                list(qa_info.keys()),
                index=1,  # Default to advanced_balanced (recommended)
                format_func=lambda x: qa_info[x]['name']
            )
        
        
        with col2:
            if st.button("🚀 Extract Real-time Data", type="primary"):
                with st.spinner("Extracting live MODIS data from Google Earth Engine..."):
                    df_single = extract_modis_time_series_realtime(
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        qa_level=selected_qa,
                        product=product,
                        max_observations=max_obs
                    )
                    
                    if not df_single.empty:
                        st.session_state['realtime_single_data'] = df_single
                        st.success(f"✅ Extracted {len(df_single)} observations with {qa_info[selected_qa]['name']}")
                    else:
                        st.error("❌ No data found for the selected parameters")
    
    # Display single QA level results (outside of else block)
    if 'realtime_single_data' in st.session_state:
        df_single = st.session_state['realtime_single_data']
        
        # Get the QA configuration name from the data or use default
        qa_config_name = df_single.get('qa_config', ['Unknown QA Level']).iloc[0] if 'qa_config' in df_single.columns else "QA Level Analysis"
        
        # Statistics summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Observations", len(df_single))
        with col2:
            st.metric("Mean Albedo", f"{df_single['albedo_mean'].mean():.3f}")
        with col3:
            st.metric("Std Deviation", f"{df_single['albedo_mean'].std():.3f}")
        with col4:
            st.metric("Mean Pixels/Day", f"{df_single['pixel_count'].mean():.0f}")
        
        # Time series plot
        fig_ts = px.scatter(
            df_single,
            x='date',
            y='albedo_mean',
            title=f'Real-time Albedo Time Series - {qa_config_name}',
            hover_data=['pixel_count', 'albedo_stdDev'],
            labels={
                'albedo_mean': 'Albedo',
                'date': 'Date'
            }
        )
        fig_ts.update_traces(mode='markers')
        fig_ts.update_layout(height=400)
        st.plotly_chart(fig_ts, use_container_width=True)
        
        # Data quality metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Pixel count over time
            fig_pixels = px.line(
                df_single,
                x='date',
                y='pixel_count',
                title='Valid Pixels Over Time',
                labels={'pixel_count': 'Number of Valid Pixels', 'date': 'Date'}
            )
            fig_pixels.update_layout(height=300)
            st.plotly_chart(fig_pixels, use_container_width=True)
        
        with col2:
            # Albedo distribution
            fig_hist = px.histogram(
                df_single,
                x='albedo_mean',
                nbins=30,
                title='Albedo Distribution',
                labels={'albedo_mean': 'Albedo', 'count': 'Frequency'}
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
    
    # QA Distribution Diagnosis
    st.subheader("🔍 QA Distribution Diagnosis")
    st.markdown("**Analyze the actual QA values present in your MODIS data**")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔬 Diagnose QA Distribution", type="secondary"):
            with st.spinner("Analyzing QA distribution in MODIS data..."):
                qa_diag = diagnose_qa_distribution(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if qa_diag:
                    st.session_state['qa_diagnosis'] = qa_diag
                    st.success("✅ QA diagnosis complete!")
                else:
                    st.error("❌ QA diagnosis failed")
    
    with col2:
        if 'qa_diagnosis' in st.session_state:
            diag = st.session_state['qa_diagnosis']
            st.markdown("**QA Distribution Results:**")
            
            if diag.get('qa_0_percent', 0) > 0:
                st.write(f"🟢 QA=0 (Best): {diag['qa_0_percent']:.1f}%")
            if diag.get('qa_1_percent', 0) > 0:
                st.write(f"🟡 QA=1 (Good): {diag['qa_1_percent']:.1f}%")
            if diag.get('qa_2_percent', 0) > 0:
                st.write(f"🟠 QA=2 (OK): {diag['qa_2_percent']:.1f}%")
            if diag.get('qa_higher_percent', 0) > 0:
                st.write(f"🔴 QA≥3 (Poor): {diag['qa_higher_percent']:.1f}%")
    
    # Display QA diagnosis results in detail
    if 'qa_diagnosis' in st.session_state:
        diag = st.session_state['qa_diagnosis']
        
        with st.expander("📊 Detailed QA Analysis"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Images Analyzed", diag['total_images'])
                st.metric("QA=0 Pixels", f"{diag['qa_0_total']:,}")
                
            with col2:
                st.metric("QA=1 Pixels", f"{diag['qa_1_total']:,}")
                st.metric("QA=2 Pixels", f"{diag['qa_2_total']:,}")
                
            with col3:
                st.metric("QA≥3 Pixels", f"{diag['qa_higher_total']:,}")
                total_pixels = (diag['qa_0_total'] + diag['qa_1_total'] + 
                               diag['qa_2_total'] + diag['qa_higher_total'])
                st.metric("Total Pixels", f"{total_pixels:,}")
            
            # QA distribution chart
            if total_pixels > 0:
                qa_df = pd.DataFrame({
                    'QA Level': ['QA=0 (Best)', 'QA=1 (Good)', 'QA=2 (OK)', 'QA≥3 (Poor)'],
                    'Pixels': [diag['qa_0_total'], diag['qa_1_total'], 
                              diag['qa_2_total'], diag['qa_higher_total']],
                    'Percentage': [diag.get('qa_0_percent', 0), diag.get('qa_1_percent', 0),
                                  diag.get('qa_2_percent', 0), diag.get('qa_higher_percent', 0)]
                })
                
                # Remove zero entries
                qa_df = qa_df[qa_df['Pixels'] > 0]
                
                if not qa_df.empty:
                    fig_qa = px.pie(
                        qa_df,
                        values='Pixels',
                        names='QA Level',
                        title='QA Distribution in Your Dataset',
                        color_discrete_sequence=['green', 'yellow', 'orange', 'red']
                    )
                    fig_qa.update_layout(height=400)
                    st.plotly_chart(fig_qa, use_container_width=True)
                    
                    # Interpretation
                    st.markdown("**🎯 Interpretation:**")
                    if diag.get('qa_0_percent', 0) > 80:
                        st.success("✅ Excellent data quality - mostly best quality pixels")
                    elif diag.get('qa_0_percent', 0) + diag.get('qa_1_percent', 0) > 80:
                        st.info("ℹ️ Good data quality - mostly best+good pixels")
                    else:
                        st.warning("⚠️ Mixed data quality - significant lower quality pixels present")
                    
                    if diag.get('qa_1_percent', 0) < 5:
                        st.error("🚨 **PROBLEM DETECTED**: Very few QA=1 pixels found!")
                        st.error("This explains why QA threshold 0 vs 1 shows similar results.")
                        st.info("💡 Try using Algorithm QA flags for better differentiation.")

    # QA Levels Comparison
    st.subheader("📊 Real-time QA Levels Comparison")
    st.markdown("**Compare all QA levels simultaneously using live Earth Engine data**")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        comparison_period = st.selectbox(
            "Comparison Time Period",
            [
                "Last 3 months",
                "Last 6 months", 
                "2023 Melt Season",
                "2022 Melt Season",
                "Custom"
            ]
        )
        
        if comparison_period == "Custom":
            comp_start = st.date_input("Comparison Start", value=start_date)
            comp_end = st.date_input("Comparison End", value=end_date)
        elif comparison_period == "Last 3 months":
            comp_end = datetime.now()
            comp_start = comp_end - timedelta(days=90)
        elif comparison_period == "Last 6 months":
            comp_end = datetime.now()
            comp_start = comp_end - timedelta(days=180)
        elif comparison_period == "2023 Melt Season":
            comp_start = datetime(2023, 6, 1)
            comp_end = datetime(2023, 9, 30)
        else:  # 2022 Melt Season
            comp_start = datetime(2022, 6, 1)
            comp_end = datetime(2022, 9, 30)
    
    with col2:
        if st.button("🔄 Compare All QA Levels", type="secondary"):
            with st.spinner("Comparing QA levels using real-time Earth Engine data..."):
                comparison_results = compare_qa_levels_realtime(
                    comp_start.strftime('%Y-%m-%d'),
                    comp_end.strftime('%Y-%m-%d'),
                    product=product
                )
                
                if comparison_results:
                    st.session_state['realtime_comparison'] = comparison_results
                    st.success("✅ Real-time QA comparison complete!")
                else:
                    st.error("❌ QA comparison failed")
    
    # Display comparison results
    if 'realtime_comparison' in st.session_state:
        results = st.session_state['realtime_comparison']
        
        # Create comparison table with pixel statistics
        comparison_data = []
        max_obs = max([r['count'] for r in results.values() if r['count'] > 0], default=1)
        max_pixels = max([r['mean_pixels'] for r in results.values() if r['mean_pixels'] > 0], default=1)
        
        for qa_level, data in results.items():
            # Calculate total pixels across all observations
            total_pixels = data['mean_pixels'] * data['count'] if data['count'] > 0 else 0
            pixel_retention = (data['mean_pixels'] / max_pixels) * 100 if max_pixels > 0 else 0
            
            comparison_data.append({
                'QA Level': data['config']['name'],
                'Observations': data['count'],
                'Obs Retention %': f"{(data['count'] / max_obs) * 100:.1f}%",
                'Avg Pixels/Obs': f"{data['mean_pixels']:.1f}" if data['mean_pixels'] > 0 else "0",
                'Pixel Retention %': f"{pixel_retention:.1f}%",
                'Total Pixels': f"{total_pixels:.0f}",
                'Mean Albedo': f"{data['mean_albedo']:.3f}" if data['mean_albedo'] is not None else "N/A",
                'Std Dev': f"{data['std_albedo']:.3f}" if data['std_albedo'] is not None else "N/A",
                'Range': f"{data['min_albedo']:.3f} - {data['max_albedo']:.3f}" if data['min_albedo'] is not None else "N/A"
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        
        st.subheader("📋 QA Levels Comparison Table")
        st.dataframe(df_comparison, use_container_width=True)
        
        # Extract pixel data for visualization FIRST
        pixel_data = []
        for qa_level, data in results.items():
            if data['count'] > 0:
                pixel_data.append({
                    'QA Level': data['config']['name'],
                    'Avg Pixels per Observation': data['mean_pixels'],
                    'Total Pixels': data['mean_pixels'] * data['count'],
                    'Observations': data['count']
                })
        
        # Pixel impact summary
        st.subheader("🎯 Pixel Filtering Impact Summary")
        
        # Calculate pixel filtering statistics
        max_avg_pixels = max([r['mean_pixels'] for r in results.values() if r['mean_pixels'] > 0], default=1)
        
        summary_cols = st.columns(3)
        
        for i, (qa_level, data) in enumerate(results.items()):
            if data['count'] > 0:
                with summary_cols[i % 3]:
                    config_name = data['config']['name']
                    pixel_retention = (data['mean_pixels'] / max_avg_pixels) * 100 if max_avg_pixels > 0 else 0
                    
                    st.metric(
                        label=f"📊 {config_name}",
                        value=f"{data['mean_pixels']:.1f} pixels/obs",
                        delta=f"{pixel_retention:.1f}% retention"
                    )
        
        # Detailed pixel analysis
        with st.expander("🔍 Detailed Pixel Analysis"):
            st.markdown("""
            ### Interpretation des Résultats Pixels
            
            **Pixels par Observation**: Nombre moyen de pixels MODIS valides par date d'observation
            - Plus de pixels = Meilleure couverture spatiale du glacier
            - Moins de pixels = Filtrage plus strict, mais données plus pures
            
            **Pixel Retention %**: Pourcentage de pixels conservés vs niveau QA le moins strict
            - 100% = Tous les pixels du niveau de base
            - <100% = Filtrage progressif des pixels de moindre qualité
            
            **Total Pixels**: Pixels × Observations = Volume total de données
            - Metric importante pour analyses statistiques robustes
            - Trade-off entre qualité et quantité de données
            """)
            
            if pixel_data:
                # Show detailed breakdown
                for item in pixel_data:
                    st.markdown(f"""
                    **{item['QA Level']}:**
                    - {item['Avg Pixels per Observation']:.1f} pixels/observation 
                    - {item['Total Pixels']:.0f} pixels total
                    - {item['Observations']} observations
                    """)
        
        st.info("""
        💡 **Points Clés**: 
        - **Fewer pixels ≠ Bad**: Un filtrage strict peut donner moins de pixels mais de meilleure qualité
        - **Spatial Coverage**: Surveillez que vous gardez assez de pixels pour représenter le glacier
        - **Statistical Power**: Plus de pixels total = Analyses statistiques plus robustes
        """)
        
        # Pixel retention analysis
        st.subheader("🔍 Pixel Retention Analysis")
        
        if pixel_data:
            df_pixels = pd.DataFrame(pixel_data)
            
            # Three-column pixel visualization
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Average pixels per observation
                fig_avg_pixels = px.bar(
                    df_pixels,
                    x='QA Level',
                    y='Avg Pixels per Observation',
                    title='Average Pixels per Observation',
                    color='Avg Pixels per Observation',
                    color_continuous_scale='blues'
                )
                fig_avg_pixels.update_layout(height=350, xaxis_tickangle=45)
                st.plotly_chart(fig_avg_pixels, use_container_width=True)
            
            with col2:
                # Total pixels across all observations
                fig_total_pixels = px.bar(
                    df_pixels,
                    x='QA Level',
                    y='Total Pixels',
                    title='Total Pixels (All Observations)',
                    color='Total Pixels',
                    color_continuous_scale='greens'
                )
                fig_total_pixels.update_layout(height=350, xaxis_tickangle=45)
                st.plotly_chart(fig_total_pixels, use_container_width=True)
            
            with col3:
                # Pixel efficiency (pixels per observation)
                df_pixels['Pixel Efficiency'] = df_pixels['Total Pixels'] / df_pixels['Observations']
                fig_efficiency = px.bar(
                    df_pixels,
                    x='QA Level',
                    y='Pixel Efficiency',
                    title='Pixel Efficiency<br>(Total Pixels ÷ Observations)',
                    color='Pixel Efficiency',
                    color_continuous_scale='oranges'
                )
                fig_efficiency.update_layout(height=350, xaxis_tickangle=45)
                st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # Data retention comparison
        st.subheader("📊 Data & Albedo Comparison")
        col1, col2 = st.columns(2)
        
        with col1:
            # Observation retention rates
            fig_retention = px.bar(
                df_comparison,
                x='QA Level',
                y='Observations',
                title='Observations Retained by QA Level',
                color='Observations',
                color_continuous_scale='viridis',
                text='Obs Retention %'
            )
            fig_retention.update_traces(textposition='outside')
            fig_retention.update_layout(height=400, xaxis_tickangle=45)
            st.plotly_chart(fig_retention, use_container_width=True)
        
        with col2:
            # Albedo means comparison
            valid_results = {k: v for k, v in results.items() if v['mean_albedo'] is not None}
            if valid_results:
                qa_names = [results[k]['config']['name'] for k in valid_results.keys()]
                mean_albedos = [v['mean_albedo'] for v in valid_results.values()]
                std_albedos = [v['std_albedo'] for v in valid_results.values()]
                
                fig_albedo = go.Figure()
                fig_albedo.add_trace(go.Bar(
                    x=qa_names,
                    y=mean_albedos,
                    error_y=dict(type='data', array=std_albedos),
                    name='Mean Albedo ± Std Dev',
                    marker_color='lightblue'
                ))
                fig_albedo.update_layout(
                    title='Albedo Statistics by QA Level',
                    yaxis_title='Albedo',
                    xaxis_tickangle=45,
                    height=400
                )
                st.plotly_chart(fig_albedo, use_container_width=True)
        
        # Time series comparison (if data available)
        valid_datasets = {k: v for k, v in results.items() if not v['data'].empty}
        
        if valid_datasets:
            st.subheader("📈 Time Series Comparison")
            
            fig_comparison = go.Figure()
            
            colors = ['blue', 'green', 'red', 'orange']
            for i, (qa_level, data) in enumerate(valid_datasets.items()):
                df_qa = data['data']
                fig_comparison.add_trace(go.Scatter(
                    x=df_qa['date'],
                    y=df_qa['albedo_mean'],
                    mode='markers',
                    name=data['config']['name'],
                    marker=dict(color=colors[i % len(colors)], size=6),
                    opacity=0.7
                ))
            
            fig_comparison.update_layout(
                title='Albedo Time Series - All QA Levels',
                xaxis_title='Date',
                yaxis_title='Albedo',
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Technical Information
    with st.expander("🔧 Technical Details"):
        st.markdown("""
        ### Real-time Data Extraction Process
        
        1. **Earth Engine Authentication**: Connects to Google Earth Engine using service account
        2. **QA Filter Application**: Applies actual MODIS QA filtering (not simulation)
        3. **Time Series Extraction**: Extracts albedo statistics for Athabasca Glacier
        4. **Quality Control**: Validates results and provides metadata
        
        ### QA Filtering Details (3 Optimized Levels)
        
        **Standard QA**: Basic QA ≤ 1 (original system)
        - Uses only NDSI_Snow_Cover_Basic_QA band
        - Maximum data retention (~100%)
        - Use case: Exploratory analysis, maximum temporal coverage
        
        **Advanced QA Balanced**: Basic QA ≤ 2 + Critical algorithm filtering  
        - Filters critical contamination (water, clouds, low signals)
        - Allows temp/height and spatial flagged pixels (common on glaciers)
        - Optimal balance quality/coverage (~80% retention)
        - **RECOMMENDED for most research**
        
        **Advanced QA Strict**: Basic QA ≤ 1 + Comprehensive algorithm filtering
        - Filters critical flags + temp/height + spatial issues
        - Publication-grade filtering (~30% retention)
        - Use case: High-quality case studies, method validation
        
        ### Performance Notes
        - Caching enabled for 5-10 minutes to reduce Earth Engine calls
        - Maximum observations limited for dashboard performance
        - Real-time extraction may take 30-60 seconds depending on date range
        """)
    
    return True