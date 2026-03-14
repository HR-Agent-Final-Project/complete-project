# AI-Powered HR Management System
## Multi-Agent LangGraph Architecture — B.Tech Final Year Project
### University of Vocational Technology, Sri Lanka

**Group:** B1-S3 | SOF/21/B1/17 – K. C. Deshapriya | SOF/21/B1/10 – J. A. D. D. Theekshana  
**Supervisor:** Dr. Kaneeka Vidanage

---

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and DATABASE_URL

# 2. Install dependencies
uv add -r requirements.txt

# 3. Run the server
uv run uvicorn main:app --reload --port 8001

# 4. Open API docs
http://localhost:8001/docs
```

---

## Architecture

```
User Request
     │
     ▼
[Supervisor Agent]  ← classifies intent via structured LLM output
     │
     ├──→ [HR Chat Agent]      agents/hr_chat_agent.py
     ├──→ [Leave Agent]        agents/leave_agent.py       ← 9-node workflow + interrupt
     ├──→ [Payroll Agent]      agents/payroll_agent.py     ← 8-node workflow
     ├──→ [Attendance Agent]   agents/attendance_agent.py  ← face recognition
     ├──→ [Performance Agent]  agents/performance_agent.py ← scoring + LLM narrative
     ├──→ [Recruitment Agent]  agents/recruitment_agent.py ← CV + interview
     ├──→ [Detection Agent]    agents/detection_agent.py   ← security alerts
     └──→ [Reporting Agent]    agents/reporting_agent.py   ← analytics

Shared Services:
  ChromaDB (RAG) → rag/knowledge_base.py
  PostgreSQL      → models/database.py
  Notifications   → tools/email_tools.py
  Audit Logger    → models/database.py (AuditLog)
```

## Project Structure

```
hr_agent_system/
├── main.py                    FastAPI entry point
├── requirements.txt
├── .env.example
├── config/settings.py         All config in one place
├── core/
│   ├── state.py               HRSystemState (shared TypedDict)
│   ├── supervisor.py          Intent classification + routing
│   └── graph.py               Master LangGraph compilation
├── agents/
│   ├── hr_chat_agent.py       ReAct loop with RAG tools
│   ├── leave_agent.py         9-node sequential workflow
│   ├── payroll_agent.py       8-node payroll calculation
│   ├── attendance_agent.py    Face recognition workflow
│   ├── performance_agent.py   Scoring + LLM narrative
│   ├── recruitment_agent.py   CV screening + interview
│   ├── detection_agent.py     Security threat assessment
│   └── reporting_agent.py     Analytics + KPI reports
├── tools/
│   ├── database_tools.py      SQLAlchemy query tools
│   ├── rag_tools.py           ChromaDB retrieval tools
│   ├── face_recognition_tools.py  DeepFace tools
│   ├── email_tools.py         Notification tools
│   └── analytics_tools.py    Aggregation tools
├── models/
│   ├── database.py            SQLAlchemy ORM models
│   └── schemas.py             Pydantic schemas
├── rag/
│   ├── knowledge_base.py      ChromaDB setup + seeding
│   └── sample_policies/       HR policy text files
├── api/routes/
│   ├── chat.py                POST /api/chat
│   ├── attendance.py          POST /api/attendance/checkin
│   ├── leave.py               POST /api/leave/apply
│   ├── payroll.py             GET /api/payroll/generate/{id}/{period}
│   └── reports.py             GET/POST /api/reports
└── tests/
    ├── test_supervisor.py
    ├── test_leave_agent.py
    └── test_graph_flow.py
```

## API Endpoints

| Method | Path | Agent | Description |
|--------|------|-------|-------------|
| POST | `/api/chat` | HR Chat | Natural language HR questions |
| POST | `/api/leave/apply` | Leave | Submit leave application |
| POST | `/api/attendance/checkin` | Attendance | Face recognition clock-in/out |
| GET | `/api/payroll/generate/{id}/{period}` | Payroll | Generate payslip |
| GET | `/api/performance/{id}` | Performance | Evaluation report |
| POST | `/api/recruitment/interview` | Recruitment | CV screening + interview |
| POST | `/api/security/detect` | Detection | Security alert |
| POST | `/api/reports/generate` | Reporting | Analytics report |
| GET | `/api/graph/visualize` | System | LangGraph Mermaid diagram |

## Key Design Principles

- **No if-else in agents** — LLM drives all reasoning via `with_structured_output()`
- **Shared state** — `HRSystemState` TypedDict is the contract between all agents
- **Tools = data only** — tools fetch data, LLM decides what it means
- **Sub-graphs** — each agent is independently testable and composable
- **Interrupt** — graph pauses at `human_review_checkpoint` for escalated cases
- **Audit trail** — every agent step appended with `operator.add` reducer

## Running Tests

```bash
uv run pytest tests/ -v
```
