"""
api/chat.py
────────────
Module 5 — AI Chat Agent REST API

The chat agent is a LangGraph ReAct loop backed by ChromaDB (RAG) and live DB data.
It maintains multi-turn conversation history via ChatSession/ChatMessage tables.

Endpoints:
  POST   /sessions               → create a new chat session
  GET    /sessions               → list my sessions
  GET    /sessions/{id}          → get session with full message history
  DELETE /sessions/{id}          → delete a session
  POST   /sessions/{id}/message  → send a message, get AI response
  POST   /quick                  → one-shot message (no session saved)
  GET    /knowledge/status       → check if ChromaDB is loaded

Architecture:
  User message
      ↓
  ChatAgent (LangGraph ReAct)
      ├─ search_hr_policy()      ← ChromaDB semantic search
      ├─ search_company_handbook() ← ChromaDB handbook search
      ├─ get_my_leave_balances() ← live DB
      ├─ get_my_attendance()     ← live DB
      └─ get_my_performance()    ← live DB
      ↓
  AI response saved to ChatMessage table
"""

import json
import logging
from typing import List, Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_employee
from app.models.employee import Employee
from app.models.chat import ChatSession, ChatMessage
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType, LeaveStatus
from app.models.attendance import Attendance
from app.models.performance import PerformanceReview
from app.schemas.chat import (
    ChatSessionOut, ChatSessionSummary,
    SendMessageRequest, QuickChatRequest, ChatResponseOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Agent invocation timeout in seconds — prevents holding DB connections indefinitely
# when OpenAI is slow or rate-limited.
AGENT_TIMEOUT_SECONDS = 120

# ── LangGraph Chat Agent — one LLM instance shared across requests ─────────────
# The LLM itself is stateless; per-request state (employee_id, db) is injected
# via tool closures each time _run_agent() is called.
_shared_llm = None


def _get_llm():
    """Return a cached ChatOpenAI instance, building it on first call."""
    global _shared_llm
    if _shared_llm is None and settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        _shared_llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )
    return _shared_llm


