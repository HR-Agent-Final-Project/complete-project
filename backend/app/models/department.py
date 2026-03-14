"""
Department model.
Example departments: Engineering, HR, Finance, Sales
"""

from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False)  # "Engineering"
    code        = Column(String(20),  unique=True, nullable=False)  # "ENG"
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)

    # One department has many employees
    employees   = relationship("Employee", back_populates="department")

    def __repr__(self):
        return f"<Department {self.code}: {self.name}>"