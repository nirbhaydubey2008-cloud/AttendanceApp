"""
database/migrate.py
Non-destructive migration script to upgrade database schema with RBAC models.
Safely adds new tables and columns while preserving all existing sessions and records.
"""

import os
import sys
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import engine, Base, SessionLocal
import database.models  # ensure models are loaded

def run_migration():
    print("=" * 60)
    print("RUNNING DATABASE MIGRATION: Phase 2 (RBAC Schema)")
    print("=" * 60)

    # 1. Ensure all new tables are created
    print("Step 1: Creating new ORM tables...")
    Base.metadata.create_all(bind=engine)
    print("  [PASS] Tables created/verified.")

    # 2. Inspect existing columns in students and sessions using sqlite3
    db_path = "attendance.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check students columns
    student_cols = [row[1] for row in cursor.execute("PRAGMA table_info(students);").fetchall()]
    print(f"Students table columns: {student_cols}")
    if "user_id" not in student_cols:
        print("Adding column 'user_id' to students table...")
        cursor.execute("ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id);")
        print("  [PASS] Added user_id to students.")
    if "initial_password" not in student_cols:
        print("Adding column 'initial_password' to students table...")
        cursor.execute("ALTER TABLE students ADD COLUMN initial_password VARCHAR(100);")
        print("  [PASS] Added initial_password to students.")
    else:
        print("  [INFO] Column initial_password already exists in students.")

    # Check sessions columns
    session_cols = [row[1] for row in cursor.execute("PRAGMA table_info(sessions);").fetchall()]
    print(f"Sessions table columns: {session_cols}")
    if "lecture_id" not in session_cols:
        print("Adding column 'lecture_id' to sessions table...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN lecture_id INTEGER REFERENCES lectures(id);")
        print("  [PASS] Added lecture_id to sessions.")

    if "teacher_id" not in session_cols:
        print("Adding column 'teacher_id' to sessions table...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN teacher_id INTEGER REFERENCES teachers(id);")
        print("  [PASS] Added teacher_id to sessions.")

    if "status" not in session_cols:
        print("Adding column 'status' to sessions table...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN status VARCHAR(20) DEFAULT 'COMPLETED';")
        print("  [PASS] Added status to sessions.")

    conn.commit()

    # Verify counts
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print("\nVerified Tables in SQLite:")
    for t in sorted(tables):
        count = cursor.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
        print(f"  - {t:<22} : {count} records")

    conn.close()
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY WITH ZERO DATA LOSS!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
