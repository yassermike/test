"""
Validateur local - règles automatiques sans appel IA
Pour gagner du temps et réduire les coûts d'API
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime


class LocalValidator:
    """Validateur basé sur des règles locales (sans IA)"""
    
    def __init__(
        self,
        check_skip_logic: bool = True,
        check_outliers: bool = True,
        check_comments: bool = True,
        check_duplicates: bool = True,
        check_dates: bool = True
    ):
        self.check_skip_logic = check_skip_logic
        self.check_outliers = check_outliers
        self.check_comments = check_comments
        self.check_duplicates = check_duplicates
        self.check_dates = check_dates
        self.errors: List[Dict] = []
    
    def validate(self, df: pd.DataFrame) -> List[Dict]:
        """Lance toutes les validations sélectionnées"""
        self.errors = []
        
        if self.check_duplicates:
            self._check_duplicates(df)
        
        if self.check_outliers:
            self._check_outliers(df)
        
        if self.check_comments:
            self._check_comments(df)
        
        if self.check_dates:
            self._check_dates(df)
        
        if self.check_skip_logic:
            self._check_basic_skip_logic(df)
        
        # Vérifications supplémentaires
        self._check_missing_values(df)
        self._check_suspicious_patterns(df)
        
        return self.errors
    
    def _add_error(
        self,
        ligne: int,
        colonne: str,
        valeur: any,
        type_erreur: str,
        description: str,
        severite: str = "moderee",
        correction: str = ""
    ):
        """Ajoute une erreur à la liste"""
        self.errors.append({
            "ligne": ligne,
            "colonne": colonne,
            "valeur_actuelle": str(valeur),
            "type_erreur": type_erreur,
            "description": description,
            "correction_suggeree": correction,
            "severite": severite,
            "regle_violee": f"local_{type_erreur}"
        })
    
    def _check_duplicates(self, df: pd.DataFrame):
        """Détecte les lignes en double"""
        duplicates = df[df.duplicated(keep=False)]
        for idx in duplicates.index:
            self._add_error(
                ligne=idx + 1,
                colonne="(toute la ligne)",
                valeur="ligne dupliquée",
                type_erreur="doublon",
                description="Cette ligne est identique à une autre - possibilité de copier-coller frauduleux",
                severite="critique",
                correction="Vérifier l'authenticité, supprimer si confirmé"
            )
    
    def _check_outliers(self, df: pd.DataFrame):
        """Détecte les valeurs aberrantes sur colonnes numériques (méthode IQR)"""
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            data = df[col].dropna()
            if len(data) < 10:
                continue
            
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR == 0:
                # Si toutes les valeurs sont identiques, c'est suspect
                if data.nunique() == 1:
                    self._add_error(
                        ligne=0,
                        colonne=col,
                        valeur=data.iloc[0],
                        type_erreur="pattern_suspect",
                        description=f"Toutes les valeurs de la colonne '{col}' sont identiques ({data.iloc[0]}) - pattern de fraude possible",
                        severite="critique"
                    )
                continue
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            for idx, row in outliers.iterrows():
                val = row[col]
                self._add_error(
                    ligne=idx + 1,
                    colonne=col,
                    valeur=val,
                    type_erreur="outlier",
                    description=f"Valeur aberrante ({val}). Plage normale: [{lower_bound:.1f}, {upper_bound:.1f}]",
                    severite="moderee",
                    correction=f"Vérifier - médiane: {data.median():.1f}"
                )
    
    def _check_comments(self, df: pd.DataFrame):
        """Vérifie que les commentaires sont présents quand les notes sont faibles ou élevées"""
        # Identifier colonnes de notes et de commentaires
        score_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['note', 'score', 'rating', 'évaluation'])]
        comment_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['commentaire', 'comment', 'observation', 'remarque', 'justification'])]
        
        if not score_cols or not comment_cols:
            return
        
        for score_col in score_cols:
            # Essayer de trouver le commentaire correspondant
            score_idx = list(df.columns).index(score_col)
            
            # Chercher le commentaire adjacent
            related_comment = None
            for comment_col in comment_cols:
                comment_idx = list(df.columns).index(comment_col)
                if abs(comment_idx - score_idx) <= 2:
                    related_comment = comment_col
                    break
            
            if related_comment is None and comment_cols:
                related_comment = comment_cols[0]
            
            if related_comment:
                for idx, row in df.iterrows():
                    score = row[score_col]
                    comment = row[related_comment]
                    
                    if pd.isna(score):
                        continue
                    
                    try:
                        score_num = float(score)
                        # Note basse sans commentaire = problème
                        if score_num <= 5:
                            if pd.isna(comment) or str(comment).strip() == "":
                                self._add_error(
                                    ligne=idx + 1,
                                    colonne=related_comment,
                                    valeur="(vide)",
                                    type_erreur="commentaire_manquant",
                                    description=f"Note faible ({score_num}/10) dans '{score_col}' mais commentaire vide. Justification requise.",
                                    severite="critique",
                                    correction="Recontacter l'enquêteur pour obtenir la justification"
                                )
                            elif len(str(comment).strip()) < 10:
                                self._add_error(
                                    ligne=idx + 1,
                                    colonne=related_comment,
                                    valeur=str(comment),
                                    type_erreur="commentaire_insuffisant",
                                    description=f"Note faible ({score_num}/10) mais commentaire trop court ({len(str(comment))} car.)",
                                    severite="moderee",
                                    correction="Demander un commentaire plus détaillé"
                                )
                    except (ValueError, TypeError):
                        pass
    
    def _check_dates(self, df: pd.DataFrame):
        """Vérifie la validité des dates"""
        date_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['date', 'jour'])]
        
        for col in date_cols:
            for idx, val in df[col].items():
                if pd.isna(val):
                    continue
                
                try:
                    date_val = pd.to_datetime(val, errors='coerce')
                    
                    if pd.isna(date_val):
                        self._add_error(
                            ligne=idx + 1,
                            colonne=col,
                            valeur=val,
                            type_erreur="date_invalide",
                            description=f"Format de date non reconnu: '{val}'",
                            severite="moderee"
                        )
                        continue
                    
                    # Date future
                    if date_val > pd.Timestamp.now():
                        self._add_error(
                            ligne=idx + 1,
                            colonne=col,
                            valeur=val,
                            type_erreur="date_invalide",
                            description=f"Date dans le futur: {date_val.date()}",
                            severite="critique"
                        )
                    
                    # Date trop ancienne (> 2 ans)
                    if date_val < pd.Timestamp.now() - pd.Timedelta(days=730):
                        self._add_error(
                            ligne=idx + 1,
                            colonne=col,
                            valeur=val,
                            type_erreur="date_suspecte",
                            description=f"Date très ancienne: {date_val.date()}",
                            severite="mineure"
                        )
                
                except Exception:
                    pass
    
    def _check_missing_values(self, df: pd.DataFrame):
        """Vérifie les colonnes critiques manquantes"""
        # Identifier colonnes "importantes" (peu de valeurs manquantes ailleurs)
        for col in df.columns:
            missing_rate = df[col].isnull().sum() / len(df)
            
            # Si une colonne a < 5% de manquants, les rares manquants sont suspects
            if 0 < missing_rate < 0.05:
                missing_rows = df[df[col].isnull()].index
                for idx in missing_rows:
                    self._add_error(
                        ligne=idx + 1,
                        colonne=col,
                        valeur="(vide)",
                        type_erreur="valeur_manquante",
                        description=f"Valeur manquante dans une colonne habituellement remplie ({missing_rate*100:.1f}% manquants au global)",
                        severite="moderee",
                        correction="Recontacter l'enquêteur"
                    )
    
    def _check_basic_skip_logic(self, df: pd.DataFrame):
        """Détection basique de skip logic violée"""
        # Cherche des paires question/sous-question
        for col in df.columns:
            col_lower = col.lower()
            
            # Pattern: si "vendeur présent = Non", alors les questions suivantes devraient être vides
            if 'accueil' in col_lower or 'présent' in col_lower or 'reçu' in col_lower:
                for idx, val in df[col].items():
                    if pd.isna(val):
                        continue
                    
                    val_str = str(val).lower().strip()
                    if val_str in ['non', 'no', '0', 'false', 'pas']:
                        # Vérifier que les colonnes suivantes (potentielles sous-questions) sont vides
                        col_idx = list(df.columns).index(col)
                        if col_idx + 1 < len(df.columns):
                            next_col = df.columns[col_idx + 1]
                            next_val = df.iloc[idx][next_col]
                            
                            if not pd.isna(next_val) and str(next_val).strip() != "":
                                # Vérifier si la colonne suivante est dépendante (basée sur le nom)
                                if any(kw in next_col.lower() for kw in ['temps', 'durée', 'qualité', 'comment']):
                                    self._add_error(
                                        ligne=idx + 1,
                                        colonne=next_col,
                                        valeur=str(next_val),
                                        type_erreur="skip_logic",
                                        description=f"'{col}' = '{val}' devrait skipper la question '{next_col}', mais elle est remplie",
                                        severite="critique",
                                        correction="Vider la cellule ou corriger la réponse précédente"
                                    )
    
    def _check_suspicious_patterns(self, df: pd.DataFrame):
        """Détecte les patterns suspects de fraude"""
        # 1. Lignes où toutes les notes sont identiques (réponse "fast-clicker")
        score_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['note', 'score', 'rating'])]
        
        if len(score_cols) >= 3:
            for idx, row in df.iterrows():
                scores = row[score_cols].dropna()
                if len(scores) >= 3 and scores.nunique() == 1:
                    self._add_error(
                        ligne=idx + 1,
                        colonne="(toutes notes)",
                        valeur=f"toutes = {scores.iloc[0]}",
                        type_erreur="fraude_potentielle",
                        description=f"Toutes les notes sont identiques ({scores.iloc[0]}) - possible 'fast-clicking' ou fraude",
                        severite="critique",
                        correction="Vérifier la cohérence avec les commentaires et photos"
                    )
        
        # 2. Commentaires trop courts ou identiques
        comment_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['commentaire', 'comment', 'observation'])]
        
        for col in comment_cols:
            comments = df[col].dropna().astype(str)
            
            # Commentaires copiés (apparaissent plus de 3 fois)
            value_counts = comments.value_counts()
            duplicated_comments = value_counts[value_counts >= 3]
            
            for comment_text, count in duplicated_comments.items():
                if len(comment_text.strip()) > 5:  # ignorer les petits "OK", "ras"
                    rows_with_dup = df[df[col] == comment_text].index
                    for idx in rows_with_dup:
                        self._add_error(
                            ligne=idx + 1,
                            colonne=col,
                            valeur=comment_text[:50],
                            type_erreur="commentaire_duplique",
                            description=f"Commentaire identique répété {count} fois - possible copier-coller frauduleux",
                            severite="moderee"
                        )
