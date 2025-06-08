# Méthodes d'interpolation et de remplissage des pixels manquants dans les produits MODIS

## 1. Introduction

Les produits de couverture neigeuse MODIS (MOD10A1/MYD10A1) souffrent de lacunes importantes dues principalement à la couverture nuageuse, qui peut représenter jusqu'à 50% des observations dans certaines régions. Ces lacunes limitent considérablement l'utilisation opérationnelle de ces données pour le suivi de la couverture neigeuse. Plusieurs méthodes ont été développées pour combler ces lacunes.

## 2. Principales approches de gap-filling

### 2.1 Cloud-Gap-Filled (CGF) officiel - MOD10A1F

Le produit MOD10A1F (Collection 6.1) est la solution officielle de la NASA pour le remplissage des pixels nuageux.

**Principe** : Conservation de la dernière observation claire
- Si un pixel est nuageux aujourd'hui, utiliser la valeur du dernier jour clair
- Un compteur "Cloud_Persistence" trace le nombre de jours depuis la dernière observation claire

**Avantages** :
- Simple et robuste
- Produit officiel avec support
- Préserve l'intégrité des observations originales

**Limitations** :
- Ne capte pas les changements sous les nuages
- Performance réduite dans les régions à neige transitoire
- Peut manquer des événements de chute/fonte de neige

### 2.2 Combinaison Terra-Aqua (TAC)

Fusion des produits MOD10A1 (Terra) et MYD10A1 (Aqua) du même jour.

**Règle de combinaison** :
1. Si les deux montrent de la neige → neige
2. Si un seul est clair → utiliser cette valeur
3. Si les deux sont nuageux → reste nuageux

```javascript
// Google Earth Engine - Combinaison Terra-Aqua
function combineTerraAqua(date) {
  var terra = ee.Image(
    ee.ImageCollection('MODIS/006/MOD10A1')
      .filterDate(date, date.advance(1, 'day'))
      .first()
  );
  
  var aqua = ee.Image(
    ee.ImageCollection('MODIS/006/MYD10A1')
      .filterDate(date, date.advance(1, 'day'))
      .first()
  );
  
  // Extraire NDSI Snow Cover
  var terraNDSI = terra.select('NDSI_Snow_Cover');
  var aquaNDSI = aqua.select('NDSI_Snow_Cover');
  
  // Règle de combinaison : priorité aux valeurs claires
  var combined = terraNDSI.where(
    terraNDSI.eq(250), // Si Terra est nuageux
    aquaNDSI          // Utiliser Aqua
  );
  
  return combined.copyProperties(terra, ['system:time_start']);
}
```

### 2.3 Interpolation temporelle

Plusieurs méthodes d'interpolation temporelle peuvent être utilisées pour estimer les valeurs manquantes basées sur l'évolution temporelle du phénomène observé.

#### a) Interpolation linéaire

L'interpolation linéaire assume une variation linéaire entre deux observations valides.

```javascript
// Google Earth Engine - Interpolation linéaire temporelle détaillée
function linearInterpolation(collection, maxGapDays) {
  // Convertir maxGap en millisecondes
  var maxGap = ee.Number(maxGapDays).multiply(86400000);
  
  // Fonction pour interpoler une seule valeur
  var interpolateValue = function(before, after, target) {
    var t1 = before.date().millis();
    var t2 = after.date().millis();
    var t = target.date().millis();
    
    // Facteur d'interpolation
    var factor = ee.Number(t.subtract(t1))
      .divide(t2.subtract(t1));
    
    // Valeurs NDSI
    var v1 = before.select('NDSI_Snow_Cover');
    var v2 = after.select('NDSI_Snow_Cover');
    
    // Interpolation linéaire : v = v1 + (v2 - v1) * factor
    var interpolated = v1.add(v2.subtract(v1).multiply(factor));
    
    return target.addBands(interpolated, null, true);
  };
  
  // Appliquer sur toute la collection
  var filled = collection.map(function(image) {
    var cloudMask = image.select('NDSI_Snow_Cover').eq(250);
    
    if (cloudMask.reduceRegion(ee.Reducer.any()).get('NDSI_Snow_Cover')) {
      // Trouver les images valides avant et après
      var date = image.date();
      var before = collection
        .filterDate(date.advance(-maxGapDays, 'day'), date)
        .filter(ee.Filter.neq('NDSI_Snow_Cover', 250))
        .sort('system:time_start', false)
        .first();
      var after = collection
        .filterDate(date, date.advance(maxGapDays, 'day'))
        .filter(ee.Filter.neq('NDSI_Snow_Cover', 250))
        .sort('system:time_start')
        .first();
      
      return ee.Image(ee.Algorithms.If(
        ee.Algorithms.IsEqual(before, null).or(ee.Algorithms.IsEqual(after, null)),
        image,
        interpolateValue(before, after, image)
      ));
    }
    return image;
  });
  
  return filled;
}
```

