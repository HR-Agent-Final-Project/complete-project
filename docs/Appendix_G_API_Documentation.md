# Appendix G — API Documentation

## G.1 FastAPI REST API Endpoint Reference (Swagger/OpenAPI)

The HR system backend is built with **FastAPI** and exposes a full REST API following OpenAPI 3.0 standards. Interactive documentation is auto-generated and available at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

### Base URL
```
http://localhost:8000/api
```

### Global Headers
| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <access_token>` | Yes (most endpoints) |
| `Content-Type` | `application/json` | Yes (POST/PUT/PATCH) |
| `Accept` | `application/json` | Recommended |

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| `200` | OK — Request succeeded |
| `201` | Created — Resource created |
| `204` | No Content — Success with no body |
| `400` | Bad Request — Validation error |
| `401` | Unauthorized — Missing or invalid token |
| `403` | Forbidden — Insufficient access level |
| `404` | Not Found — Resource does not exist |
| `409` | Conflict — Duplicate resource |
| `422` | Unprocessable Entity — FastAPI validation error |
| `429` | Too Many Requests — Rate limit exceeded |
| `500` | Internal Server Error |

### Rate Limiting
- **General endpoints:** 60 requests/minute per IP
- **Login endpoint:** 5 failed attempts triggers a **15-minute block** per IP

---

## G.2 Authentication API Specifications

**Base Path:** `/api/auth`

All authenticated endpoints require the JWT access token in the `Authorization` header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Details
| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Access Token Expiry | 60 minutes |
| Refresh Token Expiry | 7 days |
| Token Type | Bearer |

**JWT Payload Claims:**
```json
{
  "sub": "1",
  "email": "employee@company.lk",
  "role": 2,
  "exp": 1711100400,
  "type": "access"
}
```

### Access Level Matrix
| Level | Label | Permissions |
|-------|-------|-------------|
| 1 | Employee | View own data, apply for leave, use chat |
| 2 | HR Staff | View all employees, reports, manage attendance |
| 3 | HR Manager | Approve leaves, register/update employees, generate reports |
| 4 | Admin | Full system access, manage roles/departments |

---

### POST `/api/auth/login`
Authenticate with employee number or email and password.

**Auth Required:** No

**Request Body:**
```json
{
  "identifier": "IT0001",
  "password": "string"
}
```
> `identifier` accepts either employee number (e.g., `IT0001`) or personal/work email.

**Response `200 OK`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "employee_id": 1,
  "employee_name": "Kavindu Perera",
  "email": "kavindu@company.lk",
  "access_level": 2,
  "department": "IT",
  "role": "Software Engineer",
  "profile_photo": "/uploads/profile_photos/1.jpg",
  "must_change_password": false
}
```

---

### POST `/api/auth/google/firebase`
Authenticate using a Firebase Google OAuth ID token.

**Auth Required:** No

**Request Body:**
```json
{
  "id_token": "Firebase ID token from Google Sign-In"
}
```

**Response `200 OK`:** Same structure as `/login`

---

### POST `/api/auth/register`
Register a new employee account. Generates employee number and temporary password.

**Auth Required:** Yes (Level 3+ HR Manager)

**Request Body:**
```json
{
  "first_name": "Amali",
  "last_name": "Fernando",
  "personal_email": "amali@gmail.com",
  "phone_number": "0771234567",
  "department_id": 1,
  "role_id": 3,
  "employment_type": "full_time",
  "base_salary": 150000.00,
  "language_pref": "en"
}
```

**Employment Types:** `full_time` | `part_time` | `contract` | `intern`

**Response `201 Created`:**
```json
{
  "message": "Employee registered successfully.",
  "employee_id": 12,
  "employee_number": "IT0012",
  "full_name": "Amali Fernando",
  "email": "amali@gmail.com",
  "temp_password": "Temp@4521",
  "department": "IT",
  "role": "Junior Developer"
}
```

---

### POST `/api/auth/self-register`
Self-registration for HR Admin or Management roles. Requires HR approval before login is granted.

**Auth Required:** No

**Request Body:**
```json
{
  "first_name": "Nimal",
  "last_name": "Silva",
  "personal_email": "nimal@company.lk",
  "password": "Secure@123",
  "confirm_password": "Secure@123",
  "requested_role": "hr_admin",
  "phone_number": "0779876543"
}
```

**Response `200 OK`:**
```json
{
  "message": "Registration submitted. Approval email sent to HR."
}
```
> Account is created as **inactive**. An approval link is emailed to the HR Manager. Login is only permitted after approval.

---

### GET `/api/auth/approve/{token}`
Email-based approval link for self-registered accounts.

**Auth Required:** No

**Response:** HTML confirmation page

---

### POST `/api/auth/set-password`
Set a new password on first login (required when `must_change_password: true`).

