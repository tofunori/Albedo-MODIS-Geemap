import ee
import geemap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import folium
import json
from scipy.interpolate import UnivariateSpline
from scipy.signal import savgol_filter

# Initialiser Earth Engine
# ee.Authenticate()  # Exécuter une seule fois
ee.Initialize()

# ================================================================================
# CONFIGURATION OPTIMISÉE
# ================================================================================

# IMPORTANT: Utilisation des collections MODIS Version 6.1 (061)
# Les collections Version 6 (006) sont dépréciées depuis 2023
# Nouvelles collections:
# - MODIS/061/MOD10A1 (Terra Snow Cover)
# - MODIS/061/MYD10A1 (Aqua Snow Cover) 
# - MODIS/061/MCD43A3 (Combined BRDF/Albedo)

# Charger le masque GeoJSON précis du glacier Athabasca
with open('Athabasca_mask_2023 (1).geojson', 'r') as f:
    athabasca_geojson = json.load(f)

# Convertir le GeoJSON en geometry Earth Engine
# Le GeoJSON contient plusieurs features, on les combine
geometries = []
for feature in athabasca_geojson['features']:
    if feature['geometry']['type'] == 'MultiPolygon':
        for polygon in feature['geometry']['coordinates']:
            geometries.append(ee.Geometry.Polygon(polygon))
    elif feature['geometry']['type'] == 'Polygon':
        geometries.append(ee.Geometry.Polygon(feature['geometry']['coordinates']))

# Créer une collection de geometries et les unir
athabasca_roi = ee.FeatureCollection(geometries).geometry()

# Coordonnées pour la zone de visualisation (bounding box approximative)
ATHABASCA_BOUNDS = [
    [-117.32, 52.15],  # SW
    [-117.22, 52.15],  # SE  
    [-117.22, 52.22],  # NE
    [-117.32, 52.22],  # NW
    [-117.32, 52.15]   # Fermer polygone
]

# Station météo sur le glacier
ATHABASCA_STATION = [-117.245, 52.214]
station_point = ee.Geometry.Point(ATHABASCA_STATION)

# ================================================================================
# PARAMÈTRES D'OPTIMISATION
# ================================================================================

# Option 1: Période réduite (dernières années + années feux)
PERIODS_RAPIDE = {
    'recent': ('2020-01-01', '2024-10-31'),  # 5 ans récents jusqu'à automne 2024
    'fire_years': ('2017-01-01', '2021-12-31'),  # Années feux + context
    'decade': ('2015-01-01', '2024-10-31'),  # Dernière décennie
    'sample': ('2010-01-01', '2024-10-31'),  # 15 ans avec échantillonnage
    'full_recent': ('2019-01-01', '2024-10-31')  # 6 ans pour mieux voir les tendances
}

# Option 2: Échantillonnage temporel
SAMPLING_OPTIONS = {
    'weekly': 7,      # Une image par semaine
    'monthly': 30,    # Une image par mois
    'seasonal': 90    # Une image par saison
}

# Option 3: Résolution spatiale réduite
SCALE_OPTIONS = {
    'fine': 250,      # Résolution native MODIS (lent)
    'medium': 500,    # Compromis (recommandé)
    'coarse': 1000    # Rapide pour tests
}

print("🏔️ Configuration Optimisée Glacier Athabasca")

# Calculer et afficher la surface du glacier
glacier_area = athabasca_roi.area().divide(1e6).getInfo()  # Convertir en km²
print(f"📏 Surface du glacier (masque précis): {glacier_area:.2f} km²")

# ================================================================================
# FONCTIONS DE MASQUAGE SIMPLIFIÉES
# ================================================================================

