"""
Leave Management API

Endpoints:
  POST /api/leave/apply                ← Employee applies for leave (AI reviews automatically)
  GET  /api/leave/my-leaves            ← Employee's own leave history
  GET  /api/leave/my-balance           ← Employee's leave balance
  GET  /api/leave/all                  ← All leave requests (HR+)
  GET  /api/leave/pending              ← Pending requests needing HR review (HR+)
  GET  /api/leave/calendar             ← Who is on leave on a given date
  POST /api/leave/{id}/approve         ← HR Manager manually approves
  POST /api/leave/{id}/reject          ← HR Manager manually rejects
  POST /api/leave/{id}/cancel          ← Employee cancels a pending request
  POST /api/leave/{id}/appeal          ← Employee appeals a rejected decision
  POST /api/leave/ai-review/{id}       ← Re-trigger AI review
  POST /api/leave/chat                 ← RAG chatbot — ask about leave policy
  GET  /api/leave/types                ← All leave types
  POST /api/leave/types                ← Create leave type (Admin)
  GET  /api/leave/balance/{emp_id}     ← Specific employee balance (HR+)

AI Agent Logic:
  - Checks leave balance
  - Checks attendance percentage (must be >= 85%)
  - Checks HR policy via RAG
  - Auto-approves straightforward requests
  - Escalates complex/borderline cases to HR Manager
  - Sends notification after every decision
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional
import json

from app.core.database import get_db
from app.core.security import get_current_employee, require_role
from app.schemas.leave import (
    LeaveApplyRequest, LeaveApproveRequest, LeaveRejectRequest,
    LeaveCancelRequest, LeaveAppealRequest, LeaveChatRequest,
    LeaveTypeCreateRequest,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def count_working_days(start: date, end: date) -> float:
    """Count working days between start and end (excluding Sundays)."""
    total   = 0.0
    current = start
    while current <= end:
        if current.weekday() != 6:   # Exclude Sundays
            total += 1.0
        current += timedelta(days=1)
    return total


def get_leave_balance_record(db: Session, employee_id: int, leave_type_id: int):
    from app.models.leave import LeaveBalance
    return db.query(LeaveBalance).filter(
        LeaveBalance.employee_id   == employee_id,
        LeaveBalance.leave_type_id == leave_type_id,
        LeaveBalance.year          == date.today().year,
    ).first()


def get_attendance_percent(db: Session, employee_id: int) -> float:
    """Attendance percentage over last 90 days."""
    from app.models.attendance import Attendance

    three_months_ago = date.today() - timedelta(days=90)
    records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date   >= three_months_ago,
    ).all()

    if not records:
        return 100.0
    present = sum(1 for r in records if r.clock_in and not r.is_absent)
    return round((present / len(records)) * 100, 1)


def send_notification(db: Session, employee_id: int, title: str, message: str,
                      ntype: str = "leave_update", action_url: str = None):
    """Create a notification for an employee via the central notification service."""
    try:
        from app.services.notification_service import notify as _notify
        _notify(db, employee_id, ntype=ntype, title=title, message=message,
                action_url=action_url, related_entity_type="leave_request")
    except Exception as e:
        print(f"Notification failed: {e}")


def notify_hr_managers(db: Session, leave_request, employee, leave_type: str, reasoning: str):
    """Notify all HR Managers about an escalated leave request."""
    try:
        from app.services.notification_service import notify_hr_managers as _notify_mgrs
        _notify_mgrs(
            db,
            ntype   = "leave_escalated",
            title   = f"Leave Review Required — {employee.full_name}",
            message = (
                f"{employee.full_name} has requested {leave_type} from "
                f"{leave_request.start_date} to {leave_request.end_date} "
                f"({leave_request.days_requested} days). "
                f"AI escalated: {reasoning[:120]}..."
            ),
            action_url          = f"/leave/requests/{leave_request.id}",
            related_entity_type = "leave_request",
            related_entity_id   = leave_request.id,
        )
    except Exception as e:
        print(f"HR manager notification failed: {e}")


def leave_to_dict(leave) -> dict:
    return {
        "id":               leave.id,
        "employee_id":      leave.employee_id,
        "leave_type":       leave.leave_type.name if leave.leave_type else None,
        "leave_type_code":  leave.leave_type.code if leave.leave_type else None,
        "start_date":       str(leave.start_date),
        "end_date":         str(leave.end_date),
        "days_requested":   leave.days_requested or leave.total_days,
        "reason":           leave.reason,
        "status":           leave.status,
        "is_half_day":      leave.is_half_day,
        "approved_by":      leave.approved_by,
        "approved_at":      str(leave.approved_at) if leave.approved_at else None,
        "rejection_reason": leave.rejection_reason,
        "ai_decision":      leave.ai_decision,
        "ai_reasoning":     leave.ai_decision_reason,
        "is_appealed":      leave.is_appealed,
        "appeal_status":    leave.appeal_status,
        "created_at":       str(leave.created_at),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. APPLY FOR LEAVE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/apply", summary="Apply for leave — triggers AI review automatically")
def apply_leave(
    body:         LeaveApplyRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Employee applies for leave. AI agent reviews it automatically.

    AI will:
      1. Check leave balance
      2. Check attendance record (last 90 days)
      3. Check HR policy via RAG
      4. Auto-approve OR escalate to HR Manager
      5. Send notification with the decision
    """
    from app.models.leave import LeaveRequest, LeaveType, LeaveStatus

    leave_type = db.query(LeaveType).filter(
        LeaveType.id        == body.leave_type_id,
        LeaveType.is_active == True,
    ).first()
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found.")

    start_date = date.fromisoformat(body.start_date)
    end_date   = date.fromisoformat(body.end_date)

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date.")
    if start_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot apply for past dates.")

    days = 0.5 if body.is_half_day else count_working_days(start_date, end_date)

    # Check for overlapping approved/pending leave
    overlap = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == current_user.id,
        LeaveRequest.status.in_(["pending", "approved", "escalated"]),
        LeaveRequest.start_date  <= end_date,
        LeaveRequest.end_date    >= start_date,
    ).first()
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have a {overlap.status} leave from "
                f"{overlap.start_date} to {overlap.end_date}."
            ),
        )

    leave_request = LeaveRequest(
        employee_id    = current_user.id,
        leave_type_id  = leave_type.id,
        start_date     = start_date,
        end_date       = end_date,
        total_days     = days,
        days_requested = days,
        reason         = body.reason,
        is_half_day    = body.is_half_day,
        status         = LeaveStatus.PENDING,
    )
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)

    # Run AI review immediately
    ai_result = _run_ai_review(db, leave_request, current_user, leave_type)

    return {
        "message":      "Leave request submitted and reviewed by AI.",
        "leave_id":     leave_request.id,
        "days":         days,
        "leave_type":   leave_type.name,
        "ai_decision":  ai_result["decision"],
        "ai_reasoning": ai_result["reasoning"],
        "status":       leave_request.status,
        "next_step":    ai_result.get("next_step"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. AI REVIEW ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _run_ai_review(db: Session, leave_request, employee, leave_type) -> dict:
    """
    AI Leave Agent — reviews a leave request and makes a decision.

    Decision tree:
      1. Check leave balance        → REJECT if insufficient
      2. Check attendance %         → ESCALATE if < 85%
      3. Check advance notice       → ESCALATE if AL with < 3 days notice
      4. Check duration             → ESCALATE if > 5 days
      5. Check leave type (ML/PL)   → always ESCALATE
      6. Check HR policy via RAG
      7. AUTO-APPROVE if all checks pass
    """
    from app.models.leave import LeaveStatus, LeaveBalance

    steps    = []
    escalate = False
    reject   = False
    reject_reason = ""

    # ── Check 1: Leave Balance ────────────────────────────────────────────────
    balance = get_leave_balance_record(db, employee.id, leave_type.id)
    days    = leave_request.days_requested

    if not balance:
        reject        = True
        reject_reason = f"No leave balance record found for {leave_type.name}."
        steps.append(f"No balance record for {leave_type.name}.")
    elif balance.remaining_days < days:
        reject        = True
        reject_reason = (
            f"Insufficient {leave_type.name} balance. "
            f"Requested {days} days, only {balance.remaining_days} available."
        )
        steps.append(
            f"Balance FAILED — needs {days}d, has {balance.remaining_days}d."
        )
    else:
        steps.append(
            f"Balance OK — {balance.remaining_days} days available, "
            f"requesting {days} days."
        )

    # ── Check 2: Attendance Percentage ────────────────────────────────────────
    if not reject:
        att_pct = get_attendance_percent(db, employee.id)
        if att_pct < 85.0:
            escalate = True
            steps.append(f"Attendance {att_pct}% is below 85% — escalating to HR.")
        else:
            steps.append(f"Attendance {att_pct}% is above threshold.")

    # ── Check 3: Advance Notice (Annual Leave) ────────────────────────────────
    if not reject and leave_type.code == "AL":
        days_notice = (leave_request.start_date - date.today()).days
        if days_notice < 3:
            escalate = True
            steps.append(f"Only {days_notice} days notice for AL (min 3 days) — escalating.")
        else:
            steps.append(f"{days_notice} days advance notice — OK.")

    # ── Check 4: Long Duration ────────────────────────────────────────────────
    if not reject and days > 5:
        escalate = True
        steps.append(f"Duration {days} days exceeds auto-approve limit of 5 days — escalating.")
    elif not reject:
        steps.append(f"Duration {days} days is within auto-approve limit.")

    # ── Check 5: Special Leave Types (always need HR) ─────────────────────────
    if not reject and leave_type.code in ("ML", "PL", "NPL"):
        escalate = True
        steps.append(f"{leave_type.name} always requires HR Manager approval.")

    # ── Check 6: Policy RAG ───────────────────────────────────────────────────
    policy_note = _check_policy_rag(leave_type.code, days)
    steps.append(f"Policy: {policy_note}")

    reasoning = " | ".join(steps)

    # ── Final Decision ────────────────────────────────────────────────────────
    if reject:
        leave_request.status           = LeaveStatus.REJECTED
        leave_request.ai_decision      = "rejected"
        leave_request.ai_decision_reason = reasoning
        leave_request.rejection_reason = reject_reason
        leave_request.approved_at      = datetime.utcnow()
        db.commit()
        send_notification(
            db, employee.id,
            title   = f"Leave Request Rejected — {leave_type.name}",
            message = (
                f"Your {leave_type.name} request from {leave_request.start_date} "
                f"to {leave_request.end_date} was rejected. Reason: {reject_reason}"
            ),
        )
        return {
            "decision":  "rejected",
            "reasoning": reasoning,
            "next_step": "Your leave was rejected. Check your balance and reapply.",
        }

    elif escalate:
        leave_request.status             = LeaveStatus.ESCALATED
        leave_request.ai_decision        = "escalated"
        leave_request.ai_decision_reason = reasoning
        db.commit()
        notify_hr_managers(db, leave_request, employee, leave_type.name, reasoning)
        send_notification(
            db, employee.id,
            title   = f"Leave Request Under Review — {leave_type.name}",
            message = (
                f"Your {leave_type.name} request from {leave_request.start_date} "
                f"to {leave_request.end_date} has been forwarded to HR Manager."
            ),
        )
        return {
            "decision":  "escalated",
            "reasoning": reasoning,
            "next_step": "Your request has been forwarded to HR Manager for manual review.",
        }

    else:
        # AUTO-APPROVE
        leave_request.status             = LeaveStatus.APPROVED
        leave_request.ai_decision        = "approved"
        leave_request.ai_decision_reason = reasoning
        leave_request.approved_by        = "AI Agent"
        leave_request.approved_at        = datetime.utcnow()
        db.commit()

        # Deduct from balance
        if balance:
            balance.used_days      += days
            balance.remaining_days -= days
            db.commit()

        send_notification(
            db, employee.id,
            title   = f"Leave Approved — {leave_type.name}",
            message = (
                f"Your {leave_type.name} from {leave_request.start_date} "
                f"to {leave_request.end_date} ({days} days) has been approved by AI."
            ),
        )
        return {
            "decision":  "approved",
            "reasoning": reasoning,
            "next_step": "Your leave has been approved. Enjoy your time off!",
        }


def _check_policy_rag(leave_type_code: str, days: float) -> str:
    """RAG policy check — falls back to built-in rules if RAG unavailable."""
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        from langchain.chains import RetrievalQA

        embeddings = OpenAIEmbeddings()
        vectordb   = Chroma(persist_directory="chroma_db", embedding_function=embeddings)
        retriever  = vectordb.as_retriever(search_kwargs={"k": 3})
        llm        = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        qa_chain   = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        result     = qa_chain.invoke({"query": f"Policy for {leave_type_code} leave for {days} days?"})
        return result.get("result", "Policy check completed.")

    except Exception:
        rules = {
            "AL":  f"Annual Leave: 14 days/year. {'Within limit.' if days <= 14 else 'Exceeds annual limit.'}",
            "SL":  f"Sick Leave: 7 days/year. {'Medical cert required for > 2 days.' if days > 2 else 'Within limit.'}",
            "CL":  f"Casual Leave: 7 days/year. Max 3 consecutive days.",
            "ML":  "Maternity Leave: 84 days (12 weeks). HR approval required.",
            "PL":  "Paternity Leave: 3 days. HR approval required.",
            "NPL": "No Pay Leave: Salary deducted. HR approval required.",
        }
        return rules.get(leave_type_code, "Standard leave policy applies.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. HR MANUAL APPROVE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{leave_id}/approve", summary="HR Manager manually approves leave")
def approve_leave(
    leave_id:     int,
    body:         LeaveApproveRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),
):
    from app.models.leave import LeaveRequest, LeaveStatus

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if leave.status == LeaveStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Already approved.")
    if leave.status == LeaveStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot approve a cancelled request.")

    leave.status       = LeaveStatus.APPROVED
    leave.approved_by  = current_user.full_name
    leave.approved_at  = datetime.utcnow()
    leave.hr_override  = True
    leave.hr_notes     = body.note
    leave.ai_decision  = leave.ai_decision or "manual"
    db.commit()

    # Deduct balance
    balance = get_leave_balance_record(db, leave.employee_id, leave.leave_type_id)
    if balance:
        days = leave.days_requested or leave.total_days
        balance.used_days      += days
        balance.remaining_days -= days
        db.commit()

    send_notification(
        db, leave.employee_id,
        title   = f"Leave Approved by {current_user.full_name}",
        message = (
            f"Your {leave.leave_type.name} from {leave.start_date} to "
            f"{leave.end_date} ({leave.days_requested or leave.total_days} days) "
            f"has been approved by {current_user.full_name}."
            + (f" Note: {body.note}" if body.note else "")
        ),
    )

    return {
        "message":     "Leave approved successfully.",
        "leave_id":    leave_id,
        "approved_by": current_user.full_name,
        "approved_at": str(leave.approved_at),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. HR MANUAL REJECT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{leave_id}/reject", summary="HR Manager manually rejects leave")
def reject_leave(
    leave_id:     int,
    body:         LeaveRejectRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),
):
    from app.models.leave import LeaveRequest, LeaveStatus

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if leave.status == LeaveStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Already rejected.")
    if leave.status == LeaveStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot reject a cancelled request.")

    leave.status           = LeaveStatus.REJECTED
    leave.rejection_reason = body.reason
    leave.approved_by      = current_user.full_name
    leave.approved_at      = datetime.utcnow()
    leave.hr_override      = True
    db.commit()

    send_notification(
        db, leave.employee_id,
        title   = f"Leave Rejected — {leave.leave_type.name}",
        message = (
            f"Your {leave.leave_type.name} from {leave.start_date} to "
            f"{leave.end_date} was rejected by {current_user.full_name}. "
            f"Reason: {body.reason}"
        ),
    )

    return {
        "message":  "Leave rejected.",
        "leave_id": leave_id,
        "reason":   body.reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. EMPLOYEE CANCEL LEAVE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{leave_id}/cancel", summary="Employee cancels a pending or escalated leave request")
def cancel_leave(
    leave_id:     int,
    body:         LeaveCancelRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Employee can cancel their own leave request IF it is still pending or escalated.
    Approved leave cannot be cancelled here — contact HR Manager.
    """
    from app.models.leave import LeaveRequest, LeaveStatus

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    # Only the requesting employee can cancel their own leave
    if leave.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own leave requests.")

    if leave.status not in (LeaveStatus.PENDING, LeaveStatus.ESCALATED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a leave that is already {leave.status}. Contact HR."
        )

    leave.status   = LeaveStatus.CANCELLED
    leave.hr_notes = f"Cancelled by employee. Reason: {body.reason or 'No reason given.'}"
    db.commit()

    return {
        "message":  "Leave request cancelled successfully.",
        "leave_id": leave_id,
        "status":   "cancelled",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. EMPLOYEE APPEAL REJECTED LEAVE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{leave_id}/appeal", summary="Employee appeals a rejected leave decision")
def appeal_leave(
    leave_id:     int,
    body:         LeaveAppealRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Employee can appeal a REJECTED leave decision once.
    The appeal is sent to HR Managers for manual review.
    """
    from app.models.leave import LeaveRequest, LeaveStatus

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if leave.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only appeal your own leave.")
    if leave.status != LeaveStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Only rejected leaves can be appealed.")
    if leave.is_appealed:
        raise HTTPException(status_code=400, detail="You have already submitted an appeal for this request.")

    leave.is_appealed    = True
    leave.appeal_reason  = body.appeal_reason
    leave.appeal_status  = "pending"
    db.commit()

    # Notify HR Managers about the appeal
    notify_hr_managers(
        db, leave, current_user,
        leave.leave_type.name if leave.leave_type else "Leave",
        f"APPEAL SUBMITTED: {body.appeal_reason}",
    )

    send_notification(
        db, current_user.id,
        title   = "Leave Appeal Submitted",
        message = (
            f"Your appeal for {leave.leave_type.name if leave.leave_type else 'Leave'} "
            f"({leave.start_date} – {leave.end_date}) has been submitted to HR for review."
        ),
    )

    return {
        "message":      "Appeal submitted successfully.",
        "leave_id":     leave_id,
        "appeal_status": "pending",
        "next_step":    "HR Manager will review your appeal and respond shortly.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. RE-TRIGGER AI REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ai-review/{leave_id}", summary="Re-trigger AI review on a pending leave — HR+")
def ai_review(
    leave_id:     int,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    from app.models.leave import LeaveRequest, LeaveStatus, LeaveType
    from app.models.employee import Employee

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    if leave.status not in (LeaveStatus.PENDING, LeaveStatus.ESCALATED):
        raise HTTPException(status_code=400, detail=f"Can only re-review pending/escalated requests. Current: {leave.status}")

    employee   = db.query(Employee).filter(Employee.id == leave.employee_id).first()
    leave_type = db.query(LeaveType).filter(LeaveType.id == leave.leave_type_id).first()

    if not employee or not leave_type:
        raise HTTPException(status_code=404, detail="Employee or leave type not found.")

    ai_result = _run_ai_review(db, leave, employee, leave_type)

    return {
        "message":      "AI review completed.",
        "leave_id":     leave_id,
        "ai_decision":  ai_result["decision"],
        "ai_reasoning": ai_result["reasoning"],
        "status":       leave.status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. RAG CHATBOT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/chat", summary="Ask AI about leave policy — RAG chatbot")
def leave_chat(
    body:         LeaveChatRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Employee asks any question about leave policy.
    AI answers using RAG (policy documents) + employee's actual balance.

    Examples:
      "How many annual leave days do I have left?"
      "Can I take leave during probation?"
      "What documents do I need for maternity leave?"
    """
    from app.models.leave import LeaveBalance

    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == current_user.id,
        LeaveBalance.year        == date.today().year,
    ).all()

    balance_context = "\n".join([
        f"- {b.leave_type.name if b.leave_type else 'Unknown'}: "
        f"{b.remaining_days} days remaining out of {b.total_days}"
        for b in balances
    ])

    try:
        from langchain_community.vectorstores import Chroma
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        from langchain.prompts import PromptTemplate
        from langchain.chains import RetrievalQA

        embeddings = OpenAIEmbeddings()
        vectordb   = Chroma(persist_directory="chroma_db", embedding_function=embeddings)
        retriever  = vectordb.as_retriever(search_kwargs={"k": 4})

        prompt_template = """
You are a friendly HR assistant for a company in Sri Lanka.
Answer employee questions about leave policy clearly and helpfully.

Employee: {employee_name}
Department: {department}

Current Leave Balances:
{balance_context}

HR Policy Context:
{context}

Question: {question}

Provide a helpful, accurate answer. Reference actual balance numbers when relevant.
"""
        prompt = PromptTemplate(
            template        = prompt_template,
            input_variables = ["context", "question", "employee_name", "department", "balance_context"],
        )
        llm      = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        qa_chain = RetrievalQA.from_chain_type(
            llm               = llm,
            retriever         = retriever,
            chain_type_kwargs = {
                "prompt": prompt.partial(
                    employee_name   = current_user.full_name,
                    department      = current_user.department.name if current_user.department else "N/A",
                    balance_context = balance_context,
                )
            },
        )
        result = qa_chain.invoke({"query": body.question})
        answer = result.get("result", "I could not find an answer.")

    except Exception:
        answer = _built_in_leave_answer(body.question, balance_context, current_user)

    return {
        "question": body.question,
        "answer":   answer,
        "employee": current_user.full_name,
        "balances": [
            {
                "leave_type":     b.leave_type.name if b.leave_type else "Unknown",
                "code":           b.leave_type.code if b.leave_type else "N/A",
                "total_days":     b.total_days,
                "used_days":      b.used_days,
                "remaining_days": b.remaining_days,
            }
            for b in balances
        ],
    }


def _built_in_leave_answer(question: str, balance_context: str, employee) -> str:
    q = question.lower()
    if any(w in q for w in ["balance", "how many", "remaining", "left"]):
        return f"Hi {employee.first_name}! Here are your current leave balances:\n\n{balance_context}"
    if "annual" in q:
        return "Annual Leave (AL): 14 days/year. Min 3 days advance notice. Up to 7 unused days carried over."
    if "sick" in q:
        return "Sick Leave (SL): 7 days/year. Medical certificate required for more than 2 consecutive days."
    if "casual" in q:
        return "Casual Leave (CL): 7 days/year. Max 3 consecutive days. Advance notice required."
    if "maternity" in q:
        return "Maternity Leave (ML): 84 working days (12 weeks). HR Manager approval required."
    if "paternity" in q:
        return "Paternity Leave (PL): 3 working days. Must be taken within 2 weeks of birth."
    if "no pay" in q or "npl" in q:
        return "No Pay Leave (NPL): Salary deducted for the period. HR Manager approval required."
    if "carry" in q:
        return "Up to 7 unused Annual Leave days can be carried over. SL and CL cannot be carried over."
    if "probation" in q:
        return "During probation, only Casual Leave and Sick Leave can be taken. Annual Leave accrues but cannot be used."
    if "half day" in q:
        return "Half Day Leave: deducts 0.5 days from your balance. Apply using is_half_day: true."
    if "appeal" in q:
        return "If your leave is rejected, you can appeal once using the appeal endpoint. HR will review manually."
    return (
        f"Hi {employee.first_name}! I can help with:\n"
        "• Leave balances • Annual/Sick/Casual/Maternity/Paternity leave\n"
        "• Carry-over rules • Probation rules • Half-day leave • Appeals\n"
        "Please ask a specific question!"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. MY LEAVES
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-leaves", summary="My leave history")
def my_leaves(
    year:         Optional[int] = Query(None),
    status:       Optional[str] = Query(None),
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_employee),
):
    from app.models.leave import LeaveRequest

    q = db.query(LeaveRequest).filter(LeaveRequest.employee_id == current_user.id)
    if year:
        q = q.filter(LeaveRequest.start_date >= date(year, 1, 1),
                     LeaveRequest.start_date <= date(year, 12, 31))
    if status:
        q = q.filter(LeaveRequest.status == status)

    leaves = q.order_by(LeaveRequest.created_at.desc()).all()
    return {
        "employee": current_user.full_name,
        "total":    len(leaves),
        "leaves":   [leave_to_dict(l) for l in leaves],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. MY BALANCE
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-balance", summary="My leave balance")
def my_balance(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    from app.models.leave import LeaveBalance

    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == current_user.id,
        LeaveBalance.year        == date.today().year,
    ).all()

    return {
        "employee": current_user.full_name,
        "year":     date.today().year,
        "balances": [
            {
                "leave_type":     b.leave_type.name if b.leave_type else "Unknown",
                "code":           b.leave_type.code if b.leave_type else "N/A",
                "total_days":     b.total_days,
                "used_days":      b.used_days,
                "pending_days":   b.pending_days,
                "remaining_days": b.remaining_days,
                "carried_over":   b.carried_over,
            }
            for b in balances
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 11. ALL LEAVES (HR+)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/all", summary="All leave requests — HR Staff+")
def all_leaves(
    status:        Optional[str] = Query(None),
    employee_id:   Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    month:         Optional[int] = Query(None, ge=1, le=12),
    year:          Optional[int] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=100),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(require_role(2)),
):
    from app.models.leave import LeaveRequest
    from app.models.employee import Employee

    q = db.query(LeaveRequest)
    if status:        q = q.filter(LeaveRequest.status == status)
    if employee_id:   q = q.filter(LeaveRequest.employee_id == employee_id)
    if leave_type_id: q = q.filter(LeaveRequest.leave_type_id == leave_type_id)
    if year:
        q = q.filter(
            LeaveRequest.start_date >= date(year, 1, 1),
            LeaveRequest.start_date <= date(year, 12, 31),
        )
    if month and year:
        q = q.filter(
            LeaveRequest.start_date >= date(year, month, 1),
        )
    if department_id:
        q = q.join(Employee, LeaveRequest.employee_id == Employee.id).filter(
            Employee.department_id == department_id
        )

    total  = q.count()
    leaves = q.order_by(LeaveRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":    total,
        "page":     page,
        "page_size": page_size,
        "pending":  db.query(LeaveRequest).filter(LeaveRequest.status == "pending").count(),
        "escalated": db.query(LeaveRequest).filter(LeaveRequest.status == "escalated").count(),
        "leaves":   [leave_to_dict(l) for l in leaves],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 12. PENDING QUEUE (HR shortcut)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/pending", summary="Pending and escalated leaves needing HR action — HR Staff+")
def pending_leaves(
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    """Returns all pending and escalated leave requests for HR review dashboard."""
    from app.models.leave import LeaveRequest, LeaveStatus
    from app.models.employee import Employee

    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.ESCALATED])
    ).order_by(LeaveRequest.created_at.asc()).all()

    result = []
    for l in leaves:
        emp = db.query(Employee).filter(Employee.id == l.employee_id).first()
        row = leave_to_dict(l)
        row["employee_name"]   = emp.full_name if emp else "Unknown"
        row["employee_number"] = emp.employee_number if emp else None
        row["department"]      = emp.department.name if emp and emp.department else None
        row["waiting_days"]    = (date.today() - l.created_at.date()).days
        result.append(row)

    return {
        "total":        len(result),
        "pending":      sum(1 for r in result if r["status"] == "pending"),
        "escalated":    sum(1 for r in result if r["status"] == "escalated"),
        "requests":     result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 13. LEAVE CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/calendar", summary="See who is on approved leave on a given date — HR Staff+")
def leave_calendar(
    check_date:    Optional[str] = Query(None, description="YYYY-MM-DD — defaults to today"),
    department_id: Optional[int] = Query(None),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(require_role(2)),
):
    """
    Returns all employees who are on approved leave on the given date.
    Useful for HR to plan resources and spot team coverage gaps.
    """
    from app.models.leave import LeaveRequest, LeaveStatus
    from app.models.employee import Employee

    target = date.fromisoformat(check_date) if check_date else date.today()

    q = db.query(LeaveRequest).filter(
        LeaveRequest.status    == LeaveStatus.APPROVED,
        LeaveRequest.start_date <= target,
        LeaveRequest.end_date   >= target,
    )

    if department_id:
        q = q.join(Employee, LeaveRequest.employee_id == Employee.id).filter(
            Employee.department_id == department_id
        )

    on_leave = q.all()

    result = []
    for l in on_leave:
        emp = db.query(Employee).filter(Employee.id == l.employee_id).first()
        result.append({
            "employee_id":     l.employee_id,
            "employee_name":   emp.full_name if emp else "Unknown",
            "employee_number": emp.employee_number if emp else None,
            "department":      emp.department.name if emp and emp.department else None,
            "leave_type":      l.leave_type.name if l.leave_type else "Unknown",
            "start_date":      str(l.start_date),
            "end_date":        str(l.end_date),
            "days_requested":  l.days_requested or l.total_days,
        })

    return {
        "date":        str(target),
        "day":         target.strftime("%A"),
        "total_on_leave": len(result),
        "on_leave":    result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 14. LEAVE TYPES
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/types", summary="All leave types")
def get_leave_types(db: Session = Depends(get_db)):
    from app.models.leave import LeaveType

    types = db.query(LeaveType).filter(LeaveType.is_active == True).all()
    return {
        "types": [
            {
                "id":               t.id,
                "name":             t.name,
                "code":             t.code,
                "max_days":         t.max_days_per_year,
                "is_paid":          t.is_paid,
                "requires_document": t.requires_document,
                "description":      t.description,
            }
            for t in types
        ]
    }


@router.post("/types", status_code=status.HTTP_201_CREATED,
             summary="Create a new leave type — Admin only")
def create_leave_type(
    body:         LeaveTypeCreateRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(4)),
):
    from app.models.leave import LeaveType

    existing = db.query(LeaveType).filter(
        (LeaveType.name == body.name) | (LeaveType.code == body.code)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A leave type with that name or code already exists.")

    lt = LeaveType(
        name                 = body.name,
        code                 = body.code,
        max_days_per_year    = body.max_days_per_year,
        description          = body.description,
        max_consecutive_days = body.max_consecutive_days,
        requires_document    = body.requires_document,
        is_paid              = body.is_paid,
        gender_specific      = body.gender_specific,
        is_active            = True,
    )
    db.add(lt)
    db.commit()
    db.refresh(lt)

    return {
        "message": f"Leave type '{lt.name}' created successfully.",
        "id":      lt.id,
        "code":    lt.code,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 15. BALANCE FOR SPECIFIC EMPLOYEE (HR+)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/balance/{employee_id}", summary="Get leave balance for specific employee — HR Staff+")
def employee_balance(
    employee_id:  int,
    year:         Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    current_user                = Depends(require_role(2)),
):
    from app.models.leave import LeaveBalance
    from app.models.employee import Employee

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    use_year = year or date.today().year
    balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.year        == use_year,
    ).all()

    return {
        "employee": emp.full_name,
        "year":     use_year,
        "balances": [
            {
                "leave_type":     b.leave_type.name if b.leave_type else "Unknown",
                "code":           b.leave_type.code if b.leave_type else "N/A",
                "total_days":     b.total_days,
                "used_days":      b.used_days,
                "pending_days":   b.pending_days,
                "remaining_days": b.remaining_days,
                "carried_over":   b.carried_over,
            }
            for b in balances
        ],
    }
