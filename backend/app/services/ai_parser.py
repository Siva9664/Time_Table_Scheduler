import json
from typing import List, Dict, Any, Optional


class AIConstraintParser:
    """
    Parses natural language timetable constraints into structured JSON
    using an OpenAI-compatible chat completions API.

    Improvements over v1:
    - Uses the correct chat.completions.create() API (not responses.create)
    - Accepts real DB context (faculty names, subject names) to ground the AI
    - Rich system prompt with few-shot examples for reliable JSON output
    - Supports 7 constraint types, not just 2
    - Fixed self.provider crash bug
    """

    SUPPORTED_TYPES = [
        "faculty_availability",
        "faculty_unavailability",
        "consecutive_periods",
        "subject_max_per_day",
        "preferred_time_slot",
        "avoid_time_slot",
        "class_gap",
    ]

    def __init__(
        self,
        model: Optional[str] = None,
        timeout_seconds: int = 60,
        api_key: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        context: Optional[Dict[str, Any]] = None,
    ):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.context = context or {}   # {"faculty_names": [...], "subject_names": [...], "class_names": [...]}

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for AI features")
        if not self.model:
            raise ValueError("AI_MODEL is required for AI features")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def parse_constraints(self, text: str) -> List[Dict[str, Any]]:
        """
        Converts natural language constraint text into a list of structured
        constraint dicts that the TimetableScheduler can understand.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = f'Convert this scheduling request into JSON constraints:\n\n"{text}"'

        try:
            raw = self._chat(system_prompt, user_prompt)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return self._normalize_constraints(parsed)
            if isinstance(parsed, dict) and isinstance(parsed.get("constraints"), list):
                return self._normalize_constraints(parsed["constraints"])
            if isinstance(parsed, dict):
                return self._normalize_constraints([parsed])
            raise ValueError("Expected a JSON array of constraints")
        except json.JSONDecodeError as e:
            print(f"AI Parse Error (invalid JSON): {e}\nRaw response: {raw!r}")
            return []
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt building
    # ─────────────────────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        faculty_list = ", ".join(self.context.get("faculty_names", [])) or "not provided"
        subject_list = ", ".join(self.context.get("subject_names", [])) or "not provided"
        class_list   = ", ".join(self.context.get("class_names",   [])) or "not provided"

        return f"""You are a timetable scheduling assistant. Your only job is to convert natural language scheduling requests into a JSON array of structured constraint objects. Return ONLY valid JSON — no markdown, no explanation.

## Available Data Context
- Faculty names in the system: {faculty_list}
- Subject names in the system: {subject_list}
- Class/Section names in the system: {class_list}

## Supported Constraint Types

### 1. faculty_availability
Faculty is ONLY available on these days.
```json
{{"type": "faculty_availability", "faculty_name": "Dr. Smith", "available_days": ["Monday", "Wednesday", "Friday"]}}
```

### 2. faculty_unavailability
Faculty is NOT available on these days.
```json
{{"type": "faculty_unavailability", "faculty_name": "Prof. Raj", "unavailable_days": ["Friday"]}}
```

### 3. consecutive_periods
A subject type must be scheduled in back-to-back periods on the same day.
```json
{{"type": "consecutive_periods", "subject_type": "lab"}}
```

### 4. subject_max_per_day
A subject should not appear more than N times in a single day.
```json
{{"type": "subject_max_per_day", "subject_name": "Mathematics", "max_per_day": 1}}
```

### 5. preferred_time_slot
A subject/class prefers morning or afternoon slots.
```json
{{"type": "preferred_time_slot", "target": "Physics", "target_type": "subject", "preference": "morning"}}
```
`preference` must be one of: "morning", "afternoon", "first_half", "second_half"

### 6. avoid_time_slot
Block a class or subject from specific period numbers.
```json
{{"type": "avoid_time_slot", "target": "CSE-A", "target_type": "class", "periods": [7, 8]}}
```

### 7. class_gap
A class must have at least N free periods between two sessions.
```json
{{"type": "class_gap", "class_name": "CSE-A", "min_gap": 1}}
```

## Rules
- Always match names exactly to the available data context above (use the closest match).
- Map all day names to full English: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.
- If "not available on X" → use faculty_unavailability.
- If "only available on X" → use faculty_availability.
- If "continuous" or "back to back" → use consecutive_periods.
- If "not more than once a day" → use subject_max_per_day with max_per_day: 1.
- Return ONLY a JSON array. No other text.

## Few-Shot Examples

Input: "Dr. Raj cannot teach on Fridays and Saturdays"
Output: [{{"type": "faculty_unavailability", "faculty_name": "Dr. Raj", "unavailable_days": ["Friday", "Saturday"]}}]

Input: "All lab sessions must be consecutive. Physics should be in the morning."
Output: [{{"type": "consecutive_periods", "subject_type": "lab"}}, {{"type": "preferred_time_slot", "target": "Physics", "target_type": "subject", "preference": "morning"}}]

