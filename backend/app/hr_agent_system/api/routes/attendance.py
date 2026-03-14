"""api/routes/attendance.py — Attendance endpoints"""
from fastapi import APIRouter
from core.state import blank_state
from core.graph import get_hr_graph
from models.schemas import AttendanceCheckInRequest
import uuid

router = APIRouter()

@router.post("/attendance/checkin")
async def checkin(req: AttendanceCheckInRequest):
    graph  = get_hr_graph()
    state  = blank_state(
        employee_id = req.employee_id,
        user_input  = req.action,
        intent      = "attendance",
        task_data   = {"action": req.action, "image_base64": req.image_base64,
                       "employee_id": req.employee_id},
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return {
        "status":   result.get("decision"),
        "message":  result.get("agent_response"),
        "details":  result.get("structured_output"),
    }
