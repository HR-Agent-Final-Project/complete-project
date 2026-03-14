"""
agents/recruitment_agent.py
────────────────────────────
Agent 6 — Recruitment & Interview Agent

Sequential 7-node workflow:
  load_job_requirements → screen_resume → generate_questions
  → conduct_interview → evaluate_responses → rank_candidate → notify_hr
"""

import json
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from models.schemas import CandidateEvaluation
from tools.rag_tools import search_job_description
from tools.email_tools import send_hr_manager_alert
from config.settings import settings


def _llm(temp=0.3):
    return ChatOpenAI(model=settings.LLM_MODEL, temperature=temp, api_key=settings.OPENAI_API_KEY)


def node_load_requirements(state: HRSystemState) -> Dict[str, Any]:
    task = state.get("task_data") or {}
    pos  = task.get("position", "Software Engineer")
    result = json.loads(search_job_description.invoke({"role_query": pos}))
    jd_text = "\n".join(r["content"] for r in result.get("results", [])) if result.get("found") else ""
    print(f"  [Rec 1/7] JD loaded for '{pos}'")
    return {
        "task_data":   {**task, "jd_text": jd_text},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "load_requirements"}],
    }


def node_screen_resume(state: HRSystemState) -> Dict[str, Any]:
    task       = state.get("task_data") or {}
    resume     = task.get("resume_text", "")
    jd_text    = task.get("jd_text", "")
    position   = task.get("position", "role")
    try:
        response = _llm(0.0).invoke([
            SystemMessage(content="You are an expert HR recruiter. Score this resume from 0-100 for the role."),
            HumanMessage(content=f"Position: {position}\n\nJD:\n{jd_text}\n\nResume:\n{resume}\n\n"
                                  "Return JSON: {{\"score\": 0-100, \"strengths\": [], \"gaps\": [], \"summary\": \"\"}}"),
        ]).content
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        screen_data = json.loads(match.group()) if match else {"score": 50, "strengths": [], "gaps": [], "summary": response}
    except Exception as e:
        screen_data = {"score": 50, "strengths": [], "gaps": [], "summary": str(e)}
    print(f"  [Rec 2/7] Resume score: {screen_data.get('score', 0)}/100")
    return {
        "task_data":   {**task, "screening": screen_data},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "screen_resume",
                          "score": screen_data.get("score")}],
    }


def node_generate_questions(state: HRSystemState) -> Dict[str, Any]:
    task     = state.get("task_data") or {}
    position = task.get("position", "role")
    jd_text  = task.get("jd_text", "")
    gaps     = task.get("screening", {}).get("gaps", [])
    try:
        response = _llm(0.5).invoke([
            SystemMessage(content="Generate 5 targeted interview questions."),
            HumanMessage(content=f"Role: {position}\nJD: {jd_text}\nGaps to probe: {gaps}\n"
                                  "Return a JSON array of 5 question strings."),
        ]).content
        import re
        match = re.search(r'\[.*\]', response, re.DOTALL)
        questions = json.loads(match.group()) if match else [response]
    except Exception:
        questions = [
            f"Describe your experience with {position} responsibilities.",
            "How do you handle tight deadlines?",
            "Give an example of a challenging problem you solved.",
            "How do you stay updated with industry trends?",
            "Where do you see yourself in 3 years?",
        ]
    print(f"  [Rec 3/7] Generated {len(questions)} interview questions")
    return {
        "task_data":   {**task, "questions": questions},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "generate_questions"}],
    }


def node_conduct_interview(state: HRSystemState) -> Dict[str, Any]:
    """
    In a real deployment: this node runs iteratively, presenting
    each question and collecting answers through the API.
    Here we simulate with pre-provided answers.
    """
    task      = state.get("task_data") or {}
    questions = task.get("questions", [])
    answers   = task.get("interview_answers", [""] * len(questions))
    qa_log    = [{"q": q, "a": a} for q, a in zip(questions, answers)]
    print(f"  [Rec 4/7] Interview: {len(qa_log)} Q&A pairs recorded")
    return {
        "task_data":   {**task, "qa_log": qa_log},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "conduct_interview"}],
    }


