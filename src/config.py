"""
Configuration file for Athabasca Glacier analysis
Contains region of interest and other global parameters
"""

import ee
import json
import os

# Initialize Earth Engine (if not already done)
try:
    ee.Initialize()
except:
    pass

# ================================================================================
# CONFIGURATION GLACIER
# ================================================================================

# Charger le masque du glacier Athabasca (priorité au shapefile)
geojson_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'geospatial', 'masks', 'Athabasca_mask_2023_cut.geojson')
shapefile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'geospatial', 'shapefiles', 'Masque_athabasca_2023_Arcgis.shp')

# Vérifier la disponibilité du nouveau shapefile
if os.path.exists(shapefile_path):
    print(f"📂 Nouveau shapefile trouvé: {os.path.basename(shapefile_path)}")
    use_shapefile = True
    mask_path = shapefile_path
else:
    print(f"📂 Nouveau shapefile non trouvé, utilisation du GeoJSON: {os.path.basename(geojson_path)}")
    use_shapefile = False
    mask_path = geojson_path
    # Charger le GeoJSON si on l'utilise
    with open(geojson_path, 'r') as f:
        athabasca_geojson = json.load(f)

if use_shapefile:
    # Lecture du shapefile avec geopandas
    try:
        import geopandas as gpd
        print("🔧 Lecture du shapefile avec geopandas...")
        
        # Lire le shapefile
        gdf = gpd.read_file(shapefile_path)
        print(f"📊 Shapefile info: {len(gdf)} features, CRS: {gdf.crs}")
        
        # Convertir en WGS84 si nécessaire
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            print(f"🔄 Reprojection vers WGS84...")
            gdf = gdf.to_crs(4326)
        
        # Calculer la surface totale
        # Utiliser une projection équivalente d'aire pour le calcul (UTM ou Albers)
        gdf_area = gdf.to_crs('EPSG:3857')  # Web Mercator pour approximation
        total_area_m2 = gdf_area.geometry.area.sum()
        total_area_km2 = total_area_m2 / 1e6
        
        print(f"📏 Surface totale du shapefile: {total_area_km2:.2f} km²")
        
        # Simplifier si plusieurs features
        if len(gdf) > 1:
            print("🔗 Union de plusieurs features...")
            unified_geom = gdf.geometry.unary_union
        else:
            unified_geom = gdf.geometry.iloc[0]
        
        # Convertir en coordonnées pour Earth Engine
        if hasattr(unified_geom, 'geoms'):
            # MultiPolygon
            geometries = []
            for geom in unified_geom.geoms:
                if geom.geom_type == 'Polygon':
                    coords = [list(geom.exterior.coords)]
                    geometries.append(ee.Geometry.Polygon(coords))
            athabasca_roi = ee.FeatureCollection(geometries).geometry()
        else:
            # Polygon simple
            coords = [list(unified_geom.exterior.coords)]
            athabasca_roi = ee.Geometry.Polygon(coords)
        
        print(f"✅ Shapefile chargé avec succès dans Earth Engine")
        
    except ImportError:
        print("❌ geopandas non disponible, fallback vers GeoJSON")
        use_shapefile = False
        with open(geojson_path, 'r') as f:
            athabasca_geojson = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture shapefile: {e}")
        print("🔄 Fallback vers GeoJSON")
        use_shapefile = False
        with open(geojson_path, 'r') as f:
            athabasca_geojson = json.load(f)

if not use_shapefile:
    # Convertir le GeoJSON en geometry Earth Engine
    # IMPORTANT: Utiliser seulement le premier polygone comme dans Streamlit
    # Cela donne le bon nombre de pixels (~20 au lieu de 40)
    
    if athabasca_geojson['features']:
        first_feature = athabasca_geojson['features'][0]
        geometry = first_feature['geometry']
        
        # Prendre seulement le premier polygone des coordonnées
        if geometry['type'] == 'MultiPolygon':
            # Pour MultiPolygon, prendre le premier polygone
            coords = geometry['coordinates'][0]
            athabasca_roi = ee.Geometry.Polygon(coords)
            print(f"📊 Utilisation du premier polygone du MultiPolygon (méthode Streamlit)")
        elif geometry['type'] == 'Polygon':
            # Pour Polygon simple
            coords = geometry['coordinates']
            athabasca_roi = ee.Geometry.Polygon(coords)
            print(f"📊 Utilisation du polygone simple")
        
        # Info sur la feature
        count = first_feature['properties'].get('count', 0)
        print(f"🧮 Feature properties: count={count}")
    else:
        raise ValueError("Aucune feature trouvée dans le GeoJSON")

# Station météo sur le glacier
ATHABASCA_STATION = [-117.245, 52.214]
station_point = ee.Geometry.Point(ATHABASCA_STATION)

# ================================================================================
# PARAMÈTRES D'ANALYSE
# ================================================================================

# Périodes prédéfinies
PERIODS_RAPIDE = {
    'recent': ('2020-01-01', '2024-10-31'),      # 5 ans récents
    'fire_years': ('2017-01-01', '2021-12-31'),  # Années feux + contexte
    'decade': ('2010-01-01', '2024-10-31'),      # Dernière décennie
    'sample': ('2010-01-01', '2024-10-31'),      # 15 ans avec échantillonnage
    'full_recent': ('2019-01-01', '2024-10-31')  # 6 ans pour mieux voir les tendances
}

# Options d'échantillonnage temporel
SAMPLING_OPTIONS = {
    'weekly': 7,       # Une image par semaine
    'monthly': 30,     # Une image par mois
    'seasonal': 90     # Une image par saison
}

# Options de résolution spatiale
SCALE_OPTIONS = {
    'fine': 250,       # Résolution native MODIS (lent)
    'medium': 500,     # Compromis (recommandé)
    'coarse': 1000     # Rapide pour tests
}

# Années de feux majeurs pour annotations
FIRE_YEARS = {
    2017: "Feux BC",
    2018: "Feux BC", 
    2019: "Feux AB",
    2020: "Feux CA/US",
    2023: "Feux record"
}

# ================================================================================
# PRODUITS MODIS
# ================================================================================

# Collections MODIS Version 6.1 (061)
MODIS_COLLECTIONS = {
    'snow_terra': 'MODIS/061/MOD10A1',    # Terra Snow Cover
    'snow_aqua': 'MODIS/061/MYD10A1',     # Aqua Snow Cover
    'broadband': 'MODIS/061/MCD43A3'      # Combined BRDF/Albedo
}

# Calcul et affichage de la surface du glacier
try:
    glacier_area = athabasca_roi.area().divide(1e6).getInfo()  # Convertir en km²
    print(f"🏔️ Configuration Glacier Athabasca")
    print(f"📏 Surface du glacier: {glacier_area:.2f} km²")
except:
    print("🏔️ Configuration Glacier Athabasca")
    print("📏 Surface du glacier: calcul en cours...")

# Note: athabasca_roi is already loaded from the GeoJSON mask above
# Do not overwrite it with a simple bounding box!

# Default analysis parameters
DEFAULT_START_YEAR = 2010
DEFAULT_END_YEAR = 2024
DEFAULT_SCALE = 500  # meters
MELT_SEASON_MONTHS = [6, 7, 8, 9]  # June through September

# File paths
MASK_FILE = mask_path

# Fire years for Athabasca region (from literature and records)
FIRE_YEARS = [2017, 2018, 2023]  # Years with significant fire activity affecting albedo 