# Scripts Utilitaires Streamlit

Scripts d'aide pour le déploiement et la maintenance de l'interface web.

## 📋 **Fichiers**

### **`deploy_streamlit.py`**
- **Usage** : Script de déploiement automatisé
- **Fonction** : Déploie l'application sur Streamlit Cloud
- **Commande** : `python deploy_streamlit.py --upload`

### **`fix_pyarrow.py`**
- **Usage** : Correctif pour les problèmes PyArrow sur Windows
- **Problème** : Erreurs "DLL load failed" avec PyArrow
- **Commande** : `python fix_pyarrow.py`

### **`generate_pixel_data.py`**
- **Usage** : Génération de données de pixels MODIS
- **Fonction** : Crée des données d'exemple pour tests
- **Commande** : `python generate_pixel_data.py`

## 🚀 **Usage**

### Déploiement
```bash
# Déployer l'application
python scripts/deploy_streamlit.py --upload

# Vérifier le statut
python scripts/deploy_streamlit.py --status
```

### Correctifs
```bash
# Corriger PyArrow
python scripts/fix_pyarrow.py

# Générer des données de test
python scripts/generate_pixel_data.py
```

## 🔧 **Maintenance**

Ces scripts facilitent :
- **Déploiement automatisé** sur Streamlit Cloud
- **Résolution de problèmes** courants
- **Génération de données** de test
- **Vérification** de l'environnement

---
*Scripts utilitaires - Organisation : 2025-01-08*