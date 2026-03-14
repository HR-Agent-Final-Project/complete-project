"""api/routes/leave.py — Leave management endpoints"""
from fastapi import APIRouter
from core.state import blank_state
from core.graph import get_hr_graph
from models.schemas import LeaveApplyRequest, LeaveResponse
import uuid

router = APIRouter()

@router.post("/leave/apply", response_model=LeaveResponse)
async def apply_leave(req: LeaveApplyRequest):
    graph  = get_hr_graph()
    state  = blank_state(
        employee_id = req.employee_id,
        user_input  = f"Apply {req.days} days {req.leave_type}",
        intent      = "leave_request",
        task_data   = {
            "leave_type":      req.leave_type,
            "leave_type_id":   req.leave_type_id,
            "leave_type_code": req.leave_type[:2].upper(),
            "start_date":      req.start_date,
            "end_date":        req.end_date,
            "days":            req.days,
            "reason":          req.reason,
            "is_half_day":     req.is_half_day,
        },
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return LeaveResponse(
        decision     = result.get("decision", "PENDING"),
        explanation  = result.get("decision_explanation", ""),
        message      = result.get("agent_response", ""),
        needs_review = result.get("requires_human_review", False),
    )

@router.post("/leave/{leave_id}/resume")
async def resume_leave_review(leave_id: int, thread_id: str, hr_decision: str = "approve"):
    """Resume a paused leave graph after HR review."""
    graph  = get_hr_graph()
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(None, config)
    return {"message": "Leave review resumed.", "decision": result.get("decision")}
