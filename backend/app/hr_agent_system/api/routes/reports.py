"""api/routes/reports.py — Reporting & Analytics endpoints"""
from fastapi import APIRouter
from core.state import blank_state
from core.graph import get_hr_graph
from models.schemas import ReportRequest
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/reports/generate")
async def generate_report(req: ReportRequest):
    graph  = get_hr_graph()
    period = req.period or datetime.now().strftime("%Y-%m")
    state  = blank_state(
        user_input  = f"Generate {req.report_type} report for {period}",
        role        = req.generated_by,
        intent      = "analytics_report",
        task_data   = {"report_type": req.report_type, "period": period,
                       "department": req.department},
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return result.get("structured_output", {})

@router.get("/reports/monthly")
async def monthly_report():
    period = datetime.now().strftime("%Y-%m")
    req    = ReportRequest(report_type="monthly_summary", period=period)
    return await generate_report(req)