**Auth Required:** Yes (JWT Bearer)

**Password Requirements:** Minimum 8 characters, at least 1 uppercase letter, at least 1 digit.

**Request Body:**
```json
{
  "temp_password": "Temp@4521",
  "new_password": "NewSecure@99",
  "confirm_password": "NewSecure@99"
}
```

**Response `200 OK`:**
```json
{
  "message": "Password updated successfully. Please log in again."
}
```

---

### POST `/api/auth/forgot-password`
Send a password reset link to the employee's registered email.

**Auth Required:** No

**Request Body:**
```json
{
  "email": "amali@gmail.com"
}
```

**Response `200 OK`:**
```json
{
  "message": "If your email is registered, you will receive a reset link."
}
```
> Always returns success to prevent email enumeration attacks.

---

### POST `/api/auth/reset-password`
Reset the password using a token from the reset email link.

**Auth Required:** No

**Request Body:**
```json
{
  "reset_token": "abc123xyz",
  "new_password": "NewPass@88",
  "confirm_password": "NewPass@88"
}
```

**Response `200 OK`:**
```json
{
  "message": "Password reset successful. Please log in with your new password."
}
```

---

### POST `/api/auth/refresh`
Obtain a new access token using a valid refresh token.

**Auth Required:** No

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response `200 OK`:** Same structure as `/login`

---

### GET `/api/auth/me`
Get the profile of the currently authenticated user.

**Auth Required:** Yes

**Response `200 OK`:**
```json
{
  "id": 1,
  "employee_number": "IT0001",
  "full_name": "Kavindu Perera",
  "email": "kavindu@gmail.com",
  "work_email": "kavindu@company.lk",
  "department": "IT",
  "role": "Software Engineer",
  "access_level": 1,
  "status": "active",
  "face_registered": true,
  "language_pref": "en",
  "profile_photo": "/uploads/profile_photos/1.jpg",
  "hire_date": "2025-01-15"
}
```

---

### POST `/api/auth/logout`
Invalidate the current session and access token.

**Auth Required:** Yes

**Response `200 OK`:**
```json
{
  "message": "Goodbye Kavindu! Logged out successfully."
}
```

---

### POST `/api/auth/token`
OAuth2 password flow endpoint for Swagger UI authentication.

**Auth Required:** No

**Form Data:** `username`, `password` (OAuth2PasswordRequestForm)

**Response `200 OK`:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## G.3 Attendance API Specifications

**Base Path:** `/api/attendance`

The attendance module supports **face recognition-based clock-in/clock-out** via DeepFace embeddings, manual HR overrides, and detailed reporting.

---

### POST `/api/attendance/register-face`
Enroll an employee's face for biometric attendance.

**Auth Required:** Yes (Any employee or HR+)

**Request Body:**
```json
{
  "image_base64": "<base64-encoded JPEG image>"
}
```

**Response `200 OK`:**
```json
{
  "message": "Face registered successfully.",
  "employee_id": 1,
  "face_registered": true
}
```
> Only the DeepFace **embedding vector** is stored — the actual photo is not persisted.

---

### POST `/api/attendance/clock-in-face`
Clock in using face recognition. Designed for use with a shared tablet/kiosk.

**Auth Required:** No (tablet endpoint)

**Request Body:**
```json
{
  "employee_id": 1,
  "image_base64": "<base64-encoded JPEG>"
}
```

**Response `200 OK`:**
```json
{
  "message": "Clocked in successfully.",
  "employee_name": "Kavindu Perera",
  "clock_in_time": "08:32:00",
  "is_late": true,
  "late_minutes": 2
}
```

---

### POST `/api/attendance/clock-out-face`
Clock out using face recognition.

**Auth Required:** No (tablet endpoint)

**Request Body:**
```json
{
  "employee_id": 1,
  "image_base64": "<base64-encoded JPEG>"
}
```

**Response `200 OK`:**
```json
{
  "message": "Clocked out successfully.",
  "employee_name": "Kavindu Perera",
  "clock_in_time": "08:32:00",
  "clock_out_time": "17:35:00",
  "work_hours": 9.05,
  "overtime_hours": 0.55,
  "attendance_type": "overtime"
}
```

**Attendance Types:** `regular` | `overtime` | `late` | `absent` | `half_day`

---

### GET `/api/attendance/today`
Get the authenticated employee's attendance record for today.

**Auth Required:** Yes

**Response `200 OK`:**
```json
{
  "work_date": "2026-03-22",
  "clock_in": "08:32:00",
  "clock_out": "17:35:00",
  "work_hours": 9.05,
  "overtime_hours": 0.55,
  "is_late": true,
  "late_minutes": 2,
  "is_absent": false
}
```

---

