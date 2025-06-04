import ee
import geemap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import folium

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

# Coordonnées précises glacier Athabasca (Alberta, Canada)
ATHABASCA_COORDS = [
    [-117.270, 52.198],  # SW
    [-117.220, 52.198],  # SE  
    [-117.220, 52.230],  # NE
    [-117.270, 52.230],  # NW
    [-117.270, 52.198]   # Fermer polygone
]

# Zone d'intérêt
athabasca_roi = ee.Geometry.Polygon(ATHABASCA_COORDS)

# Station météo sur le glacier
ATHABASCA_STATION = [-117.245, 52.214]
station_point = ee.Geometry.Point(ATHABASCA_STATION)

# ================================================================================
# PARAMÈTRES D'OPTIMISATION
# ================================================================================

# Option 1: Période réduite (dernières années + années feux)
PERIODS_RAPIDE = {
    'recent': ('2020-01-01', '2024-12-31'),  # 5 ans récents
    'fire_years': ('2017-01-01', '2021-12-31'),  # Années feux + context
    'decade': ('2015-01-01', '2024-12-31'),  # Dernière décennie
    'sample': ('2010-01-01', '2024-12-31')  # 15 ans avec échantillonnage
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
    Version rapide - statistiques simples par zone d'élévation
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
    
    # DEM pour zones d'élévation
    dem = ee.Image('USGS/SRTMGL1_003').clip(athabasca_roi)
    median_elevation = dem.reduceRegion(
        reducer=ee.Reducer.median(),
        geometry=athabasca_roi,
        scale=scale,
        maxPixels=1e9
    ).get('elevation')
    
    # Masques d'élévation simplifiés
    above_median = dem.gt(ee.Number(median_elevation))
    below_median = dem.lte(ee.Number(median_elevation))
    
    def calculate_simple_stats(image):
        """Calculs simplifiés - seulement 2 zones"""
        albedo = image.select(albedo_band)
        
        # Stats zone haute (accumulation)
        stats_above = albedo.updateMask(above_median).reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=scale,
            maxPixels=1e9
        )
        
        # Stats zone basse (ablation)
        stats_below = albedo.updateMask(below_median).reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.count(),
                sharedInputs=True
            ),
            geometry=athabasca_roi,
            scale=scale,
            maxPixels=1e9
        )
        
        # Stats glacier complet
        stats_total = albedo.reduceRegion(
            reducer=ee.Reducer.mean().combine(
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
            'albedo_above': stats_above.get(f'{albedo_band}_mean'),
            'count_above': stats_above.get(f'{albedo_band}_count'),
            'albedo_below': stats_below.get(f'{albedo_band}_mean'),
            'count_below': stats_below.get(f'{albedo_band}_count'),
            'albedo_total': stats_total.get(f'{albedo_band}_mean'),
            'count_total': stats_total.get(f'{albedo_band}_count'),
            'median_elevation': median_elevation
        })
    
    # Traitement collection
    time_series = collection.map(calculate_simple_stats)
    
    # Conversion DataFrame
    try:
        data_list = time_series.getInfo()['features']
        records = [f['properties'] for f in data_list if f['properties'].get('albedo_total')]
        
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
        
        print(f"✅ Extraction rapide terminée: {len(df)} observations")
        return df
        
    except Exception as e:
        print(f"❌ Erreur extraction: {e}")
        return pd.DataFrame()

# ================================================================================
# VISUALISATION RAPIDE
# ================================================================================

