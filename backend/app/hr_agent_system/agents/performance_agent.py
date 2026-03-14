"""
agents/performance_agent.py  —  Agent 5: Performance Tracking
agents/recruitment_agent.py  —  Agent 6: Recruitment / Interview
agents/detection_agent.py    —  Agent 7: Illegal Worker Detection
agents/reporting_agent.py    —  Agent 8: Analytics & Reporting

All 4 follow the same sequential sub-graph pattern.
"""
# This file is performance_agent.py

import json
from typing import Dict, Any
from datetime import datetime, date

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from models.schemas import PerformanceOutput
from models.database import SessionLocal, PerformanceReview
from tools.database_tools import get_employee_profile, get_attendance_stats
from tools.analytics_tools import get_monthly_summary
from config.settings import settings


def _llm():
    return ChatOpenAI(model=settings.LLM_MODEL, temperature=0.4,
                      api_key=settings.OPENAI_API_KEY)


NARRATIVE_PROMPT = """
Write a professional 3-sentence performance evaluation narrative for an employee.
Reference the specific data provided. Be constructive, fair, and specific.
Do NOT mention raw scores or percentages — describe the performance in qualitative terms.
"""


def node_collect_metrics(state: HRSystemState) -> Dict[str, Any]:
    emp_id = state.get("employee_id", "")
    stats  = json.loads(get_attendance_stats.invoke({"employee_id": emp_id, "days": 90}))
    emp    = json.loads(get_employee_profile.invoke({"employee_id": emp_id}))
    print(f"  [Perf 1/6] Metrics: att={stats.get('attendance_percent', 0)}%")
    task = state.get("task_data") or {}
    return {
        "employee_data": emp,
        "task_data":     {**task, "att_stats": stats},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "collect_metrics"}],
    }


def node_calculate_scores(state: HRSystemState) -> Dict[str, Any]:
    task      = state.get("task_data") or {}
    stats     = task.get("att_stats", {})
    att_pct   = stats.get("attendance_percent", 100.0)
    late_days = stats.get("late_days", 0)
    ot_hours  = stats.get("overtime_hours", 0.0)

    att_score  = min(100.0, att_pct)
    punc_score = max(0.0, 100.0 - late_days * 5)
    ot_score   = min(100.0, ot_hours * 3)
    overall    = round(att_score * 0.4 + punc_score * 0.4 + ot_score * 0.2, 1)
    rating     = ("Excellent"         if overall >= 85 else
                  "Good"              if overall >= 70 else
                  "Average"           if overall >= 55 else "Needs Improvement")
    flags      = []
    if att_pct < 85:  flags.append(f"Low attendance: {att_pct}%")
    if late_days > 3: flags.append(f"Frequent late arrivals: {late_days}")

    print(f"  [Perf 2/6] Scores: att={att_score:.1f} punc={punc_score:.1f} overall={overall} → {rating}")
    return {
        "task_data": {**task, "att_score": att_score, "punc_score": punc_score,
                      "ot_score": ot_score, "overall": overall, "rating": rating, "flags": flags},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "calculate_scores",
                          "overall": overall, "rating": rating}],
    }


def node_generate_evaluation(state: HRSystemState) -> Dict[str, Any]:
    task = state.get("task_data") or {}
    emp  = state.get("employee_data") or {}
    try:
        narrative = _llm().invoke([
            SystemMessage(content=NARRATIVE_PROMPT),
            HumanMessage(content=(
                f"Employee: {emp.get('name', 'Employee')}, Dept: {emp.get('department', '')}\n"
                f"Attendance: {task.get('att_stats', {}).get('attendance_percent', 0)}%\n"
                f"Late days: {task.get('att_stats', {}).get('late_days', 0)}\n"
                f"OT hours: {task.get('att_stats', {}).get('overtime_hours', 0)}\n"
                f"Rating: {task.get('rating', 'N/A')}"
            )),
        ]).content
    except Exception as e:
        narrative = f"Performance evaluation for {task.get('rating', 'N/A')} quarter."
    print(f"  [Perf 3/6] Narrative generated ({len(narrative)} chars)")
    return {
        "task_data":   {**task, "narrative": narrative},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "generate_eval"}],
    }


def node_compare_benchmarks(state: HRSystemState) -> Dict[str, Any]:
    # Production: compare vs department averages from DB
    task = state.get("task_data") or {}
    print(f"  [Perf 4/6] Benchmarks: company avg = 78.5")
    return {
        "task_data": {**task, "company_avg": 78.5,
                      "vs_benchmark": task.get("overall", 0) - 78.5},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "compare_benchmarks"}],
    }


def node_flag_concerns(state: HRSystemState) -> Dict[str, Any]:
    task  = state.get("task_data") or {}
    flags = task.get("flags", [])
    if flags:
        print(f"  [Perf 5/6] Flags: {flags}")
    return {"audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "flag_concerns"}]}


def node_update_performance(state: HRSystemState) -> Dict[str, Any]:
    task  = state.get("task_data") or {}
    period = task.get("period", f"{date.today().year}-Q{(date.today().month - 1)//3 + 1}")
    output = PerformanceOutput(
        employee_id       = state.get("employee_id", ""),
        period            = period,
        attendance_score  = task.get("att_score", 0),
        punctuality_score = task.get("punc_score", 0),
        overtime_score    = task.get("ot_score", 0),
        overall_score     = task.get("overall", 0),
        rating            = task.get("rating", "N/A"),
        narrative         = task.get("narrative", ""),
        flags             = task.get("flags", []),
    )
    db = SessionLocal()
    try:
        # Derive period dates from quarterly period string (e.g. "2026-Q1")
        year = date.today().year
        q    = (date.today().month - 1) // 3 + 1
        p_start = date(year, (q - 1) * 3 + 1, 1)
        p_end   = date(year, min(q * 3, 12), 28)
        db.add(PerformanceReview(
            employee_id       = output.employee_id,
            period_type       = "quarterly",
            period_start      = p_start,
            period_end        = p_end,
            attendance_score  = output.attendance_score,
            punctuality_score = output.punctuality_score,
            overtime_score    = output.overtime_score,
            overall_score     = output.overall_score,
            rating            = output.rating,
            ai_summary        = output.narrative,
            status            = "completed",
            is_promotion_eligible = output.overall_score >= 85,
            requires_pip          = output.overall_score < 55,
        ))
        db.commit()
        print(f"  [Perf 6/6] Saved: {output.rating} ({output.overall_score})")
    except Exception as e:
        db.rollback()
        print(f"  [Perf 6/6] DB error: {e}")
    finally:
        db.close()
    return {
        "structured_output": output.model_dump(),
        "agent_response":    f"Performance: {output.rating} ({output.overall_score}/100). {output.narrative}",
        "decision":          "EVALUATED",
        "is_complete":       True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "update_performance"}],
    }


def build_performance_subgraph():
    g = StateGraph(HRSystemState)
    for name, fn in [
        ("collect_metrics",     node_collect_metrics),
        ("calculate_scores",    node_calculate_scores),
        ("generate_evaluation", node_generate_evaluation),
        ("compare_benchmarks",  node_compare_benchmarks),
        ("flag_concerns",       node_flag_concerns),
        ("update_performance",  node_update_performance),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("collect_metrics")
    nodes = ["collect_metrics","calculate_scores","generate_evaluation",
             "compare_benchmarks","flag_concerns","update_performance"]
    for i in range(len(nodes) - 1):
        g.add_edge(nodes[i], nodes[i + 1])
    g.add_edge("update_performance", END)
    return g.compile()
