"""
core/graph.py
─────────────
Master LangGraph — wires all 7 agent sub-graphs + supervisor into one graph.

Structure:
  supervisor  ← entry point, classifies intent
      │
      └─ conditional edges (route_to_agent) ─→ 7 agent nodes ─→ END

Each agent node IS a compiled sub-graph.
When the master calls "leave_agent", the entire leave sub-graph runs.
This makes each agent independently testable AND composable.

Memory: MemorySaver enables conversation continuity across turns.
Interrupt: graph pauses before human_review_checkpoint (leave escalation).
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import HRSystemState
from core.supervisor import supervisor_node, route_to_agent

# Import each agent's build function
from agents.hr_chat_agent     import build_hr_chat_subgraph
from agents.leave_agent       import build_leave_subgraph
from agents.attendance_agent  import build_attendance_subgraph
from agents.performance_agent import build_performance_subgraph
from agents.recruitment_agent import build_recruitment_subgraph
from agents.detection_agent   import build_detection_subgraph
from agents.reporting_agent   import build_reporting_subgraph


def build_hr_graph():
    """
    Compile the complete HR management system into one StateGraph.
    Called once at startup in main.py.
    """
    # ── Build each agent sub-graph ────────────────────────────────────────────
    hr_chat_sg     = build_hr_chat_subgraph()
    leave_sg       = build_leave_subgraph()
    attendance_sg  = build_attendance_subgraph()
    performance_sg = build_performance_subgraph()
    recruitment_sg = build_recruitment_subgraph()
    detection_sg   = build_detection_subgraph()
    reporting_sg   = build_reporting_subgraph()

    # ── Master graph ──────────────────────────────────────────────────────────
    graph = StateGraph(HRSystemState)

    # Entry point — supervisor classifies all requests
    graph.add_node("supervisor", supervisor_node)

    # 7 specialized agent nodes (each is a compiled sub-graph)
    graph.add_node("hr_chat_agent",     hr_chat_sg)
    graph.add_node("leave_agent",       leave_sg)
    graph.add_node("attendance_agent",  attendance_sg)
    graph.add_node("performance_agent", performance_sg)
    graph.add_node("recruitment_agent", recruitment_sg)
    graph.add_node("detection_agent",   detection_sg)
    graph.add_node("reporting_agent",   reporting_sg)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor routes to agents via conditional edges
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "hr_chat_agent":     "hr_chat_agent",
            "leave_agent":       "leave_agent",
            "attendance_agent":  "attendance_agent",
            "performance_agent": "performance_agent",
            "recruitment_agent": "recruitment_agent",
            "detection_agent":   "detection_agent",
            "reporting_agent":   "reporting_agent",
        },
    )

    # All agents return to END after completing their workflow
    for agent_name in [
        "hr_chat_agent", "leave_agent",
        "attendance_agent", "performance_agent", "recruitment_agent",
        "detection_agent", "reporting_agent",
    ]:
        graph.add_edge(agent_name, END)

    # Compile with MemorySaver for conversation continuity across turns.
    # Note: interrupt_before=["human_review_checkpoint"] is set on the
    # leave sub-graph itself (leave_agent.py), not the master graph,
    # because the node lives inside the sub-graph.
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ── Singleton graph instance ──────────────────────────────────────────────────
_hr_graph = None

def get_hr_graph():
    """Returns the compiled master graph. Builds once, reuses."""
    global _hr_graph
    if _hr_graph is None:
        print("[Graph] Building master HR graph...")
        _hr_graph = build_hr_graph()
        print("[Graph] ✅ Master graph ready.")
    return _hr_graph
