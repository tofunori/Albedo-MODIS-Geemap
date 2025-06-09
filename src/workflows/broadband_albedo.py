"""
MCD43A3 Broadband Albedo Analysis Workflow
Following Williamson & Menounos (2021) methodology

Refactored main workflow that orchestrates:
- Data extraction via mcd43a3_extraction module
- Spectral analysis via spectral_analysis module  
- Visualization via spectral_plots module

This provides a streamlined interface to the complete MCD43A3 analysis pipeline.
"""

import pandas as pd
from datetime import datetime

# Import modular components
from src.data.mcd43a3_extraction import (
    initialize_earth_engine,
    extract_mcd43a3_data_fixed,
    extract_mcd43a3_data_yearly,
    analyze_data_quality
)
from src.analysis.spectral_analysis import (
    analyze_spectral_trends,
    calculate_spectral_ratios,
    detect_contamination_events,
    analyze_seasonal_patterns
)
from src.visualization.spectral_plots import (
    create_spectral_plot_fixed,
    create_spectral_ratio_plot,
    create_seasonal_spectral_plot,
    create_multi_year_seasonal_evolution,
    create_interactive_seasonal_evolution
)


def run_mcd43a3_analysis(start_year=2010, end_year=2024):
    """
    Complete MCD43A3 broadband albedo analysis workflow
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
    
    Returns:
        dict: Complete MCD43A3 analysis results
    """
    print("🌈 ATHABASCA GLACIER MCD43A3 BROADBAND ALBEDO ANALYSIS")
    print("=" * 80)
    print("📡 Product: MODIS MCD43A3 16-day broadband albedo composites")
    print("📚 Method: Following Williamson & Menounos (2021) spectral methodology")
    print("🎯 Focus: Spectral albedo analysis for contamination detection")
    
    # Initialize Earth Engine
    initialize_earth_engine()
    
    # Extract MCD43A3 data
    df = extract_mcd43a3_data_fixed(start_year=start_year, end_year=end_year)
    
    if df.empty:
        print("❌ No MCD43A3 data extracted. Analysis cannot proceed.")
        return None
    
    # Export raw data
    from src.paths import get_output_path
    
    csv_path = get_output_path('MCD43A3_spectral_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Raw MCD43A3 data exported: {csv_path}")
    
    # Analyze data quality
    quality_results = analyze_data_quality(df)
    
    # Perform spectral trend analysis
    spectral_results = analyze_spectral_trends(df)
    
    if not spectral_results:
        print("❌ Spectral trend analysis failed.")
        return None
    
    # Create visualizations
    create_spectral_plot_fixed(df, spectral_results)
    
    # Create multi-year seasonal evolution plot
    print("\n📊 Creating multi-year seasonal evolution plot...")
    create_multi_year_seasonal_evolution(df)
    
    # Create interactive seasonal evolution dashboard
    print("\n🌐 Creating interactive seasonal evolution dashboard...")
    create_interactive_seasonal_evolution(df)
    
    # Export results summary
    results_path = get_output_path('MCD43A3_results.csv')
    
    # Create summary DataFrame for export
    summary_data = []
    for group_name, group_results in spectral_results.items():
        if group_name == 'spectral_comparison':
            continue
            
        for band, band_results in group_results.items():
            if 'change_percent_per_year' in band_results:
                summary_data.append({
                    'spectral_group': group_name,
                    'band': band,
                    'change_percent_per_year': band_results['change_percent_per_year'],
                    'mann_kendall_p_value': band_results['mann_kendall']['p_value'],
                    'trend_direction': band_results['mann_kendall']['trend'],
                    'significance': band_results['significance'],
                    'n_years': band_results['n_years']
                })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(results_path, index=False)
        print(f"💾 MCD43A3 results exported: {results_path}")
    
    # Final summary
    print(f"\n🎉 MCD43A3 SPECTRAL ANALYSIS COMPLETE!")
    print("=" * 60)
    print(f"📊 Period analyzed: {start_year}-{end_year}")
    print(f"📈 Total observations: {len(df)}")
    
    if 'spectral_comparison' in spectral_results:
        comp = spectral_results['spectral_comparison']
        print(f"🔍 Key finding: {comp['interpretation'].replace('_', ' ').title()} decline pattern")
        print(f"📊 Visible change: {comp['visible_avg_change']:.2f}%/year")
        print(f"📊 NIR change: {comp['nir_avg_change']:.2f}%/year")
    
    print(f"💾 Files generated:")
    print(f"   📊 Spectral analysis: figures/melt_season/athabasca_mcd43a3_spectral_analysis.png")
    print(f"   📊 Seasonal evolution: figures/melt_season/mcd43a3_seasonal_evolution_grid.png")
    print(f"   🌐 Interactive dashboard: maps/interactive/interactive_seasonal_evolution.html")
    print(f"   💾 Raw data: outputs/csv/MCD43A3_spectral_data.csv")
    print(f"   💾 Results: outputs/csv/MCD43A3_results.csv")
    
    # Compile comprehensive results
    comprehensive_results = {
        'spectral_data': df,
        'statistics': spectral_results,
        'quality_analysis': quality_results,
        'dataset_info': {
            'total_observations': len(df),
            'years_analyzed': sorted(df['year'].unique()),
            'period': f"{start_year}-{end_year}",
            'product': "MODIS MCD43A3 16-day broadband albedo",
            'method': "Williamson & Menounos (2021) Spectral Analysis",
            'quality_filtering': "QA ≤ 1 (Full + magnitude inversions)"
        }
    }
    
    # Generate automatic report
    try:
        from src.utils.report_generator import generate_analysis_report
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"outputs/athabasca_mcd43a3_rapport_{timestamp}.txt"
        
        generate_analysis_report(
            analysis_type='MCD43A3',
            results_data=comprehensive_results,
            output_path=report_path,
            start_year=start_year,
            end_year=end_year
        )
        
    except Exception as e:
        print(f"⚠️  Erreur génération rapport automatique: {e}")
    
    return comprehensive_results


def run_extended_spectral_analysis(start_year=2010, end_year=2024):
    """
    Extended spectral analysis with additional visualizations
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
    
    Returns:
        dict: Extended analysis results
    """
    print("🌈 EXTENDED MCD43A3 SPECTRAL ANALYSIS")
    print("=" * 60)
    
    # Run main analysis first
    results = run_mcd43a3_analysis(start_year, end_year)
    
    if results is None:
        return None
    
    df = results['spectral_data']
    
    # Additional analyses
    print("\n🔍 Running extended spectral analysis...")
    
    # Multi-year seasonal evolution plot
    print("\n📊 Creating multi-year seasonal evolution plot...")
    create_multi_year_seasonal_evolution(df)
    
    # Spectral ratio analysis
    contamination_events = detect_contamination_events(df)
    if not contamination_events.empty:
        print(f"⚠️  Detected {len(contamination_events)} potential contamination events")
        create_spectral_ratio_plot(df)
    
    # Seasonal pattern analysis
    seasonal_results = analyze_seasonal_patterns(df)
    if seasonal_results:
        print(f"📊 Seasonal analysis complete: {seasonal_results['total_observations']} observations")
        create_seasonal_spectral_plot(df)
    
    # Update results with extended analysis
    results['contamination_events'] = contamination_events
    results['seasonal_analysis'] = seasonal_results
    
    print("\n🎉 EXTENDED SPECTRAL ANALYSIS COMPLETE!")
    
    return results