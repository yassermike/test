"""
Module de parsing des instructions de vérification depuis Excel
Lit la feuille "Instructions de vérification" et la convertit en règles exploitables
"""
import pandas as pd
from typing import List, Dict, Optional
import re


class InstructionsParser:
    """Parse les instructions de vérification depuis un fichier Excel multi-feuilles"""
    
    # Noms possibles pour la feuille de questionnaire
    QUESTIONNAIRE_SHEET_NAMES = [
        'questionnaire', 'questions', 'feuille1', 'sheet1',
        'enquete', 'enquête', 'survey', 'données', 'donnees', 'data'
    ]
    
    # Noms possibles pour la feuille d'instructions
    INSTRUCTIONS_SHEET_NAMES = [
        'instructions de vérification', 'instructions de verification',
        'instructions', 'règles', 'regles', 'rules', 'validation',
        'vérification', 'verification', 'feuille2', 'sheet2',
        'controles', 'contrôles'
    ]
    
    def __init__(self, file_path: str = None, file_buffer = None):
        self.file_path = file_path
        self.file_buffer = file_buffer
        self.all_sheets = {}
        self.questionnaire_df: Optional[pd.DataFrame] = None
        self.instructions_df: Optional[pd.DataFrame] = None
        self.questionnaire_sheet_name = None
        self.instructions_sheet_name = None
        self.parsed_rules: List[Dict] = []
    
    def load(self) -> Dict:
        """Charge le fichier Excel et identifie automatiquement les feuilles"""
        source = self.file_path if self.file_path else self.file_buffer
        
        # Charger toutes les feuilles
        self.all_sheets = pd.read_excel(source, sheet_name=None)
        
        sheet_names = list(self.all_sheets.keys())
        
        # Identifier la feuille questionnaire (par nom, sinon la 1ère)
        for sheet in sheet_names:
            if any(kw in sheet.lower() for kw in self.QUESTIONNAIRE_SHEET_NAMES):
                self.questionnaire_sheet_name = sheet
                self.questionnaire_df = self.all_sheets[sheet]
                break
        
        if self.questionnaire_df is None and sheet_names:
            self.questionnaire_sheet_name = sheet_names[0]
            self.questionnaire_df = self.all_sheets[sheet_names[0]]
        
        # Identifier la feuille instructions (par nom, sinon la 2ème)
        for sheet in sheet_names:
            if any(kw in sheet.lower() for kw in self.INSTRUCTIONS_SHEET_NAMES):
                self.instructions_sheet_name = sheet
                self.instructions_df = self.all_sheets[sheet]
                break
        
        if self.instructions_df is None and len(sheet_names) >= 2:
            self.instructions_sheet_name = sheet_names[1]
            self.instructions_df = self.all_sheets[sheet_names[1]]
        
        return {
            "sheets_found": sheet_names,
            "questionnaire_sheet": self.questionnaire_sheet_name,
            "instructions_sheet": self.instructions_sheet_name,
            "nb_rows_questionnaire": len(self.questionnaire_df) if self.questionnaire_df is not None else 0,
            "nb_rules": len(self.instructions_df) if self.instructions_df is not None else 0
        }
    
    def parse_rules(self) -> List[Dict]:
        """
        Parse les instructions de vérification en règles exploitables.
        
        Reconnaît les colonnes types suivantes (insensible à la casse):
        - ID / N° / Numéro
        - Règle / Description / Instruction / Contrôle
        - Colonne / Question / Variable / Champ
        - Condition / Si / When
        - Valeur attendue / Expected / Doit être
        - Sévérité / Priorité / Importance
        - Type / Catégorie
        - Action / Correction
        """
        if self.instructions_df is None:
            return []
        
        df = self.instructions_df.copy()
        # Supprimer les lignes entièrement vides
        df = df.dropna(how='all')
        
        # Normaliser les noms de colonnes
        col_mapping = self._map_columns(df.columns)
        
        rules = []
        for idx, row in df.iterrows():
            rule = self._row_to_rule(row, col_mapping, idx)
            if rule:
                rules.append(rule)
        
        self.parsed_rules = rules
        return rules
    
    def _map_columns(self, columns) -> Dict[str, str]:
        """Mappe automatiquement les colonnes du fichier vers nos champs standards"""
        mapping = {}
        
        patterns = {
            'id': [r'^id$', r'n°', r'num[ée]ro', r'^#$', r'r[èe]gle.*n°'],
            'description': [r'description', r'r[èe]gle', r'instruction', r'contr[ôo]le', 
                          r'v[ée]rification', r'libell[ée]', r'rule'],
            'colonne_cible': [r'colonne', r'question', r'variable', r'champ', r'field', 
                            r'cible', r'target'],
            'condition': [r'condition', r'si\b', r'when', r'lorsque', r'crit[èe]re'],
            'valeur_attendue': [r'valeur.*attendu', r'expected', r'doit.*[êe]tre', 
                              r'r[ée]ponse.*correct', r'valid'],
            'severite': [r's[ée]v[ée]rit[ée]', r'priorit[ée]', r'importance', r'gravit[ée]', 
                       r'criticit[ée]', r'severity'],
            'type': [r'^type$', r'cat[ée]gorie', r'category', r'nature'],
            'action': [r'action', r'correction', r'que.*faire', r'remediation'],
            'commentaire': [r'commentaire', r'note', r'remarque', r'comment'],
        }
        
        for col in columns:
            col_str = str(col).lower().strip()
            for field, regex_list in patterns.items():
                if any(re.search(p, col_str) for p in regex_list):
                    if field not in mapping.values():
                        mapping[col] = field
                        break
        
        return mapping
    
    def _row_to_rule(self, row, col_mapping: Dict, idx: int) -> Optional[Dict]:
        """Convertit une ligne en règle structurée"""
        rule = {
            "id": f"R{idx + 1}",
            "source_row": idx + 1,
            "description": "",
            "colonne_cible": "",
            "condition": "",
            "valeur_attendue": "",
            "severite": "moderee",
            "type": "custom",
            "action": "",
            "commentaire": "",
            "raw_data": {}
        }
        
        # Remplir depuis le mapping détecté
        for original_col, mapped_field in col_mapping.items():
            value = row[original_col]
            if pd.notna(value):
                rule[mapped_field] = str(value).strip()
        
        # Garder toutes les données brutes pour le contexte
        for col in row.index:
            value = row[col]
            if pd.notna(value):
                rule["raw_data"][str(col)] = str(value).strip()
        
        # Normaliser la sévérité
        rule["severite"] = self._normalize_severity(rule["severite"])
        
        # Normaliser le type
        rule["type"] = self._normalize_type(rule["type"], rule["description"])
        
        # Filtrer les règles vides
        if not rule["description"] and not rule["condition"] and not rule["raw_data"]:
            return None
        
        # Si pas de description mais des données brutes, construire une description
        if not rule["description"] and rule["raw_data"]:
            rule["description"] = " | ".join(f"{k}: {v}" for k, v in rule["raw_data"].items())
        
        return rule
    
    def _normalize_severity(self, severity: str) -> str:
        """Normalise la sévérité en critique/moderee/mineure"""
        sev_lower = severity.lower().strip()
        
        if not sev_lower:
            return "moderee"
        
        # Critique
        if any(kw in sev_lower for kw in ['critique', 'critical', 'élevé', 'eleve', 
                                            'haut', 'high', 'majeur', '1', 'bloquant']):
            return "critique"
        
        # Mineure
        if any(kw in sev_lower for kw in ['mineur', 'minor', 'faible', 'low', 'bas', 
                                           '3', 'info', 'warning']):
            return "mineure"
        
        # Modérée par défaut
        return "moderee"
    
    def _normalize_type(self, type_str: str, description: str) -> str:
        """Normalise le type de règle"""
        combined = (type_str + " " + description).lower()
        
        if any(kw in combined for kw in ['skip', 'branch', 'logique', 'logic', 'conditionnel']):
            return "skip_logic"
        if any(kw in combined for kw in ['outlier', 'aberrant', 'plage', 'min', 'max', 'range']):
            return "outlier"
        if any(kw in combined for kw in ['commentaire', 'comment', 'justif']):
            return "commentaire"
        if any(kw in combined for kw in ['photo', 'image', 'pièce']):
            return "photo"
        if any(kw in combined for kw in ['date', 'heure', 'time']):
            return "date"
        if any(kw in combined for kw in ['doublon', 'duplicate', 'unique']):
            return "doublon"
        if any(kw in combined for kw in ['obligatoire', 'mandatory', 'required', 'manquant']):
            return "obligatoire"
        if any(kw in combined for kw in ['coh[ée]rence', 'consist']):
            return "coherence"
        
        return "custom"
    
    def get_rules_summary(self) -> Dict:
        """Retourne un résumé des règles parsées"""
        if not self.parsed_rules:
            return {}
        
        by_severity = {}
        by_type = {}
        
        for rule in self.parsed_rules:
            sev = rule["severite"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            t = rule["type"]
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total": len(self.parsed_rules),
            "par_severite": by_severity,
            "par_type": by_type,
            "colonnes_concernees": list(set(r["colonne_cible"] for r in self.parsed_rules if r["colonne_cible"]))
        }
    
    def get_rules_as_prompt(self) -> str:
        """Formate les règles pour les inclure dans un prompt Claude"""
        if not self.parsed_rules:
            return "Aucune règle spécifique fournie."
        
        prompt_lines = ["RÈGLES DE VÉRIFICATION MÉTIER À APPLIQUER:\n"]
        
        for i, rule in enumerate(self.parsed_rules, 1):
            prompt_lines.append(f"\n--- Règle {rule['id']} ({rule['severite'].upper()}) ---")
            if rule["description"]:
                prompt_lines.append(f"Description: {rule['description']}")
            if rule["colonne_cible"]:
                prompt_lines.append(f"Colonne concernée: {rule['colonne_cible']}")
            if rule["condition"]:
                prompt_lines.append(f"Condition: {rule['condition']}")
            if rule["valeur_attendue"]:
                prompt_lines.append(f"Valeur attendue: {rule['valeur_attendue']}")
            if rule["action"]:
                prompt_lines.append(f"Action en cas d'erreur: {rule['action']}")
        
        return "\n".join(prompt_lines)