### GET `/api/attendance/all`
Retrieve paginated attendance records across all employees.

**Auth Required:** Yes (Level 2+ HR Staff)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `employee_id` | int | No | Filter by employee |
| `start_date` | date | No | Format: `YYYY-MM-DD` |
| `end_date` | date | No | Format: `YYYY-MM-DD` |
| `page` | int | No | Default: `1` |
| `page_size` | int | No | Default: `20`, max: `100` |

**Response `200 OK`:**
```json
{
  "total": 250,
  "page": 1,
  "records": [
    {
      "id": 100,
      "employee_id": 1,
      "work_date": "2026-03-22",
      "day": "Saturday",
      "clock_in": "08:32:00",
      "clock_out": "17:35:00",
      "work_hours": 9.05,
      "overtime_hours": 0.55,
      "attendance_type": "overtime",
      "is_late": true,
      "late_minutes": 2,
      "is_absent": false,
      "flagged": false,
      "flag_reason": null
    }
  ]
}
```

---

### GET `/api/attendance/summary`
Monthly attendance summary for HR reporting.

**Auth Required:** Yes (Level 2+)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `period` | string | No | Format: `YYYY-MM`, defaults to current month |
| `department_id` | int | No | Filter by department |

**Response `200 OK`:**
```json
{
  "period": "2026-03",
  "working_days": 22,
  "total_employees": 50,
  "summary": {
    "overall_attendance_rate": 91.5,
    "total_present": 1005,
    "total_absent": 95,
    "total_late": 125,
    "total_ot_hours": 312.5,
    "below_threshold": 5
  },
  "employees": [
    {
      "employee_id": 1,
      "employee_number": "IT0001",
      "name": "Kavindu Perera",
      "present_days": 20,
      "absent_days": 2,
      "late_days": 3,
      "overtime_hours": 12.5,
      "attendance_rate": 90.9,
      "below_threshold": false
    }
  ]
}
```

---

### GET `/api/attendance/ot-report`
Overtime breakdown report by employee.

**Auth Required:** Yes (Level 3+ HR Manager)

**Query Parameters:** `period` (YYYY-MM), `department_id`

**Response `200 OK`:**
```json
{
  "period": "2026-03",
  "summary": {
    "total_ot_hours": 312.5,
    "total_ot_cost_units": 468.75,
    "employees_with_ot": 25,
    "avg_ot_per_employee": 12.5
  },
  "breakdown": [
    {
      "employee_id": 1,
      "employee_name": "Kavindu Perera",
      "total_ot_hours": 12.5,
      "weekday_ot_hours": 9.0,
      "weekday_ot_cost": 13.5,
      "saturday_ot_hours": 2.5,
      "saturday_ot_cost": 3.75,
      "sunday_ot_hours": 1.0,
      "sunday_ot_cost": 2.0
    }
  ]
}
```

---

### POST `/api/attendance/manual`
Manually enter or correct an attendance record.

**Auth Required:** Yes (Level 2+)

**Request Body:**
```json
{
  "employee_id": 1,
  "work_date": "2026-03-22",
  "clock_in": "08:30:00",
  "clock_out": "17:30:00",
  "is_absent": false,
  "reason": "System was unavailable — manual correction"
}
```

**Response `200 OK`:**
```json
{
  "message": "Attendance recorded.",
  "attendance": { "...": "..." }
}
```

---

### POST `/api/attendance/{id}/resolve-flag`
Resolve a flagged attendance record.

**Auth Required:** Yes (Level 3+)

**Request Body:**
```json
{
  "resolution": "Approved — employee presented valid reason",
  "attendance_type": "regular"
}
```

**Response `200 OK`:**
```json
{
  "message": "Flag resolved.",
  "attendance": { "...": "..." }
}
```

---

## G.4 Leave Management API Specifications

**Base Path:** `/api/leave`

The leave module features an **AI-powered auto-review engine** that evaluates requests against HR policies using Retrieval-Augmented Generation (RAG), attendance history, and leave balance — and auto-approves or escalates accordingly.

---

### POST `/api/leave/apply`
Submit a leave request. The AI agent automatically reviews and decides.

**Auth Required:** Yes (Any employee)

**Request Body:**
```json
{
  "leave_type_id": 1,
  "start_date": "2026-04-01",
  "end_date": "2026-04-03",
  "days_requested": 3.0,
  "reason": "Family event",
  "is_half_day": false
}
```

**Response `201 Created`:**
```json
{
  "id": 42,
  "message": "Leave request submitted.",
  "employee_id": 1,
  "leave_type": "Annual Leave",
  "leave_type_code": "AL",
  "start_date": "2026-04-01",
  "end_date": "2026-04-03",
  "days_requested": 3.0,
  "reason": "Family event",
  "status": "approved",
  "is_half_day": false,
  "ai_decision": "approved",
  "ai_reasoning": "Employee has 8 remaining annual leave days. Attendance rate is 92% (above 85% threshold). Request approved automatically.",
  "created_at": "2026-03-22T10:00:00"
}
```

