from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import re


class GenerateReportRequest(BaseModel):
    report_type : str = "monthly_summary"
    # monthly_summary | attendance | leave | performance | department
    period      : Optional[str] = None
    # "2026-03" for monthly, "2026" for annual, leave blank for current
    department_id: Optional[int] = None
    # filter by department (None = all departments)


class ReportOut(BaseModel):
    id           : int
    report_type  : str
    period       : Optional[str]
    title        : str
    narrative    : Optional[str]
    content      : Optional[Dict[str, Any]]
    generated_by : str
    created_at   : Optional[datetime]

    model_config = {"from_attributes": True}


class ReportSummary(BaseModel):
    id          : int
    report_type : str
    period      : Optional[str]
    title       : str
    created_at  : Optional[datetime]

    model_config = {"from_attributes": True}
