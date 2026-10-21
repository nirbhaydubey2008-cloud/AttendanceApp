"""
database/models.py
SQLAlchemy ORM models defining classroom attendance, student biometrics,
multimodal engagement telemetry, rule-based recommendations, and RBAC authentication
(Users, Teachers, Courses, Enrollments, Lectures, and AuditLogs).
"""

import time
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.database import Base


class User(Base):
    """
    Authenticated user account with role-based access control.
    Role is strictly either TEACHER or STUDENT.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="STUDENT", nullable=False)  # TEACHER, STUDENT
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student_profile = relationship("Student", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Teacher(Base):
    """
    Teacher profile associated with an authenticated TEACHER user.
    """
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(100), default="Computer Science & Engineering", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="teacher_profile")
    courses = relationship("Course", back_populates="teacher")
    lectures = relationship("Lecture", back_populates="teacher")

    def __repr__(self):
        return f"<Teacher {self.employee_id}: {self.name}>"


class Student(Base):
    """
    Enrolled student biometric identity and metadata.
    Can be associated with an authenticated STUDENT user account.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    student_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    roll_no = Column(String(50), nullable=True, index=True)
    photo_path = Column(String(255), nullable=True)
    initial_password = Column(String(100), nullable=True)
    consent_given = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="student_profile")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    metrics = relationship("PersonMetric", back_populates="student")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.student_id}: {self.name}>"


class Course(Base):
    """
    Academic course managed by an instructor.
    """
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teacher = relationship("Teacher", back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    lectures = relationship("Lecture", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course {self.course_code}: {self.title}>"


class Enrollment(Base):
    """
    Student enrollment in an academic course.
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_course_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")

    def __repr__(self):
        return f"<Enrollment Course#{self.course_id} - Student#{self.student_id}>"


class Lecture(Base):
    """
    Academic lecture representing planned and conducted class events.
    Lifecycle: DRAFT -> SCHEDULED -> LIVE -> COMPLETED (or CANCELLED).
    """
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(String(100), unique=True, index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    topic = Column(String(200), nullable=True)
    scheduled_date = Column(DateTime, nullable=True)
    planned_duration_min = Column(Integer, default=60, nullable=False)
    status = Column(String(20), default="SCHEDULED", nullable=False)  # DRAFT, SCHEDULED, LIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course", back_populates="lectures")
    teacher = relationship("Teacher", back_populates="lectures")
    sessions = relationship("Session", back_populates="lecture")

    def __repr__(self):
        return f"<Lecture {self.lecture_id}: {self.title} ({self.status})>"


class Session(Base):
    """
    Classroom lecture session state and temporal boundaries.
    Represents an actual live execution of a planned Lecture.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    title = Column(String(200), default="Classroom Lecture", nullable=False)
    course_code = Column(String(50), default="CS101", nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="LIVE", nullable=False)  # LIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lecture = relationship("Lecture", back_populates="sessions")
    teacher = relationship("Teacher")
    attendance_records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")
    metrics = relationship("PersonMetric", back_populates="session", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.session_id}: {self.title}>"


class AttendanceRecord(Base):
    """
    Session-level student attendance verification and duration summary.
    """
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.session_id"), index=True, nullable=False)
    student_id = Column(String(50), ForeignKey("students.student_id"), nullable=True, index=True)
    student_name = Column(String(100), nullable=False)
    track_id = Column(String(50), nullable=False)
    time_present_sec = Column(Float, default=0.0, nullable=False)
    presence_ratio = Column(Float, default=0.0, nullable=False)
    status = Column(String(20), default="ABSENT", nullable=False)  # PRESENT, PARTIAL, ABSENT
    mean_engagement = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")

    def __repr__(self):
        return f"<AttendanceRecord {self.student_name}: {self.status} ({self.presence_ratio*100:.1f}%)>"


class PersonMetric(Base):
    """
    Fine-grained multimodal engagement telemetry recorded per student per frame/window.
    """
    __tablename__ = "person_metrics"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.session_id"), index=True, nullable=False)
    student_id = Column(String(50), ForeignKey("students.student_id"), nullable=True, index=True)
    track_id = Column(String(50), index=True, nullable=False)
    timestamp = Column(Float, nullable=False, index=True)
    
    # Visual metrics
    gaze_score = Column(Float, default=0.0, nullable=False)
    yaw = Column(Float, default=0.0, nullable=False)
    pitch = Column(Float, default=0.0, nullable=False)
    roll = Column(Float, default=0.0, nullable=False)
    ear = Column(Float, default=0.25, nullable=False)
    is_blinking = Column(Boolean, default=False, nullable=False)
    is_looking_forward = Column(Boolean, default=True, nullable=False)
    
    # Audio context
    audio_state = Column(String(30), default="QUIET", nullable=False)
    audio_rms = Column(Float, default=0.0, nullable=False)
    
    # Fused engagement
    engagement_score = Column(Float, default=0.0, nullable=False)
    tier = Column(String(20), default="MEDIUM", nullable=False)  # HIGH, MEDIUM, LOW
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="metrics")
    student = relationship("Student", back_populates="metrics")

    def __repr__(self):
        return f"<PersonMetric Track#{self.track_id}: Score={self.engagement_score} ({self.tier})>"


class Recommendation(Base):
    """
    Pedagogical feedback and actionable recommendations generated by reasoning engine.
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.session_id"), index=True, nullable=False)
    timestamp = Column(Float, default=time.time, nullable=False)
    trigger_type = Column(String(50), nullable=False)  # LOW_ENGAGEMENT, DISTURBANCE, HIGH_HEAD_TURN, etc.
    suggestion_text = Column(Text, nullable=False)
    priority = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, URGENT
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation [{self.priority}] {self.trigger_type}>"


class AuditLog(Base):
    """
    Immutable audit log tracking sensitive actions (e.g. manual attendance overrides).
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    target_entity = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.target_entity} at {self.timestamp}>"