**AI Decision Logic:**
| Condition | Decision |
|-----------|----------|
| Sufficient balance + attendance ≥ 85% + policy allows | `approved` |
| Insufficient balance or attendance < 85% | `rejected` |
| Ambiguous / policy conflict / special type | `escalated` → HR Manager |

**Status Values:** `pending` | `approved` | `rejected` | `escalated` | `cancelled`

---

### GET `/api/leave/my-leaves`
Retrieve the current employee's leave request history.

**Auth Required:** Yes

**Query Parameters:** `status`, `page`, `page_size`

**Response `200 OK`:**
```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "leaves": [
    {
      "id": 42,
      "leave_type": "Annual Leave",
      "leave_type_code": "AL",
      "start_date": "2026-04-01",
      "end_date": "2026-04-03",
      "days_requested": 3.0,
      "reason": "Family event",
      "status": "approved",
      "ai_decision": "approved",
      "ai_reasoning": "string",
      "is_appealed": false,
      "appeal_status": null,
      "approved_at": "2026-03-22T11:00:00",
      "created_at": "2026-03-22T10:00:00"
    }
  ]
}
```

---

### GET `/api/leave/my-balance`
Get the authenticated employee's leave balance for the current year.

**Auth Required:** Yes

**Response `200 OK`:**
```json
{
  "year": 2026,
  "balances": [
    {
      "leave_type_id": 1,
      "leave_type": "Annual Leave",
      "code": "AL",
      "total_days": 14.0,
      "used_days": 3.0,
      "pending_days": 3.0,
      "remaining_days": 8.0,
      "carried_over": 0.0
    }
  ]
}
```

---

### GET `/api/leave/all`
List all leave requests across all employees.

**Auth Required:** Yes (Level 2+)

**Query Parameters:** `employee_id`, `status`, `page`, `page_size`

**Response `200 OK`:** Same structure as `/my-leaves`

---

### GET `/api/leave/pending`
List all pending and escalated leave requests awaiting HR action.

**Auth Required:** Yes (Level 2+)

**Response `200 OK`:**
```json
{
  "total": 3,
  "pending_requests": [
    {
      "id": 42,
      "employee_id": 1,
      "employee_name": "Kavindu Perera",
      "leave_type": "Annual Leave",
      "start_date": "2026-04-01",
      "days": 3.0,
      "reason": "Family event",
      "status": "escalated",
      "ai_decision": "escalated",
      "ai_reasoning": "Escalated — consecutive days exceed 7-day limit"
    }
  ]
}
```

---

### GET `/api/leave/calendar`
Get all employees who are on leave for a given date.

**Auth Required:** Yes (Level 2+)

**Query Parameters:** `date` (YYYY-MM-DD, default: today), `department_id`

**Response `200 OK`:**
```json
{
  "date": "2026-04-01",
  "on_leave": [
    {
      "id": 42,
      "employee_id": 1,
      "employee_name": "Kavindu Perera",
      "leave_type": "Annual Leave",
      "start_date": "2026-04-01",
      "end_date": "2026-04-03"
    }
  ]
}
```

---

### POST `/api/leave/{id}/approve`
Manually approve a leave request (overrides AI decision).

**Auth Required:** Yes (Level 3+)

**Request Body:**
```json
{
  "approval_notes": "Approved as requested."
}
```

**Response `200 OK`:**
```json
{
  "message": "Leave approved.",
  "leave": { "...": "..." }
}
```

---

### POST `/api/leave/{id}/reject`
Manually reject a leave request.

**Auth Required:** Yes (Level 3+)

**Request Body:**
```json
{
  "rejection_reason": "Insufficient notice period."
}
```

**Response `200 OK`:**
```json
{
  "message": "Leave rejected.",
  "leave": { "...": "..." }
}
```

---

### POST `/api/leave/{id}/cancel`
Cancel a pending or escalated leave request (employee action).

**Auth Required:** Yes (Own leave only)

**Request Body:**
```json
{
  "cancel_reason": "Plans changed."
}
```

**Response `200 OK`:**
```json
{
  "message": "Leave cancelled.",
  "leave": { "...": "..." }
}
```
> Only `pending` or `escalated` requests can be cancelled.

---

### POST `/api/leave/{id}/appeal`
Appeal a rejected leave decision.

**Auth Required:** Yes (Own leave only)

**Request Body:**
```json
{
  "appeal_reason": "I believe this qualifies under the compassionate leave policy."
}
```

**Response `200 OK`:**
```json
{
  "message": "Appeal submitted.",
  "leave": { "...": "..." }
}
```

