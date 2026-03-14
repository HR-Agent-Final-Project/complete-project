"""
agents/reporting_agent.py
──────────────────────────
Agent 8 — Reporting & Analytics Agent

Sequential 7-node workflow generating executive HR reports.
"""

import json
from typing import Dict, Any
from datetime import datetime, date

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from models.schemas import ReportOutput
from models.database import SessionLocal, HRReport
from tools.analytics_tools import (
    get_monthly_summary, get_department_breakdown,
    get_leave_utilisation, get_top_performers,
)
from config.settings import settings


def _llm():
    return ChatOpenAI(model=settings.LLM_MODEL, temperature=0.3, api_key=settings.OPENAI_API_KEY)


def node_determine_type(state: HRSystemState) -> Dict[str, Any]:
    task   = state.get("task_data") or {}
    rtype  = task.get("report_type", "monthly_summary")
    period = task.get("period") or datetime.now().strftime("%Y-%m")
    print(f"  [Rep 1/7] Report type: '{rtype}' period: '{period}'")
    return {
        "task_data":   {**task, "report_type": rtype, "period": period},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "determine_type"}],
    }


def node_fetch_data(state: HRSystemState) -> Dict[str, Any]:
    task   = state.get("task_data") or {}
    period = task.get("period", datetime.now().strftime("%Y-%m"))
    summary = json.loads(get_monthly_summary.invoke({"period": period}))
    depts   = json.loads(get_department_breakdown.invoke({"period": period}))
    year    = int(period[:4])
    leave   = json.loads(get_leave_utilisation.invoke({"year": year}))
    top5    = json.loads(get_top_performers.invoke({"period": period, "limit": 5}))
    print(f"  [Rep 2/7] Data fetched: {summary.get('total_employees', 0)} employees")
    return {
        "task_data": {**task, "summary": summary, "depts": depts,
                      "leave_util": leave, "top_performers": top5},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "fetch_data"}],
    }


def node_calculate_kpis(state: HRSystemState) -> Dict[str, Any]:
    task    = state.get("task_data") or {}
    summary = task.get("summary", {})
    kpis    = {
        "attendance_rate":      summary.get("attendance_rate", 0),
        "total_employees":      summary.get("total_employees", 0),
        "total_overtime_hours": summary.get("overtime_hours", 0),
        "total_leave_requests": summary.get("total_leave_apps", 0),
        "absenteeism_rate":     round(100 - summary.get("attendance_rate", 100), 1),
    }
    print(f"  [Rep 3/7] KPIs: att={kpis['attendance_rate']}%, absenteeism={kpis['absenteeism_rate']}%")
    return {
        "task_data":   {**task, "kpis": kpis},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "calculate_kpis"}],
    }


def node_detect_trends(state: HRSystemState) -> Dict[str, Any]:
    task    = state.get("task_data") or {}
    kpis    = task.get("kpis", {})
    summary = task.get("summary", {})
    trends  = []
    if kpis.get("attendance_rate", 100) < 85:
        trends.append(f"⚠️ Attendance below threshold: {kpis['attendance_rate']}%")
    if kpis.get("total_overtime_hours", 0) > 200:
        trends.append(f"📈 High OT hours: {kpis['total_overtime_hours']:.0f}h — consider hiring review")
    if kpis.get("absenteeism_rate", 0) > 15:
        trends.append(f"⚠️ High absenteeism: {kpis['absenteeism_rate']}%")
    if not trends:
        trends.append("✅ All key metrics within normal ranges.")
    print(f"  [Rep 4/7] Trends detected: {len(trends)}")
    return {
        "task_data":   {**task, "trends": trends},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "detect_trends"}],
    }


def node_generate_narrative(state: HRSystemState) -> Dict[str, Any]:
    task   = state.get("task_data") or {}
    period = task.get("period", "")
    kpis   = task.get("kpis", {})
    trends = task.get("trends", [])
    try:
        narrative = _llm().invoke([
            SystemMessage(content="Write a concise 4-sentence executive HR report narrative."),
            HumanMessage(content=(
                f"Period: {period}\n"
                f"KPIs: {json.dumps(kpis)}\n"
                f"Key Trends: {trends}\n"
                "Summarise performance, highlight concerns, and recommend actions."
            )),
        ]).content
    except Exception as e:
        narrative = f"HR Report for {period}. Attendance: {kpis.get('attendance_rate')}%. See detailed data for full breakdown."
    print(f"  [Rep 5/7] Narrative generated ({len(narrative)} chars)")
    return {
        "task_data":   {**task, "narrative": narrative},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "generate_narrative"}],
    }


def node_format_report(state: HRSystemState) -> Dict[str, Any]:
    task    = state.get("task_data") or {}
    period  = task.get("period", "")
    rtype   = task.get("report_type", "monthly_summary")
    output  = ReportOutput(
        report_type = rtype,
        period      = period,
        title       = f"HR {rtype.replace('_', ' ').title()} Report — {period}",
        kpis        = task.get("kpis", {}),
        trends      = task.get("trends", []),
        narrative   = task.get("narrative", ""),
        data        = {
            "summary":        task.get("summary", {}),
            "departments":    task.get("depts", {}),
            "leave_util":     task.get("leave_util", {}),
            "top_performers": task.get("top_performers", {}),
        },
    )
    print(f"  [Rep 6/7] Report formatted: '{output.title}'")
    return {
        "structured_output": output.model_dump(),
        "agent_response":    f"Report '{output.title}' generated. {output.narrative[:200]}",
        "decision":          "GENERATED",
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "format_report"}],
    }


def node_archive_report(state: HRSystemState) -> Dict[str, Any]:
    out = state.get("structured_output") or {}
    db  = SessionLocal()
    try:
        db.add(HRReport(
            report_type = out.get("report_type", ""),
            period      = out.get("period", ""),
            title       = out.get("title", ""),
            content     = out.get("data", {}),
            narrative   = out.get("narrative", ""),
        ))
        db.commit()
        print(f"  [Rep 7/7] Archived to DB")
    except Exception as e:
        db.rollback()
        print(f"  [Rep 7/7] DB error: {e}")
    finally:
        db.close()
    return {
        "is_complete": True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "archive_report"}],
    }


def build_reporting_subgraph():
    g = StateGraph(HRSystemState)
    nodes = [
        ("determine_type",    node_determine_type),
        ("fetch_data",        node_fetch_data),
        ("calculate_kpis",    node_calculate_kpis),
        ("detect_trends",     node_detect_trends),
        ("generate_narrative",node_generate_narrative),
        ("format_report",     node_format_report),
        ("archive_report",    node_archive_report),
    ]
    for name, fn in nodes:
        g.add_node(name, fn)
    g.set_entry_point(nodes[0][0])
    for i in range(len(nodes) - 1):
        g.add_edge(nodes[i][0], nodes[i + 1][0])
    g.add_edge(nodes[-1][0], END)
    return g.compile()
