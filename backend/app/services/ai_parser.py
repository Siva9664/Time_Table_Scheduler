import json
import re
import difflib
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI


class AIConstraintParser:
    """
    Parses natural language timetable constraints into structured JSON.
    Features:
    - AI (Groq/OpenAI) + rule-based hybrid parsing
    - Fuzzy name matching with auto-correction tracking
    - Rich diagnostics: corrections, warnings, unrecognized phrases
    - All 8 constraint types supported
    """

    SUPPORTED_TYPES = [
        "faculty_availability", "faculty_unavailability", "faculty_time_unavailability", "consecutive_periods",
        "subject_max_per_day", "preferred_time_slot", "avoid_time_slot",
        "class_gap", "specific_time_slot",
    ]

    ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    WEEKDAY_ALIASES = {
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "weekend": ["Saturday", "Sunday"],
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
        "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
    }

    def __init__(self, model=None, timeout_seconds=60, api_key=None,
                 api_base="https://api.openai.com/v1", context=None):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.context = context or {}
        self._corrections: List[Dict] = []
        self._warnings: List[str] = []
        self._unrecognized: List[str] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def parse_constraints(self, text: str) -> List[Dict[str, Any]]:
        return self.parse_constraints_with_diagnostics(text)["constraints"]

    def parse_constraints_with_diagnostics(self, text: str) -> Dict[str, Any]:
        self._corrections = []
        self._warnings = []
        self._unrecognized = []

        if not self.api_key or not self.model:
            constraints = self._rule_based(text)
        else:
            try:
                raw = self._chat(self._build_system_prompt(), self._build_user_prompt(text))
                ai_c = self._extract_constraints(json.loads(raw))
                rule_c = self._rule_based(text)
                constraints = self._merge(self._normalize(ai_c), rule_c)
            except Exception as e:
                print(f"AI Parse Error: {e}")
                constraints = self._rule_based(text)

        return {
            "constraints": constraints,
            "corrections": self._corrections,
            "warnings": self._warnings,
            "unrecognized": self._unrecognized,
        }

    # ── Prompt building ────────────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(text: str) -> str:
        return (
            "Convert this scheduling request into JSON constraints. "
            "Extract EVERY independent constraint. Treat separate sentences, lines, "
            "bullets, and clauses as separate constraints.\n\n"
            "Return ONLY this JSON shape: {\"constraints\": [ ... ]}\n\n"
            f"Scheduling request:\n{text}"
        )

    def _build_system_prompt(self) -> str:
        faculty_list = ", ".join(self.context.get("faculty_names", [])) or "not provided"
        subject_list = ", ".join(self.context.get("subject_names", [])) or "not provided"
        class_list   = ", ".join(self.context.get("class_names",   [])) or "not provided"
        return f"""You are a timetable scheduling assistant. Convert natural language scheduling requests into structured constraint objects. Return ONLY valid JSON.

## Context
- Faculty: {faculty_list}
- Subjects: {subject_list}
- Classes: {class_list}

## Constraint Types
1. faculty_availability  – {{"type":"faculty_availability","faculty_name":"Dr. X","available_days":["Monday"]}}
2. faculty_unavailability – {{"type":"faculty_unavailability","faculty_name":"Prof. Y","unavailable_days":["Friday"]}}
3. faculty_time_unavailability – {{"type":"faculty_time_unavailability","faculty_name":"Dr. X","start_time":"10:15","end_time":"12:30"}}
4. consecutive_periods   – {{"type":"consecutive_periods","subject_type":"lab"}}
5. subject_max_per_day   – {{"type":"subject_max_per_day","subject_name":"Maths","max_per_day":1}}
6. preferred_time_slot   – {{"type":"preferred_time_slot","target":"Physics","target_type":"subject","preference":"morning"}}
7. avoid_time_slot       – {{"type":"avoid_time_slot","target":"CSE-A","target_type":"class","periods":[7,8]}}
8. class_gap             – {{"type":"class_gap","class_name":"CSE-A","min_gap":1}}
9. specific_time_slot    – {{"type":"specific_time_slot","target":"Physics","target_type":"subject","day":"Monday","period":2}}

## Rules
- Match names exactly to the context above.
- Day names → full English (Monday, Tuesday, ...).
- Extract EVERY constraint, not just the first.
- Return ONLY {{"constraints":[...]}}. No other text.

## Examples
Input: "Dr. Raj cannot teach on Fridays and Saturdays"
Output: {{"constraints":[{{"type":"faculty_unavailability","faculty_name":"Dr. Raj","unavailable_days":["Friday","Saturday"]}}]}}

Input: "Labs must be consecutive. Physics in the morning."
Output: {{"constraints":[{{"type":"consecutive_periods","subject_type":"lab"}},{{"type":"preferred_time_slot","target":"Physics","target_type":"subject","preference":"morning"}}]}}
"""

    # ── AI chat ────────────────────────────────────────────────────────────────

    def _chat(self, system: str, user: str) -> str:
        client = OpenAI(api_key=self.api_key, base_url=self.api_base, timeout=self.timeout_seconds)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
            response_format={"type": "json_object"} if self._supports_json_mode() else None,
        )
        return self._strip_md(response.choices[0].message.content or "")

    def _supports_json_mode(self) -> bool:
        supported = {"gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o-mini", "llama", "mixtral", "gemma"}
        return any(s in (self.model or "").lower() for s in supported)

    @staticmethod
    def _strip_md(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"): text = text[7:].strip()
        elif text.startswith("```"): text = text[3:].strip()
        if text.endswith("```"): text = text[:-3].strip()
        return text

    @staticmethod
    def _extract_constraints(parsed: Any) -> List[Dict[str, Any]]:
        if isinstance(parsed, list): return parsed
        if isinstance(parsed, dict):
            c = parsed.get("constraints")
            if isinstance(c, list): return c
            if isinstance(c, dict): return [c]
            if parsed.get("type"): return [parsed]
        raise ValueError("Expected JSON object with constraints array")

    # ── Name matching (exact + fuzzy) ──────────────────────────────────────────

    @staticmethod
    def _normalize_text(value: Any) -> str:
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", " ", value).strip()
        honorifics = {"sir", "madam", "mam", "maam", "dr", "prof", "professor", "mr", "mrs", "ms"}
        return " ".join(t for t in value.split() if t not in honorifics)

    def _fuzzy_match(self, text: str, names: List[str], cutoff: float = 0.70) -> Optional[Tuple[str, Optional[str]]]:
        """
        Returns (matched_name, misspelled_word_or_None).
        Tries exact substring match first, then token-level fuzzy.
        """
        norm_text = self._normalize_text(text)
        text_tokens = norm_text.split()

        for name in names:
            norm_name = self._normalize_text(name)
            if not norm_name:
                continue
            # 1. Exact full-name word-boundary match → no typo
            if re.search(r'\b' + re.escape(norm_name) + r'\b', norm_text):
                return (name, None)
            # 2. All key tokens present — check if any token differs (typo detection)
            name_tokens = [t for t in norm_name.split() if len(t) >= 3]
            if name_tokens:
                typo_found = None
                all_present = True
                for nt in name_tokens:
                    if nt in text_tokens:
                        continue  # exact match — no typo for this token
                    # Check near-exact (e.g. "shivaa" vs "shiva")
                    close = difflib.get_close_matches(nt, text_tokens, n=1, cutoff=0.78)
                    if close:
                        typo_found = close[0]  # what the user typed (the misspelling)
                    else:
                        all_present = False
                        break
                if all_present:
                    return (name, typo_found)  # typo_found is the misspelling or None if all exact

        # 3. Lower-cutoff fuzzy for more distant typos
        for name in names:
            norm_name = self._normalize_text(name)
            name_tokens = [t for t in norm_name.split() if len(t) >= 3]
            if not name_tokens:
                continue
            matched, typo_pair = 0, None
            for nt in name_tokens:
                close = difflib.get_close_matches(nt, text_tokens, n=1, cutoff=cutoff)
                if close:
                    matched += 1
                    if close[0] != nt:
                        typo_pair = (close[0], nt)
            if matched >= max(1, (len(name_tokens) + 1) // 2):
                typo_word = typo_pair[0] if typo_pair else None
                return (name, typo_word)

        return None


    def _context_match(self, text: str, names: List[str]) -> Optional[str]:
        """Match a name from context with fuzzy fallback and correction tracking."""
        result = self._fuzzy_match(text, names)
        if result:
            matched_name, typo = result
            if typo:
                self._corrections.append({
                    "original": typo,
                    "corrected": matched_name,
                    "reason": f"Auto-corrected '{typo}' → '{matched_name}'"
                })
            return matched_name
        return None

    # ── Day parsing ────────────────────────────────────────────────────────────

    def _parse_day_names(self, value: Any) -> List[str]:
        """Parse day names from a string or list, supporting ranges, aliases, and abbreviations."""
        if not value:
            return []

        # Normalise to a single string first
        if isinstance(value, list):
            text = " , ".join(str(v) for v in value)
        else:
            text = str(value)

        lower = text.lower()

        # Expand weekdays/weekend aliases
        if "weekdays" in lower:
            return self.WEEKDAY_ALIASES["weekdays"]
        if "weekend" in lower:
            return self.WEEKDAY_ALIASES["weekend"]

        # Handle ranges like "Mon-Thu" or "Monday to Friday"
        range_match = re.search(r"(\w+)\s*(?:[-–]|to)\s*(\w+)", text, re.IGNORECASE)
        if range_match:
            s = self._single_day(range_match.group(1))
            e = self._single_day(range_match.group(2))
            if s and e:
                si, ei = self.ALL_DAYS.index(s), self.ALL_DAYS.index(e)
                return self.ALL_DAYS[si : ei + 1]

        # Tokenise by separators (commas, slashes, ampersands)
        # Do NOT split on "and" here — "Monday, Tuesday and Thursday" is fine as tokens
        normalized = re.sub(r"[/&;,]+", " ", text)
        # Replace " and " surrounded by spaces with a space only
        normalized = re.sub(r"\band\b", " ", normalized, flags=re.IGNORECASE)

        result = []
        for word in normalized.split():
            day = self._single_day(word)
            if day and day not in result:
                result.append(day)
        return sorted(result, key=lambda d: self.ALL_DAYS.index(d))

    def _single_day(self, text: str) -> Optional[str]:
        lower = text.strip().lower()
        alias = self.WEEKDAY_ALIASES.get(lower)
        if isinstance(alias, str):
            return alias
        for day in self.ALL_DAYS:
            if lower == day.lower() or lower.startswith(day[:3].lower()):
                return day
        return None

    def _parse_period_numbers(self, text: str) -> List[int]:
        """Extract period numbers from text, supporting various phrasings."""
        lower = text.lower()
        periods = []

        # "last N periods"
        m = re.search(r"last\s+(\d+)\s+period", lower)
        if m:
            total = self.context.get("periods_per_day", 7)
            n = int(m.group(1))
            periods.extend(range(total - n + 1, total + 1))

        if re.search(r"\bfirst\s+period\b", lower):
            periods.append(1)
        if re.search(r"\blast\s+period\b", lower):
            periods.append(self.context.get("periods_per_day", 7))

        # "period N" or "periods N and M" or just numbers after "period"
        # First find all numbers associated with period mentions
        period_section = re.sub(r"period[s]?\s*", "PERIOD ", lower)
        raw = re.findall(r"(?:PERIOD\s*)?(\d+)", period_section)
        # Only pick up numbers that appear after "period" or "avoid period N and M"
        for m2 in re.finditer(r"(?:period[s]?)\s*([\d\s,and]+)", lower):
            nums = re.findall(r"\d+", m2.group(1))
            periods.extend(int(n) for n in nums if 1 <= int(n) <= 20)

        return sorted(set(p for p in periods if 1 <= p <= 20))

    # ── Text splitting (sentence-level only, NOT on "and") ──────────────────────

    def _split_text(self, text: str) -> List[str]:
        """Split on sentence boundaries only. Never split on 'and' — it's part of day lists."""
        # Fix dots in time formats (12.30 -> 12:30) before splitting
        if text:
            text = re.sub(r"(\d)\.(\d)", r"\1:\2", text)
        # Split on periods, semicolons, newlines, bullets
        chunks = re.split(r"[.;\n\r]+", text or "")
        result = []
        for chunk in chunks:
            chunk = chunk.strip(" -•\t*")
            if chunk:
                result.append(chunk)
        return result

    # ── Rule-based parser with diagnostics ────────────────────────────────────

    def _rule_based(self, text: str) -> List[Dict[str, Any]]:
        constraints: List[Dict[str, Any]] = []
        faculty_names = self.context.get("faculty_names", [])
        subject_names = self.context.get("subject_names", [])
        class_names   = self.context.get("class_names",   [])

        for chunk in self._split_text(text):
            produced = False
            lower = chunk.lower()

            faculty = self._context_match(chunk, faculty_names)
            subject = self._context_match(chunk, subject_names)

            # Only match a class if the chunk doesn't already match a subject
            # (prevents "Physics" from accidentally matching "CSE-A" via a partial word)
            cls = self._context_match(chunk, class_names) if not subject else None

            # ── 1. faculty_availability ─────────────────────────────────────
            if faculty and re.search(r"only\s+available|available\s+only", lower):
                days = self._parse_day_names(chunk)
                if days:
                    constraints.append({
                        "type": "faculty_availability",
                        "faculty_name": faculty,
                        "available_days": days,
                    })
                    produced = True

            # ── 2. faculty_unavailability ───────────────────────────────────
            UNAVAIL_PHRASES = [
                "not available", "unavailable", "cannot teach", "can't teach",
                "cant teach", "will not teach", "wont teach", "won't teach",
                "not come", "absent", "on leave", "not teaching",
                "cannot come", "can't come", "cant come",
            ]
            if faculty and any(p in lower for p in UNAVAIL_PHRASES):
                time_matches = list(re.finditer(r"(\d{1,2}[:.]\d{2}\s*(?:am|pm)?)\s*(?:to|-)\s*(\d{1,2}[:.]\d{2}\s*(?:am|pm)?)", lower))
                if time_matches:
                    for tm in time_matches:
                        constraints.append({
                            "type": "faculty_time_unavailability",
                            "faculty_name": faculty,
                            "start_time": tm.group(1),
                            "end_time": tm.group(2),
                        })
                        produced = True
                else:
                    days = self._parse_day_names(chunk)
                    if days:
                        constraints.append({
                            "type": "faculty_unavailability",
                            "faculty_name": faculty,
                            "unavailable_days": days,
                        })
                        produced = True

            # ── 3. consecutive_periods ──────────────────────────────────────
            CONSEC_PHRASES = ["consecutive", "continuous", "back to back", "back-to-back", "together"]
            if any(p in lower for p in CONSEC_PHRASES):
                sub_type = "lab" if "lab" in lower else (subject or "lab")
                if isinstance(sub_type, str):
                    constraints.append({"type": "consecutive_periods", "subject_type": sub_type})
                    produced = True

            # ── 4. subject_max_per_day ──────────────────────────────────────
            MAX_PHRASES = [
                "not more than once", "only once", "once a day",
                "one time per day", "at most once", "maximum once",
                "not more than one", "no more than once",
            ]
            if subject and any(p in lower for p in MAX_PHRASES):
                constraints.append({
                    "type": "subject_max_per_day",
                    "subject_name": subject,
                    "max_per_day": 1,
                })
                produced = True

            # "max N times per day"
            max_n = re.search(r"(?:max|maximum|at most)\s+(\d+)\s+(?:time|period|class|hour)", lower)
            if subject and max_n:
                constraints.append({
                    "type": "subject_max_per_day",
                    "subject_name": subject,
                    "max_per_day": int(max_n.group(1)),
                })
                produced = True

            # ── 5. preferred_time_slot ──────────────────────────────────────
            PREF_MAP = {
                "morning":     ["morning", "early morning", "first half"],
                "afternoon":   ["afternoon", "after lunch", "post lunch", "second half"],
                "first_half":  ["first half"],
                "second_half": ["second half"],
            }
            for pref, kws in PREF_MAP.items():
                if any(kw in lower for kw in kws):
                    if subject:
                        constraints.append({
                            "type": "preferred_time_slot",
                            "target": subject,
                            "target_type": "subject",
                            "preference": pref,
                        })
                        produced = True
                    elif cls:
                        constraints.append({
                            "type": "preferred_time_slot",
                            "target": cls,
                            "target_type": "class",
                            "preference": pref,
                        })
                        produced = True
                    elif "lab" in lower:
                        constraints.append({
                            "type": "preferred_time_slot",
                            "target": "lab",
                            "target_type": "subject",
                            "preference": pref,
                        })
                        produced = True
                    break

            # ── 6. avoid_time_slot ──────────────────────────────────────────
            AVOID_PHRASES = [
                "avoid", "not in period", "should not", "don't schedule",
                "do not schedule", "no class at", "block period", "not at period",
            ]
            periods = self._parse_period_numbers(chunk)
            if periods and any(p in lower for p in AVOID_PHRASES):
                target = cls or subject
                t_type = "class" if cls else ("subject" if subject else None)
                if target and t_type:
                    constraints.append({
                        "type": "avoid_time_slot",
                        "target": target,
                        "target_type": t_type,
                        "periods": periods,
                    })
                    produced = True

            # ── 7. class_gap ────────────────────────────────────────────────
            GAP_KWS = ["gap", "free period", "break between", "free slot", "rest"]
            gap_m = re.search(r"(\d+)\s*(?:period|slot|free|hour|gap)", lower)
            if cls and any(k in lower for k in GAP_KWS) and gap_m:
                constraints.append({
                    "type": "class_gap",
                    "class_name": cls,
                    "min_gap": int(gap_m.group(1)),
                })
                produced = True

            # ── 8. specific_time_slot ───────────────────────────────────────
            SPECIFIC_KWS = ["schedule on", "place on", "fix on", "must be on",
                            "assign to period", "keep on", "should be on"]
            if any(k in lower for k in SPECIFIC_KWS) and periods:
                days = self._parse_day_names(chunk)
                target = subject or cls
                t_type = "subject" if subject else ("class" if cls else None)
                if target and t_type:
                    c: Dict[str, Any] = {
                        "type": "specific_time_slot",
                        "target": target,
                        "target_type": t_type,
                        "period": periods[0],
                    }
                    if days:
                        c["day"] = days[0]
                    constraints.append(c)
                    produced = True

            # Track unrecognized
            if not produced and len(chunk.split()) > 2:
                self._unrecognized.append(chunk)

        return self._normalize(constraints)

    # ── Normalisation ──────────────────────────────────────────────────────────

    def _normalize(self, constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for c in constraints:
            if not isinstance(c, dict):
                continue
            t = str(c.get("type", "")).lower().replace(" ", "_")

            if t in {"faculty_availability", "availability"}:
                name = c.get("faculty_name") or c.get("faculty") or c.get("name")
                days = self._parse_day_names(c.get("available_days") or c.get("days") or [])
                if name and days:
                    out.append({"type": "faculty_availability", "faculty_name": str(name), "available_days": days})

            elif t in {"faculty_unavailability", "unavailability", "unavailable", "not_available"}:
                name = c.get("faculty_name") or c.get("faculty") or c.get("name")
                unavail = self._parse_day_names(
                    c.get("unavailable_days") or c.get("not_available_days") or c.get("days") or []
                )
                avail = [d for d in self.ALL_DAYS if d not in unavail]
                if name and unavail:
                    # Store as faculty_availability with the complement days
                    out.append({"type": "faculty_availability", "faculty_name": str(name), "available_days": avail})

            elif t in {"faculty_time_unavailability", "time_unavailability", "faculty_time"}:
                name = c.get("faculty_name") or c.get("faculty") or c.get("name")
                start = c.get("start_time") or c.get("start")
                end = c.get("end_time") or c.get("end")
                if name and start and end:
                    # try to ensure HH:MM format
                    start = str(start).replace(".", ":").lower()
                    end = str(end).replace(".", ":").lower()
                    # simplistic am/pm cleanup
                    for suffix in [" am", " pm", "am", "pm"]:
                        start = start.replace(suffix, "")
                        end = end.replace(suffix, "")
                    out.append({"type": "faculty_time_unavailability", "faculty_name": str(name), "start_time": start.strip(), "end_time": end.strip()})

            elif t in {"consecutive_periods", "consecutive", "continuous"}:
                st = c.get("subject_type") or c.get("subject") or "lab"
                out.append({"type": "consecutive_periods", "subject_type": str(st).lower()})

            elif t in {"subject_max_per_day", "max_per_day", "daily_limit"}:
                sn = c.get("subject_name") or c.get("subject") or ""
                mp = c.get("max_per_day") or c.get("max") or 1
                try:
                    mp = int(mp)
                except (TypeError, ValueError):
                    mp = 1
                if sn:
                    out.append({"type": "subject_max_per_day", "subject_name": str(sn), "max_per_day": mp})

            elif t in {"preferred_time_slot", "preferred_slot", "time_preference"}:
                target = c.get("target") or c.get("subject_name") or c.get("class_name") or ""
                t_type = c.get("target_type") or ("class" if c.get("class_name") else "subject")
                pref = str(c.get("preference") or "morning").lower()
                if pref not in {"morning", "afternoon", "first_half", "second_half"}:
                    pref = "morning"
                if target:
                    nc: Dict[str, Any] = {
                        "type": "preferred_time_slot",
                        "target": str(target),
                        "target_type": str(t_type),
                        "preference": pref,
                    }
                    if c.get("soft") is not None:
                        nc["soft"] = bool(c["soft"])
                    out.append(nc)

            elif t in {"avoid_time_slot", "blocked_periods", "avoid_periods"}:
                target = c.get("target") or c.get("class_name") or c.get("subject_name") or ""
                t_type = c.get("target_type") or "class"
                periods = c.get("periods") or c.get("blocked_periods") or []
                if isinstance(periods, int):
                    periods = [periods]
                try:
                    periods = [int(p) for p in periods]
                except (TypeError, ValueError):
                    periods = []
                if target and periods:
                    out.append({
                        "type": "avoid_time_slot",
                        "target": str(target),
                        "target_type": str(t_type),
                        "periods": periods,
                    })

            elif t in {"class_gap", "gap", "free_period"}:
                cn = c.get("class_name") or c.get("class") or ""
                mg = c.get("min_gap") or c.get("gap") or 1
                try:
                    mg = int(mg)
                except (TypeError, ValueError):
                    mg = 1
                if cn:
                    out.append({"type": "class_gap", "class_name": str(cn), "min_gap": mg})

            elif t in {"specific_time_slot", "exact_time_slot", "specific_slot"}:
                target = c.get("target") or c.get("subject_name") or c.get("class_name") or ""
                t_type = c.get("target_type") or "subject"
                dv = c.get("day") or c.get("day_name")
                day = self._single_day(dv) if dv else None
                period = c.get("period") or c.get("period_number")
                try:
                    period = int(period) if period is not None else None
                except (TypeError, ValueError):
                    period = None
                if target and period is not None:
                    nc2: Dict[str, Any] = {
                        "type": "specific_time_slot",
                        "target": str(target),
                        "target_type": str(t_type),
                        "period": period,
                    }
                    if day:
                        nc2["day"] = day
                    out.append(nc2)
            else:
                out.append(c)
        return out

    # ── Merge (deduplicate + combine overlapping) ──────────────────────────────

    @staticmethod
    def _merge(primary: List[Dict], supplemental: List[Dict]) -> List[Dict]:
        merged: List[Dict] = []
        by_id: Dict[str, Dict] = {}

        for c in primary + supplemental:
            ct = c.get("type")
            ident = None
            if ct == "faculty_availability":
                ident = f"fa::{c.get('faculty_name','').lower()}"
            elif ct == "avoid_time_slot":
                ident = f"av::{c.get('target_type','').lower()}::{c.get('target','').lower()}"

            if ident and ident in by_id:
                ex = by_id[ident]
                if ct == "faculty_availability":
                    ex["available_days"] = sorted(
                        set(ex.get("available_days", [])) | set(c.get("available_days", [])),
                        key=lambda d: AIConstraintParser.ALL_DAYS.index(d)
                        if d in AIConstraintParser.ALL_DAYS else 99,
                    )
                elif ct == "avoid_time_slot":
                    ex["periods"] = sorted(
                        set(ex.get("periods", [])) | set(c.get("periods", []))
                    )
                continue

            key = json.dumps(c, sort_keys=True)
            if any(json.dumps(m, sort_keys=True) == key for m in merged):
                continue
            merged.append(c)
            if ident:
                by_id[ident] = c

        return merged
