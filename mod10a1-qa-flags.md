# Guide des QA Flags du produit MODIS MOD10A1

## Vue d'ensemble

Le produit MOD10A1 (MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid) contient deux types de données d'assurance qualité (QA) :

1. **NDSI_Snow_Cover_Basic_QA** : Une estimation générale de la qualité
2. **NDSI_Snow_Cover_Algorithm_Flags_QA** : Des flags détaillés bit par bit

## 1. NDSI_Snow_Cover_Basic_QA

### Description
Une estimation de la qualité de base du résultat de l'algorithme pour chaque pixel.

### Structure
- **Type de données** : UINT8 (8 bits non signé)
- **Dimensions** : 2400 x 2400 pixels (pour chaque tuile)
- **Plage valide** : 0-4
- **Valeur de remplissage** : 255

### Valeurs et significations

| Valeur | Signification | Description |
|--------|---------------|-------------|
| 0 | Best | Meilleure qualité |
| 1 | Good | Bonne qualité |
| 2 | OK | Qualité acceptable |
| 3 | Poor | Pauvre qualité (non utilisé) |
| 4 | Other | Autre qualité (non utilisé) |
| 211 | Night | Nuit |
| 239 | Ocean | Océan |
| 255 | Fill/No data | Données L1B inutilisables ou pas de données |

### Utilisation
- La valeur QA est initialisée à "best" (0) et ajustée selon la qualité des données d'entrée
- Si les données de radiance sont hors de la plage 5-100% TOA mais utilisables → QA = "good" (1)
- Si l'angle zénithal solaire (SZA) est entre 70° et 85° → QA = "ok" (2)
- Si les données d'entrée sont inutilisables → QA = "other" (4)

## 2. NDSI_Snow_Cover_Algorithm_Flags_QA

### Description
Flags détaillés bit par bit indiquant les résultats des différents tests et filtres appliqués dans l'algorithme.

### Structure
- **Type de données** : UINT8 (8 bits)
- **Dimensions** : 2400 x 2400 pixels
- **Format** : Bit flags
- **Plage valide** : 0-254
- **Valeur de remplissage** : 255

### Signification des bits

| Bit | Nom du flag | Description | Action |
|-----|-------------|-------------|---------|
| **0** | Inland water flag | Identifie les plans d'eau intérieurs | Marquage uniquement |
| **1** | Low visible screen | Test de réflectance visible faible échoué | Détection de neige inversée → "no decision" |
| **2** | Low NDSI screen | NDSI < 0.10 | Détection de neige inversée → "not snow" |
| **3** | Temperature & height screen | Test combiné température/altitude | - Si altitude < 1300m et T ≥ 281K : détection inversée<br>- Si altitude ≥ 1300m et T ≥ 281K : neige marquée comme "trop chaude" |
| **4** | High SWIR screen | Réflectance SWIR trop élevée | - Si 0.25 < SWIR ≤ 0.45 : neige suspecte (bit activé)<br>- Si SWIR > 0.45 : détection inversée → "not snow" |
| **5** | MOD35_L2 probably cloudy | Masque nuage "probablement nuageux" | Information du masque nuage |
| **6** | MOD35_L2 probably clear | Masque nuage "probablement clair" | Information du masque nuage |
| **7** | Solar zenith screen | Angle zénithal solaire > 70° | Incertitude accrue dans les résultats |

### Détails des seuils (Collection 6.1)

#### Bit 1 - Low visible screen
- **Collection 6** : Band 2 ≤ 0.10 ou Band 4 ≤ 0.11
- **Collection 6.1** : Band 2 < 0.07 ou Band 4 < 0.07 (seuils abaissés)
- Objectif : Réduire les résultats "no decision"

#### Bit 3 - Temperature & height screen
- **Seuil de température** : 281 K (≈ 8°C)
- **Seuil d'altitude** : 1300 m
- Double fonction :
  1. Éviter les erreurs de commission à basse altitude
  2. Signaler la neige anormalement chaude à haute altitude

#### Bit 4 - High SWIR reflectance screen
- **Seuil d'avertissement** : 0.25 < Band 6 TOA ≤ 0.45
- **Seuil d'inversion** : Band 6 TOA > 0.45
- Objectif : Détecter les surfaces non-neigeuses qui ressemblent spectralement à la neige

## 3. Interprétation et utilisation

### Lecture des bits
Pour extraire un bit spécifique d'un pixel :

```python
# Exemple en Python
def check_bit(value, bit_position):
    """Vérifie si un bit est activé (1) ou non (0)"""
    return (value >> bit_position) & 1

# Pour un pixel avec valeur QA = 132 (10000100 en binaire)
qa_value = 132
inland_water = check_bit(qa_value, 0)  # Bit 0
low_vis = check_bit(qa_value, 1)       # Bit 1
solar_zenith = check_bit(qa_value, 7)  # Bit 7
```

