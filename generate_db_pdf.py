from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame
from reportlab.lib.colors import HexColor
import os

OUTPUT_PATH = "d:/HR/HR_Database_Structure.pdf"

# ── Color palette ────────────────────────────────────────────────────────────
C_HEADER_BG   = HexColor("#1E3A5F")   # dark navy
C_HEADER_FG   = colors.white
C_SUBHDR_BG   = HexColor("#2E6DA4")   # mid-blue
C_ROW_ALT     = HexColor("#EBF3FB")   # very light blue
C_ROW_NORMAL  = colors.white
C_PK          = HexColor("#F0F8E8")   # light green for PK rows
C_FK          = HexColor("#FFF8E1")   # light yellow for FK rows
C_BORDER      = HexColor("#AECDE8")
C_TITLE_BG    = HexColor("#0D2B4E")
C_SECTION_BG  = HexColor("#F0F4F8")

# ── Page setup ───────────────────────────────────────────────────────────────
PAGE = landscape(A4)
L_MARGIN = R_MARGIN = 15 * mm
T_MARGIN = 20 * mm
B_MARGIN = 20 * mm

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=PAGE,
    leftMargin=L_MARGIN, rightMargin=R_MARGIN,
    topMargin=T_MARGIN, bottomMargin=B_MARGIN,
    title="HR System – Database Structure",
    author="HR System"
)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    "DocTitle", parent=styles["Title"],
    fontSize=28, textColor=colors.white,
    spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"
)
subtitle_style = ParagraphStyle(
    "DocSub", parent=styles["Normal"],
    fontSize=13, textColor=HexColor("#AECDE8"),
    spaceAfter=4, alignment=TA_CENTER
)
table_name_style = ParagraphStyle(
    "TableName", parent=styles["Heading2"],
    fontSize=14, textColor=C_HEADER_BG,
    spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold"
)
section_style = ParagraphStyle(
    "Section", parent=styles["Heading1"],
    fontSize=16, textColor=C_TITLE_BG,
    spaceBefore=18, spaceAfter=6, fontName="Helvetica-Bold",
    borderPad=4
)
note_style = ParagraphStyle(
    "Note", parent=styles["Normal"],
    fontSize=8, textColor=HexColor("#555555"),
    spaceAfter=2, leading=10
)
cell_style = ParagraphStyle(
    "Cell", parent=styles["Normal"],
    fontSize=8, leading=10
)

# ── Helper ───────────────────────────────────────────────────────────────────
def make_cell(text, bold=False, color=None):
    style = ParagraphStyle(
        "c", parent=cell_style,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        textColor=color or colors.black
    )
    return Paragraph(str(text), style)

def build_table(headers, rows, col_widths):
    """
    headers: list of str
    rows: list of lists (each cell: str or tuple (str, options))
    """
    # Build header row
    h_cells = [
        Paragraph(h, ParagraphStyle("H", fontName="Helvetica-Bold",
                                     fontSize=8, textColor=C_HEADER_FG,
                                     leading=10))
        for h in headers
    ]
    table_data = [h_cells]

    for i, row in enumerate(rows):
        cells = []
        for cell in row:
            if isinstance(cell, tuple):
                text, opts = cell
                bold = opts.get("bold", False)
                clr  = opts.get("color", colors.black)
            else:
                text, bold, clr = cell, False, colors.black
            cells.append(Paragraph(str(text),
                ParagraphStyle("c", parent=cell_style,
                               fontName="Helvetica-Bold" if bold else "Helvetica",
                               textColor=clr, fontSize=8, leading=10)))
        table_data.append(cells)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Base style
    style_cmds = [
        # Header
        ("BACKGROUND",  (0,0), (-1,0), C_HEADER_BG),
        ("TEXTCOLOR",   (0,0), (-1,0), C_HEADER_FG),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 8),
        ("ROWBACKGROUND",(0,1), (-1,-1), [C_ROW_NORMAL, C_ROW_ALT]),
        ("GRID",        (0,0), (-1,-1), 0.4, C_BORDER),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0), (-1,-1), 4),
        ("LINEBELOW",   (0,0), (-1,0), 1.5, HexColor("#0D2B4E")),
    ]
    # Highlight PK rows (row index 1-based)
    for i, row in enumerate(rows, start=1):
        constraints = str(row[3]) if len(row) > 3 else ""
        if "PRIMARY KEY" in constraints:
            style_cmds.append(("BACKGROUND", (0,i), (-1,i), C_PK))
        elif "FOREIGN KEY" in constraints:
            style_cmds.append(("BACKGROUND", (0,i), (-1,i), C_FK))

    t.setStyle(TableStyle(style_cmds))
    return t


