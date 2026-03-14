"""
agents/hr_chat_agent.py
────────────────────────
Agent 1 — HR Chat Agent

Architecture: LangGraph ReAct loop (create_react_agent)
Purpose:      Answer any HR policy question using RAG + employee data.

The LLM freely decides which tools to call in any order.
No hardcoded logic — LLM reasons over retrieved documents.

Tools available:
  search_hr_policy       — ChromaDB semantic search
  search_company_culture — handbook search
  get_all_leave_balances — real-time employee balance
  get_attendance_stats   — real-time attendance data
"""

from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from tools.rag_tools import search_hr_policy, search_company_culture
from tools.database_tools import get_all_leave_balances, get_attendance_stats
from config.settings import settings


# ── System Prompt ─────────────────────────────────────────────────────────────

HR_CHAT_SYSTEM = """
You are a friendly, knowledgeable HR assistant for a company in Sri Lanka.
Answer employee questions about HR policies, leave, attendance,
conduct rules, and any other workplace matters.

How to respond:
  - Use your tools to look up accurate policy information
  - Always cite which policy document you're referencing
  - Give clear, specific answers with actual numbers (days, rates, percentages)
  - If you retrieve the employee's personal data, personalise your response
  - If you cannot find an answer, say so and suggest contacting HR directly
  - Be professional but friendly and approachable

You can answer questions like:
  "How many annual leave days do I have left?"
  "What is the overtime rate on Sundays?"
  "Can I carry over unused leave?"
  "What happens if I'm late 5 times in a month?"
  "What is the dress code policy?"
"""


# ── Build Agent ───────────────────────────────────────────────────────────────

def build_hr_chat_agent():
    """Builds the ReAct chat agent. Called once, reused."""
    llm   = ChatOpenAI(model=settings.LLM_MODEL, temperature=0.3,
                       api_key=settings.OPENAI_API_KEY)
    tools = [
        search_hr_policy,
        search_company_culture,
        get_all_leave_balances,
        get_attendance_stats,
    ]
    return create_react_agent(llm, tools, prompt=HR_CHAT_SYSTEM)


_agent = None

def get_hr_chat_agent():
    global _agent
    if _agent is None:
        _agent = build_hr_chat_agent()
    return _agent


# ── Master Graph Node Wrapper ─────────────────────────────────────────────────

def hr_chat_node(state: HRSystemState) -> Dict[str, Any]:
    """
    Node function for the master graph.
    Wraps the ReAct agent to fit the HRSystemState interface.
    """
    user_input = state.get("user_input", "")
    emp_id     = state.get("employee_id", "")

    # Inject employee context into the message
    context = f"[Employee ID: {emp_id}]\n{user_input}" if emp_id else user_input

    try:
        agent  = get_hr_chat_agent()
        result = agent.invoke({"messages": [HumanMessage(content=context)]})
        answer = result["messages"][-1].content
    except Exception as e:
        answer = (
            "I couldn't retrieve the policy information right now. "
            "Please contact HR directly or try again later. "
            f"(Error: {e})"
        )

    return {
        "agent_response": answer,
        "is_complete":    True,
        "audit_trail": [{
            "timestamp": datetime.utcnow().isoformat(),
            "agent":     "hr_chat_agent",
            "action":    "answered_query",
            "input":     user_input[:100],
        }],
    }


# ── Sub-Graph ─────────────────────────────────────────────────────────────────

def build_hr_chat_subgraph():
    g = StateGraph(HRSystemState)
    g.add_node("chat", hr_chat_node)
    g.set_entry_point("chat")
    g.add_edge("chat", END)
    return g.compile()
