"""
Melt Season Analysis Workflow
Complete workflow for analyzing glacier albedo trends during melt season
Following Williamson & Menounos (2021) methodology
"""

import pandas as pd
import numpy as np
import os
import ee
from datetime import datetime
from config import athabasca_roi
from paths import get_output_path

# Import analysis modules
from data.extraction import extract_melt_season_data_yearly

# Try different import paths for utils.file_utils
try:
    from utils.file_utils import safe_csv_write, get_safe_output_path
except ImportError:
    try:
        from src.utils.file_utils import safe_csv_write, get_safe_output_path
    except ImportError:
        # Fallback: define safe functions inline
        import time
        import tempfile
        
        def safe_csv_write(df, file_path, index=False, max_retries=3, retry_delay=0.5):
            """Fallback safe CSV write function"""
            import pandas as pd
            
            # Store reference to original to_csv to avoid any recursion issues
            original_to_csv = pd.DataFrame.to_csv
            
            try:
                file_path = os.path.normpath(file_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                for attempt in range(max_retries):
                    backup_file = None  # Initialize backup_file
                    try:
                        temp_file = file_path + '.tmp'
                        print(f"🔍 Fallback: Writing to {temp_file}")
                        
                        # Call original pandas method directly to avoid recursion
                        original_to_csv(df, temp_file, index=index)
                        print(f"🔍 Fallback: Write successful")
                        
                        if os.path.exists(file_path):
                            backup_file = file_path + '.bak'
                            if os.path.exists(backup_file):
                                os.remove(backup_file)
                            os.rename(file_path, backup_file)
                        
                        os.rename(temp_file, file_path)
                        
                        # Clean up backup file if it exists
                        if backup_file and os.path.exists(backup_file):
                            os.remove(backup_file)
                        
                        print(f"🔍 Fallback: CSV write completed successfully")
                        return True
                    except (PermissionError, OSError) as e:
                        print(f"🔍 Fallback: Attempt {attempt + 1} failed: {e}")
                        # Clean up temp file if it exists
                        temp_file = file_path + '.tmp'
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except:
                                pass
                        
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise e
                return False
            except Exception as e:
                print(f"❌ Fallback CSV write error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def get_safe_output_path(filename):
            """Fallback safe path function"""
            # Find project root
            current_dir = os.path.abspath(os.path.dirname(__file__))
            project_root = current_dir
            
            for _ in range(10):
                if os.path.exists(os.path.join(project_root, 'outputs', 'csv')):
                    break
                project_root = os.path.dirname(project_root)
            
            csv_dir = os.path.join(project_root, 'outputs', 'csv')
            os.makedirs(csv_dir, exist_ok=True)
            return os.path.normpath(os.path.join(csv_dir, filename))

def run_melt_season_analysis_williamson(start_year=2010, end_year=2024, scale=500, use_advanced_qa=False, qa_level='standard', progress_callback=None):
    """
    Complete melt season analysis workflow following Williamson & Menounos (2021)
    Focus on June-September period for glacier albedo trends
    
    Args:
        start_year: Start year for analysis
        end_year: End year for analysis
        scale: Spatial resolution in meters
        use_advanced_qa: Whether to use advanced Algorithm QA flags filtering
        qa_level: Quality level ('strict', 'standard', 'relaxed')
        progress_callback: Function to call with progress updates (progress, message)
    
    Returns:
        dict: Complete analysis results
    """
    def update_progress(progress, message):
        """Helper function to update progress"""
        print(f"📊 Progress {progress}%: {message}")
        if progress_callback:
            try:
                progress_callback(progress, message)
            except Exception as e:
                print(f"Warning: Progress callback failed: {e}")
    
    update_progress(0, "Initializing analysis...")
    
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
    
    update_progress(5, "Setting up safe file operations...")
    
    # Note: Removed dangerous monkey patching that caused infinite recursion
    print("🔧 Using direct safe CSV writing (no monkey patching)")
    
    update_progress(10, "Initializing Earth Engine...")
    
    # Initialize Earth Engine
    ee.Initialize()
    
    # Extract melt season data with optional advanced QA
    update_progress(15, "Starting data extraction...")
    print(f"\n⏳ Extracting MODIS albedo data year by year...")
    print(f"🔄 This ensures manageable memory usage for long time series")
    
    df = extract_melt_season_data_yearly(
        start_year=start_year, 
        end_year=end_year, 
        scale=scale,
        use_advanced_qa=use_advanced_qa,
        qa_level=qa_level
    )
    
    update_progress(60, "Data extraction completed, validating...")
    
    # Check memory usage and data size
    import psutil
    import sys
    
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"🔍 Memory usage: {memory_mb:.1f} MB")
        print(f"🔍 DataFrame shape: {df.shape}")
        print(f"🔍 DataFrame memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
        
        if memory_mb > 1000:  # More than 1GB
            print("⚠️ HIGH MEMORY USAGE - This might cause crashes!")
            
    except Exception as e:
        print(f"Memory check failed: {e}")
    
    if df.empty:
        print("❌ No data extracted. Check your date range and region.")
        update_progress(0, "No data extracted - check parameters")
        return None
    
    # Export raw data with error handling
    try:
        update_progress(65, "Exporting raw data...")
        
        # Create QA-specific filename
        qa_suffix = f"{'advanced_' if use_advanced_qa else 'basic_'}{qa_level}"
        data_filename = f'athabasca_melt_season_data_{qa_suffix}.csv'
        
        print(f"🔍 About to get output path...")
        csv_path = get_safe_output_path(data_filename)
        print(f"🔍 Got path: {csv_path}")
        print(f"🔍 About to write CSV...")
        
        # Add QA metadata columns to the dataframe
        df_with_qa = df.copy()
        df_with_qa['qa_advanced'] = use_advanced_qa
        df_with_qa['qa_level'] = qa_level
        df_with_qa['qa_description'] = f"{'Advanced' if use_advanced_qa else 'Basic'} QA, {qa_level} level"
        
        # Flush stdout before potentially hanging operation
        import sys
        sys.stdout.flush()
        
        success = safe_csv_write(df_with_qa, csv_path, index=False)
        print(f"🔍 CSV write returned: {success}")
        
        if success:
            print(f"\n💾 Raw data exported: {csv_path}")
            print(f"📋 QA Settings: {'Advanced' if use_advanced_qa else 'Basic'} QA, {qa_level} level")
        else:
            print(f"\n⚠️ Warning: Could not export raw data to {csv_path}")
            
    except Exception as e:
        print(f"❌ Error during raw data export: {e}")
        import traceback
        traceback.print_exc()
        update_progress(0, f"Raw data export failed: {e}")
        return {'error': f'Raw data export failed: {e}', 'success': False}
    
    # Perform comprehensive analysis with error handling
    try:
        update_progress(70, "Performing trend analysis...")
        print(f"\n🔍 Performing comprehensive trend analysis...")
        
        # Import the analysis function safely
        try:
            from analysis.temporal import analyze_melt_season_trends
        except ImportError as e:
            print(f"❌ Could not import analysis function: {e}")
            update_progress(0, f"Import error: {e}")
            return {'error': f'Analysis import failed: {e}', 'success': False}
        
        results = analyze_melt_season_trends(df)
        
        if not results or not results.get('annual_trends'):
            print("❌ Trend analysis failed.")
            update_progress(0, "Trend analysis failed")
            return {'error': 'Trend analysis returned no results', 'success': False}
            
    except Exception as e:
        print(f"❌ Error during trend analysis: {e}")
        import traceback
        traceback.print_exc()
        update_progress(0, f"Trend analysis failed: {e}")
        return {'error': f'Trend analysis failed: {e}', 'success': False}
    
    # Create visualization with error handling
    try:
        update_progress(80, "Creating visualization...")
        from paths import get_figure_path
        figure_path = get_figure_path('athabasca_melt_season_analysis.png', 'melt_season')
        
        # Import visualization function safely
        try:
            from visualization.plots import create_melt_season_plot
        except ImportError as e:
            print(f"❌ Could not import visualization function: {e}")
            # Continue without visualization rather than crashing
            figure_path = None
        
        if figure_path:
            create_melt_season_plot(
                results['annual_trends'], 
                results['monthly_trends'], 
                df, 
                str(figure_path)
            )
            print(f"📊 Visualization created: {figure_path}")
        else:
            print("⚠️ Skipping visualization due to import error")
            
    except Exception as e:
        print(f"❌ Error during visualization: {e}")
        print("⚠️ Continuing without visualization...")
        figure_path = None
    
    # Export results summary with error handling
    try:
        update_progress(85, "Preparing results summary...")
        # Create summary dataframe
        summary_data = []
        
        # Annual trend
        if results.get('annual_trends'):
            annual = results['annual_trends']
            summary_data.append({
                'analysis_type': 'Annual Melt Season',
                'period': annual.get('period', 'Unknown'),
                'trend': annual.get('mann_kendall', {}).get('trend', 'Unknown'),
                'p_value': annual.get('mann_kendall', {}).get('p_value', 'Unknown'),
                'sens_slope_per_year': annual.get('change_per_year', 'Unknown'),
                'percent_change_per_year': annual.get('change_percent_per_year', 'Unknown'),
                'total_change': annual.get('total_change', 'Unknown'),
                'significance': annual.get('significance', 'Unknown'),
                'qa_advanced': use_advanced_qa,
                'qa_level': qa_level,
                'qa_description': f"{'Advanced' if use_advanced_qa else 'Basic'} QA, {qa_level} level"
            })
        
        # Monthly trends
        if results.get('monthly_trends'):
            for month, monthly in results['monthly_trends'].items():
                summary_data.append({
                    'analysis_type': f'{monthly.get("month_name", month)} Only',
                    'period': monthly.get('period', 'Unknown'),
                    'trend': monthly.get('mann_kendall', {}).get('trend', 'Unknown'),
                    'p_value': monthly.get('mann_kendall', {}).get('p_value', 'Unknown'),
                    'sens_slope_per_year': monthly.get('change_per_year', 'Unknown'),
                    'percent_change_per_year': monthly.get('change_percent_per_year', 'Unknown'),
                    'total_change': monthly.get('total_change', 'Unknown'),
                    'significance': monthly.get('significance', 'Unknown'),
                    'qa_advanced': use_advanced_qa,
                    'qa_level': qa_level,
                    'qa_description': f"{'Advanced' if use_advanced_qa else 'Basic'} QA, {qa_level} level"
                })
        
        summary_df = pd.DataFrame(summary_data)
        update_progress(90, "Exporting results summary...")
        
        # Create QA-specific filename for results
        results_filename = f'athabasca_melt_season_results_{qa_suffix}.csv'
        summary_path = get_safe_output_path(results_filename)
        if safe_csv_write(summary_df, summary_path, index=False):
            print(f"💾 Results summary exported: {summary_path}")
        else:
            print(f"⚠️ Warning: Could not export results summary to {summary_path}")
            
    except Exception as e:
        print(f"❌ Error during results summary: {e}")
        print("⚠️ Continuing without results summary...")
        summary_path = None
    
    # Print key findings with error handling
    try:
        update_progress(95, "Finalizing analysis...")
        print_key_findings(results)
    except Exception as e:
        print(f"❌ Error printing key findings: {e}")
        print("⚠️ Skipping key findings display...")
    
    print(f"\n🎉 MELT SEASON ANALYSIS COMPLETE!")
    print(f"Files generated:")
    print(f"   📊 Visualization: {figure_path}")
    print(f"   💾 Raw data: {csv_path}")
    print(f"   💾 Results summary: {summary_path}")
    
    # Prepare comprehensive results for report with error handling
    try:
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
            },
            'success': True,
            'files_generated': {
                'visualization': str(figure_path) if figure_path else None,
                'raw_data': str(csv_path) if csv_path else None,
                'results_summary': str(summary_path) if summary_path else None
            }
        }
    except Exception as e:
        print(f"❌ Error preparing comprehensive results: {e}")
        # Return minimal results
        comprehensive_results = {
            'success': True,
            'error': None,
            'dataset_info': {
                'total_observations': len(df) if 'df' in locals() else 0,
                'period': f"{start_year}-{end_year}",
                'method': "Williamson & Menounos (2021) Melt Season Analysis"
            }
        }
    
    # Generate automatic report with error handling
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
    
    # Final progress update with error handling
    try:
        update_progress(100, "Analysis completed successfully!")
    except Exception as e:
        print(f"⚠️ Progress callback error: {e}")
    
    print("🎯 Workflow completed without crashing!")
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