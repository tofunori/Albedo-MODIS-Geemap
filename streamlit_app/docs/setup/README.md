# Documentation de Configuration

Guides de configuration et de déploiement pour l'interface web Streamlit.

## 📋 **Guides Disponibles**

### **`EARTH_ENGINE_SETUP.md`**
- **Sujet** : Configuration de Google Earth Engine
- **Contenu** : 
  - Authentification du service
  - Configuration des credentials
  - Variables d'environnement
  - Résolution de problèmes d'accès

### **`QA_IMPLEMENTATION_SUMMARY.md`**
- **Sujet** : Résumé de l'implémentation QA
- **Contenu** :
  - Niveaux de qualité MODIS
  - Filtres QA implémentés
  - Configuration des seuils
  - Exemples d'utilisation

### **`STREAMLIT_DEPLOYMENT.md`**
- **Sujet** : Guide de déploiement Streamlit
- **Contenu** :
  - Déploiement local
  - Déploiement sur Streamlit Cloud
  - Configuration des secrets
  - Bonnes pratiques de production

## 🚀 **Configuration Rapide**

### **Google Earth Engine**
1. Lire `EARTH_ENGINE_SETUP.md`
2. Configurer les credentials dans `assets/credentials/`
3. Tester l'authentification

### **Qualité des Données**
1. Consulter `QA_IMPLEMENTATION_SUMMARY.md`
2. Choisir le niveau QA approprié
3. Configurer les filtres

### **Déploiement**
1. Suivre `STREAMLIT_DEPLOYMENT.md`
2. Configurer les variables d'environnement
3. Déployer et tester

## ⚙️ **Prérequis**

### **Compte Google Earth Engine**
- Inscription sur [Google Earth Engine](https://earthengine.google.com/)
- Validation du compte pour l'accès aux données
- Génération d'une clé de service

### **Compte Streamlit Cloud**
- Inscription sur [Streamlit Cloud](https://share.streamlit.io/)
- Connexion au repository GitHub
- Configuration des secrets

## 🔧 **Dépannage**

### **Problèmes courants**
- **Authentification Earth Engine** → Voir `EARTH_ENGINE_SETUP.md`
- **Erreurs PyArrow** → Utiliser `../scripts/fix_pyarrow.py`
- **Configuration QA** → Consulter `QA_IMPLEMENTATION_SUMMARY.md`
- **Déploiement** → Suivre `STREAMLIT_DEPLOYMENT.md`

### **Support**
- Vérifier la documentation dans ce dossier
- Consulter les logs de l'application
- Tester les configurations étape par étape

---
*Documentation de configuration - Organisation : 2025-01-08*