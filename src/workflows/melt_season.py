"""
Melt Season Analysis Workflow
Complete workflow for analyzing glacier albedo trends during melt season
Following Williamson & Menounos (2021) methodology
"""

import pandas as pd
import numpy as np
import ee
from datetime import datetime
from config import athabasca_roi
from paths import get_output_path

# Import analysis modules
from analysis.temporal import analyze_melt_season_trends, analyze_annual_trends, analyze_monthly_trends
from visualization.plots import create_melt_season_plot
from data.extraction import extract_melt_season_data_yearly

def run_melt_season_analysis_williamson(start_year=2010, end_year=2024, scale=500, use_advanced_qa=False, qa_level='standard'):
    """
    Complete melt season analysis workflow following Williamson & Menounos (2021)
    Focus on June-September period for glacier albedo trends
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
        scale: Spatial resolution in meters
        use_advanced_qa: Whether to use advanced Algorithm QA flags filtering
        qa_level: Quality level ('strict', 'standard', 'relaxed')
    
    Returns:
        dict: Complete analysis results
    """
    print("🏔️  ATHABASCA GLACIER MELT SEASON ALBEDO ANALYSIS")
    print("=" * 80)
    print(f"📊 Using Williamson & Menounos (2021) methodology")
    print(f"🗓️  Period: {start_year}-{end_year}")
    print(f"📏 Resolution: {scale}m")
    print(f"🎯 Focus: June-September (melt season)")
    if use_advanced_qa:
        print(f"⚙️  Advanced QA: {qa_level} filtering with Algorithm flags")
    else:
        print(f"⚙️  Standard QA: Basic filtering only")
    
    # Initialize Earth Engine
    ee.Initialize()
    
    # Extract melt season data with optional advanced QA
    print(f"\n⏳ Extracting MODIS albedo data year by year...")
    print(f"🔄 This ensures manageable memory usage for long time series")
    
    df = extract_melt_season_data_yearly(
        start_year=start_year, 
        end_year=end_year, 
        scale=scale,
        use_advanced_qa=use_advanced_qa,
        qa_level=qa_level
    )
    
    if df.empty:
        print("❌ No data extracted. Check your date range and region.")
        return None
    
    # Export raw data
    csv_path = get_output_path('athabasca_melt_season_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Raw data exported: {csv_path}")
    
    # Perform comprehensive analysis
    print(f"\n🔍 Performing comprehensive trend analysis...")
    results = analyze_melt_season_trends(df)
    
    if not results or not results.get('annual_trends'):
        print("❌ Trend analysis failed.")
        return None
    
    # Create visualization
    from paths import get_figure_path
    figure_path = get_figure_path('athabasca_melt_season_analysis.png', 'melt_season')
    create_melt_season_plot(
        results['annual_trends'], 
        results['monthly_trends'], 
        df, 
        str(figure_path)
    )
    
    # Export results summary
    summary_path = get_output_path('athabasca_melt_season_results.csv')
    
    # Create summary dataframe
    summary_data = []
    
    # Annual trend
    if results['annual_trends']:
        annual = results['annual_trends']
        summary_data.append({
            'analysis_type': 'Annual Melt Season',
            'period': annual['period'],
            'trend': annual['mann_kendall']['trend'],
            'p_value': annual['mann_kendall']['p_value'],
            'sens_slope_per_year': annual['change_per_year'],
            'percent_change_per_year': annual['change_percent_per_year'],
            'total_change': annual['total_change'],
            'significance': annual['significance']
        })
    
    # Monthly trends
    for month, monthly in results['monthly_trends'].items():
        summary_data.append({
            'analysis_type': f'{monthly["month_name"]} Only',
            'period': monthly['period'],
            'trend': monthly['mann_kendall']['trend'],
            'p_value': monthly['mann_kendall']['p_value'],
            'sens_slope_per_year': monthly['change_per_year'],
            'percent_change_per_year': monthly['change_percent_per_year'],
            'total_change': monthly['total_change'],
            'significance': monthly['significance']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_path, index=False)
    print(f"💾 Results summary exported: {summary_path}")
    
    # Print key findings
    print_key_findings(results)
    
    print(f"\n🎉 MELT SEASON ANALYSIS COMPLETE!")
    print(f"Files generated:")
    print(f"   📊 Visualization: {figure_path}")
    print(f"   💾 Raw data: {csv_path}")
    print(f"   💾 Results summary: {summary_path}")
    
    # Prepare comprehensive results for report
    comprehensive_results = {
        'melt_season_data': df,
        'overall_statistics': results.get('annual_trends'),
        'monthly_statistics': results.get('monthly_trends'),
        'fire_impact': results.get('fire_impact'),
        'dataset_info': {
            'total_observations': len(df),
            'years_analyzed': sorted(df['year'].unique()) if 'year' in df.columns else [],
            'period': f"{start_year}-{end_year}",
            'product': "MODIS MOD10A1/MYD10A1 Snow Albedo",
            'method': "Williamson & Menounos (2021) Melt Season Analysis",
            'quality_filtering': "QA ≤ 1 (Best + good quality)"
        }
    }
    
    # Generate automatic report
    try:
        from src.utils.report_generator import generate_analysis_report
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"outputs/athabasca_melt_season_rapport_{timestamp}.txt"
        
        generate_analysis_report(
            analysis_type='Melt_Season',
            results_data=comprehensive_results,
            output_path=report_path,
            start_year=start_year,
            end_year=end_year,
            fire_years=results.get('fire_impact', {}).get('fire_years', []),
            fire_significance=results.get('fire_impact', {}).get('p_value', 1.0)
        )
        
    except Exception as e:
        print(f"⚠️  Erreur génération rapport automatique: {e}")
    
    return comprehensive_results

def print_key_findings(results):
    """Print key findings from the analysis"""
    print(f"\n🎯 KEY FINDINGS:")
    print("=" * 50)
    
    # Overall trend
    if results['annual_trends']:
        annual = results['annual_trends']
        print(f"\n📈 OVERALL MELT SEASON TREND:")
        print(f"   Period: {annual['period']}")
        print(f"   Trend: {annual['mann_kendall']['trend'].replace('_', ' ').title()}")
        print(f"   Change: {annual['change_percent_per_year']:.2f}%/year")
        print(f"   Total change: {annual['total_percent_change']:.1f}%")
        print(f"   Significance: {annual['significance'].upper()}")
    
    # Most significant monthly trend
    if results['monthly_trends']:
        significant_months = [
            (month, data) for month, data in results['monthly_trends'].items()
            if data['mann_kendall']['p_value'] < 0.05
        ]
        
        if significant_months:
            print(f"\n📅 SIGNIFICANT MONTHLY TRENDS:")
            for month, data in significant_months:
                print(f"   {data['month_name']}: {data['change_percent_per_year']:.2f}%/year (p={data['mann_kendall']['p_value']:.3f})")
    
    # Fire impact
    if results['fire_impact'] and results['fire_impact']['significant']:
        fire = results['fire_impact']
        print(f"\n🔥 FIRE IMPACT:")
        print(f"   Fire years albedo: {fire['fire_mean']:.3f}")
        print(f"   Non-fire years albedo: {fire['non_fire_mean']:.3f}")
        print(f"   Difference: {fire['percent_difference']:.1f}%")
        print(f"   Statistical significance: YES (p={fire['p_value']:.3f})") 