---

### POST `/api/leave/ai-review/{id}`
Re-trigger the AI review engine on an existing leave request.

**Auth Required:** Yes (Level 3+)

**Response `200 OK`:**
```json
{
  "message": "AI review triggered.",
  "ai_decision": "approved",
  "ai_reasoning": "On re-evaluation, employee has sufficient balance."
}
```

---

### POST `/api/leave/chat`
Ask a natural-language question about leave policies (RAG-powered).

**Auth Required:** Yes

**Request Body:**
```json
{
  "question": "How many sick leave days am I entitled to?"
}
```

**Response `200 OK`:**
```json
{
  "answer": "According to the Leave Policy (Section 3.2), employees are entitled to 7 sick leave days per calendar year. Medical certification is required for absences exceeding 3 consecutive days.",
  "sources": ["leave_policy.pdf"]
}
```

---

### GET `/api/leave/types`
List all available leave types.

**Auth Required:** Yes (Level 2+)

**Response `200 OK`:**
```json
[
  {
    "id": 1,
    "name": "Annual Leave",
    "code": "AL",
    "description": "Paid annual vacation leave",
    "max_days_per_year": 14,
    "max_consecutive_days": null,
    "requires_document": false,
    "is_paid": true,
    "gender_specific": null,
    "is_active": true
  }
]
```

---

### POST `/api/leave/types`
Create a new leave type.

**Auth Required:** Yes (Level 4 Admin)

**Request Body:**
```json
{
  "name": "Study Leave",
  "code": "STL",
  "description": "Paid leave for professional study",
  "max_days_per_year": 5,
  "max_consecutive_days": 3,
  "requires_document": true,
  "is_paid": false,
  "gender_specific": null
}
```

**Response `201 Created`:** Created leave type object

---

### GET `/api/leave/balance/{emp_id}`
Get leave balance for a specific employee.

**Auth Required:** Yes (Level 2+)

**Response `200 OK`:** Same as `/my-balance`

---

## G.5 Payroll API Specifications

**Base Path:** `/api/payroll`

The payroll module calculates monthly salary slips based on attendance, overtime, deductions, and EPF/ETF contributions.

---

### GET `/api/payroll/my-slips`
Get the authenticated employee's payslip history.

**Auth Required:** Yes

**Query Parameters:** `page`, `page_size`

**Response `200 OK`:**
```json
{
  "total": 6,
  "page": 1,
  "slips": [
    {
      "id": 25,
      "period": "2026-03",
      "period_label": "March 2026",
      "base_salary": 150000.00,
      "overtime_pay": 8750.00,
      "gross_pay": 158750.00,
      "epf_employee": 19050.00,
      "etf": 6350.00,
      "tax": 5000.00,
      "other_deductions": 0.00,
      "total_deductions": 24050.00,
      "net_pay": 134700.00,
      "present_days": 20,
      "absent_days": 2,
      "overtime_hours": 12.5,
      "status": "paid",
      "paid_on": "2026-03-25",
      "created_at": "2026-03-24T08:00:00"
    }
  ]
}
```

---

### GET `/api/payroll/slip/{slip_id}`
Get a specific payslip by ID.

**Auth Required:** Yes (Own slip, or Level 3+ for any)

**Response `200 OK`:** Full payslip object (see above)

---

### GET `/api/payroll/all`
List all payslips across all employees.

**Auth Required:** Yes (Level 3+)

**Query Parameters:** `period` (YYYY-MM), `employee_id`, `status`, `page`, `page_size`

**Response `200 OK`:**
```json
{
  "total": 150,
  "page": 1,
  "slips": [ { "...": "..." } ]
}
```

---

### POST `/api/payroll/generate`
Generate monthly payslips for all active employees.

**Auth Required:** Yes (Level 3+)

**Request Body:**
```json
{
  "period": "2026-03",
  "run_for_all": true,
  "employee_ids": null
}
```
> Set `employee_ids` to an array of IDs to run for specific employees instead of all.

**Response `200 OK`:**
```json
{
  "message": "Payroll generated for March 2026.",
  "period": "2026-03",
  "generated_count": 50,
  "total_gross": 8250000.00,
  "total_net": 6950000.00,
  "slips": [ { "...": "..." } ]
}
```

**Payroll Calculation Formula:**
| Component | Formula |
|-----------|---------|
| Base Salary | Configured per employee |
| Overtime Pay | `OT_hours × (base_salary / 240) × 1.5` |
| Gross Pay | `base_salary + overtime_pay` |
| EPF (Employee) | `gross_pay × 8%` |
| EPF (Employer) | `gross_pay × 12%` |
| ETF | `gross_pay × 3%` |
| PAYE Tax | Slab-based (as per Sri Lanka IRD) |
| Net Pay | `gross_pay − total_deductions` |

