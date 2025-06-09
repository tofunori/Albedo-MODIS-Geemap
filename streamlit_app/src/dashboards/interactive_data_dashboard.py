"""
Interactive Data Table Dashboard
Provides Excel-style data exploration and analysis capabilities
"""

import streamlit as st
import pandas as pd


def create_interactive_data_table_dashboard(df_data):
    """
    Create flexible interactive data table with all column visibility
    """
    if df_data.empty:
        st.warning("No data available for the table")
        return
    
    # Prepare data for the table
    table_data = df_data.copy()
    available_columns = table_data.columns.tolist()
    
    # Data overview
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", f"{len(table_data):,}")
    with col2:
        st.metric("Total Columns", len(available_columns))
    with col3:
        if 'date' in table_data.columns:
            date_range = f"{table_data['date'].min()} to {table_data['date'].max()}"
            st.metric("Date Range", date_range)
    
    # Column selection interface
    with st.expander("🔧 Column Selection & Options", expanded=False):
        col_sel1, col_sel2 = st.columns(2)
        
        with col_sel1:
            # Essential columns (always recommended)
            essential_cols = []
            for col in ['date', 'date_str', 'albedo_mean', 'albedo_min', 'albedo_max', 'albedo_std']:
                if col in available_columns:
                    essential_cols.append(col)
            
            selected_essential = st.multiselect(
                "📋 Essential Columns:",
                essential_cols,
                default=essential_cols,
                help="Core columns for analysis"
            )
        
        with col_sel2:
            # Additional columns
            additional_cols = [col for col in available_columns if col not in essential_cols]
            selected_additional = st.multiselect(
                "🔍 Additional Columns:",
                additional_cols,
                default=[],
                help="Select additional columns to display"
            )
        
        # Combine selected columns
        all_selected_cols = selected_essential + selected_additional
        
        if not all_selected_cols:
            st.warning("Please select at least one column to display")
            return
    
    # Create display dataframe with selected columns
    display_df = table_data[all_selected_cols].copy()
    
    # Round numeric columns automatically
    numeric_columns = display_df.select_dtypes(include=['float64', 'float32']).columns
    for col in numeric_columns:
        if 'albedo' in col.lower():
            display_df[col] = display_df[col].round(6)
        elif 'elevation' in col.lower():
            display_df[col] = display_df[col].round(1)
        else:
            display_df[col] = display_df[col].round(3)
    
    # Filtering and search options
    with st.expander("🔍 Filters & Search", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Date filtering
            if 'date' in display_df.columns:
                date_col = pd.to_datetime(display_df['date'])
                min_date = date_col.min().date()
                max_date = date_col.max().date()
                
                date_range = st.date_input(
                    "Date Range:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
        
        with filter_col2:
            # Year filtering
            if 'date' in display_df.columns:
                years = sorted(pd.to_datetime(display_df['date']).dt.year.unique())
                selected_years = st.multiselect(
                    "Years:",
                    years,
                    default=years,
                    help="Select specific years"
                )
        
        with filter_col3:
            # Search
            search_term = st.text_input(
                "Search:",
                placeholder="Search all columns...",
                help="Search across all visible columns"
            )
    
    # Apply filters
    filtered_df = display_df.copy()
    
    # Date range filter
    if 'date' in filtered_df.columns and len(date_range) == 2:
        date_mask = (pd.to_datetime(filtered_df['date']).dt.date >= date_range[0]) & \
                   (pd.to_datetime(filtered_df['date']).dt.date <= date_range[1])
        filtered_df = filtered_df[date_mask]
    
    # Year filter
    if 'date' in filtered_df.columns and selected_years:
        year_mask = pd.to_datetime(filtered_df['date']).dt.year.isin(selected_years)
        filtered_df = filtered_df[year_mask]
    
    # Search filter
    if search_term:
        search_mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[search_mask]
    
    # Display controls
    display_col1, display_col2, display_col3 = st.columns(3)
    with display_col1:
        rows_per_page = st.selectbox(
            "Rows per page:",
            [25, 50, 100, 200, "All"],
            index=1
        )
    with display_col2:
        st.metric("Filtered Rows", f"{len(filtered_df):,}")
    with display_col3:
        sort_column = st.selectbox(
            "Sort by:",
            [""] + list(filtered_df.columns),
            help="Choose column to sort by"
        )
    
    # Apply sorting
    if sort_column:
        try:
            if filtered_df[sort_column].dtype in ['object', 'string']:
                filtered_df = filtered_df.sort_values(sort_column)
            else:
                filtered_df = filtered_df.sort_values(sort_column, ascending=False)
        except:
            pass
    
    # Display the table
    if rows_per_page == "All":
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=600,
            hide_index=True,
        )
    else:
        # Paginated display
        total_pages = len(filtered_df) // rows_per_page + (1 if len(filtered_df) % rows_per_page > 0 else 0)
        
        if total_pages > 1:
            page = st.number_input(
                f"Page (1-{total_pages})",
                min_value=1,
                max_value=max(1, total_pages),
                value=1
            )
            
            start_idx = (page - 1) * rows_per_page
            end_idx = start_idx + rows_per_page
            page_df = filtered_df.iloc[start_idx:end_idx]
            
            st.caption(f"Showing rows {start_idx + 1}-{min(end_idx, len(filtered_df))} of {len(filtered_df)}")
        else:
            page_df = filtered_df
        
        st.dataframe(
            page_df,
            use_container_width=True,
            height=400,
            hide_index=True,
        )
    
    # Download and export options
    with st.expander("📥 Download & Export", expanded=False):
        col_down1, col_down2 = st.columns(2)
        
        with col_down1:
            # CSV download
            csv_data = filtered_df.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_data,
                file_name=f"athabasca_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        
        with col_down2:
            # Show data summary
            if st.button("📊 Show Data Summary"):
                st.markdown("### Data Summary")
                st.write(filtered_df.describe())
                
                # Show column info
                st.markdown("### Column Information")
                col_info = pd.DataFrame({
                    'Column': filtered_df.columns,
                    'Type': filtered_df.dtypes,
                    'Non-null Count': filtered_df.count(),
                    'Null Count': filtered_df.isnull().sum()
                })
                st.dataframe(col_info, use_container_width=True)

