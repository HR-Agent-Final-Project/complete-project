# Appendix H — Database Schema Documentation

## H.1 — PostgreSQL Table Definitions and Relationships

---

## Database Configuration

| Parameter        | Value                                      |
|------------------|--------------------------------------------|
| Engine           | PostgreSQL via SQLAlchemy                  |
| ORM              | SQLAlchemy DeclarativeBase                 |
| Pool Size        | 5 (max overflow: 10)                       |
| Pool Timeout     | 30 seconds                                 |
| Pool Recycle     | 300 seconds                                |
| Connection Timeout | 10 seconds                               |
| Timestamps       | All tables: `created_at`, `updated_at` (auto, timezone-aware) |
| URL Format       | `postgresql://username:password@host:port/database_name` |

---

## Table Overview

| # | Table Name              | Domain              | Description                                 |
|---|-------------------------|---------------------|---------------------------------------------|
| 1 | `employees`             | Core HR             | All employee records and authentication     |
| 2 | `departments`           | Core HR             | Company departments                         |
| 3 | `roles`                 | Core HR             | Job roles and access levels                 |
| 4 | `attendance`            | Attendance          | Daily attendance records (face recognition) |
| 5 | `attendance_scans`      | Attendance          | Individual clock-in/out scan events         |
| 6 | `leave_types`           | Leave Management    | Leave type definitions and rules            |
| 7 | `leave_balances`        | Leave Management    | Per-employee leave balance tracking         |
| 8 | `leave_requests`        | Leave Management    | Leave applications with AI decision fields  |
| 9 | `performance_reviews`   | Performance         | Periodic employee performance reviews       |
| 10 | `performance_metrics`  | Performance         | Individual metric scores per review         |
| 11 | `hr_policies`          | Policy & Compliance | HR policy documents (linked to ChromaDB)    |
| 12 | `notifications`        | Communication       | In-app and email notifications              |
| 13 | `audit_logs`           | Audit & Security    | Full action audit trail                     |
| 14 | `job_postings`         | Recruitment         | Open job postings                           |
| 15 | `job_applications`     | Recruitment         | Candidate applications with AI scoring      |
| 16 | `chat_sessions`        | Communication       | AI chatbot conversation sessions            |
| 17 | `chat_messages`        | Communication       | Individual chatbot messages                 |
| 18 | `hr_reports`           | Reporting           | Generated HR reports and narratives         |

---

## Table 1 — `employees`

> Central table. All other tables relate back to this one either directly or indirectly.

| Column              | Type                                                                 | Constraints                        | Description                                  |
|---------------------|----------------------------------------------------------------------|------------------------------------|----------------------------------------------|
| id                  | INTEGER                                                              | PRIMARY KEY                        | Unique identifier                            |
| employee_number     | VARCHAR(20)                                                          | UNIQUE, NOT NULL, INDEX            | Company-assigned ID (e.g., `EMP001`)         |
| first_name          | VARCHAR(100)                                                         | NOT NULL                           | First name                                   |
| last_name           | VARCHAR(100)                                                         | NOT NULL                           | Last name                                    |
| full_name           | VARCHAR(200)                                                         | NOT NULL                           | Cached full name                             |
| nic_number          | VARCHAR(20)                                                          | UNIQUE, NULLABLE                   | Sri Lanka National ID Card number            |
| date_of_birth       | DATE                                                                 | NULLABLE                           | Date of birth                                |
| gender              | ENUM(`male`, `female`, `other`)                                      | NULLABLE                           | Gender                                       |
| personal_email      | VARCHAR(200)                                                         | UNIQUE, NOT NULL                   | Personal email address                       |
| work_email          | VARCHAR(200)                                                         | UNIQUE, NULLABLE                   | Work email address                           |
| phone_number        | VARCHAR(100)                                                         | NULLABLE                           | Contact phone number                         |
| address             | TEXT                                                                 | NULLABLE                           | Street address                               |
| city                | VARCHAR(100)                                                         | NULLABLE                           | City                                         |
| district            | VARCHAR(100)                                                         | NULLABLE                           | Sri Lanka district                           |
| hashed_password     | VARCHAR(255)                                                         | NOT NULL                           | Bcrypt hashed password                       |
| is_active           | BOOLEAN                                                              | DEFAULT TRUE                       | Account active flag                          |
| last_login          | TIMESTAMPTZ                                                          | NULLABLE                           | Last login timestamp                         |
| department_id       | INTEGER                                                              | FK → departments.id                | Department reference                         |
| role_id             | INTEGER                                                              | FK → roles.id                      | Job role reference                           |
| manager_id          | INTEGER                                                              | FK → employees.id (self-ref)       | Direct manager (self-referencing)            |
| hire_date           | DATE                                                                 | NULLABLE                           | Employment start date                        |
| probation_end       | DATE                                                                 | NULLABLE                           | Probation period end date                    |
| termination_date    | DATE                                                                 | NULLABLE                           | Employment end date                          |
| employment_type     | VARCHAR(50)                                                          | DEFAULT `full_time`                | `full_time` / `part_time` / `contract` / `intern` |
| status              | ENUM(`active`, `inactive`, `on_leave`, `terminated`, `probation`)   | DEFAULT `probation`                | Current employment status                    |
| base_salary         | NUMERIC(12,2)                                                        | NULLABLE                           | Monthly salary in LKR                        |
| bank_account        | VARCHAR(50)                                                          | NULLABLE                           | Bank account number                          |
| bank_name           | VARCHAR(100)                                                         | NULLABLE                           | Bank name                                    |
| face_embedding      | JSON                                                                 | NULLABLE                           | DeepFace vector array for recognition        |
| face_registered     | BOOLEAN                                                              | DEFAULT FALSE                      | Face enrollment flag                         |
| face_registered_at  | TEXT                                                                 | NULLABLE                           | ISO datetime string of face registration     |
| language_pref       | VARCHAR(5)                                                           | DEFAULT `en`                       | UI language preference: `en` / `si` / `ta`  |
| profile_photo       | VARCHAR(500)                                                         | NULLABLE                           | Profile photo URL                            |
| created_at          | TIMESTAMPTZ                                                          | SERVER DEFAULT now()               | Record creation timestamp                    |
| updated_at          | TIMESTAMPTZ                                                          | SERVER DEFAULT now()               | Record last updated timestamp                |

