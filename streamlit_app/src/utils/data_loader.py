"""
Data Loading Utilities for Streamlit Dashboard
Handles CSV data loading from URLs with fallback to local files
"""

import streamlit as st
import pandas as pd
import requests
from io import StringIO


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
def load_data_from_url(url, fallback_path=None, show_status=True):
    """
    Load CSV data from URL with local fallback
    
    Args:
        url: URL to load data from
        fallback_path: Local file path to use if URL fails
        show_status: Whether to show status messages (default True)
        
    Returns:
        tuple: (DataFrame, source_type)
    """
    try:
        # Try to load from URL first
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse CSV from response
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        if show_status:
            with st.sidebar:
                st.success(f"✅ Data loaded from online source: {len(df)} records")
        return df, "online"
        
    except Exception as e:
        if show_status:
            with st.sidebar:
                st.warning(f"⚠️ Could not load from URL: {str(e)}")
        
        # Fallback to local file if available
        if fallback_path:
            try:
                df = pd.read_csv(fallback_path)
                if show_status:
                    with st.sidebar:
                        st.info(f"📁 Using local fallback data: {len(df)} records")
                return df, "local"
            except Exception as local_e:
                if show_status:
                    with st.sidebar:
                        st.error(f"❌ Local fallback also failed: {str(local_e)}")
                return pd.DataFrame(), "failed"
        
        return pd.DataFrame(), "failed"


def load_dataset(dataset_name):
    """
    Load a specific dataset by name
    
    Args:
        dataset_name: Name of dataset from DATA_SOURCES
        
    Returns:
        tuple: (DataFrame, source_type)
    """
    if dataset_name not in DATA_SOURCES:
        st.error(f"Unknown dataset: {dataset_name}")
        return pd.DataFrame(), "failed"
    
    config = DATA_SOURCES[dataset_name]
    return load_data_from_url(config['url'], config['local_fallback'])


def load_all_melt_season_data():
    """
    Load all melt season related datasets
    
    Returns:
        dict: Dictionary with all melt season data
    """
    data = {}
    
    # Load main time series data
    df_data, _ = load_dataset('melt_season')
    data['time_series'] = df_data
    
    # Load statistical results
    df_results, _ = load_dataset('melt_season_results')
    data['results'] = df_results
    
    # Load focused analysis data
    df_focused, _ = load_dataset('melt_season_focused')
    data['focused'] = df_focused
    
    return data


def load_hypsometric_data(show_status=True):
    """
    Load hypsometric analysis data (both results and raw data)
    
    Args:
        show_status: Whether to show data loading status messages
    
    Returns:
        dict: Dictionary with hypsometric data
    """
    data = {}
    
    # Load results
    df_results, _ = load_dataset('hypsometric') if show_status else load_data_from_url(
        DATA_SOURCES['hypsometric']['url'], 
        DATA_SOURCES['hypsometric']['local_fallback'], 
        show_status=False
    )
    data['results'] = df_results
    
    # Load raw hypsometric data (local only for now)
    try:
        df_data, _ = load_data_from_url(
            '../outputs/csv/athabasca_hypsometric_data.csv',
            '../outputs/csv/athabasca_hypsometric_data.csv',
            show_status=show_status
        )
        data['time_series'] = df_data
    except:
        data['time_series'] = pd.DataFrame()
    
    return data


def get_data_source_info():
    """
    Get information about all available data sources
    
    Returns:
        dict: Data source configuration
    """
    return DATA_SOURCES