def plot_albedo_fast(df, title_suffix=""):
    """Graphiques rapides essentiels"""
    if df.empty:
        print("❌ Aucune donnée à visualiser")
        return None
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Glacier Athabasca - Analyse Rapide{title_suffix}', 
                 fontsize=14, fontweight='bold')
    
    # 1. Série temporelle zones élévation
    axes[0,0].plot(df['date'], df['albedo_above'], 'b-', label='Zone Haute', linewidth=1.5)
    axes[0,0].plot(df['date'], df['albedo_below'], 'r-', label='Zone Basse', linewidth=1.5)
    axes[0,0].plot(df['date'], df['albedo_total'], 'k--', label='Glacier Total', alpha=0.7)
    axes[0,0].set_title('Évolution Albédo par Zone')
    axes[0,0].set_ylabel('Albédo')
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # 2. Tendances annuelles
    annual_stats = df.groupby('year').agg({
        'albedo_above': 'mean',
        'albedo_below': 'mean',
        'albedo_total': 'mean'
    }).reset_index()
    
    if len(annual_stats) > 1:
        axes[0,1].plot(annual_stats['year'], annual_stats['albedo_above'], 'bo-', label='Zone Haute')
        axes[0,1].plot(annual_stats['year'], annual_stats['albedo_below'], 'ro-', label='Zone Basse')
        axes[0,1].plot(annual_stats['year'], annual_stats['albedo_total'], 'ko-', label='Total')
        
        # Tendance linéaire zone haute
        if len(annual_stats) > 2:
            z = np.polyfit(annual_stats['year'], annual_stats['albedo_above'], 1)
            p = np.poly1d(z)
            axes[0,1].plot(annual_stats['year'], p(annual_stats['year']), 'b--', alpha=0.7,
                          label=f'Tendance: {z[0]:.4f}/an')
    
    axes[0,1].set_title('Moyennes Annuelles')
    axes[0,1].set_xlabel('Année')
    axes[0,1].set_ylabel('Albédo Moyen')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # 3. Cycle saisonnier
    seasonal_stats = df.groupby('month').agg({
        'albedo_above': ['mean', 'std'],
        'albedo_total': ['mean', 'std']
    }).reset_index()
    
    months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
              'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    
    axes[1,0].plot(seasonal_stats['month'], seasonal_stats[('albedo_above', 'mean')], 
                  'bo-', label='Zone Haute', linewidth=2)
    axes[1,0].fill_between(seasonal_stats['month'],
                          seasonal_stats[('albedo_above', 'mean')] - seasonal_stats[('albedo_above', 'std')],
                          seasonal_stats[('albedo_above', 'mean')] + seasonal_stats[('albedo_above', 'std')],
                          alpha=0.3, color='blue')
    
    axes[1,0].set_title('Cycle Saisonnier Zone Haute')
    axes[1,0].set_xlabel('Mois')
    axes[1,0].set_ylabel('Albédo')
    axes[1,0].set_xticks(range(1, 13))
    axes[1,0].set_xticklabels(months, rotation=45)
    axes[1,0].grid(True, alpha=0.3)
    
    # 4. Distribution par saison
    season_order = ['Hiver', 'Printemps', 'Été', 'Automne']
    df_season = df[df['season'].isin(season_order)]
    
    if not df_season.empty:
        sns.boxplot(data=df_season, x='season', y='albedo_above', 
                   order=season_order, ax=axes[1,1])
        axes[1,1].set_title('Distribution Saisonnière Zone Haute')
        axes[1,1].set_xlabel('Saison')
        axes[1,1].set_ylabel('Albédo')
    
    plt.tight_layout()
    plt.show()
    
    return fig

# ================================================================================
# FONCTION PRINCIPALE AVEC OPTIONS
# ================================================================================

def run_analysis_optimized(period='recent', sampling=None, scale=500, use_broadband=False):
    """
    Fonction principale avec options d'optimisation
    
    Args:
        period: 'recent', 'fire_years', 'decade', 'sample', ou tuple (start, end)
        sampling: None, 'weekly', 'monthly', 'seasonal'
        scale: 250, 500, 1000 (résolution en mètres)
        use_broadband: False (neige) ou True (large bande)
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
    
    if 'albedo_above' in df.columns:
        zone_data = df['albedo_above'].dropna()
        if not zone_data.empty:
            print(f"   • Albédo moyen zone haute: {zone_data.mean():.3f} ± {zone_data.std():.3f}")
            print(f"   • Tendance annuelle: ", end="")
            
            annual_mean = df.groupby('year')['albedo_above'].mean()
            if len(annual_mean) > 2:
                trend = np.polyfit(annual_mean.index, annual_mean.values, 1)[0]
                print(f"{trend:.4f}/an")
            else:
                print("Insuffisant pour calcul")
    
    # Visualisation
    print(f"\n📊 Génération graphiques...")
    plot_albedo_fast(df, f" - {period_name}")
    
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
    
    # Recommandation par défaut: OPTION 2 - RAPIDE
    print(f"\n🎯 EXÉCUTION OPTION 2 (RAPIDE)...")
    df_result = run_analysis_optimized(
        period='fire_years',    # 2017-2021
        sampling=None,          # Toutes images disponibles
        scale=500,              # Résolution MODIS standard
        use_broadband=False     # Albédo neige quotidien
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