**Relationships:**

| Relation             | Type        | Target Table           | Notes                       |
|----------------------|-------------|------------------------|-----------------------------|
| department           | Many → One  | departments            | back_populates="employees"  |
| role                 | Many → One  | roles                  | back_populates="employees"  |
| manager              | Many → One  | employees (self)       | remote_side=[id]            |
| attendance_records   | One → Many  | attendance             | cascade delete              |
| leave_requests       | One → Many  | leave_requests         | cascade delete              |
| leave_balances       | One → Many  | leave_balances         | cascade delete              |
| performance_reviews  | One → Many  | performance_reviews    | cascade delete              |
| notifications        | One → Many  | notifications          | cascade delete              |
| audit_logs           | One → Many  | audit_logs             | cascade delete              |
| job_applications     | One → Many  | job_applications       | cascade delete              |

---

## Table 2 — `departments`

| Column      | Type         | Constraints          | Description                         |
|-------------|--------------|----------------------|-------------------------------------|
| id          | INTEGER      | PRIMARY KEY          | Unique identifier                   |
| name        | VARCHAR(100) | UNIQUE, NOT NULL     | Department name (e.g., `Engineering`) |
| code        | VARCHAR(20)  | UNIQUE, NOT NULL     | Short code (e.g., `ENG`)            |
| description | TEXT         | NULLABLE             | Department description              |
| is_active   | BOOLEAN      | DEFAULT TRUE         | Active flag                         |
| created_at  | TIMESTAMPTZ  | SERVER DEFAULT now() | Record creation timestamp           |
| updated_at  | TIMESTAMPTZ  | SERVER DEFAULT now() | Record last updated timestamp       |

**Relationships:** ← `employees.department_id`, ← `job_postings.department_id`

---

## Table 3 — `roles`

| Column      | Type           | Constraints          | Description                                          |
|-------------|----------------|----------------------|------------------------------------------------------|
| id          | INTEGER        | PRIMARY KEY          | Unique identifier                                    |
| title       | VARCHAR(100)   | UNIQUE, NOT NULL     | Job title (e.g., `Software Engineer`)                |
| code        | VARCHAR(30)    | UNIQUE, NOT NULL     | Role code (e.g., `SWE`)                              |
| description | TEXT           | NULLABLE             | Role description                                     |
| access_level| INTEGER        | DEFAULT 1            | `1`=Employee, `2`=HR Staff, `3`=HR Manager, `4`=Admin |
| base_salary | NUMERIC(12,2)  | NULLABLE             | Default LKR base salary for this role                |
| is_active   | BOOLEAN        | DEFAULT TRUE         | Active flag                                          |
| created_at  | TIMESTAMPTZ    | SERVER DEFAULT now() | Record creation timestamp                            |
| updated_at  | TIMESTAMPTZ    | SERVER DEFAULT now() | Record last updated timestamp                        |

**Relationships:** ← `employees.role_id`

---

## Table 4 — `attendance`

> One record per employee per working day. Clock-in/out times stored with timezone.

| Column              | Type                                                   | Constraints          | Description                                      |
|---------------------|--------------------------------------------------------|----------------------|--------------------------------------------------|
| id                  | INTEGER                                                | PRIMARY KEY          | Unique identifier                                |
| employee_id         | INTEGER                                                | FK → employees.id, NOT NULL, INDEX | Employee reference                   |
| work_date           | DATE                                                   | NOT NULL, INDEX      | Calendar date                                    |
| clock_in            | TIMESTAMPTZ                                            | NULLABLE             | Clock-in timestamp                               |
| clock_out           | TIMESTAMPTZ                                            | NULLABLE             | Clock-out timestamp                              |
| work_hours          | FLOAT                                                  | NULLABLE             | Calculated working hours (e.g., `8.5`)           |
| confidence_score    | FLOAT                                                  | NULLABLE             | DeepFace recognition confidence (0.0–1.0)        |
| verification_method | ENUM(`face_recognition`, `manual_override`, `rfid`)    | DEFAULT `face_recognition` | How attendance was verified              |
| is_verified         | BOOLEAN                                                | DEFAULT FALSE        | Face confirmed flag                              |
| attendance_type     | ENUM(`regular`, `overtime`, `half_day`, `holiday`)     | DEFAULT `regular`    | Type of attendance                               |
| is_late             | BOOLEAN                                                | DEFAULT FALSE        | Arrived after workday start + grace period       |
| late_minutes        | INTEGER                                                | DEFAULT 0            | Minutes late from scheduled start               |
| is_early_departure  | BOOLEAN                                                | DEFAULT FALSE        | Left before workday end                          |
| overtime_hours      | FLOAT                                                  | DEFAULT 0.0          | Hours worked beyond standard day                 |
| location            | VARCHAR(200)                                           | NULLABLE             | e.g., `Head Office`, `Remote`, `Matara Branch`   |
| is_absent           | BOOLEAN                                                | DEFAULT FALSE        | Absence flag                                     |
| absence_reason      | TEXT                                                   | NULLABLE             | Reason for absence                               |
| notes               | TEXT                                                   | NULLABLE             | HR notes (e.g., `Approved WFH`)                  |
| flagged             | BOOLEAN                                                | DEFAULT FALSE        | Suspicious activity flag                         |
| flag_reason         | TEXT                                                   | NULLABLE             | e.g., `Low confidence 0.45`                      |
| clock_in_photo      | VARCHAR(500)                                           | NULLABLE             | Snapshot file path at clock-in                   |
| clock_out_photo     | VARCHAR(500)                                           | NULLABLE             | Snapshot file path at clock-out                  |
| created_at          | TIMESTAMPTZ                                            | SERVER DEFAULT now() | Record creation timestamp                        |
| updated_at          | TIMESTAMPTZ                                            | SERVER DEFAULT now() | Record last updated timestamp                    |

