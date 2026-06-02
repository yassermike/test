"""
Plateforme de Validation - Études Client Mystère & Satisfaction
Auteur: Data Analyst - Étude de marché
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from modules.excel_reader import ExcelReader
from modules.claude_analyzer import ClaudeAnalyzer
from modules.validator import LocalValidator
from modules.report_generator import ReportGenerator
from modules.instructions_parser import InstructionsParser
from modules.sga_validator import SGAValidator, export_to_excel

# ============= CONFIGURATION DE LA PAGE =============
st.set_page_config(
    page_title="Validateur Client Mystère",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============= PROTECTION PAR MOT DE PASSE =============
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("## 🔐 Accès réservé — Dusens Research")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        correct = st.secrets.get("APP_PASSWORD", "dusens2024")
        if password == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    return False

if not check_password():
    st.stop()

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .error-box {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #f44336;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #4caf50;
    }
    .warning-box {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #ff9800;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============= ÉTAT DE SESSION =============
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'structure_analysis' not in st.session_state:
    st.session_state.structure_analysis = None
if 'errors_found' not in st.session_state:
    st.session_state.errors_found = []
if 'df' not in st.session_state:
    st.session_state.df = None
if 'rules' not in st.session_state:
    st.session_state.rules = []
if 'business_rules' not in st.session_state:
    st.session_state.business_rules = []
if 'instructions_summary' not in st.session_state:
    st.session_state.instructions_summary = None

# ============= HEADER =============
st.markdown('<h1 class="main-header">🔍 Plateforme de Validation</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color: #666; font-size: 1.1rem;">Études Client Mystère & Satisfaction — Vérification automatisée avec IA</p>', unsafe_allow_html=True)
st.markdown("---")

# ============= SIDEBAR : CONFIGURATION =============
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Type d'étude
    study_type = st.selectbox(
        "📋 Type d'étude",
        ["Visite Mystère", "Étude de Satisfaction", "Mixte (les deux)"],
        help="Sélectionnez le type d'étude pour adapter la validation"
    )
    
    st.markdown("---")
    
    # Modes de validation
    st.subheader("🎯 Modes de validation")
    check_skip_logic = st.checkbox("✅ Cohérence logique (skip logic)", value=True)
    check_outliers = st.checkbox("✅ Détection valeurs aberrantes", value=True)
    check_comments = st.checkbox("✅ Validation commentaires/photos", value=True)
    check_duplicates = st.checkbox("✅ Détection doublons", value=True)
    check_dates = st.checkbox("✅ Validation dates/heures", value=True)
    
    st.markdown("---")
    
    # Prompt personnalisé
    st.subheader("💬 Prompt personnalisé")
    custom_prompt = st.text_area(
        "Instructions spéciales pour Claude",
        placeholder="Ex: Vérifie que les notes ≥ 8 ont un commentaire positif, et que les notes ≤ 4 ont un commentaire détaillé avec photo...",
        height=180,
        help="Ajoutez vos règles métier spécifiques"
    )
    
    # Charger/sauvegarder prompts
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Sauvegarder"):
            if custom_prompt:
                with open("prompts/custom_prompts.json", "r+") as f:
                    try:
                        data = json.load(f)
                    except:
                        data = {}
                    name = f"prompt_{datetime.now().strftime('%Y%m%d_%H%M')}"
                    data[name] = custom_prompt
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=2)
                st.success("Prompt sauvegardé!")
    
    st.markdown("---")
    
    # Paramètres avancés
    with st.expander("🔧 Paramètres avancés"):
        max_rows = st.number_input("Lignes max à analyser par IA", 10, 10000, 5000)
        batch_size = st.number_input("Taille des batches", 1, 20, 10)
        model_choice = st.selectbox(
            "Modèle IA",
            ["mistral-small-latest (rapide)", "mistral-large-latest (précis)"],
            index=0
        )

    st.markdown("---")
    st.caption("🚀 Propulsé par Mistral AI (gratuit)")

# ============= ÉTAT VALIDATION SGA =============
if 'sga_df_data' not in st.session_state:
    st.session_state.sga_df_data = None
if 'sga_df_corrections' not in st.session_state:
    st.session_state.sga_df_corrections = None
if 'sga_summary' not in st.session_state:
    st.session_state.sga_summary = None

# ============= ZONE PRINCIPALE =============
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 1. Upload Données",
    "📋 2. Règles SGA",
    "🚀 3. Lancer la validation",
    "📥 4. Télécharger les résultats",
    "🤖 5. Analyse IA (optionnel)"
])

# ============= TAB 1 : UPLOAD =============
with tab1:
    st.header("📤 Téléversez votre fichier Excel")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Sélectionnez votre fichier (.xlsx, .xls, .csv)",
            type=['xlsx', 'xls', 'csv'],
            help="Fichier Excel contenant les réponses des enquêteurs/clients mystère"
        )
    
    with col2:
        st.info("""
        **Formats acceptés:**
        - Excel (.xlsx, .xls)
        - CSV (.csv)
        
        **Taille optimale:**
        500 à 2000 lignes
        """)
    
    if uploaded_file:
        try:
            # Lire le fichier
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.session_state.df = df
            
            st.success(f"✅ Fichier chargé: **{uploaded_file.name}**")
            
            # Métriques
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-card"><h3>{len(df)}</h3><p>Lignes</p></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><h3>{len(df.columns)}</h3><p>Colonnes</p></div>', unsafe_allow_html=True)
            with col3:
                missing = df.isnull().sum().sum()
                st.markdown(f'<div class="metric-card"><h3>{missing}</h3><p>Cellules vides</p></div>', unsafe_allow_html=True)
            with col4:
                duplicates = df.duplicated().sum()
                st.markdown(f'<div class="metric-card"><h3>{duplicates}</h3><p>Doublons</p></div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Aperçu
            st.subheader("👁️ Aperçu des données")
            st.dataframe(df.head(20), use_container_width=True)
            
            # Détail colonnes
            with st.expander("📋 Détails des colonnes"):
                col_info = pd.DataFrame({
                    "Colonne": df.columns,
                    "Type": df.dtypes.astype(str),
                    "Valeurs uniques": [df[c].nunique() for c in df.columns],
                    "Valeurs manquantes": df.isnull().sum().values,
                    "% manquantes": (df.isnull().sum() / len(df) * 100).round(2).values
                })
                st.dataframe(col_info, use_container_width=True)
                
        except Exception as e:
            st.error(f"❌ Erreur de lecture: {e}")

# ============= TAB 2 : RÈGLES SGA =============
with tab2:
    st.header("📋 Règles de vérification SGA — codées en dur")
    st.markdown("Ces 7 règles sont appliquées automatiquement à chaque validation. Aucun fichier d'instructions à charger.")

    rules_info = [
        ("R1", "critique",  "Couverture agence",
         "Chaque agence doit avoir exactement **3 visites**. Toute agence avec moins ou plus de 3 visites est signalée."),
        ("R2", "critique",  "Mix profils PRI/PRO",
         "Par agence : au moins **2 visites PRI + 1 PRO**, ou **1 PRI + 2 PRO**. Un mix homogène (3 PRI ou 3 PRO) est invalide."),
        ("R3", "modérée",   "Diversité des scénarios",
         "Les 3 visites d'une agence doivent avoir des **scénarios différents** (PRI, PRO, CORPO). Les doublons de scénario sont signalés."),
        ("R4", "modérée",   "Cohérence note / satisfaction / recommandation",
         "Une note ≥ 8 doit correspondre à *Satisfait* ou *Très satisfait*. Une note ≤ 4 doit correspondre à *Insatisfait*. Incohérence entre satisfaction et recommandation également vérifiée."),
        ("R5", "modérée",   "Cohérence heure de visite / créneau déclaré",
         "L'heure réelle de visite doit tomber dans le créneau horaire coché par l'enquêteur (ex : 13h30–15h30)."),
        ("R6", "mineure",   "Cohérence temps d'attente / créneau",
         "Le nombre de minutes d'attente déclaré doit correspondre à la tranche cochée (0–5 min, 6–10 min, etc.)."),
        ("R7", "mineure",   "Cohérence temps conseiller / créneau",
         "Le temps passé avec le conseiller (en minutes) doit correspondre à la tranche cochée."),
    ]

    sev_colors = {"critique": "🔴", "modérée": "🟠", "mineure": "🟡"}

    for rid, sev, title, desc in rules_info:
        icon = sev_colors.get(sev, "⚪")
        with st.expander(f"{icon} **{rid}** — {title}  *({sev})*", expanded=False):
            st.markdown(desc)

    st.markdown("---")
    st.info("Pour modifier ou ajouter une règle, contactez l'équipe Dusens Research.")


# ============= TAB 3 : VALIDATION SGA =============
with tab3:
    st.header("🚀 Validation SGA")

    if st.session_state.df is None:
        st.warning("⚠️ Commencez par téléverser votre fichier dans l'onglet 1.")
    else:
        df = st.session_state.df
        st.info(f"Fichier chargé : **{len(df)} lignes × {len(df.columns)} colonnes**")
        st.markdown("Les **7 règles SGA** vont être appliquées à l'ensemble du fichier. Cliquez sur le bouton ci-dessous.")

        # Afficher les colonnes détectées
        with st.expander("🔍 Colonnes détectées dans votre fichier"):
            try:
                v_check = SGAValidator(df)
                st.write({
                    "Profil client": v_check.col_profil,
                    "Scénario PRI": v_check.col_scen_pri,
                    "Scénario PRO": v_check.col_scen_pro,
                    "Heure visite": v_check.col_heure,
                    "Créneau heure": v_check.col_heure_grille,
                    "Temps attente (min)": v_check.col_att_min,
                    "Créneau attente": v_check.col_att_grille,
                    "Note valorisation": v_check.col_note,
                    "Satisfaction": v_check.col_satisfaction,
                    "Recommandation": v_check.col_recommandation,
                    "Nb colonnes agence": len(v_check.city_cols),
                })
            except Exception as ex:
                st.warning(f"Détection colonnes: {ex}")

        if st.button("▶️ Lancer la validation complète", type="primary", use_container_width=True):
            with st.spinner("Validation en cours..."):
                try:
                    validator = SGAValidator(df)
                    df_data, df_corrections = validator.run()
                    summary = validator.get_summary()

                    st.session_state.sga_df_data        = df_data
                    st.session_state.sga_df_corrections = df_corrections
                    st.session_state.sga_summary        = summary
                    st.session_state.analysis_done      = True

                except Exception as e:
                    st.error(f"Erreur lors de la validation : {e}")
                    st.exception(e)

        if st.session_state.sga_summary:
            s = st.session_state.sga_summary
            st.markdown("---")
            st.subheader("📊 Résumé")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Lignes analysées",        s['lignes_total'])
            c2.metric("Lignes avec problème",     s['lignes_avec_erreur'])
            c3.metric("Erreurs critiques",        s['by_severite'].get('critique', 0))
            c4.metric("Erreurs modérées/mineures",s['by_severite'].get('moderee', 0) + s['by_severite'].get('mineure', 0))

            st.markdown("**Détail par règle :**")
            rule_df = pd.DataFrame([
                {"Règle": k, "Nb erreurs": v}
                for k, v in sorted(s['by_rule'].items())
            ])
            if not rule_df.empty:
                st.bar_chart(rule_df.set_index('Règle'))

            st.markdown("---")
            st.success("✅ Validation terminée. Rendez-vous dans l'onglet **4. Télécharger les résultats**.")

# ============= TAB 4 : TÉLÉCHARGER =============
with tab4:
    st.header("📥 Télécharger les résultats")

    if not st.session_state.analysis_done or st.session_state.sga_df_data is None:
        st.warning("⚠️ Lancez d'abord la validation dans l'onglet 3.")
    else:
        s = st.session_state.sga_summary
        c1, c2, c3 = st.columns(3)
        c1.metric("Total erreurs", s['total_erreurs'])
        c2.metric("Lignes avec problème", s['lignes_avec_erreur'])
        c3.metric("Lignes propres", s['lignes_total'] - s['lignes_avec_erreur'])

        st.markdown("---")

        # Génération des fichiers Excel
        with st.spinner("Génération des fichiers Excel..."):
            excel_bytes = export_to_excel(
                st.session_state.sga_df_data,
                st.session_state.sga_df_corrections
            )

        now = datetime.now().strftime('%Y%m%d_%H%M')

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 Fichier 1 — Données vérifiées")
            st.markdown("""
            Contient **toutes vos données originales** + 3 colonnes ajoutées au début :
            - `Nb_problèmes` : nombre d'incohérences sur cette ligne
            - `Règles_violées` : quelles règles (R1, R2…)
            - `Détail_problèmes` : explication complète

            **Code couleur :**
            - 🟢 Vert = ligne correcte
            - 🟡 Orange = erreur modérée/mineure
            - 🔴 Rouge = erreur critique (R1 ou R2)
            """)

        with col2:
            st.subheader("📋 Fichier 2 — Corrections suggérées")
            st.markdown("""
            Contient **une ligne par erreur détectée**, avec :
            - La ligne concernée, l'agence, la wilaya
            - La règle violée et son explication
            - La **valeur actuelle** et la **correction suggérée**

            Trié par sévérité (critiques en premier).
            """)

        st.markdown("---")

        st.download_button(
            label="⬇️ Télécharger le fichier Excel complet (2 feuilles)",
            data=excel_bytes,
            file_name=f"SGA_validation_{now}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

        st.markdown("---")
        st.subheader("👁️ Aperçu des corrections")
        st.dataframe(st.session_state.sga_df_corrections.head(50), use_container_width=True, height=400)

# ============= TAB 5 : ANALYSE IA (OPTIONNEL) =============
with tab5:
    st.header("🤖 Analyse IA supplémentaire (optionnel)")
    st.info("Cette fonctionnalité utilise Mistral AI pour détecter des incohérences supplémentaires non couvertes par les 7 règles SGA. Elle nécessite une clé MISTRAL_API_KEY valide.")

    if st.session_state.df is None:
        st.warning("⚠️ Veuillez d'abord téléverser un fichier dans l'onglet 1")
    else:
        if st.button("🚀 Lancer l'analyse IA", type="secondary", use_container_width=True):
            try:
                analyzer = ClaudeAnalyzer(
                    model="mistral-large-latest" if "précis" in model_choice else "mistral-small-latest"
                )
                with st.spinner("🧠 Analyse IA en cours..."):
                    structure = analyzer.analyze_structure(
                        questions=list(st.session_state.df.columns),
                        sample_data=st.session_state.df.head(3).to_dict('records'),
                        study_type=study_type,
                        custom_prompt=custom_prompt
                    )
                st.session_state.structure_analysis = structure
                import re as _re
                json_match = _re.search(r'\{.*\}', structure, _re.DOTALL)
                parsed = json.loads(json_match.group()) if json_match else {"raw": structure}
                st.success("✅ Analyse IA terminée")
                st.json(parsed)
            except Exception as e:
                st.error(f"Erreur: {e}")
                st.info("Vérifiez que votre clé MISTRAL_API_KEY est bien configurée dans le fichier .env")

# ============= FOOTER =============
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#999;">💡 Plateforme développée pour les études de marché - Visites mystère & Satisfaction</p>',
    unsafe_allow_html=True
)
