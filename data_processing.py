"""
Fonctions de traitement et extraction des données MODIS
"""
import ee
import pandas as pd
import numpy as np
from config import athabasca_roi, MODIS_COLLECTIONS

# ================================================================================
# FONCTIONS DE MASQUAGE MODIS
# ================================================================================

def mask_modis_snow_albedo_fast(image):
    """Version simplifiée du masquage pour vitesse"""
    # Sélection rapide - moins de contrôles qualité
    albedo = image.select('Snow_Albedo_Daily_Tile')
    qa = image.select('NDSI_Snow_Cover_Basic_QA')
    
    # Masque basique
    valid_albedo = albedo.gte(5).And(albedo.lte(99))
    good_quality = qa.lte(1)  # Meilleure et bonne qualité
    
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
# EXTRACTION DES SÉRIES TEMPORELLES
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
        collection = ee.ImageCollection(MODIS_COLLECTIONS['broadband']) \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date) \
            .map(mask_modis_broadband_albedo_fast)
        albedo_band = 'albedo_broadband'
    else:
        # Combiner MOD10A1 et MYD10A1 (Version 6.1)
        mod_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_terra']) \
            .filterBounds(athabasca_roi) \
            .filterDate(start_date, end_date) \
            .map(mask_modis_snow_albedo_fast)
        
        myd_col = ee.ImageCollection(MODIS_COLLECTIONS['snow_aqua']) \
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
    from scipy.interpolate import UnivariateSpline
    from scipy.signal import savgol_filter
    
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