def node_evaluate_responses(state: HRSystemState) -> Dict[str, Any]:
    task     = state.get("task_data") or {}
    qa_log   = task.get("qa_log", [])
    position = task.get("position", "role")
    qa_str   = "\n".join(f"Q: {qa['q']}\nA: {qa['a']}" for qa in qa_log)
    try:
        response = _llm(0.0).invoke([
            SystemMessage(content="Evaluate interview answers. Return JSON with technical_score(0-100), cultural_fit(0-100), notes."),
            HumanMessage(content=f"Role: {position}\n\n{qa_str}"),
        ]).content
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        scores = json.loads(match.group()) if match else {"technical_score": 70, "cultural_fit": 70, "notes": ""}
    except Exception:
        scores = {"technical_score": 70, "cultural_fit": 70, "notes": "Evaluation pending"}
    print(f"  [Rec 5/7] Scores: tech={scores.get('technical_score')} culture={scores.get('cultural_fit')}")
    return {
        "task_data":   {**task, "interview_scores": scores},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "evaluate_responses"}],
    }


def node_rank_candidate(state: HRSystemState) -> Dict[str, Any]:
    task    = state.get("task_data") or {}
    isc     = task.get("interview_scores", {})
    screen  = task.get("screening", {})
    t_score = isc.get("technical_score", 0)
    c_score = isc.get("cultural_fit", 0)
    r_score = screen.get("score", 0)
    overall = round((t_score * 0.4 + c_score * 0.3 + r_score * 0.3), 1)
    rec     = ("SHORTLIST" if overall >= 70 else "HOLD" if overall >= 50 else "REJECT")
    name    = task.get("candidate_name", "Candidate")
    pos     = task.get("position", "role")
    eval_   = CandidateEvaluation(
        candidate_name     = name,
        position           = pos,
        technical_score    = t_score,
        cultural_fit_score = c_score,
        overall_score      = overall,
        recommendation     = rec,
        interview_questions= task.get("questions", []),
        evaluation_notes   = isc.get("notes", ""),
    )
    print(f"  [Rec 6/7] {name}: {rec} ({overall}/100)")
    return {
        "structured_output": eval_.model_dump(),
        "agent_response":    f"{name}: {rec} (Score: {overall}/100)",
        "decision":          rec,
        "task_data": {**task, "evaluation": eval_.model_dump()},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "rank_candidate",
                          "recommendation": rec}],
    }


def node_notify_hr(state: HRSystemState) -> Dict[str, Any]:
    out  = state.get("structured_output") or {}
    name = out.get("candidate_name", "Candidate")
    pos  = out.get("position", "role")
    rec  = out.get("recommendation", "N/A")
    send_hr_manager_alert.invoke({
        "subject": f"🧑‍💼 Candidate Evaluation: {name} — {rec}",
        "message": f"Candidate: {name}\nPosition: {pos}\nRecommendation: {rec}\nScore: {out.get('overall_score')}/100",
    })
    print(f"  [Rec 7/7] HR notified: {name} → {rec}")
    return {
        "is_complete": True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "notify_hr"}],
    }


def build_recruitment_subgraph():
    g     = StateGraph(HRSystemState)
    nodes = [
        ("load_requirements",   node_load_requirements),
        ("screen_resume",       node_screen_resume),
        ("generate_questions",  node_generate_questions),
        ("conduct_interview",   node_conduct_interview),
        ("evaluate_responses",  node_evaluate_responses),
        ("rank_candidate",      node_rank_candidate),
        ("notify_hr",           node_notify_hr),
    ]
    for name, fn in nodes:
        g.add_node(name, fn)
    g.set_entry_point(nodes[0][0])
    for i in range(len(nodes) - 1):
        g.add_edge(nodes[i][0], nodes[i + 1][0])
    g.add_edge(nodes[-1][0], END)
    return g.compile()
