from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.timetable import Department, Class, Subject, Faculty, Room, Batch
import time
import logging
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TimetableScheduler:
    def __init__(self, db: Session, working_days: List[str], periods_per_day: int, time_limit_seconds: int = 60, custom_constraints: List[Dict[str, Any]] = None):
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
        self.rooms = []
        
        # OR-Tools
        self.model = cp_model.CpModel()
        self.model = cp_model.CpModel()
        self.variables = {} # Map: "s{subject_id}_d{day_index}_p{period_index}_r{room_id}" -> BoolVar
        
        # Optimization Caches
        self.vars_by_room = {}   # room_id -> day -> list of {'start', 'end', 'var', 'period'}
        self.vars_by_faculty = {} # faculty_id -> day -> list of {'start', 'end', 'var'}
        self.vars_by_subject_room = {} # (subject_id, room_id) -> list of vars

    def load_data(self, department_ids: Optional[List[int]] = None, batch_ids: Optional[List[int]] = None, class_ids: Optional[List[int]] = None, faculty_ids: Optional[List[int]] = None):
        """Loads all necessary data from DB."""
        logger.info("Step 1/5: Loading data from database...")
        # Departments
        query = self.db.query(Department)
        if department_ids:
            query = query.filter(Department.id.in_(department_ids))
        self.departments = query.all()
        dept_ids = [d.id for d in self.departments]

        # Batches
        b_query = self.db.query(Batch)
        if batch_ids:
            b_query = b_query.filter(Batch.id.in_(batch_ids))
        self.batches = b_query.all()
        
        # Classes
        c_query = self.db.query(Class)
        if class_ids:
            c_query = c_query.filter(Class.id.in_(class_ids))
        # Also filter by departments if provided (and if classes linked to dept)
        if dept_ids:
             c_query = c_query.filter(Class.department_id.in_(dept_ids))
        self.classes = c_query.all()
        self.classes = c_query.all()
        # Re-derive class_ids from actual loaded classes to ensure subject filtering matches
        loaded_class_ids = [c.id for c in self.classes]
        # Fast lookup for capacity checks
        self.class_map = {c.id: c for c in self.classes}
        
        # Subjects
        s_query = self.db.query(Subject)
        # Filter subjects that belong to the loaded classes
        s_query = s_query.filter(Subject.class_id.in_(loaded_class_ids))
        self.subjects = s_query.all()
        
        # Faculty
        # Fix: Load ANY faculty that is assigned to the loaded subjects, 
        # plus any faculty belonging to the selected departments (optional, but good for completeness)
        f_query = self.db.query(Faculty)
        
        # Collect all faculty IDs referenced by the loaded subjects
        assigned_faculty_ids = {s.faculty_id for s in self.subjects if s.faculty_id}
        
        if faculty_ids:
             # If specific faculty requested (not usual flow, but supported)
             all_ids = set(faculty_ids) | assigned_faculty_ids
             f_query = f_query.filter(Faculty.id.in_(all_ids))
        elif dept_ids:
             # Standard flow: Load Dept faculty + any external faculty mapped to these subjects
             f_query = f_query.filter(
                 (Faculty.department_id.in_(dept_ids)) | 
                 (Faculty.id.in_(assigned_faculty_ids))
             )
        
        self.faculty = f_query.all()
        
        # Rooms
        self.rooms = self.db.query(Room).all()

        summary = {
            "departments": len(self.departments), "batches": len(self.batches),
            "classes": len(self.classes), "subjects": len(self.subjects),
            "faculty": len(self.faculty), "rooms": len(self.rooms)
        }
        logger.info(f"Data Loaded: {summary}")
        return summary

    def _parse_time(self, time_str: str) -> int:
        """Converts HH:MM string to minutes from midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _get_class_period_intervals(self, class_obj: Class) -> List[Tuple[int, int]]:
        """
        Returns a list of (start_minute, end_minute) for each period of the day for this class.
        Based on the class's Batch configuration.
        """
        if not class_obj.batch:
            # Fallback if no batch assigned: Simple uniform 60min slots starting 09:00
            start = 9 * 60
            intervals = []
            for _ in range(self.periods_per_day):
                intervals.append((start, start + 60))
                start += 60
            return intervals

        batch = class_obj.batch
        current_time = self._parse_time(batch.start_time)
        period_duration = batch.period_duration
        
        # Pre-process breaks for easier lookup (start_min -> end_min)
        breaks_map = {} # start_time_min -> duration
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
            # Check if current_time is a break start
            if current_time in breaks_map:
                current_time += breaks_map[current_time] # Skip break
            
            # Additional check: some breaks might not align perfectly, but let's assume valid config for now
            # or check if current_time is INSIDE a break (simplified logic here)
            
            p_start = current_time
            p_end = p_start + period_duration
            intervals.append((p_start, p_end))
            current_time = p_end
            
        return intervals

    def create_variables(self):
        """Creates boolean variables: X[subject, day, period, room]"""
        logger.info("Step 2/5: Creating decision variables...")
        
        # Pre-fetch class timings to avoid repeated lookups
        class_timings = {c.id: self._get_class_period_intervals(c) for c in self.classes}
        
        # Initialize caches
        # room -> day -> list
        self.vars_by_room = {r.id: {d: [] for d in range(self.num_days)} for r in self.rooms}
        # faculty -> day -> list
        self.vars_by_faculty = {f.id: {d: [] for d in range(self.num_days)} for f in self.faculty}
        # (sub, room) -> list
        self.vars_by_subject_room = {} 

        for subject in self.subjects:
            # Check capacity once per subject/room
            params_by_room = {}
            if subject.class_id in self.class_map:
                 cls = self.class_map[subject.class_id]
                 c_intervals = class_timings.get(cls.id, [])
            else:
                 c_intervals = [] # Should not happen if data consistent

            valid_rooms = []
            for room in self.rooms:
                # Type check
                if subject.requires_lab and room.room_type != 'lab': continue
                if not subject.requires_lab and room.room_type == 'lab': continue
                # Capacity check
                if cls.student_count and room.capacity < cls.student_count: continue
                valid_rooms.append(room)
                self.vars_by_subject_room[(subject.id, room.id)] = []

            if not valid_rooms:
                continue

            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    if period >= len(c_intervals): continue
                    start, end = c_intervals[period]
                    
                    for room in valid_rooms:
                        var_name = f"s{subject.id}_d{day}_p{period}_r{room.id}"
                        var = self.model.NewBoolVar(var_name)
                        self.variables[var_name] = var
                        
                        # Populate caches
                        entry = {'start': start, 'end': end, 'var': var, 'period': period}
                        
                        self.vars_by_room[room.id][day].append(entry)
                        
                        if subject.faculty_id:
                            # Note: Faculty cache needs to be initialized if faculty not in self.faculty list?
                            # load_data ensures self.faculty contains all assigned.
                            if subject.faculty_id in self.vars_by_faculty:
                                self.vars_by_faculty[subject.faculty_id][day].append(entry)
                        
                        self.vars_by_subject_room[(subject.id, room.id)].append(var)

        logger.info(f"Total decision variables created: {len(self.variables)}")

    def add_constraints(self):
        logger.info("Step 3/5: Adding constraints to the model...")
        
        # 1. Subject Requirements: sum(all subject vars) == hours_per_week
        # This iterates S*D*P*R, but we know R is filtered.
        # We can use vars_by_subject_room for faster access?
        # vars_by_subject_room is keyed by (s,r).
        # Let's stick to iterating available variables for simplicity/correctness, 
        # or iterate self.variables directly? No, unstructured.
        # Let's use the caches we built. subject->room is distinct.
        # But we need sum over ALL days/periods/rooms for a subject.
        
        # We can just iterate self.subjects and use vars_by_subject_room
        for subject in self.subjects:
            all_sub_vars = []
            for room in self.rooms:
                if (subject.id, room.id) in self.vars_by_subject_room:
                    all_sub_vars.extend(self.vars_by_subject_room[(subject.id, room.id)])
            
            if all_sub_vars:
                self.model.Add(sum(all_sub_vars) == subject.hours_per_week)
        logger.debug("Added Subject Requirement constraints")

        # 2. Class Concurrency: Max 1 subject per class per period
        # We need vars by class/day/period.
        # Construct ad-hoc or iterate?
        # Iterating Classes -> Days -> Periods -> Subjects -> Rooms is safe enough (50k iters).
        # We can optimize by iterating existing vars only?
        # For now, let's keep the logic but use simple sums if possible.
        # Actually, let's just stick to the specific variable lookups to be safe on correctness.
        # Or better: Iterate vars_by_room and bucket them by Class?
        pass # We'll implement below concisely.
        
        # Build a temporary cache: class_id -> day -> period -> [vars]
        class_period_vars = {c.id: {d: {p: [] for p in range(self.periods_per_day)} for d in range(self.num_days)} for c in self.classes}
        
        # Iterate all created variables to populate this (O(Variables) ~ 150k operations - fast)
        # Using vars_by_room to iterate is easy
        for r_id, day_map in self.vars_by_room.items():
             for day, entries in day_map.items():
                 for entry in entries:
                     # entry: {'start', 'end', 'var', 'period'}
                     # We need to know which subject/class this var belongs to.
                     # We didn't store subject in entry. 
                     # Checking var name string is slow.
                     # Let's adjust create_variables? No, too late.
                     # We can iterate subjects.
                     pass 

        # Fallback to standard iteration but minimized
        for class_obj in self.classes:
            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    slot_vars = []
                    for sub in class_subjects:
                        # Iterate only valid rooms for this subject
                        # use vars_by_subject_room to find vars for this day/period?
                        # vars_by_subject_room is list of vars. Not indexed by day/period.
                        # So we might still look up key.
                        for room in self.rooms:
                             key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                             if key in self.variables:
                                 slot_vars.append(self.variables[key])
                    if slot_vars:
                        self.model.Add(sum(slot_vars) <= 1)
        logger.debug("Added Class Concurrency constraints")

        # 3. RESOURCE CONFLICTS (Optimized)
        
        def add_overlap_constraints(allocations_map, entity_name):
            # allocations_map: id -> day -> list of {start, end, var}
            for entity_id, day_map in allocations_map.items():
                for day, entries in day_map.items():
                    if not entries: continue
                    
                    # 1. Group by exact interval
                    groups = {} # (start, end) -> [vars]
                    for e in entries:
                        key = (e['start'], e['end'])
                        if key not in groups: groups[key] = []
                        groups[key].append(e['var'])
                    
                    # 2. Create sum variables/expressions for each group
                    # If a group has multiple vars, sum(vars) represents "usage during this interval"
                    # Optimization: If only 1 group exists, and sum(vars) <= 1?
                    # No, for Faculty, sum(vars) <= 1 is the requirement itself if all in same interval.
                    
                    group_sums = []
                    for (start, end), vars_list in groups.items():
                        # Constraint: Within explicit same interval, max 1
                        # self.model.Add(sum(vars_list) <= 1) 
                        # Wait, we need to enforce sum(vars_list) + sum(vars_list_overlapping) <= 1
                        # So let's just hold the expression.
                        group_sums.append({
                            'start': start,
                            'end': end,
                            'expr': sum(vars_list) 
                        })
                    
                    # 3. Pairwise check between groups
                    # O(G^2) where G is number of unique intervals (usually 7) -> 49 checks.
                    if len(group_sums) == 1:
                        # Simple case
                        self.model.Add(group_sums[0]['expr'] <= 1)
                    else:
                        for i in range(len(group_sums)):
                            # Self-check? "expr <= 1" must always hold.
                            # Because even if no other group overlaps, you can't be in 2 places at once.
                            # Start with that unless covered by overlaps?
                            # If we have [A, B] and they don't overlap. A<=1, B<=1.
                            # If they overlap, A+B <= 1 (implies A<=1, B<=1).
                            # So strictly checking overlaps suffices?
                            # Not if a group has NO overlaps with others. It still needs <= 1.
                            # We can add `expr <= 1` for all, then `expr1 + expr2 <= 1` for overlaps.
                            # `expr1 + expr2 <= 1` dominates `expr1 <= 1`.
                            # So we track "is constrained".
                            
                            g1 = group_sums[i]
                            has_overlap = False
                            
                            for j in range(i + 1, len(group_sums)):
                                g2 = group_sums[j]
                                if g1['start'] < g2['end'] and g2['start'] < g1['end']:
                                    self.model.Add(g1['expr'] + g2['expr'] <= 1)
                                    has_overlap = True
                            
                            # If this group didn't overlap with any SUBSEQUENT group...
                            # We might have overlapped with previous.
                            # Safest: Just add `expr <= 1` for every group always.
                            # CP-SAT pre-solve removes redundant constraints efficiently.
                            self.model.Add(g1['expr'] <= 1)

        add_overlap_constraints(self.vars_by_faculty, "Faculty")
        add_overlap_constraints(self.vars_by_room, "Room")
        
        logger.debug("Added Resource Conflict (Faculty/Room) constraints")

        # 4. DEFAULT: Labs Consecutive (Optimized?)
        # Logic: If lab, total_daily_slots >= 2. And Convexity.
        # This iterates Subjects * Days * Periods. 
        # Loop limit: 150 * 5 * 7 = 5000. Fast enough. 
        # String formatting f"..." inside might be slow.
        # Can we lookup vars from caches? 
        # vars_by_subject_room[(s,r)] gives list of vars. 
        # But we need them structured by Day/Period.
        # Let's reconstruct structure from caches for specific subjects?
        # Or just use key lookup. 5000 * 50 lookups = 250k. Acceptable.
        
        for sub in self.subjects:
            if sub.requires_lab:
                 for day in range(self.num_days):
                    period_vars = [[] for _ in range(self.periods_per_day)]
                    
                    found_any = False
                    for room in self.rooms:
                        # Optimization: Skip if room/sub combo invalid
                        if (sub.id, room.id) not in self.vars_by_subject_room: continue
                        
                        # We have list of vars for this (s,r).
                        # But we don't know which day/period they correspond to easily 
                        # without iterating them or storing metadata.
                        # We stored day/period in create_variables logic but didn't save to vars_by_subject_room.
                        # Back to string lookup or iterating vars_by_subject_room to sort?
                        # String lookup is safest for now.
                        
                        for period in range(self.periods_per_day):
                             key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                             if key in self.variables:
                                 period_vars[period].append(self.variables[key])
                                 found_any = True

                    if not found_any: continue

                    # Flatten for daily sum
                    all_day_vars = [v for p_list in period_vars for v in p_list]
                    if not all_day_vars: continue

                    # Constraint: Min Block Size (e.g. 2 hours)
                    if sub.hours_per_week >= 2:
                         is_scheduled = self.model.NewBoolVar(f"sched_s{sub.id}_d{day}")
                         total_daily_slots = sum(all_day_vars)
                         
                         self.model.Add(total_daily_slots <= self.periods_per_day * is_scheduled)
                         self.model.Add(total_daily_slots >= is_scheduled)
                         self.model.Add(total_daily_slots >= 2 * is_scheduled)

                    # Convexity
                    p_present_vars = []
                    for p in range(self.periods_per_day):
                        if period_vars[p]:
                            p_var = self.model.NewBoolVar(f"pres_s{sub.id}_d{day}_p{p}")
                            self.model.Add(sum(period_vars[p]) == p_var)
                            p_present_vars.append(p_var)
                        else:
                            p_present_vars.append(0)
                    
                    for i in range(self.periods_per_day):
                        for k in range(i + 2, self.periods_per_day):
                            for j in range(i + 1, k):
                                self.model.Add(p_present_vars[i] + p_present_vars[k] - p_present_vars[j] <= 1)

        # 5. DEFAULT: Single Room per Subject (Optimized)
        for sub in self.subjects:
             # Gather rooms that are actually used by this subject
             used_rooms = []
             room_usage_vars = []
             
             for room in self.rooms:
                 if (sub.id, room.id) in self.vars_by_subject_room:
                     vars_list = self.vars_by_subject_room[(sub.id, room.id)]
                     if vars_list:
                         u_var = self.model.NewBoolVar(f"use_r{room.id}_s{sub.id}")
                         room_usage_vars.append(u_var)
                         
                         # Link: Each slot var implies u_var
                         for v in vars_list:
                             self.model.Add(v <= u_var)
             
             if room_usage_vars:
                 self.model.Add(sum(room_usage_vars) == 1)

        logger.debug("Added Default (Lab/Room) constraints")

        # 6. CUSTOM CONSTRAINTS
        for constraint in self.custom_constraints:
            c_type = constraint.get("type")
            if c_type == "faculty_availability":
                f_name = constraint.get("faculty_name", "").lower()
                allowed_days = [d.lower() for d in constraint.get("available_days", [])]
                
                target_fac = next((f for f in self.faculty if f_name in f.name.lower()), None)
                if target_fac:
                    for day_idx, day_name in enumerate(self.working_days):
                        if day_name.lower() not in allowed_days:
                            # Forbid all vars for this faculty on this day
                            # Optimization: Use cache!
                            if day_idx in self.vars_by_faculty[target_fac.id]:
                                entries = self.vars_by_faculty[target_fac.id][day_idx]
                                for e in entries:
                                    self.model.Add(e['var'] == 0)


    def solve(self) -> Dict[str, Any]:
        logger.info(f"Step 4/5: Solving model (Time Limit: {self.time_limit_seconds}s)...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.num_search_workers = 8 # Use all cores
        solver.parameters.log_search_progress = True # Debugging
        
        start_time = time.time()
        status = solver.Solve(self.model)
        duration = time.time() - start_time
        logger.info(f"Step 5/5: Solver finished in {duration:.2f}s with status: {solver.StatusName(status)}")
        
        # Log Solver Stats
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
            intervals = self._get_class_period_intervals(class_obj) # Get REAL times for this class
            
            class_schedule = {
                "class_id": class_obj.id, 
                "class_name": f"{class_obj.name} {class_obj.section or ''}",
                "department": next((d.name for d in self.departments if d.id == class_obj.department_id), ""),
                "batch_name": class_obj.batch.name if class_obj.batch else "Default",
                "timetable": {}
            }
            
            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]
            
            for day_idx, day_name in enumerate(self.working_days):
                day_schedule = []
                for p_idx in range(self.periods_per_day):
                    # Default empty slot
                    slot_info = {
                        "period": p_idx + 1, 
                        "time": f"{intervals[p_idx][0]//60:02d}:{intervals[p_idx][0]%60:02d} - {intervals[p_idx][1]//60:02d}:{intervals[p_idx][1]%60:02d}",
                        "subject": None
                    }
                    
                    # Find assigned subject
                    for sub in class_subjects:
                        for room in self.rooms:
                            key = f"s{sub.id}_d{day_idx}_p{p_idx}_r{room.id}"
                            if key in self.variables and solver.Value(self.variables[key]) == 1:
                                faculty_name = "TBA"
                                if sub.faculty_id:
                                    fac = next((f for f in self.faculty if f.id == sub.faculty_id), None)
                                    if fac: faculty_name = fac.name
                                
                                slot_info.update({
                                    "subject": sub.name,
                                    "subject_code": sub.code,
                                    "faculty": faculty_name,
                                    "room": room.name,
                                    "is_lab": sub.requires_lab
                                })
                                break # Found the subject for this slot
                    day_schedule.append(slot_info)
                class_schedule["timetable"][day_name] = day_schedule
                
            schedule[f"class_{class_obj.id}"] = class_schedule
        return schedule

    def generate_schedule(self, department_ids: Optional[List[int]] = None, batch_ids: Optional[List[int]] = None, class_ids: Optional[List[int]] = None, faculty_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        data_summary = self.load_data(department_ids, batch_ids, class_ids, faculty_ids)
        if not self.classes or not self.subjects:
             # Just return empty valid result if no classes, instead of error hard crash
            msg = "No classes found." if not self.classes else "Found Classes, but NO Subjects are assigned to them.\nHint: Go to 'Mapping' and assign your Global Subjects to these Classes."
            return {"status": "ERROR", "message": msg, "data_summary": data_summary}

        # VALIDATION: Ensure every subject has a Faculty and Class mapped
        missing_mappings = []
        for sub in self.subjects:
            issues = []
            if not sub.class_id: issues.append("Missing Class")
            if not sub.faculty_id: issues.append("Missing Faculty")
            
            if issues:
                missing_mappings.append(f"{sub.name} ({sub.code}): {', '.join(issues)}")
        
        if missing_mappings:
            # Just log warning, don't stop. Treat them as TBA.
            logger.warning(f"Data Mapping Warning: The following subjects are incomplete:\n" + "\n".join(missing_mappings))
            # return {
            #     "status": "ERROR", 
            #     "message": f"Data Mapping Error: The following subjects are incomplete:\n" + "\n".join(missing_mappings),
            #     "data_summary": data_summary
            # }

        # VALIDATION 2: Class Workload vs Available Slots
        # Total slots available per week = num_days * periods_per_day
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

