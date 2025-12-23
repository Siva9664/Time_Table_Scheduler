from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.timetable import Department, Class, Subject, Faculty, Room, Batch
import time
from datetime import datetime, timedelta

class TimetableScheduler:
    def __init__(self, db: Session, working_days: List[str], periods_per_day: int, time_limit_seconds: int = 300, custom_constraints: List[Dict[str, Any]] = None):
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
        self.variables = {} # Map: "s{subject_id}_d{day_index}_p{period_index}_r{room_id}" -> BoolVar

    def load_data(self, department_ids: Optional[List[int]] = None, batch_ids: Optional[List[int]] = None, class_ids: Optional[List[int]] = None, faculty_ids: Optional[List[int]] = None):
        """Loads all necessary data from DB."""
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
        # Re-derive class_ids from actual loaded classes to ensure subject filtering matches
        loaded_class_ids = [c.id for c in self.classes]
        
        # Subjects
        s_query = self.db.query(Subject)
        # Filter subjects that belong to the loaded classes
        s_query = s_query.filter(Subject.class_id.in_(loaded_class_ids))
        self.subjects = s_query.all()
        
        # Faculty
        f_query = self.db.query(Faculty)
        if faculty_ids:
             f_query = f_query.filter(Faculty.id.in_(faculty_ids))
        elif dept_ids:
             f_query = f_query.filter(Faculty.department_id.in_(dept_ids))
        self.faculty = f_query.all()
        
        # Rooms
        self.rooms = self.db.query(Room).all()

        return {
            "departments": len(self.departments), "batches": len(self.batches),
            "classes": len(self.classes), "subjects": len(self.subjects),
            "faculty": len(self.faculty), "rooms": len(self.rooms)
        }

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
        for subject in self.subjects:
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    for room in self.rooms:
                        # Optimization: Only create vars if room type matches subject requirement
                        if subject.requires_lab and room.room_type != 'lab':
                            continue
                        if not subject.requires_lab and room.room_type == 'lab':
                            continue # Theory classes shouldn't hog labs ideally, though soft constraint possible
                            
                        var_name = f"s{subject.id}_d{day}_p{period}_r{room.id}"
                        self.variables[var_name] = self.model.NewBoolVar(var_name)

    def add_constraints(self):
        # 1. Subject Requirements: Each subject must be taught exactly 'hours_per_week' times
        for subject in self.subjects:
            sub_vars = []
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    for room in self.rooms:
                        key = f"s{subject.id}_d{day}_p{period}_r{room.id}"
                        if key in self.variables:
                            sub_vars.append(self.variables[key])
            self.model.Add(sum(sub_vars) == subject.hours_per_week)

        # 2. Class Concurrency: A class can only be in one room/subject at a specific period
        # (This is still 'Period' based because a Class has a single timeline)
        for class_obj in self.classes:
            class_subjects = [s for s in self.subjects if s.class_id == class_obj.id]
            for day in range(self.num_days):
                for period in range(self.periods_per_day):
                    slot_vars = []
                    for sub in class_subjects:
                        for room in self.rooms:
                            key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                            if key in self.variables:
                                slot_vars.append(self.variables[key])
                    # Sum <= 1 implies max one subject per period for this class
                    self.model.Add(sum(slot_vars) <= 1)

        # 3. RESOURCE CONFLICTS (Real-Time Check)
        # We need to ensure Faculty and Rooms are not double-booked across DIFFERENT classes/batches
        # that might have overlapping time intervals.
        
        # Pre-calculate time intervals for all classes: Map[ClassID] -> List[(Start, End)]
        class_timings = {c.id: self._get_class_period_intervals(c) for c in self.classes}

        # We will check conflicts Day by Day
        for day in range(self.num_days):
            
            # --- FACULTY CONFLICTS ---
            for faculty in self.faculty:
                fac_subjects = [s for s in self.subjects if s.faculty_id == faculty.id]
                # Group subjects by Class to know their timing
                # Variables: list of (Variable, StartTime, EndTime)
                active_assignments = [] 
                
                for sub in fac_subjects:
                    c_id = sub.class_id
                    if c_id not in class_timings: continue
                    intervals = class_timings[c_id]
                    
                    for period in range(self.periods_per_day):
                        if period >= len(intervals): continue
                        start, end = intervals[period]
                        
                        for room in self.rooms:
                            key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                            if key in self.variables:
                                active_assignments.append({
                                    "var": self.variables[key],
                                    "start": start,
                                    "end": end
                                })
                
                # Now enforce: If two assignments overlap in time, their sum <= 1
                # Optimization: Discretize time or check pairwise.
                # Since periods are few (e.g. 7-8), pairwise check for this faculty on this day is fine.
                for i in range(len(active_assignments)):
                    for j in range(i + 1, len(active_assignments)):
                        a1 = active_assignments[i]
                        a2 = active_assignments[j]
                        # Overlap logic: StartA < EndB and StartB < EndA
                        if a1["start"] < a2["end"] and a2["start"] < a1["end"]:
                            self.model.Add(a1["var"] + a2["var"] <= 1)

            # --- ROOM CONFLICTS ---
            for room in self.rooms:
                room_assignments = []
                for sub in self.subjects: # All subjects could use this room
                    c_id = sub.class_id
                    if c_id not in class_timings: continue
                    intervals = class_timings[c_id]
                    
                    for period in range(self.periods_per_day):
                        if period >= len(intervals): continue
                        start, end = intervals[period]
                        
                        key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                        if key in self.variables:
                             room_assignments.append({
                                "var": self.variables[key],
                                "start": start,
                                "end": end
                            })

                # Pairwise overlap check for rooms
                for i in range(len(room_assignments)):
                    for j in range(i + 1, len(room_assignments)):
                        a1 = room_assignments[i]
                        a2 = room_assignments[j]
                        if a1["start"] < a2["end"] and a2["start"] < a1["end"]:
                            self.model.Add(a1["var"] + a2["var"] <= 1)

        # 4. CUSTOM CONSTRAINTS (From AI Parser)
        for constraint in self.custom_constraints:
            c_type = constraint.get("type")
            
            # Constraint: Faculty Availability
            if c_type == "faculty_availability":
                f_name = constraint.get("faculty_name", "").lower()
                allowed_days = [d.lower() for d in constraint.get("available_days", [])]
                
                # Find the faculty ID
                target_fac = next((f for f in self.faculty if f_name in f.name.lower()), None)
                if target_fac:
                    # Forbid assignment on days NOT in allowed_days
                    for day_idx, day_name in enumerate(self.working_days):
                        if day_name.lower() not in allowed_days:
                            # Forbid all variables for this faculty on this day
                            fac_subjects = [s for s in self.subjects if s.faculty_id == target_fac.id]
                            for sub in fac_subjects:
                                for p in range(self.periods_per_day):
                                    for r in self.rooms:
                                        key = f"s{sub.id}_d{day_idx}_p{p}_r{r.id}"
                                        if key in self.variables:
                                            self.model.Add(self.variables[key] == 0)

            # Constraint: Consecutive Periods (Labs)
            elif c_type == "consecutive_periods" and constraint.get("subject_type") == "lab":
                # Enforce that if a lab is scheduled, it must be in blocks of 2 or more (simplified: just force blocks if possible)
                # Harder constraint: Labs usually have 'hours_per_week' and if it's 3, maybe we want 3 consecutive?
                # Implementation: If Subject.requires_lab is True, try to make periods consecutive on the same day.
                
                # Implementation: For each day, ensure no gaps for this subject.
                # Pattern banning: For a subject S on Day D, we cannot have 1, 0, 1 (gap of 1)
                # nor 1, 0, 0, 1 (gap of 2), etc.
                # Essentially, if S is Present at P1 and P2 (P1 < P2), then for all k between P1, P2, S must be Present.
                
                for sub in self.subjects:
                    if sub.requires_lab:
                         for day in range(self.num_days):
                            # Gather variables for this subject on this day
                            daily_vars = []
                            for period in range(self.periods_per_day):
                                found_var = None
                                for room in self.rooms:
                                    key = f"s{sub.id}_d{day}_p{period}_r{room.id}"
                                    if key in self.variables:
                                        found_var = self.variables[key]
                                        break # Logic assumes one room per subject slot mostly
                                daily_vars.append(found_var)
                            
                            # Filter out None (in case subject/room combo invalid)
                            valid_vars = [v for v in daily_vars if v is not None]
                            if not valid_vars: continue

                            # Constraint: Convexity
                            # If we have P vars [x0, x1, x2, ... xN]
                            # For every triplet i < j < k, if x_i=1 and x_k=1, then x_j must be 1.
                            # This ensures block structure.
                            for i in range(len(valid_vars)):
                                for k in range(i + 2, len(valid_vars)):
                                    # Check all j in between
                                    for j in range(i + 1, k):
                                        # (x_i AND x_k) => x_j
                                        # Equivalent to: x_i + x_k - x_j <= 1
                                        self.model.Add(valid_vars[i] + valid_vars[k] - valid_vars[j] <= 1)


    def solve(self) -> Dict[str, Any]:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        status = solver.Solve(self.model)
        
        status_map = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE", 
                     cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID", 
                     cp_model.UNKNOWN: "UNKNOWN"}
        
        result = {"status": status_map.get(status, "UNKNOWN"), "schedule": None}
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
            return {"status": "ERROR", "message": "No classes or matching subjects found", "data_summary": data_summary}
        
        self.create_variables()
        self.add_constraints()
        result = self.solve()
        result["data_summary"] = data_summary
        return result

