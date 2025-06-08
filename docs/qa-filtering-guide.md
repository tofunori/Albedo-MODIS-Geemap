# Guide Complet du Filtrage Qualité MOD10A1/MYD10A1

## Vue d'ensemble

Ce guide détaille les différents niveaux de filtrage qualité disponibles pour les données MODIS MOD10A1/MYD10A1 dans votre analyse d'albédo du glacier Athabasca. L'implémentation suit les meilleures pratiques de Williamson & Menounos (2021) pour l'analyse glaciaire.

## 🏔️ Contexte Scientifique

L'analyse de l'albédo glaciaire nécessite des données de haute qualité pour:
- **Tests statistiques robustes** (Mann-Kendall, pente de Sen)
- **Détection de tendances fiables** sur les séries temporelles
- **Éviter les faux signaux** causés par la contamination (nuages, eau, neige de faible qualité)
- **Conformité aux standards scientifiques** pour publication

## 📊 Niveaux de Filtrage Disponibles

### 1️⃣ Standard QA (Basic QA seulement)
**Système original - Filtrage minimal**

```python
use_advanced_qa=False
qa_level='standard'  # Non utilisé dans ce mode
```

#### Critères de filtrage:
- **Basic QA ≤ 1**: Qualité "best" (0) et "good" (1) uniquement
- **Plage albédo**: 5-99 avant mise à l'échelle (0.05-0.99 après)
- **Aucun filtrage Algorithm flags**

#### Avantages:
- ✅ **Maximum de couverture temporelle**
- ✅ **Traitement rapide**
- ✅ **Compatible avec analyses précédentes**

#### Inconvénients:
- ⚠️ **Peut inclure pixels contaminés** (nuages, eau)
- ⚠️ **Moins robuste statistiquement**
- ⚠️ **Non optimal pour Williamson & Menounos (2021)**

#### Utilisation recommandée:
- Analyses exploratoires
- Comparaison avec résultats antérieurs
- Situations nécessitant maximum de données

---

### 2️⃣ Advanced QA Relaxed
**Filtrage intermédiaire - Équilibre données/qualité**

```python
use_advanced_qa=True
qa_level='relaxed'
```

#### Critères de filtrage:
- **Basic QA ≤ 2**: Qualité "best" (0), "good" (1) et "ok" (2)
- **Plage albédo**: 5-99 avant mise à l'échelle
- **Algorithm flags filtrés**:
  - ❌ Bit 0: Eau continentale (toujours exclu)
  - ❌ Bit 1: Faible réflectance visible (toujours exclu)
  - ❌ Bit 2: Faible NDSI (toujours exclu)
  - ✅ Bit 3: Température/hauteur (permis - commun sur glaciers)
  - ❌ Bit 5: Nuages probables (toujours exclu)

#### Avantages:
- ✅ **Bon équilibre couverture/qualité**
- ✅ **Élimine contaminations critiques**
- ✅ **Préserve données glaciaires légitimes**

#### Inconvénients:
- ⚠️ **Peut inclure quelques pixels de qualité moyenne**
- ⚠️ **Moins strict que standards de publication**

#### Utilisation recommandée:
- Analyses préliminaires étendues
- Régions avec couverture nuageuse importante
- Études nécessitant longues séries temporelles

---

### 3️⃣ Advanced QA Standard ⭐ **RECOMMANDÉ**
**Filtrage optimisé - Williamson & Menounos (2021)**

```python
use_advanced_qa=True
qa_level='standard'
```

#### Critères de filtrage:
- **Basic QA ≤ 1**: Qualité "best" (0) et "good" (1) uniquement
- **Plage albédo**: 5-99 avant mise à l'échelle
- **Algorithm flags filtrés**:
  - ❌ Bit 0: Eau continentale
  - ❌ Bit 1: Faible réflectance visible
  - ❌ Bit 2: Faible NDSI
  - ✅ Bit 3: Température/hauteur (permis)
  - ❌ Bit 5: Nuages probables

