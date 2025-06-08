# Legacy Code

This directory contains deprecated code that is being phased out during the codebase reorganization.

## Contents

### `streamlit_old/`
- **`streamlit_dashboard_modular.py`** - Original monolithic dashboard file (1,500+ lines)
  - ⚠️ **DEPRECATED** - Use `streamlit_app/streamlit_main.py` instead
  - Moved here on 2025-01-08 as part of modularization effort
  - Preserved for reference during transition period

## ⚠️ Important Notes

- **Do not use this code for new development**
- **Do not modify files in this directory**
- These files are preserved for reference only
- Will be removed once the new modular structure is fully validated

## Migration Status

- ✅ **New modular structure created**
- ✅ **All functionality migrated to new files**
- ✅ **Old file moved to legacy**
- 🔄 **Testing new structure in progress**
- ⏳ **Final cleanup pending**

## New Structure Location

The replacement files are located in:
- **Main entry**: `streamlit_app/streamlit_main.py`
- **Components**: `streamlit_app/src/dashboards/`
- **Utilities**: `streamlit_app/src/utils/`

## Usage

```bash
# OLD (deprecated)
# streamlit run streamlit_app/streamlit_dashboard_modular.py

# NEW (current)
streamlit run streamlit_app/streamlit_main.py
```

---
*Legacy preservation date: 2025-01-08*