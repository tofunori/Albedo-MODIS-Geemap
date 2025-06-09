# Références Scientifiques - Fusion Terra-Aqua pour Albédo Glaciaire

## Références Principales (2022-2024)

### 1. Liu et al. (2024) - Plateau Tibétain
**Citation complète:**
```
Liu, P., Wu, G., Cao, B., Zhao, X., & Chen, Y. (2024). 
Variation in Glacier Albedo on the Tibetan Plateau between 2001 and 2022 Based on MODIS Data. 
Remote Sensing, 16(18), 3472. 
https://doi.org/10.3390/rs16183472
```

**Résumé:**
- **Publié**: 19 septembre 2024 (très récent)
- **Période d'étude**: 2001-2022
- **Données**: MOD10A1 (Terra prioritaire)
- **Région**: Plateau Tibétain
- **Contribution**: Analyse des variations spatiotemporelles d'albédo glaciaire sur 22 ans
- **Constats**: Albédo glaciaire principalement entre 0.50-0.60, plus élevé printemps/hiver, plus bas été

### 2. Wang et al. (2024) - Asian Water Tower
**Citation complète:**
```
Wang, X., Che, T., Dai, L., Zheng, Z., Li, X., & Jiang, L. (2024). 
MODIS daily cloud-gap-filled fractional snow cover dataset of the Asian Water Tower region (2000–2022). 
Earth System Science Data, 16, 2501-2525. 
https://doi.org/10.5194/essd-16-2501-2024
```

**Résumé:**
- **Période d'étude**: 2000-2022
- **Méthodologie**: MESMA-AGE + MSTI pour fusion Terra-Aqua
- **Stratégie**: Terra comme base, Aqua pour gap-filling
- **Innovation**: Cloud-gap-filled fractional snow cover quotidien
- **Région**: Asian Water Tower (High Mountain Asia)

### 3. Xie et al. (2024) - Karakoram
**Citation complète:**
```
Xie, S., Wang, X., Xiang, Y., Pu, T., Kang, S., & Du, W. (2024). 
Seasonal and interannual variability of Karakoram glacier surface albedo from AVHRR-MODIS data, 1982–2020. 
Global and Planetary Change, 342, 104557.
https://doi.org/10.1016/j.gloplacha.2024.104557
```

**Résumé:**
- **Période d'étude**: 1982-2020 (38 ans)
- **Données**: AVHRR + MODIS (multi-capteurs)
- **Région**: Karakoram (Pakistan)
- **Constats**: Diminution albédo glaciaire 2000-2020, liée à réduction précipitations et hausse températures
- **Variabilité**: Hétérogénéité spatiotemporelle significative

## Références Fondamentales (2020-2021)

### 4. Muhammad & Thapa (2021) - High Mountain Asia
**Citation complète:**
```
Muhammad, S. & Thapa, A. (2021). 
Daily Terra–Aqua MODIS cloud-free snow and Randolph Glacier Inventory 6.0 combined product (M*D10A1GL06) 
for high-mountain Asia between 2002 and 2019. 
Earth System Science Data, 13, 767-776. 
https://doi.org/10.5194/essd-13-767-2021
```

**Contribution clé:**
- **Priorité Terra explicite**: "Priority was given to the Terra product since the Aqua MODIS instrument provides less accurate snow maps due to dysfunction of band 6 on Aqua"
- **Méthodologie M*D10A1GL06**: Produit combiné quotidien Terra-Aqua + RGI 6.0
- **Gap-filling**: Terra d'abord, Aqua pour combler manques
- **Période**: 2002-2019, High Mountain Asia

### 5. Muhammad & Thapa (2020) - MOYDGL06*
**Citation complète:**
```
Muhammad, S. & Thapa, A. (2020). 
An improved Terra–Aqua MODIS snow cover and Randolph Glacier Inventory 6.0 combined product (MOYDGL06*) 
for high-mountain Asia between 2002 and 2018. 
Earth System Science Data, 12, 345-356. 
https://doi.org/10.5194/essd-12-345-2020
```