**Relationships:** → `employees`, ← `attendance_scans.attendance_id`

---

## Table 5 — `attendance_scans`

> Raw scan events. Multiple scans may exist per attendance record (e.g., re-attempts).

| Column        | Type         | Constraints                          | Description                                |
|---------------|--------------|--------------------------------------|--------------------------------------------|
| id            | INTEGER      | PRIMARY KEY                          | Unique identifier                          |
| attendance_id | INTEGER      | FK → attendance.id, NOT NULL, INDEX  | Parent attendance record                   |
| employee_id   | INTEGER      | FK → employees.id, NOT NULL, INDEX   | Employee reference                         |
| scan_type     | VARCHAR(20)  | NOT NULL                             | `clock_in` or `clock_out`                  |
| scanned_at    | TIMESTAMPTZ  | NOT NULL                             | Timestamp of the scan event                |
| confidence    | FLOAT        | NULLABLE                             | DeepFace confidence (0.0–1.0)              |
| photo_path    | VARCHAR(500) | NULLABLE                             | Path to saved face snapshot                |
| created_at    | TIMESTAMPTZ  | SERVER DEFAULT now()                 | Record creation timestamp                  |
| updated_at    | TIMESTAMPTZ  | SERVER DEFAULT now()                 | Record last updated timestamp              |

**Relationships:** → `attendance`, → `employees`

---

## Table 6 — `leave_types`

> Master configuration for each leave category available in the system.

| Column               | Type         | Constraints          | Description                                          |
|----------------------|--------------|----------------------|------------------------------------------------------|
| id                   | INTEGER      | PRIMARY KEY          | Unique identifier                                    |
| name                 | VARCHAR(100) | UNIQUE, NOT NULL     | e.g., `Annual Leave`, `Sick Leave`, `Maternity Leave` |
| code                 | VARCHAR(20)  | UNIQUE, NOT NULL     | Short code: `AL`, `SL`, `ML`, `CL`                   |
| description          | TEXT         | NULLABLE             | Description of the leave type                        |
| max_days_per_year    | INTEGER      | NOT NULL             | Maximum days allowed per calendar year               |
| max_consecutive_days | INTEGER      | NULLABLE             | Max days in a single request (null = unlimited)      |
| requires_document    | BOOLEAN      | DEFAULT FALSE        | Medical certificate or document required             |
| is_paid              | BOOLEAN      | DEFAULT TRUE         | Paid or unpaid leave                                 |
| gender_specific      | VARCHAR(10)  | NULLABLE             | `female` for maternity leave; null = all genders     |
| is_active            | BOOLEAN      | DEFAULT TRUE         | Active flag                                          |
| created_at           | TIMESTAMPTZ  | SERVER DEFAULT now() | Record creation timestamp                            |
| updated_at           | TIMESTAMPTZ  | SERVER DEFAULT now() | Record last updated timestamp                        |

**Relationships:** ← `leave_balances.leave_type_id`, ← `leave_requests.leave_type_id`

---

## Table 7 — `leave_balances`

> Tracks each employee's leave entitlement and usage per leave type per year.

| Column          | Type        | Constraints                          | Description                                     |
|-----------------|-------------|--------------------------------------|-------------------------------------------------|
| id              | INTEGER     | PRIMARY KEY                          | Unique identifier                               |
| employee_id     | INTEGER     | FK → employees.id, NOT NULL, INDEX   | Employee reference                              |
| leave_type_id   | INTEGER     | FK → leave_types.id, NOT NULL        | Leave type reference                            |
| year            | INTEGER     | NOT NULL                             | Calendar year (e.g., `2025`)                    |
| total_days      | FLOAT       | NOT NULL                             | Days allocated for this year                    |
| used_days       | FLOAT       | DEFAULT 0.0                          | Days already taken                              |
| pending_days    | FLOAT       | DEFAULT 0.0                          | Days in pending/approved requests               |
| remaining_days  | FLOAT       | NOT NULL                             | `total_days - used_days - pending_days`         |
| carried_over    | FLOAT       | DEFAULT 0.0                          | Days carried forward from previous year         |
| created_at      | TIMESTAMPTZ | SERVER DEFAULT now()                 | Record creation timestamp                       |
| updated_at      | TIMESTAMPTZ | SERVER DEFAULT now()                 | Record last updated timestamp                   |

**Relationships:** → `employees`, → `leave_types`

---

## Table 8 — `leave_requests`

> Leave application records. Includes full AI decision fields and HR override support.

