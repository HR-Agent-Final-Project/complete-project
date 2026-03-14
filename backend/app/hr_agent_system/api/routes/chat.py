"""api/routes/chat.py — POST /api/chat"""
from fastapi import APIRouter
from core.state import blank_state
from core.graph import get_hr_graph
from models.schemas import ChatRequest, ChatResponse
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    graph     = get_hr_graph()
    state     = blank_state(req.employee_id, req.message, req.user_role)
    thread_id = req.session_id or str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}
    result    = graph.invoke(state, config)
    return ChatResponse(
        response   = result.get("agent_response", "No response."),
        agent_used = result.get("current_agent", ""),
        message    = "OK",
    )