def _build_agent(employee_id: int, db: Session):
    """
    Builds a LangGraph ReAct agent with tools bound to the current employee.
    Tools are closures that capture employee_id + db session.
    The underlying LLM is shared/cached via _get_llm() to avoid re-initialisation.
    """
    from langchain.tools import tool
    from langgraph.prebuilt import create_react_agent

    llm = _get_llm()
    if llm is None:
        return None

    # ── Tool 1: HR Policy RAG ────────────────────────────────────────────────

    @tool
    def search_hr_policy(query: str) -> str:
        """
        Search the company HR policy documents for rules about leave,
        attendance, overtime, conduct, probation, and entitlements.
        Use this for any policy question.
        """
        try:
            import chromadb
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
            )
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            store  = Chroma(
                client=client,
                collection_name="hr_policies",
                embedding_function=embeddings,
            )
            retriever = store.as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(query)
            if not docs:
                return json.dumps({"found": False, "message": "No relevant policy found."})
            return json.dumps({
                "found": True,
                "results": [
                    {"rank": i + 1, "content": d.page_content,
                     "source": d.metadata.get("file", "hr_policy")}
                    for i, d in enumerate(docs)
                ],
            })
        except Exception as e:
            return json.dumps({"found": False, "error": str(e),
                               "message": "Policy search unavailable. Please check ChromaDB."})

    # ── Tool 2: Company Handbook RAG ─────────────────────────────────────────

    @tool
    def search_company_handbook(query: str) -> str:
        """
        Search the company employee handbook for conduct rules, values,
        disciplinary procedures, dress code, and general workplace guidelines.
        """
        try:
            import chromadb
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
            )
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            store  = Chroma(
                client=client,
                collection_name="company_culture",
                embedding_function=embeddings,
            )
            retriever = store.as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(query)
            if not docs:
                return json.dumps({"found": False, "message": "No handbook entry found."})
            return json.dumps({
                "found": True,
                "results": [{"rank": i + 1, "content": d.page_content}
                             for i, d in enumerate(docs)],
            })
        except Exception as e:
            return json.dumps({"found": False, "error": str(e)})

    # ── Tool 3: Live Leave Balances ───────────────────────────────────────────

    @tool
    def get_my_leave_balances(dummy: str = "") -> str:
        """
        Fetch the current employee's leave balances for all leave types.
        Returns remaining days for Annual Leave, Sick Leave, Casual Leave, etc.
        Use when employee asks 'how many leave days do I have?'
        """
        try:
            balances = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year        == date.today().year,
            ).all()
            if not balances:
                return json.dumps({"found": False, "message": "No leave balances found."})
            return json.dumps({
                "found": True,
                "year": date.today().year,
                "balances": [
                    {
                        "type":      b.leave_type.name if b.leave_type else "Unknown",
                        "code":      b.leave_type.code if b.leave_type else "",
                        "total":     float(b.total_days),
                        "used":      float(b.used_days),
                        "pending":   float(b.pending_days),
                        "remaining": float(b.remaining_days),
                    }
                    for b in balances if b.leave_type
                ],
            })
        except Exception as e:
            return json.dumps({"found": False, "error": str(e)})

    # ── Tool 4: Live Attendance Stats ─────────────────────────────────────────

    @tool
    def get_my_attendance(days: int = 30) -> str:
        """
        Fetch the current employee's attendance statistics for the last N days.
        Returns attendance percentage, present/absent/late counts, overtime hours.
        Use when employee asks about attendance rate, late arrivals, or OT.
        """
        try:
            since   = date.today() - timedelta(days=days)
            records = db.query(Attendance).filter(
                Attendance.employee_id == employee_id,
                Attendance.work_date   >= since,
            ).all()
            if not records:
                return json.dumps({"message": f"No attendance records in last {days} days."})
            total   = len(records)
            present = sum(1 for r in records if not r.is_absent)
            late    = sum(1 for r in records if r.is_late)
            ot_hrs  = sum(r.overtime_hours or 0.0 for r in records)
            pct     = round(present / total * 100, 1) if total > 0 else 100.0
            return json.dumps({
                "period_days":        days,
                "total_records":      total,
                "present_days":       present,
                "absent_days":        total - present,
                "late_days":          late,
                "overtime_hours":     round(ot_hrs, 2),
                "attendance_percent": pct,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ── Tool 5: Performance Summary ───────────────────────────────────────────

    @tool
    def get_my_performance(dummy: str = "") -> str:
        """
        Fetch the current employee's latest performance review scores.
        Returns overall score, rating, attendance score, punctuality score.
        Use when employee asks about their performance, KPI, or appraisal.
        """
        try:
            review = db.query(PerformanceReview).filter(
                PerformanceReview.employee_id == employee_id,
            ).order_by(PerformanceReview.period_end.desc()).first()
            if not review:
                return json.dumps({"found": False, "message": "No performance reviews found."})
            return json.dumps({
                "found":             True,
                "period_type":       review.period_type,
                "period_start":      str(review.period_start)[:10],
                "period_end":        str(review.period_end)[:10],
                "overall_score":     review.overall_score,
                "rating":            review.rating,
                "attendance_score":  review.attendance_score,
                "punctuality_score": review.punctuality_score,
                "overtime_score":    review.overtime_score,
                "ai_summary":        review.ai_summary,
                "requires_pip":      review.requires_pip,
                "is_promotion_eligible": review.is_promotion_eligible,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ── Tool 6: Apply Leave ─────────────────────────────────────────────────

    @tool
    def apply_leave_for_me(
        leave_type_code: str,
        start_date: str,
        end_date: str,
        reason: str,
        is_half_day: bool = False,
    ) -> str:
        """
        Apply for leave on behalf of the current employee. This CREATES a real
        leave request in the database and triggers the AI review engine.

        Parameters:
          leave_type_code: The leave type code — one of AL (Annual), SL (Sick),
                          CL (Casual), ML (Maternity), PL (Paternity), NPL (No Pay)
          start_date: Start date in ISO format YYYY-MM-DD (e.g. "2026-04-01")
          end_date:   End date in ISO format YYYY-MM-DD (e.g. "2026-04-03")
          reason:     The reason for the leave request
          is_half_day: True if applying for half-day leave (default False)

        Use this when the employee says things like:
          "I want to take annual leave from April 1 to April 3"
          "Apply sick leave for tomorrow, I'm not feeling well"
          "I need casual leave on March 20 for a personal matter"

        IMPORTANT: Always confirm the details with the employee BEFORE calling
        this tool. Ask them to confirm the leave type, dates, and reason.
        """
        try:
            from datetime import date as date_cls, timedelta

            # Validate leave type
            leave_type = db.query(LeaveType).filter(
                LeaveType.code == leave_type_code.upper(),
                LeaveType.is_active == True,
            ).first()
            if not leave_type:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid leave type code '{leave_type_code}'. "
                             f"Valid codes: AL, SL, CL, ML, PL, NPL",
                })

            # Parse and validate dates
            try:
                s_date = date_cls.fromisoformat(start_date)
                e_date = date_cls.fromisoformat(end_date)
            except ValueError:
                return json.dumps({
                    "success": False,
                    "error": "Invalid date format. Use YYYY-MM-DD.",
                })

            if s_date > e_date:
                return json.dumps({
                    "success": False,
                    "error": "Start date must be before or equal to end date.",
                })
            if s_date < date_cls.today():
                return json.dumps({
                    "success": False,
                    "error": "Cannot apply for past dates.",
                })

            # Count working days (exclude Sundays)
            if is_half_day:
                days = 0.5
            else:
                days = 0.0
                current = s_date
                while current <= e_date:
                    if current.weekday() != 6:  # Exclude Sundays
                        days += 1.0
                    current += timedelta(days=1)

            # Check for overlapping leave
            overlap = db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status.in_(["pending", "approved", "escalated"]),
                LeaveRequest.start_date <= e_date,
                LeaveRequest.end_date >= s_date,
            ).first()
            if overlap:
                return json.dumps({
                    "success": False,
                    "error": f"You already have a {overlap.status} leave from "
                             f"{overlap.start_date} to {overlap.end_date}. "
                             f"Cancel it first or choose different dates.",
                })

            # Create the leave request
            leave_request = LeaveRequest(
                employee_id=employee_id,
                leave_type_id=leave_type.id,
                start_date=s_date,
                end_date=e_date,
                total_days=days,
                days_requested=days,
                reason=reason,
                is_half_day=is_half_day,
                status=LeaveStatus.PENDING,
            )
            db.add(leave_request)
            db.commit()
            db.refresh(leave_request)

            # Run AI review engine (same logic as POST /api/leave/apply)
            from app.models.employee import Employee as EmpModel
            employee = db.query(EmpModel).filter(EmpModel.id == employee_id).first()
            from app.api.leave import _run_ai_review
            ai_result = _run_ai_review(db, leave_request, employee, leave_type)

            return json.dumps({
                "success": True,
                "leave_id": leave_request.id,
                "leave_type": leave_type.name,
                "start_date": str(s_date),
                "end_date": str(e_date),
                "days": days,
                "is_half_day": is_half_day,
                "ai_decision": ai_result["decision"],
                "ai_reasoning": ai_result["reasoning"],
                "status": leave_request.status.value if hasattr(leave_request.status, 'value') else str(leave_request.status),
                "next_step": ai_result.get("next_step", ""),
            })

        except Exception as e:
            logger.error("[Chat] apply_leave_for_me error: %s", e)
            return json.dumps({"success": False, "error": str(e)})

    # ── Tool 7: Cancel Leave ─────────────────────────────────────────────────

    @tool
    def cancel_my_leave(leave_id: int) -> str:
        """
        Cancel a pending or escalated leave request for the current employee.

        Parameters:
          leave_id: The ID of the leave request to cancel

        Use this when the employee says:
          "Cancel my leave request"
          "I want to cancel leave #15"
          "Never mind, cancel that leave I just applied for"

        Only pending or escalated leaves can be cancelled.
        """
        try:
            leave = db.query(LeaveRequest).filter(
                LeaveRequest.id == leave_id,
                LeaveRequest.employee_id == employee_id,
            ).first()

            if not leave:
                return json.dumps({
                    "success": False,
                    "error": f"Leave request #{leave_id} not found or doesn't belong to you.",
                })

            status_val = leave.status.value if hasattr(leave.status, 'value') else str(leave.status)
            if status_val not in ("pending", "escalated"):
                return json.dumps({
                    "success": False,
                    "error": f"Cannot cancel a leave that is '{status_val}'. "
                             f"Only pending or escalated leaves can be cancelled. "
                             f"Contact HR for approved leaves.",
                })

            leave.status = LeaveStatus.CANCELLED
            leave.hr_notes = "Cancelled by employee via AI Chat Agent."
            db.commit()

            return json.dumps({
                "success": True,
                "leave_id": leave_id,
                "message": f"Leave request #{leave_id} has been cancelled successfully.",
                "leave_type": leave.leave_type.name if leave.leave_type else "Unknown",
                "dates": f"{leave.start_date} to {leave.end_date}",
            })

        except Exception as e:
            logger.error("[Chat] cancel_my_leave error: %s", e)
            return json.dumps({"success": False, "error": str(e)})

    # ── Tool 8: List My Leave Requests ────────────────────────────────────────

    @tool
    def get_my_leave_requests(status_filter: str = "") -> str:
        """
        Fetch the current employee's recent leave requests with their status.

        Parameters:
          status_filter: Optional filter — "pending", "approved", "rejected",
                        "escalated", "cancelled", or "" for all

        Use this when the employee asks:
          "What are my recent leave requests?"
          "Do I have any pending leaves?"
          "Show me my leave history"
          "What's the status of my leave?"
        """
        try:
            q = db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == employee_id,
            )
            if status_filter and status_filter.strip():
                q = q.filter(LeaveRequest.status == status_filter.strip().lower())

            leaves = q.order_by(LeaveRequest.created_at.desc()).limit(10).all()

            if not leaves:
                return json.dumps({
                    "found": False,
                    "message": "No leave requests found"
                              + (f" with status '{status_filter}'." if status_filter else "."),
                })

            return json.dumps({
                "found": True,
                "total": len(leaves),
                "requests": [
                    {
                        "id": l.id,
                        "leave_type": l.leave_type.name if l.leave_type else "Unknown",
                        "code": l.leave_type.code if l.leave_type else "",
                        "start_date": str(l.start_date),
                        "end_date": str(l.end_date),
                        "days": l.days_requested or l.total_days,
                        "reason": l.reason,
                        "status": l.status.value if hasattr(l.status, 'value') else str(l.status),
                        "ai_decision": l.ai_decision,
                        "created_at": str(l.created_at)[:10] if l.created_at else None,
                    }
                    for l in leaves
                ],
            })

        except Exception as e:
            logger.error("[Chat] get_my_leave_requests error: %s", e)
            return json.dumps({"found": False, "error": str(e)})

    # ── System Prompt ────────────────────────────────────────────────────────

    SYSTEM_PROMPT = """You are a friendly, knowledgeable HR assistant for a company in Sri Lanka.
Your role is to help employees with HR-related questions AND take actions on their behalf.

How to respond:
- Use your tools to look up accurate policy information and personal data
- Always cite which policy document you're referencing (e.g. "According to the Leave Policy...")
- Give clear, specific answers with actual numbers (days, rates, percentages)
- When you retrieve the employee's personal data, personalise your response
- If you cannot find an answer, say so and suggest contacting HR directly
- Be professional, friendly, and approachable — avoid being robotic

You can answer questions like:
  "How many annual leave days do I have left?"
  "What is the overtime rate on weekends?"
  "What is my attendance percentage this month?"

You can also TAKE ACTIONS directly:
  ✅ Apply for leave: "I want to take annual leave from April 1 to April 3 for a family trip"
  ✅ Cancel leave: "Cancel my pending leave request"
  ✅ Check leave status: "What's the status of my leave requests?"

IMPORTANT RULES for applying leave:
1. Before applying, ALWAYS confirm the details with the employee:
   - Leave type (AL/SL/CL/ML/PL/NPL)
   - Start date and end date
   - Reason for leave
2. If the employee doesn't specify all details, ASK them before proceeding
3. Use get_my_leave_balances first to check if they have enough days
4. After applying, clearly communicate the AI decision (approved/rejected/escalated)
5. Leave type codes: AL=Annual Leave, SL=Sick Leave, CL=Casual Leave,
   ML=Maternity Leave, PL=Paternity Leave, NPL=No Pay Leave

For cancellation:
1. Use get_my_leave_requests to find the leave ID first
2. Only pending or escalated leaves can be cancelled
"""

    tools = [
        search_hr_policy,
        search_company_handbook,
        get_my_leave_balances,
        get_my_attendance,
        get_my_performance,
        apply_leave_for_me,
        cancel_my_leave,
        get_my_leave_requests,
    ]
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


