# HRAgent SaaS Platform — Multi-Tenant Enterprise HR System
## Complete Engineering Specification

---

## Project Vision

Convert the existing single-company HR system into a **production-grade, multi-tenant SaaS platform** hosted at a single domain, where independent companies purchase subscriptions and receive fully isolated, secure HR environments.

The platform must be designed from day one to handle **millions of concurrent requests** with enterprise-scale reliability, zero cross-tenant data leakage, and a built-in AI knowledge layer per company.

**Platform owner company:** zeven.ink — SSO/OAuth integrations will be handled through zeven.ink's existing infrastructure.

---

## Part 1 — Multi-Tenancy Architecture

**Tenant = one registered company.**

Every company registration creates an isolated tenant with its own:
- Scoped database schema or row-level tenant ID on all tables
- Dedicated **Pinecone vector database index** (one index per company, not shared)
- Isolated file storage namespace
- Isolated AI conversation context (no bleed between companies)

**Rules:**
- Tenant ID must be validated on **every single API call** at the middleware layer before any business logic executes
- A request from Company A must be **physically incapable** of returning Company B data — enforced at ORM/query level, not just UI filtering
- New tenant provisioning (including Pinecone index creation) must be **fully automated** on company registration

---

## Part 2 — Company Onboarding Profile

On registration, companies complete a full onboarding wizard collecting:

### Basic Details
- Company name, industry, size (headcount), registration/tax number
- Headquarters address, country, timezone
- Primary contact: name, email, phone

### Knowledge Base
Used to populate the company's dedicated vector database index.

- Vision statement
- Mission statement
- Core values
- Company policies (HR policy, leave policy, code of conduct, etc.)
- Active departments and projects
- Top-level leadership: name + designation (CEO, CTO, HR Director, etc.)

### Document Upload
Accepts: `.txt`, `.docx`, `.pdf`, `.csv`

- All uploaded documents are chunked, embedded, and stored in the company's **dedicated Pinecone index** at registration time
- This vector data powers the AI chat agent to answer company-specific HR questions

---

## Part 3 — Subscription Packages & Billing

**Payment Gateway:** Dialog (Sri Lanka) and HelaPay (Sri Lanka)

| Package | Billing | Employee Seat Limit | AI Access | REST API |
|---|---|---|---|---|
| **Basic** | Monthly / Annual | Max **50** employees | 1-week preview per month | No access |
| **Pro** | Monthly / Annual | Max **500** employees | Full access all month | Limited (rate-capped) |
| **Enterprise** | One-time lifetime | **Unlimited** employees | Full access, unlimited | Unlimited, no rate limits |

### Free Trial
- All new registrations and all companies currently using the existing system receive **1 month free Pro trial**
- No payment info required upfront
- At trial end: company selects a paid package or account auto-deactivates

### AI Usage (Claude API — Anthropic)
- **Basic:** AI agent available for a **1-week preview window per month** (upsell preview only)
- **Pro:** Full AI agent system access for the entire month
- **Enterprise:** Full AI agent system access, unlimited, forever

### REST API Access
- **Basic:** No API access
- **Pro:** API access with rate limits (requests per minute/day cap)
- **Enterprise:** API access with no rate limits

---

## Part 4 — Subscription Lifecycle & Data Retention

### Active → Deactivated Flow (Basic & Pro only)

```
Payment lapses
    → Day 7 before cutoff: warning email sent
    → Day 3 before cutoff: warning email sent
    → Day 1 before cutoff: final warning email sent
    → Cutoff date: login disabled, all features inaccessible
    → Data retained securely for 12 months
    → Day 335 (30 days before purge): final warning email sent
    → Day 365: automated data export job runs BEFORE any deletion
        - Full database export (all tenant tables) → compressed archive
        - All uploaded files → archive
        - Pinecone vector index → exported snapshot
        - Archive stored in cold storage (platform-controlled)
    → After successful archive: live data purged from active systems
    → Pinecone index kept in cold storage (NOT deleted)
```

### Reactivation
- During 12-month retention: company can reactivate at any time by resuming payment — data restored instantly
- After 12 months: company archive available for a **data recovery fee** (premium service revenue stream)

### Enterprise Accounts
Never deactivate. Permanent. No lifecycle rules apply.

---

## Part 5 — Role-Based Access Control (RBAC)

