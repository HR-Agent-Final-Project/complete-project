"""
Role model.
Defines job roles AND system access levels.

access_level:
  1 = Employee      → sees only own data
  2 = HR Staff      → sees team data
  3 = HR Manager    → full HR access
  4 = Admin         → full system access
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(100), unique=True, nullable=False)  # "Software Engineer"
    code         = Column(String(30),  unique=True, nullable=False)  # "SWE"
    description  = Column(Text, nullable=True)
    access_level = Column(Integer, default=1, nullable=False)        # 1 to 4
    base_salary  = Column(Numeric(12, 2), nullable=True)             # LKR
    is_active    = Column(Boolean, default=True, nullable=False)

    # One role has many employees
    employees    = relationship("Employee", back_populates="role")

    def __repr__(self):
        return f"<Role {self.code}: {self.title} (level {self.access_level})>"