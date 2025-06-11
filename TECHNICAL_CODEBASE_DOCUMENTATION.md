# 🔧 Documentation Technique Complète - Codebase Albedo Athabasca

## 📖 Table des Matières
1. [Architecture Générale](#architecture-générale)
2. [Carte Interactive - Fonctions Essentielles](#carte-interactive---fonctions-essentielles)
3. [MOD10A1/MYD10A1 - Implémentation Complète](#mod10a1myd10a1---implémentation-complète)
4. [MCD43A3 - Implémentation Détaillée](#mcd43a3---implémentation-détaillée)
5. [Innovations Techniques](#innovations-techniques)
6. [Flux de Données](#flux-de-données)
7. [Fonctions Critiques](#fonctions-critiques)

---

## 🏗️ Architecture Générale

### **Structure du Projet**
```
streamlit_app/
├── streamlit_main.py              # Point d'entrée principal
├── src/
│   ├── dashboards/                # Interfaces utilisateur
│   │   ├── interactive_albedo_dashboard.py    # Carte interactive
│   │   ├── melt_season_dashboard.py          # MOD10A1 analysis
│   │   ├── mcd43a3_dashboard.py              # MCD43A3 analysis
│   │   └── homepage_dashboard.py             # Page d'accueil
│   ├── utils/
│   │   ├── maps.py                          # Visualisation cartes
│   │   ├── earth_engine/                    # Google Earth Engine
│   │   │   ├── modis_extraction.py         # Extraction données MODIS
│   │   │   ├── pixel_processing.py         # Traitement pixels
│   │   │   └── initialization.py           # Init Earth Engine
│   │   ├── data_loader.py                  # Chargement données
│   │   ├── qa_config.py                    # Configuration qualité
│   │   └── processing_manager.py           # Gestion traitements
│   └── workflows/                          # Analyses complètes
│       ├── melt_season.py                  # Workflow MOD10A1
│       ├── broadband_albedo.py             # Workflow MCD43A3
│       └── hypsometric.py                  # Analyse hypsométrique
```

---

## 🗺️ Carte Interactive - Fonctions Essentielles

### **📍 Point d'Entrée Principal**
**Fichier** : `streamlit_main.py`
```python
# Ligne 463: Sélection carte interactive
elif selected_dataset == "Interactive Albedo Map":
    create_interactive_albedo_dashboard(qa_config, selected_qa_level)
```

### **🎮 Interface Utilisateur Principale**
**Fichier** : `src/dashboards/interactive_albedo_dashboard.py`

#### **Fonction Maîtresse**
```python
def create_interactive_albedo_dashboard(qa_config=None, qa_level=None):
    """
    Ligne 11: Point d'entrée principal carte interactive
    
    Responsabilités:
    - Chargement données hypsométriques
    - Création contrôles sidebar
    - Gestion sélection dates
    - Affichage carte et statistiques
    """
```

#### **Contrôles Sidebar**
```python
def _create_sidebar_controls(qa_config, qa_level):
    """
    Ligne 59: Création interface de contrôle
    
    Innovations Implémentées:
    ✅ Default MCD43A3 (index=1, ligne 73)
    ✅ Default QA≤1 (index=1, ligne 195) 
    ✅ Diffuse fraction slider (lignes 100-122)
    ✅ Band selection pour MCD43A3
    ✅ Interprétation conditions atmosphériques
    
    Returns:
    - selected_product, qa_threshold, qa_option
    - use_advanced_qa, algorithm_flags, selected_band
    - diffuse_fraction ← NOTRE INNOVATION
    """
    
    # Contrôles Produit MODIS
    product_options = {
        "MOD10A1 (Daily Snow)": "MOD10A1",
        "MCD43A3 (Broadband)": "MCD43A3"
    }
    
    # DEFAULT: MCD43A3 sélectionné (ligne 73)
    selected_product_name = st.sidebar.radio(
        "MODIS Product:",
        list(product_options.keys()),
        index=1,  # ← MCD43A3 par défaut
        key="product_selector"
    )
    
    # Diffuse Fraction Innovation (lignes 100-122)
    if selected_product == "MCD43A3":
        diffuse_fraction = st.sidebar.slider(
            "Diffuse Fraction:",
            min_value=0.0,
            max_value=1.0,
            value=0.2,  # Default pour glaciers
            step=0.05,
            help="0.0 = Pure direct (clear sky)\\n0.2 = Typical glacier (default)\\n0.5 = Mixed conditions\\n1.0 = Pure diffuse (overcast)",
            key="diffuse_fraction_slider"
        )
        
        # Interprétation temps réel (lignes 111-120)
        if diffuse_fraction <= 0.15:
            condition = "☀️ Clear sky conditions"
        elif diffuse_fraction <= 0.35:
            condition = "🌤️ Typical glacier conditions"
        elif diffuse_fraction <= 0.65:
            condition = "⛅ Mixed sky conditions"
        else:
            condition = "☁️ Overcast conditions"
```

#### **Sélection de Dates**
```python
def _create_date_selection_interface(available_dates, use_pixel_analysis):
    """
    Ligne 392: Interface sélection dates
    └── _create_date_list_picker() (ligne 437)
        ├── Groupement par mois
        ├── Sélection hiérarchique
        └── Validation disponibilité données
    """
```

### **🗺️ Création & Affichage Carte**
**Fichier** : `src/utils/maps.py`

#### **Fonction Maîtresse Carte**
```python
def create_albedo_map(df_data, selected_date=None, product='MOD10A1', 
                     qa_threshold=1, use_advanced_qa=False, algorithm_flags={}, 
                     selected_band=None, diffuse_fraction=None):
    """
    Ligne 503: Fonction centrale création carte
    
    INNOVATIONS IMPLÉMENTÉES:
    ✅ Auto-centrage sur glacier (lignes 519-547)
    ✅ Zoom niveau 17 pour détail pixels
    ✅ Diffuse fraction parameter flow
    ✅ Tooltips dynamiques BSA/WSA
    
    Workflow:
    1. Calcul limites glacier → calculate_glacier_bounds()
    2. Création carte centrée → create_base_map()
    3. Ajout boundary glacier → add_glacier_boundary()
    4. Extraction pixels MODIS → get_modis_pixels_for_date()
    5. Affichage tooltips → HTML dynamique
    """
    
    # AUTO-CENTRAGE INNOVATION (lignes 519-525)
    glacier_geojson = _load_glacier_boundary_for_bounds()
    center_lat, center_lon, bounds = calculate_glacier_bounds(glacier_geojson)
    m = create_base_map(center_lat=center_lat, center_lon=center_lon, 
                       zoom_start=17, satellite_only=True)  # ← Zoom 17
    
    # AJUSTEMENT SERRÉ (lignes 530-545)
    if bounds:
        lat_buffer = 0.0018  # ~200m buffer
        lon_buffer = 0.003
        tight_bounds = [
            [min_lat - lat_buffer, min_lon - lon_buffer],
            [max_lat + lat_buffer, max_lon + lon_buffer]
        ]
        m.fit_bounds(tight_bounds, padding=(3, 3))  # Padding minimal
```

#### **Auto-Centrage Dynamique**
```python
def calculate_glacier_bounds(glacier_geojson):
    """
    Ligne 245: Calcul automatique centre et limites glacier
    
    NOTRE INNOVATION MAJEURE:
    ✅ Extraction coordonnées min/max du masque réel
    ✅ Calcul centre géométrique automatique
    ✅ Création bounds pour folium.fit_bounds()
    ✅ Fallback coordonnées Athabasca si échec
    
    Returns:
    - center_lat, center_lon: Centre géométrique
    - bounds: [[south, west], [north, east]] pour folium
    """
    
    # Extraction coordonnées de toutes les features
    all_lats, all_lons = [], []
    for feature in glacier_geojson['features']:
        if feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
            # Traitement Polygon vs MultiPolygon
            coords = feature['geometry']['coordinates']
            # ... extraction coordonnées ...
            for coord in ring:
                if len(coord) >= 2:
                    lon, lat = coord[0], coord[1]
                    all_lons.append(lon)
                    all_lats.append(lat)
    
    # Calcul centre et limites
    min_lat, max_lat = min(all_lats), max(all_lats)
    min_lon, max_lon = min(all_lons), max(all_lons)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    bounds = [[min_lat, min_lon], [max_lat, max_lon]]
```

#### **Tooltips Dynamiques**
```python
# Génération tooltips avec données temps réel (lignes 494-522)
if 'MCD43A3' in product_display:
    if 'Visible' in product_display:
        albedo_type = "Visible Albedo"
        extra_info = "<br><small style='color: #666;'>0.3-0.7 μm BSA</small>"
    elif 'NIR' in product_display:
        albedo_type = "NIR Albedo"
        extra_info = "<br><small style='color: #666;'>0.7-5.0 μm BSA</small>"
    else:
        albedo_type = "Blue-Sky Albedo"
        # INNOVATION: BSA/WSA dynamiques depuis propriétés pixel
        bsa_pct = feature['properties'].get('bsa_percentage', 80)
        wsa_pct = feature['properties'].get('wsa_percentage', 20)
        extra_info = f"<br><small style='color: #666;'>BSA: {bsa_pct:.0f}%, WSA: {wsa_pct:.0f}%</small>"

# HTML tooltip complet (lignes 510-522)
html_content = f"""
<div style="font-family: Arial, sans-serif; padding: 10px; background: rgba(255,255,255,0.95); border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
    <div style="font-size: 18px; font-weight: bold; color: #e65100; margin-bottom: 8px;">
        {albedo_type}: {albedo_value:.3f}{extra_info}
    </div>
    <div style="font-size: 13px; line-height: 1.5;">
        <strong>Product:</strong> {product_display}<br>
        <strong>Date:</strong> {selected_date}<br>
        <strong>Source:</strong> {satellite_source}<br>
        <strong>Quality:</strong> {quality_filter}
    </div>
</div>
"""
```

---

## ❄️ MOD10A1/MYD10A1 - Implémentation Complète

### **🏔️ Dashboard Principal MOD10A1**
**Fichier** : `src/dashboards/melt_season_dashboard.py`

#### **Point d'Entrée**
```python
def create_melt_season_dashboard(df_data, df_results, df_focused, qa_config=None, qa_level=None):
    """
    Ligne 11: Dashboard analyse saison de fonte
    
    Fonctionnalités:
    ✅ Terra-Aqua fusion workflow
    ✅ Advanced QA filtering
    ✅ Williamson & Menounos methodology
    ✅ Trend analysis (Mann-Kendall, Sen's slope)
    ✅ Export capabilities
    """
```

### **📊 Workflow Complet MOD10A1**
**Fichier** : `src/workflows/melt_season.py`

#### **Analyse Saison de Fonte**
```python
def run_melt_season_analysis_williamson(start_year=2010, end_year=2024, 
                                       use_advanced_qa=False, qa_level='standard',
                                       export_data=True, export_figures=True):
    """
    Ligne 23: Workflow complet Williamson & Menounos (2021)
    
    MÉTHODOLOGIE SCIENTIFIQUE:
    ✅ Extraction année par année (évite timeouts GEE)
    ✅ Terra-Aqua fusion literature-based
    ✅ QA filtering multi-niveaux
    ✅ Range filtering (0.05-0.99)
    ✅ Statistical analysis robuste
    """
    
    print(f"🌨️ DÉMARRAGE ANALYSE SAISON DE FONTE")
    print(f"📅 Période: {start_year}-{end_year}")
    print(f"🔍 Qualité: {'Advanced' if use_advanced_qa else 'Basic'} QA, niveau {qa_level}")
    print(f"📊 Méthodologie: Williamson & Menounos (2021)")
    
    all_data = []
    successful_years = []
    failed_years = []
    
    # Extraction année par année pour robustesse
    for year in range(start_year, end_year + 1):
        try:
            year_data = extract_melt_season_data_yearly(
                year, glacier_mask, use_advanced_qa, qa_level
            )
            if not year_data.empty:
                all_data.append(year_data)
                successful_years.append(year)
            else:
                failed_years.append(year)
        except Exception as e:
            failed_years.append(year)
            print(f"   ❌ {year}: Erreur - {str(e)[:50]}...")
    
    # Combinaison et analyse statistique
    if all_data:
        df_combined = pd.concat(all_data, ignore_index=True)
        results = perform_statistical_analysis(df_combined)
        return df_combined, results
```

### **🛰️ Extraction Terra-Aqua MOD10A1**
**Fichier** : `src/utils/earth_engine/modis_extraction.py`

#### **Fonction Principale MOD10A1**
```python
def _extract_mod10a1_pixels(date, roi, qa_threshold, use_advanced_qa, algorithm_flags, silent):
    """
    Ligne 146: Extraction pixels MOD10A1/MYD10A1 avec fusion Terra-Aqua
    
    INNOVATION TERRA-AQUA FUSION:
    ✅ Priorité Terra (10h30) sur Aqua (13h30)
    ✅ Gap-filling hiérarchique
    ✅ Score qualité: Terra=100, Aqua=50
    ✅ Composition quotidienne unique
    ✅ Élimination pseudo-réplication
    """
    
    # Collections Terra et Aqua
    mod10a1 = ee.ImageCollection('MODIS/006/MOD10A1')  # Terra
    myd10a1 = ee.ImageCollection('MODIS/006/MYD10A1')  # Aqua
    
    # Filtrage temporel strict (jour exact)
    start_date = ee.Date(date)
    end_date = start_date.advance(1, 'day')
    
    terra_images = mod10a1.filterDate(start_date, end_date).filterBounds(roi)
    aqua_images = myd10a1.filterDate(start_date, end_date).filterBounds(roi)
    
    # FUSION TERRA-AQUA LITERATURE-BASED
    def combine_terra_aqua_literature_method(terra_col, aqua_col):
        """
        Fusion basée littérature scientifique:
        - Terra prioritaire (dysfonctionnement bande 6 Aqua)
        - Gap-filling avec Aqua si Terra manquant
        - Score qualité pour mosaïque optimale
        """
        
        def add_quality_score(image):
            # Score Terra = 100, Aqua = 50
            satellite = image.get('system:index')
            score = ee.Algorithms.If(
                ee.String(satellite).index('MOD').gte(0),
                100,  # Terra (priorité)
                50    # Aqua (fallback)
            )
            return image.set('quality_score', score)
        
        # Application scores et combinaison
        terra_scored = terra_col.map(add_quality_score)
        aqua_scored = aqua_col.map(add_quality_score)
        combined = terra_scored.merge(aqua_scored)
        
        # Mosaïque basée score qualité (Terra prioritaire)
        return combined.qualityMosaic('quality_score')
```

#### **Filtrage QA Avancé MOD10A1**
```python
def mask_modis_snow_albedo_advanced(image, qa_threshold=1, algorithm_flags={}):
    """
    Ligne 180: Filtrage QA avancé MOD10A1
    
    QA FLAGS IMPLÉMENTÉS:
    ✅ Basic QA (0=best, 1=good, 2=ok)
    ✅ Algorithm flags (8 bits détaillés)
    ✅ Range filtering Williamson & Menounos
    ✅ Multi-level quality control
    
    Algorithm Flags (NDSI_Snow_Cover_Algorithm_Flags_QA):
    - Bit 0: Inland water
    - Bit 1: Low visible reflectance
    - Bit 2: Low NDSI (< 0.4)
    - Bit 3: Temperature/height screen
    - Bit 4: High SWIR reflectance
    - Bit 5-6: Cloud confidence
    - Bit 7: Low illumination/shadows
    """
    
    # Bandes essentielles
    albedo = image.select('NDSI_Snow_Cover')
    basic_qa = image.select('NDSI_Snow_Cover_Basic_QA')
    algo_qa = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA')
    
    # Filtrage QA basique
    good_quality = basic_qa.lte(qa_threshold)
    
    # Range filtering (Williamson & Menounos 2021)
    valid_albedo = albedo.gte(5).And(albedo.lte(99))  # Avant scaling
    
    # Advanced algorithm flags
    if algorithm_flags:
        flag_masks = []
        
        if algorithm_flags.get('no_inland_water', False):
            mask = algo_qa.bitwiseAnd(1).eq(0)    # Bit 0
            flag_masks.append(mask)
        if algorithm_flags.get('no_low_visible', False):
            mask = algo_qa.bitwiseAnd(2).eq(0)    # Bit 1
            flag_masks.append(mask)
        if algorithm_flags.get('no_low_ndsi', False):
            mask = algo_qa.bitwiseAnd(4).eq(0)    # Bit 2
            flag_masks.append(mask)
        if algorithm_flags.get('no_temp_issues', False):
            mask = algo_qa.bitwiseAnd(8).eq(0)    # Bit 3
            flag_masks.append(mask)
        if algorithm_flags.get('no_high_swir', False):
            mask = algo_qa.bitwiseAnd(16).eq(0)   # Bit 4
            flag_masks.append(mask)
        if algorithm_flags.get('no_clouds', False):
            mask = algo_qa.bitwiseAnd(96).eq(0)   # Bits 5-6
            flag_masks.append(mask)
        if algorithm_flags.get('no_shadows', False):
            mask = algo_qa.bitwiseAnd(128).eq(0)  # Bit 7
            flag_masks.append(mask)
        
        # Combinaison tous les flags
        if flag_masks:
            algorithm_mask = flag_masks[0]
            for mask in flag_masks[1:]:
                algorithm_mask = algorithm_mask.And(mask)
            final_quality = good_quality.And(algorithm_mask)
        else:
            final_quality = good_quality
    else:
        final_quality = good_quality
    
    # Application masques et scaling
    masked = albedo.updateMask(valid_albedo.And(final_quality)).multiply(0.01)
    
    return masked.rename('albedo_daily').copyProperties(image, ['system:time_start'])
```

### **📈 Analyse Statistique MOD10A1**
**Fichier** : `src/analysis/statistics.py`

#### **Tests de Tendance**
```python
def perform_trend_analysis(df, value_column='albedo_mean'):
    """
    Tests statistiques robustes pour MOD10A1
    
    TESTS IMPLÉMENTÉS:
    ✅ Mann-Kendall (tendance non-paramétrique)
    ✅ Sen's slope (magnitude tendance)
    ✅ Spearman correlation
    ✅ Linear regression avec CI
    ✅ Seasonal decomposition
    """
    
    # Préparation données annuelles
    df_annual = df.groupby('year')[value_column].agg(['mean', 'std', 'count']).reset_index()
    
    # Test Mann-Kendall
    mk_result = mk.original_test(df_annual['mean'])
    
    # Sen's slope
    slope_result = mk.sens_estimator(df_annual['mean'])
    
    # Résultats compilés
    results = {
        'trend': mk_result.trend,
        'p_value': mk_result.p,
        'slope_per_year': slope_result,
        'slope_percent_per_year': (slope_result / df_annual['mean'].mean()) * 100,
        'significance': 'significant' if mk_result.p < 0.05 else 'not_significant'
    }
    
    return results
```

---

## 🌈 MCD43A3 - Implémentation Détaillée

### **🎨 Dashboard Principal MCD43A3**
**Fichier** : `src/dashboards/mcd43a3_dashboard.py`

#### **Interface Spectrale**
```python
def create_mcd43a3_dashboard(mcd43a3_data, qa_config=None, qa_level=None):
    """
    Ligne 11: Dashboard analyse spectrale MCD43A3
    
    FONCTIONNALITÉS SPÉCIALISÉES:
    ✅ Analyse multi-bandes (vis, NIR, shortwave)
    ✅ BSA vs WSA comparisons
    ✅ Blue-Sky albedo calculations
    ✅ Seasonal evolution analysis
    ✅ Spectral contamination detection
    """
```

### **🌟 Extraction MCD43A3 Avancée**
**Fichier** : `src/utils/earth_engine/modis_extraction.py`

#### **Fonction Principale MCD43A3**
```python
def _extract_mcd43a3_pixels(date, roi, qa_threshold, silent, selected_band=None, diffuse_fraction=None):
    """
    Ligne 41: Extraction MCD43A3 avec BSA/WSA ajustable
    
    NOTRE INNOVATION MAJEURE:
    ✅ Diffuse fraction parameter dynamique
    ✅ Blue-Sky albedo calculation adaptative
    ✅ Multi-band selection (shortwave, vis, nir)
    ✅ BSA/WSA metadata pour tooltips
    ✅ Williamson & Menounos range filtering
    """
    
    # Collection MCD43A3
    mcd43a3 = ee.ImageCollection('MODIS/061/MCD43A3')
    
    # Filtrage temporel (±1 jour pour couverture)
    start_date = ee.Date(date).advance(-1, 'day')
    end_date = ee.Date(date).advance(1, 'day')
    images = mcd43a3.filterDate(start_date, end_date).filterBounds(roi)
    
    # Validation diffuse fraction
    if diffuse_fraction is None:
        diffuse_fraction = 0.2  # Default glaciers
    
    def mask_mcd43a3_albedo(image):
        """
        ALGORITHME BSA/WSA INNOVATION:
        ✅ Extraction BSA et WSA séparément
        ✅ Calcul Blue-Sky adaptatif
        ✅ Quality filtering QA ≤ threshold
        ✅ Range filtering (0.05-0.99)
        ✅ Multi-band processing
        """
        
        # Extraction bandes BSA et WSA
        bsa_shortwave = image.select('Albedo_BSA_shortwave')
        wsa_shortwave = image.select('Albedo_WSA_shortwave')
        bsa_vis = image.select('Albedo_BSA_vis')
        bsa_nir = image.select('Albedo_BSA_nir')
        
        # QA filtering
        qa_shortwave = image.select('BRDF_Albedo_Band_Mandatory_Quality_shortwave')
        good_quality = qa_shortwave.lte(qa_threshold)
        
        # Scaling (facteur 0.001 pour MCD43A3)
        bsa_masked = bsa_shortwave.updateMask(good_quality).multiply(0.001)
        wsa_masked = wsa_shortwave.updateMask(good_quality).multiply(0.001)
        
        # CALCUL BLUE-SKY ALBEDO ADAPTATIF
        # Blue_Sky = (1 - f_diffuse) × BSA + f_diffuse × WSA
        blue_sky_shortwave = bsa_masked.multiply(1 - diffuse_fraction).add(
            wsa_masked.multiply(diffuse_fraction)
        )
        
        # Range filtering Williamson & Menounos (2021)
        range_mask = blue_sky_shortwave.gte(0.05).And(blue_sky_shortwave.lte(0.99))
        
        # Processing bandes spectrales
        vis_masked = bsa_vis.updateMask(good_quality).multiply(0.001)
        nir_masked = bsa_nir.updateMask(good_quality).multiply(0.001)
        
        # Sélection bande primaire
        if selected_band == 'vis':
            primary_albedo = vis_masked.updateMask(range_mask)
        elif selected_band == 'nir':
            primary_albedo = nir_masked.updateMask(range_mask)
        else:  # Default shortwave (blue-sky)
            primary_albedo = blue_sky_shortwave.updateMask(range_mask)
        
        # Image multi-bandes avec métadonnées
        return primary_albedo.rename('albedo_daily').addBands([
            blue_sky_shortwave.updateMask(range_mask).rename('blue_sky_shortwave'),
            bsa_masked.rename('bsa_shortwave'),
            wsa_masked.rename('wsa_shortwave'),
            vis_masked.updateMask(range_mask).rename('albedo_vis'),
            nir_masked.updateMask(range_mask).rename('albedo_nir')
        ]).copyProperties(image, ['system:time_start'])
    
    # Processing et composition
    processed_images = images.map(mask_mcd43a3_albedo)
    combined_image = processed_images.mean()  # Moyenne si multiple dates
    
    # Identification produit avec diffuse fraction
    if selected_band == 'vis':
        product_name = 'MCD43A3 Visible'
        band_desc = 'Visible (0.3-0.7 μm) BSA'
    elif selected_band == 'nir':
        product_name = 'MCD43A3 NIR'
        band_desc = 'NIR (0.7-5.0 μm) BSA'
    else:
        product_name = 'MCD43A3'
        band_desc = f'Blue-Sky albedo ({diffuse_fraction*100:.0f}% diffuse)'
    
    quality_description = f'QA ≤ {qa_threshold} (BRDF+magnitude), {band_desc}'
    
    return _process_pixels_to_geojson(combined_image, roi, date, product_name, 
                                    quality_description, silent, diffuse_fraction)
```

### **🎯 Workflow MCD43A3 Complet**
**Fichier** : `src/workflows/broadband_albedo.py`

#### **Analyse Spectrale Complète**
```python
def run_mcd43a3_analysis_complete(start_year=2010, end_year=2024, 
                                 export_data=True, export_figures=True):
    """
    Ligne 28: Workflow complet MCD43A3 spectral
    
    ANALYSES IMPLÉMENTÉES:
    ✅ Multi-band extraction (6 bandes)
    ✅ BSA vs WSA analysis
    ✅ Seasonal evolution
    ✅ Spectral ratio analysis
    ✅ Contamination detection
    ✅ Statistical trend analysis
    """
    
    print(f"🌈 DÉMARRAGE ANALYSE MCD43A3 COMPLÈTE")
    print(f"📡 Produit: MCD43A3 (16-day broadband albedo)")
    print(f"🔬 Analyse: Multi-spectrale avec BSA/WSA")
    
    # Extraction données spectrales
    mcd43a3_data = extract_mcd43a3_data_yearly(start_year, end_year)
    
    if mcd43a3_data.empty:
        print("❌ Aucune donnée MCD43A3 extraite")
        return None, None
    
    # Analyse spectrale détaillée
    spectral_results = analyze_spectral_patterns(mcd43a3_data)
    
    # Analyse temporelle
    temporal_results = analyze_temporal_evolution(mcd43a3_data)
    
    # Détection contamination
    contamination_results = detect_spectral_contamination(mcd43a3_data)
    
    return mcd43a3_data, {
        'spectral': spectral_results,
        'temporal': temporal_results,
        'contamination': contamination_results
    }
```

---

## 🔧 Innovations Techniques

### **1. 🌤️ BSA/WSA Ratio Ajustable**

#### **Interface Utilisateur**
```python
# Slider diffuse fraction (interactive_albedo_dashboard.py:100-122)
diffuse_fraction = st.sidebar.slider(
    "Diffuse Fraction:",
    min_value=0.0,
    max_value=1.0,
    value=0.2,  # Default pour glaciers
    step=0.05,
    help="Atmospheric conditions control",
    key="diffuse_fraction_slider"
)

# Interprétation conditions (lignes 111-120)
conditions = {
    0.0-0.15: "☀️ Clear sky conditions",
    0.15-0.35: "🌤️ Typical glacier conditions", 
    0.35-0.65: "⛅ Mixed sky conditions",
    0.65-1.0: "☁️ Overcast conditions"
}
```

#### **Algorithme Blue-Sky**
```python
# Calcul adaptatif (modis_extraction.py:90-98)
if diffuse_fraction is None:
    diffuse_fraction = 0.2  # Default scientific

# Formule Blue-Sky Albedo
blue_sky_shortwave = bsa_masked.multiply(1 - diffuse_fraction).add(
    wsa_masked.multiply(diffuse_fraction)
)

# Exemples pratiques:
# Ciel clair (f=0.1): 90% BSA + 10% WSA
# Glacier typique (f=0.2): 80% BSA + 20% WSA
# Conditions mixtes (f=0.4): 60% BSA + 40% WSA
```

#### **Métadonnées Tooltips**
```python
# Propriétés pixels dynamiques (pixel_processing.py:141-144)
if diffuse_fraction is not None and 'MCD43A3' in product_name:
    properties['diffuse_fraction'] = diffuse_fraction
    properties['bsa_percentage'] = (1 - diffuse_fraction) * 100
    properties['wsa_percentage'] = diffuse_fraction * 100

# Affichage tooltips (maps.py:505-507)
bsa_pct = feature['properties'].get('bsa_percentage', 80)
wsa_pct = feature['properties'].get('wsa_percentage', 20)
extra_info = f"BSA: {bsa_pct:.0f}%, WSA: {wsa_pct:.0f}%"
```

### **2. 🎯 Auto-Centrage & Zoom Dynamique**

#### **Calcul Limites Automatique**
```python
def calculate_glacier_bounds(glacier_geojson):
    """
    Innovation: Calcul automatique centre glacier
    """
    all_lats, all_lons = [], []
    
    # Extraction toutes coordonnées masque
    for feature in glacier_geojson['features']:
        coords = feature['geometry']['coordinates']
        for ring in coords:
            for coord in ring:
                lon, lat = coord[0], coord[1]
                all_lons.append(lon)
                all_lats.append(lat)
    
    # Centre géométrique
    center_lat = (min(all_lats) + max(all_lats)) / 2
    center_lon = (min(all_lons) + max(all_lons)) / 2
    
    return center_lat, center_lon, bounds
```

#### **Zoom & Centrage Optimal**
```python
# Configuration zoom détaillé (maps.py:523-545)
zoom_start = 17  # Niveau détaillé pour pixels 500m
lat_buffer = 0.0018  # ~200m buffer
lon_buffer = 0.003   # Ajusté longitude 52°N
padding = (3, 3)     # Padding minimal interface

# Application centrage
m = create_base_map(center_lat, center_lon, zoom_start)
m.fit_bounds(tight_bounds, padding)
```

### **3. 🏷️ Tooltips Intelligents & Adaptatifs**

#### **Contenu Dynamique par Produit**
```python
# Tooltips MCD43A3 adaptatifs (maps.py:494-522)
if 'MCD43A3' in product_display:
    if 'Visible' in product_display:
        albedo_type = "Visible Albedo"
        extra_info = "0.3-0.7 μm BSA"
    elif 'NIR' in product_display:
        albedo_type = "NIR Albedo" 
        extra_info = "0.7-5.0 μm BSA"
    else:
        albedo_type = "Blue-Sky Albedo"
        # INNOVATION: Pourcentages BSA/WSA dynamiques
        bsa_pct = feature['properties'].get('bsa_percentage', 80)
        wsa_pct = feature['properties'].get('wsa_percentage', 20)
        extra_info = f"BSA: {bsa_pct:.0f}%, WSA: {wsa_pct:.0f}%"

# HTML styling responsive
html_content = f"""
<div style="font-family: Arial, sans-serif; padding: 10px; background: rgba(255,255,255,0.95); border-radius: 5px;">
    <div style="font-size: 18px; font-weight: bold; color: #e65100;">
        {albedo_type}: {albedo_value:.3f}
        <br><small style='color: #666;'>{extra_info}</small>
    </div>
    <div style="font-size: 13px; line-height: 1.5;">
        <strong>Product:</strong> {product_display}<br>
        <strong>Date:</strong> {selected_date}<br>
        <strong>Source:</strong> {satellite_source}<br>
        <strong>Quality:</strong> {quality_filter}
    </div>
</div>
"""
```

### **4. 🛰️ Terra-Aqua Fusion Literature-Based**

#### **Algorithme Scientifique**
```python
def combine_terra_aqua_literature_method(terra_col, aqua_col):
    """
    Innovation: Fusion basée littérature scientifique
    
    JUSTIFICATION LITTÉRAIRE:
    ✅ Terra prioritaire (dysfonctionnement bande 6 Aqua)
    ✅ Validation Groenland: MOD10A1 RMS=0.067 vs MYD10A1 RMS=0.075
    ✅ Gap-filling hiérarchique si Terra manquant
    ✅ Composition quotidienne (élimine pseudo-réplication)
    """
    
    def add_quality_score(image):
        satellite = image.get('system:index')
        # Score qualité: Terra=100, Aqua=50
        score = ee.Algorithms.If(
            ee.String(satellite).index('MOD').gte(0),
            100,  # Terra (10h30, conditions optimales)
            50    # Aqua (13h30, fallback)
        )
        # Bonus couverture nuageuse
        cloud_score = image.select('NDSI_Snow_Cover_Basic_QA')
        coverage_bonus = cloud_score.eq(0).multiply(10)  # +10 si QA=0
        
        return image.set('quality_score', score.add(coverage_bonus))
    
    # Application scores
    terra_scored = terra_col.map(add_quality_score)
    aqua_scored = aqua_col.map(add_quality_score)
    combined = terra_scored.merge(aqua_scored)
    
    # Mosaïque optimale (Terra prioritaire)
    return combined.qualityMosaic('quality_score')
```

---

## 🔄 Flux de Données

### **📊 Pipeline Carte Interactive Complet**

```
1. USER INPUT (Sidebar Controls)
   ├── Product Selection: MOD10A1 vs MCD43A3
   ├── QA Level: 0, 1, 2 + Advanced flags  
   ├── Band Selection: shortwave, vis, nir (MCD43A3)
   ├── Diffuse Fraction: 0.0-1.0 slider ← INNOVATION
   └── Date Selection: Month → Day picker
   │
   │ File: interactive_albedo_dashboard.py:59-211
   │
   ▼
2. MAP CREATION (Auto-centering)
   ├── Load glacier boundary → _load_glacier_boundary_for_bounds()
   ├── Calculate bounds → calculate_glacier_bounds()
   ├── Center map → create_base_map(center_lat, center_lon, zoom=17)
   └── Fit bounds → m.fit_bounds(tight_bounds, padding=(3,3))
   │
   │ File: maps.py:503-547
   │
   ▼
3. EARTH ENGINE QUERY (Real-time processing)
   ├── Initialize EE → initialize_earth_engine()
   ├── Get ROI → get_roi_from_geojson(glacier_geojson)
   ├── Extract pixels → get_modis_pixels_for_date()
   │   ├── MOD10A1: _extract_mod10a1_pixels() + Terra-Aqua fusion
   │   └── MCD43A3: _extract_mcd43a3_pixels() + BSA/WSA calculation
   └── Quality filtering → mask_modis_*_albedo()
   │
   │ File: earth_engine/modis_extraction.py:10-199
   │
   ▼
4. PIXEL PROCESSING (GeoJSON conversion)
   ├── Convert to vectors → reduceToVectors()
   ├── Clip to glacier → intersection(roi)
   ├── Add properties → add_pixel_properties()
   │   ├── albedo_value (scaled)
   │   ├── satellite source (Terra/Aqua)
   │   ├── diffuse_fraction metadata ← INNOVATION
   │   ├── bsa_percentage, wsa_percentage ← INNOVATION
   │   └── quality_filter description
   └── Export GeoJSON → getInfo()
   │
   │ File: earth_engine/pixel_processing.py:27-194
   │
   ▼
5. MAP VISUALIZATION (Interactive display)
   ├── Color coding → get_albedo_color_palette()
   ├── Tooltip generation → HTML dynamique avec BSA/WSA %
   ├── Folium polygons → GeoJson() avec styling
   ├── Measurement tools → MeasureControl + Draw
   └── Display → st_folium(albedo_map)
   │
   │ File: maps.py:439-600 + dashboard:516
   │
   ▼
6. USER INTERACTION (Real-time feedback)
   ├── Hover tooltips → Albedo + metadata
   ├── Click details → Comprehensive popup
   ├── Measurement → Distance/area tools
   └── Parameter adjustment → Re-trigger pipeline
```

### **🔄 Parameter Flow Detailed**

```
┌─ diffuse_fraction (0.0-1.0) ────────────────────────────────────────┐
│                                                                     │
│ dashboard.py:100 → maps.py:491 → modis_extraction.py:41 →          │
│ pixel_processing.py:142 → maps.py:505 → tooltip display            │
│                                                                     │
│ Transformations:                                                    │
│ • Slider value → Earth Engine calculation                          │
│ • Blue-Sky = (1-f) × BSA + f × WSA                                │
│ • Metadata: bsa_percentage = (1-f) × 100                          │
│ • Tooltip: "BSA: 80%, WSA: 20%"                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─ qa_threshold + algorithm_flags ────────────────────────────────────┐
│                                                                     │
│ dashboard.py:127-203 → maps.py:487 → modis_extraction.py:146 →     │
│ mask_modis_*_albedo() → filtered pixels → quality_filter string    │
│                                                                     │
│ Processing:                                                         │
│ • Basic QA: 0=best, 1=good, 2=ok                                  │
│ • Algorithm flags: 8-bit filtering                                 │
│ • Range filter: 0.05-0.99 (Williamson & Menounos)                │
│ • Description: "QA ≤ 1 (BRDF+magnitude), Blue-Sky albedo"         │
└─────────────────────────────────────────────────────────────────────┘

┌─ selected_band (shortwave/vis/nir) ─────────────────────────────────┐
│                                                                     │
│ dashboard.py:78-96 → maps.py:490 → modis_extraction.py:105 →       │
│ band selection logic → primary_albedo → tooltip type              │
│                                                                     │
│ Band Processing:                                                    │
│ • shortwave: Blue-Sky albedo (default)                            │
│ • vis: Visible BSA (0.3-0.7 μm)                                   │
│ • nir: NIR BSA (0.7-5.0 μm)                                       │
│ • Product name: "MCD43A3 Visible", "MCD43A3 NIR", "MCD43A3"       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Fonctions Critiques par Fonctionnalité

### **🚀 Top 10 Fonctions Essentielles**

| **Rang** | **Fonction** | **Fichier** | **Ligne** | **Responsabilité** |
|----------|--------------|-------------|-----------|-------------------|
| **1** | `create_interactive_albedo_dashboard()` | `interactive_albedo_dashboard.py` | 11 | **Point d'entrée principal** |
| **2** | `create_albedo_map()` | `maps.py` | 503 | **Maître création carte** |
| **3** | `get_modis_pixels_for_date()` | `modis_extraction.py` | 10 | **Extraction Earth Engine** |
| **4** | `_extract_mcd43a3_pixels()` | `modis_extraction.py` | 41 | **BSA/WSA innovation** |
| **5** | `calculate_glacier_bounds()` | `maps.py` | 245 | **Auto-centrage** |
| **6** | `_create_sidebar_controls()` | `interactive_albedo_dashboard.py` | 59 | **Interface contrôles** |
| **7** | `mask_mcd43a3_albedo()` | `modis_extraction.py` | 68 | **Algorithme Blue-Sky** |
| **8** | `add_pixel_properties()` | `pixel_processing.py` | 124 | **Métadonnées pixels** |
| **9** | `_extract_mod10a1_pixels()` | `modis_extraction.py` | 146 | **Terra-Aqua fusion** |
| **10** | `combine_terra_aqua_literature_method()` | `modis_extraction.py` | 170 | **Fusion scientifique** |

### **🔧 Fonctions par Innovation**

#### **🌤️ BSA/WSA Ajustable**
```python
# Interface
interactive_albedo_dashboard.py:100-122  # Slider + interprétation

# Algorithme  
modis_extraction.py:90-98                # Blue-Sky calculation

# Métadonnées
pixel_processing.py:141-144             # bsa_percentage, wsa_percentage

# Affichage
maps.py:505-507                         # Tooltips dynamiques
```

#### **🎯 Auto-Centrage**
```python
# Calcul limites
maps.py:245-301                         # calculate_glacier_bounds()

# Application
maps.py:519-547                         # Centre + zoom + fit_bounds
```

#### **🛰️ Terra-Aqua Fusion**
```python
# Algorithme principal
modis_extraction.py:146-199             # _extract_mod10a1_pixels()

# Méthode scientifique  
modis_extraction.py:170-198             # combine_terra_aqua_literature_method()
```

#### **🏷️ Tooltips Intelligents**
```python
# Génération contenu
maps.py:494-522                         # HTML adaptatif par produit

# Styling responsive
maps.py:510-522                         # CSS inline + données dynamiques
```

### **📊 Fonctions par Produit MODIS**

#### **❄️ MOD10A1/MYD10A1**
```python
# Dashboard
melt_season_dashboard.py:11              # create_melt_season_dashboard()

# Workflow
melt_season.py:23                       # run_melt_season_analysis_williamson()

# Extraction
modis_extraction.py:146                 # _extract_mod10a1_pixels()

# QA filtering
modis_extraction.py:180                 # mask_modis_snow_albedo_advanced()

# Analysis
statistics.py:15                        # perform_trend_analysis()
```

#### **🌈 MCD43A3**
```python
# Dashboard
mcd43a3_dashboard.py:11                 # create_mcd43a3_dashboard()

# Workflow  
broadband_albedo.py:28                  # run_mcd43a3_analysis_complete()

# Extraction
modis_extraction.py:41                  # _extract_mcd43a3_pixels()

# BSA/WSA processing
modis_extraction.py:68                  # mask_mcd43a3_albedo()

# Spectral analysis
spectral_analysis.py:20                 # analyze_spectral_patterns()
```

---

## 📝 Notes Techniques Importantes

### **🔒 Sécurité & Robustesse**
```python
# Gestion erreurs Earth Engine
try:
    modis_pixels = get_modis_pixels_for_date(...)
except Exception as e:
    st.error(f"Error loading MODIS pixels: {e}")
    return None

# Validation paramètres
if diffuse_fraction is None:
    diffuse_fraction = 0.2  # Scientific default

# Fallbacks géographiques  
if not glacier_geojson:
    return 52.188, -117.265, [[52.17, -117.28], [52.21, -117.24]]
```

### **⚡ Performance & Optimisation**
```python
# Limitazione pixels pour performance
pixels_limited = pixels_with_data.limit(200)

# Processing année par année (évite timeouts)
for year in range(start_year, end_year + 1):
    year_data = extract_melt_season_data_yearly(year)

# Cache session Streamlit
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = {}
```

### **📊 Standards Scientifiques**
```python
# Williamson & Menounos (2021) range filtering
valid_albedo = albedo.gte(5).And(albedo.lte(99))  # Avant scaling
albedo_range_mask = scaled_albedo.gte(0.05).And(scaled_albedo.lte(0.99))

# Terra-Aqua fusion literature-based
# Priorité Terra (dysfonctionnement bande 6 Aqua)
score = ee.Algorithms.If(satellite.index('MOD').gte(0), 100, 50)

# QA filtering multi-niveaux
basic_qa.lte(qa_threshold)  # Basic quality
algo_qa.bitwiseAnd(flags)   # Algorithm flags
```

---

**Cette documentation technique complète couvre tous les aspects essentiels du codebase, des innovations implémentées aux flux de données, en passant par les fonctions critiques pour chaque produit MODIS ! 🔧📊**

*Dernière mise à jour: 6 janvier 2025*  
*Version: Complète avec innovations BSA/WSA, auto-centrage, et Terra-Aqua fusion*