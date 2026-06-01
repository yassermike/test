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

# ============= CONFIGURATION DE LA PAGE =============
st.set_page_config(
    page_title="Validateur Client Mystère",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        max_rows = st.number_input("Lignes max à analyser par IA", 10, 500, 50)
        batch_size = st.number_input("Taille des batches", 1, 10, 3)
        model_choice = st.selectbox(
            "Modèle IA",
            ["mistral-small-latest (rapide)", "mistral-large-latest (précis)"],
            index=0
        )

    st.markdown("---")
    st.caption("🚀 Propulsé par Mistral AI (gratuit)")

# ============= ZONE PRINCIPALE =============
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 1. Upload Données",
    "📋 2. Règles Métier",
    "🤖 3. Analyse IA",
    "🔎 4. Validation",
    "📊 5. Rapport"
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

# ============= TAB 2 : RÈGLES MÉTIER (INSTRUCTIONS DE VÉRIFICATION) =============
with tab2:
    st.header("📋 Règles Métier - Instructions de Vérification")
    
    st.markdown("""
    Chargez ici votre fichier Excel **"Instructions de vérification"** qui contient les règles 
    spécifiques à votre étude. La plateforme va parser automatiquement ces règles et les appliquer 
    lors de la validation.
    
    💡 **Format attendu** : un fichier Excel avec :
    - **Feuille 1** : le questionnaire (structure de l'étude)
    - **Feuille 2** : les instructions de vérification (les règles)
    
    Les colonnes reconnues automatiquement : ID, Description/Règle, Colonne cible, Condition, 
    Valeur attendue, Sévérité, Type, Action...
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        instructions_file = st.file_uploader(
            "📥 Téléversez le fichier d'instructions de vérification",
            type=['xlsx', 'xls'],
            key="instructions_uploader",
            help="Fichier Excel contenant les règles de validation spécifiques à votre étude"
        )
    
    with col2:
        st.info("""
        **Astuce** : Vous pouvez aussi uploader ici le fichier qui contient 
        à la fois le questionnaire ET les instructions sur 2 feuilles séparées.
        """)
    
    if instructions_file:
        try:
            parser = InstructionsParser(file_buffer=instructions_file)
            load_info = parser.load()
            
            st.success(f"✅ Fichier chargé: **{instructions_file.name}**")
            
            # Afficher les feuilles détectées
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📑 Feuilles détectées:**")
                for sheet in load_info["sheets_found"]:
                    marker = ""
                    if sheet == load_info["questionnaire_sheet"]:
                        marker = " 🔵 (Questionnaire)"
                    elif sheet == load_info["instructions_sheet"]:
                        marker = " 🟢 (Instructions)"
                    st.markdown(f"- `{sheet}`{marker}")
            
            with col_b:
                st.metric("📋 Règles détectées", load_info["nb_rules"])
                st.metric("❓ Questions", load_info["nb_rows_questionnaire"])
            
            # Permettre à l'utilisateur de réassigner les feuilles si auto-détection incorrecte
            with st.expander("🔧 Modifier l'attribution des feuilles"):
                sheets = load_info["sheets_found"]
                
                q_sheet = st.selectbox(
                    "Feuille du questionnaire",
                    sheets,
                    index=sheets.index(load_info["questionnaire_sheet"]) if load_info["questionnaire_sheet"] in sheets else 0
                )
                
                i_sheet = st.selectbox(
                    "Feuille des instructions",
                    sheets,
                    index=sheets.index(load_info["instructions_sheet"]) if load_info["instructions_sheet"] in sheets else (1 if len(sheets) > 1 else 0)
                )
                
                if st.button("🔄 Réassigner"):
                    parser.questionnaire_df = parser.all_sheets[q_sheet]
                    parser.instructions_df = parser.all_sheets[i_sheet]
                    parser.questionnaire_sheet_name = q_sheet
                    parser.instructions_sheet_name = i_sheet
                    st.rerun()
            
            # Aperçu du questionnaire
            st.markdown("---")
            st.subheader("📝 Aperçu du questionnaire (Feuille 1)")
            if parser.questionnaire_df is not None:
                st.dataframe(parser.questionnaire_df.head(10), use_container_width=True)
            
            # Aperçu des instructions
            st.subheader("📜 Aperçu des instructions de vérification (Feuille 2)")
            if parser.instructions_df is not None:
                st.dataframe(parser.instructions_df, use_container_width=True)
            
            # Parser les règles
            if st.button("⚙️ Parser les règles automatiquement", type="primary", use_container_width=True):
                with st.spinner("Analyse des règles en cours..."):
                    rules = parser.parse_rules()
                
                st.session_state.business_rules = rules
                st.session_state.instructions_summary = parser.get_rules_summary()
                
                st.success(f"✅ **{len(rules)} règles** parsées et prêtes à être appliquées")
                
                # Résumé
                summary = parser.get_rules_summary()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total règles", summary.get("total", 0))
                with col2:
                    critique = summary.get("par_severite", {}).get("critique", 0)
                    st.metric("🔴 Critiques", critique)
                with col3:
                    types_count = len(summary.get("par_type", {}))
                    st.metric("Types de règles", types_count)
                
                # Détail par type
                if summary.get("par_type"):
                    st.markdown("**📊 Répartition par type:**")
                    type_df = pd.DataFrame([
                        {"Type": k, "Nombre": v}
                        for k, v in summary["par_type"].items()
                    ])
                    st.bar_chart(type_df.set_index("Type"))
                
                # Tableau des règles
                st.markdown("---")
                st.subheader("📜 Règles parsées")
                rules_display = pd.DataFrame([
                    {
                        "ID": r["id"],
                        "Description": r["description"][:100] + ("..." if len(r["description"]) > 100 else ""),
                        "Colonne": r["colonne_cible"],
                        "Sévérité": r["severite"],
                        "Type": r["type"]
                    }
                    for r in rules
                ])
                st.dataframe(rules_display, use_container_width=True, height=400)
                
                # Détail d'une règle
                with st.expander("🔍 Voir le détail d'une règle"):
                    rule_id = st.selectbox("Sélectionnez une règle", [r["id"] for r in rules])
                    selected_rule = next((r for r in rules if r["id"] == rule_id), None)
                    if selected_rule:
                        st.json(selected_rule)
        
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement: {e}")
            st.exception(e)
    
    # Afficher l'état actuel
    if st.session_state.business_rules:
        st.markdown("---")
        st.success(f"✅ **{len(st.session_state.business_rules)} règles métier** chargées et prêtes")
    else:
        st.info("ℹ️ Aucune règle métier chargée. La validation utilisera uniquement les règles génériques.")


# ============= TAB 3 : ANALYSE IA =============
with tab3:
    st.header("🤖 Analyse intelligente par Claude")
    
    if st.session_state.df is None:
        st.warning("⚠️ Veuillez d'abord téléverser un fichier dans l'onglet 1")
    else:
        # Indicateur règles métier
        if st.session_state.business_rules:
            st.success(f"✅ {len(st.session_state.business_rules)} règles métier chargées seront intégrées à l'analyse")
        else:
            st.info("ℹ️ Aucune règle métier chargée. Claude utilisera ses règles génériques. Pour de meilleurs résultats, chargez vos instructions dans l'onglet 2.")
        
        st.markdown("""
        Claude va analyser la **structure de votre étude** pour:
        - Identifier le type et le secteur
        - Mapper vos règles métier aux colonnes du fichier
        - Détecter les questions à branchement (skip logic)
        - Proposer des règles supplémentaires
        """)
        
        if st.button("🚀 Lancer l'analyse de structure", type="primary", use_container_width=True):
            try:
                analyzer = ClaudeAnalyzer(
                    model="mistral-large-latest" if "précis" in model_choice else "mistral-small-latest"
                )
                
                with st.spinner("🧠 Llama analyse votre étude... (peut prendre 30-60 sec)"):
                    if st.session_state.business_rules:
                        # Analyse avec règles métier
                        structure = analyzer.analyze_with_business_rules(
                            questionnaire_columns=list(st.session_state.df.columns),
                            sample_data=st.session_state.df.head(5).to_dict('records'),
                            business_rules=st.session_state.business_rules,
                            study_type=study_type,
                            custom_prompt=custom_prompt
                        )
                    else:
                        # Analyse générique
                        structure = analyzer.analyze_structure(
                            questions=list(st.session_state.df.columns),
                            sample_data=st.session_state.df.head(5).to_dict('records'),
                            study_type=study_type,
                            custom_prompt=custom_prompt
                        )
                
                st.session_state.structure_analysis = structure
                
                # Parser la réponse
                try:
                    import re
                    json_match = re.search(r'\{.*\}', structure, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                    else:
                        parsed = {"raw": structure}
                except:
                    parsed = {"raw": structure}
                
                # Combiner règles métier + règles auto-détectées
                auto_rules = parsed.get("regles_supplementaires", []) or parsed.get("regles", []) or parsed.get("rules", [])
                st.session_state.rules = st.session_state.business_rules + auto_rules
                
                # Affichage
                st.success(f"✅ Analyse terminée! ({len(st.session_state.rules)} règles au total)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Synthèse")
                    if "type_etude" in parsed:
                        st.info(f"**Type identifié:** {parsed['type_etude']}")
                    if "secteur" in parsed:
                        st.info(f"**Secteur:** {parsed['secteur']}")
                    if "questions_critiques" in parsed:
                        st.markdown("**🎯 Questions critiques:**")
                        for q in parsed["questions_critiques"]:
                            st.markdown(f"- {q}")
                
                with col2:
                    st.subheader("🔗 Mapping règles métier")
                    if "regles_metier_mappees" in parsed:
                        for mapping in parsed["regles_metier_mappees"]:
                            st.markdown(f"**{mapping.get('id_regle')}** → `{mapping.get('colonne_questionnaire')}`")
                            st.caption(mapping.get('interpretation', ''))
                    else:
                        st.markdown("**Règles auto-détectées:**")
                        for rule in auto_rules[:5]:
                            if isinstance(rule, dict):
                                st.markdown(f"- {rule.get('description', rule)}")
                
                with st.expander("🔍 Voir la réponse complète de Claude"):
                    st.json(parsed)
                
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
                st.info("Vérifiez que votre clé MISTRAL_API_KEY est bien configurée dans le fichier .env")

# ============= TAB 4 : VALIDATION =============
with tab4:
    st.header("🔎 Validation détaillée des données")
    
    if st.session_state.df is None:
        st.warning("⚠️ Veuillez d'abord téléverser un fichier")
    elif st.session_state.structure_analysis is None:
        st.warning("⚠️ Lancez d'abord l'analyse de structure (Onglet 2)")
    else:
        st.markdown("Cette étape valide chaque ligne selon les règles détectées et vos critères personnalisés.")
        
        col1, col2 = st.columns(2)
        with col1:
            rows_to_check = st.slider(
                "Nombre de lignes à vérifier",
                min_value=10,
                max_value=min(len(st.session_state.df), max_rows),
                value=min(50, len(st.session_state.df))
            )
        with col2:
            validation_depth = st.radio(
                "Profondeur de validation",
                ["⚡ Rapide (règles locales)", "🤖 Approfondie (IA Claude)", "🔥 Complète (les deux)"],
                index=2
            )
        
        if st.button("▶️ Lancer la validation", type="primary", use_container_width=True):
            errors_all = []
            df_subset = st.session_state.df.head(rows_to_check)
            
            # ===== Validation locale =====
            if "Rapide" in validation_depth or "Complète" in validation_depth:
                st.subheader("⚡ Validation locale (règles automatiques)")
                local_validator = LocalValidator(
                    check_skip_logic=check_skip_logic,
                    check_outliers=check_outliers,
                    check_comments=check_comments,
                    check_duplicates=check_duplicates,
                    check_dates=check_dates
                )
                
                with st.spinner("Validation locale en cours..."):
                    local_errors = local_validator.validate(df_subset)
                
                errors_all.extend(local_errors)
                st.success(f"✅ Validation locale terminée: **{len(local_errors)} anomalies** détectées")
            
            # ===== Validation IA =====
            if "Approfondie" in validation_depth or "Complète" in validation_depth:
                st.subheader("🤖 Validation IA (Claude)")
                
                analyzer = ClaudeAnalyzer(
                    model="mistral-large-latest" if "précis" in model_choice else "mistral-small-latest"
                )
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Traitement par batches
                rows_list = df_subset.to_dict('records')
                total_batches = (len(rows_list) + batch_size - 1) // batch_size
                
                for batch_idx in range(total_batches):
                    start = batch_idx * batch_size
                    end = min(start + batch_size, len(rows_list))
                    batch = rows_list[start:end]
                    
                    status_text.text(f"Batch {batch_idx + 1}/{total_batches} - Lignes {start+1} à {end}")
                    
                    try:
                        batch_errors = analyzer.validate_batch(
                            rows=batch,
                            rules=st.session_state.rules,
                            start_row=start + 1,
                            custom_prompt=custom_prompt
                        )
                        errors_all.extend(batch_errors)
                    except Exception as e:
                        st.warning(f"⚠️ Erreur batch {batch_idx + 1}: {e}")
                    
                    progress_bar.progress((batch_idx + 1) / total_batches)
                
                status_text.text("✅ Validation IA terminée!")
            
            # Stocker les erreurs
            st.session_state.errors_found = errors_all
            st.session_state.analysis_done = True
            
            # Affichage résultats
            st.markdown("---")
            st.subheader("📋 Résultats")
            
            if not errors_all:
                st.markdown('<div class="success-box"><h3>✅ Aucune anomalie détectée!</h3><p>Vos données semblent cohérentes.</p></div>', unsafe_allow_html=True)
            else:
                # Stats par sévérité
                severities = {}
                for err in errors_all:
                    sev = err.get('severite', 'info')
                    severities[sev] = severities.get(sev, 0) + 1
                
                col1, col2, col3 = st.columns(3)
                col1.metric("🔴 Critiques", severities.get('critique', 0))
                col2.metric("🟠 Modérées", severities.get('moderee', 0) + severities.get('warning', 0))
                col3.metric("🟡 Mineures", severities.get('mineure', 0) + severities.get('info', 0))
                
                # Tableau d'erreurs
                errors_df = pd.DataFrame(errors_all)
                st.dataframe(errors_df, use_container_width=True, height=400)

# ============= TAB 5 : RAPPORT =============
with tab5:
    st.header("📊 Rapport & Export")
    
    if not st.session_state.analysis_done:
        st.warning("⚠️ Lancez d'abord une validation (Onglet 3)")
    else:
        st.success(f"✅ {len(st.session_state.errors_found)} anomalies trouvées")
        
        # Génération rapport
        generator = ReportGenerator(
            df=st.session_state.df,
            errors=st.session_state.errors_found,
            structure=st.session_state.structure_analysis
        )
        
        # Visualisations
        if st.session_state.errors_found:
            st.subheader("📈 Visualisations")
            
            errors_df = pd.DataFrame(st.session_state.errors_found)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'colonne' in errors_df.columns:
                    by_col = errors_df['colonne'].value_counts().head(10)
                    st.bar_chart(by_col)
                    st.caption("Top 10 colonnes avec erreurs")
            
            with col2:
                if 'type_erreur' in errors_df.columns:
                    by_type = errors_df['type_erreur'].value_counts()
                    st.bar_chart(by_type)
                    st.caption("Répartition par type d'erreur")
        
        st.markdown("---")
        st.subheader("📥 Export des résultats")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export CSV
            csv_data = generator.to_csv()
            st.download_button(
                "📄 Télécharger CSV",
                csv_data,
                f"rapport_erreurs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Export Excel avec corrections
            excel_data = generator.to_excel_with_corrections()
            st.download_button(
                "📊 Excel avec corrections",
                excel_data,
                f"donnees_corrigees_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col3:
            # Rapport HTML
            html_report = generator.to_html_report()
            st.download_button(
                "📑 Rapport HTML",
                html_report,
                f"rapport_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                "text/html",
                use_container_width=True
            )

# ============= FOOTER =============
st.markdown("---")
st.markdown(
    '<p style="text-align:center; color:#999;">💡 Plateforme développée pour les études de marché - Visites mystère & Satisfaction</p>',
    unsafe_allow_html=True
)
