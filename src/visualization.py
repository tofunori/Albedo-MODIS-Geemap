"""
Visualization functions for MODIS albedo analysis
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from data_processing import smooth_timeseries
from config import FIRE_YEARS
from paths import get_figure_path

# ================================================================================
# ENHANCED EVOLUTION PLOT
# ================================================================================

def plot_albedo_evolution_enhanced(df, title="", smoothing_method='rolling', save_path=None):
    """
    Graphique d'évolution temporelle amélioré avec style moderne
    """
    if df.empty:
        print("❌ Aucune donnée à visualiser")
        return None
    
    # Style moderne
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Couleurs personnalisées
    colors = {
        'raw': '#B0BEC5',      # Gris bleu clair
        'smooth_7d': '#2196F3', # Bleu
        'smooth_30d': '#F44336', # Rouge
        'fill': '#FFCDD2',      # Rouge très clair
        'grid': '#E0E0E0'       # Gris clair
    }
    
    # Trier les données
    df_sorted = df.sort_values('date').copy()
    
    # 1. Données brutes
    ax.scatter(df_sorted['date'], df_sorted['albedo_mean'], 
              alpha=0.2, s=8, color=colors['raw'], label='Données quotidiennes', 
              edgecolors='none', rasterized=True)
    
    # 2. Lissages
    smooth_7d = smooth_timeseries(df_sorted['date'], df_sorted['albedo_mean'], 
                                  method='rolling', window=7)
    smooth_30d = smooth_timeseries(df_sorted['date'], df_sorted['albedo_mean'], 
                                   method=smoothing_method, window=30)
    
    # Tracer les courbes
    ax.plot(df_sorted['date'], smooth_7d, 
           color=colors['smooth_7d'], linewidth=1.5, alpha=0.7, 
           label='Moyenne 7 jours')
    ax.plot(df_sorted['date'], smooth_30d, 
           color=colors['smooth_30d'], linewidth=3, 
           label=f'Tendance 30 jours ({smoothing_method})')
    
    # 3. Bande d'incertitude
    if 'albedo_stdDev' in df_sorted.columns:
        std_smooth = smooth_timeseries(df_sorted['date'], df_sorted['albedo_stdDev'], 
                                      method='rolling', window=30)
        ax.fill_between(df_sorted['date'], 
                       smooth_30d - std_smooth,
                       smooth_30d + std_smooth,
                       alpha=0.15, color=colors['smooth_30d'], 
                       label='Intervalle de confiance (±1σ)')
    
    # 4. Annotations pour les saisons
    years = df_sorted['year'].unique()
    for year in years:
        # Marquer le début de chaque été (juin)
        summer_date = pd.Timestamp(f'{year}-06-01')
        if summer_date >= df_sorted['date'].min() and summer_date <= df_sorted['date'].max():
            ax.axvline(summer_date, color='orange', alpha=0.3, linestyle='--', linewidth=0.8)
            ax.text(summer_date, ax.get_ylim()[1]*0.98, 'Été', 
                   rotation=0, ha='center', va='top', fontsize=8, alpha=0.7)
    
    # 5. Marquer les années de feux majeurs
    for year, label in FIRE_YEARS.items():
        if year in years:
            # Zone ombrée pour l'année de feu
            year_start = pd.Timestamp(f'{year}-01-01')
            year_end = pd.Timestamp(f'{year}-12-31')
            ax.axvspan(year_start, year_end, alpha=0.1, color='red', zorder=0)
            # Étiquette
            mid_year = pd.Timestamp(f'{year}-07-01')
            if mid_year >= df_sorted['date'].min() and mid_year <= df_sorted['date'].max():
                ax.text(mid_year, ax.get_ylim()[0] + 0.02, label, 
                       rotation=90, ha='center', va='bottom', fontsize=9, 
                       color='darkred', alpha=0.7)
    
    # 6. Statistiques dans le graphique
    mean_albedo = df_sorted['albedo_mean'].mean()
    ax.axhline(mean_albedo, color='black', linestyle=':', alpha=0.5, linewidth=1)
    ax.text(df_sorted['date'].iloc[-1], mean_albedo, f'  Moyenne: {mean_albedo:.3f}', 
           va='center', ha='left', fontsize=10)
    
    # 7. Tendance linéaire globale
    if len(df_sorted) > 10:
        x_numeric = pd.to_numeric(df_sorted['date']) / 1e11  # Normaliser pour la régression
        z = np.polyfit(x_numeric, df_sorted['albedo_mean'], 1)
        p = np.poly1d(z)
        trend_line = p(x_numeric)
        ax.plot(df_sorted['date'], trend_line, 'k--', alpha=0.5, linewidth=2,
               label=f'Tendance: {z[0]*365.25/10:.4f}/an')
    
    # Mise en forme
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Albédo', fontsize=12, fontweight='bold')
    ax.set_title(f'Évolution de l\'albédo du glacier Athabasca{title}', 
                fontsize=16, fontweight='bold', pad=20)
    
    # Limites et grille
    ax.set_ylim(bottom=0, top=max(df_sorted['albedo_mean'].max() * 1.1, 1.0))
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Légende
    ax.legend(loc='upper left', frameon=True, fancybox=True, 
             shadow=True, fontsize=10, ncol=2)
    
    # Format des dates sur l'axe X
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator([4, 7, 10]))
    
    # Rotation des labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
    
    # Ajustement final
    plt.tight_layout()
    
    # Sauvegarder si demandé
    if save_path:
        fig_path = get_figure_path(save_path, category='evolution')
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"💾 Graphique sauvegardé: {fig_path}")
    
    plt.show()
    return fig

# ================================================================================
# FAST PLOTTING FUNCTION
# ================================================================================

def plot_albedo_fast(df, title_suffix="", smoothing_method='rolling'):
    """Graphiques simplifiés pour glacier entier"""
    if df.empty:
        print("❌ Aucune donnée à visualiser")
        return None
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Glacier Athabasca - Analyse Albédo{title_suffix}', 
                 fontsize=14, fontweight='bold')
    
    # 1. Série temporelle avec bande d'erreur et lissage
    # Trier les données par date
    df_sorted = df.sort_values('date').copy()
    
    # Données brutes en points transparents
    axes[0,0].scatter(df_sorted['date'], df_sorted['albedo_mean'], 
                     alpha=0.3, s=15, color='gray', label='Données brutes', zorder=1)
    
    # Appliquer différents lissages
    # Lissage court terme (7 jours)
    smooth_7d = smooth_timeseries(df_sorted['date'], df_sorted['albedo_mean'], 
                                  method='rolling', window=7)
    
    # Lissage moyen terme (30 jours) 
    smooth_30d = smooth_timeseries(df_sorted['date'], df_sorted['albedo_mean'], 
                                   method=smoothing_method, window=30)
    
    # Tracer les courbes lissées
    axes[0,0].plot(df_sorted['date'], smooth_7d, 
                  'b-', label='Moyenne mobile 7 jours', linewidth=1.2, alpha=0.7, zorder=2)
    axes[0,0].plot(df_sorted['date'], smooth_30d, 
                  'r-', label=f'Lissage 30 jours ({smoothing_method})', linewidth=2.5, zorder=3)
    
    # Bande d'incertitude lissée
    if 'albedo_stdDev' in df_sorted.columns:
        std_smooth = smooth_timeseries(df_sorted['date'], df_sorted['albedo_stdDev'], 
                                      method='rolling', window=30)
        axes[0,0].fill_between(df_sorted['date'], 
                             smooth_30d - std_smooth,
                             smooth_30d + std_smooth,
                             alpha=0.15, color='red', label='± 1 écart-type (lissé)', zorder=0)
    
    # Mise en forme
    axes[0,0].set_title('Évolution temporelle de l\'albédo', fontsize=12, fontweight='bold')
    axes[0,0].set_ylabel('Albédo', fontsize=11)
    axes[0,0].set_xlabel('Date', fontsize=11)
    axes[0,0].legend(loc='best', fontsize=9)
    axes[0,0].grid(True, alpha=0.3, linestyle='--')
    axes[0,0].set_ylim(bottom=0)  # L'albédo ne peut pas être négatif
    
    # 2. Tendances annuelles avec régression
    annual_stats = df.groupby('year').agg({
        'albedo_mean': ['mean', 'std', 'count']
    }).reset_index()
    annual_stats.columns = ['year', 'mean', 'std', 'count']
    
    if len(annual_stats) > 1:
        axes[0,1].errorbar(annual_stats['year'], annual_stats['mean'], 
                          yerr=annual_stats['std'], fmt='bo-', capsize=5,
                          label='Moyenne annuelle ± écart-type')
        
        # Tendance linéaire
        if len(annual_stats) > 2:
            z = np.polyfit(annual_stats['year'], annual_stats['mean'], 1)
            p = np.poly1d(z)
            axes[0,1].plot(annual_stats['year'], p(annual_stats['year']), 'r--', 
                          alpha=0.7, label=f'Tendance: {z[0]:.4f}/an')
            
            # Calcul R²
            yhat = p(annual_stats['year'])
            ybar = np.mean(annual_stats['mean'])
            ssreg = np.sum((yhat - ybar)**2)
            sstot = np.sum((annual_stats['mean'] - ybar)**2)
            r2 = ssreg / sstot if sstot > 0 else 0
            axes[0,1].text(0.05, 0.95, f'R² = {r2:.3f}', transform=axes[0,1].transAxes,
                          verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    axes[0,1].set_title('Moyennes annuelles et tendance')
    axes[0,1].set_xlabel('Année')
    axes[0,1].set_ylabel('Albédo moyen')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # 3. Cycle saisonnier
    seasonal_stats = df.groupby('month').agg({
        'albedo_mean': ['mean', 'std', 'count']
    }).reset_index()
    
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
              'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    
    axes[1,0].errorbar(seasonal_stats['month'], 
                      seasonal_stats[('albedo_mean', 'mean')],
                      yerr=seasonal_stats[('albedo_mean', 'std')],
                      fmt='bo-', capsize=5, linewidth=2)
    axes[1,0].set_title('Cycle saisonnier moyen')
    axes[1,0].set_xlabel('Mois')
    axes[1,0].set_ylabel('Albédo')
    axes[1,0].set_xticks(range(1, 13))
    axes[1,0].set_xticklabels(months, rotation=45)
    axes[1,0].grid(True, alpha=0.3)
    
    # 4. Distribution par saison avec statistiques
    season_order = ['Hiver', 'Printemps', 'Été', 'Automne']
    df_season = df[df['season'].isin(season_order)]
    
    if not df_season.empty:
        box_plot = sns.boxplot(data=df_season, x='season', y='albedo_mean', 
                              order=season_order, ax=axes[1,1])
        
        # Ajouter les moyennes
        means = df_season.groupby('season')['albedo_mean'].mean()
        positions = range(len(season_order))
        for pos, season in enumerate(season_order):
            if season in means.index:
                axes[1,1].text(pos, means[season], f'{means[season]:.3f}', 
                             ha='center', va='bottom', fontsize=10)
        
        axes[1,1].set_title('Distribution saisonnière')
        axes[1,1].set_xlabel('Saison')
        axes[1,1].set_ylabel('Albédo')
    
    plt.tight_layout()
    plt.show()
    
    return fig