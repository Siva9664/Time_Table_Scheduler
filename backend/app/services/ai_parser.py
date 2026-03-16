try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
import json
from typing import List, Dict, Any, Optional

class AIConstraintParser:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key is required for AI features")
        if not GENAI_AVAILABLE:
            print("WARNING: google-generativeai is not installed. AI features disabled.")
            self.model = None
            return
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def parse_constraints(self, text: str) -> List[Dict[str, Any]]:
        if not GENAI_AVAILABLE or not getattr(self, 'model', None):
            print("AI parsing disabled - missing google-generativeai")
            return []
        """
        Parses natural language text into structured JSON constraints.
        Expected Output Format:
        [
            {"type": "faculty_availability", "faculty_name": "Shiva", "available_days": ["Monday", "Tuesday"]},
            {"type": "consecutive_periods", "subject_type": "lab"}
        ]
        """
        prompt = f"""
        You are an AI Timetable Assistant. Convert the following natural language constraints into a structured JSON array.
        
        Input Text: "{text}"
        
        Supported Constraint Types:
        1. Faculty Availability:
           - type: "faculty_availability"
           - faculty_name: string (extract exact name)
           - available_days: list of strings (e.g. ["Monday", "Wednesday"])
        
        2. Consecutive Periods (for labs/sessions):
           - type: "consecutive_periods"
           - subject_type: string (e.g. "lab", "theory") - usually "lab" for continuous sessions.
        
        Rules:
        - Return ONLY valid JSON. No markdown formatting.
        - If input mentions "continuous" or "spread out", map to "consecutive_periods".
        - Map day names to full English names (Monday, Tuesday, etc.).
        
        JSON Output:
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Clean response if it contains markdown code blocks
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text)
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return [] # Return empty list on failure, don't crash the scheduler