**Contribution:**
- **Validation croisée**: "Consider snow only where pixels in both products are classified as snow"
- **Réduction biais**: Sous-estimation (nuages) et sur-estimation (angle solaire)
- **Composite 8-jours**: Base pour produits quotidiens améliorés

## Références Validation (2005-2006)

### 6. Stroeve et al. (2005) - Validation Groenland
**Citation complète:**
```
Stroeve, J., Box, J. E., Gao, F., Liang, S., Nolin, A., & Schaaf, C. (2005). 
Evaluation of the MODIS (MOD10A1) daily snow albedo product over the Greenland ice sheet. 
Remote Sensing of Environment, 105(2), 155-171. 
https://doi.org/10.1016/j.rse.2005.11.009
```

**Validation quantitative:**
- **MOD10A1 (Terra)**: RMS error = 0.067
- **MYD10A1 (Aqua)**: RMS error = 0.075
- **Conclusion**: Terra légèrement plus précis qu'Aqua
- **Période**: Validation avec 5 stations météo automatiques Groenland

## Références Gap-Filling Récentes

### 7. Dong et al. (2024) - NDSI Gap-Filling
**Citation complète:**
```
Dong, J., Li, S., Yu, W., Li, X., Yang, K., Du, M., Zhang, G., Zhou, J., Zhao, Q., & Chen, S. (2024). 
Development and Evaluation of a Cloud-Gap-Filled MODIS Normalized Difference Snow Index Product 
over High Mountain Asia. 
Remote Sensing, 16(1), 192. 
https://doi.org/10.3390/rs16010192
```

**Innovation:**
- **CGF method**: Combine interpolation cubique spline + méthode spatio-temporelle pondérée
- **Terra-Aqua NDSI**: Produit quotidien gap-filled 2000-2021
- **Région**: High Mountain Asia

## Documentation Technique MODIS

### 8. MODIS Snow Products Collection 6.1 User Guide
**Citation:**
```
Riggs, G. A., Hall, D. K., & Roman, M. O. (2019). 
MODIS Snow Products Collection 6.1 User Guide. 
NASA Goddard Space Flight Center.
```

### 9. NSIDC MOD10A1 Documentation
**Citation:**
```
Hall, D. K. & Riggs, G. A. (2021). 
MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid, Version 61 [Data Set]. 
Boulder, Colorado USA. NASA National Snow and Ice Data Center Distributed Active Archive Center. 
https://doi.org/10.5067/MODIS/MOD10A1.061
```

## Synthèse Méthodologique

### Consensus Scientifique 2024:
1. **Terra prioritaire** sur Aqua (dysfonctionnement bande 6, RMS plus faible)
2. **Gap-filling hiérarchique** (Terra → Aqua si manquant)
3. **Composite quotidien** (éviter pseudo-réplication)
4. **Validation croisée** optionnelle (accord Terra-Aqua)

### Justification pour Votre Méthode:
```
"Following established best practices for Terra-Aqua MODIS data fusion in glacier studies 
(Liu et al., 2024; Wang et al., 2024; Muhammad & Thapa, 2021), we implemented a daily 
composite approach prioritizing Terra observations due to superior accuracy (Stroeve et al., 2005) 
and band 6 reliability issues in Aqua (Muhammad & Thapa, 2021). Aqua data were used for 
gap-filling when Terra observations were unavailable or of poor quality, consistent with 
recent methodologies for High Mountain Asia glacier monitoring."
```

### Evolution Temporelle:
- **2005**: Validation Terra > Aqua (Stroeve et al.)
- **2020-2021**: Méthodes gap-filling sophistiquées (Muhammad & Thapa)
- **2024**: Machine learning + fusion avancée (Liu, Wang, Xie et al.)

## Notes sur l'Évolution des Satellites
- **Terra**: Drift orbital, crossing équateur plus tôt
- **Aqua**: Constellation exit janvier 2022, fin mission août 2026
- **Impact**: Nécessité transition vers autres capteurs (VIIRS, Sentinel)

---
*Document mis à jour: 6 janvier 2025*
*Projet: Analyse albédo glacier Athabasca - Méthodologie Terra-Aqua*