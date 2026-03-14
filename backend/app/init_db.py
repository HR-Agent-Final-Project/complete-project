"""
Database initialization script.

Run this ONCE to create all tables and seed default data:
    uv run python db.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal
from app.models.base import Base
import app.models  # noqa — triggers all model imports


def create_all_tables():
    Base.metadata.create_all(bind=engine)
    print("All tables created.")


def seed_departments(db: Session):
    from app.models.department import Department

    departments = [
        Department(name="Human Resources", code="HR",    description="HR and people management"),
        Department(name="Engineering",      code="ENG",   description="Software development"),
        Department(name="Finance",          code="FIN",   description="Finance and accounting"),
        Department(name="Sales",            code="SALES", description="Sales and business development"),
        Department(name="Operations",       code="OPS",   description="Day-to-day operations"),
        Department(name="Management",       code="MGMT",  description="Senior management"),
    ]

    for dept in departments:
        exists = db.query(Department).filter(Department.code == dept.code).first()
        if not exists:
            db.add(dept)

    db.commit()
    print("Departments seeded.")


def seed_roles(db: Session):
    from app.models.role import Role

    roles = [
        Role(title="Software Engineer",        code="SWE",    access_level=1, base_salary=150000),
        Role(title="Senior Software Engineer",  code="SSE",    access_level=1, base_salary=220000),
        Role(title="UI/UX Designer",            code="UIUX",   access_level=1, base_salary=130000),
        Role(title="HR Executive",              code="HRE",    access_level=2, base_salary=120000),
        Role(title="HR Manager",                code="HRM",    access_level=3, base_salary=200000),
        Role(title="Finance Officer",           code="FINO",   access_level=1, base_salary=130000),
        Role(title="Sales Executive",           code="SALE",   access_level=1, base_salary=110000),
        Role(title="Operations Manager",        code="OPSMGR", access_level=2, base_salary=180000),
        Role(title="System Administrator",      code="SYSADM", access_level=4, base_salary=160000),
        Role(title="General Manager",           code="GM",     access_level=3, base_salary=350000),
    ]

    for role in roles:
        exists = db.query(Role).filter(Role.code == role.code).first()
        if not exists:
            db.add(role)

    db.commit()
    print("Roles seeded.")


def seed_leave_types(db: Session):
    from app.models.leave import LeaveType

    leave_types = [
        LeaveType(
            name="Annual Leave", code="AL",
            description="Paid annual vacation leave.",
            max_days_per_year=14, max_consecutive_days=14,
            requires_document=False, is_paid=True,
        ),
        LeaveType(
            name="Sick Leave", code="SL",
            description="Leave due to illness.",
            max_days_per_year=7, max_consecutive_days=3,
            requires_document=True, is_paid=True,
        ),
        LeaveType(
            name="Casual Leave", code="CL",
            description="Short-notice personal leave.",
            max_days_per_year=7, max_consecutive_days=3,
            requires_document=False, is_paid=True,
        ),
        LeaveType(
            name="Maternity Leave", code="ML",
            description="Paid maternity leave — Sri Lanka labor law.",
            max_days_per_year=84, max_consecutive_days=84,
            requires_document=True, is_paid=True, gender_specific="female",
        ),
        LeaveType(
            name="Paternity Leave", code="PL",
            description="Leave for fathers on birth of child.",
            max_days_per_year=3, max_consecutive_days=3,
            requires_document=True, is_paid=True,
        ),
        LeaveType(
            name="No Pay Leave", code="NPL",
            description="Unpaid leave when other balances exhausted.",
            max_days_per_year=30, max_consecutive_days=30,
            requires_document=False, is_paid=False,
        ),
        LeaveType(
            name="Lieu Leave", code="LL",
            description="Leave in lieu of working on a public holiday.",
            max_days_per_year=14, max_consecutive_days=5,
            requires_document=False, is_paid=True,
        ),
    ]

    for lt in leave_types:
        exists = db.query(LeaveType).filter(LeaveType.code == lt.code).first()
        if not exists:
            db.add(lt)

    db.commit()
    print("Leave types seeded.")


def seed_admin_user(db: Session):
    from app.models.employee import Employee, EmployeeStatus
    from app.models.role import Role
    from app.models.department import Department
    from passlib.context import CryptContext
    from datetime import date

    exists = db.query(Employee).filter(Employee.employee_number == "EMP001").first()
    if exists:
        print("Admin user already exists, skipping.")
        return

    # Use a stable pure-passlib scheme for seeding to avoid pbkdf2_sha256 backend
    # compatibility issues during local setup.
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    hr_role = db.query(Role).filter(Role.code == "SYSADM").first()
    hr_dept = db.query(Department).filter(Department.code == "HR").first()

    admin = Employee(
        employee_number = "EMP001",
        first_name      = "Admin",
        last_name       = "User",
        full_name       = "Admin User",
        personal_email  = "admin@company.com",
        work_email      = "admin@company.com",
        hashed_password = pwd_context.hash("Admin@123"),
        role_id         = hr_role.id if hr_role else None,
        department_id   = hr_dept.id if hr_dept else None,
        hire_date       = date.today(),
        status          = EmployeeStatus.ACTIVE,
        is_active       = True,
        base_salary     = 160000,
        language_pref   = "en",
    )
    db.add(admin)
    db.commit()
    print("Admin user created cp1252 admin@company.com / Admin@123")
    print("Change this password after first login!")


def main():
    print("\n Initializing AI-HR database...\n")

    create_all_tables()

    db = SessionLocal()
    try:
        seed_departments(db)
        seed_roles(db)
        seed_leave_types(db)
        seed_admin_user(db)
    finally:
        db.close()

    print("\n Done! Now run:")
    print("   uv run uvicorn main:app --reload\n")


if __name__ == "__main__":
    main()
