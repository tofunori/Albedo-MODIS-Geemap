#!/usr/bin/env python3
"""
Script de test pour diagnostiquer les problèmes MCD43A3
"""

import sys
import os
sys.path.append('src')

def test_mcd43a3_basic():
    """Test basique de l'analyse MCD43A3"""
    try:
        print("🔧 DIAGNOSTIC MCD43A3")
        print("=" * 50)
        
        # Test des imports
        print("1️⃣ Test des imports...")
        from workflows.broadband_albedo import initialize_earth_engine, extract_mcd43a3_data_fixed
        print("   ✅ Imports réussis")
        
        # Test Earth Engine
        print("2️⃣ Test Google Earth Engine...")
        initialize_earth_engine()
        print("   ✅ Earth Engine initialisé")
        
        # Test de configuration
        print("3️⃣ Test de configuration...")
        from config import athabasca_roi
        print(f"   ✅ Glacier mask chargé: {type(athabasca_roi)}")
        
        # Test extraction (période courte)
        print("4️⃣ Test extraction données (2023-2024)...")
        df = extract_mcd43a3_data_fixed(start_year=2023, end_year=2024)
        
        if not df.empty:
            print(f"   ✅ Données extraites: {len(df)} observations")
            print(f"   📅 Période: {df['date'].min()} à {df['date'].max()}")
            print(f"   📊 Colonnes: {list(df.columns)}")
            
            # Test graphique simple
            print("5️⃣ Test graphique...")
            import matplotlib.pyplot as plt
            import pandas as pd
            
            plt.figure(figsize=(10, 6))
            
            if 'Albedo_BSA_vis' in df.columns:
                plt.scatter(df['year'], df['Albedo_BSA_vis'], alpha=0.6, label='Visible')
            if 'Albedo_BSA_nir' in df.columns:
                plt.scatter(df['year'], df['Albedo_BSA_nir'], alpha=0.6, label='NIR')
                
            plt.xlabel('Année')
            plt.ylabel('Albédo')
            plt.title('Test MCD43A3 - Données Athabasca')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Sauvegarder
            output_path = 'figures/test_mcd43a3.png'
            os.makedirs('figures', exist_ok=True)
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.show()
            
            print(f"   ✅ Graphique sauvegardé: {output_path}")
            
        else:
            print("   ❌ Aucune donnée extraite")
            
        return df
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_mcd43a3_basic()
    if result is not None and not result.empty:
        print("\n✅ Test MCD43A3 réussi!")
    else:
        print("\n❌ Test MCD43A3 échoué!") 