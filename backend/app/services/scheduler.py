from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId
import time
import logging
from datetime import datetime, timedelta

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
        self.model = cp_model.CpModel()
        self.variables = {}  # Map: "s{subject_id}_d{day_index}_p{period_index}" -> BoolVar

        # Optimization Caches
        self.vars_by_faculty = {}  # faculty_id -> day -> list of {'start', 'end', 'var', 'period'}
        self.vars_by_subject = {}  # subject_id -> list of BoolVar

    def _wrap(self, doc: dict) -> _Obj:
        return _Obj(doc)

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
        self.class_map = {c.id: c for c in self.classes}

        # Subjects (linked to loaded classes)
        if loaded_class_ids:
            self.subjects = [self._wrap(d) for d in self.db["subjects"].find({"class_id": {"$in": loaded_class_ids}})]
        else:
            self.subjects = []

        # Faculty
        assigned_faculty_ids = {s.faculty_id for s in self.subjects if s.faculty_id}
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
        target_name = target_name.strip().lower()
        tokens = [token for token in target_name.split() if token]
        for fac in self.faculty:
            faculty_name = str(fac.name or "").strip().lower()
            if target_name == faculty_name or target_name in faculty_name or faculty_name in target_name:
                return fac
            if tokens and all(token in faculty_name for token in tokens):
                return fac
        return None

    def _get_class_period_intervals(self, class_obj: _Obj) -> List[Tuple[int, int]]:
        """
        Returns a list of (start_minute, end_minute) for each period of the day for this class.
        Based on the class's Batch configuration.
        """
        batch = class_obj._doc.get("_batch_obj")
        if not batch:
            # Fallback if no batch assigned: Simple uniform 60min slots starting 09:00
            start = 9 * 60
            intervals = []
            for _ in range(self.periods_per_day):
                intervals.append((start, start + 60))
                start += 60
            return intervals

        current_time = self._parse_time(batch.start_time)
        period_duration = batch.period_duration or 60

        # Pre-process breaks for easier lookup (start_min -> end_min)
        breaks_map = {}
        if batch.break_times:
            for b in batch.break_times:
                b_start = self._parse_time(b['start'])
                b_end = self._parse_time(b['end'])
                breaks_map[b_start] = b_end - b_start

        if batch.lunch_break:
            l_start = self._parse_time(batch.lunch_break['start'])
            l_end = self._parse_time(batch.lunch_break['end'])
            breaks_map[l_start] = l_end - l_start

        intervals = []
        for _ in range(self.periods_per_day):
            if current_time in breaks_map:
                current_time += breaks_map[current_time]

            p_start = current_time
            p_end = p_start + period_duration
            intervals.append((p_start, p_end))
            current_time = p_end

        return intervals

    def create_variables(self):
        """Creates boolean variables: X[subject, day, period]"""
        logger.info("Step 2/5: Creating decision variables...")

        class_timings = {c.id: self._get_class_period_intervals(c) for c in self.classes}
        faculty_map = {f.id: f for f in self.faculty}

        self.vars_by_faculty = {f.id: {d: [] for d in range(self.num_days)} for f in self.faculty}
        self.vars_by_subject = {}

        for subject in self.subjects:
            if subject.class_id in self.class_map:
                cls = self.class_map[subject.class_id]
                c_intervals = class_timings.get(cls.id, [])
            else:
                c_intervals = []

            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    if period >= len(c_intervals):
                        continue
                    start, end = c_intervals[period]
                    faculty = faculty_map.get(subject.faculty_id)
                    if faculty and self._is_faculty_unavailable(faculty, day, self.working_days[day], period, start, end):
                        continue

                    var_name = f"s{subject.id}_d{day}_p{period}"
                    var = self.model.NewBoolVar(var_name)
                    self.variables[var_name] = var

                    entry = {'start': start, 'end': end, 'var': var, 'period': period}
                    if subject.faculty_id in self.vars_by_faculty:
                        self.vars_by_faculty[subject.faculty_id][day].append(entry)

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
            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]
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
                            entries = self.vars_by_faculty.get(target_fac.id, {}).get(day_idx, [])
                            for e in entries:
                                self.model.Add(e['var'] == 0)
                    logger.debug(f"Applied faculty_availability for '{f_name}'")
                else:
                    logger.warning(f"faculty_availability: faculty '{f_name}' not found in loaded data")

            # ── subject_max_per_day ────────────────────────────────────────────
            elif c_type == "subject_max_per_day":
                sub_name = str(constraint.get("subject_name", "")).strip().lower()
                max_pd = int(constraint.get("max_per_day", 1))
                for sub in self.subjects:
                    if str(sub.name or "").strip().lower() == sub_name or sub_name in str(sub.name or "").strip().lower():
                        for day in range(self.num_days):
                            day_vars = [
                                self.variables[f"s{sub.id}_d{day}_p{p}"]
                                for p in range(self.periods_per_day)
                                if f"s{sub.id}_d{day}_p{p}" in self.variables
                            ]
                            if day_vars:
                                self.model.Add(sum(day_vars) <= max_pd)
                logger.debug(f"Applied subject_max_per_day for '{sub_name}' (max={max_pd})")

            # ── preferred_time_slot ────────────────────────────────────────────
            elif c_type == "preferred_time_slot":
                target = str(constraint.get("target", "")).strip().lower()
                pref = str(constraint.get("preference", "morning")).lower()
                half = self.periods_per_day // 2

                # Determine which periods to PREFER (soft: penalise non-preferred)
                # We implement this as a hard constraint to keep it simple & reliable
                if pref in {"morning", "first_half"}:
                    preferred_periods = set(range(0, half))
                else:  # afternoon / second_half
                    preferred_periods = set(range(half, self.periods_per_day))

                non_preferred = set(range(self.periods_per_day)) - preferred_periods

                for sub in self.subjects:
                    if target in str(sub.name or "").strip().lower():
                        for day in range(self.num_days):
                            for p in non_preferred:
                                key = f"s{sub.id}_d{day}_p{p}"
                                if key in self.variables:
                                    self.model.Add(self.variables[key] == 0)
                logger.debug(f"Applied preferred_time_slot for '{target}' → {pref}")

            # ── avoid_time_slot ────────────────────────────────────────────────
            elif c_type == "avoid_time_slot":
                target = str(constraint.get("target", "")).strip().lower()
                target_type = str(constraint.get("target_type", "class")).lower()
                blocked_periods = [int(p) - 1 for p in constraint.get("periods", [])]  # convert 1-indexed → 0-indexed

                if target_type == "class":
                    for cls in self.classes:
                        if target in str(cls.name or "").strip().lower():
                            cls_subjects = [s for s in self.subjects if s.class_id == cls.id]
                            for sub in cls_subjects:
                                for day in range(self.num_days):
                                    for p in blocked_periods:
                                        if 0 <= p < self.periods_per_day:
                                            key = f"s{sub.id}_d{day}_p{p}"
                                            if key in self.variables:
                                                self.model.Add(self.variables[key] == 0)
                elif target_type == "subject":
                    for sub in self.subjects:
                        if target in str(sub.name or "").strip().lower():
                            for day in range(self.num_days):
                                for p in blocked_periods:
                                    if 0 <= p < self.periods_per_day:
                                        key = f"s{sub.id}_d{day}_p{p}"
                                        if key in self.variables:
                                            self.model.Add(self.variables[key] == 0)
                logger.debug(f"Applied avoid_time_slot for '{target}' (periods={blocked_periods})")

            # ── consecutive_periods ────────────────────────────────────────────
            elif c_type == "consecutive_periods":
                sub_type = str(constraint.get("subject_type", "lab")).strip().lower()
                for sub in self.subjects:
                    matches = False
                    if sub_type == "lab" and sub.requires_lab:
                        matches = True
                    elif sub_type in str(sub.name or "").strip().lower() or sub_type in str(sub.code or "").strip().lower():
                        matches = True
                    
                    if matches:
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
                logger.debug(f"Applied consecutive_periods for type '{sub_type}'")

            # ── class_gap ──────────────────────────────────────────────────────
            elif c_type == "class_gap":
                cls_name = str(constraint.get("class_name", "")).strip().lower()
                min_gap = int(constraint.get("min_gap", 1))
                for cls in self.classes:
                    if cls_name in str(cls.name or "").strip().lower():
                        cls_subjects = [s for s in self.subjects if s.class_id == cls.id]
                        for sub in cls_subjects:
                            for day in range(self.num_days):
                                for p in range(self.periods_per_day):
                                    for gap in range(1, min_gap + 1):
                                        p_next = p + gap
                                        if p_next < self.periods_per_day:
                                            key1 = f"s{sub.id}_d{day}_p{p}"
                                            key2 = f"s{sub.id}_d{day}_p{p_next}"
                                            if key1 in self.variables and key2 in self.variables:
                                                self.model.Add(self.variables[key1] + self.variables[key2] <= 1)
                logger.debug(f"Applied class_gap for class '{cls_name}' (min_gap={min_gap})")



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

        if len(theory_daily_load) >= 2:
            max_load = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "max_load")
            min_load = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "min_load")
            self.model.AddMaxEquality(max_load, theory_daily_load)
            self.model.AddMinEquality(min_load, theory_daily_load)
            spread = self.model.NewIntVar(0, self.periods_per_day * len(self.subjects), "spread")
            self.model.Add(spread == max_load - min_load)
            self.model.Minimize(spread)
            logger.debug("Added even distribution objective (minimise daily load spread)")

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
            intervals = self._get_class_period_intervals(class_obj)
            batch = class_obj._doc.get("_batch_obj")
            dept_name = next((d.name for d in self.departments if d.id == class_obj.department_id), "")

            class_schedule = {
                "class_id": class_obj.id,
                "class_name": f"{class_obj.name} {class_obj.section or ''}",
                "department": dept_name,
                "batch_name": batch.name if batch else "Default",
                "timetable": {}
            }

            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]

            for day_idx, day_name in enumerate(self.working_days):
                day_schedule = []
                for p_idx in range(self.periods_per_day):
                    slot_info = {
                        "period": p_idx + 1,
                        "time": f"{intervals[p_idx][0]//60:02d}:{intervals[p_idx][0]%60:02d} - {intervals[p_idx][1]//60:02d}:{intervals[p_idx][1]%60:02d}",
                        "subject": None
                    }

                    for sub in class_subjects:
                        key = f"s{sub.id}_d{day_idx}_p{p_idx}"
                        if key in self.variables and solver.Value(self.variables[key]) == 1:
                            faculty_name = "TBA"
                            if sub.faculty_id:
                                fac = next((f for f in self.faculty if f.id == sub.faculty_id), None)
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

    def generate_schedule(self, department_ids: Optional[List[str]] = None, batch_ids: Optional[List[str]] = None, class_ids: Optional[List[str]] = None, faculty_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        data_summary = self.load_data(department_ids, batch_ids, class_ids, faculty_ids)
        if not self.classes or not self.subjects:
            msg = "No classes found." if not self.classes else "Found Classes, but NO Subjects are assigned to them.\nHint: Go to 'Mapping' and assign your Global Subjects to these Classes."
            return {"status": "ERROR", "message": msg, "data_summary": data_summary}

        # VALIDATION: Ensure every subject has a Faculty and Class mapped
        missing_mappings = []
        for sub in self.subjects:
            issues = []
            if not sub.class_id:
                issues.append("Missing Class")
            if not sub.faculty_id:
                issues.append("Missing Faculty")
            if issues:
                missing_mappings.append(f"{sub.name} ({sub.code}): {', '.join(issues)}")

        if missing_mappings:
            logger.warning(f"Data Mapping Warning:\n" + "\n".join(missing_mappings))

        # VALIDATION 2: Class Workload vs Available Slots
        total_slots = self.num_days * self.periods_per_day
        overloaded_classes = []
        for class_obj in self.classes:
            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]
            total_hours = sum(s.hours_per_week for s in class_subjects)
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
            fac_subjects = [s for s in self.subjects if s.faculty_id == fac.id]
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
        result = self.solve()
        result["data_summary"] = data_summary
        return result
