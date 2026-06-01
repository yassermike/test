"""
Module de lecture et préparation des fichiers Excel
"""
import pandas as pd
from typing import Dict, List, Optional


class ExcelReader:
    """Classe pour lire et analyser les fichiers Excel d'études client mystère"""
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path
        self.df: Optional[pd.DataFrame] = None
        self.questions: List[str] = []
        
        if file_path:
            self.load()
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame):
        """Créer un ExcelReader depuis un DataFrame déjà chargé"""
        instance = cls()
        instance.df = df
        instance.questions = list(df.columns)
        return instance
    
    def load(self) -> pd.DataFrame:
        """Charge le fichier Excel ou CSV"""
        if self.file_path.endswith('.csv'):
            self.df = pd.read_csv(self.file_path)
        else:
            self.df = pd.read_excel(self.file_path, sheet_name=0)
        
        self.questions = list(self.df.columns)
        return self.df
    
    def get_summary(self) -> Dict:
        """Retourne un résumé détaillé du fichier"""
        if self.df is None:
            return {}
        
        return {
            "nb_lignes": len(self.df),
            "nb_questions": len(self.questions),
            "questions": self.questions,
            "valeurs_manquantes": self.df.isnull().sum().to_dict(),
            "doublons": int(self.df.duplicated().sum()),
            "types": {col: str(dtype) for col, dtype in self.df.dtypes.items()}
        }
    
    def get_sample(self, n: int = 5) -> List[Dict]:
        """Retourne un échantillon des données"""
        if self.df is None:
            return []
        return self.df.head(n).to_dict('records')
    
    def detect_column_types(self) -> Dict[str, str]:
        """Détecte automatiquement le type sémantique de chaque colonne"""
        types = {}
        if self.df is None:
            return types
        
        for col in self.df.columns:
            col_lower = col.lower()
            
            # Détection par mot-clé dans le nom
            if any(kw in col_lower for kw in ['date', 'jour']):
                types[col] = 'date'
            elif any(kw in col_lower for kw in ['heure', 'time', 'horaire']):
                types[col] = 'time'
            elif any(kw in col_lower for kw in ['note', 'score', 'rating', 'évaluation']):
                types[col] = 'score'
            elif any(kw in col_lower for kw in ['commentaire', 'comment', 'observation', 'remarque']):
                types[col] = 'comment'
            elif any(kw in col_lower for kw in ['photo', 'image', 'pièce jointe']):
                types[col] = 'photo'
            elif any(kw in col_lower for kw in ['nom', 'magasin', 'point de vente', 'enseigne']):
                types[col] = 'identifier'
            elif any(kw in col_lower for kw in ['durée', 'duration', 'temps']):
                types[col] = 'duration'
            elif self.df[col].dtype in ['int64', 'float64']:
                # Détection numérique : si peu de valeurs uniques = note, sinon mesure
                unique_vals = self.df[col].nunique()
                if unique_vals <= 10:
                    types[col] = 'categorical_numeric'
                else:
                    types[col] = 'numeric'
            else:
                unique_vals = self.df[col].nunique()
                if unique_vals <= 5:
                    types[col] = 'categorical'
                else:
                    types[col] = 'text'
        
        return types
    
    def get_basic_stats(self) -> Dict:
        """Statistiques de base sur les colonnes numériques"""
        if self.df is None:
            return {}
        
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        stats = {}
        
        for col in numeric_cols:
            stats[col] = {
                "min": float(self.df[col].min()) if not pd.isna(self.df[col].min()) else None,
                "max": float(self.df[col].max()) if not pd.isna(self.df[col].max()) else None,
                "mean": float(self.df[col].mean()) if not pd.isna(self.df[col].mean()) else None,
                "std": float(self.df[col].std()) if not pd.isna(self.df[col].std()) else None,
            }
        
        return stats
