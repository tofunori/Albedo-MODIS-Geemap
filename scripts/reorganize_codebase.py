#!/usr/bin/env python3
"""
Codebase Reorganization Script
Automatically reorganizes the Albedo MODIS Geemap project structure
"""

import os
import shutil
import sys
from pathlib import Path


class CodebaseReorganizer:
    """Handles the reorganization of the codebase structure"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup_before_reorganization"
        
    def create_backup(self):
        """Create a backup of the current structure"""
        print("📦 Creating backup of current structure...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        # Copy important directories to backup
        important_dirs = ['src', 'streamlit_app', 'outputs', 'data']
        
        for dir_name in important_dirs:
            src_path = self.project_root / dir_name
            if src_path.exists():
                dst_path = self.backup_dir / dir_name
                shutil.copytree(src_path, dst_path)
                print(f"  ✅ Backed up {dir_name}/")
        
        print(f"✅ Backup created at: {self.backup_dir}")
    
    def create_new_structure(self):
        """Create the new directory structure"""
        print("🏗️ Creating new directory structure...")
        
        new_dirs = [
            # Core configuration
            "config",
            
            # Enhanced data organization
            "data/masks",
            "data/raw",
            "data/processed",
            
            # Better output organization
            "outputs/csv",
            "outputs/figures/evolution",
            "outputs/figures/melt_season",
            "outputs/figures/trends",
            "outputs/maps/interactive",
            "outputs/maps/comparison",
            "outputs/reports",
            
            # New web structure
            "web",
            "web/pages",
            "web/components", 
            "web/utils",
            "web/assets/styles",
            "web/assets/images",
            "web/assets/configs",
            
            # Enhanced src structure
            "src/core",
            "src/data/extractors",
            "src/data/processors", 
            "src/data/loaders",
            "src/analysis/workflows",
            "src/analysis/statistics",
            "src/analysis/validation",
            "src/visualization/plots",
            "src/visualization/maps",
            "src/visualization/dashboards",
            
            # Scripts and utilities
            "scripts/migration",
            
            # Testing structure
            "tests/unit",
            "tests/integration",
            "tests/fixtures",
            
            # Notebooks
            "notebooks",
            
            # Legacy preservation
            "legacy/streamlit_old",
            "legacy/deprecated"
        ]
        
        for dir_path in new_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created {dir_path}/")
    
    def migrate_files(self):
        """Migrate files to new locations"""
        print("🚚 Migrating files to new structure...")
        
        # Migration mappings
        migrations = [
            # Configuration files
            ("src/config.py", "config/settings.py"),
            ("src/paths.py", "config/paths.py"),
            
            # Move glacier masks
            ("Athabasca_mask_2023.geojson", "data/masks/Athabasca_mask_2023.geojson"),
            ("Athabasca_mask_2023_cut.geojson", "data/masks/Athabasca_mask_2023_cut.geojson"),
            ("Athabasca_mask_2023_cut.qmd", "data/masks/Athabasca_mask_2023_cut.qmd"),
            
            # Web interface files
            ("streamlit_app/streamlit_main.py", "web/main.py"),
            ("streamlit_app/src/dashboards/processing_dashboard.py", "web/pages/data_processing.py"),
            ("streamlit_app/src/dashboards/mcd43a3_dashboard.py", "web/pages/mcd43a3_analysis.py"),
            ("streamlit_app/src/dashboards/melt_season_dashboard.py", "web/pages/mod10a1_analysis.py"),
            ("streamlit_app/src/dashboards/statistical_analysis_dashboard.py", "web/pages/statistical_analysis.py"),
            ("streamlit_app/src/dashboards/realtime_qa_dashboard.py", "web/pages/qa_comparison.py"),
            ("streamlit_app/src/dashboards/interactive_data_dashboard.py", "web/components/data_tables.py"),
            ("streamlit_app/src/dashboards/interactive_albedo_dashboard.py", "web/pages/interactive_maps.py"),
            ("streamlit_app/src/utils/csv_import.py", "web/components/file_upload.py"),
            
            # Core analysis modules
            ("src/workflows/melt_season.py", "src/analysis/workflows/melt_season_workflow.py"),
            ("src/workflows/broadband_albedo.py", "src/analysis/workflows/broadband_albedo_workflow.py"),
            ("src/workflows/hypsometric.py", "src/analysis/workflows/hypsometric_workflow.py"),
            
            # Data extraction modules
            ("src/data/extraction.py", "src/data/extractors/mod10a1_extractor.py"),
            ("src/data/mcd43a3_extraction.py", "src/data/extractors/mcd43a3_extractor.py"),
            
            # Analysis modules
            ("src/analysis/statistics.py", "src/analysis/statistics/trend_analysis.py"),
            ("src/analysis/temporal.py", "src/analysis/statistics/temporal_analysis.py"),
            ("src/analysis/hypsometric.py", "src/analysis/workflows/hypsometric_workflow.py"),
            ("src/analysis/spectral_analysis.py", "src/core/albedo_analysis.py"),
            
            # Visualization modules
            ("src/visualization/plots.py", "src/visualization/plots/time_series_plots.py"),
            ("src/visualization/static_plots.py", "src/visualization/plots/static_plots.py"),
            ("src/visualization/interactive_plots.py", "src/visualization/plots/spatial_plots.py"),
            ("src/visualization/spectral_plots.py", "src/visualization/plots/statistical_plots.py"),
            ("src/visualization/maps.py", "src/visualization/maps/interactive_maps.py"),
            
            # Notebooks
            ("Jupyter/01_Setup_and_Configuration.ipynb", "notebooks/01_Data_Exploration.ipynb"),
            ("Jupyter/02_Interactive_Mapping.ipynb", "notebooks/02_Method_Development.ipynb"),
            
            # Legacy preservation
            ("streamlit_app/streamlit_dashboard_modular.py", "legacy/streamlit_old/streamlit_dashboard_modular.py"),
            ("main.py", "legacy/old_main.py"),
        ]
        
        for src, dst in migrations:
            src_path = self.project_root / src
            dst_path = self.project_root / dst
            
            if src_path.exists():
                # Ensure destination directory exists
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file (don't move yet, to preserve originals)
                shutil.copy2(src_path, dst_path)
                print(f"  ✅ Migrated {src} → {dst}")
            else:
                print(f"  ⚠️ Source not found: {src}")
    
    def create_init_files(self):
        """Create __init__.py files for Python packages"""
        print("📝 Creating __init__.py files...")
        
        python_dirs = [
            "config",
            "src",
            "src/core", 
            "src/data",
            "src/data/extractors",
            "src/data/processors",
            "src/data/loaders",
            "src/analysis",
            "src/analysis/workflows",
            "src/analysis/statistics",
            "src/analysis/validation",
            "src/visualization",
            "src/visualization/plots",
            "src/visualization/maps", 
            "src/visualization/dashboards",
            "src/utils",
            "web",
            "web/pages",
            "web/components",
            "web/utils",
            "scripts",
            "scripts/migration",
            "tests",
            "tests/unit",
            "tests/integration"
        ]
        
        for dir_path in python_dirs:
            init_file = self.project_root / dir_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""' + f'\n{dir_path.replace("/", ".")} module\n' + '"""\n')
                print(f"  📄 Created {dir_path}/__init__.py")
    
    def create_config_files(self):
        """Create new configuration files"""
        print("⚙️ Creating configuration files...")
        
        # Create main settings file
        settings_content = '''"""
Global settings and configuration for Athabasca Glacier Albedo Analysis
"""

# MODIS Data Products
MODIS_PRODUCTS = {
    'MOD10A1': {
        'collection': 'MODIS/061/MOD10A1',
        'albedo_band': 'Snow_Albedo_Daily_Tile',
        'qa_band': 'NDSI_Snow_Cover_Basic_QA',
        'resolution': 500,
        'satellite': 'Terra'
    },
    'MYD10A1': {
        'collection': 'MODIS/061/MYD10A1', 
        'albedo_band': 'Snow_Albedo_Daily_Tile',
        'qa_band': 'NDSI_Snow_Cover_Basic_QA',
        'resolution': 500,
        'satellite': 'Aqua'
    },
    'MCD43A3': {
        'collection': 'MODIS/061/MCD43A3',
        'albedo_bands': {
            'vis': 'Albedo_BSA_vis',
            'nir': 'Albedo_BSA_nir',
            'shortwave': 'Albedo_BSA_shortwave'
        },
        'qa_band': 'BRDF_Albedo_Band_Mandatory_Quality_vis',
        'resolution': 500
    }
}

# Quality Assessment Levels
QA_LEVELS = {
    'strict': {'basic_qa': 0, 'description': 'Best quality only'},
    'standard': {'basic_qa': 1, 'description': 'Best + good quality'},
    'relaxed': {'basic_qa': 2, 'description': 'All acceptable quality'}
}

# Analysis Parameters
MELT_SEASON_MONTHS = [6, 7, 8, 9]  # June-September
ELEVATION_BAND_SIZE = 100  # meters
MIN_PIXEL_COUNT = 5

# File Formats
OUTPUT_FORMATS = {
    'csv': {'encoding': 'utf-8', 'index': False},
    'figures': {'format': 'png', 'dpi': 300},
    'maps': {'format': 'html'}
}
'''
        
        settings_file = self.project_root / "config" / "settings.py"
        settings_file.write_text(settings_content)
        print("  ⚙️ Created config/settings.py")
        
        # Create web requirements
        web_requirements = '''streamlit>=1.28.0
plotly>=5.15.0
folium>=0.14.0
streamlit-folium>=0.13.0
pandas>=2.0.0
numpy>=1.24.0
'''
        
        web_req_file = self.project_root / "web" / "requirements.txt"
        web_req_file.write_text(web_requirements)
        print("  📋 Created web/requirements.txt")
    
    def create_readme_files(self):
        """Create README files for new directories"""
        print("📚 Creating README files...")
        
        readme_content = {
            "web/README.md": """# Web Interface

Streamlit-based web dashboard for interactive analysis.

## Structure
- `main.py` - Main application entry point
- `pages/` - Individual dashboard pages
- `components/` - Reusable UI components
- `utils/` - Web-specific utilities
- `assets/` - Static assets and configurations

## Usage
```bash
streamlit run web/main.py
```
""",
            
            "src/README.md": """# Source Code

Core Python modules for MODIS albedo analysis.

## Structure
- `core/` - Core analysis algorithms
- `data/` - Data extraction and processing
- `analysis/` - Analysis workflows and statistics
- `visualization/` - Plotting and mapping
- `utils/` - General utilities

## Guidelines
- Keep modules under 500 lines
- Follow single responsibility principle
- Add comprehensive docstrings
""",
            
            "legacy/README.md": """# Legacy Code

This directory contains deprecated code that is being phased out.

## Contents
- `streamlit_old/` - Old Streamlit dashboard files
- `deprecated/` - Other deprecated modules

⚠️ **Do not use this code for new development**

These files are preserved for reference during the migration period.
"""
        }
        
        for file_path, content in readme_content.items():
            readme_file = self.project_root / file_path
            readme_file.write_text(content)
            print(f"  📖 Created {file_path}")
    
    def update_main_readme(self):
        """Update the main README with new structure information"""
        print("📝 Updating main README...")
        
        readme_addition = """
## 🏗️ Project Structure (Updated)

This project has been reorganized for better maintainability:

- `web/` - Streamlit web interface
- `src/` - Core Python modules  
- `config/` - Configuration files
- `data/` - Data storage and masks
- `outputs/` - Analysis results
- `scripts/` - Utility scripts
- `tests/` - Test suite
- `notebooks/` - Jupyter notebooks
- `legacy/` - Deprecated code

## 🚀 Quick Start (New Structure)

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r web/requirements.txt

# Run web interface
streamlit run web/main.py

# Run analysis scripts
python scripts/batch_processing.py
```

## 📁 File Organization Guidelines

Following the project's established principles:
- **Maximum file length**: 500 lines
- **Modular design**: Single responsibility per module
- **Clear separation**: UI, core logic, and utilities separated
- **Comprehensive docs**: Docstrings and type hints

See `CODEBASE_REORGANIZATION_PLAN.md` for detailed information.
"""
        
        readme_file = self.project_root / "README.md"
        if readme_file.exists():
            current_content = readme_file.read_text()
            if "Project Structure (Updated)" not in current_content:
                updated_content = current_content + readme_addition
                readme_file.write_text(updated_content)
                print("  ✅ Updated README.md")
        
    def run_reorganization(self):
        """Run the complete reorganization process"""
        print("🎯 Starting codebase reorganization...")
        print("=" * 50)
        
        try:
            # Phase 1: Safety and structure
            self.create_backup()
            self.create_new_structure()
            
            # Phase 2: Migration
            self.migrate_files()
            self.create_init_files()
            
            # Phase 3: Configuration
            self.create_config_files()
            self.create_readme_files()
            self.update_main_readme()
            
            print("=" * 50)
            print("✅ Reorganization completed successfully!")
            print()
            print("📋 Next Steps:")
            print("1. Review migrated files for any import path updates needed")
            print("2. Test the new web interface: streamlit run web/main.py")
            print("3. Update any remaining import statements")
            print("4. Remove legacy files when confident everything works")
            print(f"5. Backup is available at: {self.backup_dir}")
            
        except Exception as e:
            print(f"❌ Error during reorganization: {e}")
            print("💡 Restore from backup if needed")
            raise


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    print(f"🎯 Reorganizing codebase in: {project_root}")
    
    # Confirm with user
    response = input("⚠️  This will reorganize your codebase. Continue? [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Reorganization cancelled")
        return
    
    reorganizer = CodebaseReorganizer(project_root)
    reorganizer.run_reorganization()


if __name__ == "__main__":
    main()