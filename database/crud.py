"""
database/crud.py
Convenience CRUD functions for querying and persisting attendance, metrics, sessions,
users, teachers, courses, enrollments, lectures, and audit logs.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database.models import (
    Student, Session as DbSession, AttendanceRecord, PersonMetric, Recommendation,
    User, Teacher, Course, Enrollment, Lecture, AuditLog
)


# --- User CRUD ---

def create_user(
    db: Session,
    username: str,
    hashed_password: str,
    role: str = "STUDENT",
    email: Optional[str] = None,
    is_active: bool = True,
    must_change_password: bool = False
) -> User:
    """Creates a new user account with hashed password and role."""
    user = User(
        username=username.strip(),
        email=email.strip().lower() if email else None,
        hashed_password=hashed_password,
        role=role.upper(),
        is_active=is_active,
        must_change_password=must_change_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieves user by primary key."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Retrieves user by unique username (case-insensitive search)."""
    if not username or not username.strip():
        return None
    return db.query(User).filter(func.upper(User.username) == username.strip().upper()).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieves user by unique email."""
    if not email:
        return None
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    """Retrieves user by either username or email (case-insensitive)."""
    if not identifier or not identifier.strip():
        return None
    clean = identifier.strip()
    return db.query(User).filter(
        or_(func.upper(User.username) == clean.upper(), func.lower(User.email) == clean.lower())
    ).first()


def update_user_password(db: Session, user_id: int, new_hashed_password: str, must_change_password: bool = False) -> Optional[User]:
    """Updates user password and clears must_change_password flag."""
    user = get_user_by_id(db, user_id)
    if user:
        user.hashed_password = new_hashed_password
        user.must_change_password = must_change_password
        db.commit()
        db.refresh(user)
    return user


# --- Teacher CRUD ---

def create_teacher(
    db: Session,
    user_id: int,
    employee_id: str,
    name: str,
    department: str = "Computer Science & Engineering"
) -> Teacher:
    """Creates a teacher profile linked to a user."""
    teacher = Teacher(
        user_id=user_id,
        employee_id=employee_id.strip(),
        name=name.strip(),
        department=department.strip()
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def get_teacher_by_user_id(db: Session, user_id: int) -> Optional[Teacher]:
    """Retrieves teacher profile for a given user ID."""
    return db.query(Teacher).filter(Teacher.user_id == user_id).first()


def get_teacher_by_id(db: Session, teacher_id: int) -> Optional[Teacher]:
    """Retrieves teacher by primary key."""
    return db.query(Teacher).filter(Teacher.id == teacher_id).first()


def get_all_teachers(db: Session) -> List[Teacher]:
    """Retrieves all teacher profiles."""
    return db.query(Teacher).all()


# --- Course CRUD ---

def create_course(
    db: Session,
    course_code: str,
    title: str,
    teacher_id: Optional[int] = None,
    description: Optional[str] = None
) -> Course:
    """Creates a new course."""
    existing = get_course_by_code(db, course_code)
    if existing:
        return existing

    course = Course(
        course_code=course_code.strip().upper(),
        title=title.strip(),
        description=description,
        teacher_id=teacher_id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_course_by_code(db: Session, course_code: str) -> Optional[Course]:
    """Retrieves course by course code (e.g. CS101)."""
    return db.query(Course).filter(Course.course_code == course_code.strip().upper()).first()


def get_course_by_id(db: Session, course_id: int) -> Optional[Course]:
    """Retrieves course by primary key."""
    return db.query(Course).filter(Course.id == course_id).first()


def get_all_courses(db: Session) -> List[Course]:
    """Retrieves all courses."""
    return db.query(Course).order_by(Course.course_code).all()


def get_courses_by_teacher(db: Session, teacher_id: int) -> List[Course]:
    """Retrieves courses assigned to a teacher."""
    return db.query(Course).filter(Course.teacher_id == teacher_id).all()


# --- Enrollment CRUD ---

def enroll_student_in_course(db: Session, student_id: Any, course_id: int) -> Enrollment:
    """Enrolls a student in a course (prevents duplicates). Accepts student db id or string student_id."""
    s_db_id = student_id
    if isinstance(student_id, str):
        st = get_student_by_id(db, student_id)
        if st:
            s_db_id = st.id

    existing = db.query(Enrollment).filter(
        Enrollment.student_id == s_db_id,
        Enrollment.course_id == course_id
    ).first()
    if existing:
        return existing

    enrollment = Enrollment(
        course_id=course_id,
        student_id=s_db_id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def get_student_enrollments(db: Session, student_identifier: Any) -> List[Enrollment]:
    """Retrieves all enrollments for a student (by db id or string student_id)."""
    s_db_id = student_identifier
    if isinstance(student_identifier, str):
        st = get_student_by_id(db, student_identifier)
        if not st:
            return []
        s_db_id = st.id
    return db.query(Enrollment).filter(Enrollment.student_id == s_db_id).all()


def get_enrolled_courses_for_student(db: Session, student_db_id: int) -> List[Course]:
    """Retrieves all courses a student is enrolled in."""
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_db_id).all()
    course_ids = [e.course_id for e in enrollments]
    return db.query(Course).filter(Course.id.in_(course_ids)).all() if course_ids else []


def get_enrolled_students_for_course(db: Session, course_id: int) -> List[Student]:
    """Retrieves all students enrolled in a course."""
    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    student_ids = [e.student_id for e in enrollments]
    return db.query(Student).filter(Student.id.in_(student_ids)).all() if student_ids else []


# --- Lecture CRUD ---

def create_lecture(
    db: Session,
    lecture_id: str,
    course_id: int,
    teacher_id: int,
    title: str,
    topic: Optional[str] = None,
    scheduled_date: Optional[datetime] = None,
    planned_duration_min: int = 60,
    status: str = "SCHEDULED"
) -> Lecture:
    """Creates a new scheduled lecture."""
    existing = db.query(Lecture).filter(Lecture.lecture_id == lecture_id).first()
    if existing:
        return existing

    lecture = Lecture(
        lecture_id=lecture_id.strip(),
        course_id=course_id,
        teacher_id=teacher_id,
        title=title.strip(),
        topic=topic,
        scheduled_date=scheduled_date or datetime.utcnow(),
        planned_duration_min=planned_duration_min,
        status=status.upper()
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    return lecture


def get_lecture_by_id(db: Session, lecture_id: str) -> Optional[Lecture]:
    """Retrieves lecture by string identifier (e.g. LEC_CS101_01)."""
    return db.query(Lecture).filter(Lecture.lecture_id == lecture_id).first()


def get_lecture_by_db_id(db: Session, id: int) -> Optional[Lecture]:
    """Retrieves lecture by integer primary key."""
    return db.query(Lecture).filter(Lecture.id == id).first()


def get_all_lectures(db: Session, limit: int = 50) -> List[Lecture]:
    """Retrieves all lectures ordered newest scheduled first."""
    return db.query(Lecture).order_by(Lecture.scheduled_date.desc()).limit(limit).all()


def get_lectures_by_course(db: Session, course_id: int) -> List[Lecture]:
    """Retrieves lectures for a specific course."""
    return db.query(Lecture).filter(Lecture.course_id == course_id).order_by(Lecture.scheduled_date.desc()).all()


def get_lectures_by_teacher(db: Session, teacher_id: int) -> List[Lecture]:
    """Retrieves lectures instructed by a teacher."""
    return db.query(Lecture).filter(Lecture.teacher_id == teacher_id).order_by(Lecture.scheduled_date.desc()).all()


def update_lecture_status(db: Session, lecture_id: str, new_status: str) -> Optional[Lecture]:
    """Updates status of a lecture (DRAFT, SCHEDULED, LIVE, COMPLETED, CANCELLED)."""
    lecture = get_lecture_by_id(db, lecture_id)
    if lecture:
        lecture.status = new_status.upper()
        db.commit()
        db.refresh(lecture)
    return lecture


# --- Audit Log CRUD ---

def create_audit_log(
    db: Session,
    action: str,
    target_entity: str,
    user_id: Optional[int] = None,
    details: Optional[str] = None
) -> AuditLog:
    """Creates an immutable audit log entry for administrative/security actions."""
    log = AuditLog(
        user_id=user_id,
        action=action.strip(),
        target_entity=target_entity.strip(),
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(db: Session, limit: int = 100) -> List[AuditLog]:
    """Retrieves recent audit logs in reverse chronological order."""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()


# --- Student Biometrics CRUD ---

def create_or_get_student(
    db: Session,
    student_id: str,
    name: str,
    roll_no: Optional[str] = None,
    photo_path: Optional[str] = None,
    consent_given: bool = True,
    user_id: Optional[int] = None,
    initial_password: Optional[str] = None
) -> Student:
    """Gets an existing student or creates a new enrolled student record."""
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        student = Student(
            student_id=student_id,
            name=name,
            roll_no=roll_no,
            photo_path=photo_path,
            consent_given=consent_given,
            user_id=user_id,
            initial_password=initial_password
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    else:
        if user_id and not student.user_id:
            student.user_id = user_id
        if initial_password and not student.initial_password:
            student.initial_password = initial_password
        db.commit()
        db.refresh(student)
    return student


def get_student_by_id(db: Session, student_id: str) -> Optional[Student]:
    """Retrieves student record by student_id string (case-insensitive)."""
    if not student_id or not student_id.strip():
        return None
    return db.query(Student).filter(func.upper(Student.student_id) == student_id.strip().upper()).first()


def get_student_by_roll_no(db: Session, roll_no: str) -> Optional[Student]:
    """Retrieves student record by academic roll number (case-insensitive)."""
    if not roll_no or not roll_no.strip():
        return None
    clean = roll_no.strip().upper()
    direct = db.query(Student).filter(func.upper(Student.roll_no) == clean).first()
    if direct:
        return direct
    if not clean.startswith("ROLL-"):
        prefixed = db.query(Student).filter(func.upper(Student.roll_no) == f"ROLL-{clean}").first()
        if prefixed:
            return prefixed
    return None


def get_student_by_user_id(db: Session, user_id: int) -> Optional[Student]:
    """Retrieves student record linked to a user account."""
    return db.query(Student).filter(Student.user_id == user_id).first()


def generate_next_student_id(db: Session, year: Optional[int] = None) -> str:
    """
    Generates the next sequential unique Student ID in format STU-YYYY-XXXX (e.g. STU-2026-0001).
    """
    if year is None:
        year = datetime.utcnow().year

    prefix = f"STU-{year}-"
    records = db.query(Student.student_id).filter(Student.student_id.like(f"{prefix}%")).all()

    max_num = 0
    for (s_id,) in records:
        suffix = s_id[len(prefix):]
        if suffix.isdigit():
            val = int(suffix)
            if val > max_num:
                max_num = val

    candidate_num = max_num + 1
    candidate_id = f"{prefix}{candidate_num:04d}"

    while db.query(Student).filter(Student.student_id == candidate_id).first():
        candidate_num += 1
        candidate_id = f"{prefix}{candidate_num:04d}"

    return candidate_id


# --- Session CRUD ---

def create_session(
    db: Session,
    session_id: str,
    title: str = "Classroom Lecture",
    course_code: str = "CS101",
    lecture_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    status: str = "LIVE"
) -> DbSession:
    """Creates a new classroom lecture session."""
    existing = db.query(DbSession).filter(DbSession.session_id == session_id).first()
    if existing:
        return existing
    
    session = DbSession(
        session_id=session_id,
        title=title,
        course_code=course_code,
        lecture_id=lecture_id,
        teacher_id=teacher_id,
        status=status.upper(),
        start_time=datetime.utcnow(),
        is_active=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: Session, session_id: str) -> Optional[DbSession]:
    """Marks a session as inactive, sets end timestamp, and status to COMPLETED."""
    session = db.query(DbSession).filter(DbSession.session_id == session_id).first()
    if session:
        session.is_active = False
        session.status = "COMPLETED"
        session.end_time = datetime.utcnow()
        if session.lecture_id:
            # Also update linked lecture status if applicable
            lecture = db.query(Lecture).filter(Lecture.id == session.lecture_id).first()
            if lecture and lecture.status == "LIVE":
                lecture.status = "COMPLETED"
        db.commit()
        db.refresh(session)
    return session


def get_active_session(db: Session) -> Optional[DbSession]:
    """Retrieves currently active session if one exists."""
    return db.query(DbSession).filter(DbSession.is_active == True).first()


def save_attendance_record(
    db: Session,
    session_id: str,
    student_name: str,
    track_id: str,
    time_present_sec: float,
    presence_ratio: float,
    status: str,
    mean_engagement: float,
    student_id: Optional[str] = None
) -> AttendanceRecord:
    """Creates or updates an attendance record for a student in a session."""
    query = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id)
    if student_id:
        record = query.filter(AttendanceRecord.student_id == student_id).first()
    else:
        record = query.filter(AttendanceRecord.track_id == track_id).first()

    if not record:
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            student_name=student_name,
            track_id=track_id,
            time_present_sec=time_present_sec,
            presence_ratio=presence_ratio,
            status=status,
            mean_engagement=mean_engagement
        )
        db.add(record)
    else:
        record.time_present_sec = time_present_sec
        record.presence_ratio = presence_ratio
        record.status = status
        record.mean_engagement = mean_engagement
        if student_id and not record.student_id:
            record.student_id = student_id
            record.student_name = student_name

    db.commit()
    db.refresh(record)
    return record


def save_person_metric(
    db: Session,
    session_id: str,
    track_id: str,
    timestamp: float,
    gaze_score: float,
    yaw: float,
    pitch: float,
    roll: float,
    ear: float,
    is_blinking: bool,
    is_looking_forward: bool,
    audio_state: str,
    audio_rms: float,
    engagement_score: float,
    tier: str,
    student_id: Optional[str] = None
) -> PersonMetric:
    """Inserts a fine-grained telemetry point for a student."""
    metric = PersonMetric(
        session_id=session_id,
        student_id=student_id,
        track_id=track_id,
        timestamp=timestamp,
        gaze_score=gaze_score,
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        ear=ear,
        is_blinking=is_blinking,
        is_looking_forward=is_looking_forward,
        audio_state=audio_state,
        audio_rms=audio_rms,
        engagement_score=engagement_score,
        tier=tier
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def save_recommendation(
    db: Session,
    session_id: str,
    trigger_type: str,
    suggestion_text: str,
    priority: str = "INFO",
    timestamp: Optional[float] = None
) -> Recommendation:
    """Inserts a generated pedagogical recommendation."""
    rec = Recommendation(
        session_id=session_id,
        timestamp=timestamp or datetime.utcnow().timestamp(),
        trigger_type=trigger_type,
        suggestion_text=suggestion_text,
        priority=priority
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_session_attendance(db: Session, session_id: str) -> List[AttendanceRecord]:
    """Retrieves all attendance records for a session."""
    return db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).all()


def get_student_attendance_history(db: Session, student_id: str) -> List[AttendanceRecord]:
    """Retrieves all attendance records across all sessions for a specific student."""
    return db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).order_by(AttendanceRecord.created_at.desc()).all()


def get_session_metrics(
    db: Session,
    session_id: str,
    track_id: Optional[str] = None,
    limit: int = 500
) -> List[PersonMetric]:
    """Queries telemetry metrics for a session."""
    query = db.query(PersonMetric).filter(PersonMetric.session_id == session_id)
    if track_id:
        query = query.filter(PersonMetric.track_id == track_id)
    return query.order_by(PersonMetric.timestamp.desc()).limit(limit).all()


def get_session_recommendations(db: Session, session_id: str) -> List[Recommendation]:
    """Queries generated recommendations for a session."""
    return db.query(Recommendation).filter(Recommendation.session_id == session_id).order_by(Recommendation.timestamp.desc()).all()


def get_all_sessions(db: Session, limit: int = 50) -> List[DbSession]:
    """Retrieves all sessions ordered newest first."""
    return db.query(DbSession).order_by(DbSession.start_time.desc()).limit(limit).all()


def get_session_by_id(db: Session, session_id: str) -> Optional[DbSession]:
    """Retrieves a single session by session_id."""
    return db.query(DbSession).filter(DbSession.session_id == session_id).first()


def update_attendance_status(db: Session, session_id: str, student_key: str, status: str) -> Optional[AttendanceRecord]:
    """Manually overrides attendance record status in SQLite."""
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id,
        (AttendanceRecord.student_id == student_key) | (AttendanceRecord.track_id == student_key)
    ).first()
    if record:
        record.status = str(status).upper()
        db.commit()
        db.refresh(record)
    return record


def get_db_stats(db: Session) -> Dict[str, int]:
    """Returns total record counts for system diagnostics."""
    return {
        "users": db.query(User).count(),
        "teachers": db.query(Teacher).count(),
        "courses": db.query(Course).count(),
        "enrollments": db.query(Enrollment).count(),
        "lectures": db.query(Lecture).count(),
        "sessions": db.query(DbSession).count(),
        "students": db.query(Student).count(),
        "attendance_records": db.query(AttendanceRecord).count(),
        "person_metrics": db.query(PersonMetric).count(),
        "recommendations": db.query(Recommendation).count(),
        "audit_logs": db.query(AuditLog).count()
    }


def delete_course(db: Session, course_code: str) -> bool:
    """Deletes a course and all associated student enrollments and scheduled lectures."""
    clean_code = course_code.strip().upper()
    course = get_course_by_code(db, clean_code)
    if not course:
        return False

    # Remove student enrollments for this course
    db.query(Enrollment).filter(Enrollment.course_id == course.id).delete(synchronize_session=False)

    # Handle lectures for this course
    lectures = db.query(Lecture).filter(Lecture.course_id == course.id).all()
    lecture_ids = [lec.id for lec in lectures]
    if lecture_ids:
        # Disassociate sessions tied to these lectures
        db.query(Session).filter(Session.lecture_id.in_(lecture_ids)).update({Session.lecture_id: None}, synchronize_session=False)
        db.query(Lecture).filter(Lecture.id.in_(lecture_ids)).delete(synchronize_session=False)

    # Delete course itself
    db.delete(course)
    db.commit()
    return True


def delete_student(db: Session, student_id: str) -> bool:
    """Deletes a student record, associated user account, and all enrollments."""
    clean_id = student_id.strip()
    student = get_student_by_id(db, clean_id)
    if not student:
        student = get_student_by_roll_no(db, clean_id)

    if not student:
        # Check if user exists with this username
        user = get_user_by_username(db, clean_id)
        if user:
            db.delete(user)
            db.commit()
            return True
        return False

    user_id = student.user_id
    # Delete student enrollments
    db.query(Enrollment).filter(Enrollment.student_id == student.id).delete()
    # Delete student attendance history
    db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.student_id).delete()
    # Delete student profile
    db.delete(student)
    # Delete associated user account
    user = None
    if user_id:
        user = get_user_by_id(db, user_id)
    if not user:
        user = get_user_by_username(db, student.student_id)
    if not user and student.roll_no:
        user = get_user_by_username(db, student.roll_no)
    if not user:
        user = get_user_by_username(db, clean_id)

    if user:
        db.delete(user)

    db.commit()
    return True