#### b) Spline cubique (CSI - Cubic Spline Interpolation)

La spline cubique offre une interpolation plus douce qui capture mieux les transitions graduelles de la couverture neigeuse.

```javascript
// Implémentation simplifiée de spline cubique dans GEE
function cubicSplineInterpolation(collection, windowSize) {
  // Fonction pour calculer les coefficients de spline
  var calculateSplineCoefficients = function(times, values) {
    // Simplification : utiliser une approximation polynomiale
    var n = times.size();
    
    // Calculer les différences
    var h = times.slice(1).zip(times.slice(0,-1))
      .map(function(pair) {
        return ee.Number(ee.List(pair).get(0))
          .subtract(ee.List(pair).get(1));
      });
    
    // Système tridiagonal (simplifié)
    // Dans une vraie implémentation, résoudre Ax = b
    return values; // Placeholder
  };
  
  // Application sur chaque pixel
  var interpolated = collection.map(function(image) {
    var date = image.date();
    var window = collection.filterDate(
      date.advance(-windowSize, 'day'),
      date.advance(windowSize, 'day')
    );
    
    // Extraire les valeurs valides
    var validData = window
      .filter(ee.Filter.neq('NDSI_Snow_Cover', 250))
      .sort('system:time_start');
    
    var times = validData.aggregate_array('system:time_start');
    var values = validData.aggregate_array('NDSI_Snow_Cover');
    
    // Si assez de points, interpoler
    return ee.Image(ee.Algorithms.If(
      times.size().gte(4),
      image.set('interpolated', true),
      image
    ));
  });
  
  return interpolated;
}
```

#### c) Interpolation adaptative avec poids temporels

Cette méthode attribue des poids décroissants aux observations selon leur distance temporelle.

```javascript
// Interpolation pondérée temporelle
function weightedTemporalInterpolation(collection, halfLife) {
  return collection.map(function(image) {
    var targetDate = image.date();
    var cloudMask = image.select('NDSI_Snow_Cover').eq(250);
    
    // Calculer les poids basés sur la distance temporelle
    var weights = collection.map(function(img) {
      var timeDiff = targetDate.difference(img.date(), 'day').abs();
      var weight = ee.Number(1).divide(
        ee.Number(1).add(timeDiff.divide(halfLife).pow(2))
      );
      return img.addBands(ee.Image.constant(weight).rename('weight'));
    });
    
    // Moyenne pondérée
    var weighted = weights
      .filter(ee.Filter.neq('NDSI_Snow_Cover', 250))
      .map(function(img) {
        return img.select('NDSI_Snow_Cover')
          .multiply(img.select('weight'));
      });
    
    var sumWeights = weights
      .filter(ee.Filter.neq('NDSI_Snow_Cover', 250))
      .select('weight')
      .sum();
    
    var interpolated = weighted.sum().divide(sumWeights);
    
    return image.where(cloudMask, interpolated);
  });
}
```

### 2.4 Méthodes spatio-temporelles

#### a) Filtrage spatio-temporel pondéré (STW)

Utilise l'information des pixels voisins dans l'espace et le temps.

```javascript
// Google Earth Engine - Filtre spatio-temporel simple
function spatioTemporalFilter(collection, kernelSize, temporalWindow) {
  var kernel = ee.Kernel.square(kernelSize, 'pixels');
  
  var stFilter = function(image) {
    var date = image.date();
    
    // Fenêtre temporelle
    var start = date.advance(-temporalWindow, 'day');
    var end = date.advance(temporalWindow, 'day');
    
    // Images voisines temporellement
    var neighbors = collection.filterDate(start, end);
    
    // Moyenne pondérée spatio-temporelle
    var mean = neighbors.mean()
      .focal_mean(kernelSize, 'square', 'pixels');
    
    // Remplacer les pixels nuageux
    var filled = image.where(
      image.select('NDSI_Snow_Cover').eq(250),
      mean.select('NDSI_Snow_Cover')
    );
    
    return filled;
  };
  
  return collection.map(stFilter);
}
```