Input: "Prof. Meena is available only on Monday, Tuesday and Thursday. Maths should not appear more than once a day."
Output: [{{"type": "faculty_availability", "faculty_name": "Prof. Meena", "available_days": ["Monday", "Tuesday", "Thursday"]}}, {{"type": "subject_max_per_day", "subject_name": "Maths", "max_per_day": 1}}]
"""

    # ─────────────────────────────────────────────────────────────────────────
    # OpenAI chat call (correct API)
    # ─────────────────────────────────────────────────────────────────────────

    def _chat(self, system: str, user: str) -> str:
        from openai import OpenAI
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=self.timeout_seconds,
        )
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0,          # deterministic output
                response_format={"type": "json_object"} if self._supports_json_mode() else None,
            )
        except Exception as e:
            raise RuntimeError(f"AI API request failed: {e}") from e

        raw = response.choices[0].message.content or ""
        return self._strip_markdown(raw)

    def _supports_json_mode(self) -> bool:
        """Only certain models support response_format=json_object."""
        supported = {"gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o-mini"}
        return any(s in (self.model or "").lower() for s in supported)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove ```json ... ``` fences if present."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:].strip()
        elif text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        return text

    # ─────────────────────────────────────────────────────────────────────────
    # Normalisation
    # ─────────────────────────────────────────────────────────────────────────

    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def _parse_day_names(self, value: Any) -> List[str]:
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
            for day in self.ALL_DAYS:
                if lower == day.lower() or lower.startswith(day[:3].lower()):
                    normalized.append(day)
                    break
        return sorted(set(normalized), key=lambda d: self.ALL_DAYS.index(d))

    def _normalize_constraints(self, constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []

        for c in constraints:
            if not isinstance(c, dict):
                continue

            c_type = str(c.get("type", "")).lower().replace(" ", "_")

            # ── faculty_availability ─────────────────────────────────────────
            if c_type in {"faculty_availability", "availability"}:
                name = c.get("faculty_name") or c.get("faculty") or c.get("name")
                days = c.get("available_days") or c.get("days") or c.get("available") or []
                days = self._parse_day_names(days)
                if name and days:
                    normalized.append({"type": "faculty_availability", "faculty_name": str(name), "available_days": days})

            # ── faculty_unavailability ───────────────────────────────────────
            elif c_type in {"faculty_unavailability", "unavailability", "unavailable", "not_available", "not available"}:
                name = c.get("faculty_name") or c.get("faculty") or c.get("name")
                unavail = c.get("unavailable_days") or c.get("unavailable") or c.get("not_available") or c.get("days") or []
                unavail = self._parse_day_names(unavail)
                avail = [d for d in self.ALL_DAYS if d not in unavail]
                if name and unavail:
                    normalized.append({"type": "faculty_availability", "faculty_name": str(name), "available_days": avail})

            # ── consecutive_periods ──────────────────────────────────────────
            elif c_type in {"consecutive_periods", "consecutive", "continuous", "continuity"}:
                subject_type = c.get("subject_type") or c.get("subject") or "lab"
                normalized.append({"type": "consecutive_periods", "subject_type": str(subject_type).lower()})

            # ── subject_max_per_day ──────────────────────────────────────────
            elif c_type in {"subject_max_per_day", "max_per_day", "daily_limit"}:
                subject_name = c.get("subject_name") or c.get("subject") or ""
                max_pd = c.get("max_per_day") or c.get("max") or 1
                try:
                    max_pd = int(max_pd)
                except (TypeError, ValueError):
                    max_pd = 1
                if subject_name:
                    normalized.append({"type": "subject_max_per_day", "subject_name": str(subject_name), "max_per_day": max_pd})

            # ── preferred_time_slot ──────────────────────────────────────────
            elif c_type in {"preferred_time_slot", "preferred_slot", "time_preference"}:
                target = c.get("target") or c.get("subject_name") or c.get("class_name") or ""
                target_type = c.get("target_type") or ("class" if c.get("class_name") else "subject")
                pref = str(c.get("preference") or c.get("slot") or "morning").lower()
                if pref not in {"morning", "afternoon", "first_half", "second_half"}:
                    pref = "morning"
                if target:
                    normalized.append({"type": "preferred_time_slot", "target": str(target), "target_type": str(target_type), "preference": pref})

            # ── avoid_time_slot ──────────────────────────────────────────────
            elif c_type in {"avoid_time_slot", "blocked_periods", "avoid_periods"}:
                target = c.get("target") or c.get("class_name") or c.get("subject_name") or ""
                target_type = c.get("target_type") or "class"
                periods = c.get("periods") or c.get("blocked_periods") or []
                if isinstance(periods, int):
                    periods = [periods]
                try:
                    periods = [int(p) for p in periods]
                except (TypeError, ValueError):
                    periods = []
                if target and periods:
                    normalized.append({"type": "avoid_time_slot", "target": str(target), "target_type": str(target_type), "periods": periods})

            # ── class_gap ────────────────────────────────────────────────────
            elif c_type in {"class_gap", "gap", "free_period"}:
                class_name = c.get("class_name") or c.get("class") or ""
                min_gap = c.get("min_gap") or c.get("gap") or 1
                try:
                    min_gap = int(min_gap)
                except (TypeError, ValueError):
                    min_gap = 1
                if class_name:
                    normalized.append({"type": "class_gap", "class_name": str(class_name), "min_gap": min_gap})

            # ── pass-through unknowns ────────────────────────────────────────
            else:
                normalized.append(c)

        return normalized
