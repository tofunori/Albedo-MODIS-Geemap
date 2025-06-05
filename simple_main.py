#!/usr/bin/env python3
"""
Menu Principal Simplifié - Analyse MODIS Albedo Glacier Athabasca
Université du Québec à Trois-Rivières - Projet de Maîtrise

Seulement 2 options qui FONCTIONNENT:
1. Analyse de la saison de fonte (Williamson & Menounos 2021) - VERSION QUI MARCHE
2. Cartographie interactive
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
        from trend_analysis import run_melt_season_analysis_williamson
        results = run_melt_season_analysis_williamson()
        
        print("\n✅ Analyse terminée!")
        print("📊 Consultez les fichiers générés:")
        print("   • outputs/csv/athabasca_melt_season_focused_data.csv") 
        print("   • figures/melt_season/athabasca_melt_season_comprehensive_analysis.png")
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
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
            filename = f"glacier_map_{date}.html"
            map_obj.save(filename)
            print(f"💾 Carte sauvegardée: {filename}")
            
        elif choice == 'b':
            date1 = input("Première date (YYYY-MM-DD) [2023-06-15]: ").strip() or "2023-06-15"
            date2 = input("Deuxième date (YYYY-MM-DD) [2023-09-15]: ").strip() or "2023-09-15"
            
            map_obj = create_comparison_map(date1, date2)
            
            # Sauvegarder
            filename = f"glacier_comparison_{date1}_vs_{date2}.html"
            map_obj.save(filename)
            print(f"💾 Carte de comparaison sauvegardée: {filename}")
        
        else:
            print("❌ Choix invalide")
        
        print("📂 Ouvrez le fichier HTML dans votre navigateur")
        return map_obj
        
    except Exception as e:
        print(f"❌ Erreur lors de la cartographie: {e}")
        return None

def show_menu():
    """Afficher le menu principal"""
    print("🏔️ ANALYSE MODIS ALBEDO - GLACIER ATHABASCA")
    print("Université du Québec à Trois-Rivières")
    print("=" * 50)
    print()
    print("Options disponibles:")
    print("1️⃣ Analyse saison de fonte (Williamson & Menounos 2021)")
    print("2️⃣ Cartographie interactive")
    print("0️⃣ Quitter")
    print()

def main():
    """Fonction principale avec menu interactif"""
    while True:
        show_menu()
        
        try:
            choice = input("🔸 Votre choix (0-2): ").strip()
            
            if choice == '0':
                print("👋 Au revoir!")
                break
                
            elif choice == '1':
                run_melt_season_analysis()
                
            elif choice == '2':
                run_interactive_mapping()
                
            else:
                print("❌ Choix invalide. Veuillez choisir 0, 1 ou 2.")
            
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Analyse interrompue.")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()