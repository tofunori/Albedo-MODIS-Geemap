"""
Configuration et paramètres pour l'analyse MODIS du glacier Athabasca
"""
import ee
import json

# Initialiser Earth Engine
ee.Initialize()

# ================================================================================
# CONFIGURATION GLACIER
# ================================================================================

# Charger le masque GeoJSON découpé du glacier Athabasca
with open('Athabasca_mask_2023_cut.geojson', 'r') as f:
    athabasca_geojson = json.load(f)

# Convertir le GeoJSON en geometry Earth Engine
geometries = []
for feature in athabasca_geojson['features']:
    if feature['geometry']['type'] == 'MultiPolygon':
        for polygon in feature['geometry']['coordinates']:
            geometries.append(ee.Geometry.Polygon(polygon))
    elif feature['geometry']['type'] == 'Polygon':
        geometries.append(ee.Geometry.Polygon(feature['geometry']['coordinates']))

# Créer une collection de geometries et les unir
athabasca_roi = ee.FeatureCollection(geometries).geometry()

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
    'decade': ('2015-01-01', '2024-10-31'),      # Dernière décennie
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