---

### POST `/api/payroll/slip/{slip_id}/mark-paid`
Mark a payslip as paid after bank transfer.

**Auth Required:** Yes (Level 3+)

**Request Body:**
```json
{
  "paid_on": "2026-03-25",
  "payment_reference": "TXN20260325001"
}
```

**Response `200 OK`:**
```json
{
  "message": "Payslip marked as paid.",
  "slip_id": 25,
  "status": "paid"
}
```

---

### GET `/api/payroll/summary`
Payroll cost summary for a given period.

**Auth Required:** Yes (Level 3+)

**Query Parameters:** `period` (YYYY-MM)

**Response `200 OK`:**
```json
{
  "period": "2026-03",
  "period_label": "March 2026",
  "employee_count": 50,
  "total_base_salary": 7500000.00,
  "total_overtime_pay": 750000.00,
  "total_gross": 8250000.00,
  "total_epf_employee": 990000.00,
  "total_epf_employer": 990000.00,
  "total_etf": 247500.00,
  "total_tax": 62500.00,
  "total_net": 6950000.00
}
```

---

## G.6 Chat Agent API Specifications

**Base Path:** `/api/chat`

The AI Chat Agent is a multi-tool RAG + database-connected assistant powered by Claude (Anthropic). It can answer HR policy questions, retrieve live employee data, and perform actions (e.g., apply for leave) conversationally. Voice interaction is supported via Whisper (STT) and TTS.

---

### Available Agent Tools

| Tool | Description |
|------|-------------|
| `search_hr_policy` | Semantic search on HR policy documents (ChromaDB) |
| `search_company_handbook` | Search company culture and employee handbook (ChromaDB) |
| `get_my_leave_balances` | Fetch the employee's current leave balances |
| `get_my_attendance` | Get attendance statistics for the last N days |
| `get_my_performance` | Get the latest performance review scores |
| `apply_leave_for_me` | Submit a leave application and trigger AI review |
| `cancel_my_leave` | Cancel a pending or escalated leave request |
| `get_my_leave_requests` | Fetch the employee's recent leave request history |

---

### POST `/api/chat/sessions`
Create a new chat session.

**Auth Required:** Yes

**Response `201 Created`:**
```json
{
  "session_id": 5,
  "message": "Session created."
}
```

---

### GET `/api/chat/sessions`
List all chat sessions for the authenticated employee.

**Auth Required:** Yes

**Response `200 OK`:**
```json
[
  {
    "id": 5,
    "title": "Leave application April 1-3",
    "is_active": true,
    "created_at": "2026-03-22T10:00:00",
    "message_count": 4
  }
]
```

---

### GET `/api/chat/sessions/{session_id}`
Retrieve a session with its full message history.

**Auth Required:** Yes (Session owner only)

**Response `200 OK`:**
```json
{
  "id": 5,
  "title": "Leave application April 1-3",
  "is_active": true,
  "created_at": "2026-03-22T10:00:00",
  "messages": [
    {
      "id": 10,
      "role": "user",
      "content": "I want annual leave from April 1 to 3.",
      "sources": [],
      "created_at": "2026-03-22T10:00:00"
    },
    {
      "id": 11,
      "role": "assistant",
      "content": "I've submitted your annual leave request for April 1–3 (3 days). It has been automatically approved. Your remaining balance is 5 days.",
      "sources": [],
      "created_at": "2026-03-22T10:00:05"
    }
  ]
}
```

---

### POST `/api/chat/sessions/{session_id}/message`
Send a message within an existing session.

**Auth Required:** Yes (Session owner only)

**Request Body:**
```json
{
  "message": "What is the policy on maternity leave?"
}
```

**Response `200 OK`:**
```json
{
  "session_id": 5,
  "message_id": 12,
  "response": "According to the HR Policy (Section 4.1), female employees are entitled to 84 days (12 weeks) of paid maternity leave after completing 6 months of service.",
  "sources": ["hr_policy.pdf"]
}
```

---

### POST `/api/chat/quick`
One-shot message without creating a persistent session.

**Auth Required:** Yes

**Request Body:**
```json
{
  "message": "What is my attendance rate this month?"
}
```

**Response `200 OK`:**
```json
{
  "session_id": 6,
  "message_id": 1,
  "response": "Your attendance rate for March 2026 is 92.3%. You have been present for 20 out of 22 working days.",
  "sources": []
}
```

---

### POST `/api/chat/voice`
Voice-based chat using Whisper STT and TTS response.

**Auth Required:** Yes

**Request:** Multipart form-data
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `audio` | file | Yes | Audio file (webm, mp3, ogg, wav) |
| `session_id` | int | No | Existing session; creates new if omitted |

