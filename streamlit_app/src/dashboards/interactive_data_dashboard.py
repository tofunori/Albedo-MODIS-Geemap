"""
Interactive Data Table Dashboard
Provides Excel-style data exploration and analysis capabilities
"""

import streamlit as st
import pandas as pd


def create_interactive_data_table_dashboard(df_data):
    """
    Create interactive data table with search, filter, and export capabilities
    """
    st.markdown("#### 📋 Interactive Data Table")
    st.markdown("*Excel-style data exploration and analysis*")
    
    if df_data.empty:
        st.warning("No data available for the table")
        return
    
    # Prepare data for the table
    table_data = df_data.copy()
    
    # Check available columns and determine date column
    available_columns = table_data.columns.tolist()
    
    # Debug: Show available columns
    with st.expander("🔍 Debug: Available Data Columns", expanded=False):
        st.write("Available columns:", available_columns)
        st.write("Data shape:", table_data.shape)
        if not table_data.empty:
            st.write("First few rows:")
            st.dataframe(table_data.head())
    
    # Find the date column (could be 'date', 'date_str', etc.)
    date_column = None
    for col in ['date_str', 'date', 'observation_date']:
        if col in available_columns:
            date_column = col
            break
    
    if date_column is None:
        st.error(f"No date column found in the data. Available columns: {available_columns}")
        return
    
    # Create date_str column if it doesn't exist
    if 'date_str' not in available_columns:
        if 'date' in available_columns:
            # Convert date to string format
            table_data['date_str'] = pd.to_datetime(table_data['date']).dt.strftime('%Y-%m-%d')
        else:
            st.error("Unable to create date string column")
            return
    
    # Count observations per date (this is what we have in the data)
    pixel_counts_per_date = table_data.groupby('date_str').size().reset_index(name='observations_count')
    table_data = table_data.merge(pixel_counts_per_date, on='date_str', how='left')
    
    # Select relevant columns that exist in the data
    columns_to_show = ['date_str', 'albedo_mean']
    
    # Add optional columns if they exist
    if 'albedo_std' in available_columns:
        columns_to_show.append('albedo_std')
    if 'elevation' in available_columns:
        columns_to_show.append('elevation')
    
    # Always add observations count
    columns_to_show.append('observations_count')
    
    # Create display dataframe
    display_df = table_data[columns_to_show].copy()
    
    # Rename columns for clarity
    column_names = ['Date', 'Mean Albedo']
    if 'albedo_std' in columns_to_show:
        column_names.append('Std Dev')
    if 'elevation' in columns_to_show:
        column_names.append('Elevation (m)')
    column_names.append('Observations')
    
    display_df.columns = column_names
    
    # Round numeric columns
    if 'Mean Albedo' in display_df.columns:
        display_df['Mean Albedo'] = display_df['Mean Albedo'].round(4)
    if 'Std Dev' in display_df.columns:
        display_df['Std Dev'] = display_df['Std Dev'].round(4)
    if 'Elevation (m)' in display_df.columns:
        display_df['Elevation (m)'] = display_df['Elevation (m)'].round(1)
    
    # Add year and month columns for easier filtering
    display_df['Year'] = pd.to_datetime(display_df['Date']).dt.year
    display_df['Month'] = pd.to_datetime(display_df['Date']).dt.strftime('%b')  # Abbreviated month names
    
    # Reorder columns
    col_order = ['Date', 'Year', 'Month', 'Mean Albedo']
    if 'Std Dev' in display_df.columns:
        col_order.append('Std Dev')
    if 'Elevation (m)' in display_df.columns:
        col_order.append('Elevation (m)')
    col_order.append('Observations')
    display_df = display_df[col_order]
    
    # Table options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        show_full_data = st.checkbox("Show all rows", value=False, help="Display all data (may be slow for large datasets)")
    with col2:
        enable_download = st.checkbox("Enable CSV download", value=True)
    with col3:
        search_term = st.text_input("🔍 Search table:", placeholder="Type to search...")
    
    # Apply search filter
    if search_term:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = display_df[mask]
        st.info(f"Found {len(filtered_df)} matching rows")
    else:
        filtered_df = display_df
    
    # Display the interactive table
    if show_full_data:
        # Show all data with advanced features
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=600,
            column_config=_get_column_config(filtered_df),
            hide_index=True,
        )
    else:
        # Show paginated data
        rows_per_page = 50
        total_pages = len(filtered_df) // rows_per_page + (1 if len(filtered_df) % rows_per_page > 0 else 0)
        
        page = st.number_input(
            f"Page (1-{total_pages})", 
            min_value=1, 
            max_value=max(1, total_pages), 
            value=1
        )
        
        start_idx = (page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        
        st.dataframe(
            filtered_df.iloc[start_idx:end_idx],
            use_container_width=True,
            height=400,
            column_config=_get_column_config(filtered_df),
            hide_index=True,
        )
        
        st.caption(f"Showing rows {start_idx + 1} to {min(end_idx, len(filtered_df))} of {len(filtered_df)} total rows")
    
    # Download button
    if enable_download:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download filtered data as CSV",
            data=csv,
            file_name=f"athabasca_albedo_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def _get_column_config(filtered_df):
    """Get column configuration for streamlit dataframe display"""
    config = {
        "Date": st.column_config.DateColumn(
            "Date",
            help="Observation date",
            format="YYYY-MM-DD",
            width=90,
        ),
        "Year": st.column_config.NumberColumn(
            "Year",
            help="Year",
            width=50,
        ),
        "Month": st.column_config.TextColumn(
            "Month",
            help="Month name",
            width=60,
        ),
        "Mean Albedo": st.column_config.NumberColumn(
            "Mean Albedo",
            help="Average albedo value",
            format="%.3f",
            min_value=0,
            max_value=1,
            width=70,
        ),
        "Observations": st.column_config.NumberColumn(
            "Observations",
            help="Number of observations for this date",
            width=70,
        ),
    }
    
    # Add optional columns if they exist
    if 'Std Dev' in filtered_df.columns:
        config["Std Dev"] = st.column_config.NumberColumn(
            "Std Dev",
            help="Standard deviation",
            format="%.3f",
            width=60,
        )
    
    if 'Elevation (m)' in filtered_df.columns:
        config["Elevation (m)"] = st.column_config.NumberColumn(
            "Elevation (m)",
            help="Elevation in meters",
            format="%.0f",
            width=60,
        )
    
    return config