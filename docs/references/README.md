# Reference Documentation

Contains official documentation, user guides, and reference materials for MODIS data products.

## Files

### **`mod10a1-v061-userguide_1.pdf`**
- **Type**: Official NASA user guide
- **Product**: MOD10A1/MYD10A1 Version 6.1
- **Description**: Comprehensive user guide for MODIS daily snow albedo products
- **Usage**: Reference for understanding data structure, QA flags, and processing algorithms

### **`mod10a1-qa-flags.md`**
- **Type**: Technical documentation
- **Description**: Detailed explanation of quality assessment flags for MOD10A1/MYD10A1
- **Usage**: Reference for implementing QA filtering in analysis code
- **Content**: 
  - NDSI Snow Cover Basic QA interpretation
  - Algorithm flags bit definitions
  - Quality level recommendations

### **`modis-gap-filling-interpolation.md`**
- **Type**: Technical methodology
- **Description**: Methods for handling missing MODIS data
- **Usage**: Reference for implementing gap-filling techniques
- **Note**: Contains JavaScript (Google Earth Engine) examples that need Python conversion

## Usage

### Quick Reference
```python
# For QA filtering implementation, see:
# docs/references/mod10a1-qa-flags.md

# For gap-filling techniques, see:
# docs/references/modis-gap-filling-interpolation.md
```

### Integration with Code
- **QA filtering**: `src/core/qa_filtering.py` implements methods described in these docs
- **Gap filling**: `src/data/processors/` contains gap-filling implementations
- **Validation**: `tests/qa_validation/` includes tests based on these specifications

## Important Notes
- ⚠️ **JavaScript Examples**: The gap-filling document contains Google Earth Engine JavaScript code that needs adaptation for Python
- 📚 **Official Source**: Always refer to the latest NASA documentation for updates
- 🔗 **Cross-Reference**: These docs support the methodology described in `docs/methodology.md`

## External Links
- [NASA MODIS Documentation](https://modis.gsfc.nasa.gov/)
- [Google Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD10A1)
- [NSIDC Snow Products](https://nsidc.org/data/modis/snow_ice)