**Response `200 OK`:**
```json
{
  "session_id": 5,
  "transcript": "How many annual leave days do I have left?",
  "response": "You have 8 annual leave days remaining out of 14 for 2026.",
  "sources": [],
  "audio_base64": "SUQzBAAAI1RTU0UAAAAPAAADTGF2ZjU..."
}
```

---

### DELETE `/api/chat/sessions/{session_id}`
Delete a chat session and all its messages.

**Auth Required:** Yes (Session owner only)

**Response `204 No Content`**

---

### GET `/api/chat/knowledge/status`
Check the status of the vector knowledge base.

**Auth Required:** No

**Response `200 OK`:**
```json
{
  "status": "ok",
  "collections": {
    "hr_policies": {
      "loaded": true,
      "chunks": 145
    },
    "company_culture": {
      "loaded": true,
      "chunks": 87
    },
    "job_descriptions": {
      "loaded": true,
      "chunks": 32
    }
  }
}
```

---

## G.7 Recruitment API Specifications

**Base Path:** `/api/recruitment`

The recruitment module manages job postings and applicant tracking. External candidates can apply without authentication. AI scoring of applicants is supported.

---

### GET `/api/recruitment/jobs`
List all job postings.

**Auth Required:** Yes

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | bool | `true` | Show only open positions |

**Response `200 OK`:**
```json
[
  {
    "id": 1,
    "title": "Software Engineer",
    "department": "IT",
    "department_id": 1,
    "description": "We are looking for a talented software engineer...",
    "requirements": "3+ years experience with Python or Java",
    "salary_range": "120,000 – 180,000 LKR",
    "employment_type": "full_time",
    "location": "Colombo",
    "positions_count": 2,
    "closing_date": "2026-04-30",
    "status": "active",
    "posted_date": "2026-03-01",
    "applications_count": 15
  }
]
```

---

### POST `/api/recruitment/jobs`
Create a new job posting.

**Auth Required:** Yes (Level 2+)

**Request Body:**
```json
{
  "title": "Product Manager",
  "department": "Product",
  "description": "Lead our product strategy...",
  "requirements": "MBA preferred, 3+ years PM experience",
  "salary_range": "150,000 – 200,000 LKR",
  "employment_type": "full_time",
  "location": "Colombo",
  "positions_count": 1,
  "closing_date": "2026-05-30"
}
```

**Response `201 Created`:** Created job posting object

---

### GET `/api/recruitment/jobs/{job_id}`
Get a single job posting by ID.

**Auth Required:** Yes

**Response `200 OK`:** Single job posting object

---

### PUT `/api/recruitment/jobs/{job_id}`
Update an existing job posting.

**Auth Required:** Yes (Level 2+)

**Request Body:** Same as create (all fields optional)

**Response `200 OK`:** Updated job posting object

---

### DELETE `/api/recruitment/jobs/{job_id}`
Close a job posting (soft delete — marks as inactive).

**Auth Required:** Yes (Level 2+)

**Response `204 No Content`**

---

### GET `/api/recruitment/jobs/{job_id}/applicants`
List all applicants for a specific job posting.

**Auth Required:** Yes (Level 2+)

**Response `200 OK`:**
```json
[
  {
    "id": 1,
    "job_id": 1,
    "name": "Nimal Jayasinghe",
    "email": "nimal@gmail.com",
    "phone": "0771234567",
    "status": "shortlisted",
    "ai_score": 87.5,
    "ai_recommendation": "Strong candidate — 5 years experience matches requirements",
    "interview_status": "shortlisted",
    "cover_letter": "I am very interested in this position...",
    "hr_notes": "Scheduled for interview on April 10",
    "applied_at": "2026-03-20T10:00:00"
  }
]
```

**Applicant Status Values:** `applied` | `reviewed` | `shortlisted` | `interviewed` | `rejected`

---

### POST `/api/recruitment/jobs/{job_id}/applicants`
Submit a job application (public/external endpoint).

**Auth Required:** No

**Request Body:**
```json
{
  "applicant_name": "Saman Perera",
  "applicant_email": "saman@gmail.com",
  "applicant_phone": "0779998877",
  "cover_letter": "I am very interested in contributing to your team..."
}
```

**Response `201 Created`:**
```json
{
  "id": 50,
  "job_id": 1,
  "name": "Saman Perera",
  "email": "saman@gmail.com",
  "phone": "0779998877",
  "status": "applied",
  "ai_score": null,
  "ai_recommendation": null,
  "interview_status": "applied",
  "cover_letter": "...",
  "hr_notes": null,
  "applied_at": "2026-03-22T10:00:00"
}
```

---

### PATCH `/api/recruitment/applicants/{app_id}/status`
Update the status of a job applicant.

**Auth Required:** Yes (Level 2+)