#### b) Méthode du cube spatio-temporel (STCPI)

Calcule la probabilité conditionnelle basée sur un cube 5×5×5 (spatial × spatial × temporel).

```javascript
// Structure conceptuelle STCPI
function stcpiGapFilling(collection, cubeSize) {
  // Pour chaque pixel nuageux :
  // 1. Extraire un cube spatio-temporel autour du pixel
  // 2. Calculer les probabilités conditionnelles
  // 3. Déterminer l'état le plus probable (neige/non-neige)
  
  var fillGaps = function(image) {
    var cloudMask = image.select('NDSI_Snow_Cover').eq(250);
    
    // Extraire le voisinage spatio-temporel
    var neighbors = extractSTCube(image, collection, cubeSize);
    
    // Calculer les probabilités
    var snowProbability = calculateConditionalProbability(neighbors);
    
    // Appliquer le seuil de décision
    var filled = image.where(
      cloudMask,
      snowProbability.gt(0.5).multiply(100) // Convertir en NDSI
    );
    
    return filled;
  };
  
  return collection.map(fillGaps);
}
```

### 2.5 Méthodes avancées

#### a) Non-Local Spatio-Temporal Filtering (NSTF)

Utilise des pixels similaires non-adjacents basés sur l'apprentissage automatique.

**Principe** :
- Recherche de pixels similaires dans toute l'image
- Pondération basée sur la similarité spectrale et temporelle
- Remplissage par moyenne pondérée

#### b) Machine Learning et Deep Learning

Approches récentes utilisant des réseaux de neurones pour prédire les valeurs manquantes.

```javascript
// Exemple conceptuel - Préparation des données pour ML
function prepareMLFeatures(collection, targetDate) {
  // Features temporels
  var before = collection
    .filterDate(targetDate.advance(-30, 'day'), targetDate)
    .mean();
    
  var after = collection
    .filterDate(targetDate, targetDate.advance(30, 'day'))
    .mean();
  
  // Features spatiaux
  var spatial = ee.Image(collection.filterDate(targetDate).first())
    .focal_mean(3)
    .focal_std(3);
  
  // Features topographiques
  var elevation = ee.Image('USGS/SRTMGL1_003');
  var slope = ee.Terrain.slope(elevation);
  var aspect = ee.Terrain.aspect(elevation);
  
  // Combiner toutes les features
  return ee.Image.cat([
    before, after, spatial, 
    elevation, slope, aspect
  ]).float();
}
```

## 3. Comparaison des méthodes

| Méthode | Précision | Complexité | Temps de calcul | Cas d'usage optimal |
|---------|-----------|------------|-----------------|---------------------|
| CGF (MOD10A1F) | Moyenne | Faible | Rapide | Monitoring opérationnel |
| TAC | Bonne | Faible | Rapide | Réduction immédiate des nuages |
| Interpolation linéaire | Moyenne | Moyenne | Moyen | Séries temporelles régulières |
| Spline cubique | Bonne | Élevée | Lent | Transitions graduelles |
| STW | Très bonne | Élevée | Lent | Régions hétérogènes |
| STCPI | Excellente | Très élevée | Très lent | Haute précision requise |
| NSTF | Excellente | Très élevée | Très lent | Recherche avancée |

## 4. Implémentation complète dans GEE

Voici un exemple complet combinant plusieurs approches :