def mask_modis_snow_albedo_fast(image):
    """Version simplifiée du masquage pour vitesse"""
    # Sélection rapide - moins de contrôles qualité
    albedo = image.select('Snow_Albedo_Daily_Tile')
    qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    # Masque basique
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    good_quality = qa.eq(0)  # Seulement meilleure qualité
    
    # Facteur échelle
    scaled = albedo.multiply(0.01).updateMask(valid_albedo.And(good_quality))
    
    return scaled.rename('albedo_daily').copyProperties(image, ['system:time_start'])

def mask_modis_broadband_albedo_fast(image):
    """Version simplifiée albédo large bande"""
    vis_albedo = image.select('Albedo_WSA_vis')
    nir_albedo = image.select('Albedo_WSA_nir')
    qa = image.select('BRDF_Albedo_Quality')
    
    # Masque simplifié
    good_quality = qa.lte(1)
    valid_vis = vis_albedo.gte(0).And(vis_albedo.lte(1000))
    valid_nir = nir_albedo.gte(0).And(nir_albedo.lte(1000))
    
    # Facteur échelle et calcul
    vis_scaled = vis_albedo.multiply(0.001).updateMask(good_quality.And(valid_vis))
    nir_scaled = nir_albedo.multiply(0.001).updateMask(good_quality.And(valid_nir))
    broadband = vis_scaled.multiply(0.7).add(nir_scaled.multiply(0.3))
    
    return broadband.rename('albedo_broadband').copyProperties(image, ['system:time_start'])

# ================================================================================
# EXTRACTION SIMPLIFIÉE
# ================================================================================

def extract_time_series_fast(start_date, end_date, 
                            use_broadband=False,
                            sampling_days=None,
                            scale=500):
    """
    Version simplifiée - statistiques pour le glacier entier sans division par zones
    """
    print(f"⚡ Extraction RAPIDE {start_date} à {end_date}")
    print(f"   Échantillonnage: {sampling_days} jours, Résolution: {scale}m")
    
    # Choisir collection et fonction masquage
    if use_broadband:
        collection = ee.ImageCollection('MODIS/061/MCD43A3') \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date) \
            .map(mask_modis_broadband_albedo_fast)
        albedo_band = 'albedo_broadband'
    else:
        # Combiner MOD10A1 et MYD10A1 (Version 6.1)
        mod_col = ee.ImageCollection('MODIS/061/MOD10A1') \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date) \
            .map(mask_modis_snow_albedo_fast)
        
        myd_col = ee.ImageCollection('MODIS/061/MYD10A1') \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date) \
            .map(mask_modis_snow_albedo_fast)
        
        collection = mod_col.merge(myd_col).sort('system:time_start')
        albedo_band = 'albedo_daily'
    
    # Échantillonnage temporel si spécifié
    if sampling_days:
        # Prendre seulement certaines images pour réduire la charge
        collection = collection.filterMetadata('system:index', 'not_equals', '') \
            .limit(1000)  # Limite pour éviter timeout
    
    print(f"📡 Images à traiter: {collection.size().getInfo()}")
    
    def calculate_simple_stats(image):
        """Calculs simplifiés - glacier entier seulement"""
        albedo = image.select(albedo_band)
        
        # Stats glacier complet avec plusieurs métriques
        stats = albedo.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.min(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.max(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=scale,
            maxPixels=1e9
        )
        
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'timestamp': image.date().millis(),
            'albedo_mean': stats.get(f'{albedo_band}_mean'),
            'albedo_stdDev': stats.get(f'{albedo_band}_stdDev'),
            'albedo_min': stats.get(f'{albedo_band}_min'),
            'albedo_max': stats.get(f'{albedo_band}_max'),
            'pixel_count': stats.get(f'{albedo_band}_count')
        })
    
    # Traitement collection
    time_series = collection.map(calculate_simple_stats)
    
    # Conversion DataFrame
    try:
        data_list = time_series.getInfo()['features']
        records = [f['properties'] for f in data_list if f['properties'].get('albedo_mean')]
        
        df = pd.DataFrame(records)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # Colonnes temporelles
            df['year'] = df['date'].dt.year
            df['month'] = df['date'].dt.month
            df['season'] = df['month'].map({
                12: 'Hiver', 1: 'Hiver', 2: 'Hiver',
                3: 'Printemps', 4: 'Printemps', 5: 'Printemps',
                6: 'Été', 7: 'Été', 8: 'Été',
                9: 'Automne', 10: 'Automne', 11: 'Automne'
            })
        
        print(f"✅ Extraction terminée: {len(df)} observations")
        return df
        
    except Exception as e:
        print(f"❌ Erreur extraction: {e}")
        return pd.DataFrame()

