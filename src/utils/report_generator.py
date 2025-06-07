#!/usr/bin/env python3
"""
Report Generator for MODIS Albedo Analyses
Generates comprehensive analysis reports in text format
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
from pathlib import Path

def generate_analysis_report(analysis_type, results_data, output_path, **kwargs):
    """
    Generate comprehensive analysis report
    
    Args:
        analysis_type: Type of analysis (e.g., 'MCD43A3', 'Melt_Season', 'Hypsometric')
        results_data: Dictionary containing analysis results
        output_path: Path to save the report
        **kwargs: Additional parameters specific to analysis type
    """
    
    # Common header
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"                    ANALYSES COMPLÈTES DU GLACIER ATHABASCA")
    report_lines.append(f"                         DONNÉES MODIS {analysis_type.upper()}")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"DATE DE GÉNÉRATION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("ZONE D'ÉTUDE: Glacier Athabasca, Champs de Glace Columbia, Alberta, Canada")
    report_lines.append("MASQUE UTILISÉ: Athabasca_mask_2023_cut.geojson")
    report_lines.append("FILTRAGE QUALITÉ: QA ≤ 1 (Full + magnitude inversions)")
    
    # Analysis-specific content
    if analysis_type == 'MCD43A3':
        report_lines.extend(_generate_mcd43a3_report(results_data, **kwargs))
    elif analysis_type == 'Melt_Season':
        report_lines.extend(_generate_melt_season_report(results_data, **kwargs))
    elif analysis_type == 'Hypsometric':
        report_lines.extend(_generate_hypsometric_report(results_data, **kwargs))
    
    # Common footer
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("FIN DU RAPPORT - GLACIER ATHABASCA ANALYSES COMPLÈTES")
    report_lines.append(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    
    # Write report
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"📄 RAPPORT GÉNÉRÉ: {output_path}")
    return output_path

def _generate_mcd43a3_report(results_data, **kwargs):
    """Generate MCD43A3-specific report content"""
    
    lines = []
    
    # Get data
    df = results_data.get('spectral_data', pd.DataFrame())
    stats = results_data.get('statistics', {})
    start_year = kwargs.get('start_year', 2010)
    end_year = kwargs.get('end_year', 2024)
    
    lines.append(f"SATELLITE: MODIS Terra/Aqua (MCD43A3)")
    lines.append(f"RÉSOLUTION: 500m")
    lines.append(f"PÉRIODE: {start_year}-{end_year} (Saison de fonte: Juin-Septembre)")
    lines.append("")
    
    # Executive Summary
    lines.append("=" * 80)
    lines.append("1. RÉSUMÉ EXÉCUTIF")
    lines.append("=" * 80)
    lines.append("")
    
    if not df.empty:
        lines.append(f"PRINCIPALES DÉCOUVERTES:")
        lines.append(f"- {len(df)} observations valides sur la période {start_year}-{end_year}")
        lines.append(f"- Années analysées: {end_year - start_year + 1} ans")
        if 'date' in df.columns:
            lines.append(f"- Période couverte: {df['date'].min()} à {df['date'].max()}")
        
        # Find max/min values for visible albedo
        if 'Albedo_BSA_vis' in df.columns:
            max_vis = df['Albedo_BSA_vis'].max()
            min_vis = df['Albedo_BSA_vis'].min()
            max_idx = df['Albedo_BSA_vis'].idxmax()
            min_idx = df['Albedo_BSA_vis'].idxmin()
            max_date = df.loc[max_idx, 'date'] if 'date' in df.columns else "N/A"
            min_date = df.loc[min_idx, 'date'] if 'date' in df.columns else "N/A"
            lines.append(f"- MAXIMUM D'ALBEDO: {max_vis:.3f} le {max_date}")
            lines.append(f"- MINIMUM D'ALBEDO: {min_vis:.3f} le {min_date}")
            lines.append(f"- AMPLITUDE TOTALE: {max_vis - min_vis:.3f} unités")
    
    lines.append("")
    lines.append("ANALYSES EFFECTUÉES:")
    lines.append("✓ Analyse spectrale détaillée (6 bandes MODIS)")
    lines.append("✓ Analyse temporelle avec test de tendance")
    lines.append("✓ Tests statistiques (Mann-Kendall, Sen's slope)")
    lines.append("✓ Analyse qualité des données")
    lines.append("")
    
    # Spectral comparison summary
    if stats and 'spectral_comparison' in stats:
        comp = stats['spectral_comparison']
        lines.append("RÉSULTATS SPECTRAUX CLÉS:")
        lines.append(f"- Pattern: {comp.get('interpretation', 'N/A').replace('_', ' ').title()}")
        lines.append(f"- Visible change: {comp.get('visible_avg_change', 0):.2f}%/year")
        lines.append(f"- NIR change: {comp.get('nir_avg_change', 0):.2f}%/year")
        lines.append("")
    
    # Raw Data Section
    lines.append("=" * 80)
    lines.append(f"2. DONNÉES BRUTES - OBSERVATIONS INDIVIDUELLES ({len(df)} observations)")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Format: Date | Albedo_Visible | Albedo_NIR | Band1(Rouge) | Band2(NIR) | Band3(Bleu) | Band4(Vert)")
    lines.append("")
    
    # Sample data (first 10, then last 5)
    if not df.empty:
        # Sort by date if available
        if 'date' in df.columns:
            df_sorted = df.sort_values('date')
        else:
            df_sorted = df
            
        for _, row in df_sorted.head(10).iterrows():
            line = f"{row.get('date', 'N/A'):<12} | "
            line += f"{row.get('Albedo_BSA_vis', 0):.3f} | "
            line += f"{row.get('Albedo_BSA_nir', 0):.3f} | "
            line += f"{row.get('Albedo_BSA_Band1', 0):.3f} | "
            line += f"{row.get('Albedo_BSA_Band2', 0):.3f} | "
            line += f"{row.get('Albedo_BSA_Band3', 0):.3f} | "
            line += f"{row.get('Albedo_BSA_Band4', 0):.3f}"
            lines.append(line)
        
        if len(df) > 10:
            lines.append("...")
            lines.append(f"[{len(df) - 15} observations intermédiaires omises]")
            lines.append("...")
            lines.append("")
            # Show last few
            for _, row in df_sorted.tail(5).iterrows():
                line = f"{row.get('date', 'N/A'):<12} | "
                line += f"{row.get('Albedo_BSA_vis', 0):.3f} | "
                line += f"{row.get('Albedo_BSA_nir', 0):.3f} | "
                line += f"{row.get('Albedo_BSA_Band1', 0):.3f} | "
                line += f"{row.get('Albedo_BSA_Band2', 0):.3f} | "
                line += f"{row.get('Albedo_BSA_Band3', 0):.3f} | "
                line += f"{row.get('Albedo_BSA_Band4', 0):.3f}"
                lines.append(line)
    
    lines.append("")
    
    # Statistical Analysis
    lines.append("=" * 80)
    lines.append("3. ANALYSE STATISTIQUE DÉTAILLÉE")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append("BANDES MODIS ANALYSÉES:")
    lines.append("- Band 1 (Rouge): 620-670 nm    | Groupe: Visible")
    lines.append("- Band 2 (NIR):   841-876 nm    | Groupe: Proche Infrarouge")
    lines.append("- Band 3 (Bleu):  459-479 nm    | Groupe: Visible")
    lines.append("- Band 4 (Vert):  545-565 nm    | Groupe: Visible")
    lines.append("- BSA Visible: Composite visible | Groupe: Visible")
    lines.append("- BSA NIR: Composite NIR         | Groupe: Proche Infrarouge")
    lines.append("")
    
    if stats:
        for group_name, group_results in stats.items():
            if group_name == 'spectral_comparison':
                continue
                
            lines.append(f"GROUPE: {group_name.upper()}")
            lines.append("-" * 40)
            
            for band, band_stats in group_results.items():
                lines.append(f"\n{band}:")
                if 'change_percent_per_year' in band_stats:
                    lines.append(f"- Changement: {band_stats['change_percent_per_year']:.2f}% par an")
                    
                if 'mann_kendall' in band_stats:
                    mk = band_stats['mann_kendall']
                    lines.append(f"- Test Mann-Kendall: {mk.get('trend', 'N/A')}")
                    lines.append(f"- P-value: {mk.get('p_value', 1.0):.4f}")
                    
                if 'significance' in band_stats:
                    lines.append(f"- Significance: {band_stats['significance']}")
                    
                if 'n_years' in band_stats:
                    lines.append(f"- Années analysées: {band_stats['n_years']}")
                    
            lines.append("")
    
    # Technical metadata
    lines.append("=" * 80)
    lines.append("4. MÉTADONNÉES TECHNIQUES")
    lines.append("=" * 80)
    lines.append("")
    lines.append("CONTRÔLE QUALITÉ:")
    lines.append("- Filtrage QA: ≤ 1 (Full + Magnitude inversions)")
    lines.append("- Validation pixels: Minimum 5 pixels/observation")
    lines.append("- Période standardisée: Saison fonte (juin-septembre)")
    lines.append("- Projection: WGS84 Geographic (EPSG:4326)")
    lines.append("")
    lines.append("LOGICIELS UTILISÉS:")
    lines.append("- Google Earth Engine (acquisition/traitement)")
    lines.append("- Python 3.x (analyse statistique)")
    lines.append("- Bibliothèques: geemap, pandas, scipy, matplotlib")
    lines.append("")
    
    return lines

def _generate_melt_season_report(results_data, **kwargs):
    """Generate Melt Season-specific report content"""
    
    lines = []
    
    # Get data
    df = results_data.get('melt_season_data', pd.DataFrame())
    monthly_stats = results_data.get('monthly_statistics', {})
    overall_stats = results_data.get('overall_statistics', {})
    fire_impact = results_data.get('fire_impact', {})
    start_year = kwargs.get('start_year', 2010)
    end_year = kwargs.get('end_year', 2024)
    
    lines.append(f"SATELLITE: MODIS Terra (MOD10A1) + Aqua (MYD10A1)")
    lines.append(f"RÉSOLUTION: 500m")
    lines.append(f"PÉRIODE: {start_year}-{end_year} (Saison de fonte: Juin-Septembre)")
    lines.append("")
    
    # Executive Summary
    lines.append("=" * 80)
    lines.append("1. RÉSUMÉ EXÉCUTIF - ANALYSE SAISON DE FONTE")
    lines.append("=" * 80)
    lines.append("")
    
    if overall_stats:
        slope = overall_stats.get('change_percent_per_year', 0)
        p_value = overall_stats.get('mann_kendall', {}).get('p_value', 1.0)
        significance = "SIGNIFICATIF" if p_value < 0.05 else "NON SIGNIFICATIF"
        
        lines.append(f"TENDANCE GLOBALE ({start_year}-{end_year}):")
        lines.append(f"• Changement: {slope:.2f}%/year")
        lines.append(f"• Total change: {slope * (end_year - start_year):.1f}%")
        lines.append(f"• Significance: p = {p_value:.4f}")
        lines.append(f"• Status: {significance}")
        lines.append("")
        
        if not df.empty:
            lines.append("DATASET:")
            lines.append(f"• Years analyzed: {end_year - start_year + 1}")
            lines.append(f"• Total observations: {len(df)}")
            lines.append(f"• Period: {start_year}-{end_year}")
            lines.append("")
    
    # Monthly breakdown
    if monthly_stats:
        lines.append("TENDANCES MENSUELLES:")
        for month_num, stats in monthly_stats.items():
            if isinstance(stats, dict):
                slope = stats.get('change_percent_per_year', 0)
                p_value = stats.get('mann_kendall', {}).get('p_value', 1.0)
                significance = "**" if p_value < 0.05 else ""
                month_name = stats.get('month_name', f'Month {month_num}')
                lines.append(f"• {month_name}: {slope:.2f}%/yr {significance}")
        
        # Fire years if detected
        fire_years = kwargs.get('fire_years', [])
        if fire_years:
            lines.append("")
            lines.append(f"FIRE YEARS: {', '.join(map(str, fire_years))}")
            fire_p = kwargs.get('fire_significance', 1.0)
            if fire_p < 0.05:
                lines.append("• Statistically significant (p<0.05)")
    
    lines.append("")
    
    # ====== NEW: DETAILED DATA EXCERPTS SECTION ======
    if not df.empty:
        lines.append("=" * 80)
        lines.append("2. DONNÉES BRUTES COMPLÈTES - EXTRAITS DÉTAILLÉS")
        lines.append("=" * 80)
        lines.append("")
        
        # Ensure we have necessary columns for proper formatting
        data_cols = []
        if 'date' in df.columns:
            data_cols.append('date')
        if 'year' in df.columns:
            data_cols.append('year')
        if 'month' in df.columns:
            data_cols.append('month')
        if 'albedo' in df.columns:
            data_cols.append('albedo')
        elif 'albedo_mean' in df.columns:
            data_cols.append('albedo_mean')
        if 'albedo_min' in df.columns:
            data_cols.append('albedo_min')
        if 'albedo_max' in df.columns:
            data_cols.append('albedo_max')
        if 'albedo_stdDev' in df.columns:
            data_cols.append('albedo_stdDev')
        
        lines.append(f"STRUCTURE DES DONNÉES:")
        lines.append(f"• Total d'observations: {len(df)}")
        lines.append(f"• Colonnes disponibles: {', '.join(df.columns)}")
        lines.append(f"• Période couverte: {df['date'].min() if 'date' in df.columns else 'N/A'} à {df['date'].max() if 'date' in df.columns else 'N/A'}")
        lines.append("")
        
        # Sort data by date if available
        df_display = df.copy()
        if 'date' in df.columns:
            df_display = df_display.sort_values('date')
            
        # Sample of raw data - first 20 observations
        lines.append("ÉCHANTILLON DE DONNÉES BRUTES (20 premières observations):")
        lines.append("-" * 120)
        
        header = ""
        if 'date' in df_display.columns:
            header += "Date        "
        if 'year' in df_display.columns:
            header += "Année "
        if 'month' in df_display.columns:
            header += "Mois "
        if 'albedo' in df_display.columns:
            header += "Albedo   "
        elif 'albedo_mean' in df_display.columns:
            header += "Alb_Moy  "
        if 'albedo_min' in df_display.columns:
            header += "Alb_Min  "
        if 'albedo_max' in df_display.columns:
            header += "Alb_Max  "
        if 'albedo_stdDev' in df_display.columns:
            header += "Écart-type"
            
        lines.append(header)
        lines.append("-" * len(header))
        
        for i, (_, row) in enumerate(df_display.head(20).iterrows()):
            line = ""
            if 'date' in df_display.columns:
                line += f"{str(row['date']):<12}"
            if 'year' in df_display.columns:
                line += f"{int(row['year']):<5} "
            if 'month' in df_display.columns:
                line += f"{int(row['month']):<4} "
            if 'albedo' in df_display.columns:
                line += f"{row['albedo']:.3f}    "
            elif 'albedo_mean' in df_display.columns:
                line += f"{row['albedo_mean']:.3f}     "
            if 'albedo_min' in df_display.columns:
                line += f"{row['albedo_min']:.3f}    "
            if 'albedo_max' in df_display.columns:
                line += f"{row['albedo_max']:.3f}    "
            if 'albedo_stdDev' in df_display.columns:
                line += f"{row['albedo_stdDev']:.3f}"
            lines.append(line)
        
        if len(df_display) > 20:
            lines.append(f"... [{len(df_display) - 40} observations intermédiaires omises] ...")
            lines.append("")
            
            # Show last 20 observations
            lines.append("DERNIÈRES 20 OBSERVATIONS:")
            lines.append("-" * len(header))
            lines.append(header)
            lines.append("-" * len(header))
            
            for _, row in df_display.tail(20).iterrows():
                line = ""
                if 'date' in df_display.columns:
                    line += f"{str(row['date']):<12}"
                if 'year' in df_display.columns:
                    line += f"{int(row['year']):<5} "
                if 'month' in df_display.columns:
                    line += f"{int(row['month']):<4} "
                if 'albedo' in df_display.columns:
                    line += f"{row['albedo']:.3f}    "
                elif 'albedo_mean' in df_display.columns:
                    line += f"{row['albedo_mean']:.3f}     "
                if 'albedo_min' in df_display.columns:
                    line += f"{row['albedo_min']:.3f}    "
                if 'albedo_max' in df_display.columns:
                    line += f"{row['albedo_max']:.3f}    "
                if 'albedo_stdDev' in df_display.columns:
                    line += f"{row['albedo_stdDev']:.3f}"
                lines.append(line)
        
        lines.append("")
        
        # ====== NEW: YEARLY DETAILED BREAKDOWN ======
        lines.append("=" * 80)
        lines.append("3. ANALYSE DÉTAILLÉE PAR ANNÉE")
        lines.append("=" * 80)
        lines.append("")
        
        albedo_col = 'albedo' if 'albedo' in df.columns else 'albedo_mean'
        if 'year' in df.columns and albedo_col in df.columns:
            yearly_stats = df.groupby('year')[albedo_col].agg([
                'count', 'mean', 'std', 'min', 'max', 'median'
            ]).round(4)
            
            lines.append("STATISTIQUES ANNUELLES COMPLÈTES:")
            lines.append("Année | Obs | Moyenne | Éc.Type | Minimum | Maximum | Médiane")
            lines.append("------|-----|---------|---------|---------|---------|--------")
            
            for year, stats in yearly_stats.iterrows():
                lines.append(f"{int(year):<5} | {int(stats['count']):<3} | {stats['mean']:.4f}  | {stats['std']:.4f}  | {stats['min']:.4f}  | {stats['max']:.4f}  | {stats['median']:.4f}")
            
            lines.append("")
            
            # ASCII trend visualization
            lines.append("TENDANCE VISUELLE (ASCII):")
            yearly_means = yearly_stats['mean']
            min_val, max_val = yearly_means.min(), yearly_means.max()
            range_val = max_val - min_val
            
            lines.append(f"Plage: {min_val:.3f} - {max_val:.3f} (amplitude: {range_val:.3f})")
            lines.append("")
            
            for year, mean_val in yearly_means.items():
                # Scale to 50 characters width
                if range_val > 0:
                    scaled_pos = int(((mean_val - min_val) / range_val) * 50)
                else:
                    scaled_pos = 25
                bar = " " * scaled_pos + "█"
                lines.append(f"{int(year)} |{bar:<50} {mean_val:.3f}")
            
            lines.append("")
        
        # ====== NEW: MONTHLY DETAILED BREAKDOWN ======
        lines.append("=" * 80)
        lines.append("4. ANALYSE DÉTAILLÉE PAR MOIS")
        lines.append("=" * 80)
        lines.append("")
        
        if 'month' in df.columns and albedo_col in df.columns:
            monthly_data = df.groupby('month')[albedo_col].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).round(4)
            
            month_names = {6: 'Juin', 7: 'Juillet', 8: 'Août', 9: 'Septembre'}
            
            lines.append("STATISTIQUES MENSUELLES (Saison de fonte):")
            lines.append("Mois      | Obs | Moyenne | Éc.Type | Minimum | Maximum")
            lines.append("----------|-----|---------|---------|---------|--------")
            
            for month, stats in monthly_data.iterrows():
                month_name = month_names.get(month, f"Mois {month}")
                lines.append(f"{month_name:<9} | {int(stats['count']):<3} | {stats['mean']:.4f}  | {stats['std']:.4f}  | {stats['min']:.4f}  | {stats['max']:.4f}")
            
            lines.append("")
            
            # Monthly progression visualization
            lines.append("PROGRESSION MENSUELLE (ASCII):")
            monthly_means = monthly_data['mean']
            min_monthly = monthly_means.min()
            max_monthly = monthly_means.max()
            range_monthly = max_monthly - min_monthly
            
            lines.append(f"Plage mensuelle: {min_monthly:.3f} - {max_monthly:.3f}")
            lines.append("")
            
            for month, mean_val in monthly_means.items():
                month_name = month_names.get(month, f"M{month}")
                if range_monthly > 0:
                    scaled_pos = int(((mean_val - min_monthly) / range_monthly) * 40)
                else:
                    scaled_pos = 20
                bar = "█" * max(1, scaled_pos)
                lines.append(f"{month_name:<9} |{bar:<40} {mean_val:.3f}")
            
            lines.append("")
        
        # ====== NEW: EXTREME VALUES ANALYSIS ======
        lines.append("=" * 80)
        lines.append("5. ANALYSE DES VALEURS EXTRÊMES")
        lines.append("=" * 80)
        lines.append("")
        
        if albedo_col in df.columns:
            # Find extreme values
            max_idx = df[albedo_col].idxmax()
            min_idx = df[albedo_col].idxmin()
            
            max_row = df.loc[max_idx]
            min_row = df.loc[min_idx]
            
            lines.append("VALEUR MAXIMALE D'ALBEDO:")
            lines.append(f"• Valeur: {max_row[albedo_col]:.4f}")
            if 'date' in df.columns:
                lines.append(f"• Date: {max_row['date']}")
            if 'year' in df.columns and 'month' in df.columns:
                month_name = {6: 'Juin', 7: 'Juillet', 8: 'Août', 9: 'Septembre'}.get(max_row['month'], f"Mois {max_row['month']}")
                lines.append(f"• Période: {month_name} {int(max_row['year'])}")
            lines.append("")
            
            lines.append("VALEUR MINIMALE D'ALBEDO:")
            lines.append(f"• Valeur: {min_row[albedo_col]:.4f}")
            if 'date' in df.columns:
                lines.append(f"• Date: {min_row['date']}")
            if 'year' in df.columns and 'month' in df.columns:
                month_name = {6: 'Juin', 7: 'Juillet', 8: 'Août', 9: 'Septembre'}.get(min_row['month'], f"Mois {min_row['month']}")
                lines.append(f"• Période: {month_name} {int(min_row['year'])}")
            lines.append("")
            
            # Find top/bottom 10 values
            top_10 = df.nlargest(10, albedo_col)
            bottom_10 = df.nsmallest(10, albedo_col)
            
            lines.append("TOP 10 VALEURS D'ALBEDO LES PLUS ÉLEVÉES:")
            lines.append("Rang | Date        | Albedo | Année | Mois")
            lines.append("-----|-------------|--------|-------|------")
            for i, (_, row) in enumerate(top_10.iterrows(), 1):
                date_str = str(row['date']) if 'date' in df.columns else "N/A"
                year_str = str(int(row['year'])) if 'year' in df.columns else "N/A"
                month_str = str(int(row['month'])) if 'month' in df.columns else "N/A"
                lines.append(f"{i:<4} | {date_str:<11} | {row[albedo_col]:.4f} | {year_str:<5} | {month_str}")
            
            lines.append("")
            
            lines.append("TOP 10 VALEURS D'ALBEDO LES PLUS FAIBLES:")
            lines.append("Rang | Date        | Albedo | Année | Mois")
            lines.append("-----|-------------|--------|-------|------")
            for i, (_, row) in enumerate(bottom_10.iterrows(), 1):
                date_str = str(row['date']) if 'date' in df.columns else "N/A"
                year_str = str(int(row['year'])) if 'year' in df.columns else "N/A"
                month_str = str(int(row['month'])) if 'month' in df.columns else "N/A"
                lines.append(f"{i:<4} | {date_str:<11} | {row[albedo_col]:.4f} | {year_str:<5} | {month_str}")
        
        lines.append("")
    
    # ====== ENHANCED: STATISTICAL ANALYSIS ======
    lines.append("=" * 80)
    lines.append("6. ANALYSE STATISTIQUE AVANCÉE")
    lines.append("=" * 80)
    lines.append("")
    
    if overall_stats:
        lines.append("TESTS STATISTIQUES DÉTAILLÉS:")
        
        # Mann-Kendall test details
        mk_stats = overall_stats.get('mann_kendall', {})
        if mk_stats:
            lines.append(f"• Test Mann-Kendall:")
            lines.append(f"  - Statistic tau: {mk_stats.get('tau', 'N/A')}")
            lines.append(f"  - P-value: {mk_stats.get('p_value', 'N/A')}")
            lines.append(f"  - Tendance: {mk_stats.get('trend', 'N/A')}")
        
        # Sen's slope details  
        sens_stats = overall_stats.get('sens_slope', {})
        if sens_stats:
            lines.append(f"• Pente de Sen:")
            lines.append(f"  - Pente: {sens_stats.get('slope', 'N/A')}")
            lines.append(f"  - Pente/année: {sens_stats.get('slope_per_year', 'N/A')}")
            lines.append(f"  - Changement %/an: {overall_stats.get('change_percent_per_year', 'N/A'):.3f}%")
        
        lines.append("")
    
    # Enhanced monthly statistics
    if monthly_stats:
        lines.append("DÉTAIL PAR MOIS - TESTS STATISTIQUES:")
        lines.append("")
        month_names = {6: 'Juin', 7: 'Juillet', 8: 'Août', 9: 'Septembre'}
        
        for month_num, stats in monthly_stats.items():
            if isinstance(stats, dict):
                month_name = month_names.get(month_num, f'Mois {month_num}')
                lines.append(f"{month_name.upper()}:")
                
                slope = stats.get('change_percent_per_year', 0)
                lines.append(f"  • Changement: {slope:.3f}%/année")
                
                mk_stats = stats.get('mann_kendall', {})
                if mk_stats:
                    lines.append(f"  • Mann-Kendall tau: {mk_stats.get('tau', 'N/A')}")
                    lines.append(f"  • P-value: {mk_stats.get('p_value', 'N/A'):.4f}")
                    lines.append(f"  • Tendance: {mk_stats.get('trend', 'N/A')}")
                
                sens_stats = stats.get('sens_slope', {})
                if sens_stats:
                    lines.append(f"  • Pente Sen: {sens_stats.get('slope_per_year', 'N/A')}")
                
                n_years = stats.get('n_years', 0)
                lines.append(f"  • Années analysées: {n_years}")
                lines.append("")
    
    # Fire impact section (enhanced)
    if fire_impact and fire_impact.get('significant'):
        lines.append("=" * 80)
        lines.append("7. IMPACT DES FEUX DE FORÊT - ANALYSE DÉTAILLÉE")
        lines.append("=" * 80)
        lines.append("")
        
        fire_years = fire_impact.get('fire_years', [])
        lines.append(f"ANNÉES DE FEUX IDENTIFIÉES: {', '.join(map(str, fire_years))}")
        lines.append("")
        
        lines.append("COMPARAISON STATISTIQUE:")
        lines.append(f"• Albedo moyen années de feux: {fire_impact.get('fire_mean', 0):.4f}")
        lines.append(f"• Albedo moyen années normales: {fire_impact.get('non_fire_mean', 0):.4f}")
        lines.append(f"• Différence absolue: {fire_impact.get('non_fire_mean', 0) - fire_impact.get('fire_mean', 0):.4f}")
        lines.append(f"• Différence relative: {fire_impact.get('percent_difference', 0):.2f}%")
        lines.append(f"• Test statistique: p = {fire_impact.get('p_value', 1.0):.6f}")
        
        if fire_impact.get('p_value', 1.0) < 0.001:
            lines.append("• Significativité: TRÈS HAUTEMENT SIGNIFICATIF (p < 0.001)")
        elif fire_impact.get('p_value', 1.0) < 0.01:
            lines.append("• Significativité: HAUTEMENT SIGNIFICATIF (p < 0.01)")
        elif fire_impact.get('p_value', 1.0) < 0.05:
            lines.append("• Significativité: SIGNIFICATIF (p < 0.05)")
        else:
            lines.append("• Significativité: NON SIGNIFICATIF")
        
        lines.append("")
        
        # Show fire years data if available
        if not df.empty and 'year' in df.columns and albedo_col in df.columns:
            lines.append("DONNÉES DÉTAILLÉES POUR LES ANNÉES DE FEUX:")
            lines.append("Année | Obs | Albedo Moyen | Écart-type | Min   | Max")
            lines.append("------|-----|--------------|------------|-------|-------")
            
            for year in fire_years:
                year_data = df[df['year'] == year]
                if not year_data.empty:
                    stats = year_data[albedo_col].agg(['count', 'mean', 'std', 'min', 'max'])
                    lines.append(f"{year:<5} | {int(stats['count']):<3} | {stats['mean']:.6f}   | {stats['std']:.6f} | {stats['min']:.3f} | {stats['max']:.3f}")
        
        lines.append("")
    
    return lines

def _generate_hypsometric_report(results_data, **kwargs):
    """Generate Hypsometric-specific report content"""
    
    lines = []
    
    # Get data
    elevation_stats = results_data.get('elevation_statistics', {})
    median_elevation = results_data.get('median_elevation', 0)
    elevation_comparison = results_data.get('elevation_comparison', {})
    start_year = kwargs.get('start_year', 2010)
    end_year = kwargs.get('end_year', 2024)
    
    lines.append(f"SATELLITE: MODIS Terra (MOD10A1) + Aqua (MYD10A1)")
    lines.append(f"RÉSOLUTION: 500m")
    lines.append(f"PÉRIODE: {start_year}-{end_year}")
    lines.append(f"MÉTHODE: Analyse hypsométrique par bandes d'élévation")
    lines.append(f"ÉLÉVATION MÉDIANE: {median_elevation:.0f} m")
    lines.append("")
    
    # Executive Summary
    lines.append("=" * 80)
    lines.append("1. RÉSUMÉ EXÉCUTIF - ANALYSE HYPSOMÉTRIQUE")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append("MÉTHODOLOGIE:")
    lines.append("• Division en 3 bandes d'élévation")
    lines.append("• Référence: Médiane d'élévation du glacier")
    lines.append("• Seuil: ±100m autour de la médiane")
    lines.append(f"• Élévation médiane calculée: {median_elevation:.0f} m")
    lines.append("")
    
    if elevation_stats:
        lines.append("RÉSULTATS PAR BANDE D'ÉLÉVATION:")
        lines.append("")
        
        for band, stats in elevation_stats.items():
            band_name = stats.get('band_name', band)
            n_obs = stats.get('n_observations', 0)
            
            lines.append(f"{band_name.upper()}:")
            lines.append(f"• Observations: {n_obs}")
            
            if 'elevation_range' in stats:
                elev_range = stats['elevation_range']
                lines.append(f"• Élévation: {elev_range.get('min', 0):.0f}-{elev_range.get('max', 0):.0f} m")
            
            if 'trend_analysis' in stats:
                trend = stats['trend_analysis']
                slope = trend.get('sens_slope', {}).get('slope_per_year', 0)
                p_value = trend.get('mann_kendall', {}).get('p_value', 1.0)
                significance = "SIGNIFICATIF" if p_value < 0.05 else "NON SIGNIFICATIF"
                
                lines.append(f"• Pente Sen: {slope:.4f} par an")
                lines.append(f"• Test Mann-Kendall: p = {p_value:.2f}")
                lines.append(f"• Tendance: {significance}")
            
            lines.append("")
    
    # Elevation pattern interpretation
    if elevation_comparison:
        lines.append("=" * 80)
        lines.append("2. INTERPRÉTATION DU PATTERN D'ÉLÉVATION")
        lines.append("=" * 80)
        lines.append("")
        
        interpretation = elevation_comparison.get('interpretation', 'Pattern non identifié')
        lines.append(f"PATTERN IDENTIFIÉ: {interpretation}")
        lines.append("")
        
        if elevation_comparison.get('transient_snowline_pattern'):
            lines.append("✅ PATTERN WILLIAMSON & MENOUNOS CONFIRMÉ!")
            lines.append("Le déclin d'albedo le plus fort se produit près de l'élévation")
            lines.append("médiane, indiquant une ligne de neige transitoire montante")
            lines.append("durant la saison de fonte.")
            lines.append("")
        elif elevation_comparison.get('elevation_gradient_pattern'):
            lines.append("🌡️ RÉCHAUFFEMENT DÉPENDANT DE L'ÉLÉVATION DÉTECTÉ!")
            lines.append("Déclin plus fort aux basses altitudes suggère un")
            lines.append("réchauffement renforcé dans la zone d'ablation.")
            lines.append("")
    
    return lines

def add_report_generation_to_workflow(workflow_func, analysis_type):
    """
    Decorator to add automatic report generation to analysis workflows
    """
    def wrapper(*args, **kwargs):
        # Run original analysis
        results = workflow_func(*args, **kwargs)
        
        # Generate report if results available
        if results:
            try:
                # Determine output path
                output_dir = Path("outputs")
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = output_dir / f"athabasca_{analysis_type.lower()}_report_{timestamp}.txt"
                
                # Generate report
                generate_analysis_report(
                    analysis_type=analysis_type,
                    results_data=results,
                    output_path=str(report_path),
                    **kwargs
                )
                
                print(f"✅ RAPPORT AUTOMATIQUE GÉNÉRÉ: {report_path}")
                
            except Exception as e:
                print(f"⚠️  Erreur génération rapport: {e}")
        
        return results
    
    return wrapper 