| Column              | Type                                                                                   | Constraints                         | Description                                           |
|---------------------|----------------------------------------------------------------------------------------|-------------------------------------|-------------------------------------------------------|
| id                  | INTEGER                                                                                | PRIMARY KEY                         | Unique identifier                                     |
| employee_id         | INTEGER                                                                                | FK → employees.id, NOT NULL, INDEX  | Applicant employee                                    |
| leave_type_id       | INTEGER                                                                                | FK → leave_types.id, NOT NULL       | Leave type reference                                  |
| start_date          | DATE                                                                                   | NOT NULL                            | Leave start date                                      |
| end_date            | DATE                                                                                   | NOT NULL                            | Leave end date                                        |
| total_days          | FLOAT                                                                                  | NOT NULL                            | Calculated working days in range                      |
| reason              | TEXT                                                                                   | NOT NULL                            | Employee's stated reason                              |
| is_half_day         | BOOLEAN                                                                                | DEFAULT FALSE                       | Half-day leave flag                                   |
| status              | ENUM(`pending`, `approved`, `rejected`, `escalated`, `cancelled`, `on_leave`, `completed`) | DEFAULT `pending`, INDEX        | Current request status                                |
| ai_decision         | VARCHAR(20)                                                                            | NULLABLE                            | AI output: `approved` or `rejected`                   |
| ai_decision_reason  | TEXT                                                                                   | NULLABLE                            | LLM-generated explanation                             |
| ai_confidence       | FLOAT                                                                                  | NULLABLE                            | AI decision confidence (0.0–1.0)                      |
| ai_policy_refs      | JSON                                                                                   | NULLABLE                            | Policy document chunks used by AI                     |
| ai_processed_at     | TEXT                                                                                   | NULLABLE                            | ISO datetime of AI processing                         |
| rejection_reason    | TEXT                                                                                   | NULLABLE                            | Reason if rejected                                    |
| approved_by         | VARCHAR(200)                                                                           | NULLABLE                            | Name of approver                                      |
| approved_at         | TIMESTAMP                                                                              | NULLABLE                            | Approval timestamp                                    |
| reviewed_by_id      | INTEGER                                                                                | FK → employees.id                   | HR reviewer employee ID                               |
| hr_override         | BOOLEAN                                                                                | DEFAULT FALSE                       | HR manually overrode AI decision                      |
| hr_notes            | TEXT                                                                                   | NULLABLE                            | HR reviewer notes                                     |
| document_url        | VARCHAR(500)                                                                           | NULLABLE                            | S3/storage URL of supporting document                 |
| document_verified   | BOOLEAN                                                                                | DEFAULT FALSE                       | Document verified by HR                               |
| is_appealed         | BOOLEAN                                                                                | DEFAULT FALSE                       | Employee appealed the decision                        |
| appeal_reason       | TEXT                                                                                   | NULLABLE                            | Reason for appeal                                     |
| appeal_status       | VARCHAR(20)                                                                            | NULLABLE                            | `pending` / `upheld` / `overturned`                   |
| created_at          | TIMESTAMPTZ                                                                            | SERVER DEFAULT now()                | Record creation timestamp                             |
| updated_at          | TIMESTAMPTZ                                                                            | SERVER DEFAULT now()                | Record last updated timestamp                         |

**Relationships:** → `employees` (applicant via `employee_id`), → `employees` (reviewer via `reviewed_by_id`), → `leave_types`

---

## Table 9 — `performance_reviews`

> Periodic performance evaluations. Can be generated by AI or assigned to a manager reviewer.

| Column                 | Type                                                  | Constraints                         | Description                                           |
|------------------------|-------------------------------------------------------|-------------------------------------|-------------------------------------------------------|
| id                     | INTEGER                                               | PRIMARY KEY                         | Unique identifier                                     |
| employee_id            | INTEGER                                               | FK → employees.id, NOT NULL, INDEX  | Employee being reviewed                               |
| reviewer_id            | INTEGER                                               | FK → employees.id, NULLABLE         | Manager reviewer (null = AI-generated)                |
| period_type            | ENUM(`monthly`, `quarterly`, `annual`, `probation`)   | NOT NULL                            | Review period type                                    |
| period_start           | DATE                                                  | NOT NULL                            | Start of review period                                |
| period_end             | DATE                                                  | NOT NULL                            | End of review period                                  |
| attendance_score       | FLOAT                                                 | NULLABLE                            | 0–100: `present_days / working_days × 100`           |
| punctuality_score      | FLOAT                                                 | NULLABLE                            | 0–100: `100 - (late_days / present_days × 100)`      |
| overtime_score         | FLOAT                                                 | NULLABLE                            | 0–100: voluntary overtime contribution               |
| overall_score          | FLOAT                                                 | NULLABLE                            | 0–100: weighted average (primary KPI)                |
| rating                 | VARCHAR(50)                                           | NULLABLE                            | `Excellent` / `Good` / `Satisfactory` / `Needs Improvement` |
| strengths              | TEXT                                                  | NULLABLE                            | What the employee did well                            |
| areas_to_improve       | TEXT                                                  | NULLABLE                            | Areas requiring improvement                           |
| goals_next_period      | TEXT                                                  | NULLABLE                            | Goals set for the next period                         |
| manager_comments       | TEXT                                                  | NULLABLE                            | Free-text manager feedback                            |
| ai_summary             | TEXT                                                  | NULLABLE                            | AI-generated narrative summary                        |
| status                 | ENUM(`draft`, `pending`, `completed`, `disputed`)     | DEFAULT `draft`                     | Review workflow status                                |
| is_promotion_eligible  | BOOLEAN                                               | DEFAULT FALSE                       | Flagged for promotion consideration                   |
| requires_pip           | BOOLEAN                                               | DEFAULT FALSE                       | Performance Improvement Plan required                 |
| employee_acknowledged  | BOOLEAN                                               | DEFAULT FALSE                       | Employee has read the review                          |
| created_at             | TIMESTAMPTZ                                           | SERVER DEFAULT now()                | Record creation timestamp                             |
| updated_at             | TIMESTAMPTZ                                           | SERVER DEFAULT now()                | Record last updated timestamp                         |

**Relationships:** → `employees` (subject & reviewer), ← `performance_metrics`

---

## Table 10 — `performance_metrics`

> Granular metric breakdown per performance review.

| Column      | Type         | Constraints                                  | Description                                   |
|-------------|--------------|----------------------------------------------|-----------------------------------------------|
| id          | INTEGER      | PRIMARY KEY                                  | Unique identifier                             |
| review_id   | INTEGER      | FK → performance_reviews.id, NOT NULL, INDEX | Parent review record                          |
| metric_name | VARCHAR(200) | NOT NULL                                     | e.g., `Days Present`, `Times Late`, `OT Hours` |
| value       | FLOAT        | NOT NULL                                     | Raw metric number                             |
| score       | FLOAT        | NULLABLE                                     | Calculated 0–100 score for this metric        |
| weight      | FLOAT        | DEFAULT 1.0                                  | Weight in overall_score calculation           |
| note        | TEXT         | NULLABLE                                     | Additional notes                              |

