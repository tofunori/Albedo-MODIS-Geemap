"""
MCD43A3 Temporal Analysis Module
Advanced temporal analysis for MODIS MCD43A3 broadband albedo data
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta


def extract_mcd43a3_time_series_realtime(start_date, end_date, qa_level='standard', 
                                        band_selection='shortwave', diffuse_fraction=0.2, 
                                        max_observations=200):
    """
    Extract MCD43A3 time series with real-time Earth Engine processing
    Adapted from realtime_qa_dashboard.py for MCD43A3 temporal analysis
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)  
        qa_level: Quality filtering level ('strict' or 'standard')
        band_selection: Spectral band ('shortwave', 'vis', 'nir')
        diffuse_fraction: Atmospheric diffuse fraction (0.0-1.0)
        max_observations: Maximum number of observations to extract
        
    Returns:
        DataFrame with temporal MCD43A3 data
    """
    
    # Check for imported data first
    if 'imported_mcd43a3_temporal' in st.session_state:
        imported_df = st.session_state['imported_mcd43a3_temporal']
        st.info("📁 Using imported MCD43A3 CSV data for temporal analysis")
        return imported_df
    
    try:
        from ..utils.ee_utils import initialize_earth_engine, get_roi_from_geojson
        from ..utils.earth_engine.modis_extraction import get_modis_pixels_for_date
        import ee
        
        # Initialize Earth Engine
        ee_available = initialize_earth_engine()
        if not ee_available:
            st.error("Earth Engine not available for real-time extraction")
            return pd.DataFrame()
        
        # Load glacier boundary
        glacier_geojson = _load_glacier_boundary_for_temporal()
        if not glacier_geojson:
            st.error("Could not load glacier boundary")
            return pd.DataFrame()
            
        athabasca_roi = get_roi_from_geojson(glacier_geojson)
        
        # Generate date range focused on melt season
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Process year by year for multi-year extractions to avoid timeouts
        years_span = end_dt.year - start_dt.year + 1
        
        if years_span > 5:  # For extractions longer than 5 years, process year by year
            st.info(f"📅 Multi-year extraction detected ({years_span} years). Processing year by year to avoid timeouts...")
            
            # Generate dates year by year for melt seasons only
            all_dates = []
            for year in range(start_dt.year, end_dt.year + 1):
                # Melt season for this year (June 1 - September 30)
                year_start = max(start_dt, pd.Timestamp(year, 6, 1))
                year_end = min(end_dt, pd.Timestamp(year, 9, 30))
                
                if year_start <= year_end:
                    # Generate dates for this year's melt season with 8-day sampling
                    year_dates = pd.date_range(year_start, year_end, freq='8D')
                    year_dates = [d for d in year_dates if _validate_melt_season_date(d)]
                    all_dates.extend(year_dates)
                    print(f"📅 Year {year}: {len(year_dates)} dates generated for melt season")
            
            date_range = all_dates
            
        else:
            # For shorter extractions, use standard approach
            # For MCD43A3, use more frequent sampling during melt season
            # 16-day cycle is too sparse for melt season analysis, use 8-day sampling
            date_range = pd.date_range(start_dt, end_dt, freq='8D')  # 8-day sampling for better temporal resolution
            
            # CRITICAL: Filter to ensure dates stay within melt season bounds
            # This prevents extraction beyond September 30th
            date_range = [d for d in date_range if d <= end_dt]
            
            # Additional safety: enforce melt season bounds using validated function
            date_range = _filter_dates_to_melt_season(date_range)
        
        st.info(f"📅 Total melt season dates: {len(date_range)} from {date_range[0].strftime('%Y-%m-%d')} to {date_range[-1].strftime('%Y-%m-%d')}" if date_range else "📅 No dates in melt season range")
        
        # Limit observations for performance and reliability with better distribution
        if len(date_range) > max_observations:
            # For multi-year data, ensure we sample from each year proportionally
            if years_span > 1:
                # Sample proportionally from each year
                years = list(range(start_dt.year, end_dt.year + 1))
                samples_per_year = max(1, max_observations // len(years))
                
                sampled_dates = []
                for year in years:
                    year_dates = [d for d in date_range if d.year == year]
                    if year_dates:
                        # Sample evenly from this year
                        step = max(1, len(year_dates) // samples_per_year)
                        year_sample = year_dates[::step][:samples_per_year]
                        sampled_dates.extend(year_sample)
                
                date_range = sampled_dates[:max_observations]
                st.info(f"📊 Sampling strategy: ~{samples_per_year} dates per year, {len(date_range)} total dates selected")
            else:
                # Single year - simple sampling
                step = len(date_range) // max_observations
                date_range = date_range[::step][:max_observations]
        
        # Debug information about date range generation
        print(f"🔍 DEBUG: Date range generation:")
        print(f"   Start date: {start_date} -> {start_dt}")
        print(f"   End date: {end_date} -> {end_dt}")
        print(f"   Generated {len(date_range)} dates")
        if date_range:
            print(f"   First date: {date_range[0].strftime('%Y-%m-%d')}")
            print(f"   Last date: {date_range[-1].strftime('%Y-%m-%d')}")
        
        # Check for existing partial data in session state for resumption
        session_key = f"mcd43a3_extraction_{start_date}_{end_date}_{qa_level}_{band_selection}"
        if session_key in st.session_state:
            existing_data = st.session_state[session_key]
            
            # Filter existing data to only include melt season dates
            valid_existing_data = []
            for item in existing_data:
                if _validate_melt_season_date(item['date']):
                    valid_existing_data.append(item)
            
            if len(valid_existing_data) != len(existing_data):
                removed_count = len(existing_data) - len(valid_existing_data)
                print(f"🧹 Cleaned {removed_count} non-melt-season dates from session cache")
                st.session_state[session_key] = valid_existing_data
            
            existing_dates = [pd.to_datetime(d['date']) for d in valid_existing_data]
            # Only process dates not already extracted
            date_range = [d for d in date_range if d not in existing_dates]
            st.info(f"🔄 Resuming extraction: {len(valid_existing_data)} dates already completed, {len(date_range)} remaining")
            existing_data = valid_existing_data
        else:
            existing_data = []
        
        # Configure QA parameters with safe mapping
        qa_mapping = {
            'strict': 0,
            'standard': 1,
            'relaxed': 2
        }
        qa_threshold = qa_mapping.get(qa_level, 1)  # Default to standard if unknown
        
        # Provide feedback on QA selection
        st.info(f"🔬 Using QA threshold: {qa_threshold} (level: {qa_level})")
        
        # Extract data with progress tracking and robustness improvements
        extracted_data = []
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        st.info(f"🔍 Extracting MCD43A3 data for {len(date_range)} dates...")
        
        # Process in smaller batches to avoid timeouts with enhanced robustness
        # Adjust batch size based on extraction span
        if years_span > 10:
            batch_size = 5   # Very small batches for 10+ year extractions
            pause_time = 2   # Longer pauses
        elif years_span > 5:
            batch_size = 10  # Small batches for 5+ year extractions  
            pause_time = 1.5
        else:
            batch_size = 20  # Standard batches for shorter extractions
            pause_time = 1
            
        total_processed = 0
        failed_dates = []
        consecutive_failures = 0
        max_consecutive_failures = 10  # Stop if too many consecutive failures
        
        st.info(f"🔧 Using batch size: {batch_size}, pause time: {pause_time}s for {years_span}-year extraction")
        
        for batch_start in range(0, len(date_range), batch_size):
            batch_end = min(batch_start + batch_size, len(date_range))
            batch_dates = date_range[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(date_range) - 1) // batch_size + 1
            
            status_container.info(f"📊 Processing batch {batch_num}/{total_batches} (Years: {batch_dates[0].year}-{batch_dates[-1].year})")
            
            batch_successes = 0
            
            for i, date in enumerate(batch_dates):
                date_str = date.strftime('%Y-%m-%d')
                global_index = batch_start + i
                
                try:
                    # Extract pixels for this date with timeout handling
                    modis_pixels = get_modis_pixels_for_date(
                        date_str, athabasca_roi, product='MCD43A3', 
                        qa_threshold=qa_threshold, selected_band=band_selection,
                        diffuse_fraction=diffuse_fraction, silent=True
                    )
                    
                    if modis_pixels and 'features' in modis_pixels:
                        # Extract albedo values from pixels
                        albedo_values = []
                        for feature in modis_pixels['features']:
                            if 'properties' in feature and 'albedo_value' in feature['properties']:
                                albedo_value = feature['properties']['albedo_value']
                                if albedo_value is not None and 0 <= albedo_value <= 1:
                                    albedo_values.append(albedo_value)
                        
                        if albedo_values:
                            # Calculate statistics
                            mean_albedo = sum(albedo_values) / len(albedo_values)
                            std_albedo = pd.Series(albedo_values).std()
                            
                            extracted_data.append({
                                'date': date_str,
                                'albedo_mean': mean_albedo,
                                'albedo_std': std_albedo,
                                'pixel_count': len(albedo_values),
                                'band_type': band_selection,
                                'diffuse_fraction': diffuse_fraction,
                                'qa_level': qa_level
                            })
                            
                            print(f"✅ Successfully extracted {len(albedo_values)} pixels for {date_str}")
                            batch_successes += 1
                            consecutive_failures = 0  # Reset failure counter
                        else:
                            print(f"⚠️ No valid pixels found for {date_str}")
                            consecutive_failures += 1
                    else:
                        print(f"❌ No MODIS data found for {date_str}")
                        failed_dates.append(date_str)
                        consecutive_failures += 1
                    
                    # Update progress
                    total_processed += 1
                    progress_bar.progress(total_processed / len(date_range))
                    
                    # Check for too many consecutive failures
                    if consecutive_failures >= max_consecutive_failures:
                        st.error(f"🚨 Stopping extraction: {consecutive_failures} consecutive failures detected. This may indicate a systematic issue.")
                        break
                    
                except Exception as e:
                    print(f"ERROR: Failed to extract data for {date_str}: {e}")
                    failed_dates.append(date_str)
                    consecutive_failures += 1
                    
                    # For multi-year extractions, be more forgiving of individual failures
                    if consecutive_failures >= max_consecutive_failures:
                        st.error(f"🚨 Stopping extraction: {consecutive_failures} consecutive failures detected.")
                        break
                    continue
            
            # Check if we should stop due to consecutive failures
            if consecutive_failures >= max_consecutive_failures:
                break
            
            # Save progress periodically for long extractions
            if len(extracted_data) > 0 and batch_num % 10 == 0:  # Save every 10 batches
                st.session_state[session_key] = existing_data + extracted_data
                st.info(f"💾 Progress saved: {len(extracted_data)} new extractions completed")
            
            # Enhanced pause between batches with feedback
            if batch_num < total_batches:  # Don't pause after last batch
                print(f"⏸️ Batch {batch_num} completed ({batch_successes}/{len(batch_dates)} successful). Pausing {pause_time}s...")
                import time
                time.sleep(pause_time)
        
        progress_bar.empty()
        status_container.empty()
        
        # Combine existing data with newly extracted data
        all_extracted_data = existing_data + extracted_data
        
        # Save final progress to session state
        if all_extracted_data:
            st.session_state[session_key] = all_extracted_data
        
        # Final extraction report
        new_extractions = len(extracted_data)
        total_extractions = len(all_extracted_data)
        total_attempted = len(date_range) + len(existing_data)
        success_rate = (total_extractions / total_attempted) * 100 if total_attempted > 0 else 0
        
        st.info(f"📊 Extraction session summary:")
        st.info(f"   • New extractions: {new_extractions}")
        st.info(f"   • Total extractions: {total_extractions}")
        st.info(f"   • Success rate: {success_rate:.1f}%")
        
        if all_extracted_data:
            # Final validation: filter all extracted data to ensure only melt season dates
            valid_extracted_data = []
            for item in all_extracted_data:
                if _validate_melt_season_date(item['date']):
                    valid_extracted_data.append(item)
                else:
                    print(f"⚠️ Removing non-melt-season date from results: {item['date']}")
            
            if len(valid_extracted_data) != len(all_extracted_data):
                removed_final = len(all_extracted_data) - len(valid_extracted_data)
                st.warning(f"🧹 Removed {removed_final} dates outside melt season from final results")
            
            if valid_extracted_data:
                df = pd.DataFrame(valid_extracted_data)
                df['date'] = pd.to_datetime(df['date'])
                df['year'] = df['date'].dt.year
                df['doy'] = df['date'].dt.dayofyear
                df['month'] = df['date'].dt.month
                
                # Success summary
                st.success(f"✅ Extraction completed: {len(valid_extracted_data)} total observations ({success_rate:.1f}% success rate)")
                
                # Multi-year extraction summary
                if years_span > 1:
                    year_counts = df['year'].value_counts().sort_index()
                    st.info(f"📅 **Multi-year breakdown**: {dict(year_counts)}")
                
                if failed_dates:
                    st.warning(f"⚠️ Failed to extract data for {len(failed_dates)} dates in this session")
                    if len(failed_dates) <= 10:
                        st.write("Failed dates:", ", ".join(failed_dates[:10]))
                    else:
                        st.write(f"Failed dates (first 10): {', '.join(failed_dates[:10])}... and {len(failed_dates)-10} more")
                
                # Data summary
                date_range_actual = f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
                years_covered = sorted(df['year'].unique())
                st.info(f"📊 **Data coverage**: {date_range_actual} ({len(years_covered)} years: {years_covered})")
                
                # Verify all dates are in melt season
                melt_season_count = sum(1 for d in df['date'] if _validate_melt_season_date(d))
                st.success(f"✅ **Melt season validation**: {melt_season_count}/{len(df)} dates confirmed in melt season (June-September)")
                
                # Add extraction resumption information
                if existing_data:
                    st.info(f"🔄 **Resumption info**: {len(existing_data)} dates from previous sessions + {new_extractions} new extractions")
                
                # Add CSV download functionality
                _add_csv_download_buttons(df, band_selection, qa_level, start_date, end_date)
                
                return df
            else:
                st.warning("📊 No valid melt season data extracted")
                return pd.DataFrame()
        else:
            st.error(f"❌ No data extracted for the specified period. Failed on all {len(failed_dates)} attempted dates.")
            if failed_dates:
                st.write("Some failed dates:", ", ".join(failed_dates[:10]))
            
            # Show session resumption tip for multi-year extractions
            if years_span > 5:
                st.info(f"💡 **Tip for large extractions**: The system saves progress automatically. You can restart the extraction to resume from where it left off.")
            
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error in temporal extraction: {e}")
        return pd.DataFrame()


def _add_csv_download_buttons(df, band_selection, qa_level, start_date, end_date):
    """Add CSV download buttons for extracted data"""
    import io
    from datetime import datetime
    
    st.markdown("### 📥 Download Extracted Data")
    
    # Generate filename with parameters
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"mcd43a3_temporal_data_{band_selection}_{qa_level}_{start_date}_to_{end_date}_{timestamp}"
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Full dataset download
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📊 Download Full Dataset (CSV)",
            data=csv_data,
            file_name=f"{base_filename}_full.csv",
            mime="text/csv",
            help=f"Download all {len(df)} extracted observations with metadata"
        )
    
    with col2:
        # Summary statistics download  
        summary_stats = df.groupby(['year', 'month']).agg({
            'albedo_mean': ['mean', 'std', 'min', 'max', 'count'],
            'pixel_count': 'mean'
        }).round(4)
        
        # Flatten column names
        summary_stats.columns = ['_'.join(col).strip() for col in summary_stats.columns]
        summary_stats = summary_stats.reset_index()
        
        summary_buffer = io.StringIO()
        summary_stats.to_csv(summary_buffer, index=False, encoding='utf-8')
        summary_data = summary_buffer.getvalue()
        
        st.download_button(
            label="📈 Download Summary Stats (CSV)", 
            data=summary_data,
            file_name=f"{base_filename}_summary.csv",
            mime="text/csv",
            help="Download monthly summary statistics"
        )
    
    # Dataset info
    st.markdown("**📋 Dataset Information:**")
    st.markdown(f"""
    - **Product**: MCD43A3 ({band_selection} band)
    - **Quality Level**: {qa_level}
    - **Period**: {start_date} to {end_date}
    - **Observations**: {len(df)}
    - **Years Covered**: {sorted(df['year'].unique())}
    - **Diffuse Fraction**: {df['diffuse_fraction'].iloc[0]:.2f}
    """)


def create_temporal_evolution_plot(df, analysis_type='seasonal'):
    """
    Create comprehensive temporal evolution plots for MCD43A3
    
    Args:
        df: DataFrame with temporal MCD43A3 data
        analysis_type: Type of analysis ('seasonal', 'annual', 'monthly', 'detailed')
        
    Returns:
        Plotly figure object
    """
    if df.empty:
        return go.Figure().add_annotation(text="No data available", 
                                        xref="paper", yref="paper", x=0.5, y=0.5)
    
    if analysis_type == 'seasonal':
        return _create_seasonal_evolution_plot(df)
    elif analysis_type == 'annual':
        return _create_annual_trends_plot(df)
    elif analysis_type == 'monthly':
        return _create_monthly_analysis_plot(df)
    elif analysis_type == 'detailed':
        return _create_detailed_temporal_plot(df)
    else:
        return _create_seasonal_evolution_plot(df)


def _create_seasonal_evolution_plot(df):
    """Create seasonal evolution plot (DOY-based)"""
    fig = go.Figure()
    
    years = sorted(df['year'].unique())
    colors = px.colors.qualitative.Set3
    
    for i, year in enumerate(years):
        year_data = df[df['year'] == year]
        if not year_data.empty:
            color = colors[i % len(colors)]
            
            fig.add_trace(go.Scatter(
                x=year_data['doy'],
                y=year_data['albedo_mean'],
                mode='markers+lines',
                name=f'{year}',
                marker=dict(color=color, size=8),
                line=dict(color=color, width=2),
                error_y=dict(
                    type='data',
                    array=year_data['albedo_std'],
                    visible=True,
                    width=2
                ),
                hovertemplate=f'<b>{year}</b><br>' +
                            '📅 Date: %{customdata}<br>' +
                            '📊 Albedo: %{y:.3f}<br>' +
                            '📈 DOY: %{x}<br>' +
                            '🔢 Pixels: %{text}<extra></extra>',
                customdata=year_data['date'].dt.strftime('%B %d, %Y'),
                text=year_data['pixel_count']
            ))
    
    fig.update_layout(
        title="MCD43A3 Seasonal Evolution - Daily Broadband Albedo",
        xaxis_title="Day of Year",
        yaxis_title="Albedo",
        height=600,
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def _create_annual_trends_plot(df):
    """Create annual trends analysis"""
    # Calculate annual statistics
    annual_stats = df.groupby('year').agg({
        'albedo_mean': ['mean', 'std', 'count'],
        'pixel_count': 'mean'
    }).round(4)
    
    annual_stats.columns = ['mean_albedo', 'std_albedo', 'observation_count', 'avg_pixels']
    annual_stats = annual_stats.reset_index()
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Annual Mean Albedo Trends', 'Data Coverage'),
        vertical_spacing=0.12,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
    )
    
    # Annual albedo trends
    fig.add_trace(
        go.Scatter(
            x=annual_stats['year'],
            y=annual_stats['mean_albedo'],
            mode='markers+lines',
            name='Mean Albedo',
            marker=dict(color='blue', size=10),
            line=dict(color='blue', width=3),
            error_y=dict(
                type='data',
                array=annual_stats['std_albedo'],
                visible=True,
                width=3
            ),
            hovertemplate='<b>%{x}</b><br>📊 Mean Albedo: %{y:.3f}<br>📈 Std: %{error_y.array:.3f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Data coverage
    fig.add_trace(
        go.Bar(
            x=annual_stats['year'],
            y=annual_stats['observation_count'],
            name='Observations',
            marker=dict(color='lightblue'),
            hovertemplate='<b>%{x}</b><br>📈 Observations: %{y}<br>🔢 Avg Pixels: %{customdata:.1f}<extra></extra>',
            customdata=annual_stats['avg_pixels']
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        title_text="MCD43A3 Multi-Year Analysis (2010-2024)"
    )
    
    return fig


def _create_monthly_analysis_plot(df):
    """Create monthly analysis plot"""
    df['month_name'] = df['date'].dt.strftime('%B')
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    monthly_stats = df.groupby(['month', 'month_name']).agg({
        'albedo_mean': ['mean', 'std', 'count']
    }).round(4)
    
    monthly_stats.columns = ['mean_albedo', 'std_albedo', 'count']
    monthly_stats = monthly_stats.reset_index()
    
    # Reorder by month
    monthly_stats['month_name'] = pd.Categorical(monthly_stats['month_name'], 
                                               categories=month_order, ordered=True)
    monthly_stats = monthly_stats.sort_values('month_name')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=monthly_stats['month_name'],
        y=monthly_stats['mean_albedo'],
        error_y=dict(
            type='data',
            array=monthly_stats['std_albedo'],
            visible=True
        ),
        marker=dict(
            color=monthly_stats['mean_albedo'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Mean Albedo")
        ),
        hovertemplate='<b>%{x}</b><br>📊 Mean Albedo: %{y:.3f}<br>📈 Std: %{error_y.array:.3f}<br>📈 Count: %{customdata}<extra></extra>',
        customdata=monthly_stats['count']
    ))
    
    fig.update_layout(
        title="MCD43A3 Monthly Albedo Patterns",
        xaxis_title="Month",
        yaxis_title="Mean Albedo",
        height=600
    )
    
    return fig


def _create_detailed_temporal_plot(df):
    """Create detailed temporal plot with all data points"""
    fig = go.Figure()
    
    # Color by year for temporal progression
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['albedo_mean'],
        mode='markers',
        marker=dict(
            color=df['year'],
            colorscale='Viridis',
            size=8,
            showscale=True,
            colorbar=dict(title="Year")
        ),
        error_y=dict(
            type='data',
            array=df['albedo_std'],
            visible=True
        ),
        hovertemplate='<b>%{x}</b><br>📊 Albedo: %{y:.3f}<br>🔢 Pixels: %{customdata}<extra></extra>',
        customdata=df['pixel_count']
    ))
    
    fig.update_layout(
        title="MCD43A3 Complete Temporal Record (2010-2024)",
        xaxis_title="Date",
        yaxis_title="Albedo",
        height=600,
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    return fig


def _validate_melt_season_date(date):
    """
    Validate if a date falls within the melt season (June 1 - September 30)
    Following glaciology literature standards
    
    Args:
        date: datetime object or date string
        
    Returns:
        bool: True if date is in melt season, False otherwise
    """
    if isinstance(date, str):
        date = pd.to_datetime(date)
    
    month = date.month
    day = date.day
    
    # Melt season bounds: June 1 to September 30
    if month == 6 and day >= 1:  # June 1-30
        return True
    elif month in [7, 8]:  # July and August (full months)
        return True
    elif month == 9 and day <= 30:  # September 1-30
        return True
    else:
        return False


def _filter_dates_to_melt_season(date_list):
    """
    Filter a list of dates to only include melt season dates
    
    Args:
        date_list: List of datetime objects
        
    Returns:
        List of filtered datetime objects within melt season
    """
    filtered_dates = []
    removed_count = 0
    
    for date in date_list:
        if _validate_melt_season_date(date):
            filtered_dates.append(date)
        else:
            removed_count += 1
    
    if removed_count > 0:
        print(f"🧹 Filtered out {removed_count} dates outside melt season")
        print(f"✅ Kept {len(filtered_dates)} dates within melt season bounds")
    
    return filtered_dates


def _load_glacier_boundary_for_temporal():
    """Load glacier boundary for temporal analysis"""
    import json
    import os
    
    # Try different paths
    paths = [
        '../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',
        '../../data/geospatial/masks/Athabasca_mask_2023_cut.geojson',
        'Athabasca_mask_2023_cut.geojson'
    ]
    
    for path in paths:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            continue
    
    return None


def create_comparative_analysis(df_mcd43a3, df_mod10a1=None):
    """
    Create comparative analysis between MCD43A3 and MOD10A1 (if available)
    
    Args:
        df_mcd43a3: MCD43A3 temporal data
        df_mod10a1: MOD10A1 temporal data (optional)
        
    Returns:
        Plotly figure object
    """
    if df_mod10a1 is not None and not df_mod10a1.empty:
        return _create_product_comparison_plot(df_mcd43a3, df_mod10a1)
    else:
        return _create_mcd43a3_summary_plot(df_mcd43a3)


def _create_product_comparison_plot(df_mcd43a3, df_mod10a1):
    """Create comparison plot between MCD43A3 and MOD10A1"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('MCD43A3 vs MOD10A1 Albedo Comparison', 'Data Coverage Comparison'),
        vertical_spacing=0.12
    )
    
    # Resample both datasets to same frequency for comparison
    df_mcd43a3_monthly = df_mcd43a3.set_index('date').resample('M')['albedo_mean'].mean()
    df_mod10a1_monthly = df_mod10a1.set_index('date').resample('M')['albedo_mean'].mean()
    
    # Albedo comparison
    fig.add_trace(
        go.Scatter(
            x=df_mcd43a3_monthly.index,
            y=df_mcd43a3_monthly.values,
            mode='lines+markers',
            name='MCD43A3 (Broadband)',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_mod10a1_monthly.index,
            y=df_mod10a1_monthly.values,
            mode='lines+markers',
            name='MOD10A1 (Snow)',
            line=dict(color='red', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    # Data coverage
    mcd43a3_counts = df_mcd43a3.groupby('year').size()
    mod10a1_counts = df_mod10a1.groupby('year').size()
    
    fig.add_trace(
        go.Bar(
            x=mcd43a3_counts.index,
            y=mcd43a3_counts.values,
            name='MCD43A3 Count',
            marker=dict(color='lightblue'),
            offset=-0.2,
            width=0.4
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=mod10a1_counts.index,
            y=mod10a1_counts.values,
            name='MOD10A1 Count',
            marker=dict(color='lightcoral'),
            offset=0.2,
            width=0.4
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=800,
        title_text="MODIS Product Comparison: MCD43A3 vs MOD10A1"
    )
    
    return fig


def _create_mcd43a3_summary_plot(df_mcd43a3):
    """Create summary plot for MCD43A3 only"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Temporal Evolution', 'Annual Statistics', 
                       'Monthly Patterns', 'Quality Metrics'),
        specs=[[{"colspan": 2}, None],
               [{}, {}]]
    )
    
    # Main temporal plot
    fig.add_trace(
        go.Scatter(
            x=df_mcd43a3['date'],
            y=df_mcd43a3['albedo_mean'],
            mode='markers+lines',
            name='MCD43A3',
            marker=dict(color='blue', size=6),
            line=dict(width=2)
        ),
        row=1, col=1
    )
    
    # Annual stats
    annual_stats = df_mcd43a3.groupby('year')['albedo_mean'].mean()
    fig.add_trace(
        go.Bar(
            x=annual_stats.index,
            y=annual_stats.values,
            name='Annual Mean',
            marker=dict(color='lightblue')
        ),
        row=2, col=1
    )
    
    # Monthly patterns
    monthly_stats = df_mcd43a3.groupby('month')['albedo_mean'].mean()
    fig.add_trace(
        go.Bar(
            x=monthly_stats.index,
            y=monthly_stats.values,
            name='Monthly Mean',
            marker=dict(color='green')
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=800,
        title_text="MCD43A3 Comprehensive Analysis",
        showlegend=False
    )
    
    return fig