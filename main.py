"""
Main analysis runner for MODIS albedo analysis - Athabasca Glacier
Simplified interface for running different analysis configurations
"""
import ee
from config import PERIODS_RAPIDE, SAMPLING_OPTIONS, SCALE_OPTIONS
from data_processing import extract_time_series_fast
from visualization import plot_albedo_fast, plot_albedo_evolution_enhanced
from melt_season import analyze_melt_season, plot_melt_season_analysis
import numpy as np

# Initialize Earth Engine
ee.Initialize()

# ================================================================================
# MAIN ANALYSIS FUNCTION
# ================================================================================

def run_analysis_optimized(period='recent', sampling=None, scale=500, use_broadband=False, smoothing='rolling'):
    """
    Fonction principale avec options d'optimisation
    
    Args:
        period: 'recent', 'fire_years', 'decade', 'sample', 'full_recent', ou tuple (start, end)
        sampling: None, 'weekly', 'monthly', 'seasonal'
        scale: 250, 500, 1000 (résolution en mètres)
        use_broadband: False (neige) ou True (large bande)
        smoothing: 'rolling', 'savgol', 'spline' (méthode de lissage)
    """
    
    print("🚀 ANALYSE OPTIMISÉE Albédo Glacier Athabasca")
    print("=" * 60)
    
    # Définir période
    if isinstance(period, tuple):
        start_date, end_date = period
        period_name = f"Personnalisée ({start_date} à {end_date})"
    else:
        start_date, end_date = PERIODS_RAPIDE[period]
        period_name = period.title()
    
    # Définir échantillonnage
    sampling_days = SAMPLING_OPTIONS.get(sampling) if sampling else None
    
    print(f"📅 Période: {period_name}")
    print(f"⏱️ Échantillonnage: {sampling or 'Toutes les images'}")
    print(f"🎯 Résolution: {scale}m")
    print(f"📊 Type données: {'Large bande (MCD43A3 v6.1)' if use_broadband else 'Neige quotidien (MOD/MYD10A1 v6.1)'}")
    
    # Extraction
    df = extract_time_series_fast(
        start_date, end_date,
        use_broadband=use_broadband,
        sampling_days=sampling_days,
        scale=scale
    )
    
    if df.empty:
        print("❌ Aucune donnée extraite")
        return None
    
    # Statistiques rapides
    print(f"\n📈 RÉSULTATS:")
    print(f"   • {len(df)} observations")
    print(f"   • Période effective: {df['date'].min()} à {df['date'].max()}")
    
    if 'albedo_mean' in df.columns:
        albedo_data = df['albedo_mean'].dropna()
        if not albedo_data.empty:
            print(f"   • Albédo moyen du glacier: {albedo_data.mean():.3f} ± {albedo_data.std():.3f}")
            print(f"   • Plage de valeurs: [{albedo_data.min():.3f}, {albedo_data.max():.3f}]")
            print(f"   • Tendance annuelle: ", end="")
            
            annual_mean = df.groupby('year')['albedo_mean'].mean()
            if len(annual_mean) > 2:
                trend = np.polyfit(annual_mean.index, annual_mean.values, 1)[0]
                print(f"{trend:.4f}/an")
            else:
                print("Insuffisant pour calcul")
    
    # Visualisation
    print(f"\n📊 Génération graphiques...")
    print(f"   • Méthode de lissage: {smoothing}")
    
    # Graphiques standard
    plot_albedo_fast(df, f" - {period_name}", smoothing_method=smoothing)
    
    # Graphique d'évolution amélioré
    print(f"\n📈 Génération graphique d'évolution détaillé...")
    plot_albedo_evolution_enhanced(df, f" ({period_name})", 
                                  smoothing_method=smoothing,
                                  save_path=f'evolution_albedo_{period}_{scale}m.png')
    
    # Analyse spécifique de la saison de fonte
    print(f"\n🌡️ ANALYSE DE LA SAISON DE FONTE (Juin-Septembre)...")
    melt_stats, df_melt = analyze_melt_season(df)
    
    if melt_stats and df_melt is not None:
        print(f"   • Années analysées: {sorted(melt_stats.keys())}")
        print(f"   • Observations totales (juin-sept): {len(df_melt)}")
        
        # Statistiques résumées
        all_means = [stats['mean'] for stats in melt_stats.values()]
        print(f"   • Albédo moyen global (fonte): {np.mean(all_means):.3f}")
        
        # Année avec le plus faible albédo moyen
        min_year = min(melt_stats.items(), key=lambda x: x[1]['mean'])[0]
        print(f"   • Année avec albédo le plus faible: {min_year} ({melt_stats[min_year]['mean']:.3f})")
        
        # Générer le graphique de fonte avec lissage élevé
        plot_melt_season_analysis(df_melt, melt_stats, 
                                 title=f" ({period_name})",
                                 save_path=f'melt_season_analysis_{period}_{scale}m.png',
                                 smoothing_level='high')
    else:
        print("   ⚠️ Données insuffisantes pour l'analyse de fonte")
    
    # Export
    filename = f'athabasca_albedo_{period}_{scale}m.csv'
    df.to_csv(filename, index=False)
    print(f"💾 Données complètes exportées: {filename}")
    
    # Export données de fonte
    if df_melt is not None and not df_melt.empty:
        melt_filename = f'athabasca_melt_season_{period}_{scale}m.csv'
        df_melt.to_csv(melt_filename, index=False)
        print(f"💾 Données saison de fonte exportées: {melt_filename}")
    
    return df