**Relationships:** → `performance_reviews`

---

## Table 11 — `hr_policies`

> Stores HR policy documents. The `chroma_doc_id` links each record to its vector embeddings in ChromaDB (see H.3).

| Column          | Type                                                                              | Constraints          | Description                                     |
|-----------------|-----------------------------------------------------------------------------------|----------------------|-------------------------------------------------|
| id              | INTEGER                                                                           | PRIMARY KEY          | Unique identifier                               |
| title           | VARCHAR(300)                                                                      | NOT NULL             | e.g., `Annual Leave Policy 2025`                |
| category        | ENUM(`leave`, `attendance`, `payroll`, `conduct`, `recruitment`, `performance`, `general`) | NOT NULL, INDEX | Policy category                          |
| content         | TEXT                                                                              | NOT NULL             | Full policy text (chunked into ChromaDB)        |
| version         | VARCHAR(20)                                                                       | NULLABLE             | e.g., `v2.1`                                    |
| effective_date  | VARCHAR(20)                                                                       | NULLABLE             | ISO date string                                 |
| expiry_date     | VARCHAR(20)                                                                       | NULLABLE             | ISO date string                                 |
| chroma_doc_id   | VARCHAR(200)                                                                      | UNIQUE, NULLABLE     | ChromaDB document ID — cross-reference to H.3   |
| is_indexed      | BOOLEAN                                                                           | DEFAULT FALSE        | Whether content has been ingested to ChromaDB   |
| indexed_at      | TEXT                                                                              | NULLABLE             | ISO datetime of ChromaDB ingestion              |
| chunk_count     | INTEGER                                                                           | NULLABLE             | Number of vector chunks in ChromaDB             |
| is_active       | BOOLEAN                                                                           | DEFAULT TRUE         | Active flag                                     |
| uploaded_by_id  | INTEGER                                                                           | NULLABLE             | Employee ID of the uploader                     |
| tags            | JSON                                                                              | NULLABLE             | e.g., `["annual", "leave", "eligibility"]`      |
| language        | VARCHAR(5)                                                                        | DEFAULT `en`         | `en` / `si` / `ta`                              |
| created_at      | TIMESTAMPTZ                                                                       | SERVER DEFAULT now() | Record creation timestamp                       |
| updated_at      | TIMESTAMPTZ                                                                       | SERVER DEFAULT now() | Record last updated timestamp                   |

---

## Table 12 — `notifications`

| Column               | Type         | Constraints                         | Description                                              |
|----------------------|--------------|-------------------------------------|----------------------------------------------------------|
| id                   | INTEGER      | PRIMARY KEY                         | Unique identifier                                        |
| employee_id          | INTEGER      | FK → employees.id, NOT NULL, INDEX  | Notification recipient                                   |
| notification_type    | VARCHAR(50)  | NOT NULL, INDEX                     | e.g., `leave_approved`, `leave_rejected`, `payslip_ready`, `system_alert` |
| title                | VARCHAR(300) | NOT NULL                            | Short notification heading                               |
| message              | TEXT         | NOT NULL                            | Full notification message body                           |
| action_url           | VARCHAR(500) | NULLABLE                            | Deep link (e.g., `/leave/request/42`)                    |
| channel              | ENUM(`in_app`, `email`, `both`) | DEFAULT `both`       | Delivery channel                                         |
| is_read              | BOOLEAN      | DEFAULT FALSE                       | Read status                                              |
| read_at              | TEXT         | NULLABLE                            | ISO datetime when read                                   |
| email_sent           | BOOLEAN      | DEFAULT FALSE                       | Email delivery confirmed flag                            |
| email_sent_at        | TEXT         | NULLABLE                            | ISO datetime of email send                               |
| related_entity_type  | VARCHAR(50)  | NULLABLE                            | e.g., `leave_request`, `payroll`, `performance_review`   |
| related_entity_id    | INTEGER      | NULLABLE                            | ID of the related record                                 |
| priority             | VARCHAR(20)  | DEFAULT `normal`                    | `low` / `normal` / `high` / `urgent`                     |
| extra_data           | JSON         | NULLABLE                            | Additional structured data                               |
| created_at           | TIMESTAMPTZ  | SERVER DEFAULT now()                | Record creation timestamp                                |
| updated_at           | TIMESTAMPTZ  | SERVER DEFAULT now()                | Record last updated timestamp                            |

**Relationships:** → `employees`

---

## Table 13 — `audit_logs`

> Immutable audit trail for all actions performed by employees, HR managers, admins, and the AI agent.

| Column       | Type         | Constraints                        | Description                                              |
|--------------|--------------|------------------------------------|----------------------------------------------------------|
| id           | INTEGER      | PRIMARY KEY                        | Unique identifier                                        |
| employee_id  | INTEGER      | FK → employees.id, NULLABLE, INDEX | Who performed the action (null = system)                 |
| actor_type   | VARCHAR(20)  | NOT NULL                           | `employee` / `hr_manager` / `admin` / `ai_agent` / `system` |
| ip_address   | VARCHAR(50)  | NULLABLE                           | Source IP address                                        |
| action       | VARCHAR(100) | NOT NULL, INDEX                    | Dot-notation: `module.verb` (e.g., `leave.approved`)     |
| description  | TEXT         | NULLABLE                           | Human-readable action description                        |
| entity_type  | VARCHAR(50)  | NULLABLE                           | `leave_request` / `employee` / `payroll` / `attendance`  |
| entity_id    | INTEGER      | NULLABLE                           | ID of the affected record                                |
| before_state | JSON         | NULLABLE                           | Record state before the action                           |
| after_state  | JSON         | NULLABLE                           | Record state after the action                            |
| metadata     | JSON         | NULLABLE                           | AI reasoning, policy references, extra context           |
| status       | VARCHAR(20)  | DEFAULT `success`                  | `success` / `failed` / `blocked`                         |
| error_message| TEXT         | NULLABLE                           | Error details on failure                                 |
| created_at   | TIMESTAMPTZ  | SERVER DEFAULT now()               | Record creation timestamp                                |
| updated_at   | TIMESTAMPTZ  | SERVER DEFAULT now()               | Record last updated timestamp                            |

