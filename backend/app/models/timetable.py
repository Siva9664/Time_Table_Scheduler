from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.database import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    classes = relationship("Class", back_populates="department", cascade="all, delete-orphan")
    faculty = relationship("Faculty", back_populates="department")

class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    period_duration = Column(Integer, default=60)
    break_times = Column(JSON, default=[])
    lunch_break = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    classes = relationship("Class", back_populates="batch")

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    section = Column(String)
    semester = Column(Integer)
    student_count = Column(Integer)
    department_id = Column(Integer, ForeignKey("departments.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    department = relationship("Department", back_populates="classes") 
    batch = relationship("Batch", back_populates="classes")
    # subjects removed (linked via Batch/Dept now)


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=False, nullable=False)
    hours_per_week = Column(Integer, nullable=False)
    requires_lab = Column(Boolean, default=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    department = relationship("Department")
    batch = relationship("Batch")
    assigned_class = relationship("Class")
    faculty = relationship("Faculty", back_populates="subjects")

class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    max_hours_per_week = Column(Integer, default=20)
    unavailable_slots = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    department = relationship("Department", back_populates="faculty")
    subjects = relationship("Subject", back_populates="faculty")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    room_type = Column(String)
    capacity = Column(Integer, nullable=False)
    has_projector = Column(Boolean, default=False)
    has_computers = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    academic_year = Column(String)
    semester = Column(Integer)
    schedule_data = Column(JSON)
    constraints_used = Column(JSON)
    solver_status = Column(String)
    solve_time_seconds = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
