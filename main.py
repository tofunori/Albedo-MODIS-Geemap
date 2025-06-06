#!/usr/bin/env python3
"""
Menu Principal Simplifié - Analyse MODIS Albedo Glacier Athabasca
Université du Québec à Trois-Rivières - Projet de Maîtrise

Options disponibles:
1. Analyse de la saison de fonte (Williamson & Menounos 2021) - VERSION QUI MARCHE
2. Analyse hypsométrique - Tranches d'élévation ±100m (NOUVEAU!)
3. Cartographie interactive
4. Analyse spectrale MCD43A3 (Williamson & Menounos 2021) - NOUVEAU! 🌈
"""

def run_melt_season_analysis():
    """Lancer l'analyse de la saison de fonte"""
    try:
        print("🔬 Lancement de l'analyse de saison de fonte...")
        print("📚 Méthodologie: Williamson & Menounos (2021)")
        print("⏳ Cela peut prendre plusieurs minutes...")
        print()
        
        # Import et exécution de l'analyse qui fonctionne
        import sys
        sys.path.append('src')
        from workflows.melt_season import run_melt_season_analysis_williamson
        results = run_melt_season_analysis_williamson()
        
        print("\n✅ Analyse terminée!")
        print("📊 Consultez les fichiers générés:")
        print("   • outputs/csv/athabasca_melt_season_data.csv") 
        print("   • figures/melt_season/athabasca_melt_season_analysis.png")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        return None

def run_hypsometric_analysis():
    """Lancer l'analyse hypsométrique (par tranches d'élévation)"""
    try:
        print("🏔️ Lancement de l'analyse hypsométrique...")
        print("📚 Méthodologie: Williamson & Menounos (2021) - Tranches d'élévation ±100m")
        print("📏 Analyse par bandes d'élévation autour de l'élévation médiane du glacier")
        print("⏳ Cela peut prendre plusieurs minutes...")
        print()
        
        # Import et exécution de l'analyse hypsométrique
        import sys
        sys.path.append('src')
        from workflows.hypsometric import run_hypsometric_analysis_williamson
        results = run_hypsometric_analysis_williamson()
        
        print("\n✅ Analyse hypsométrique terminée!")
        print("📊 Consultez les fichiers générés:")
        print("   • outputs/csv/athabasca_hypsometric_data.csv") 
        print("   • outputs/csv/athabasca_hypsometric_results.csv")
        print("   • figures/trends/athabasca_hypsometric_analysis.png")
        print("   • figures/evolution/athabasca_melt_season_with_elevation.png")
        
        if results and results.get('elevation_comparison', {}).get('transient_snowline_pattern', False):
            print("\n🎯 RÉSULTAT IMPORTANT:")
            print("   ✅ PATTERN DE LIGNE DE NEIGE TRANSITOIRE DÉTECTÉ!")
            print("   📏 Ceci correspond aux résultats de Williamson & Menounos (2021)")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse hypsométrique: {e}")
        return None

def run_elevation_map():
    """Créer une carte d'élévation avec les bandes hypsométriques"""
    try:
        print("🗺️ Création de la carte d'élévation du glacier...")
        print("📏 Avec bandes hypsométriques selon Williamson & Menounos (2021)")
        print("⏳ Extraction des données SRTM et génération de la carte...")
        print()
        
        # Import des fonctions de cartographie d'élévation
        import sys
        sys.path.append('src')
        from visualization.maps import create_elevation_map
        
        # Créer la carte d'élévation
        map_obj = create_elevation_map()
        
        if map_obj:
            print("✅ Carte d'élévation créée avec succès!")
            print("📂 Fichier: maps/interactive/athabasca_elevation_map.html")
            print("🌐 Ouvrez ce fichier dans votre navigateur web")
            print("\n📋 La carte contient:")
            print("   • Élévation topographique SRTM")
            print("   • Frontière du glacier Athabasca")
            print("   • Élévation médiane du glacier")
            print("   • Bandes d'élévation Williamson & Menounos:")
            print("     - Au-dessus médiane (>100m)")
            print("     - Près médiane (±100m)")
            print("     - En-dessous médiane (>100m)")
        else:
            print("❌ Échec de la création de la carte")
        
        return map_obj
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la carte d'élévation: {e}")
        return None

