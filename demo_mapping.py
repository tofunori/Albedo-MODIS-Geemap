#!/usr/bin/env python3
"""
Demonstration script for the new mapping functionality
Shows how to create interactive maps of the Athabasca Glacier with MODIS data
"""

def demo_mapping_functions():
    """
    Demonstrate the mapping functionality with examples
    Note: Requires Earth Engine authentication to run
    """
    
    print("🗺️ DEMONSTRATION: Mapping Functions for Athabasca Glacier")
    print("=" * 65)
    print()
    
    try:
        # Import the mapping functions
        from mapping import show_glacier_map, create_comparison_map, display_glacier_info
        
        print("✅ Mapping module imported successfully!")
        print()
        
        # Show glacier information
        print("📍 GLACIER INFORMATION:")
        print("-" * 30)
        glacier_info = display_glacier_info()
        print()
        
        # Demo 1: Single date map
        print("🗺️ DEMO 1: Single Date Interactive Map")
        print("-" * 40)
        print("Creating map for August 15, 2023 at 500m resolution...")
        
        try:
            map1 = show_glacier_map(date='2023-08-15', scale=500)
            
            # Save the map
            map1.to_html('demo_glacier_map_single.html')
            print("✅ Single date map created and saved as 'demo_glacier_map_single.html'")
            print("   This map shows:")
            print("   • Glacier boundary in red")
            print("   • MODIS 500m pixel grid in blue")
            print("   • Snow albedo data as colored overlay")
            print("   • Weather station location as yellow marker")
            
        except Exception as e:
            print(f"❌ Could not create single date map: {e}")
        
        print()
        
        # Demo 2: Comparison map
        print("🗺️ DEMO 2: Side-by-Side Comparison Map")
        print("-" * 42)
        print("Creating comparison between June 15 and September 15, 2023...")
        
        try:
            map2 = create_comparison_map(
                date1='2023-06-15',  # Early melt season
                date2='2023-09-15',  # Late melt season
                scale=500
            )
            
            # Save the comparison map
            map2.to_html('demo_glacier_comparison.html')
            print("✅ Comparison map created and saved as 'demo_glacier_comparison.html'")
            print("   This split-panel map shows:")
            print("   • Left: June 15, 2023 (early melt season)")
            print("   • Right: September 15, 2023 (late melt season)")
            print("   • Allows direct visual comparison of albedo changes")
            
        except Exception as e:
            print(f"❌ Could not create comparison map: {e}")
        
        print()
        
        # Usage instructions
        print("💡 USAGE INSTRUCTIONS:")
        print("-" * 25)
        print("1. Open the generated HTML files in your web browser")
        print("2. The maps are fully interactive - you can:")
        print("   • Zoom in/out with mouse wheel or controls")
        print("   • Pan by clicking and dragging")
        print("   • Toggle layers on/off using the layer control")
        print("   • Click on features for more information")
        print()
        print("3. Integration with main analysis:")
        print("   • Use interactive_menu() and select option 6 or 7")
        print("   • Or call functions directly:")
        print("     - show_glacier_map('2023-08-15', 500)")
        print("     - create_comparison_map('2023-06-15', '2023-09-15')")
        
        print()
        print("🎯 NEXT STEPS:")
        print("-" * 15)
        print("• Run 'python main.py' and select mapping options from menu")
        print("• Customize dates and resolution for your specific needs")
        print("• Combine mapping with time series analysis for comprehensive studies")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have installed the required packages:")
        print("pip install earthengine-api geemap folium")
        print()
        print("And authenticated with Google Earth Engine:")
        print("python -c 'import ee; ee.Authenticate()'")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def show_mapping_features():
    """
    Display the features available in the mapping module
    """
    print("🔧 MAPPING MODULE FEATURES:")
    print("=" * 35)
    print()
    print("📍 Core Functions:")
    print("  • show_glacier_map() - Single date interactive map")
    print("  • create_comparison_map() - Side-by-side date comparison")
    print("  • create_glacier_map() - Advanced map with custom options")
    print("  • display_glacier_info() - Glacier statistics and coordinates")
    print()
    print("🗺️ Map Layers:")
    print("  • Glacier boundary (red outline)")
    print("  • MODIS pixel grid (blue grid)")
    print("  • Snow albedo data (color-coded)")
    print("  • Broadband albedo data (optional)")
    print("  • Weather station marker (yellow)")
    print()
    print("⚙️ Customization Options:")
    print("  • Date selection for MODIS data")
    print("  • Resolution: 250m, 500m, or 1000m")
    print("  • Toggle data layers on/off")
    print("  • Multiple albedo products (snow vs broadband)")
    print()
    print("💾 Export Options:")
    print("  • Interactive HTML maps")
    print("  • Glacier boundary as GeoJSON/KML")
    print("  • High-resolution screenshots")
    print()
    print("🎛️ Integration:")
    print("  • Available in main.py interactive menu")
    print("  • Standalone function calls")
    print("  • Jupyter notebook compatible")

if __name__ == "__main__":
    # Show features first
    show_mapping_features()
    print()
    print()
    
    # Ask user if they want to run the demo
    try:
        response = input("🤔 Do you want to run the mapping demonstration? (y/n): ").strip().lower()
        if response in ['y', 'yes', 'oui']:
            print()
            demo_mapping_functions()
        else:
            print("👋 Demo skipped. You can run this script anytime to test the mapping functions!")
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled.")