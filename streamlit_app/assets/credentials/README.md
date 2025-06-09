# Credentials et Assets

Fichiers de configuration sensibles pour l'authentification et les services externes.

## 🔒 **Fichiers de Credentials**

### **`leafy-bulwark-442103-e7-40c3cef68089.json`**
- **Type** : Clé de service Google Earth Engine
- **Usage** : Authentification pour l'accès aux données MODIS
- **Format** : JSON avec clés privées Google Cloud
- **Variable d'env** : `GOOGLE_APPLICATION_CREDENTIALS`

## ⚠️ **SÉCURITÉ IMPORTANTE**

### **🚨 NE PAS COMMITER ces fichiers !**
```bash
# Ajouter à .gitignore
echo "streamlit_app/assets/credentials/*.json" >> .gitignore
echo "streamlit_app/assets/credentials/*.key" >> .gitignore
```

### **Configuration sécurisée**
```bash
# Variable d'environnement locale
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/streamlit_app/assets/credentials/leafy-bulwark-442103-e7-40c3cef68089.json"

# Pour production (Streamlit Cloud)
# → Configurer dans les "Secrets" de l'application
```

## 🔧 **Configuration**

### **Développement local**
1. Placer le fichier JSON dans ce dossier
2. Configurer la variable d'environnement
3. Tester l'authentification : `earthengine authenticate`

### **Déploiement production**
1. **NE PAS** inclure le fichier dans git
2. Configurer via les secrets Streamlit Cloud
3. Utiliser les variables d'environnement

## 📋 **Gestion des Credentials**

### **Génération d'une nouvelle clé**
1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Sélectionner le projet `leafy-bulwark-442103-e7`
3. IAM & Admin → Comptes de service
4. Créer une clé JSON pour le compte Earth Engine

### **Rotation des clés**
- Générer une nouvelle clé périodiquement
- Supprimer les anciennes clés
- Mettre à jour dans tous les environnements

### **Sauvegarde sécurisée**
- Stocker dans un gestionnaire de mots de passe
- Chiffrer pour la sauvegarde
- Accès restreint aux développeurs autorisés

## 🚫 **Ce qu'il ne faut PAS faire**

- ❌ Commiter les fichiers JSON dans git
- ❌ Partager les clés par email/Slack
- ❌ Laisser les clés en clair dans le code
- ❌ Utiliser la même clé pour dev et prod

## ✅ **Bonnes pratiques**

- ✅ Utiliser des variables d'environnement
- ✅ Configurer .gitignore approprié
- ✅ Rotation régulière des clés
- ✅ Accès minimal nécessaire
- ✅ Monitoring de l'utilisation

---
*Documentation credentials - Sécurité : 2025-01-08*

⚠️ **RAPPEL** : Ces fichiers contiennent des informations sensibles. Manipuler avec précaution !