#### Avantages:
- ✅ **Optimal pour analyses glaciaires**
- ✅ **Conforme Williamson & Menounos (2021)**
- ✅ **Robustesse statistique élevée**
- ✅ **Équilibre qualité/couverture**
- ✅ **Acceptable pour publication**

#### Inconvénients:
- ⚠️ **Réduction modérée des données** (~10-30%)
- ⚠️ **Traitement légèrement plus lent**

#### Utilisation recommandée:
- **Toutes analyses de routine** 🎯
- Travaux de recherche principaux
- Analyses de tendances temporelles
- Préparation de publications

---

### 4️⃣ Advanced QA Strict
**Filtrage maximal - Qualité publication**

```python
use_advanced_qa=True
qa_level='strict'
```

#### Critères de filtrage:
- **Basic QA = 0**: Qualité "best" uniquement
- **Plage albédo**: 5-99 avant mise à l'échelle
- **Algorithm flags filtrés** (TOUS):
  - ❌ Bit 0: Eau continentale
  - ❌ Bit 1: Faible réflectance visible
  - ❌ Bit 2: Faible NDSI
  - ❌ Bit 3: Température/hauteur
  - ❌ Bit 5: Nuages probables

#### Avantages:
- ✅ **Qualité maximale garantie**
- ✅ **Idéal pour publications**
- ✅ **Robustesse statistique maximale**
- ✅ **Aucune contamination**

#### Inconvénients:
- ⚠️ **Réduction significative des données** (30-50%)
- ⚠️ **Peut exclure données glaciaires valides**
- ⚠️ **Risque de sous-échantillonnage temporel**

#### Utilisation recommandée:
- Analyses finales pour publication
- Études de cas détaillées
- Validation de méthodes
- Comparaisons inter-études

---

## 🔬 Détails Techniques des Algorithm Flags

### Signification des Bits (MOD10A1 Algorithm QA)

| Bit | Signification | Impact Glaciaire | Filtrage |
|-----|---------------|------------------|----------|
| 0 | Eau continentale détectée | ❌ **Critique** - Fausse détection | Toujours exclu |
| 1 | Faible réflectance visible | ❌ **Critique** - Problème de détection | Toujours exclu |
| 2 | NDSI faible | ❌ **Critique** - Signal neige faible | Toujours exclu |
| 3 | Écran température/hauteur | ⚠️ **Modéré** - Commun en altitude | Exclu en mode strict seulement |
| 4 | Écran spatial | ⚠️ **Variable** - Dépend du contexte | Disponible pour personnalisation |
| 5 | Nuages probables | ❌ **Critique** - Contamination atmosphérique | Toujours exclu |
| 6 | Mauvais inversion aéroportée | ⚠️ **Variable** - Problème algorithmique | Disponible pour personnalisation |
| 7 | Réservé | - | Non utilisé |

### Logique de Filtrage

```python
# Exemple: Mode Standard
basic_quality = basic_qa.lte(1)  # QA ≤ 1
no_water = algo_qa.bitwiseAnd(1).eq(0)      # Bit 0 = 0
no_low_vis = algo_qa.bitwiseAnd(2).eq(0)    # Bit 1 = 0  
no_low_ndsi = algo_qa.bitwiseAnd(4).eq(0)   # Bit 2 = 0
# Bit 3 permis en mode standard
no_clouds = algo_qa.bitwiseAnd(32).eq(0)    # Bit 5 = 0

final_mask = basic_quality.And(no_water).And(no_low_vis).And(no_low_ndsi).And(no_clouds)
```

---

## 📈 Impact sur les Analyses

### Couverture Temporelle Attendue