# ================================================================================
# CONVENIENCE FUNCTIONS FOR COMMON ANALYSES
# ================================================================================

def quick_recent_analysis():
    """Analyse rapide des années récentes (2019-2024)"""
    print("🎯 ANALYSE RAPIDE - Années récentes (2019-2024)")
    return run_analysis_optimized(
        period='full_recent',
        sampling=None,
        scale=500,
        use_broadband=False,
        smoothing='savgol'
    )

def fire_impact_analysis():
    """Analyse de l'impact des feux (2017-2021)"""
    print("🔥 ANALYSE IMPACT FEUX - Années 2017-2021")
    return run_analysis_optimized(
        period='fire_years',
        sampling=None,
        scale=500,
        use_broadband=False,
        smoothing='rolling'
    )

def decade_trend_analysis():
    """Analyse des tendances sur la dernière décennie"""
    print("📈 ANALYSE TENDANCES - Dernière décennie (2015-2024)")
    return run_analysis_optimized(
        period='decade',
        sampling='weekly',
        scale=500,
        use_broadband=False,
        smoothing='spline'
    )

def fast_test_analysis():
    """Test rapide avec paramètres optimisés pour la vitesse"""
    print("⚡ TEST RAPIDE - Résolution réduite et échantillonnage mensuel")
    return run_analysis_optimized(
        period='recent',
        sampling='monthly',
        scale=1000,
        use_broadband=False,
        smoothing='rolling'
    )

def custom_analysis(start_date, end_date, **kwargs):
    """Analyse personnalisée avec dates spécifiques"""
    print(f"🎛️ ANALYSE PERSONNALISÉE - {start_date} à {end_date}")
    return run_analysis_optimized(
        period=(start_date, end_date),
        **kwargs
    )

# ================================================================================
# INTERACTIVE MENU
# ================================================================================

def interactive_menu():
    """Menu interactif pour choisir le type d'analyse"""
    print("\n🎛️ MENU INTERACTIF - Analyses MODIS Albédo Athabasca")
    print("=" * 60)
    print("1️⃣ Analyse rapide récente (2019-2024) - Recommandé")
    print("2️⃣ Impact des feux (2017-2021)")
    print("3️⃣ Tendances décennales (2015-2024)")
    print("4️⃣ Test rapide (résolution réduite)")
    print("5️⃣ Analyse personnalisée")
    print("0️⃣ Quitter")
    
    while True:
        try:
            choice = input("\n🔸 Votre choix (0-5): ").strip()
            
            if choice == '0':
                print("👋 Au revoir!")
                break
            elif choice == '1':
                return quick_recent_analysis()
            elif choice == '2':
                return fire_impact_analysis()
            elif choice == '3':
                return decade_trend_analysis()
            elif choice == '4':
                return fast_test_analysis()
            elif choice == '5':
                print("\n🎛️ Analyse personnalisée:")
                start = input("Date de début (YYYY-MM-DD): ").strip()
                end = input("Date de fin (YYYY-MM-DD): ").strip()
                
                print("\nOptions avancées (appuyez sur Entrée pour valeurs par défaut):")
                scale = input("Résolution (250/500/1000) [500]: ").strip() or "500"
                smoothing = input("Lissage (rolling/savgol/spline) [rolling]: ").strip() or "rolling"
                
                return custom_analysis(start, end, scale=int(scale), smoothing=smoothing)
            else:
                print("❌ Choix invalide. Veuillez choisir entre 0 et 5.")
                
        except KeyboardInterrupt:
            print("\n👋 Analyse interrompue.")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")

# ================================================================================
# MAIN EXECUTION
# ================================================================================

if __name__ == "__main__":
    print("🏔️ MODIS Albedo Analysis - Athabasca Glacier")
    print("Université du Québec à Trois-Rivières - Projet de Maîtrise")
    print("=" * 70)
    
    # Option 1: Exécution directe avec analyse recommandée
    print("\n🎯 EXÉCUTION AUTOMATIQUE: Analyse récente complète...")
    df_result = quick_recent_analysis()
    
    # Option 2: Menu interactif (décommentez pour activer)
    # interactive_menu()
    
    print(f"\n✅ ANALYSE TERMINÉE!")
    print(f"💡 Pour d'autres analyses, utilisez les fonctions:")
    print(f"   • quick_recent_analysis()")
    print(f"   • fire_impact_analysis()")
    print(f"   • decade_trend_analysis()")
    print(f"   • custom_analysis('2020-01-01', '2022-12-31')")
    print(f"   • interactive_menu()")