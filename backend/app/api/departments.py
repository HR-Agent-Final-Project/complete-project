"""
Department management API.
Endpoints for creating and managing departments.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate

router = APIRouter()


def _dept_to_dict(dept, employee_count: int = 0) -> dict:
    return {
        "id":             dept.id,
        "name":           dept.name,
        "code":           dept.code,
        "description":    dept.description,
        "is_active":      dept.is_active,
        "employee_count": employee_count,
    }


def _get_employee_count(dept_id: int, db: Session) -> int:
    from app.models.employee import Employee
    return db.query(Employee).filter(
        Employee.department_id == dept_id,
        Employee.is_active == True
    ).count()


# GET /api/departments/ — List all departments

@router.get("/", summary="List all departments — HR Staff+")
def list_departments(
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    departments = db.query(Department).order_by(Department.name).all()
    return [_dept_to_dict(d, _get_employee_count(d.id, db)) for d in departments]


# GET /api/departments/{id} — Get one department

@router.get("/{department_id}", summary="Get department by ID — HR Staff+")
def get_department(
    department_id: int,
    db:            Session = Depends(get_db),
    current_user           = Depends(require_role(2)),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department #{department_id} not found."
        )
    return _dept_to_dict(dept, _get_employee_count(department_id, db))


# POST /api/departments/ — Create department

@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create department — HR Manager+")
def create_department(
    body:         DepartmentCreate,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),
):
    existing = db.query(Department).filter(
        (Department.name == body.name) | (Department.code == body.code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with that name or code already exists."
        )

    dept = Department(
        name        = body.name,
        code        = body.code,
        description = body.description,
        is_active   = True,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    return {
        "message": f"Department '{dept.name}' created successfully.",
        "id":      dept.id,
        "code":    dept.code,
    }


# PUT /api/departments/{id} — Update department

@router.put("/{department_id}", summary="Update department — HR Manager+")
def update_department(
    department_id: int,
    body:          DepartmentUpdate,
    db:            Session = Depends(get_db),
    current_user           = Depends(require_role(3)),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department #{department_id} not found."
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(dept, field, value)

    db.commit()
    db.refresh(dept)

    return {
        "message": f"Department '{dept.name}' updated successfully.",
        "id":      dept.id,
    }


# DELETE /api/departments/{id} — Delete department (Admin only)

@router.delete("/{department_id}", summary="Delete department — Admin only")
def delete_department(
    department_id: int,
    db:            Session = Depends(get_db),
    current_user           = Depends(require_role(4)),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department #{department_id} not found."
        )

    active_count = _get_employee_count(department_id, db)
    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {active_count} active employee(s) still assigned to this department."
        )

    name = dept.name
    db.delete(dept)
    db.commit()

    return {"message": f"Department '{name}' deleted permanently."}
