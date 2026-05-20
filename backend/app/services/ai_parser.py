import json
from typing import List, Dict, Any, Optional

from openai import OpenAI

class AIConstraintParser:
    def __init__(
        self,
        model: Optional[str] = None,
        timeout_seconds: int = 60,
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
    ):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for AI features")
        if not self.model:
            raise ValueError("AI_MODEL is required for AI features")

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
                return self._normalize_constraints(parsed)
            if isinstance(parsed, dict) and isinstance(parsed.get("constraints"), list):
                return self._normalize_constraints(parsed["constraints"])
            if isinstance(parsed, dict):
                return self._normalize_constraints([parsed])
            raise ValueError("Expected a JSON array of constraints")
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return []

    def _parse_day_names(self, value: Any) -> List[str]:
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if not value:
            return []

        if isinstance(value, str):
            parts = [p.strip() for p in value.replace("and", ",").replace(";", ",").split(",") if p.strip()]
        elif isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.extend([p.strip() for p in item.replace("and", ",").replace(";", ",").split(",") if p.strip()])
        else:
            return []

        normalized = []
        for part in parts:
            lower = part.lower()
            for day in all_days:
                if lower == day.lower() or lower.startswith(day[:3].lower()):
                    normalized.append(day)
                    break
        return sorted(set(normalized), key=lambda d: all_days.index(d))

    def _normalize_constraints(self, constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        full_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        def parse_days(value: Any) -> List[str]:
            if isinstance(value, list):
                return self._parse_day_names([str(v) for v in value if v is not None])
            return self._parse_day_names(str(value))

        for constraint in constraints:
            if not isinstance(constraint, dict):
                continue

            c_type = str(constraint.get("type", "")).lower()
            if c_type in {"faculty_availability", "availability", "faculty availability", "faculty_unavailability", "unavailable", "not available", "not_available"}:
                faculty_name = constraint.get("faculty_name") or constraint.get("faculty") or constraint.get("name")
                available_days = constraint.get("available_days") or constraint.get("days") or constraint.get("available")
                unavailable_days = constraint.get("unavailable_days") or constraint.get("unavailable") or constraint.get("not_available")

                if c_type in {"faculty_unavailability", "unavailable", "not available", "not_available"} and not available_days:
                    unavailable_days = parse_days(unavailable_days)
                    available_days = [day for day in full_days if day not in unavailable_days]

                if not isinstance(available_days, list):
                    available_days = parse_days(available_days)

                if faculty_name and available_days:
                    normalized.append({
                        "type": "faculty_availability",
                        "faculty_name": faculty_name,
                        "available_days": available_days,
                    })
                continue

            if c_type in {"consecutive_periods", "continuity", "continuous", "consecutive"}:
                subject_type = constraint.get("subject_type") or constraint.get("subject") or "lab"
                normalized.append({
                    "type": "consecutive_periods",
                    "subject_type": str(subject_type).lower(),
                })
                continue

            normalized.append(constraint)

        return normalized

    def _generate(self, prompt: str) -> str:
        client = OpenAI(api_key=self.api_key, api_base=self.api_base)
        try:
            response = client.responses.create(model=self.model, input=prompt)
        except Exception as e:
            raise RuntimeError(f"OpenAI/Grok request failed: {e}") from e

        if hasattr(response, "to_dict"):
            data = response.to_dict()
        elif hasattr(response, "model_dump"):
            data = response.model_dump()
        else:
            data = dict(response)

        clean_text = self._extract_text_from_response(data)
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:].strip()
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:].strip()
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3].strip()

        if not clean_text:
            raise RuntimeError(f"{self.provider.capitalize()} returned an empty response")
        return clean_text

    def _extract_text_from_response(self, data: Dict[str, Any]) -> str:
        if isinstance(data.get("response"), str):
            return data["response"].strip()
        if isinstance(data.get("output_text"), str):
            return data["output_text"].strip()

        output = data.get("output")
        if isinstance(output, list):
            parts = []
            for item in output:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    content = item.get("content")
                    if isinstance(content, str):
                        parts.append(content)
                    elif isinstance(content, list):
                        for c in content:
                            if isinstance(c, str):
                                parts.append(c)
                            elif isinstance(c, dict) and isinstance(c.get("text"), str):
                                parts.append(c["text"])
            return "\n".join(parts).strip()

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            message = first.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        return json.dumps(data)
