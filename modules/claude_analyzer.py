"""
Module d'analyse IA avec Mistral AI via HTTP direct
"""
import os
import json
import re
from typing import List, Dict
import httpx
from dotenv import load_dotenv

load_dotenv()

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


class ClaudeAnalyzer:

    SYSTEM_PROMPT_STRUCTURE = """Tu es un expert senior en études client mystère et satisfaction client.
Tu maîtrises les visites mystère, études de satisfaction, skip logic, détection de fraude.
IMPORTANT: Réponds TOUJOURS en JSON valide, sans texte autour."""

    SYSTEM_PROMPT_VALIDATION = """Tu es un auditeur qualité d'études client mystère.
Détecte: incohérences logiques, skip logic non respectée, valeurs aberrantes, commentaires manquants, doublons, fraude.
Réponds en JSON strict, sans markdown."""

    def __init__(self, model: str = "mistral-small-latest"):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY non définie dans .env")
        self.model_name = model

    def _call(self, system_prompt: str, user_message: str, max_tokens: int = 4000) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        response = httpx.post(MISTRAL_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _truncate(self, data: List[Dict], max_rows: int = 3, max_val_len: int = 100) -> List[Dict]:
        result = []
        for row in data[:max_rows]:
            truncated = {}
            for k, v in row.items():
                s = str(v)
                truncated[k] = s[:max_val_len] + "…" if len(s) > max_val_len else s
            result.append(truncated)
        return result

    def analyze_structure(self, questions, sample_data, study_type="Visite Mystère", custom_prompt="") -> str:
        user_message = f"""Analyse cette étude de type **{study_type}**.

QUESTIONS ({len(questions)} colonnes):
{json.dumps(questions, ensure_ascii=False, indent=2)}

ÉCHANTILLON (3 lignes):
{json.dumps(self._truncate(sample_data), ensure_ascii=False, indent=2, default=str)}

INSTRUCTIONS: {custom_prompt if custom_prompt else "Aucune."}

Retourne UNIQUEMENT ce JSON (sans markdown):
{{
  "type_etude": "string",
  "secteur": "string",
  "questions_critiques": [],
  "skip_logic": [{{"si_colonne": "X", "vaut": "val", "alors_colonnes": ["Y"], "doivent_etre": "remplies|vides"}}],
  "questions_score": [],
  "questions_commentaire": [],
  "questions_photo": [],
  "regles": [
    {{"id": "R1", "description": "...", "type": "skip_logic|outlier|commentaire|coherence", "colonnes_concernees": [], "condition": "...", "severite": "critique|moderee|mineure"}}
  ],
  "questions_suspectes_fraude": []
}}"""
        return self._call(self.SYSTEM_PROMPT_STRUCTURE, user_message, max_tokens=4000)

    def analyze_with_business_rules(self, questionnaire_columns, sample_data, business_rules, study_type="Visite Mystère", custom_prompt="") -> str:
        rules_text = ""
        for rule in business_rules:
            rules_text += f"\n• {rule['id']} ({rule['severite']}): {rule['description']}"
            if rule.get('colonne_cible'):
                rules_text += f" → {rule['colonne_cible']}"

        user_message = f"""Analyse étude **{study_type}** avec règles métier.

QUESTIONS ({len(questionnaire_columns)} colonnes):
{json.dumps(questionnaire_columns, ensure_ascii=False, indent=2)}

ÉCHANTILLON:
{json.dumps(self._truncate(sample_data), ensure_ascii=False, indent=2, default=str)}

RÈGLES ({len(business_rules)}):
{rules_text}

INSTRUCTIONS: {custom_prompt if custom_prompt else "Aucune."}

Retourne UNIQUEMENT ce JSON:
{{
  "type_etude": "string",
  "secteur": "string",
  "regles_metier_mappees": [{{"id_regle": "R1", "colonne_questionnaire": "...", "interpretation": "..."}}],
  "regles_supplementaires": [{{"id": "AUTO1", "description": "...", "type": "coherence", "severite": "moderee"}}],
  "questions_critiques": [],
  "skip_logic_detectees": []
}}"""
        return self._call(self.SYSTEM_PROMPT_STRUCTURE, user_message, max_tokens=5000)

    def validate_batch(self, rows, rules, start_row=1, custom_prompt="") -> List[Dict]:
        rules_text = json.dumps(rules, ensure_ascii=False, indent=2) if rules else "Expertise générale"
        user_message = f"""Vérifie ces réponses d'enquêteurs.

RÈGLES: {rules_text}
INSTRUCTIONS: {custom_prompt if custom_prompt else "Vérifie cohérence générale."}

DONNÉES ({len(rows)} lignes à partir de {start_row}):
{json.dumps(rows, ensure_ascii=False, indent=2, default=str)}

Retourne UNIQUEMENT ce JSON:
{{
  "erreurs": [
    {{
      "ligne": <numéro>,
      "colonne": "<nom>",
      "valeur_actuelle": "<val>",
      "type_erreur": "skip_logic|outlier|coherence|commentaire_manquant|fraude|autre",
      "description": "<explication>",
      "correction_suggeree": "<recommandation>",
      "severite": "critique|moderee|mineure",
      "regle_violee": "<ID>"
    }}
  ]
}}
Si aucune erreur: {{"erreurs": []}}"""
        text = self._call(self.SYSTEM_PROMPT_VALIDATION, user_message, max_tokens=8000)
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group()).get("erreurs", [])
            return []
        except json.JSONDecodeError:
            return []

    def suggest_correction(self, row, error) -> str:
        user_message = f"""Données: {json.dumps(row, ensure_ascii=False, default=str)}
Erreur: {json.dumps(error, ensure_ascii=False)}
Retourne JSON: {{"correction": "...", "justification": "...", "action_recommandee": "corriger|supprimer_ligne|recontacter_enqueteur"}}"""
        return self._call(self.SYSTEM_PROMPT_VALIDATION, user_message, max_tokens=1000)