### Cas d'usage courants

1. **Filtrer les détections incertaines** :
   - Exclure les pixels où bit 1 = 1 (low visible)
   - Exclure les pixels où bit 7 = 1 (high solar zenith)

2. **Identifier les plans d'eau** :
   - Utiliser bit 0 pour masquer/extraire les lacs et rivières

3. **Analyser la confusion nuage/neige** :
   - Examiner bits 5 et 6 pour les cas ambigus

4. **Évaluer la qualité des détections** :
   - Combiner plusieurs bits pour créer des masques de qualité

### Notes importantes

- **Bits multiples** : Plusieurs bits peuvent être activés simultanément pour un pixel
- **Propagation** : Les valeurs QA sont propagées du niveau L2 au niveau L3 (MOD10A1)
- **Antarctica** : Masquée comme 100% neige pour des raisons esthétiques
- **Collection 6.1** : Les bits 5 et 6 sont nouveaux (étaient des bits de réserve en C6)

## 4. Valeurs spéciales du NDSI_Snow_Cover

En plus des valeurs NDSI de 0-100 représentant le pourcentage de couverture neigeuse, le produit MOD10A1 utilise des valeurs spéciales pour identifier d'autres conditions :

| Valeur | Signification | Description |
|--------|---------------|-------------|
| 0-100 | NDSI snow | Pourcentage de couverture neigeuse |
| 200 | Missing data | Données manquantes |
| 201 | No decision | Pas de décision (conditions ambiguës) |
| 211 | Night | Nuit |
| 237 | Inland water | Plans d'eau intérieurs |
| 239 | Ocean | Océan |
| 250 | Cloud | Nuage |
| 254 | Detector saturated | Détecteur saturé |
| 255 | Fill | Valeur de remplissage |

Ces valeurs doivent être prises en compte lors du filtrage et de l'analyse des données.

## 4. Exemples pratiques dans Google Earth Engine

### Fonction d'extraction des bits

```javascript
// Fonction pour extraire les bits QA
function getQABits(image, start, end, bandName) {
  // Calculer le motif de bits à extraire
  var pattern = 0;
  for (var i = start; i <= end; i++) {
    pattern += Math.pow(2, i);
  }
  
  // Extraire et retourner les bits QA
  return image.select(bandName)
    .bitwiseAnd(pattern)
    .rightShift(start);
}
```

### Application d'un masque de qualité sur MOD10A1

```javascript
// Charger la collection MOD10A1
var snowCollection = ee.ImageCollection('MODIS/006/MOD10A1')
  .filter(ee.Filter.date('2020-01-01', '2020-12-31'))
  .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Basic_QA', 
           'NDSI_Snow_Cover_Algorithm_Flags_QA']);

// Fonction pour appliquer le masque de qualité
function qualityMask(image) {
  // Obtenir la bande QA de base
  var qa_basic = image.select('NDSI_Snow_Cover_Basic_QA');
  
  // Masquer les pixels de mauvaise qualité (garder seulement 0=best et 1=good)
  var goodQuality = qa_basic.lte(1);
  
  // Obtenir les flags d'algorithme
  var qa_flags = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA');
  
  // Extraire les bits individuels
  var inlandWater = getQABits(qa_flags, 0, 0, 'NDSI_Snow_Cover_Algorithm_Flags_QA');
  var lowVis = getQABits(qa_flags, 1, 1, 'NDSI_Snow_Cover_Algorithm_Flags_QA');
  var highSolarZenith = getQABits(qa_flags, 7, 7, 'NDSI_Snow_Cover_Algorithm_Flags_QA');
  
  // Créer un masque combiné (exclure low vis et high solar zenith)
  var combinedMask = goodQuality
    .and(lowVis.eq(0))
    .and(highSolarZenith.eq(0));
  
  // Appliquer le masque
  return image.updateMask(combinedMask);
}

// Appliquer le masque à la collection
var maskedSnow = snowCollection.map(qualityMask);
```

### Identification et masquage des plans d'eau

```javascript
// Fonction pour extraire et masquer les plans d'eau
function maskWaterBodies(image) {
  var qa_flags = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA');
  
  // Extraire le bit 0 (inland water)
  var waterMask = qa_flags.bitwiseAnd(1).eq(0); // 0 = pas d'eau, 1 = eau
  
  return image.updateMask(waterMask);
}
```

### Analyse de la confusion nuage/neige

