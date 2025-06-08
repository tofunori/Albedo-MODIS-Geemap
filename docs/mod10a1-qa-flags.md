# MOD10A1 Quality Assessment Flags Reference

## Overview
This document provides a detailed reference for interpreting the Quality Assessment (QA) flags in the MOD10A1 MODIS Terra Snow Cover Daily product.

## NDSI_Snow_Cover_Basic_QA

Basic quality assessment values that provide a qualitative estimate of the algorithm result:

| Value | Quality Level | Description |
|-------|--------------|-------------|
| 0 | Best | Highest quality result |
| 1 | Good | Good quality, minor uncertainties |
| 2 | OK | Acceptable quality, increased uncertainty (70° ≤ SZA < 85°) |
| 3 | Poor | Not used in MOD10A1 |
| 4 | Other | Not used in MOD10A1 |
| 211 | Night | Solar zenith angle ≥ 85° |
| 239 | Ocean | Ocean mask applied |
| 255 | No data | Unusable input or missing data |

## NDSI_Snow_Cover_Algorithm_Flags_QA

Algorithm-specific bit flags that indicate data screen results. Convert decimal values to binary to interpret individual bits.

### Bit Flag Definitions

| Bit | Screen Name | Description | Action |
|-----|------------|-------------|--------|
| **0** | Inland Water | Identifies inland water bodies | Pixel set to 237 in NDSI_Snow_Cover |
| **1** | Low Visible Reflectance | Visible reflectance < 0.07 | Result set to 'no decision' (201) |
| **2** | Low NDSI | NDSI < 0.1 | Snow detection reversed to 'not snow' |
| **3** | Temperature/Height | Combined screen based on elevation and temperature | See detailed rules below |
| **4** | High SWIR | Shortwave IR reflectance anomaly | See detailed rules below |
| **5** | Cloud Possible - Cloudy | MOD35_L2 indicates probably cloudy | Flag set for cloud confusion |
| **6** | Cloud Possible - Clear | MOD35_L2 indicates probably clear | Flag set for evaluation |
| **7** | Low Illumination | Solar zenith angle > 70° | Increased uncertainty flagged |

### Detailed Screen Rules

#### Bit 3: Temperature/Height Screen
- **Low elevation (< 1300m) + Warm (Tb ≥ 281K)**: Snow reversed to 'not snow'
- **High elevation (≥ 1300m) + Warm (Tb ≥ 281K)**: Flagged as unusual but kept as snow

#### Bit 4: High SWIR Reflectance Screen
- **SWIR > 0.45**: Snow detection reversed to 'not snow'
- **0.25 < SWIR ≤ 0.45**: Flagged as unusual snow condition, detection not reversed

## NDSI_Snow_Cover Values

Main data values indicating snow cover status:

| Value Range | Meaning |
|-------------|---------|
| 0-100 | NDSI snow cover percentage |
| 200 | Missing data |
| 201 | No decision |
| 211 | Night |
| 237 | Inland water |
| 239 | Ocean |
| 250 | Cloud |
| 254 | Detector saturated |
| 255 | Fill |

## Usage in Code

### Example: Decoding bit flags in Python

```python
def decode_qa_flags(qa_value):
    """Decode MOD10A1 Algorithm QA flags"""
    if qa_value == 255:  # Fill value
        return None
    
    flags = {
        'inland_water': bool(qa_value & (1 << 0)),
        'low_visible': bool(qa_value & (1 << 1)),
        'low_ndsi': bool(qa_value & (1 << 2)),
        'temp_height': bool(qa_value & (1 << 3)),
        'high_swir': bool(qa_value & (1 << 4)),
        'cloud_maybe_cloudy': bool(qa_value & (1 << 5)),
        'cloud_maybe_clear': bool(qa_value & (1 << 6)),
        'low_illumination': bool(qa_value & (1 << 7))
    }
    return flags

# Example usage
qa_value = 129  # Binary: 10000001
flags = decode_qa_flags(qa_value)
# Result: inland_water=True, low_illumination=True, others=False
```

### Quality Filtering Best Practices

1. **Strictest filtering (highest confidence)**:
   - Basic QA = 0 (best quality only)
   - No algorithm flags set (Algorithm QA = 0)

2. **Standard filtering**:
   - Basic QA ≤ 1 (best + good)
   - Exclude critical flags (bits 1, 2, 5)

3. **Relaxed filtering**:
   - Basic QA ≤ 2 (best + good + ok)
   - Evaluate flags case by case

## References

- Hall, D. K. and G. A. Riggs. 2021. MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid, Version 61
- Riggs, G.A., Hall, D.K. and Roman, M.O. 2019. MODIS Snow Products Collection 6.1 User Guide
- Full user guide: `mod10a1-user-guide.md`