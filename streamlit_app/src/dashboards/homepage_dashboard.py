"""
Homepage Dashboard for Athabasca Glacier Albedo Analysis Project
Provides project overview, methodology, and navigation guide
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def create_homepage_dashboard():
    """
    Create comprehensive homepage dashboard with project overview
    """
    # Header with project title and description
    st.title("🏔️ Athabasca Glacier Albedo Analysis")
    st.markdown("### *MODIS Satellite Data Analysis for Glaciological Research*")
    
    # Project overview section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 📖 Project Overview
        
        This dashboard provides comprehensive analysis tools for studying albedo changes on the **Athabasca Glacier** 
        using **MODIS satellite data** from Google Earth Engine. The project implements advanced methodologies 
        for glaciological research and climate change studies.
        
        ### 🎯 Research Objectives
        
        - **Monitor albedo temporal evolution** on Athabasca Glacier (2010-2024)
        - **Implement Williamson & Menounos (2021) methodology** for hypsometric analysis
        - **Compare MODIS products** (MOD10A1/MYD10A1 vs MCD43A3) for glacier studies
        - **Analyze spectral albedo patterns** across different elevation bands
        - **Provide interactive tools** for real-time data exploration
        """)
        
    with col2:
        st.markdown("""
        ### 📍 Study Area
        
        **Athabasca Glacier**  
        📍 **Location**: 52.2°N, 117.2°W  
        🏔️ **Elevation**: 1,900 - 3,500m  
        🗺️ **Region**: Columbia Icefield, Alberta  
        📏 **Area**: ~6 km² (2023 mask)  
        
        ### 📡 Data Sources
        
        **MODIS Products:**
        - **MOD10A1/MYD10A1**: Daily Snow Albedo
        - **MCD43A3**: 16-day Broadband Albedo
        
        **Resolution:** 500m × 500m  
        **Period:** 2010-2024  
        **Platform:** Google Earth Engine
        """)
    
    st.markdown("---")
    
    # Methodology section
    st.markdown("## 🔬 Scientific Methodology")
    
    method_col1, method_col2, method_col3 = st.columns(3)
    
    with method_col1:
        st.markdown("""
        ### 📊 **Data Processing**
        
        - **Terra-Aqua Fusion**: Literature-based combination
        - **Quality Filtering**: Advanced QA flags implementation
        - **Temporal Compositing**: Melt season focus (Jun-Sep)
        - **Spatial Masking**: Accurate glacier boundary (2023)
        """)
        
    with method_col2:
        st.markdown("""
        ### 📈 **Analysis Methods**
        
        - **Hypsometric Analysis**: Elevation-based albedo patterns
        - **Trend Detection**: Mann-Kendall & Sen's slope tests
        - **Spectral Analysis**: Multi-band albedo comparison
        - **Statistical Validation**: Robust uncertainty estimation
        """)
        
    with method_col3:
        st.markdown("""
        ### 🛰️ **Remote Sensing**
        
        - **BRDF Modeling**: BSA/WSA albedo calculations
        - **Atmospheric Correction**: Diffuse fraction adjustment
        - **Cloud Masking**: Advanced algorithm flags filtering
        - **Gap Filling**: Terra-Aqua temporal fusion
        """)
    
    st.markdown("---")
    
    # Navigation guide
    st.markdown("## 🧭 Dashboard Navigation Guide")
    
    nav_data = [
        {
            "📋": "Data Processing & Configuration",
            "Description": "Configure data processing parameters, import CSV files, and manage analysis settings",
            "Use Case": "Initial setup, data import, parameter optimization"
        },
        {
            "🌈": "MCD43A3 Broadband Albedo", 
            "Description": "Analyze 16-day broadband albedo data with spectral band comparison and Blue-Sky calculations",
            "Use Case": "BRDF analysis, spectral studies, atmospheric conditions"
        },
        {
            "❄️": "MOD10A1/MYD10A1 Daily Snow Albedo",
            "Description": "Process daily snow albedo with Terra-Aqua fusion following Williamson & Menounos methodology", 
            "Use Case": "Daily monitoring, melt season analysis, temporal trends"
        },
        {
            "📏": "Hypsometric Analysis",
            "Description": "Elevation-based albedo analysis with statistical trend detection and uncertainty quantification",
            "Use Case": "Climate change studies, elevation gradients, trend analysis"
        },
        {
            "🗺️": "Interactive Albedo Map",
            "Description": "Real-time MODIS pixel visualization on satellite imagery with adjustable parameters",
            "Use Case": "Spatial analysis, pixel-level inspection, data exploration"
        },
        {
            "⚡": "Real-time QA Comparison",
            "Description": "Compare different quality filtering approaches with live Earth Engine processing",
            "Use Case": "Quality assessment, filtering optimization, method validation"
        }
    ]
    
    # Create navigation table
    df_nav = pd.DataFrame(nav_data)
    
    # Display with custom styling
    for i, row in df_nav.iterrows():
        icon = list(row.keys())[0]
        title = row[icon]
        description = row["Description"]
        use_case = row["Use Case"]
        
        with st.expander(f"{icon} **{title}**"):
            st.markdown(f"**Description:** {description}")
            st.markdown(f"**Typical Use Cases:** {use_case}")
    
    st.markdown("---")
    
    # Technical specifications
    tech_col1, tech_col2 = st.columns(2)
    
    with tech_col1:
        st.markdown("""
        ## ⚙️ Technical Specifications
        
        ### **Software Stack**
        - **Frontend**: Streamlit (Python web framework)
        - **Backend**: Google Earth Engine API
        - **Data Processing**: Pandas, NumPy, SciPy
        - **Visualization**: Plotly, Folium, Matplotlib
        - **Statistical Analysis**: PyMannKendall, SciPy.stats
        
        ### **Data Architecture**
        - **Real-time Processing**: Google Earth Engine
        - **Local Storage**: CSV exports for reproducibility  
        - **Visualization**: Interactive maps and plots
        - **Export**: Results, figures, and comprehensive reports
        """)
        
    with tech_col2:
        st.markdown("""
        ## 📚 Academic References
        
        ### **Primary Methodology**
        - **Williamson & Menounos (2021)**: Hypsometric analysis framework
        - **Schaaf et al. (2002)**: MODIS BRDF/Albedo algorithm
        - **Lucht et al. (2000)**: RossThick-LiSparse-R model
        
        ### **Validation Studies**
        - **Stroeve et al. (2005)**: Greenland MODIS validation
        - **Wang et al. (2012)**: Snow albedo product evaluation
        - **Muhammad & Thapa (2021)**: High Mountain Asia studies
        
        ### **Quality Assessment**
        - **NASA MODIS Documentation**: QA flags implementation
        - **Terra-Aqua Fusion**: Literature-based methods
        - **Glaciological Applications**: Best practices
        """)
    
    st.markdown("---")
    
    # Getting started section
    st.markdown("## 🚀 Getting Started")
    
    start_col1, start_col2, start_col3 = st.columns(3)
    
    with start_col1:
        st.markdown("""
        ### 1️⃣ **For New Users**
        
        1. Start with **"Interactive Albedo Map"**
        2. Select a recent date (2024)
        3. Explore MODIS pixels on glacier
        4. Adjust quality parameters
        5. Understand data patterns
        """)
        
    with start_col2:
        st.markdown("""
        ### 2️⃣ **For Researchers**
        
        1. Check **"Data Processing"** for settings
        2. Run **"Hypsometric Analysis"** for trends
        3. Compare **"MCD43A3"** vs **"MOD10A1"**
        4. Use **"QA Comparison"** for validation
        5. Export results for publications
        """)
        
    with start_col3:
        st.markdown("""
        ### 3️⃣ **For Analysis**
        
        1. Load your CSV data if available
        2. Configure quality parameters
        3. Run comprehensive analysis
        4. Generate publication-ready figures
        5. Export detailed reports
        """)
    
    # Status and information footer
    st.markdown("---")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.markdown("""
        ### 📊 **Project Status**
        
        **Status**: ✅ Production Ready  
        **Version**: 2.0 (January 2025)  
        **Data Coverage**: 2010-2024  
        **Last Update**: Real-time via GEE
        """)
        
    with status_col2:
        st.markdown("""
        ### 🏛️ **Institution**
        
        **University**: UQTR (Université du Québec à Trois-Rivières)  
        **Program**: Maîtrise en Sciences  
        **Domain**: Glaciology & Remote Sensing  
        **Location**: Québec, Canada
        """)
        
    with status_col3:
        st.markdown("""
        ### 🔗 **Resources**
        
        **Earth Engine**: [code.earthengine.google.com](https://code.earthengine.google.com)  
        **MODIS Data**: [lpdaac.usgs.gov](https://lpdaac.usgs.gov)  
        **Documentation**: Available in `/docs` folder  
        **Support**: See README.md for guidance
        """)
    
    # Final call to action
    st.markdown("---")
    st.markdown("""
    ## 🎯 Ready to Start?
    
    **👈 Select an analysis type from the sidebar to begin exploring Athabasca Glacier albedo data!**
    
    *For immediate results, try the **"Interactive Albedo Map"** to see real-time MODIS pixels on satellite imagery.*
    """)