**Request Body:**
```json
{
  "status": "shortlisted",
  "hr_notes": "Strong profile — schedule technical interview"
}
```

**Response `200 OK`:** Updated applicant object

---

## Additional API Modules

### Employee Management — `/api/employees`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/employees` | Level 2+ | List all employees (paginated, filterable) |
| `GET` | `/api/employees/me` | Any | Get own profile |
| `GET` | `/api/employees/{id}` | Level 1+ | Get employee by ID |
| `POST` | `/api/employees/register` | Level 3+ | Register new employee |
| `PUT` | `/api/employees/{id}` | Level 3+ | Update employee details |
| `DELETE` | `/api/employees/{id}` | Level 3+ | Permanently delete employee |
| `PATCH` | `/api/employees/{id}/status` | Level 3+ | Activate / deactivate employee |
| `POST` | `/api/employees/{id}/enroll-face` | Level 3+ | Enroll biometric face data |
| `POST` | `/api/employees/{id}/upload-photo` | Level 1+ (own) | Upload profile photo |

---

### Reports & Analytics — `/api/reports`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/reports/dashboard` | Level 2+ | Real-time HR KPI dashboard |
| `GET` | `/api/reports/attendance/summary` | Level 2+ | Monthly attendance summary |
| `GET` | `/api/reports/attendance/trends` | Level 2+ | 6-month attendance trend chart data |
| `GET` | `/api/reports/leave/summary` | Level 2+ | Annual leave utilisation summary |
| `GET` | `/api/reports/leave/trends` | Level 2+ | Monthly leave request trends |
| `GET` | `/api/reports/performance/summary` | Level 2+ | Quarterly performance overview |
| `GET` | `/api/reports/headcount` | Level 2+ | Headcount by department/gender/status |
| `GET` | `/api/reports/department/{id}` | Level 2+ | Department deep-dive report |
| `POST` | `/api/reports/generate` | Level 3+ | Generate AI-written narrative report |
| `GET` | `/api/reports/history` | Level 2+ | Report generation history |
| `GET` | `/api/reports/history/{id}` | Level 2+ | Get specific saved report |

---

### Notifications — `/api/notifications`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/notifications` | Any | List own notifications |
| `GET` | `/api/notifications/unread-count` | Any | Badge count of unread notifications |
| `PATCH` | `/api/notifications/{id}/read` | Any | Mark single notification as read |
| `PATCH` | `/api/notifications/read-all` | Any | Mark all as read |
| `DELETE` | `/api/notifications/{id}` | Any | Delete single notification |
| `DELETE` | `/api/notifications/clear-all` | Any | Clear all read notifications |
| `POST` | `/api/notifications/send` | Level 2+ | Send to specific employees |
| `POST` | `/api/notifications/broadcast` | Level 3+ | Broadcast to all / department |
| `WS` | `/api/notifications/ws?token=JWT` | Any | Real-time WebSocket stream |

---

### Performance Reviews — `/api/performance`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/performance/generate/{emp_id}` | Level 3+ | AI-generate a performance review |
| `GET` | `/api/performance/my-reviews` | Any | Get own performance history |
| `GET` | `/api/performance/my-summary` | Any | Quick summary with latest score |
| `GET` | `/api/performance/review/{id}` | Level 1+ | Get specific review |
| `GET` | `/api/performance/employee/{id}` | Level 2+ | All reviews for employee |
| `GET` | `/api/performance/all` | Level 3+ | All reviews (filterable) |
| `GET` | `/api/performance/team` | Level 3+ | Team overview with top/bottom performers |
| `PATCH` | `/api/performance/review/{id}/acknowledge` | Any | Employee acknowledges review |
| `PATCH` | `/api/performance/review/{id}/comments` | Level 3+ | HR adds manager comments |
| `POST` | `/api/performance/review/{id}/dispute` | Any | Employee disputes review |
| `PATCH` | `/api/performance/review/{id}/resolve` | Level 3+ | HR resolves dispute |

---

### Departments — `/api/departments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/departments` | Level 2+ | List all departments |
| `GET` | `/api/departments/{id}` | Level 2+ | Get department by ID |
| `POST` | `/api/departments` | Level 3+ | Create department |
| `PUT` | `/api/departments/{id}` | Level 3+ | Update department |
| `DELETE` | `/api/departments/{id}` | Level 4 | Delete department |

---

### Roles — `/api/roles`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/roles` | Level 2+ | List all roles |
| `GET` | `/api/roles/{id}` | Level 2+ | Get role by ID |
| `POST` | `/api/roles` | Level 4 | Create role |
| `PUT` | `/api/roles/{id}` | Level 4 | Update role |
| `DELETE` | `/api/roles/{id}` | Level 4 | Delete role |

---

*End of Appendix G — API Documentation*