# ================================================================================
# FONCTIONS DE LISSAGE
# ================================================================================

def smooth_timeseries(dates, values, method='rolling', window=30):
    """
    Applique différentes méthodes de lissage aux données
    
    Args:
        dates: Series pandas de dates
        values: Series pandas de valeurs
        method: 'rolling', 'savgol', 'spline'
        window: taille de la fenêtre pour rolling et savgol
    
    Returns:
        Series pandas lissée
    """
    if method == 'rolling':
        return values.rolling(window=window, center=True, min_periods=1).mean()
    
    elif method == 'savgol':
        # Filtre Savitzky-Golay (préserve mieux les pics)
        if len(values) > window:
            return pd.Series(savgol_filter(values, window, 3), index=values.index)
        else:
            return values
    
    elif method == 'spline':
        # Interpolation par spline cubique
        # Convertir dates en nombres pour l'interpolation
        x = pd.to_numeric(dates)
        x_norm = (x - x.min()) / (x.max() - x.min())  # Normaliser pour stabilité
        
        # Supprimer les NaN
        mask = ~np.isnan(values)
        if mask.sum() > 3:  # Besoin d'au moins 4 points
            spl = UnivariateSpline(x_norm[mask], values[mask], s=0.1)
            return pd.Series(spl(x_norm), index=values.index)
        else:
            return values
    
    return values

# ================================================================================
# VISUALISATION AMÉLIORÉE
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
    fire_years = {
        2017: "Feux BC",
        2018: "Feux BC", 
        2019: "Feux AB",
        2020: "Feux CA/US",
        2023: "Feux record"
    }
    
    for year, label in fire_years.items():
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
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator([4, 7, 10]))
    
    # Rotation des labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
    
    # Ajustement final
    plt.tight_layout()
    
    # Sauvegarder si demandé
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Graphique sauvegardé: {save_path}")
    
    plt.show()
    return fig

# ================================================================================
# VISUALISATION RAPIDE
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

# ================================================================================
# FONCTION PRINCIPALE AVEC OPTIONS
# ================================================================================

