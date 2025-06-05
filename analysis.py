"""
Fonctions d'analyse spécialisées pour les données d'albédo
"""
import pandas as pd
import numpy as np
from melt_season import analyze_melt_season

# ================================================================================
# GENERAL STATISTICS FUNCTIONS  
# ================================================================================

# Note: analyze_melt_season has been moved to melt_season.py module

# ================================================================================
# STATISTIQUES GÉNÉRALES
# ================================================================================

def calculate_annual_trends(df):
    """
    Calcule les tendances annuelles d'albédo
    
    Args:
        df: DataFrame avec colonnes 'year' et 'albedo_mean'
    
    Returns:
        dict: Statistiques de tendance
    """
    if df.empty or 'albedo_mean' not in df.columns:
        return None
    
    annual_mean = df.groupby('year')['albedo_mean'].mean()
    
    if len(annual_mean) > 2:
        # Régression linéaire
        years = annual_mean.index.values
        values = annual_mean.values
        slope, intercept = np.polyfit(years, values, 1)
        
        # Calcul R²
        predictions = slope * years + intercept
        ss_res = np.sum((values - predictions) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'slope_per_year': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'n_years': len(annual_mean),
            'period': f"{years.min()}-{years.max()}",
            'mean_albedo': np.mean(values),
            'std_albedo': np.std(values)
        }
    
    return None

def calculate_seasonal_statistics(df):
    """
    Calcule les statistiques par saison
    
    Args:
        df: DataFrame avec colonnes 'season' et 'albedo_mean'
    
    Returns:
        dict: Statistiques par saison
    """
    if df.empty or 'season' not in df.columns:
        return None
    
    seasonal_stats = {}
    for season in ['Hiver', 'Printemps', 'Été', 'Automne']:
        season_data = df[df['season'] == season]['albedo_mean'].dropna()
        if not season_data.empty:
            seasonal_stats[season] = {
                'mean': season_data.mean(),
                'std': season_data.std(),
                'min': season_data.min(),
                'max': season_data.max(),
                'count': len(season_data)
            }
    
    return seasonal_stats

def identify_extreme_years(df, metric='albedo_mean', threshold_std=1.5):
    """
    Identifie les années avec des valeurs extrêmes d'albédo
    
    Args:
        df: DataFrame avec données
        metric: Colonne à analyser
        threshold_std: Seuil en écarts-types pour définir les extrêmes
    
    Returns:
        dict: Années avec valeurs extrêmes
    """
    if df.empty or metric not in df.columns:
        return None
    
    annual_means = df.groupby('year')[metric].mean()
    overall_mean = annual_means.mean()
    overall_std = annual_means.std()
    
    threshold_low = overall_mean - threshold_std * overall_std
    threshold_high = overall_mean + threshold_std * overall_std
    
    extreme_years = {
        'low_albedo': annual_means[annual_means < threshold_low].to_dict(),
        'high_albedo': annual_means[annual_means > threshold_high].to_dict(),
        'thresholds': {
            'mean': overall_mean,
            'std': overall_std,
            'low_threshold': threshold_low,
            'high_threshold': threshold_high
        }
    }
    
    return extreme_years