| Niveau QA | Réduction Données | Observations/An | Robustesse Statistique |
|-----------|-------------------|-----------------|------------------------|
| Standard | 0% (référence) | ~120-150 | Modérée |
| Relaxed | 5-15% | ~100-130 | Bonne |
| **Standard** | **10-30%** | **80-120** | **Élevée** ⭐ |
| Strict | 30-50% | ~60-100 | Maximale |

### Tests Statistiques

#### Mann-Kendall & Sen's Slope
- **Minimum recommandé**: 30 observations/an
- **Optimal**: 60+ observations/an
- **Advanced QA améliore**: Puissance statistique, réduction faux positifs

#### Analyse de Tendances
- **Standard QA**: Peut détecter fausses tendances (contamination)
- **Advanced QA**: Tendances plus fiables et reproductibles

---

## 🚀 Guide d'Utilisation Pratique

### 1. Choix du Niveau QA

```
Analyse exploratoire → Relaxed
Recherche de routine → Standard ⭐
Publication finale → Strict
Comparaison historique → Standard (original)
```

### 2. Interface Main.py

Lors du lancement de `python main.py` option 1:

```
⚙️  FILTRAGE QUALITÉ DES DONNÉES:
1️⃣ Standard QA (Basic QA seulement) - Maximum de données
2️⃣ Advanced QA Relaxed - Bon équilibre données/qualité
3️⃣ Advanced QA Standard - Recommandé pour la plupart des analyses
4️⃣ Advanced QA Strict - Qualité maximale pour publications

🔸 Votre choix de qualité (1-4) [3]:
```

### 3. Usage Programmatique

```python
from src.workflows.melt_season import run_melt_season_analysis_williamson

# Pour la plupart des analyses
results = run_melt_season_analysis_williamson(
    start_year=2020,
    end_year=2024,
    use_advanced_qa=True,
    qa_level='standard'
)

# Pour analyses de publication
results = run_melt_season_analysis_williamson(
    start_year=2020,
    end_year=2024,
    use_advanced_qa=True,
    qa_level='strict'
)
```

### 4. Comparaison des Méthodes

Utilisez le script de comparaison pour évaluer l'impact:

```bash
python run_qa_comparison.py
```

---

## 📚 Références et Justification Scientifique

### Williamson & Menounos (2021)
- **Filtrage QA strict** pour analyses glaciaires
- **Exclusion contamination atmosphérique** (nuages, aérosols)
- **Focus sur données haute confiance** pour tendances climatiques

### Standards MODIS Collection 6.1
- **QA flags hierarchiques**: Basic QA + Algorithm flags
- **Approche conservative** recommandée pour études climatiques
- **Documentation complète** des critères qualité

### Meilleures Pratiques
- **Tests de sensibilité** aux critères QA
- **Documentation méthodologique** détaillée
- **Comparaison multi-niveaux** pour validation

---

## ⚠️ Considérations Importantes

### Limitations Géographiques
- **Haute latitude**: Problèmes illumination solaire
- **Terrain complexe**: Effets topographiques
- **Couverture nuageuse**: Réduction temporelle

### Considérations Temporelles
- **Début/fin saison**: Moins d'observations valides
- **Conditions météo**: Variabilité inter-annuelle
- **Évolution instrumentale**: Cohérence long-terme

### Recommandations Méthodologiques
1. **Toujours documenter** le niveau QA utilisé
2. **Tester sensibilité** aux critères choisis
3. **Comparer résultats** entre niveaux QA
4. **Justifier choix** dans publications

---

## 🎯 Résumé Exécutif

| Aspect | Recommandation |
|--------|----------------|
| **Usage général** | Advanced QA Standard |
| **Publications** | Advanced QA Strict |
| **Exploration** | Advanced QA Relaxed |
| **Compatibilité** | Standard QA |
| **Documentation** | Toujours spécifier niveau utilisé |

**L'Advanced QA Standard offre le meilleur équilibre entre qualité scientifique et couverture temporelle pour l'analyse du glacier Athabasca.** ⭐