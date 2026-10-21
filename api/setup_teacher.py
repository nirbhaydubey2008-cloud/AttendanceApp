#!/usr/bin/env python3
"""
api/setup_teacher.py
Secure CLI script for provisioning teacher accounts.
Public registration is strictly prohibited; teacher accounts must be provisioned
via this administrative tool.

Usage:
  python api/setup_teacher.py --username prof_dubey --name "Prof. Nirbhay Dubey" --employee-id EMP001 --password "SecurePass123!"
Or interactively:
  python api/setup_teacher.py
"""

import os
import sys
import argparse
import getpass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import SessionLocal, init_db
import database.crud as crud
from services.auth_service import hash_password


def setup_teacher(username, name, employee_id, password, email=None, department="Computer Science & Engineering"):
    init_db()
    db = SessionLocal()
    try:
        # Check if username or email exists
        if crud.get_user_by_username(db, username):
            print(f"[ERROR] User with username '{username}' already exists.")
            return False

        if email and crud.get_user_by_email(db, email):
            print(f"[ERROR] User with email '{email}' already exists.")
            return False

        # Hash password securely
        pw_hash = hash_password(password)

        # Create user
        user = crud.create_user(
            db,
            username=username,
            hashed_password=pw_hash,
            role="TEACHER",
            email=email,
            is_active=True,
            must_change_password=False
        )

        # Create teacher profile
        teacher = crud.create_teacher(
            db,
            user_id=user.id,
            employee_id=employee_id,
            name=name,
            department=department
        )

        # Ensure default course exists for this teacher
        default_course = crud.get_course_by_code(db, "CS101")
        if not default_course:
            crud.create_course(
                db,
                course_code="CS101",
                title="Introduction to Computer Science & Algorithms",
                teacher_id=teacher.id,
                description="Core introductory lecture course on computer algorithms and perception systems."
            )
            print(f"  [INFO] Created default course CS101 assigned to {name}.")
        else:
            if not default_course.teacher_id:
                default_course.teacher_id = teacher.id
                db.commit()
                print(f"  [INFO] Linked existing course CS101 to {name}.")

        # Log action
        crud.create_audit_log(
            db,
            action="TEACHER_PROVISIONED",
            target_entity=f"Teacher:{employee_id}",
            user_id=user.id,
            details=f"Teacher account {username} ({name}) provisioned via CLI."
        )

        print("\n" + "=" * 60)
        print("TEACHER ACCOUNT PROVISIONED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Username    : {username}")
        print(f"Name        : {name}")
        print(f"Employee ID : {employee_id}")
        print(f"Role        : TEACHER")
        print(f"Department  : {department}")
        print("=" * 60)
        return True
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Administrative provisioning script for Teacher accounts.")
    parser.add_argument("--username", help="Teacher username (e.g. prof_dubey)")
    parser.add_argument("--name", help="Teacher full name (e.g. Prof. Nirbhay Dubey)")
    parser.add_argument("--employee-id", help="Institutional employee ID (e.g. EMP001)")
    parser.add_argument("--password", help="Password for teacher account (or prompt securely)")
    parser.add_argument("--email", help="Optional institutional email")
    parser.add_argument("--department", default="Computer Science & Engineering", help="Academic department")

    args = parser.parse_args()

    username = args.username or input("Enter Teacher Username: ").strip()
    name = args.name or input("Enter Teacher Full Name: ").strip()
    employee_id = args.employee_id or input("Enter Employee ID: ").strip()
    email = args.email or input("Enter Institutional Email (optional, press Enter to skip): ").strip()
    if not email:
        email = None
    department = args.department or "Computer Science & Engineering"

    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Enter Secure Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    if len(password) < 6:
        print("[ERROR] Password must be at least 6 characters long.")
        sys.exit(1)

    success = setup_teacher(
        username=username,
        name=name,
        employee_id=employee_id,
        password=password,
        email=email,
        department=department
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
