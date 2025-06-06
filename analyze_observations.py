#!/usr/bin/env python3
"""
Analyse détaillée des observations MCD43A3
"""

import pandas as pd
import numpy as np

def analyze_mcd43a3_observations():
    """Analyser les observations MCD43A3 en détail"""
    
    print("📊 ANALYSE DÉTAILLÉE DES OBSERVATIONS MCD43A3")
    print("=" * 60)
    
    # Charger les données
    try:
        df = pd.read_csv('outputs/csv/athabasca_mcd43a3_spectral_data.csv')
        df['date'] = pd.to_datetime(df['date'])
        
        print(f"✅ Données chargées: {len(df)} observations")
        
        # Analyse temporelle
        print(f"\n📅 RÉPARTITION TEMPORELLE")
        print(f"Période: {df['date'].min()} à {df['date'].max()}")
        print(f"Années uniques: {sorted(df['year'].unique())}")
        
        print(f"\n📊 Observations par année:")
        yearly_counts = df['year'].value_counts().sort_index()
        for year, count in yearly_counts.items():
            print(f"   {year}: {count} observations")
        
        print(f"\n📊 Observations par mois:")
        monthly_counts = df['date'].dt.month.value_counts().sort_index()
        month_names = {6: 'Juin', 7: 'Juillet', 8: 'Août', 9: 'Septembre', 
                      10: 'Octobre', 11: 'Novembre'}
        for month, count in monthly_counts.items():
            month_name = month_names.get(month, f'Mois {month}')
            print(f"   {month_name}: {count} observations")
        
        # Analyse de la fréquence
        print(f"\n⏰ ANALYSE DE FRÉQUENCE")
        
        # Différences entre dates consécutives
        df_sorted = df.sort_values('date')
        df_sorted['date_diff'] = df_sorted['date'].diff()
        
        print(f"Différences moyennes entre observations:")
        mean_diff = df_sorted['date_diff'].mean()
        print(f"   Moyenne: {mean_diff}")
        
        # Vérifier si c'est des données journalières
        daily_obs = df_sorted['date_diff'].dt.days
        daily_obs = daily_obs[daily_obs.notna()]
        
        print(f"\nDifférences en jours (échantillon):")
        print(f"   Min: {daily_obs.min()} jours")
        print(f"   Max: {daily_obs.max()} jours") 
        print(f"   Médiane: {daily_obs.median()} jours")
        print(f"   Mode: {daily_obs.mode().iloc[0] if len(daily_obs.mode()) > 0 else 'N/A'} jours")
        
        # Compter les observations par intervalle
        interval_counts = daily_obs.value_counts().head(10)
        print(f"\nTop 10 des intervalles (jours):")
        for interval, count in interval_counts.items():
            print(f"   {interval} jour(s): {count} fois")
        
        # Vérification théorique
        print(f"\n🔍 VÉRIFICATION THÉORIQUE")
        print(f"MCD43A3 = composite de 16 jours")
        print(f"Saison de fonte (juin-septembre) = ~4 mois = ~120 jours")
        print(f"Attendu par année: ~120/16 = ~7-8 composites")
        print(f"Attendu sur 5 ans: ~35-40 observations")
        print(f"Observé: {len(df)} observations")
        
        ratio = len(df) / 40
        print(f"Ratio observé/attendu: {ratio:.1f}x")
        
        if ratio > 2:
            print("⚠️  ATTENTION: Beaucoup plus d'observations que prévu!")
            print("   Possible explication: données journalières au lieu de composites 16-jours")
        
        # Échantillon de dates
        print(f"\n📋 ÉCHANTILLON DE DATES (premières 20):")
        sample_dates = df_sorted.head(20)
        for _, row in sample_dates.iterrows():
            print(f"   {row['date'].strftime('%Y-%m-%d')} (année {row['year']}, mois {row['date'].month})")
        
        return df
        
    except FileNotFoundError:
        print("❌ Fichier de données non trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

if __name__ == "__main__":
    analyze_mcd43a3_observations() 