def run_interactive_mapping():
    """Lancer la cartographie interactive"""
    try:
        print("🗺️ Cartographie interactive du glacier...")
        
        # Import des fonctions de cartographie du module original
        import sys
        sys.path.append('src')
        from mapping import show_glacier_map, create_comparison_map
        
        print("\nOptions de cartographie:")
        print("a) Carte simple du glacier")
        print("b) Comparaison entre deux dates")
        
        choice = input("Votre choix (a/b): ").strip().lower()
        
        if choice == 'a':
            date = input("Date pour la carte (YYYY-MM-DD) [2023-08-15]: ").strip() or "2023-08-15"
            map_obj = show_glacier_map(date=date)
            
            # Sauvegarder
            from src.paths import get_map_path
            map_path = get_map_path(f"glacier_map_{date}.html", 'interactive')
            map_obj.save(str(map_path))
            print(f"💾 Carte sauvegardée: {map_path}")
            
        elif choice == 'b':
            date1 = input("Première date (YYYY-MM-DD) [2023-06-15]: ").strip() or "2023-06-15"
            date2 = input("Deuxième date (YYYY-MM-DD) [2023-09-15]: ").strip() or "2023-09-15"
            
            map_obj = create_comparison_map(date1, date2)
            
            # Sauvegarder
            comparison_path = get_map_path(f"glacier_comparison_{date1}_vs_{date2}.html", 'comparison')
            map_obj.save(str(comparison_path))
            print(f"💾 Carte de comparaison sauvegardée: {comparison_path}")
        
        else:
            print("❌ Choix invalide")
        
        print("📂 Ouvrez le fichier HTML dans votre navigateur")
        return map_obj
        
    except Exception as e:
        print(f"❌ Erreur lors de la cartographie: {e}")
        return None

def run_mcd43a3_analysis():
    """Lancer l'analyse spectrale MCD43A3 (broadband albedo)"""
    try:
        print("🌈 Lancement de l'analyse spectrale MCD43A3...")
        print("📚 Méthodologie: Williamson & Menounos (2021) - Analyse spectrale")
        print("📡 Produit: MODIS MCD43A3 composites d'albédo à large bande (16 jours)")
        print("🔬 Focus: Analyse visible vs infrarouge proche pour détection contamination")
        print("⏳ Cela peut prendre plusieurs minutes...")
        print()
        
        # Import et exécution de l'analyse MCD43A3
        import sys
        sys.path.append('src')
        from workflows.broadband_albedo import run_mcd43a3_analysis
        
        # Options par défaut - peut être étendu plus tard
        start_year = 2015
        end_year = 2024
        
        results = run_mcd43a3_analysis(start_year=start_year, end_year=end_year)
        
        print("\n✅ Analyse MCD43A3 terminée!")
        
        if results and results.get('dataset_info'):
            info = results['dataset_info']
            print("📊 Consultez les fichiers générés:")
            print("   • outputs/csv/athabasca_mcd43a3_spectral_data.csv") 
            print("   • outputs/csv/athabasca_mcd43a3_results.csv")
            print("   • figures/melt_season/athabasca_mcd43a3_spectral_analysis.png")
            
            print(f"\n🎯 RÉSULTATS CLÉS:")
            print(f"   📊 Période analysée: {info['period']}")
            print(f"   📈 Total observations: {info['total_observations']}")
            print(f"   🌈 Analyse spectrale complète (visible vs NIR)")
            
            if 'spectral_analysis' in results and 'spectral_comparison' in results['spectral_analysis']:
                comp = results['spectral_analysis']['spectral_comparison']
                print(f"   🔍 Pattern détecté: {comp['interpretation'].replace('_', ' ').title()}")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse MCD43A3: {e}")
        return None

def show_menu():
    """Afficher le menu principal"""
    print("🏔️ ANALYSE MODIS ALBEDO - GLACIER ATHABASCA")
    print("Université du Québec à Trois-Rivières")
    print("=" * 50)
    print()
    print("Options disponibles:")
    print("1️⃣ Analyse saison de fonte (Williamson & Menounos 2021)")
    print("2️⃣ Analyse hypsométrique - Tranches d'élévation ±100m")
    print("3️⃣ Carte d'élévation interactive avec bandes hypsométriques")
    print("4️⃣ Cartographie interactive (autres options)")
    print("5️⃣ Analyse spectrale MCD43A3 (Williamson & Menounos 2021) 🌈")
    print("0️⃣ Quitter")
    print()

def main():
    """Fonction principale avec menu interactif"""
    while True:
        show_menu()
        
        try:
            choice = input("🔸 Votre choix (0-5): ").strip()
            
            if choice == '0':
                print("👋 Au revoir!")
                break
                
            elif choice == '1':
                run_melt_season_analysis()
                
            elif choice == '2':
                run_hypsometric_analysis()
                
            elif choice == '3':
                run_elevation_map()
                
            elif choice == '4':
                run_interactive_mapping()
                
            elif choice == '5':
                run_mcd43a3_analysis()
                
            else:
                print("❌ Choix invalide. Veuillez choisir 0, 1, 2, 3, 4 ou 5.")
            
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Analyse interrompue.")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()