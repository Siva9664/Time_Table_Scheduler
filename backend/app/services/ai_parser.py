import json
from typing import List, Dict, Any
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

class AIConstraintParser:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 60):
        if not base_url:
            raise ValueError("Ollama base URL is required for AI features")
        if not model:
            raise ValueError("Ollama model is required for AI features")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def parse_constraints(self, text: str) -> List[Dict[str, Any]]:
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
            clean_text = self._generate(prompt)
            parsed = json.loads(clean_text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and isinstance(parsed.get("constraints"), list):
                return parsed["constraints"]
            raise ValueError("Expected a JSON array of constraints")
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return [] # Return empty list on failure, don't crash the scheduler

    def _generate(self, prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0
            }
        }).encode("utf-8")

        req = urlrequest.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlrequest.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error {e.code}: {e.reason}") from e
        except URLError as e:
            raise RuntimeError(f"Could not connect to Ollama at {self.base_url}: {e.reason}") from e

        clean_text = data.get("response", "").strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:].strip()
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:].strip()
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3].strip()

        if not clean_text:
            raise RuntimeError("Ollama returned an empty response")
        return clean_text