**Relationships:** → `employees`

---

## Table 14 — `job_postings`

| Column                  | Type           | Constraints                          | Description                                  |
|-------------------------|----------------|--------------------------------------|----------------------------------------------|
| id                      | INTEGER        | PRIMARY KEY                          | Unique identifier                            |
| title                   | VARCHAR(200)   | NOT NULL                             | Job title                                    |
| department_id           | INTEGER        | FK → departments.id, NULLABLE        | Hiring department                            |
| description             | TEXT           | NOT NULL                             | Full job description                         |
| requirements            | TEXT           | NOT NULL                             | Required skills and qualifications           |
| responsibilities        | TEXT           | NULLABLE                             | Job responsibilities                         |
| salary_min              | NUMERIC(12,2)  | NULLABLE                             | Minimum salary (LKR)                         |
| salary_max              | NUMERIC(12,2)  | NULLABLE                             | Maximum salary (LKR)                         |
| employment_type         | VARCHAR(50)    | DEFAULT `full_time`                  | `full_time` / `part_time` / `contract`        |
| location                | VARCHAR(200)   | NULLABLE                             | Job location                                 |
| positions_count         | INTEGER        | DEFAULT 1                            | Number of open positions                     |
| closing_date            | DATE           | NULLABLE                             | Application deadline                         |
| is_active               | BOOLEAN        | DEFAULT TRUE                         | Posting active flag                          |
| posted_by_id            | INTEGER        | FK → employees.id, NULLABLE          | HR employee who created the posting          |
| ai_interview_questions  | JSON           | NULLABLE                             | AI-generated interview questions             |
| culture_keywords        | JSON           | NULLABLE                             | Company culture keyword tags                 |
| created_at              | TIMESTAMPTZ    | SERVER DEFAULT now()                 | Record creation timestamp                    |
| updated_at              | TIMESTAMPTZ    | SERVER DEFAULT now()                 | Record last updated timestamp                |

**Relationships:** → `departments`, → `employees` (poster), ← `job_applications`

---

## Table 15 — `job_applications`

> Stores both internal (existing employees) and external candidate applications, including AI screening scores.

| Column               | Type         | Constraints                          | Description                                               |
|----------------------|--------------|--------------------------------------|-----------------------------------------------------------|
| id                   | INTEGER      | PRIMARY KEY                          | Unique identifier                                         |
| job_posting_id       | INTEGER      | FK → job_postings.id, NOT NULL, INDEX| Job posting reference                                     |
| applicant_id         | INTEGER      | FK → employees.id, NULLABLE          | Internal candidate (employee)                             |
| applicant_name       | VARCHAR(200) | NULLABLE                             | External candidate name                                   |
| applicant_email      | VARCHAR(200) | NULLABLE                             | External candidate email                                  |
| applicant_phone      | VARCHAR(20)  | NULLABLE                             | External candidate phone                                  |
| resume_url           | VARCHAR(500) | NULLABLE                             | Storage URL of uploaded resume                            |
| cover_letter         | TEXT         | NULLABLE                             | Cover letter text                                         |
| status               | ENUM(`applied`, `screening`, `ai_interview`, `shortlisted`, `hr_interview`, `offered`, `accepted`, `rejected`, `withdrawn`) | DEFAULT `applied` | Application pipeline status |
| ai_resume_score      | FLOAT        | NULLABLE                             | 0–100: AI resume-to-job-description match score           |
| ai_interview_score   | FLOAT        | NULLABLE                             | 0–100: AI interview performance score                     |
| ai_culture_fit       | FLOAT        | NULLABLE                             | 0–100: AI culture fit score                               |
| ai_overall_score     | FLOAT        | NULLABLE                             | Weighted average of the three AI scores                   |
| ai_recommendation    | VARCHAR(50)  | NULLABLE                             | `shortlist` / `reject` / `hold`                           |
| ai_feedback          | TEXT         | NULLABLE                             | Detailed AI evaluation feedback                           |
| interview_transcript | JSON         | NULLABLE                             | Array of `{question, answer, score}` objects              |
| hr_notes             | TEXT         | NULLABLE                             | HR reviewer notes                                         |
| reviewed_by_id       | INTEGER      | FK → employees.id, NULLABLE          | HR reviewer employee                                      |
| hr_score             | FLOAT        | NULLABLE                             | HR manual score                                           |
| created_at           | TIMESTAMPTZ  | SERVER DEFAULT now()                 | Record creation timestamp                                 |
| updated_at           | TIMESTAMPTZ  | SERVER DEFAULT now()                 | Record last updated timestamp                             |

**Relationships:** → `job_postings`, → `employees` (applicant), → `employees` (reviewer)

---

## Table 16 — `chat_sessions`

| Column      | Type         | Constraints                         | Description                                  |
|-------------|--------------|-------------------------------------|----------------------------------------------|
| id          | INTEGER      | PRIMARY KEY                         | Unique identifier                            |
| employee_id | INTEGER      | FK → employees.id, NOT NULL, INDEX  | Session owner                                |
| title       | VARCHAR(200) | NULLABLE                            | Auto-populated from first message content    |
| is_active   | BOOLEAN      | DEFAULT TRUE                        | Session active flag                          |
| created_at  | TIMESTAMPTZ  | SERVER DEFAULT now()                | Record creation timestamp                    |
| updated_at  | TIMESTAMPTZ  | SERVER DEFAULT now()                | Record last updated timestamp                |