### Platform-Level Roles
| Role | Scope |
|---|---|
| Platform Super Admin (zeven.ink) | All tenants, billing, platform metrics |

### Within Each Company Tenant
| Role | Permissions |
|---|---|
| Company Admin | Full access to all company data and settings |
| HR Manager | Employees, leave, attendance, recruitment, reports |
| Employee | Own profile, own leave, own attendance, own payslips |
| *(extensible)* | Additional roles configurable by Company Admin |

**Enforcement rules:**
- Role + tenant ID embedded in JWT on every authenticated request
- Every API endpoint validates both before returning any data
- All database queries always scoped by `tenant_id` + role permissions at ORM level — never at UI layer only

---

## Part 6 — Enterprise-Scale Architecture

### Backend
- **FastAPI** — stateless, horizontally scalable services
- Load balancer in front of all API instances
- **PostgreSQL** with connection pooling (PgBouncer) and read replicas
- **Redis** for session caching, rate limiting, tenant config caching
- **Celery** async task queue for:
  - AI agent processing
  - Report generation
  - Bulk CSV imports
  - Document embedding jobs
  - Data export/archive jobs
  - Subscription lifecycle jobs (deactivation, warnings)
- Per-tenant rate limiting to prevent noisy-neighbor degradation

### AI / Vector Layer
- **Pinecone:** one dedicated index per tenant, auto-provisioned on company registration
- **Claude API (Anthropic):** powers all AI agent features in Pro/Enterprise tiers
- All AI requests include tenant-scoped context only — no shared memory across companies

### Storage
- **S3-compatible** tenant-namespaced file storage
- **Cold storage tier** for 12-month archived company data exports

### Frontend
- React / TypeScript (existing codebase)
- Neobrutalism UI design system (existing)
- CDN for all static assets

### Operations
- Docker + Docker Compose (local dev)
- Health checks and auto-restart on all services
- Zero-downtime deployments
- Horizontal autoscaling in production
- Multi-region deployment support (GDPR / EU data residency compliance)

---

## Part 7 — Platform Super-Admin Panel

Dashboard for the zeven.ink platform owner:

- List all registered companies: subscription status, plan, seat usage, join date
- Manually activate / suspend / delete tenants
- Platform-wide metrics: active tenants, MRR, churn, API usage
- Manage subscription plans and pricing
- Trigger manual data export/archive jobs
- Monitor system health: API latency, queue depths, DB connections
- View scheduled deactivations and upcoming data purges

---

## Part 8 — Security Requirements

- All inter-tenant API calls validate tenant context on every single request
- JWT tokens embed tenant ID and role — backend validates both on every endpoint
- Uploaded files (PDFs, CSVs) scanned and sandboxed before vector ingestion
- All sensitive data encrypted at rest and in transit (TLS 1.3 minimum)
- Audit logging for all admin-level actions within each tenant
- GDPR-compliant data deletion workflows enforced via the 12-month retention pipeline
- Pinecone indexes provisioned with isolated API keys per tenant

---

## Part 9 — Future Scope (Not Current Build)

These are confirmed out of scope for now and will be added in future releases:

- Custom domain / white-label per company (e.g., `hr.companyname.com`)
- Email/SMS notification system (Dialog/SendGrid integration)
- SSO / OAuth per company (Google Workspace, Microsoft 365) — will route through zeven.ink infrastructure

---

## Open Questions (2 Remaining)

| # | Question | Why It Matters |
|---|---|---|
| 1 | **Basic AI preview week** — does the 1-week reset every calendar month (always first 7 days), or is it a rolling 7-day window from when the user first triggers AI? | Determines how the AI usage counter and reset logic is implemented |
| 2 | **Enterprise seat limit** — truly unlimited headcount, or does the company set a custom seat count at purchase time (e.g., buy 2,000 seats)? | Determines if Enterprise has seat-based pricing tiers or is flat-rate |

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Database | PostgreSQL + PgBouncer + Redis |
| Task Queue | Celery |
| Vector Database | Pinecone (one index per tenant) |
| AI Model | Claude API (Anthropic) |
| Frontend | React + TypeScript |
| File Storage | S3-compatible (tenant-namespaced) |
| Containerization | Docker + Docker Compose |
| Payment | Dialog (Sri Lanka) + HelaPay (Sri Lanka) |
| Auth | JWT (tenant ID + role embedded) |
| Platform Owner | zeven.ink |