def run_analysis_optimized(period='recent', sampling=None, scale=500, use_broadband=False, smoothing='rolling'):
    """
    Fonction principale avec options d'optimisation
    
    Args:
        period: 'recent', 'fire_years', 'decade', 'sample', ou tuple (start, end)
        sampling: None, 'weekly', 'monthly', 'seasonal'
        scale: 250, 500, 1000 (résolution en mètres)
        use_broadband: False (neige) ou True (large bande)
        smoothing: 'rolling', 'savgol', 'spline' (méthode de lissage)
    """
    
    print("🚀 ANALYSE OPTIMISÉE Albédo Glacier Athabasca")
    print("=" * 60)
    
    # Définir période
    if isinstance(period, tuple):
        start_date, end_date = period
        period_name = f"Personnalisée ({start_date} à {end_date})"
    else:
        start_date, end_date = PERIODS_RAPIDE[period]
        period_name = period.title()
    
    # Définir échantillonnage
    sampling_days = SAMPLING_OPTIONS.get(sampling) if sampling else None
    
    print(f"📅 Période: {period_name}")
    print(f"⏱️ Échantillonnage: {sampling or 'Toutes les images'}")
    print(f"🎯 Résolution: {scale}m")
    print(f"📊 Type données: {'Large bande (MCD43A3 v6.1)' if use_broadband else 'Neige quotidien (MOD/MYD10A1 v6.1)'}")
    
    # Extraction
    df = extract_time_series_fast(
        start_date, end_date,
        use_broadband=use_broadband,
        sampling_days=sampling_days,
        scale=scale
    )
    
    if df.empty:
        print("❌ Aucune donnée extraite")
        return None
    
    # Statistiques rapides
    print(f"\n📈 RÉSULTATS:")
    print(f"   • {len(df)} observations")
    print(f"   • Période effective: {df['date'].min()} à {df['date'].max()}")
    
    if 'albedo_mean' in df.columns:
        albedo_data = df['albedo_mean'].dropna()
        if not albedo_data.empty:
            print(f"   • Albédo moyen du glacier: {albedo_data.mean():.3f} ± {albedo_data.std():.3f}")
            print(f"   • Plage de valeurs: [{albedo_data.min():.3f}, {albedo_data.max():.3f}]")
            print(f"   • Tendance annuelle: ", end="")
            
            annual_mean = df.groupby('year')['albedo_mean'].mean()
            if len(annual_mean) > 2:
                trend = np.polyfit(annual_mean.index, annual_mean.values, 1)[0]
                print(f"{trend:.4f}/an")
            else:
                print("Insuffisant pour calcul")
    
    # Visualisation
    print(f"\n📊 Génération graphiques...")
    print(f"   • Méthode de lissage: {smoothing}")
    
    # Graphiques standard
    plot_albedo_fast(df, f" - {period_name}", smoothing_method=smoothing)
    
    # Graphique d'évolution amélioré
    print(f"\n📈 Génération graphique d'évolution détaillé...")
    plot_albedo_evolution_enhanced(df, f" ({period_name})", 
                                  smoothing_method=smoothing,
                                  save_path=f'evolution_albedo_{period}_{scale}m.png')
    
    # Export
    filename = f'athabasca_albedo_{period}_{scale}m.csv'
    df.to_csv(filename, index=False)
    print(f"💾 Données exportées: {filename}")
    
    return df

# ================================================================================
# EXEMPLES D'UTILISATION RAPIDE
# ================================================================================

if __name__ == "__main__":
    print("🎛️ OPTIONS D'ANALYSE RAPIDE:")
    print("\n1️⃣ ULTRA-RAPIDE (test): 5 ans récents, résolution 1km")
    print("2️⃣ RAPIDE: Années feux, résolution 500m")  
    print("3️⃣ STANDARD: Dernière décennie, résolution 500m")
    print("4️⃣ PERSONNALISÉ: Vos paramètres")
    
    # Recommandation par défaut: Période récente étendue jusqu'à automne 2024
    print(f"\n🎯 EXÉCUTION: Analyse récente complète (2019-Oct 2024)...")
    df_result = run_analysis_optimized(
        period='full_recent',   # 2019-2024 (automne)
        sampling=None,          # Toutes images disponibles
        scale=500,              # Résolution MODIS standard
        use_broadband=False,    # Albédo neige quotidien
        smoothing='savgol'      # Lissage Savitzky-Golay pour préserver les détails
    )
    
    print(f"\n✅ ANALYSE TERMINÉE!")
    print(f"💡 Pour d'autres options, modifiez les paramètres de run_analysis_optimized()")
    
    # Exemples autres configurations:
    print(f"\n🔧 AUTRES EXEMPLES:")
    print(f"# Ultra-rapide (test)")
    print(f"# run_analysis_optimized('recent', 'monthly', 1000)")
    print(f"")
    print(f"# Période personnalisée")
    print(f"# run_analysis_optimized(('2018-01-01', '2020-12-31'), None, 500)")
    print(f"")
    print(f"# Albédo large bande")
    print(f"# run_analysis_optimized('decade', 'weekly', 500, use_broadband=True)")