```javascript
// Pipeline complet de gap-filling pour MOD10A1
var gapFillPipeline = function(roi, startDate, endDate) {
  
  // 1. Charger et combiner Terra-Aqua
  var terra = ee.ImageCollection('MODIS/006/MOD10A1')
    .filterBounds(roi)
    .filter(ee.Filter.date(startDate, endDate))
    .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Basic_QA']);
    
  var aqua = ee.ImageCollection('MODIS/006/MYD10A1')
    .filterBounds(roi)
    .filter(ee.Filter.date(startDate, endDate))
    .select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Basic_QA']);
  
  // Fonction de combinaison Terra-Aqua
  var combineTerraAqua = function(date) {
    var dateStr = ee.Date(date).format('YYYY-MM-dd');
    var t = terra.filterDate(date, date.advance(1, 'day')).first();
    var a = aqua.filterDate(date, date.advance(1, 'day')).first();
    
    return ee.Image(ee.Algorithms.If(
      t,
      ee.Image(ee.Algorithms.If(
        a,
        t.blend(a.updateMask(t.select('NDSI_Snow_Cover').eq(250))),
        t
      )),
      a
    )).set('system:time_start', date.millis());
  };
  
  // 2. Créer la collection combinée
  var dateRange = ee.List.sequence(
    startDate.millis(), 
    endDate.millis(), 
    86400000 // 1 jour en millisecondes
  );
  
  var combined = ee.ImageCollection.fromImages(
    dateRange.map(function(d) {
      return combineTerraAqua(ee.Date(d));
    }).filter(ee.Filter.notNull(['system:time_start']))
  );
  
  // 3. Appliquer un filtre temporel
  var temporalFilter = function(image) {
    var date = image.date();
    var before = combined
      .filterDate(date.advance(-3, 'day'), date)
      .mean();
    var after = combined
      .filterDate(date.advance(1, 'day'), date.advance(4, 'day'))
      .mean();
    
    var temporal = before.blend(after).focal_mean(1);
    
    return image.where(
      image.select('NDSI_Snow_Cover').eq(250),
      temporal.select('NDSI_Snow_Cover')
    );
  };
  
  // 4. Appliquer le gap-filling
  var gapFilled = combined.map(temporalFilter);
  
  // 5. Post-traitement : lisser les transitions
  var smoothed = gapFilled.map(function(image) {
    return image.focal_median(1.5, 'circle', 'pixels');
  });
  
  return smoothed;
};

// Utilisation
var roi = ee.Geometry.Rectangle([70, 30, 80, 40]);
var filled = gapFillPipeline(
  roi, 
  ee.Date('2020-01-01'), 
  ee.Date('2020-12-31')
);

// Visualisation
Map.centerObject(roi, 6);
Map.addLayer(
  filled.select('NDSI_Snow_Cover').median(),
  {min: 0, max: 100, palette: ['black', 'white']},
  'Gap-filled NDSI'
);
```

## 5. Évaluation et validation

### Métriques d'évaluation

1. **Overall Accuracy (OA)** : Précision globale
2. **RMSE** : Erreur quadratique moyenne
3. **R²** : Coefficient de détermination
4. **Spatial Efficiency (SPAEF)** : Efficacité spatiale

### Méthode de validation "Cloud Assumption"

```javascript
// Validation par simulation de nuages
function cloudAssumptionValidation(original, gapFilled, cloudFraction) {
  // Créer un masque de nuages artificiel
  var randomCloud = ee.Image.random()
    .lt(cloudFraction)
    .rename('cloud_mask');
  
  // Appliquer le masque
  var masked = original.updateMask(randomCloud.not());
  
  // Comparer avec le gap-filled
  var diff = gapFilled.subtract(original).abs();
  
  // Calculer les métriques
  var rmse = diff.reduceRegion({
    reducer: ee.Reducer.mean(),
    scale: 500,
    maxPixels: 1e9
  });
  
  return rmse;
}
```

## 6. Recommandations pratiques

1. **Pour un usage opérationnel** : Utiliser MOD10A1F ou TAC simple
2. **Pour des analyses temporelles** : Interpolation temporelle (linéaire ou spline)
3. **Pour des régions complexes** : Méthodes spatio-temporelles
4. **Pour la recherche avancée** : NSTF ou approches ML

### Considérations importantes

- La persistance des nuages au-delà de 7 jours réduit significativement la fiabilité
- Les méthodes spatiales fonctionnent mieux dans les régions homogènes
- L'interpolation temporelle assume des changements graduels
- Toujours valider avec des données indépendantes (Landsat, stations météo)

## Références

1. Hall et al. (2010). Development and evaluation of a cloud-gap-filled MODIS daily snow-cover product. Remote Sensing of Environment, 114, 496-503.
2. Tang et al. (2020). A Conditional Probability Interpolation Method Based on a Space-Time Cube for MODIS Snow Cover Products Gap Filling. Remote Sensing, 12(21), 3577.
3. Muhammad & Thapa (2019). Gap-Filling of MODIS Fractional Snow Cover Products via Non-Local Spatio-Temporal Filtering. Remote Sensing, 11(1), 90.
4. Li et al. (2024). MODIS daily cloud-gap-filled fractional snow cover dataset of the Asian Water Tower region (2000–2022). Earth System Science Data, 16, 2501-2523.