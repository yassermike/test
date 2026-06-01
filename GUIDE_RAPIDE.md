# 🚀 GUIDE DÉMARRAGE RAPIDE (10 minutes)

## Étape 1 : Préparer l'environnement (3 min)

### Sur Windows :
```cmd
# Ouvrir PowerShell ou CMD dans le dossier du projet
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Sur Mac/Linux :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Étape 2 : Configurer la clé API Claude (2 min)

1. Va sur **console.anthropic.com**
2. Connecte-toi et crée une clé API
3. Renomme `.env.example` en `.env`
4. Ouvre `.env` et remplace par ta vraie clé :
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxx
   ```

## Étape 3 : Lancer la plateforme (1 min)

```bash
streamlit run app.py
```

→ Ouvre automatiquement **http://localhost:8501**

## Étape 4 : Utilisation (4 min)

### Onglet 1 : Upload
- Glisse-dépose ton fichier Excel des études client mystère

### Onglet 2 : Analyse IA
- Clique sur "Lancer l'analyse" 
- Claude détecte automatiquement la structure

### Onglet 3 : Validation
- Choisis "Complète" pour la meilleure qualité
- Lance la validation

### Onglet 4 : Rapport
- Télécharge en Excel (avec cellules colorées)
- Ou en HTML pour partager

---

## 🌐 Pour rendre la plateforme accessible à tous :

### Option 1 : Streamlit Cloud (gratuit, recommandé)

1. Crée un compte GitHub si pas déjà
2. Push ton projet :
```bash
git init
git add .
git commit -m "Premier commit"
git branch -M main
git remote add origin https://github.com/TON_USER/mystery-shopper-validator.git
git push -u origin main
```

3. Va sur **share.streamlit.io**
4. "New app" → connecte ton repo
5. Dans **Advanced settings → Secrets**, colle :
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-xxxxx"
```

6. Deploy ! Tu obtiens une URL publique en 2 minutes.

### Option 2 : Réseau local
Pour partager dans ton bureau :
```bash
streamlit run app.py --server.address 0.0.0.0
```
Puis les collègues accèdent via `http://TON_IP:8501`

---

## 🔧 Utiliser Claude Code pour améliorer la plateforme

Dans VS Code, ouvre un terminal :
```bash
claude
```

Exemples de demandes utiles :
- "Ajoute une fonction qui détecte les visites mystère effectuées la nuit"
- "Crée un dashboard avec graphiques par enquêteur"  
- "Ajoute un système de scoring de qualité par enquêteur"
- "Intègre l'envoi automatique du rapport par email"

---

## ❓ Problèmes fréquents

**Erreur "ANTHROPIC_API_KEY non définie"**
→ Vérifie que le fichier `.env` est bien à la racine et contient la clé

**Erreur "Module not found"**
→ Active bien le venv : `source venv/bin/activate` (ou `venv\Scripts\activate` sur Windows)

**L'analyse IA est lente**
→ Réduis le nombre de lignes ou utilise le modèle Sonnet (plus rapide)

**Coût API trop élevé**
→ Utilise le mode "Rapide" (règles locales uniquement, gratuit)