**Relationships:** → `employees`, ← `chat_messages`

---

## Table 17 — `chat_messages`

| Column     | Type        | Constraints                             | Description                                       |
|------------|-------------|-----------------------------------------|---------------------------------------------------|
| id         | INTEGER     | PRIMARY KEY                             | Unique identifier                                 |
| session_id | INTEGER     | FK → chat_sessions.id, NOT NULL, INDEX  | Parent session                                    |
| role       | VARCHAR(20) | NOT NULL                                | `user` or `assistant`                             |
| content    | TEXT        | NOT NULL                                | Message text                                      |
| sources    | TEXT        | NULLABLE                                | JSON list of HR policy sources cited              |
| created_at | TIMESTAMPTZ | SERVER DEFAULT now()                    | Record creation timestamp                         |
| updated_at | TIMESTAMPTZ | SERVER DEFAULT now()                    | Record last updated timestamp                     |

**Relationships:** → `chat_sessions`

---

## Table 18 — `hr_reports`

| Column       | Type         | Constraints          | Description                                              |
|--------------|--------------|----------------------|----------------------------------------------------------|
| id           | INTEGER      | PRIMARY KEY          | Unique identifier                                        |
| report_type  | VARCHAR(100) | NOT NULL, INDEX      | e.g., `monthly_summary`, `attendance`, `leave`, `performance`, `department` |
| period       | VARCHAR(50)  | NULLABLE             | e.g., `2026-03`, `2026-Q1`, `2026`                       |
| title        | VARCHAR(300) | NOT NULL             | Report title                                             |
| content      | JSON         | DEFAULT `{}`         | Full structured data — KPIs, breakdowns, statistics      |
| narrative    | TEXT         | NULLABLE             | AI-generated executive summary                           |
| generated_by | VARCHAR(200) | DEFAULT `system`     | `AI Agent` or employee name                              |
| created_at   | TIMESTAMPTZ  | SERVER DEFAULT now() | Record creation timestamp                                |
| updated_at   | TIMESTAMPTZ  | SERVER DEFAULT now() | Record last updated timestamp                            |

---

## Enum Definitions

### EmployeeStatus
| Value       | Description                     |
|-------------|---------------------------------|
| `active`    | Currently employed              |
| `inactive`  | Temporarily inactive            |
| `on_leave`  | Currently on approved leave     |
| `terminated`| Employment ended                |
| `probation` | In probationary period          |

### Gender
| Value    | Description |
|----------|-------------|
| `male`   | Male        |
| `female` | Female      |
| `other`  | Other       |

### AttendanceType
| Value      | Description                    |
|------------|--------------------------------|
| `regular`  | Standard working day           |
| `overtime` | Overtime day                   |
| `half_day` | Half-day attendance            |
| `holiday`  | Public holiday attendance      |

### VerificationMethod
| Value              | Description                        |
|--------------------|------------------------------------|
| `face_recognition` | DeepFace biometric verification    |
| `manual_override`  | HR manually confirmed attendance   |
| `rfid`             | RFID card scan                     |

### LeaveStatus
| Value       | Description                           |
|-------------|---------------------------------------|
| `pending`   | Awaiting AI/HR decision               |
| `approved`  | Leave approved                        |
| `rejected`  | Leave denied                          |
| `escalated` | Escalated to senior HR                |
| `cancelled` | Cancelled by employee                 |
| `on_leave`  | Employee currently on this leave      |
| `completed` | Leave period has ended                |

### ReviewPeriod
| Value       | Description                |
|-------------|----------------------------|
| `monthly`   | Monthly review             |
| `quarterly` | Quarterly review           |
| `annual`    | Annual review              |
| `probation` | End-of-probation review    |

### ReviewStatus
| Value       | Description                     |
|-------------|---------------------------------|
| `draft`     | In preparation                  |
| `pending`   | Awaiting acknowledgement        |
| `completed` | Finalised                       |
| `disputed`  | Employee has raised a dispute   |

### PolicyCategory
| Value          | Description                    |
|----------------|--------------------------------|
| `leave`        | Leave-related policies         |
| `attendance`   | Attendance policies            |
| `payroll`      | Payroll and compensation       |
| `conduct`      | Code of conduct                |
| `recruitment`  | Recruitment policies           |
| `performance`  | Performance management         |
| `general`      | General HR policies            |

### NotificationChannel
| Value    | Description                          |
|----------|--------------------------------------|
| `in_app` | In-application notification only     |
| `email`  | Email notification only              |
| `both`   | Both in-app and email                |

### ApplicationStatus
| Value          | Description                          |
|----------------|--------------------------------------|
| `applied`      | Application received                 |
| `screening`    | Under initial screening              |
| `ai_interview` | In AI interview stage                |
| `shortlisted`  | Shortlisted for HR interview         |
| `hr_interview` | HR interview scheduled/completed     |
| `offered`      | Job offer extended                   |
| `accepted`     | Offer accepted                       |
| `rejected`     | Application rejected                 |
| `withdrawn`    | Candidate withdrew application       |

---

## Key Constraints and Indexes

### Unique Constraints

| Table            | Column(s)                                 |
|------------------|-------------------------------------------|
| employees        | `employee_number`, `nic_number`, `personal_email`, `work_email` |
| departments      | `name`, `code`                            |
| roles            | `title`, `code`                           |
| leave_types      | `name`, `code`                            |
| hr_policies      | `chroma_doc_id`                           |

### Foreign Key Constraints