# ── Database definitions ─────────────────────────────────────────────────────
HEADERS = ["Field / Column", "Data Type", "Nullable", "Constraints / Notes"]

# widths (landscape A4 usable ≈ 267 mm)
W = [doc.width * f for f in [0.22, 0.17, 0.09, 0.52]]

DB = [
    # ── 1. EMPLOYEE ───────────────────────────────────────────────────────
    {
        "section": "Core HR",
        "name": "Employee",
        "table": "employees",
        "desc": "Central employee record. Every other table relates back to this one.",
        "rows": [
            ("id",               "Integer",          "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_number",  "String(20)",        "NOT NULL", "UNIQUE, indexed — company ID (e.g. EMP001)"),
            ("first_name",       "String(100)",       "NOT NULL", ""),
            ("last_name",        "String(100)",       "NOT NULL", ""),
            ("full_name",        "String(200)",       "NOT NULL", "Stored for quick display"),
            ("nic_number",       "String(20)",        "nullable", "UNIQUE — Sri Lanka National ID"),
            ("date_of_birth",    "Date",              "nullable", ""),
            ("gender",           "Enum",              "nullable", "Values: MALE, FEMALE, OTHER"),
            ("personal_email",   "String(200)",       "NOT NULL", "UNIQUE"),
            ("work_email",       "String(200)",       "nullable", "UNIQUE"),
            ("phone_number",     "String(100)",       "nullable", ""),
            ("address",          "Text",              "nullable", ""),
            ("city",             "String(100)",       "nullable", ""),
            ("district",         "String(100)",       "nullable", "Sri Lanka district"),
            ("hashed_password",  "String(255)",       "NOT NULL", "Bcrypt hash for authentication"),
            ("is_active",        "Boolean",           "NOT NULL", "Default: True"),
            ("last_login",       "DateTime",          "nullable", ""),
            ("department_id",    "Integer",           "nullable", "FOREIGN KEY → departments.id"),
            ("role_id",          "Integer",           "nullable", "FOREIGN KEY → roles.id"),
            ("manager_id",       "Integer",           "nullable", "FOREIGN KEY → employees.id (self-reference)"),
            ("hire_date",        "Date",              "nullable", ""),
            ("probation_end",    "Date",              "nullable", ""),
            ("termination_date", "Date",              "nullable", ""),
            ("employment_type",  "String(50)",        "NOT NULL", "Default: full_time  |  full_time / part_time / contract / intern"),
            ("status",           "Enum",              "NOT NULL", "Default: PROBATION  |  ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, PROBATION"),
            ("base_salary",      "Numeric(12,2)",     "nullable", "Monthly salary in LKR"),
            ("bank_account",     "String(50)",        "nullable", ""),
            ("bank_name",        "String(100)",       "nullable", ""),
            ("face_embedding",   "JSON",              "nullable", "DeepFace vector array (not the photo itself)"),
            ("face_registered",  "Boolean",           "NOT NULL", "Default: False"),
            ("face_registered_at","Text",             "nullable", "ISO datetime string"),
            ("language_pref",    "String(5)",         "NOT NULL", "Default: en  |  en / si / ta"),
            ("profile_photo",    "String(500)",       "nullable", "Path to profile image"),
            ("created_at",       "DateTime",          "NOT NULL", "Server default: now()"),
            ("updated_at",       "DateTime",          "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 2. DEPARTMENT ─────────────────────────────────────────────────────
    {
        "section": "Core HR",
        "name": "Department",
        "table": "departments",
        "desc": "Organisational units (Engineering, HR, Finance, …).",
        "rows": [
            ("id",          "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("name",        "String(100)","NOT NULL", "UNIQUE — e.g. Engineering"),
            ("code",        "String(20)", "NOT NULL", "UNIQUE — e.g. ENG"),
            ("description", "Text",       "nullable", ""),
            ("is_active",   "Boolean",    "NOT NULL", "Default: True"),
            ("created_at",  "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",  "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 3. ROLE ───────────────────────────────────────────────────────────
    {
        "section": "Core HR",
        "name": "Role",
        "table": "roles",
        "desc": "Job roles with access levels. access_level: 1=Employee, 2=HR Staff, 3=HR Manager, 4=Admin.",
        "rows": [
            ("id",           "Integer",      "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("title",        "String(100)",  "NOT NULL", "UNIQUE — e.g. Software Engineer"),
            ("code",         "String(30)",   "NOT NULL", "UNIQUE — e.g. SWE"),
            ("description",  "Text",         "nullable", ""),
            ("access_level", "Integer",      "NOT NULL", "Default: 1  |  1=Employee … 4=Admin"),
            ("base_salary",  "Numeric(12,2)","nullable", "Base salary in LKR"),
            ("is_active",    "Boolean",      "NOT NULL", "Default: True"),
            ("created_at",   "DateTime",     "NOT NULL", "Server default: now()"),
            ("updated_at",   "DateTime",     "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 4. ATTENDANCE ─────────────────────────────────────────────────────
    {
        "section": "Attendance",
        "name": "Attendance",
        "table": "attendance",
        "desc": "Daily attendance record per employee. Includes face-recognition confidence, GPS, and overtime data.",
        "rows": [
            ("id",                  "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",         "Integer",    "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("work_date",           "Date",       "NOT NULL", "Indexed — the calendar date"),
            ("clock_in",            "DateTime(tz)","nullable","Timezone-aware check-in timestamp"),
            ("clock_out",           "DateTime(tz)","nullable","Timezone-aware check-out timestamp"),
            ("work_hours",          "Float",      "nullable", "Calculated hours worked (e.g. 8.5)"),
            ("confidence_score",    "Float",      "nullable", "DeepFace confidence 0.0–1.0"),
            ("verification_method", "Enum",       "NOT NULL", "Default: FACE_RECOGNITION  |  FACE_RECOGNITION, MANUAL_OVERRIDE, RFID"),
            ("is_verified",         "Boolean",    "NOT NULL", "Default: False"),
            ("attendance_type",     "Enum",       "NOT NULL", "Default: REGULAR  |  REGULAR, OVERTIME, HALF_DAY, HOLIDAY"),
            ("is_late",             "Boolean",    "NOT NULL", "Default: False"),
            ("late_minutes",        "Integer",    "NOT NULL", "Default: 0"),
            ("is_early_departure",  "Boolean",    "NOT NULL", "Default: False"),
            ("overtime_hours",      "Float",      "NOT NULL", "Default: 0.0"),
            ("location",            "String(200)","nullable", "e.g. Head Office, Remote"),
            ("latitude",            "Float",      "nullable", "GPS latitude at clock-in"),
            ("longitude",           "Float",      "nullable", "GPS longitude at clock-in"),
            ("checkout_latitude",   "Float",      "nullable", "GPS latitude at clock-out"),
            ("checkout_longitude",  "Float",      "nullable", "GPS longitude at clock-out"),
            ("is_absent",           "Boolean",    "NOT NULL", "Default: False — no clock-in recorded"),
            ("absence_reason",      "Text",       "nullable", ""),
            ("notes",               "Text",       "nullable", "HR notes"),
            ("flagged",             "Boolean",    "NOT NULL", "Default: False — suspicious activity"),
            ("flag_reason",         "Text",       "nullable", "e.g. Low confidence score"),
            ("clock_in_photo",      "String(500)","nullable", "Path to saved snapshot"),
            ("clock_out_photo",     "String(500)","nullable", "Path to saved snapshot"),
            ("created_at",          "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",          "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 5. ATTENDANCE_SCAN ────────────────────────────────────────────────
    {
        "section": "Attendance",
        "name": "AttendanceScan",
        "table": "attendance_scans",
        "desc": "Individual scan events linked to an attendance record (supports multiple scans per day).",
        "rows": [
            ("id",            "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("attendance_id", "Integer",    "NOT NULL", "FOREIGN KEY → attendance.id, indexed"),
            ("employee_id",   "Integer",    "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("scan_type",     "String(20)", "NOT NULL", "clock_in or clock_out"),
            ("scanned_at",    "DateTime(tz)","NOT NULL","Exact scan timestamp (timezone-aware)"),
            ("confidence",    "Float",      "nullable", "Face recognition confidence"),
            ("photo_path",    "String(500)","nullable", "Path to saved snapshot"),
            ("created_at",    "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",    "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 6. LEAVE_TYPE ─────────────────────────────────────────────────────
    {
        "section": "Leave Management",
        "name": "LeaveType",
        "table": "leave_types",
        "desc": "Catalogue of leave categories with eligibility rules.",
        "rows": [
            ("id",                    "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("name",                  "String(100)","NOT NULL", "UNIQUE — e.g. Annual Leave, Sick Leave"),
            ("code",                  "String(20)", "NOT NULL", "UNIQUE — e.g. AL, SL, ML"),
            ("description",           "Text",       "nullable", ""),
            ("max_days_per_year",     "Integer",    "NOT NULL", "Total days allowed per year"),
            ("max_consecutive_days",  "Integer",    "nullable", "Max days in one request"),
            ("requires_document",     "Boolean",    "NOT NULL", "Default: False — e.g. medical cert required"),
            ("is_paid",               "Boolean",    "NOT NULL", "Default: True"),
            ("gender_specific",       "String(10)", "nullable", "female for maternity, NULL for all"),
            ("is_active",             "Boolean",    "NOT NULL", "Default: True"),
            ("created_at",            "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",            "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 7. LEAVE_BALANCE ──────────────────────────────────────────────────
    {
        "section": "Leave Management",
        "name": "LeaveBalance",
        "table": "leave_balances",
        "desc": "Per-employee, per-leave-type annual balance tracker.",
        "rows": [
            ("id",             "Integer",       "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",    "Integer",       "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("leave_type_id",  "Integer",       "NOT NULL", "FOREIGN KEY → leave_types.id"),
            ("year",           "Integer",       "NOT NULL", "e.g. 2025, 2026"),
            ("total_days",     "Float",         "NOT NULL", "Days allocated this year"),
            ("used_days",      "Float",         "NOT NULL", "Default: 0.0 — days already taken"),
            ("pending_days",   "Float",         "NOT NULL", "Default: 0.0 — days in pending requests"),
            ("remaining_days", "Float",         "NOT NULL", "total_days - used_days - pending_days"),
            ("carried_over",   "Float",         "NOT NULL", "Default: 0.0 — carried from previous year"),
            ("created_at",     "DateTime",      "NOT NULL", "Server default: now()"),
            ("updated_at",     "DateTime",      "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 8. LEAVE_REQUEST ──────────────────────────────────────────────────
    {
        "section": "Leave Management",
        "name": "LeaveRequest",
        "table": "leave_requests",
        "desc": "Employee leave applications with AI decision tracking and HR override capability.",
        "rows": [
            ("id",                "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",       "Integer",    "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("leave_type_id",     "Integer",    "NOT NULL", "FOREIGN KEY → leave_types.id"),
            ("start_date",        "Date",       "NOT NULL", ""),
            ("end_date",          "Date",       "NOT NULL", ""),
            ("total_days",        "Float",      "NOT NULL", "Working days between start and end"),
            ("days_requested",    "Float",      "nullable", "Alias for total_days"),
            ("reason",            "Text",       "NOT NULL", "Employee's stated reason"),
            ("is_half_day",       "Boolean",    "NOT NULL", "Default: False"),
            ("status",            "Enum",       "NOT NULL", "Default: PENDING, indexed  |  PENDING, APPROVED, REJECTED, ESCALATED, CANCELLED, ON_LEAVE, COMPLETED"),
            ("ai_decision",       "String(20)", "nullable", "approved or rejected"),
            ("ai_decision_reason","Text",       "nullable", "LLM explanation"),
            ("ai_confidence",     "Float",      "nullable", "AI confidence 0.0–1.0"),
            ("ai_policy_refs",    "JSON",       "nullable", "Policy chunks used: [Section 4.2, ...]"),
            ("ai_processed_at",   "Text",       "nullable", "ISO datetime when AI processed"),
            ("rejection_reason",  "Text",       "nullable", "Reason for rejection"),
            ("approved_by",       "String(200)","nullable", "AI Agent or HR employee name"),
            ("approved_at",       "DateTime",   "nullable", "When approved / rejected"),
            ("reviewed_by_id",    "Integer",    "nullable", "FOREIGN KEY → employees.id (HR reviewer)"),
            ("hr_override",       "Boolean",    "NOT NULL", "Default: False — HR overrode AI decision"),
            ("hr_notes",          "Text",       "nullable", ""),
            ("reviewed_at",       "Text",       "nullable", "ISO datetime"),
            ("document_url",      "String(500)","nullable", "S3 URL of supporting document"),
            ("document_verified", "Boolean",    "NOT NULL", "Default: False"),
            ("is_appealed",       "Boolean",    "NOT NULL", "Default: False"),
            ("appeal_reason",     "Text",       "nullable", ""),
            ("appeal_status",     "String(20)", "nullable", "pending, upheld, or overturned"),
            ("created_at",        "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",        "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 9. PERFORMANCE_REVIEW ─────────────────────────────────────────────
    {
        "section": "Performance",
        "name": "PerformanceReview",
        "table": "performance_reviews",
        "desc": "Period-based employee performance evaluations (attendance, punctuality, OT). Supports AI summaries.",
        "rows": [
            ("id",                    "Integer", "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",           "Integer", "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("reviewer_id",           "Integer", "nullable", "FOREIGN KEY → employees.id (null if AI-generated)"),
            ("period_type",           "Enum",    "NOT NULL", "MONTHLY, QUARTERLY, ANNUAL, PROBATION"),
            ("period_start",          "Date",    "NOT NULL", ""),
            ("period_end",            "Date",    "NOT NULL", ""),
            ("attendance_score",      "Float",   "nullable", "(present_days / working_days) × 100"),
            ("punctuality_score",     "Float",   "nullable", "100 − (late_days / present_days × 100)"),
            ("overtime_score",        "Float",   "nullable", "Based on voluntary overtime"),
            ("overall_score",         "Float",   "nullable", "Weighted average — used by AI"),
            ("rating",                "String(50)","nullable","Excellent, Good, Satisfactory, Needs Improvement"),
            ("strengths",             "Text",    "nullable", ""),
            ("areas_to_improve",      "Text",    "nullable", ""),
            ("goals_next_period",     "Text",    "nullable", ""),
            ("manager_comments",      "Text",    "nullable", ""),
            ("ai_summary",            "Text",    "nullable", "AI-generated narrative"),
            ("status",                "Enum",    "NOT NULL", "Default: DRAFT  |  DRAFT, PENDING, COMPLETED, DISPUTED"),
            ("is_promotion_eligible", "Boolean", "NOT NULL", "Default: False"),
            ("requires_pip",          "Boolean", "NOT NULL", "Default: False — Performance Improvement Plan"),
            ("employee_acknowledged", "Boolean", "NOT NULL", "Default: False"),
            ("created_at",            "DateTime","NOT NULL", "Server default: now()"),
            ("updated_at",            "DateTime","NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 10. PERFORMANCE_METRIC ────────────────────────────────────────────
    {
        "section": "Performance",
        "name": "PerformanceMetric",
        "table": "performance_metrics",
        "desc": "Granular metric values attached to a PerformanceReview.",
        "rows": [
            ("id",          "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("review_id",   "Integer",    "NOT NULL", "FOREIGN KEY → performance_reviews.id, indexed"),
            ("metric_name", "String(200)","NOT NULL", "e.g. Days Present, Times Late"),
            ("value",       "Float",      "NOT NULL", "Raw number"),
            ("score",       "Float",      "nullable", "0–100 score derived from value"),
            ("weight",      "Float",      "NOT NULL", "Default: 1.0 — contribution to overall_score"),
            ("note",        "Text",       "nullable", ""),
        ],
    },
    # ── 11. JOB_POSTING ───────────────────────────────────────────────────
    {
        "section": "Recruitment",
        "name": "JobPosting",
        "table": "job_postings",
        "desc": "Open job positions published by HR. Includes AI interview questions for the screening pipeline.",
        "rows": [
            ("id",                    "Integer",       "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("title",                 "String(200)",   "NOT NULL", "Job title"),
            ("department_id",         "Integer",       "nullable", "FOREIGN KEY → departments.id"),
            ("description",           "Text",          "NOT NULL", "Full job description"),
            ("requirements",          "Text",          "NOT NULL", "Skills, experience, qualifications"),
            ("responsibilities",      "Text",          "nullable", ""),
            ("salary_min",            "Numeric(12,2)", "nullable", ""),
            ("salary_max",            "Numeric(12,2)", "nullable", ""),
            ("employment_type",       "String(50)",    "NOT NULL", "Default: full_time"),
            ("location",              "String(200)",   "nullable", ""),
            ("positions_count",       "Integer",       "NOT NULL", "Default: 1 — number of openings"),
            ("closing_date",          "Date",          "nullable", ""),
            ("is_active",             "Boolean",       "NOT NULL", "Default: True"),
            ("posted_by_id",          "Integer",       "nullable", "FOREIGN KEY → employees.id"),
            ("ai_interview_questions","JSON",           "nullable", "Questions for AI to ask candidates"),
            ("culture_keywords",      "JSON",           "nullable", "Keywords for RAG culture-fit matching"),
            ("created_at",            "DateTime",      "NOT NULL", "Server default: now()"),
            ("updated_at",            "DateTime",      "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 12. JOB_APPLICATION ───────────────────────────────────────────────
    {
        "section": "Recruitment",
        "name": "JobApplication",
        "table": "job_applications",
        "desc": "Candidate applications with AI screening scores (resume match, interview, culture fit).",
        "rows": [
            ("id",                  "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("job_posting_id",      "Integer",    "NOT NULL", "FOREIGN KEY → job_postings.id, indexed"),
            ("applicant_id",        "Integer",    "nullable", "FOREIGN KEY → employees.id (internal applicants)"),
            ("applicant_name",      "String(200)","nullable", "External applicant name"),
            ("applicant_email",     "String(200)","nullable", ""),
            ("applicant_phone",     "String(20)", "nullable", ""),
            ("resume_url",          "String(500)","nullable", "S3 URL of resume"),
            ("cover_letter",        "Text",       "nullable", ""),
            ("status",              "Enum",       "NOT NULL", "Default: APPLIED  |  APPLIED, SCREENING, AI_INTERVIEW, SHORTLISTED, HR_INTERVIEW, OFFERED, ACCEPTED, REJECTED, WITHDRAWN"),
            ("ai_resume_score",     "Float",      "nullable", "0–100 resume match score"),
            ("ai_interview_score",  "Float",      "nullable", "0–100 from AI interview"),
            ("ai_culture_fit",      "Float",      "nullable", "0–100 culture match"),
            ("ai_overall_score",    "Float",      "nullable", "Weighted average of AI scores"),
            ("ai_recommendation",   "String(50)", "nullable", "shortlist, reject, or hold"),
            ("ai_feedback",         "Text",       "nullable", "Detailed AI feedback"),
            ("interview_transcript","JSON",        "nullable", "Q&A list: [{q, a, score}, …]"),
            ("hr_notes",            "Text",       "nullable", ""),
            ("reviewed_by_id",      "Integer",    "nullable", "FOREIGN KEY → employees.id (HR reviewer)"),
            ("hr_score",            "Float",      "nullable", ""),
            ("created_at",          "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",          "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 13. NOTIFICATION ──────────────────────────────────────────────────
    {
        "section": "Communication",
        "name": "Notification",
        "table": "notifications",
        "desc": "In-app and email notifications with read-state tracking.",
        "rows": [
            ("id",                  "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",         "Integer",    "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("notification_type",   "String(50)", "NOT NULL", "Indexed — e.g. leave_approved, payslip_ready"),
            ("title",               "String(300)","NOT NULL", "Short heading"),
            ("message",             "Text",       "NOT NULL", "Full message body"),
            ("action_url",          "String(500)","nullable", "Deep link e.g. /leave/request/42"),
            ("channel",             "Enum",       "NOT NULL", "Default: BOTH  |  IN_APP, EMAIL, BOTH"),
            ("is_read",             "Boolean",    "NOT NULL", "Default: False"),
            ("read_at",             "Text",       "nullable", "ISO datetime"),
            ("email_sent",          "Boolean",    "NOT NULL", "Default: False"),
            ("email_sent_at",       "Text",       "nullable", "ISO datetime"),
            ("related_entity_type", "String(50)", "nullable", "leave_request, payroll, etc."),
            ("related_entity_id",   "Integer",    "nullable", "ID of related record"),
            ("priority",            "String(20)", "NOT NULL", "Default: normal  |  low, normal, high, urgent"),
            ("extra_data",          "JSON",       "nullable", "Additional structured data"),
            ("created_at",          "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",          "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 14. CHAT_SESSION ──────────────────────────────────────────────────
    {
        "section": "Communication",
        "name": "ChatSession",
        "table": "chat_sessions",
        "desc": "AI chat conversations. Title is auto-set from the first message.",
        "rows": [
            ("id",          "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id", "Integer",    "NOT NULL", "FOREIGN KEY → employees.id, indexed"),
            ("title",       "String(200)","nullable", "Auto-set from first message"),
            ("is_active",   "Boolean",    "NOT NULL", "Default: True"),
            ("created_at",  "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",  "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 15. CHAT_MESSAGE ──────────────────────────────────────────────────
    {
        "section": "Communication",
        "name": "ChatMessage",
        "table": "chat_messages",
        "desc": "Individual messages within a ChatSession.",
        "rows": [
            ("id",         "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("session_id", "Integer",    "NOT NULL", "FOREIGN KEY → chat_sessions.id, indexed"),
            ("role",       "String(20)", "NOT NULL", "user or assistant"),
            ("content",    "Text",       "NOT NULL", "Message text"),
            ("sources",    "Text",       "nullable", "JSON list of policy sources used by AI"),
            ("created_at", "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at", "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 16. AUDIT_LOG ─────────────────────────────────────────────────────
    {
        "section": "Governance",
        "name": "AuditLog",
        "table": "audit_logs",
        "desc": "Immutable log of every action taken by employees, HR, admins, and AI agents.",
        "rows": [
            ("id",            "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("employee_id",   "Integer",    "nullable", "FOREIGN KEY → employees.id, indexed (null for system/AI)"),
            ("actor_type",    "String(20)", "NOT NULL", "employee, hr_manager, admin, ai_agent, system"),
            ("ip_address",    "String(50)", "nullable", ""),
            ("action",        "String(100)","NOT NULL", "Indexed — dot notation e.g. leave.approved, employee.login"),
            ("description",   "Text",       "nullable", "Human-readable e.g. AI approved leave #42 for John"),
            ("entity_type",   "String(50)", "nullable", "leave_request, employee, payroll, etc."),
            ("entity_id",     "Integer",    "nullable", "ID of affected record"),
            ("before_state",  "JSON",       "nullable", "State BEFORE action (for undo)"),
            ("after_state",   "JSON",       "nullable", "State AFTER action"),
            ("metadata",      "JSON",       "nullable", "Extra info: AI reasoning, policy refs, etc."),
            ("status",        "String(20)", "NOT NULL", "Default: success  |  success, failed, blocked"),
            ("error_message", "Text",       "nullable", ""),
            ("created_at",    "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",    "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 17. HR_POLICY ─────────────────────────────────────────────────────
    {
        "section": "Governance",
        "name": "HRPolicy",
        "table": "hr_policies",
        "desc": "Policy documents stored in PostgreSQL and chunked into ChromaDB for RAG retrieval.",
        "rows": [
            ("id",             "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("title",          "String(300)","NOT NULL", "e.g. Annual Leave Policy 2025"),
            ("category",       "Enum",       "NOT NULL", "Indexed  |  LEAVE, ATTENDANCE, PAYROLL, CONDUCT, RECRUITMENT, PERFORMANCE, GENERAL"),
            ("content",        "Text",       "NOT NULL", "Full policy text (chunked for ChromaDB)"),
            ("version",        "String(20)", "nullable", "e.g. v2.1"),
            ("effective_date", "String(20)", "nullable", "ISO date e.g. 2025-01-01"),
            ("expiry_date",    "String(20)", "nullable", "ISO date"),
            ("chroma_doc_id",  "String(200)","nullable", "UNIQUE — links PostgreSQL row to ChromaDB document"),
            ("is_indexed",     "Boolean",    "NOT NULL", "Default: False — already in ChromaDB"),
            ("indexed_at",     "Text",       "nullable", "ISO datetime"),
            ("chunk_count",    "Integer",    "nullable", "Number of chunks created in ChromaDB"),
            ("is_active",      "Boolean",    "NOT NULL", "Default: True"),
            ("uploaded_by_id", "Integer",    "nullable", "Employee ID of uploader"),
            ("tags",           "JSON",       "nullable", "Filter keywords e.g. [annual, leave, eligibility]"),
            ("language",       "String(5)",  "NOT NULL", "Default: en  |  en, si, ta"),
            ("created_at",     "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",     "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
    # ── 18. HR_REPORT ─────────────────────────────────────────────────────
    {
        "section": "Governance",
        "name": "HRReport",
        "table": "hr_reports",
        "desc": "Generated analytics reports (monthly, quarterly, annual) with AI executive summaries.",
        "rows": [
            ("id",           "Integer",    "NOT NULL", "PRIMARY KEY, auto-increment"),
            ("report_type",  "String(100)","NOT NULL", "Indexed — monthly_summary, attendance, leave, performance, department"),
            ("period",       "String(50)", "nullable", "e.g. 2026-03, 2026-Q1, 2026"),
            ("title",        "String(300)","NOT NULL", ""),
            ("content",      "JSON",       "NOT NULL", "Default: {}  — structured KPIs and data"),
            ("narrative",    "Text",       "nullable", "AI-generated executive summary"),
            ("generated_by", "String(200)","NOT NULL", "Default: system  |  AI Agent or employee name"),
            ("created_at",   "DateTime",   "NOT NULL", "Server default: now()"),
            ("updated_at",   "DateTime",   "NOT NULL", "Server default: now(), onupdate: now()"),
        ],
    },
]

# ── Build story ───────────────────────────────────────────────────────────────
story = []

# ── Cover page ──────────────────────────────────────────────────────────────
cover_data = [["HR System — Database Structure"]]
cover_table = Table(cover_data, colWidths=[doc.width])
cover_table.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), C_TITLE_BG),
    ("TEXTCOLOR",    (0,0), (-1,-1), colors.white),
    ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 26),
    ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ("TOPPADDING",   (0,0), (-1,-1), 18),
    ("BOTTOMPADDING",(0,0), (-1,-1), 18),
]))
story.append(cover_table)
story.append(Spacer(1, 6*mm))

# Subtitle row
sub_data = [["18 Tables  ·  SQLAlchemy ORM  ·  PostgreSQL Backend  ·  Generated 2026-04-11"]]
sub_table = Table(sub_data, colWidths=[doc.width])
sub_table.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), HexColor("#162840")),
    ("TEXTCOLOR",    (0,0), (-1,-1), HexColor("#AECDE8")),
    ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
    ("FONTSIZE",     (0,0), (-1,-1), 10),
    ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ("TOPPADDING",   (0,0), (-1,-1), 6),
    ("BOTTOMPADDING",(0,0), (-1,-1), 6),
]))
story.append(sub_table)
story.append(Spacer(1, 8*mm))

# ── Legend ───────────────────────────────────────────────────────────────────
legend_data = [
    [
        Paragraph("<font color='#2E7D32'>■</font> Primary Key row", cell_style),
        Paragraph("<font color='#F57F17'>■</font> Foreign Key row", cell_style),
        Paragraph("All tables include  created_at  and  updated_at  timestamp columns (server default: now())", cell_style),
    ]
]
legend_t = Table(legend_data, colWidths=[doc.width*0.22, doc.width*0.22, doc.width*0.56])
legend_t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), C_SECTION_BG),
    ("GRID",         (0,0), (-1,-1), 0.3, C_BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 4),
    ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
]))
story.append(legend_t)
story.append(Spacer(1, 6*mm))

# ── TOC ──────────────────────────────────────────────────────────────────────
toc_rows = []
for i, db in enumerate(DB, 1):
    toc_rows.append([
        Paragraph(f"{i}.", cell_style),
        Paragraph(f"<b>{db['name']}</b>", cell_style),
        Paragraph(db["table"], ParagraphStyle("mono", parent=cell_style,
                                               fontName="Courier", fontSize=8)),
        Paragraph(db["section"], cell_style),
    ])

toc_header = [
    Paragraph("#", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8,
                                   textColor=C_HEADER_FG, leading=10)),
    Paragraph("Model", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8,
                                       textColor=C_HEADER_FG, leading=10)),
    Paragraph("Table Name", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8,
                                            textColor=C_HEADER_FG, leading=10)),
    Paragraph("Section", ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8,
                                         textColor=C_HEADER_FG, leading=10)),
]
toc_data = [toc_header] + toc_rows
toc_t = Table(toc_data, colWidths=[doc.width*0.05, doc.width*0.22,
                                    doc.width*0.30, doc.width*0.43],
              repeatRows=1)
toc_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), C_HEADER_BG),
    ("TEXTCOLOR",     (0,0), (-1,0), C_HEADER_FG),
    ("ROWBACKGROUND", (0,1), (-1,-1), [C_ROW_NORMAL, C_ROW_ALT]),
    ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING",    (0,0), (-1,-1), 3),
    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ("LINEBELOW",     (0,0), (-1,0), 1.5, HexColor("#0D2B4E")),
]))

toc_title = Paragraph("Table of Contents", ParagraphStyle(
    "TOC", parent=styles["Heading2"], fontSize=13, textColor=C_TITLE_BG,
    spaceAfter=5, fontName="Helvetica-Bold"))
story.append(KeepTogether([toc_title, toc_t]))

# ── Render each table ─────────────────────────────────────────────────────────
current_section = None
for i, db in enumerate(DB):
    story.append(PageBreak())

    # Section banner
    if db["section"] != current_section:
        current_section = db["section"]
        sec_data = [[db["section"]]]
        sec_t = Table(sec_data, colWidths=[doc.width])
        sec_t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), C_SUBHDR_BG),
            ("TEXTCOLOR",    (0,0), (-1,-1), colors.white),
            ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 13),
            ("ALIGN",        (0,0), (-1,-1), "LEFT"),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ]))
        story.append(sec_t)
        story.append(Spacer(1, 4*mm))

    # Table header card
    hdr_data = [[
        Paragraph(f"<b>{i+1}. {db['name']}</b>", ParagraphStyle(
            "TH", fontName="Helvetica-Bold", fontSize=13,
            textColor=C_HEADER_BG, leading=15)),
        Paragraph(f"Table: <font name='Courier'>{db['table']}</font>",
                  ParagraphStyle("TDB", fontName="Helvetica", fontSize=9,
                                 textColor=HexColor("#555"), leading=12)),
    ]]
    hdr_t = Table(hdr_data, colWidths=[doc.width*0.55, doc.width*0.45])
    hdr_t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), C_SECTION_BG),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("LINEBELOW",    (0,0), (-1,-1), 1, C_SUBHDR_BG),
    ]))
    story.append(hdr_t)

    # Description
    story.append(Paragraph(db["desc"], ParagraphStyle(
        "Desc", parent=styles["Normal"], fontSize=8,
        textColor=HexColor("#444"), spaceBefore=3, spaceAfter=5,
        leftIndent=8, fontName="Helvetica-Oblique")))

    # Data table
    story.append(build_table(HEADERS, db["rows"], W))
    story.append(Spacer(1, 3*mm))

# ── Build PDF ─────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF generated: {OUTPUT_PATH}")