def _run_agent(
    message: str,
    employee_id: int,
    history: List[dict],
    db: Session,
) -> tuple[str, List[str]]:
    """
    Invokes the ReAct agent with message + conversation history.
    Returns (response_text, sources_list).
    Enforces AGENT_TIMEOUT_SECONDS to prevent indefinite blocking.
    """
    import concurrent.futures
    try:
        from langchain_core.messages import HumanMessage, AIMessage

        agent = _build_agent(employee_id, db)
        if agent is None:
            return (
                "AI features are not configured. Please ask the admin to set OPENAI_API_KEY.",
                [],
            )

        # Rebuild message history for LangGraph
        lc_messages = []
        for h in history[-10:]:   # last 10 messages for context window
            if h["role"] == "user":
                lc_messages.append(HumanMessage(content=h["content"]))
            else:
                lc_messages.append(AIMessage(content=h["content"]))
        lc_messages.append(HumanMessage(content=message))

        # Run agent in a thread so we can enforce a hard timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(agent.invoke, {"messages": lc_messages})
            try:
                result = future.result(timeout=AGENT_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "[Chat] Agent timed out after %ss for employee %s",
                    AGENT_TIMEOUT_SECONDS, employee_id,
                )
                return (
                    "The request took too long to process. Please try again or contact HR directly.",
                    [],
                )

        reply   = result["messages"][-1].content

        # Extract sources from tool call messages
        sources = []
        for msg in result["messages"]:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and data.get("found"):
                        for item in data.get("results", []):
                            src = item.get("source")
                            if src and src not in sources:
                                sources.append(src)
                except Exception:
                    pass

        return reply, sources

    except Exception as e:
        import traceback
        logger.error("[Chat] Agent error for employee %s: %s\n%s", employee_id, e, traceback.format_exc())
        return (
            f"Sorry, I encountered an error: {str(e)[:200]}. Please try again or contact HR directly.",
            [],
        )


