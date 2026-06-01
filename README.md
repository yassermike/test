# 🔍 Plateforme de Validation - Études Client Mystère & Satisfaction

Plateforme web automatisée pour vérifier la qualité des bases de données Excel issues d'études client mystère et de satisfaction. Utilise l'IA Claude (Anthropic) pour détecter les incohérences, les valeurs aberrantes, les commentaires manquants et les patterns suspects.

## ✨ Fonctionnalités

- 📤 Upload de fichiers Excel/CSV (jusqu'à 50 MB)
- 📋 **NOUVEAU : Import automatique des règles métier** depuis un fichier Excel (feuille questionnaire + feuille instructions de vérification)
- 🤖 Analyse intelligente par Claude (détection automatique de la structure)
- 🔎 Validation à plusieurs niveaux :
  - **Cohérence logique** (skip logic non respectée)
  - **Valeurs aberrantes** (méthode IQR)
  - **Commentaires manquants** (sur notes faibles)
  - **Photos manquantes**
  - **Doublons et fraude potentielle**
  - **Dates invalides**
- 💬 Prompts personnalisables pour adapter à votre métier
- 📊 Rapports en CSV, Excel coloré, HTML
- 🎨 Interface dynamique et moderne
- 🌐 Accessible en ligne (déployable sur Streamlit Cloud)

## 🛠️ Installation locale

### Prérequis
- Python 3.10+
- Une clé API Anthropic ([console.anthropic.com](https://console.anthropic.com))

### Étapes

```bash
# 1. Cloner le projet
git clone <votre-repo>
cd mystery-shopper-validator

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé API
cp .env.example .env
# Éditer .env et y mettre votre clé ANTHROPIC_API_KEY

# 5. Lancer l'application
streamlit run app.py
```

L'application s'ouvre sur **http://localhost:8501**

## 🚀 Déploiement sur Streamlit Cloud (gratuit)

1. Push le code sur GitHub
2. Va sur [share.streamlit.io](https://share.streamlit.io)
3. Connecte ton compte GitHub et sélectionne le repo
4. Dans **Settings → Secrets**, ajoute :
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-xxxx"
   ```
5. Deploy ! Tu obtiens une URL publique `https://ton-app.streamlit.app`

## 📂 Structure du projet

```
mystery-shopper-validator/
├── app.py                      # Application Streamlit principale
├── modules/
│   ├── __init__.py
│   ├── excel_reader.py         # Lecture Excel/CSV
│   ├── claude_analyzer.py      # Intégration API Claude
│   ├── validator.py            # Règles locales de validation
│   └── report_generator.py     # Génération rapports
├── prompts/
│   └── custom_prompts.json     # Prompts sauvegardés
├── .streamlit/
│   └── config.toml             # Configuration UI
├── .env.example                # Template clé API
├── .gitignore
├── requirements.txt
└── README.md
```

## 💡 Utilisation

### 1. Uploadez votre fichier de données
Téléversez un fichier Excel (.xlsx) ou CSV contenant les réponses des enquêteurs.

### 2. **NOUVEAU** : Chargez vos règles métier (Onglet 2)
Uploadez votre fichier Excel "Instructions de vérification" qui contient :
- **Feuille 1** : le questionnaire (structure de l'étude)
- **Feuille 2** : les instructions de vérification (règles à appliquer)

**Format attendu pour les instructions** : un tableau avec une règle par ligne. 
Colonnes reconnues automatiquement (insensible à la casse, plusieurs noms acceptés) :

| Colonne attendue | Noms acceptés (exemples) |
|---|---|
| `id` | ID, N°, Numéro, # |
| `description` | Règle, Description, Instruction, Contrôle |
| `colonne_cible` | Colonne, Question, Variable, Champ |
| `condition` | Condition, Si, When, Lorsque |
| `valeur_attendue` | Valeur attendue, Expected, Doit être |
| `severite` | Sévérité, Priorité, Importance, Criticité |
| `type` | Type, Catégorie |
| `action` | Action, Correction, Que faire |

**Exemple de fichier instructions** :

| N° | Règle | Colonne cible | Sévérité | Action |
|---|---|---|---|---|
| 1 | Si Q1_accueil = Non, alors Q2_note doit être vide | Q2_note | Critique | Corriger |
| 2 | Si Q2_note ≤ 5, Q3_commentaire est obligatoire | Q3_commentaire | Critique | Recontacter enquêteur |
| 3 | Note doit être entre 0 et 10 | Q2_note | Modérée | Vérifier |

La plateforme parse automatiquement ces règles et les applique lors de la validation.

### 3. Analysez la structure
Claude détecte automatiquement :
- Le type d'étude et le secteur
- **Le mapping de vos règles métier aux colonnes**
- Les questions à branchement (skip logic)
- Les règles supplémentaires à ajouter

### 4. Lancez la validation
Choisissez le niveau :
- ⚡ **Rapide** : règles locales uniquement (gratuit, rapide)
- 🤖 **Approfondie** : analyse IA ligne par ligne (plus précise)
- 🔥 **Complète** : les deux combinés (recommandé)

### 5. Exportez le rapport
- **CSV** : liste plate des erreurs
- **Excel** : données avec cellules colorées par sévérité + onglets erreurs et synthèse
- **HTML** : rapport stylé à partager

## 🎯 Cas d'usage typiques

### Visites mystère retail
- Vérifier le respect du protocole d'accueil
- Cohérence durée de visite
- Photos obligatoires (vitrine, intérieur, caisse)

### Études de satisfaction (NPS, CSAT)
- Cohérence NPS (Détracteurs/Passifs/Promoteurs)
- Commentaires sur notes faibles
- Détection de répondants "fast-clickers"

### Études de marché
- Validation des quotas
- Détection de profils suspects
- Cohérence cross-question

## 💬 Personnalisation des prompts

Dans la sidebar, ajoutez vos règles métier :

```
Exemple:
"Vérifie que les notes >= 8 ont un commentaire positif, et que les notes <= 4 
ont un commentaire détaillé (> 30 caractères) avec au moins une photo. 
Détecte aussi les visites de moins de 10 minutes comme suspectes."
```

## 🔒 Sécurité & Confidentialité

- Les données ne sont **jamais stockées** (traitement en mémoire)
- La clé API reste sur le serveur (jamais exposée au client)
- Les fichiers temporaires sont supprimés à la fin de la session
- Conforme RGPD si déployé en Europe

## 📊 Coûts API estimés

Pour une base de 1000 lignes avec validation complète :
- ~5 batches de 20 lignes = **~$0.10 à $0.30**
- Modèle Sonnet 4.6 (par défaut) : très rentable
- Modèle Opus 4.7 : plus précis mais ~5x plus cher

## 🆘 Support & Améliorations

Pour personnaliser davantage, utilisez **Claude Code** :

```bash
claude
> "Ajoute un module de détection de fraude par analyse de patterns temporels"
> "Crée une visualisation cartographique des points de vente avec leur taux d'erreur"
```

## 📝 Licence

Projet personnel - usage libre pour études de marché.

---

**Développé avec ❤️ pour les analystes d'études de marché**
*Propulsé par Claude AI (Anthropic) - Streamlit - Python*
