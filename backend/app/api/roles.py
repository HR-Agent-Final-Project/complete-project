"""
Role management API.
Endpoints for creating and managing job roles and access levels.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

router = APIRouter()


_ACCESS_LABELS = {
    1: "Employee",
    2: "HR Staff",
    3: "HR Manager",
    4: "Admin",
}


def _role_to_dict(role, employee_count: int = 0) -> dict:
    return {
        "id":             role.id,
        "title":          role.title,
        "code":           role.code,
        "access_level":   role.access_level,
        "access_label":   _ACCESS_LABELS.get(role.access_level, "Unknown"),
        "description":    role.description,
        "base_salary":    float(role.base_salary) if role.base_salary else None,
        "is_active":      role.is_active,
        "employee_count": employee_count,
    }


def _get_employee_count(role_id: int, db: Session) -> int:
    from app.models.employee import Employee
    return db.query(Employee).filter(
        Employee.role_id == role_id,
        Employee.is_active == True
    ).count()


# GET /api/roles/ — List all roles

@router.get("", summary="List all roles — HR Staff+")
def list_roles(
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    roles = db.query(Role).order_by(Role.access_level, Role.title).all()
    return [_role_to_dict(r, _get_employee_count(r.id, db)) for r in roles]


# GET /api/roles/{id} — Get one role

@router.get("/{role_id}", summary="Get role by ID — HR Staff+")
def get_role(
    role_id:      int,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role #{role_id} not found."
        )
    return _role_to_dict(role, _get_employee_count(role_id, db))


# POST /api/roles/ — Create role (Admin only)

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create role — Admin only")
def create_role(
    body:         RoleCreate,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(4)),
):
    existing = db.query(Role).filter(
        (Role.title == body.title) | (Role.code == body.code)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with that title or code already exists."
        )

    role = Role(
        title        = body.title,
        code         = body.code,
        access_level = body.access_level,
        description  = body.description,
        base_salary  = body.base_salary,
        is_active    = True,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    return {
        "message":      f"Role '{role.title}' created successfully.",
        "id":           role.id,
        "access_level": role.access_level,
        "access_label": _ACCESS_LABELS.get(role.access_level),
    }


# PUT /api/roles/{id} — Update role (Admin only)

@router.put("/{role_id}", summary="Update role — Admin only")
def update_role(
    role_id:      int,
    body:         RoleUpdate,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(4)),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role #{role_id} not found."
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)

    return {
        "message": f"Role '{role.title}' updated successfully.",
        "id":      role.id,
    }


# DELETE /api/roles/{id} — Delete role (Admin only)

@router.delete("/{role_id}", summary="Delete role — Admin only")
def delete_role(
    role_id:      int,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(4)),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role #{role_id} not found."
        )

    assigned = _get_employee_count(role_id, db)
    if assigned > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {assigned} active employee(s) are assigned to this role."
        )

    title = role.title
    db.delete(role)
    db.commit()

    return {"message": f"Role '{title}' deleted permanently."}