# ── Helper: get own session or 403 ────────────────────────────────────────────

def _get_session(session_id: int, employee_id: int, db: Session) -> ChatSession:
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    if sess.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return sess


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
def create_session(
    current_user: Employee = Depends(get_current_employee),
    db: Session            = Depends(get_db),
):
    """Create a new empty chat session."""
    sess = ChatSession(employee_id=current_user.id)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return {"session_id": sess.id, "message": "Session created."}


@router.get("/sessions", response_model=List[ChatSessionSummary])
def list_sessions(
    current_user: Employee = Depends(get_current_employee),
    db: Session            = Depends(get_db),
):
    """List all active chat sessions for the current employee."""
    sessions = db.query(ChatSession).filter(
        ChatSession.employee_id == current_user.id,
        ChatSession.is_active   == True,
    ).order_by(ChatSession.id.desc()).all()

    result = []
    for s in sessions:
        result.append(ChatSessionSummary(
            id            = s.id,
            title         = s.title,
            is_active     = s.is_active,
            created_at    = s.created_at,
            message_count = len(s.messages),
        ))
    return result


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
def get_session(
    session_id  : int,
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """Get a session with its full message history."""
    sess = _get_session(session_id, current_user.id, db)
    return ChatSessionOut(
        id         = sess.id,
        title      = sess.title,
        is_active  = sess.is_active,
        created_at = sess.created_at,
        messages   = [
            _msg_to_out(m) for m in sess.messages
        ],
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id  : int,
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """Soft-delete (deactivate) a chat session."""
    sess = _get_session(session_id, current_user.id, db)
    sess.is_active = False
    db.commit()


@router.post("/sessions/{session_id}/message", response_model=ChatResponseOut)
def send_message(
    session_id  : int,
    body        : SendMessageRequest,
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """
    Send a message in an existing session.
    The AI reads the full session history for context.
    """
    sess = _get_session(session_id, current_user.id, db)

    # Save user message
    user_msg = ChatMessage(
        session_id = sess.id,
        role       = "user",
        content    = body.message,
    )
    db.add(user_msg)
    db.flush()  # get id without committing

    # Auto-set session title from first message
    if not sess.title:
        sess.title = body.message[:80] + ("…" if len(body.message) > 80 else "")

    # Build history for agent
    history = [
        {"role": m.role, "content": m.content}
        for m in sess.messages
        if m.id != user_msg.id
    ]

    # Run agent
    reply, sources = _run_agent(body.message, current_user.id, history, db)

    # Save assistant message
    ai_msg = ChatMessage(
        session_id = sess.id,
        role       = "assistant",
        content    = reply,
        sources    = json.dumps(sources) if sources else None,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    return ChatResponseOut(
        session_id = sess.id,
        message_id = ai_msg.id,
        response   = reply,
        sources    = sources,
    )


@router.post("/quick", response_model=ChatResponseOut)
def quick_chat(
    body        : QuickChatRequest,
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """
    One-shot chat — no session history.
    Creates a session automatically and returns the response.
    """
    # Auto-create a session
    sess = ChatSession(
        employee_id = current_user.id,
        title       = body.message[:80] + ("…" if len(body.message) > 80 else ""),
    )
    db.add(sess)
    db.flush()

    # Save user message
    db.add(ChatMessage(session_id=sess.id, role="user", content=body.message))
    db.flush()

    # Run agent with no history
    reply, sources = _run_agent(body.message, current_user.id, [], db)

    # Save response
    ai_msg = ChatMessage(
        session_id = sess.id,
        role       = "assistant",
        content    = reply,
        sources    = json.dumps(sources) if sources else None,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    return ChatResponseOut(
        session_id = sess.id,
        message_id = ai_msg.id,
        response   = reply,
        sources    = sources,
    )


@router.get("/knowledge/status")
def knowledge_status():
    """Check if ChromaDB is loaded and how many policy chunks are available."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        result = {}
        for col in ["hr_policies", "company_culture", "job_descriptions"]:
            try:
                coll  = client.get_collection(col)
                count = coll.count()
                result[col] = {"loaded": True, "chunks": count}
            except Exception:
                result[col] = {"loaded": False, "chunks": 0}
        return {"status": "ok", "collections": result}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


# ── Internal helper ───────────────────────────────────────────────────────────

def _msg_to_out(m: ChatMessage):
    from app.schemas.chat import ChatMessageOut
    sources = []
    if m.sources:
        try:
            sources = json.loads(m.sources)
        except Exception:
            pass
    return ChatMessageOut(
        id         = m.id,
        role       = m.role,
        content    = m.content,
        sources    = sources,
        created_at = m.created_at,
    )


# ── Voice Chat (Whisper STT → Agent → TTS) ──────────────────────────────────

@router.post("/voice")
async def voice_chat(
    audio: UploadFile   = File(...),
    session_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_employee),
    db: Session            = Depends(get_db),
):
    """
    Voice-to-voice chat:
      1. Transcribe uploaded audio with OpenAI Whisper
      2. Run the chat agent on the transcript
      3. Convert AI response to speech with OpenAI TTS
      4. Return JSON with transcript + response text + base64 audio
    """
    import base64
    import io

    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")

    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ── 1. Whisper STT ───────────────────────────────────────────────────────
    audio_bytes = await audio.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file is too small or empty.")

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", io.BytesIO(audio_bytes), audio.content_type or "audio/webm"),
            response_format="text",
        )
    except Exception as e:
        logger.error("[Voice] Whisper transcription failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    user_text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Could not understand the audio. Please try again.")

    # ── 2. Chat Agent ────────────────────────────────────────────────────────
    history = []
    sess = None

    if session_id:
        sess = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.employee_id == current_user.id,
        ).first()
        if sess:
            history = [
                {"role": m.role, "content": m.content}
                for m in sess.messages[-10:]
            ]

    if not sess:
        sess = ChatSession(
            employee_id=current_user.id,
            title=user_text[:80] + ("…" if len(user_text) > 80 else ""),
        )
        db.add(sess)
        db.flush()

    # Save user message
    db.add(ChatMessage(session_id=sess.id, role="user", content=user_text))
    db.flush()

    reply, sources = _run_agent(user_text, current_user.id, history, db)

    # Save AI response
    ai_msg = ChatMessage(
        session_id=sess.id,
        role="assistant",
        content=reply,
        sources=json.dumps(sources) if sources else None,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)

    # ── 3. OpenAI TTS ────────────────────────────────────────────────────────
    tts_audio_b64 = None
    try:
        tts_response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=reply[:4096],  # TTS has a character limit
            response_format="mp3",
        )
        tts_audio_b64 = base64.b64encode(tts_response.content).decode("utf-8")
    except Exception as e:
        logger.warning("[Voice] TTS generation failed: %s", e)

    return {
        "session_id":  sess.id,
        "transcript":  user_text,
        "response":    reply,
        "sources":     sources,
        "audio_base64": tts_audio_b64,
    }
