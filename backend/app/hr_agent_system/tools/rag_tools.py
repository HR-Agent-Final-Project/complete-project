"""
tools/rag_tools.py
──────────────────
ChromaDB RAG retrieval tools used by HR Chat and Leave agents.
Pure retrieval — no decision logic. LLM reasons over returned text.
"""

import json
from langchain.tools import tool
from rag.knowledge_base import get_retriever


@tool
def search_hr_policy(query: str) -> str:
    """
    Semantic search across HR policy documents (leave, attendance rules, conduct).
    Use for questions about entitlements, rules, thresholds, and procedures.
    Returns the top 3 most relevant policy excerpts.
    """
    retriever = get_retriever("hr_policies", k=3)
    if not retriever:
        return json.dumps({"found": False, "message": "Policy knowledge base unavailable."})
    docs = retriever.invoke(query)
    if not docs:
        return json.dumps({"found": False, "message": f"No policy found for: {query}"})
    return json.dumps({
        "found":   True,
        "results": [
            {
                "rank":    i + 1,
                "content": doc.page_content,
                "source":  doc.metadata.get("file", "hr_policy"),
            }
            for i, doc in enumerate(docs)
        ],
    })


@tool
def search_company_culture(query: str) -> str:
    """
    Search company handbook for conduct rules, disciplinary process, values, probation.
    Use when employees ask about company rules or expected behaviour.
    """
    retriever = get_retriever("company_culture", k=3)
    if not retriever:
        return json.dumps({"found": False, "message": "Handbook unavailable."})
    docs = retriever.invoke(query)
    if not docs:
        return json.dumps({"found": False, "message": f"No handbook entry for: {query}"})
    return json.dumps({
        "found":   True,
        "results": [
            {"rank": i + 1, "content": doc.page_content}
            for i, doc in enumerate(docs)
        ],
    })


@tool
def search_job_description(role_query: str) -> str:
    """
    Search job descriptions for a specific role.
    Use in recruitment agent when screening CVs or generating interview questions.
    """
    retriever = get_retriever("job_descriptions", k=2)
    if not retriever:
        return json.dumps({"found": False, "message": "Job descriptions unavailable."})
    docs = retriever.invoke(role_query)
    if not docs:
        return json.dumps({"found": False, "message": f"No job description for: {role_query}"})
    return json.dumps({
        "found":   True,
        "results": [{"rank": i + 1, "content": doc.page_content} for i, doc in enumerate(docs)],
    })


@tool
def get_leave_type_policy(leave_type_code: str) -> str:
    """
    Get specific policy rules for a leave type code: AL, SL, CL, ML, PL, NPL.
    Returns entitlement days, notice requirements, eligibility conditions.
    """
    retriever = get_retriever("hr_policies", k=3)
    if not retriever:
        return json.dumps({"found": False})
    query = f"{leave_type_code} leave policy entitlement rules conditions"
    docs  = retriever.invoke(query)
    if not docs:
        return json.dumps({"found": False, "message": f"No policy for {leave_type_code}"})
    return json.dumps({
        "found":       True,
        "leave_code":  leave_type_code,
        "policy_text": "\n\n".join(d.page_content for d in docs),
    })
