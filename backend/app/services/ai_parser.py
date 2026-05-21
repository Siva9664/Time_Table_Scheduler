import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI


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
        "specific_time_slot",
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

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def parse_constraints(self, text: str) -> List[Dict[str, Any]]:
        """
        Converts natural language constraint text into a list of structured
        constraint dicts that the TimetableScheduler can understand.
        """
        if not self.api_key or not self.model:
            return self._parse_rule_based_constraints(text)

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text)

        try:
            raw = self._chat(system_prompt, user_prompt)
            constraints = self._extract_constraints(json.loads(raw))
            return self._merge_constraints(
                self._normalize_constraints(constraints),
                self._parse_rule_based_constraints(text),
            )
        except json.JSONDecodeError as e:
            print(f"AI Parse Error (invalid JSON): {e}\nRaw response: {raw!r}")
            return self._parse_rule_based_constraints(text)
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return self._parse_rule_based_constraints(text)

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt building
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(text: str) -> str:
        return f"""Convert this scheduling request into JSON constraints.

Extract EVERY independent constraint from the text. Treat separate sentences, lines, bullets, and clauses joined by "and" as separate constraints when they describe different rules.

Return this exact JSON shape:
{{"constraints": [ ... ]}}

Scheduling request:
{text}"""

    def _build_system_prompt(self) -> str:
        faculty_list = ", ".join(self.context.get("faculty_names", [])) or "not provided"
        subject_list = ", ".join(self.context.get("subject_names", [])) or "not provided"
        class_list   = ", ".join(self.context.get("class_names",   [])) or "not provided"

        return f"""You are a timetable scheduling assistant. Your only job is to convert natural language scheduling requests into structured constraint objects. Return ONLY valid JSON — no markdown, no explanation.

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

### 8. specific_time_slot
Force a subject or class into an exact day and/or period number.
```json
{{"type": "specific_time_slot", "target": "Physics", "target_type": "subject", "day": "Monday", "period": 2}}
```
If the day is not mentioned, omit the `day` field.

## Rules
- Always match names exactly to the available data context above (use the closest match).
- Map all day names to full English: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.
- Extract every independent constraint. Do not stop after the first sentence or first rule.
- If "not available on X" → use faculty_unavailability.
- If "only available on X" → use faculty_availability.
- If "continuous" or "back to back" → use consecutive_periods.
- If "not more than once a day" → use subject_max_per_day with max_per_day: 1.
- Return ONLY a JSON object in this shape: {{"constraints": [ ... ]}}. No other text.

## Few-Shot Examples

Input: "Dr. Raj cannot teach on Fridays and Saturdays"
Output: {{"constraints": [{{"type": "faculty_unavailability", "faculty_name": "Dr. Raj", "unavailable_days": ["Friday", "Saturday"]}}]}}

Input: "All lab sessions must be consecutive. Physics should be in the morning."
Output: {{"constraints": [{{"type": "consecutive_periods", "subject_type": "lab"}}, {{"type": "preferred_time_slot", "target": "Physics", "target_type": "subject", "preference": "morning"}}]}}

Input: "Prof. Meena is available only on Monday, Tuesday and Thursday. Maths should not appear more than once a day."
Output: {{"constraints": [{{"type": "faculty_availability", "faculty_name": "Prof. Meena", "available_days": ["Monday", "Tuesday", "Thursday"]}}, {{"type": "subject_max_per_day", "subject_name": "Maths", "max_per_day": 1}}]}}
"""

    # ─────────────────────────────────────────────────────────────────────────
    # OpenAI chat call (correct API)
    # ─────────────────────────────────────────────────────────────────────────

    def _chat(self, system: str, user: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for AI parsing")
        if not self.model:
            raise RuntimeError("AI_MODEL is required for AI parsing")

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
        supported = {"gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o-mini", "llama", "mixtral", "gemma"}
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

    @staticmethod
    def _extract_constraints(parsed: Any) -> List[Dict[str, Any]]:
        """
        Accept the preferred {"constraints": [...]} response, plus older model
        responses that returned a bare array or a single constraint object.
        """
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            constraints = parsed.get("constraints")
            if isinstance(constraints, list):
                return constraints
            if isinstance(constraints, dict):
                return [constraints]
            if parsed.get("type"):
                return [parsed]
        raise ValueError("Expected JSON object with a constraints array")

    # ─────────────────────────────────────────────────────────────────────────
    # Normalisation
    # ─────────────────────────────────────────────────────────────────────────

    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def _parse_day_names(self, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            normalized_value = value.replace("/", ",").replace("&", ",").replace("and", ",").replace(";", ",")
            parts = [p.strip() for p in normalized_value.split(",") if p.strip()]
        elif isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, str):
                    normalized_item = item.replace("/", ",").replace("&", ",").replace("and", ",").replace(";", ",")
                    parts.extend([p.strip() for p in normalized_item.split(",") if p.strip()])
        else:
            return []

        normalized = []
        for part in parts:
            lower = part.lower()
            for day in self.ALL_DAYS:
                day_name = day.lower()
                day_abbr = day[:3].lower()
                if (
                    lower == day_name
                    or lower.startswith(day_abbr)
                    or re.search(rf"\b{re.escape(day_name)}\b", lower)
                    or re.search(rf"\b{re.escape(day_abbr)}\b", lower)
                ):
                    normalized.append(day)
                    break
        return sorted(set(normalized), key=lambda d: self.ALL_DAYS.index(d))

    @staticmethod
    def _normalize_text(value: Any) -> str:
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", " ", value).strip()
        honorifics = {"sir", "madam", "mam", "maam", "dr", "prof", "professor", "mr", "mrs", "ms"}
        return " ".join(token for token in value.split() if token not in honorifics)

    def _context_match(self, text: str, names: List[str]) -> Optional[str]:
        normalized_text = self._normalize_text(text)
        matches = []
        for name in names:
            normalized_name = self._normalize_text(name)
            if not normalized_name:
                continue
            if normalized_name in normalized_text:
                matches.append((len(normalized_name), name))
            else:
                tokens = normalized_name.split()
                if tokens and all(token in normalized_text for token in tokens):
                    matches.append((len(normalized_name), name))
                elif tokens and tokens[0] in normalized_text.split():
                    matches.append((len(tokens[0]), name))
        return max(matches)[1] if matches else None

    def _split_constraint_text(self, text: str) -> List[str]:
        chunks = re.split(r"[\n\r.;]+", text or "")
        return [chunk.strip(" -\t") for chunk in chunks if chunk.strip(" -\t")]

    def _parse_period_numbers(self, text: str) -> List[int]:
        numbers = re.findall(r"(?:period|periods|p)\s*(\d+)", text, flags=re.IGNORECASE)
        if "last period" in text.lower():
            numbers.append(str(self.context.get("periods_per_day") or 7))
        periods = []
        for number in numbers:
            try:
                value = int(number)
            except (TypeError, ValueError):
                continue
            if value > 0:
                periods.append(value)
        return sorted(set(periods))

    def _parse_rule_based_constraints(self, text: str) -> List[Dict[str, Any]]:
        constraints = []
        faculty_names = self.context.get("faculty_names", [])
        subject_names = self.context.get("subject_names", [])
        class_names = self.context.get("class_names", [])

        for chunk in self._split_constraint_text(text):
            lower = chunk.lower()
            faculty_name = self._context_match(chunk, faculty_names)
            subject_name = self._context_match(chunk, subject_names)
            class_name = self._context_match(chunk, class_names)

            if faculty_name and ("only available" in lower or "available only" in lower):
                days = self._parse_day_names(chunk)
                if days:
                    constraints.append({"type": "faculty_availability", "faculty_name": faculty_name, "available_days": days})

            if faculty_name and any(phrase in lower for phrase in [
                "not available",
                "unavailable",
                "cannot teach",
                "can't teach",
                "will not arrive",
                "won't arrive",
                "not arrive",
                "absent",
                "on leave",
            ]):
                days = self._parse_day_names(chunk)
                if days:
                    constraints.append({"type": "faculty_unavailability", "faculty_name": faculty_name, "unavailable_days": days})

            if "lab" in lower and any(phrase in lower for phrase in ["consecutive", "continuous", "back to back", "back-to-back"]):
                constraints.append({"type": "consecutive_periods", "subject_type": "lab"})

            if "lab" in lower and any(phrase in lower for phrase in ["after lunch", "afternoon", "post lunch", "second half"]):
                constraints.append({
                    "type": "preferred_time_slot",
                    "target": "lab",
                    "target_type": "subject",
                    "preference": "afternoon",
                    "soft": "if possible" in lower,
                })

            if subject_name and any(phrase in lower for phrase in ["not more than once", "only once", "once a day", "one time per day"]):
                constraints.append({"type": "subject_max_per_day", "subject_name": subject_name, "max_per_day": 1})

            if subject_name and any(slot in lower for slot in ["morning", "afternoon", "first half", "second half"]):
                preference = "morning"
                if "afternoon" in lower or "second half" in lower:
                    preference = "afternoon"
                elif "first half" in lower:
                    preference = "first_half"
                constraints.append({"type": "preferred_time_slot", "target": subject_name, "target_type": "subject", "preference": preference})

            if class_name and any(slot in lower for slot in ["morning", "afternoon", "first half", "second half"]):
                preference = "morning"
                if "afternoon" in lower or "second half" in lower:
                    preference = "afternoon"
                elif "first half" in lower:
                    preference = "first_half"
                constraints.append({"type": "preferred_time_slot", "target": class_name, "target_type": "class", "preference": preference})

            periods = self._parse_period_numbers(chunk)
            if periods and any(phrase in lower for phrase in ["avoid", "not in", "should not", "don't schedule", "do not schedule"]):
                if class_name:
                    constraints.append({"type": "avoid_time_slot", "target": class_name, "target_type": "class", "periods": periods})
                elif subject_name:
                    constraints.append({"type": "avoid_time_slot", "target": subject_name, "target_type": "subject", "periods": periods})

            gap_match = re.search(r"(?:gap|free period).*?(\d+)|(\d+).*?(?:gap|free period)", lower)
            if class_name and gap_match:
                min_gap = int(next(group for group in gap_match.groups() if group))
                constraints.append({"type": "class_gap", "class_name": class_name, "min_gap": min_gap})

        return self._normalize_constraints(constraints)

    @staticmethod
    def _merge_constraints(primary: List[Dict[str, Any]], supplemental: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        by_identity: Dict[str, Dict[str, Any]] = {}

        for constraint in primary + supplemental:
            c_type = constraint.get("type")
            identity = None
            if c_type == "faculty_availability":
                identity = f"faculty_availability::{constraint.get('faculty_name', '').lower()}"
            elif c_type == "faculty_unavailability":
                identity = f"faculty_unavailability::{constraint.get('faculty_name', '').lower()}"
            elif c_type == "avoid_time_slot":
                identity = f"avoid_time_slot::{constraint.get('target_type', '').lower()}::{constraint.get('target', '').lower()}"

            if identity and identity in by_identity:
                existing = by_identity[identity]
                if c_type == "faculty_availability":
                    existing["available_days"] = sorted(
                        set(existing.get("available_days", [])) | set(constraint.get("available_days", [])),
                        key=lambda day: AIConstraintParser.ALL_DAYS.index(day) if day in AIConstraintParser.ALL_DAYS else 999,
                    )
                elif c_type == "faculty_unavailability":
                    existing["unavailable_days"] = sorted(
                        set(existing.get("unavailable_days", [])) | set(constraint.get("unavailable_days", [])),
                        key=lambda day: AIConstraintParser.ALL_DAYS.index(day) if day in AIConstraintParser.ALL_DAYS else 999,
                    )
                elif c_type == "avoid_time_slot":
                    existing["periods"] = sorted(set(existing.get("periods", [])) | set(constraint.get("periods", [])))
                continue

            key = json.dumps(constraint, sort_keys=True)
            if any(json.dumps(item, sort_keys=True) == key for item in merged):
                continue
            merged.append(constraint)
            if identity:
                by_identity[identity] = constraint
        return merged

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
                    normalized_constraint = {
                        "type": "preferred_time_slot",
                        "target": str(target),
                        "target_type": str(target_type),
                        "preference": pref,
                    }
                    if c.get("soft") is not None:
                        normalized_constraint["soft"] = bool(c.get("soft"))
                    normalized.append(normalized_constraint)

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

            # ── specific_time_slot ───────────────────────────────────────────
            elif c_type in {"specific_time_slot", "exact_time_slot", "specific_slot"}:
                target = c.get("target") or c.get("subject_name") or c.get("class_name") or ""
                target_type = c.get("target_type") or "subject"
                day_val = c.get("day") or c.get("day_name")
                day = self._parse_day_names([day_val])[0] if day_val and self._parse_day_names([day_val]) else None
                period = c.get("period") or c.get("period_number")
                try:
                    period = int(period) if period is not None else None
                except (TypeError, ValueError):
                    period = None
                
                if target and period is not None:
                    constraint = {"type": "specific_time_slot", "target": str(target), "target_type": str(target_type), "period": period}
                    if day:
                        constraint["day"] = day
                    normalized.append(constraint)

            # ── pass-through unknowns ────────────────────────────────────────
            else:
                normalized.append(c)

        return normalized