```javascript
// Fonction pour analyser la confusion nuage/neige
function analyzeCloudSnowConfusion(image) {
  var qa_flags = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA');
  
  // Extraire les bits 5 et 6 (nouveaux en Collection 6.1)
  var probablyCloudy = getQABits(qa_flags, 5, 5, 'NDSI_Snow_Cover_Algorithm_Flags_QA');
  var probablyClear = getQABits(qa_flags, 6, 6, 'NDSI_Snow_Cover_Algorithm_Flags_QA');
  
  // Créer des couches pour visualisation
  return image.addBands([
    probablyCloudy.rename('probably_cloudy'),
    probablyClear.rename('probably_clear')
  ]);
}
```

### Calcul de statistiques de neige avec filtrage de qualité

```javascript
// Fonction complète pour calculer la couverture neigeuse
function calculateSnowCover(roi, startDate, endDate) {
  // Charger et filtrer la collection
  var collection = ee.ImageCollection('MODIS/006/MOD10A1')
    .filterBounds(roi)
    .filter(ee.Filter.date(startDate, endDate))
    .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Basic_QA', 
             'NDSI_Snow_Cover_Algorithm_Flags_QA']);
  
  // Fonction de masquage complet
  var applyAllMasks = function(image) {
    var ndsi = image.select('NDSI_Snow_Cover');
    var qa_basic = image.select('NDSI_Snow_Cover_Basic_QA');
    var qa_flags = image.select('NDSI_Snow_Cover_Algorithm_Flags_QA');
    
    // Masque de qualité de base (0=best, 1=good)
    var qualityMask = qa_basic.lte(1);
    
    // Masque NDSI valide (0-100)
    var validNDSI = ndsi.lte(100);
    
    // Extraire et masquer les conditions problématiques
    var lowVis = qa_flags.bitwiseAnd(2).eq(0);      // Bit 1
    var lowNDSI = qa_flags.bitwiseAnd(4).eq(0);     // Bit 2
    var tempHeight = qa_flags.bitwiseAnd(8).eq(0);  // Bit 3
    var highSWIR = qa_flags.bitwiseAnd(16).eq(0);   // Bit 4
    var solarZenith = qa_flags.bitwiseAnd(128).eq(0); // Bit 7
    
    // Combiner tous les masques
    var finalMask = qualityMask
      .and(validNDSI)
      .and(lowVis)
      .and(solarZenith);
    
    return image.updateMask(finalMask)
      .copyProperties(image, ['system:time_start']);
  };
  
  // Appliquer les masques
  var maskedCollection = collection.map(applyAllMasks);
  
  // Calculer les statistiques
  var snowBinary = maskedCollection.map(function(image) {
    // Considérer comme neige si NDSI > 40
    return image.select('NDSI_Snow_Cover').gt(40)
      .rename('snow_cover')
      .copyProperties(image, ['system:time_start']);
  });
  
  // Réduire par région pour obtenir le pourcentage
  var snowStats = snowBinary.map(function(image) {
    var stats = image.reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: roi,
      scale: 500,
      maxPixels: 1e9
    });
    
    return ee.Feature(null, {
      'date': image.date().format('YYYY-MM-dd'),
      'snow_fraction': stats.get('snow_cover'),
      'system:time_start': image.get('system:time_start')
    });
  });
  
  return ee.FeatureCollection(snowStats);
}
```

### Visualisation avec masques de qualité

```javascript
// Paramètres de visualisation
var snowVis = {
  min: 0,
  max: 100,
  palette: ['black', '0dffff', '0524ff', 'ffffff']
};

// Afficher une image avec différents niveaux de qualité
var sampleImage = maskedSnow.first();

// Couche originale
Map.addLayer(sampleImage.select('NDSI_Snow_Cover'), 
             snowVis, 'NDSI Snow Cover (masked)');

// Afficher les bits de QA individuellement
var qa_flags = snowCollection.first()
  .select('NDSI_Snow_Cover_Algorithm_Flags_QA');

Map.addLayer(getQABits(qa_flags, 0, 0, 'NDSI_Snow_Cover_Algorithm_Flags_QA'),
             {min: 0, max: 1, palette: ['white', 'blue']}, 
             'Inland Water (bit 0)');

Map.addLayer(getQABits(qa_flags, 7, 7, 'NDSI_Snow_Cover_Algorithm_Flags_QA'),
             {min: 0, max: 1, palette: ['green', 'red']}, 
             'High Solar Zenith (bit 7)');
```

## Références

- Hall, D.K., Riggs, G.A., Román, M.O. (2019). MODIS Snow Products Collection 6.1 User Guide. NASA.
- Documentation officielle NSIDC : https://nsidc.org/data/mod10a1/versions/61
- Google Earth Engine Developers Guide : https://developers.google.com/earth-engine
- Spatial Thoughts (2021). Working with QA Bands and Bitmasks in Google Earth Engine