| Table                | Column            | References                   | On Delete   |
|----------------------|-------------------|------------------------------|-------------|
| employees            | department_id     | departments.id               | SET NULL    |
| employees            | role_id           | roles.id                     | SET NULL    |
| employees            | manager_id        | employees.id (self)          | SET NULL    |
| attendance           | employee_id       | employees.id                 | CASCADE     |
| attendance_scans     | attendance_id     | attendance.id                | CASCADE     |
| attendance_scans     | employee_id       | employees.id                 | CASCADE     |
| leave_balances       | employee_id       | employees.id                 | CASCADE     |
| leave_balances       | leave_type_id     | leave_types.id               | CASCADE     |
| leave_requests       | employee_id       | employees.id                 | CASCADE     |
| leave_requests       | leave_type_id     | leave_types.id               | CASCADE     |
| leave_requests       | reviewed_by_id    | employees.id                 | SET NULL    |
| performance_reviews  | employee_id       | employees.id                 | CASCADE     |
| performance_reviews  | reviewer_id       | employees.id                 | SET NULL    |
| performance_metrics  | review_id         | performance_reviews.id       | CASCADE     |
| notifications        | employee_id       | employees.id                 | CASCADE     |
| audit_logs           | employee_id       | employees.id                 | SET NULL    |
| job_postings         | department_id     | departments.id               | SET NULL    |
| job_postings         | posted_by_id      | employees.id                 | SET NULL    |
| job_applications     | job_posting_id    | job_postings.id              | CASCADE     |
| job_applications     | applicant_id      | employees.id                 | CASCADE     |
| job_applications     | reviewed_by_id    | employees.id                 | SET NULL    |
| chat_sessions        | employee_id       | employees.id                 | CASCADE     |
| chat_messages        | session_id        | chat_sessions.id             | CASCADE     |

### Indexes

| Table               | Indexed Column(s)                   |
|---------------------|-------------------------------------|
| employees           | `employee_number`, `personal_email` |
| attendance          | `employee_id`, `work_date`          |
| attendance_scans    | `attendance_id`, `employee_id`      |
| leave_balances      | `employee_id`                       |
| leave_requests      | `employee_id`, `status`             |
| performance_reviews | `employee_id`                       |
| performance_metrics | `review_id`                         |
| notifications       | `employee_id`, `notification_type`  |
| audit_logs          | `employee_id`, `action`             |
| job_postings        | (via FK indexes)                    |
| job_applications    | `job_posting_id`                    |
| chat_sessions       | `employee_id`                       |
| chat_messages       | `session_id`                        |
| hr_policies         | `category`                          |
| hr_reports          | `report_type`                       |

---

## Entity Relationship Diagram (Text)

```
                        ┌─────────────┐
                        │ departments │
                        └──────┬──────┘
                               │ 1
                    ┌──────────┼──────────────┐
                    │          │              │
                    │ n        │ n            │ n
             ┌──────┴──────────┴──────┐  ┌───┴──────────┐
             │       employees        │  │ job_postings │
             │  (self-ref: manager)   │  └───┬──────────┘
             └──────────┬─────────────┘      │ 1
                        │                    │ n
          ┌─────────────┼──────────────┐  ┌──┴──────────────┐
          │             │              │  │ job_applications │
          │             │              │  └─────────────────┘
     ┌────┴────┐  ┌─────┴──────┐  ┌───┴──────────────────┐
     │attendance│  │leave_      │  │  performance_reviews │
     └────┬────┘  │requests    │  └──────────┬───────────┘
          │ 1     └─────┬──────┘             │ 1
          │ n           │                    │ n
   ┌──────┴──────┐  ┌───┴──────────┐  ┌─────┴────────────┐
   │attendance_  │  │leave_balances│  │performance_      │
   │scans        │  │leave_types   │  │metrics           │
   └─────────────┘  └──────────────┘  └──────────────────┘

employees ──< notifications
employees ──< audit_logs
employees ──< chat_sessions ──< chat_messages

hr_policies  (linked externally to ChromaDB via chroma_doc_id — see H.3)
hr_reports   (standalone, system-generated)
roles        (referenced by employees)
```

---

## Business Rules Encoded in Schema

| Rule                       | Value                              | Where Enforced               |
|----------------------------|------------------------------------|------------------------------|
| Attendance threshold       | 85% presence required              | leave_requests (AI check)    |
| Late arrival grace period  | 15 minutes after workday start     | attendance.is_late           |
| Workday start              | 08:30                              | attendance.late_minutes calc |
| Workday end                | 17:30                              | attendance.is_early_departure |
| Overtime multiplier        | 1.5×                               | attendance.overtime_hours    |
| EPF — Employee contribution| 8%                                 | Payroll calculation layer    |
| EPF — Employer contribution| 12%                                | Payroll calculation layer    |
| ETF                        | 3%                                 | Payroll calculation layer    |
| Default access level       | 1 (Employee)                       | roles.access_level           |
| Default employment status  | `probation`                        | employees.status             |
| AI confidence threshold    | Stored per request                 | leave_requests.ai_confidence |

---

## Summary

| Domain              | Tables                                                                   | Count |
|---------------------|--------------------------------------------------------------------------|-------|
| Core HR             | `employees`, `departments`, `roles`                                      | 3     |
| Attendance          | `attendance`, `attendance_scans`                                         | 2     |
| Leave Management    | `leave_types`, `leave_balances`, `leave_requests`                        | 3     |
| Performance         | `performance_reviews`, `performance_metrics`                             | 2     |
| Policy & Compliance | `hr_policies`                                                            | 1     |
| Recruitment         | `job_postings`, `job_applications`                                       | 2     |
| Communication/Audit | `notifications`, `audit_logs`, `chat_sessions`, `chat_messages`, `hr_reports` | 5 |
| **Total**           |                                                                          | **18**|

---

*Document: Appendix H.1 — PostgreSQL Table Definitions and Relationships*
*System: HR Management System with AI Integration*
*Generated: 2026-03-22*
