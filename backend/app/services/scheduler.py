from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId
import time
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class _Obj:
    """Simple attribute-access wrapper around a MongoDB document dict."""
    def __init__(self, doc: dict):
        self._doc = doc
        # Expose string id
        self.id = str(doc["_id"])

    def __getattr__(self, name):
        if name.startswith("_") or name == "id":
            raise AttributeError(name)
        return self._doc.get(name)

    def __repr__(self):
        return f"<_Obj id={self.id} {self._doc}>"


class TimetableScheduler:
    def __init__(self, db: Database, working_days: List[str], periods_per_day: int, time_limit_seconds: int = 60, custom_constraints: List[Dict[str, Any]] = None):
        self.db = db
        self.working_days = working_days
        self.periods_per_day = periods_per_day
        self.time_limit_seconds = time_limit_seconds
        self.custom_constraints = custom_constraints or []
        self.num_days = len(working_days)

        # Caches
        self.departments = []
        self.batches = []
        self.classes = []
        self.subjects = []
        self.faculty = []

        # OR-Tools
        self.model = cp_model.CpModel()
        self.variables = {}  # Map: "s{subject_id}_d{day_index}_p{period_index}" -> BoolVar

        # Optimization Caches
        self.vars_by_faculty = {}  # faculty_id -> day -> list of {'start', 'end', 'var', 'period'}
        self.vars_by_subject = {}  # subject_id -> list of BoolVar
        self.constraint_errors = []

    def _wrap(self, doc: dict) -> _Obj:
        return _Obj(doc)

    @staticmethod
    def _id_str(value: Any) -> str:
        return str(value) if value is not None else ""

    def _wrap_class(self, doc: dict) -> _Obj:
        """Wrap a class document and attach nested batch/department objects."""
        obj = _Obj(doc)
        # Attach batch
        batch_id = doc.get("batch_id")
        if batch_id:
            batch_doc = self.db["batches"].find_one({"_id": ObjectId(batch_id)}) if ObjectId.is_valid(batch_id) else None
            obj._doc["_batch_obj"] = _Obj(batch_doc) if batch_doc else None
        else:
            obj._doc["_batch_obj"] = None
        return obj

    def load_data(self, department_ids: Optional[List[str]] = None, batch_ids: Optional[List[str]] = None, class_ids: Optional[List[str]] = None, faculty_ids: Optional[List[str]] = None):
        """Loads all necessary data from MongoDB."""
        logger.info("Step 1/5: Loading data from database...")

        # Departments
        dept_query = {}
        if department_ids:
            oids = [ObjectId(d) for d in department_ids if ObjectId.is_valid(d)]
            dept_query = {"_id": {"$in": oids}}
        self.departments = [self._wrap(d) for d in self.db["departments"].find(dept_query)]
        dept_ids_str = [dep.id for dep in self.departments]

        # Batches
        batch_query = {}
        if batch_ids:
            oids = [ObjectId(b) for b in batch_ids if ObjectId.is_valid(b)]
            batch_query = {"_id": {"$in": oids}}
        self.batches = [self._wrap(d) for d in self.db["batches"].find(batch_query)]

        # Classes
        class_query = {}
        if class_ids:
            oids = [ObjectId(c) for c in class_ids if ObjectId.is_valid(c)]
            class_query = {"_id": {"$in": oids}}
        elif dept_ids_str:
            class_query = {"department_id": {"$in": dept_ids_str}}
        self.classes = [self._wrap_class(d) for d in self.db["classes"].find(class_query)]
        loaded_class_ids = [c.id for c in self.classes]
        self.class_map = {self._id_str(c.id): c for c in self.classes}

        # Subjects (linked to loaded classes)
        if loaded_class_ids:
            self.subjects = [self._wrap(d) for d in self.db["subjects"].find({"class_id": {"$in": loaded_class_ids}})]
        else:
            self.subjects = []

        # Faculty
        assigned_faculty_ids = {self._id_str(s.faculty_id) for s in self.subjects if s.faculty_id}
        if faculty_ids:
            all_ids = set(faculty_ids) | assigned_faculty_ids
            oids = [ObjectId(f) for f in all_ids if ObjectId.is_valid(f)]
            fac_query = {"_id": {"$in": oids}}
        elif dept_ids_str:
            fac_query = {"$or": [
                {"department_id": {"$in": dept_ids_str}},
                {"_id": {"$in": [ObjectId(f) for f in assigned_faculty_ids if ObjectId.is_valid(f)]}}
            ]} if assigned_faculty_ids else {"department_id": {"$in": dept_ids_str}}
        else:
            fac_query = {}
        self.faculty = [self._wrap(d) for d in self.db["faculty"].find(fac_query)]

        # Legacy assignment support is disabled.

        summary = {
            "departments": len(self.departments), "batches": len(self.batches),
            "classes": len(self.classes), "subjects": len(self.subjects),
            "faculty": len(self.faculty)
        }
        logger.info(f"Data Loaded: {summary}")
        return summary

    def _parse_time(self, time_str: str) -> int:
        """Converts HH:MM string to minutes from midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _format_time(self, minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _format_display_time(self, minutes: int) -> str:
        hours_24 = (minutes // 60) % 24
        mins = minutes % 60
        suffix = "AM" if hours_24 < 12 else "PM"
        hours_12 = hours_24 % 12 or 12
        return f"{hours_12}:{mins:02d} {suffix}"

    def _format_time_range(self, start: int, end: int) -> str:
        return f"{self._format_display_time(start)} - {self._format_display_time(end)}"

    def _slot_blocks_day(self, slot: Dict[str, Any], day_idx: int, day_name: str) -> bool:
        slot_day = slot.get("day") or slot.get("day_name")
        if slot_day and str(slot_day).lower() == day_name.lower():
            return True

        slot_day_index = slot.get("day_index")
        if slot_day_index is not None:
            try:
                return int(slot_day_index) == day_idx
            except (TypeError, ValueError):
                return False

        return not slot_day

    def _slot_blocks_period(self, slot: Dict[str, Any], period_idx: int, start: int, end: int) -> bool:
        period_value = slot.get("period")
        if period_value is not None:
            try:
                return int(period_value) == period_idx + 1
            except (TypeError, ValueError):
                return False

        periods = slot.get("periods")
        if isinstance(periods, list):
            normalized_periods = set()
            for value in periods:
                try:
                    normalized_periods.add(int(value))
                except (TypeError, ValueError):
                    continue
            return period_idx + 1 in normalized_periods

        start_time = slot.get("start") or slot.get("start_time")
        end_time = slot.get("end") or slot.get("end_time")
        if start_time and end_time:
            slot_start = self._parse_time(start_time)
            slot_end = self._parse_time(end_time)
            return start < slot_end and slot_start < end

        return True

    def _is_faculty_unavailable(self, faculty: _Obj, day_idx: int, day_name: str, period_idx: int, start: int, end: int) -> bool:
        for slot in faculty.unavailable_slots or []:
            if not isinstance(slot, dict):
                continue
            if self._slot_blocks_day(slot, day_idx, day_name) and self._slot_blocks_period(slot, period_idx, start, end):
                return True
        return False

    def _find_faculty_by_name(self, target_name: str) -> Optional[_Obj]:
        if not target_name:
            return None
        target_name = self._normalize_match_text(target_name)
        tokens = [token for token in target_name.split() if token]
        for fac in self.faculty:
            faculty_name = self._normalize_match_text(fac.name)
            if target_name == faculty_name or target_name in faculty_name or faculty_name in target_name:
                return fac
            if tokens and all(token in faculty_name for token in tokens):
                return fac
        return None

    @staticmethod
    def _normalize_match_text(value: Any) -> str:
        value = str(value or "").strip().lower()
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    def _matches_text(self, target: str, candidate: str) -> bool:
        target = self._normalize_match_text(target)
        candidate = self._normalize_match_text(candidate)
        if not target or not candidate:
            return False
        if target == candidate or target in candidate:
            return True
        target_tokens = target.split()
        return bool(target_tokens) and all(token in candidate for token in target_tokens)

    def _class_display_name(self, class_obj: _Obj) -> str:
        return f"{class_obj.name or ''} {class_obj.section or ''}".strip()

    def _matches_class(self, target: str, class_obj: _Obj) -> bool:
        return (
            self._matches_text(target, class_obj.name)
            or self._matches_text(target, class_obj.section)
            or self._matches_text(target, self._class_display_name(class_obj))
        )

    def _matches_subject(self, target: str, subject: _Obj) -> bool:
        return (
            self._matches_text(target, subject.name)
            or self._matches_text(target, subject.code)
        )

    def _subjects_for_class_target(self, target: str) -> List[_Obj]:
        class_ids = {self._id_str(cls.id) for cls in self.classes if self._matches_class(target, cls)}
        return [sub for sub in self.subjects if self._id_str(sub.class_id) in class_ids]

    def _subjects_for_target(self, target: str, target_type: str = "subject") -> List[_Obj]:
        if target_type == "class":
            return self._subjects_for_class_target(target)
            
        target_norm = self._normalize_match_text(target)
        if not target_norm:
            return []
            
        # Try exact match first
        exact_matches = [
            sub for sub in self.subjects
            if self._normalize_match_text(sub.name) == target_norm or self._normalize_match_text(sub.code) == target_norm
        ]
        if exact_matches:
            return exact_matches
            
        return [sub for sub in self.subjects if self._matches_subject(target, sub)]

    def _constraint_error(self, message: str):
        self.constraint_errors.append(message)
        logger.warning(message)

    def _calculate_class_period_intervals(self, class_obj: _Obj, max_periods: Optional[int] = None) -> List[Tuple[int, int]]:
        """
        Returns a list of (start_minute, end_minute) for each period of the day for this class.
        Based on the class's Batch configuration.
        """
        batch = class_obj._doc.get("_batch_obj")
        if not batch:
            # Fallback if no batch assigned: Simple uniform 60min slots starting 09:00
            start = 9 * 60
            intervals = []
            for _ in range(max_periods or self.periods_per_day):
                intervals.append((start, start + 60))
                start += 60
            return intervals

        day_start = self._parse_time(batch.start_time)
        day_end = self._parse_time(batch.end_time) if batch.end_time else day_start + (self.periods_per_day * (batch.period_duration or 60))
        period_duration = batch.period_duration or 60
        break_slots = [
            slot for slot in self._get_class_break_slots(class_obj)
            if slot["start"] < day_end and slot["end"] > day_start and slot["end"] > slot["start"]
        ]

        intervals = []
        current_time = day_start

        while (max_periods is None or len(intervals) < max_periods) and current_time + period_duration <= day_end:
            active_break = next(
                (slot for slot in break_slots if slot["start"] <= current_time < slot["end"]),
                None
            )
            if active_break:
                current_time = active_break["end"]
                continue

            next_break = next(
                (slot for slot in break_slots if slot["start"] >= current_time),
                None
            )

            if next_break and current_time + period_duration > next_break["start"]:
                if current_time < next_break["start"]:
                    logger.warning(
                        "Skipping short teaching gap %s-%s before %s because it is less than the %s-minute period duration",
                        self._format_time(current_time),
                        self._format_time(next_break["start"]),
                        next_break.get("label", "break"),
                        period_duration,
                    )
                current_time = next_break["end"]
                continue

            p_start = current_time
            p_end = current_time + period_duration
            intervals.append((p_start, p_end))
            current_time = p_end

        return intervals

    def _get_class_period_intervals(self, class_obj: _Obj) -> List[Tuple[int, int]]:
        """
        Returns teaching period intervals capped by the scheduler's effective
        period count. The effective count is derived from batch timing before
        variables are created.
        """
        return self._calculate_class_period_intervals(class_obj, self.periods_per_day)

    def _sync_periods_per_day_to_batch_timings(self):
        calculated_counts = [
            len(self._calculate_class_period_intervals(class_obj, None))
            for class_obj in self.classes
            if class_obj._doc.get("_batch_obj")
        ]
        if calculated_counts:
            self.periods_per_day = max(calculated_counts)
            logger.info(f"Effective periods per day calculated from batch timings: {self.periods_per_day}")

    def _get_class_break_slots(self, class_obj: _Obj) -> List[Dict[str, Any]]:
        batch = class_obj._doc.get("_batch_obj")
        if not batch:
            return []

        break_slots = []
        for idx, break_time in enumerate(batch.break_times or [], 1):
            start = break_time.get("start")
            end = break_time.get("end")
            if not start or not end:
                continue
            break_slots.append({
                "slot_type": "break",
                "break_type": "break",
                "label": f"Break {idx}",
                "start": self._parse_time(start),
                "end": self._parse_time(end),
            })

        lunch_break = batch.lunch_break or {}
        if lunch_break.get("start") and lunch_break.get("end"):
            break_slots.append({
                "slot_type": "break",
                "break_type": "lunch",
                "label": "Lunch",
                "start": self._parse_time(lunch_break["start"]),
                "end": self._parse_time(lunch_break["end"]),
            })

        return sorted(break_slots, key=lambda slot: (slot["start"], slot["end"]))

    def _get_class_timeline_slots(self, class_obj: _Obj) -> List[Dict[str, Any]]:
        timeline = []
        for period_idx, (start, end) in enumerate(self._get_class_period_intervals(class_obj)):
            timeline.append({
                "slot_type": "period",
                "period_index": period_idx,
                "period": period_idx + 1,
                "start": start,
                "end": end,
            })

        timeline.extend(self._get_class_break_slots(class_obj))
        return sorted(
            timeline,
            key=lambda slot: (
                slot["start"],
                0 if slot.get("slot_type") == "break" else 1,
                slot["end"],
            )
        )

    def create_variables(self):
        """Creates boolean variables: X[subject, day, period]"""
        logger.info("Step 2/5: Creating decision variables...")

        class_timings = {self._id_str(c.id): self._get_class_period_intervals(c) for c in self.classes}
        faculty_map = {self._id_str(f.id): f for f in self.faculty}

        self.vars_by_faculty = {self._id_str(f.id): {d: [] for d in range(self.num_days)} for f in self.faculty}
        self.vars_by_subject = {}

        for subject in self.subjects:
            subject_faculty_id = self._id_str(subject.faculty_id)
            subject_class_id = self._id_str(subject.class_id)
            if subject_class_id in self.class_map:
                cls = self.class_map[subject_class_id]
                c_intervals = class_timings.get(self._id_str(cls.id), [])
            else:
                c_intervals = []

            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    if period >= len(c_intervals):
                        continue
                    start, end = c_intervals[period]
                    faculty = faculty_map.get(subject_faculty_id)
                    if faculty and self._is_faculty_unavailable(faculty, day, self.working_days[day], period, start, end):
                        continue

                    var_name = f"s{subject.id}_d{day}_p{period}"
                    var = self.model.NewBoolVar(var_name)
                    self.variables[var_name] = var

                    entry = {'start': start, 'end': end, 'var': var, 'period': period}
                    if subject_faculty_id in self.vars_by_faculty:
                        self.vars_by_faculty[subject_faculty_id][day].append(entry)

                    self.vars_by_subject.setdefault(subject.id, []).append(var)

        logger.info(f"Total decision variables created: {len(self.variables)}")

    def add_constraints(self):
        logger.info("Step 3/5: Adding constraints to the model...")

        # 1. Subject Requirements: sum(all subject vars) == hours_per_week
        for subject in self.subjects:
            all_sub_vars = self.vars_by_subject.get(subject.id, [])
            if all_sub_vars:
                self.model.Add(sum(all_sub_vars) == subject.hours_per_week)
        logger.debug("Added Subject Requirement constraints")

        # 2. Class Concurrency: Max 1 subject per class per period
        for class_obj in self.classes:
            class_subjects = [s for s in self.subjects if self._id_str(s.class_id) == self._id_str(class_obj.id)]
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    slot_vars = []
                    for sub in class_subjects:
                        key = f"s{sub.id}_d{day}_p{period}"
                        if key in self.variables:
                            slot_vars.append(self.variables[key])
                    if slot_vars:
                        self.model.Add(sum(slot_vars) <= 1)
        logger.debug("Added Class Concurrency constraints")

        # 3. RESOURCE CONFLICTS (Optimized)
        def add_overlap_constraints(allocations_map, entity_name):
            for entity_id, day_map in allocations_map.items():
                for day, entries in day_map.items():
                    if not entries:
                        continue

                    groups = {}
                    for e in entries:
                        key = (e['start'], e['end'])
                        if key not in groups:
                            groups[key] = []
                        groups[key].append(e['var'])

                    group_sums = []
                    for (start, end), vars_list in groups.items():
                        group_sums.append({'start': start, 'end': end, 'expr': sum(vars_list)})

                    if len(group_sums) == 1:
                        self.model.Add(group_sums[0]['expr'] <= 1)
                    else:
                        for i in range(len(group_sums)):
                            g1 = group_sums[i]
                            for j in range(i + 1, len(group_sums)):
                                g2 = group_sums[j]
                                if g1['start'] < g2['end'] and g2['start'] < g1['end']:
                                    self.model.Add(g1['expr'] + g2['expr'] <= 1)
                            self.model.Add(g1['expr'] <= 1)

        add_overlap_constraints(self.vars_by_faculty, "Faculty")
        logger.debug("Added Resource Conflict (Faculty) constraints")

        # 4. DEFAULT: Labs — all hours on ONE day, and consecutive within that day
        for sub in self.subjects:
            if not sub.requires_lab:
                continue

            hours = sub.hours_per_week or 1

            # is_lab_day[day] = 1 if this day is chosen for the lab session
            is_lab_day = [
                self.model.NewBoolVar(f"lab_day_s{sub.id}_d{day}")
                for day in range(self.num_days)
            ]
            # At most one lab day per week
            self.model.Add(sum(is_lab_day) <= 1)

            for day in range(self.num_days):
                period_vars = []
                for period in range(self.periods_per_day):
                    key = f"s{sub.id}_d{day}_p{period}"
                    period_vars.append(self.variables[key] if key in self.variables else None)

                valid_periods = [(p, v) for p, v in enumerate(period_vars) if v is not None]
                all_day_vars = [v for _, v in valid_periods]

                if not all_day_vars:
                    # No slots available this day → cannot be lab day
                    self.model.Add(is_lab_day[day] == 0)
                    continue

                total_daily = sum(all_day_vars)

                # If this IS the lab day → exactly `hours` slots must be scheduled
                self.model.Add(total_daily == hours * is_lab_day[day])

                # Consecutive-block enforcement:
                # Build presence vars per period index
                p_present = []
                for p in range(self.periods_per_day):
                    key = f"s{sub.id}_d{day}_p{p}"
                    if key in self.variables:
                        pv = self.model.NewBoolVar(f"pres_s{sub.id}_d{day}_p{p}")
                        self.model.Add(self.variables[key] == pv)
                        p_present.append(pv)
                    else:
                        p_present.append(None)

                # No gap between any two scheduled periods (contiguous block)
                for i in range(self.periods_per_day):
                    for k in range(i + 2, self.periods_per_day):
                        for j in range(i + 1, k):
                            vi = p_present[i]
                            vk = p_present[k]
                            vj = p_present[j]
                            if vi is None or vk is None or vj is None:
                                continue
                            # if i and k are both scheduled, j must also be scheduled
                            self.model.Add(vi + vk - vj <= 1)

        logger.debug("Added Default (Lab) consecutive + single-day constraints")

        # 5. CUSTOM CONSTRAINTS
        for constraint in self.custom_constraints:
            c_type = constraint.get("type")

            # ── faculty_availability ───────────────────────────────────────────
            if c_type == "faculty_availability":
                f_name = constraint.get("faculty_name", "")
                allowed_days = [d.lower() for d in constraint.get("available_days", []) if isinstance(d, str)]
                target_fac = self._find_faculty_by_name(f_name)
                if target_fac:
                    for day_idx, day_name in enumerate(self.working_days):
                        if day_name.lower() not in allowed_days:
                            entries = self.vars_by_faculty.get(self._id_str(target_fac.id), {}).get(day_idx, [])
                            for e in entries:
                                self.model.Add(e['var'] == 0)
                    logger.debug(f"Applied faculty_availability for '{f_name}'")
                else:
                    self._constraint_error(f"faculty_availability: faculty '{f_name}' not found in loaded data")

            # ── subject_max_per_day ────────────────────────────────────────────
            elif c_type == "subject_max_per_day":
                sub_name = str(constraint.get("subject_name", ""))
                max_pd = int(constraint.get("max_per_day", 1))
                matched_subjects = [sub for sub in self.subjects if self._matches_subject(sub_name, sub)]
                for sub in matched_subjects:
                    for day in range(self.num_days):
                        day_vars = [
                            self.variables[f"s{sub.id}_d{day}_p{p}"]
                            for p in range(self.periods_per_day)
                            if f"s{sub.id}_d{day}_p{p}" in self.variables
                        ]
                        if day_vars:
                            self.model.Add(sum(day_vars) <= max_pd)
                if matched_subjects:
                    logger.debug(f"Applied subject_max_per_day for '{sub_name}' (max={max_pd})")
                else:
                    self._constraint_error(f"subject_max_per_day: subject '{sub_name}' not found in loaded data")

            # ── preferred_time_slot ────────────────────────────────────────────
            elif c_type == "preferred_time_slot":
                target = str(constraint.get("target", ""))
                target_type = str(constraint.get("target_type", "subject")).lower()
                pref = str(constraint.get("preference", "morning")).lower()
                if constraint.get("soft"):
                    logger.debug(f"Skipped soft preferred_time_slot for '{target}' ({target_type}) -> {pref}")
                    continue
                half = self.periods_per_day // 2

                # Determine which periods to PREFER (soft: penalise non-preferred)
                # We implement this as a hard constraint to keep it simple & reliable
                if pref in {"morning", "first_half"}:
                    preferred_periods = set(range(0, half))
                else:  # afternoon / second_half
                    preferred_periods = set(range(half, self.periods_per_day))

                non_preferred = set(range(self.periods_per_day)) - preferred_periods

                matched_subjects = self._subjects_for_target(target, target_type)
                for sub in matched_subjects:
                    for day in range(self.num_days):
                        for p in non_preferred:
                            key = f"s{sub.id}_d{day}_p{p}"
                            if key in self.variables:
                                self.model.Add(self.variables[key] == 0)
                if matched_subjects:
                    logger.debug(f"Applied preferred_time_slot for '{target}' ({target_type}) -> {pref}")
                else:
                    self._constraint_error(f"preferred_time_slot: target '{target}' ({target_type}) not found in loaded data")

            # ── avoid_time_slot ────────────────────────────────────────────────
            elif c_type == "avoid_time_slot":
                target = str(constraint.get("target", ""))
                target_type = str(constraint.get("target_type", "class")).lower()
                blocked_periods = [int(p) - 1 for p in constraint.get("periods", [])]  # convert 1-indexed → 0-indexed

                matched_subjects = self._subjects_for_target(target, target_type)
                for sub in matched_subjects:
                    for day in range(self.num_days):
                        for p in blocked_periods:
                            if 0 <= p < self.periods_per_day:
                                key = f"s{sub.id}_d{day}_p{p}"
                                if key in self.variables:
                                    self.model.Add(self.variables[key] == 0)
                if matched_subjects:
                    logger.debug(f"Applied avoid_time_slot for '{target}' ({target_type}, periods={blocked_periods})")
                else:
                    self._constraint_error(f"avoid_time_slot: target '{target}' ({target_type}) not found in loaded data")

            # ── consecutive_periods ────────────────────────────────────────────
            elif c_type == "consecutive_periods":
                sub_type = str(constraint.get("subject_type", "lab")).strip().lower()
                matched_count = 0
                for sub in self.subjects:
                    matches = False
                    if sub_type == "lab" and sub.requires_lab:
                        matches = True
                    elif self._matches_subject(sub_type, sub):
                        matches = True
                    
                    if matches:
                        matched_count += 1
                        for day in range(self.num_days):
                            p_present = []
                            for p in range(self.periods_per_day):
                                key = f"s{sub.id}_d{day}_p{p}"
                                if key in self.variables:
                                    pv = self.model.NewBoolVar(f"custom_pres_s{sub.id}_d{day}_p{p}")
                                    self.model.Add(self.variables[key] == pv)
                                    p_present.append(pv)
                                else:
                                    p_present.append(None)
                            
                            for i in range(self.periods_per_day):
                                for k in range(i + 2, self.periods_per_day):
                                    for j in range(i + 1, k):
                                        vi = p_present[i]
                                        vk = p_present[k]
                                        vj = p_present[j]
                                        if vi is not None and vk is not None and vj is not None:
                                            self.model.Add(vi + vk - vj <= 1)
                if matched_count:
                    logger.debug(f"Applied consecutive_periods for type '{sub_type}'")
                else:
                    self._constraint_error(f"consecutive_periods: subject type '{sub_type}' not found in loaded data")

            # ── class_gap ──────────────────────────────────────────────────────
            elif c_type == "class_gap":
                cls_name = str(constraint.get("class_name", ""))
                min_gap = int(constraint.get("min_gap", 1))
                matched_classes = [cls for cls in self.classes if self._matches_class(cls_name, cls)]
                for cls in matched_classes:
                    cls_subjects = [s for s in self.subjects if self._id_str(s.class_id) == self._id_str(cls.id)]
                    for day in range(self.num_days):
                        class_slot_vars = []
                        for p in range(self.periods_per_day):
                            slot_vars = [
                                self.variables[f"s{sub.id}_d{day}_p{p}"]
                                for sub in cls_subjects
                                if f"s{sub.id}_d{day}_p{p}" in self.variables
                            ]
                            class_slot_vars.append(slot_vars)

                        for p in range(self.periods_per_day):
                            for gap in range(1, min_gap + 1):
                                p_next = p + gap
                                if p_next < self.periods_per_day and class_slot_vars[p] and class_slot_vars[p_next]:
                                    self.model.Add(sum(class_slot_vars[p]) + sum(class_slot_vars[p_next]) <= 1)
                if matched_classes:
                    logger.debug(f"Applied class_gap for class '{cls_name}' (min_gap={min_gap})")
                else:
                    self._constraint_error(f"class_gap: class '{cls_name}' not found in loaded data")

            # ── specific_time_slot ─────────────────────────────────────────────
            elif c_type == "specific_time_slot":
                target = str(constraint.get("target", ""))
                target_type = str(constraint.get("target_type", "subject")).lower()
                period_num = constraint.get("period")
                if period_num is not None:
                    p_idx = int(period_num) - 1
                    day_name = constraint.get("day")
                    matched_subjects = self._subjects_for_target(target, target_type)
                    for sub in matched_subjects:
                        sub_vars = []
                        for day_idx in range(self.num_days):
                            if day_name and self.working_days[day_idx].lower() != day_name.lower():
                                continue
                            if 0 <= p_idx < self.periods_per_day:
                                key = f"s{sub.id}_d{day_idx}_p{p_idx}"
                                if key in self.variables:
                                    sub_vars.append(self.variables[key])
                        if sub_vars:
                            self.model.Add(sum(sub_vars) >= 1)
                    if matched_subjects:
                        logger.debug(f"Applied specific_time_slot for '{target}' ({target_type}, period={period_num}, day={day_name})")
                    else:
                        self._constraint_error(f"specific_time_slot: target '{target}' ({target_type}) not found in loaded data")

            else:
                self._constraint_error(f"Unsupported AI constraint type: '{c_type}'")



    def _add_distribution_objective(self):
        """
        Soft objective: minimise variance of theory-subject slots across days.
        Implemented by minimising the maximum daily theory-load minus the minimum.
        This encourages even spreading of theory subjects across the week.
        """
        theory_daily_load = []  # one IntVar per day
        for day in range(self.num_days):
            day_vars = []
            for sub in self.subjects:
                if not sub.requires_lab:  # only theory subjects
                    for period in range(self.periods_per_day):
                        key = f"s{sub.id}_d{day}_p{period}"
                        if key in self.variables:
                            day_vars.append(self.variables[key])
            if day_vars:
                load_var = self.model.NewIntVar(0, len(day_vars), f"load_day{day}")
                self.model.Add(load_var == sum(day_vars))
                theory_daily_load.append(load_var)

        penalty_terms = []
        for sub in self.subjects:
            c = sub.credits if sub.credits is not None else 3
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    key = f"s{sub.id}_d{day}_p{period}"
                    if key in self.variables:
                        penalty_terms.append(self.variables[key] * c * period)

        morning_penalty = sum(penalty_terms) if penalty_terms else 0

        if len(theory_daily_load) >= 2:
            max_load = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "max_load")
            min_load = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "min_load")
            self.model.AddMaxEquality(max_load, theory_daily_load)
            self.model.AddMinEquality(min_load, theory_daily_load)
            spread = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "spread")
            self.model.Add(spread == max_load - min_load)
            
            # Combine objectives: Prioritize even spread heavily, then morning priority
            self.model.Minimize(spread * 1000 + morning_penalty)
            logger.debug("Added even distribution and morning-priority objectives")
        else:
            self.model.Minimize(morning_penalty)
            logger.debug("Added morning-priority objective")

    def solve(self) -> Dict[str, Any]:
        logger.info(f"Step 4/5: Solving model (Time Limit: {self.time_limit_seconds}s)...")
        self._add_distribution_objective()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = 8
        solver.parameters.log_search_progress = True

        start_time = time.time()
        status = solver.Solve(self.model)
        duration = time.time() - start_time
        logger.info(f"Step 5/5: Solver finished in {duration:.2f}s with status: {solver.StatusName(status)}")
        logger.info(f"Solver Statistics: Conflicts: {solver.NumConflicts()}, Branches: {solver.NumBranches()}, WallTime: {solver.WallTime()}s")

        status_map = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
                      cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID",
                      cp_model.UNKNOWN: "UNKNOWN"}

        result = {
            "status": status_map.get(status, "UNKNOWN"),
            "schedule": None,
            "solve_time": solver.WallTime()
        }
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result["schedule"] = self.extract_schedule(solver)
        return result

    def extract_schedule(self, solver: cp_model.CpSolver) -> Dict[str, Any]:
        schedule = {}
        for class_obj in self.classes:
            timeline_slots = self._get_class_timeline_slots(class_obj)
            batch = class_obj._doc.get("_batch_obj")
            dept_name = next((d.name for d in self.departments if d.id == class_obj.department_id), "")

            class_schedule = {
                "class_id": class_obj.id,
                "class_name": f"{class_obj.name} {class_obj.section or ''}",
                "department": dept_name,
                "batch_name": batch.name if batch else "Default",
                "timetable": {}
            }

            class_subjects = [s for s in self.subjects if self._id_str(s.class_id) == self._id_str(class_obj.id)]

            for day_idx, day_name in enumerate(self.working_days):
                day_schedule = []
                for timeline_slot in timeline_slots:
                    if timeline_slot.get("slot_type") == "break":
                        day_schedule.append({
                            "slot_type": "break",
                            "break_type": timeline_slot.get("break_type", "break"),
                            "label": timeline_slot.get("label", "Break"),
                            "period": None,
                            "time": self._format_time_range(timeline_slot["start"], timeline_slot["end"]),
                            "subject": None,
                        })
                        continue

                    p_idx = timeline_slot["period_index"]
                    slot_info = {
                        "slot_type": "period",
                        "period": p_idx + 1,
                        "time": self._format_time_range(timeline_slot["start"], timeline_slot["end"]),
                        "subject": None
                    }

                    for sub in class_subjects:
                        key = f"s{sub.id}_d{day_idx}_p{p_idx}"
                        if key in self.variables and solver.Value(self.variables[key]) == 1:
                            faculty_name = "TBA"
                            if sub.faculty_id:
                                fac = next((f for f in self.faculty if self._id_str(f.id) == self._id_str(sub.faculty_id)), None)
                                if fac:
                                    faculty_name = fac.name

                            slot_info.update({
                                "subject": sub.name,
                                "subject_code": sub.code,
                                "faculty": faculty_name,
                                "is_lab": sub.requires_lab
                            })
                            break
                    day_schedule.append(slot_info)
                class_schedule["timetable"][day_name] = day_schedule

            schedule[f"class_{class_obj.id}"] = class_schedule
        return schedule

    def _validate_custom_constraints_against_schedule(self, schedule: Dict[str, Any]) -> List[str]:
        errors = []
        for constraint in self.custom_constraints:
            c_type = constraint.get("type")

            if c_type == "faculty_availability":
                faculty_name = str(constraint.get("faculty_name", ""))
                allowed_days = {
                    str(day).lower()
                    for day in constraint.get("available_days", [])
                    if isinstance(day, str)
                }
                if not faculty_name or not allowed_days:
                    continue

                for class_schedule in schedule.values():
                    for day_name, slots in class_schedule.get("timetable", {}).items():
                        if day_name.lower() in allowed_days:
                            continue
                        for slot in slots:
                            slot_faculty = slot.get("faculty")
                            if slot.get("subject") and self._matches_text(faculty_name, slot_faculty):
                                errors.append(
                                    f"faculty_availability violated: {slot_faculty} is scheduled for "
                                    f"{slot.get('subject')} in {class_schedule.get('class_name')} on {day_name}, "
                                    f"but allowed days are {', '.join(constraint.get('available_days', []))}."
                                )

            elif c_type == "faculty_unavailability":
                faculty_name = str(constraint.get("faculty_name", ""))
                unavailable_days = {
                    str(day).lower()
                    for day in constraint.get("unavailable_days", [])
                    if isinstance(day, str)
                }
                if not faculty_name or not unavailable_days:
                    continue

                for class_schedule in schedule.values():
                    for day_name, slots in class_schedule.get("timetable", {}).items():
                        if day_name.lower() not in unavailable_days:
                            continue
                        for slot in slots:
                            slot_faculty = slot.get("faculty")
                            if slot.get("subject") and self._matches_text(faculty_name, slot_faculty):
                                errors.append(
                                    f"faculty_unavailability violated: {slot_faculty} is scheduled for "
                                    f"{slot.get('subject')} in {class_schedule.get('class_name')} on {day_name}."
                                )

        return errors

    def _auto_assign_faculty_to_unassigned_subjects(self) -> Tuple[List[Tuple[_Obj, str]], List[_Obj]]:
        """
        Greedy in-memory assignment of faculty to subjects that lack a `faculty_id`.
        Respects faculty `max_hours_per_week` and basic availability estimation.
        Returns: (auto_assigned list of (subject, faculty_name), failed_subjects list)
        """
        auto_assigned = []
        failed = []

        # Build faculty pools by department
        fac_by_dept = {}
        assigned_hours = {}
        for f in self.faculty:
            dep = getattr(f, 'department_id', None)
            fac_by_dept.setdefault(dep, []).append(f)
            assigned_hours[self._id_str(f.id)] = 0

        # Count already assigned hours for faculties
        for s in self.subjects:
            if s.faculty_id:
                fid = self._id_str(s.faculty_id)
                assigned_hours[fid] = assigned_hours.get(fid, 0) + (s.hours_per_week or 0)

        # Subjects that need faculty
        unassigned = [s for s in self.subjects if not s.faculty_id]
        # Sort by hours desc to assign heavy subjects first
        unassigned.sort(key=lambda x: -(x.hours_per_week or 0))

        for subj in unassigned:
            # Prefer faculty from same department of the subject's class
            class_obj = self.class_map.get(self._id_str(subj.class_id))
            preferred_dept = None
            if class_obj:
                preferred_dept = getattr(class_obj, 'department_id', None)

            candidates = []
            if preferred_dept in fac_by_dept:
                candidates = fac_by_dept[preferred_dept][:]
            else:
                # fallback to any faculty
                candidates = [f for f in self.faculty]

            # Filter by capacity (max_hours)
            viable = []
            need = subj.hours_per_week or 0
            for f in candidates:
                fid = self._id_str(f.id)
                max_h = getattr(f, 'max_hours_per_week', None) or 0
                if assigned_hours.get(fid, 0) + need <= max_h:
                    # Basic availability check: count potential slots across class timelines
                    # Estimate available slots as total class slots minus faculty unavailability overlaps
                    total_potential = 0
                    # For subjects mapped to a class, calculate available period slots for that class
                    if subj.class_id and subj.class_id in self.class_map:
                        cls = self.class_map[self._id_str(subj.class_id)]
                        intervals = self._get_class_period_intervals(cls)
                        for day_idx, day_name in enumerate(self.working_days):
                            for p_idx, (start, end) in enumerate(intervals):
                                if not self._is_faculty_unavailable(f, day_idx, day_name, p_idx, start, end):
                                    total_potential += 1
                    else:
                        # conservatively allow
                        total_potential = need

                    if total_potential >= need:
                        viable.append((f, max_h - assigned_hours.get(fid, 0)))

            if not viable:
                failed.append(subj)
                continue

            # pick candidate with largest remaining capacity
            viable.sort(key=lambda x: -x[1])
            chosen = viable[0][0]
            # assign in-memory
            subj._doc['faculty_id'] = ObjectId(chosen.id) if ObjectId.is_valid(chosen.id) else chosen.id
            assigned_hours[self._id_str(chosen.id)] = assigned_hours.get(self._id_str(chosen.id), 0) + need
            auto_assigned.append((subj, chosen.name, self._id_str(chosen.id)))

        return auto_assigned, failed

    def generate_schedule(self, department_ids: Optional[List[str]] = None, batch_ids: Optional[List[str]] = None, class_ids: Optional[List[str]] = None, faculty_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        data_summary = self.load_data(department_ids, batch_ids, class_ids, faculty_ids)
        self._sync_periods_per_day_to_batch_timings()
        if not self.classes or not self.subjects:
            msg = "No classes found." if not self.classes else "Found Classes, but NO Subjects are assigned to them.\nHint: Go to 'Mapping' and assign your Global Subjects to these Classes."
            return {"status": "ERROR", "message": msg, "data_summary": data_summary}
        # VALIDATION: Ensure every subject has a Class mapped; try to auto-assign Faculty where missing.
        missing_mappings = []
        for sub in self.subjects:
            issues = []
            if not sub.class_id:
                issues.append("Missing Class")
            if not sub.faculty_id:
                issues.append("Missing Faculty")
            if issues:
                missing_mappings.append((sub, issues))

        # If some subjects are missing faculty, attempt an in-memory auto-assignment.
        if any("Missing Faculty" in issues for _, issues in missing_mappings):
            auto_assigned, failed = self._auto_assign_faculty_to_unassigned_subjects()
            if auto_assigned:
                logger.info(f"Auto-assigned faculty for {len(auto_assigned)} subjects")
                # Update data_summary with info
                data_summary["auto_assigned_subjects"] = [f"{s.name} -> {f_name}" for s, f_name, _ in auto_assigned]
                # Persist assignments to DB so mappings appear in UI
                for subj, _, fac_id in auto_assigned:
                    try:
                        sid = ObjectId(subj.id) if ObjectId.is_valid(subj.id) else subj.id
                        fid = ObjectId(fac_id) if ObjectId.is_valid(fac_id) else fac_id
                        self.db["subjects"].update_one({"_id": sid}, {"$set": {"faculty_id": fid}})
                    except Exception:
                        logger.exception(f"Failed to persist auto-assignment for subject {subj.id}")

            if failed:
                # Build clear error list for subjects still lacking mapping
                missing_list = [f"{s.name} ({s.code}): Missing Faculty" for s in failed]
                msg = "Could not auto-assign faculty for the following subjects. Please assign faculty manually before generating a timetable:\n" + "\n".join(missing_list)
                logger.warning(msg)
                return {"status": "ERROR", "message": msg, "data_summary": data_summary}

        # VALIDATION 2: Class Workload vs Available Slots
        overloaded_classes = []
        for class_obj in self.classes:
            class_subjects = [s for s in self.subjects if self._id_str(s.class_id) == self._id_str(class_obj.id)]
            total_hours = sum(s.hours_per_week for s in class_subjects)
            total_slots = self.num_days * len(self._get_class_period_intervals(class_obj))
            if total_hours > total_slots:
                overloaded_classes.append(f"{class_obj.name}: Requires {total_hours} slots, but only {total_slots} available.")

        if overloaded_classes:
            return {
                "status": "ERROR",
                "message": f"Impossible Schedule (Class Overload):\n" + "\n".join(overloaded_classes),
                "data_summary": data_summary
            }

        # VALIDATION 3: Faculty Workload vs Max Hours
        overloaded_faculty = []
        for fac in self.faculty:
            fac_subjects = [s for s in self.subjects if self._id_str(s.faculty_id) == self._id_str(fac.id)]
            total_assigned_hours = sum(s.hours_per_week for s in fac_subjects)
            if total_assigned_hours > fac.max_hours_per_week:
                overloaded_faculty.append(f"{fac.name}: Assigned {total_assigned_hours} hrs, Max is {fac.max_hours_per_week}.")

        if overloaded_faculty:
            return {
                "status": "ERROR",
                "message": f"Impossible Schedule (Faculty Overload):\n" + "\n".join(overloaded_faculty),
                "data_summary": data_summary
            }

        self.create_variables()
        self.add_constraints()
        if self.constraint_errors:
            return {
                "status": "ERROR",
                "message": "AI constraint errors:\n" + "\n".join(self.constraint_errors),
                "data_summary": data_summary,
                "effective_periods_per_day": self.periods_per_day,
            }
        result = self.solve()
        if result.get("schedule"):
            schedule_errors = self._validate_custom_constraints_against_schedule(result["schedule"])
            if schedule_errors:
                return {
                    "status": "ERROR",
                    "message": "Generated timetable violates AI constraints:\n" + "\n".join(schedule_errors),
                    "data_summary": data_summary,
                    "effective_periods_per_day": self.periods_per_day,
                }
        result["data_summary"] = data_summary
        result["effective_periods_per_day"] = self.periods_per_day
        return result
