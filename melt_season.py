"""
Melt season analysis functions for Athabasca Glacier
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from data_processing import smooth_timeseries

# ================================================================================
# MELT SEASON ANALYSIS
# ================================================================================

def analyze_melt_season(df, years=None):
    """
    Analyse spécifique de la saison de fonte (juin-septembre)
    
    Args:
        df: DataFrame avec les données d'albédo
        years: Liste d'années à analyser (None = toutes)
    
    Returns:
        dict: Statistiques par année et DataFrame filtré
    """
    if df.empty:
        print("❌ Pas de données pour l'analyse de fonte")
        return None, None
    
    # Filtrer juin à septembre (mois 6-9)
    df_melt = df[df['month'].isin([6, 7, 8, 9])].copy()
    
    if years:
        df_melt = df_melt[df_melt['year'].isin(years)]
    
    # Ajouter jour de l'année pour faciliter les comparaisons
    df_melt['day_of_year'] = df_melt['date'].dt.dayofyear
    
    # Statistiques par année
    melt_stats = {}
    for year in df_melt['year'].unique():
        year_data = df_melt[df_melt['year'] == year]
        
        if len(year_data) > 10:  # Au moins 10 observations
            stats = {
                'mean': year_data['albedo_mean'].mean(),
                'std': year_data['albedo_mean'].std(),
                'min': year_data['albedo_mean'].min(),
                'min_date': year_data.loc[year_data['albedo_mean'].idxmin(), 'date'],
                'max': year_data['albedo_mean'].max(),
                'max_date': year_data.loc[year_data['albedo_mean'].idxmax(), 'date'],
                'n_obs': len(year_data),
                'trend': None
            }
            
            # Calculer la tendance juin-septembre
            if len(year_data) > 20:
                x = year_data['day_of_year'].values
                y = year_data['albedo_mean'].values
                z = np.polyfit(x, y, 1)
                stats['trend'] = z[0]  # Pente journalière
                stats['trend_total'] = z[0] * (x.max() - x.min())  # Changement total
            
            melt_stats[year] = stats
    
    return melt_stats, df_melt

def plot_melt_season_analysis(df, melt_stats, title="", save_path=None, smoothing_level='high'):
    """
    Graphique spécialisé pour l'analyse de la saison de fonte
    
    Args:
        df: DataFrame filtré pour la saison de fonte
        melt_stats: Dictionnaire des statistiques par année
        title: Titre additionnel
        save_path: Chemin pour sauvegarder
        smoothing_level: 'low', 'medium', 'high' (niveau de lissage)
    """
    if df.empty or not melt_stats:
        print("❌ Données insuffisantes pour le graphique de fonte")
        return None
    
    # Configuration du style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig = plt.figure(figsize=(18, 12))
    
    # Grille de subplots
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 1.5, 1.5], hspace=0.3, wspace=0.3)
    
    # 1. Évolution multi-annuelle (grand panneau du haut)
    ax1 = fig.add_subplot(gs[0, :])
    
    # Couleurs pour chaque année
    years = sorted(df['year'].unique())
    colors_years = plt.cm.viridis(np.linspace(0, 1, len(years)))
    
    for i, year in enumerate(years):
        year_data = df[df['year'] == year].sort_values('date')
        if len(year_data) > 5:
            # Créer un axe temporel normalisé (jour 1 juin = 0)
            june_1 = pd.Timestamp(f'{year}-06-01')
            days_from_june = (year_data['date'] - june_1).dt.days
            
            # Points pour les valeurs brutes (très transparents et petits)
            ax1.scatter(days_from_june, year_data['albedo_mean'], 
                       color=colors_years[i], s=3, alpha=0.15, zorder=1)
            
            # Interpolation pour courbes très lisses
            if len(year_data) > 10:
                # Supprimer les valeurs aberrantes
                q1 = year_data['albedo_mean'].quantile(0.05)
                q3 = year_data['albedo_mean'].quantile(0.95)
                mask = (year_data['albedo_mean'] >= q1) & (year_data['albedo_mean'] <= q3)
                clean_data = year_data[mask]
                
                if len(clean_data) > 10:
                    # Créer une grille régulière pour l'interpolation
                    x_smooth = np.linspace(days_from_june.min(), days_from_june.max(), 200)
                    
                    # Trier les données pour l'interpolation
                    sorted_indices = np.argsort(clean_data['date'])
                    x_data = days_from_june.iloc[clean_data.index[sorted_indices] - year_data.index[0]]
                    y_data = clean_data['albedo_mean'].iloc[sorted_indices].values
                    
                    # Supprimer les doublons
                    unique_mask = np.append(True, np.diff(x_data) > 0)
                    x_unique = x_data[unique_mask]
                    y_unique = y_data[unique_mask]
                    
                    if len(x_unique) > 3:
                        try:
                            # Paramètres de lissage selon le niveau
                            if smoothing_level == 'high':
                                window = min(21, len(y_unique) // 2)
                                spline_points = 150
                            elif smoothing_level == 'medium':
                                window = min(15, len(y_unique) // 3)
                                spline_points = 200
                            else:  # low
                                window = min(7, len(y_unique) // 4)
                                spline_points = 300
                            
                            # Appliquer d'abord une moyenne mobile
                            y_smooth_pre = pd.Series(y_unique).rolling(window=window, center=True, min_periods=1).mean().values
                            
                            # Redéfinir x_smooth avec le nombre de points approprié
                            x_smooth = np.linspace(days_from_june.min(), days_from_june.max(), spline_points)
                            
                            # Puis interpolation spline
                            spl = make_interp_spline(x_unique, y_smooth_pre, k=3)
                            y_smooth = spl(x_smooth)
                            
                            # Tracer la courbe lissée
                            ax1.plot(x_smooth, y_smooth, 
                                    color=colors_years[i], linewidth=3, 
                                    label=f'{year}', alpha=0.9, zorder=2)
                        except:
                            # Si l'interpolation échoue, utiliser Savitzky-Golay
                            smooth = smooth_timeseries(year_data['date'], year_data['albedo_mean'], 
                                                     method='savgol', window=15)
                            ax1.plot(days_from_june, smooth, 
                                    color=colors_years[i], linewidth=2.5, 
                                    label=f'{year}', alpha=0.8, zorder=2)
                else:
                    # Pas assez de données pour un lissage sophistiqué
                    ax1.plot(days_from_june, year_data['albedo_mean'], 
                            color=colors_years[i], linewidth=2, 
                            label=f'{year}', alpha=0.7, zorder=2)
            else:
                # Très peu de données, tracer tel quel
                ax1.plot(days_from_june, year_data['albedo_mean'], 
                        color=colors_years[i], linewidth=2, 
                        label=f'{year}', alpha=0.7, marker='o', markersize=4, zorder=2)
    
    ax1.set_xlabel('Jours depuis le 1er juin', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Albédo', fontsize=12, fontweight='bold')
    ax1.set_title('Évolution de l\'albédo durant la saison de fonte (Juin-Septembre)', 
                  fontsize=14, fontweight='bold')
    ax1.legend(ncol=len(years)//2 + 1, loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(-5, 125)  # Juin à fin septembre (~120 jours)
    
    # Marquer les mois
    month_starts = [0, 30, 61, 92]  # Début juin, juillet, août, septembre
    month_labels = ['Juin', 'Juillet', 'Août', 'Septembre']
    for start, label in zip(month_starts, month_labels):
        ax1.axvline(start, color='gray', linestyle='--', alpha=0.3)
        ax1.text(start + 15, ax1.get_ylim()[1]*0.02, label, 
                ha='center', va='bottom', fontsize=9, alpha=0.7)
    
    # 2. Statistiques annuelles
    ax2 = fig.add_subplot(gs[1, 0])
    
    years_list = sorted(melt_stats.keys())
    means = [melt_stats[y]['mean'] for y in years_list]
    stds = [melt_stats[y]['std'] for y in years_list]
    
    ax2.errorbar(years_list, means, yerr=stds, fmt='bo-', capsize=5, 
                linewidth=2, markersize=8)
    
    # Tendance
    if len(years_list) > 2:
        z = np.polyfit(years_list, means, 1)
        p = np.poly1d(z)
        ax2.plot(years_list, p(years_list), 'r--', linewidth=2,
                label=f'Tendance: {z[0]:.4f}/an')
    
    ax2.set_xlabel('Année', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Albédo moyen (juin-sept)', fontsize=11, fontweight='bold')
    ax2.set_title('Moyennes annuelles de la saison de fonte', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Amplitude de variation annuelle
    ax3 = fig.add_subplot(gs[1, 1])
    
    ranges = [melt_stats[y]['max'] - melt_stats[y]['min'] for y in years_list]
    bars = ax3.bar(years_list, ranges, color='coral', alpha=0.7, edgecolor='black')
    
    # Colorier selon l'amplitude
    for i, (bar, range_val) in enumerate(zip(bars, ranges)):
        if range_val > np.mean(ranges) + np.std(ranges):
            bar.set_color('darkred')
            bar.set_alpha(0.8)
    
    ax3.set_xlabel('Année', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Amplitude (max - min)', fontsize=11, fontweight='bold')
    ax3.set_title('Variabilité intra-saisonnière', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Timing du minimum d'albédo
    ax4 = fig.add_subplot(gs[2, 0])
    
    min_days = []
    for year in years_list:
        min_date = melt_stats[year]['min_date']
        june_1 = pd.Timestamp(f'{year}-06-01')
        days_from_june = (min_date - june_1).days
        min_days.append(days_from_june)
    
    ax4.scatter(years_list, min_days, s=100, c='darkblue', alpha=0.7, edgecolors='black')
    
    # Tendance du timing
    if len(years_list) > 2:
        z_timing = np.polyfit(years_list, min_days, 1)
        p_timing = np.poly1d(z_timing)
        ax4.plot(years_list, p_timing(years_list), 'b--', linewidth=1.5,
                label=f'Tendance: {z_timing[0]:.2f} jours/an')
    
    ax4.set_xlabel('Année', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Jours depuis le 1er juin', fontsize=11, fontweight='bold')
    ax4.set_title('Date du minimum d\'albédo', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Marquer les mois sur l'axe Y
    ax4.set_yticks([0, 30, 61, 92])
    ax4.set_yticklabels(['1 juin', '1 juillet', '1 août', '1 sept'])
    
    # 5. Taux de changement journalier
    ax5 = fig.add_subplot(gs[2, 1])
    
    trends_daily = []
    years_with_trends = []
    for year in years_list:
        if melt_stats[year]['trend'] is not None:
            trends_daily.append(melt_stats[year]['trend'] * 1000)  # Convertir en 10^-3/jour
            years_with_trends.append(year)
    
    if trends_daily:
        bars = ax5.bar(years_with_trends, trends_daily, color='steelblue', alpha=0.7, edgecolor='black')
        
        # Colorier les barres négatives différemment
        for bar, trend in zip(bars, trends_daily):
            if trend < 0:
                bar.set_color('darkred')
        
        ax5.axhline(0, color='black', linewidth=0.5)
        ax5.set_xlabel('Année', fontsize=11, fontweight='bold')
        ax5.set_ylabel('Taux de changement (×10⁻³/jour)', fontsize=11, fontweight='bold')
        ax5.set_title('Taux de diminution de l\'albédo', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3, axis='y')
    
    # Titre général
    fig.suptitle(f'Analyse de la saison de fonte - Glacier Athabasca{title}', 
                fontsize=16, fontweight='bold', y=0.98)
    
    # Ajustement
    plt.tight_layout()
    
    # Sauvegarder
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Graphique de fonte sauvegardé: {save_path}")
    
    plt.show()
    return fig