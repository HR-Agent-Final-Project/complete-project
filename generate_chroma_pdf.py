from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor

OUTPUT_PATH = "d:/HR/HR_ChromaDB_Structure.pdf"

# ── Color palette ────────────────────────────────────────────────────────────
C_NAV        = HexColor("#1A237E")   # deep navy  (ChromaDB brand-ish)
C_MID        = HexColor("#283593")
C_ACCENT     = HexColor("#3949AB")
C_LIGHT      = HexColor("#E8EAF6")   # light indigo
C_ROW_ALT    = HexColor("#F3F4FF")
C_ROW_NORM   = colors.white
C_BORDER     = HexColor("#9FA8DA")
C_CODE_BG    = HexColor("#F5F5F5")
C_GOLD       = HexColor("#FFD600")
C_TEAL       = HexColor("#00897B")
C_TEAL_LT    = HexColor("#E0F2F1")
C_ORANGE     = HexColor("#E65100")
C_ORANGE_LT  = HexColor("#FFF3E0")
C_PURPLE     = HexColor("#6A1B9A")
C_PURPLE_LT  = HexColor("#F3E5F5")

PAGE   = landscape(A4)
L_MARGIN = R_MARGIN = 15 * mm
T_MARGIN = 20 * mm
B_MARGIN = 20 * mm

doc = SimpleDocTemplate(
    OUTPUT_PATH, pagesize=PAGE,
    leftMargin=L_MARGIN, rightMargin=R_MARGIN,
    topMargin=T_MARGIN, bottomMargin=B_MARGIN,
    title="HR System – ChromaDB Vector Database Structure",
    author="HR System"
)

styles = getSampleStyleSheet()

# ── Shared paragraph styles ──────────────────────────────────────────────────
def ps(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)

h1         = ps("H1", fontSize=26, fontName="Helvetica-Bold",
                textColor=colors.white, alignment=TA_CENTER, spaceAfter=4)
sub_hdr    = ps("Sub", fontSize=10, fontName="Helvetica",
                textColor=HexColor("#9FA8DA"), alignment=TA_CENTER, spaceAfter=2)
section_p  = ps("Sec", fontSize=13, fontName="Helvetica-Bold",
                textColor=colors.white)
cell8      = ps("C8", fontSize=8, leading=11, fontName="Helvetica")
cell8b     = ps("C8B", fontSize=8, leading=11, fontName="Helvetica-Bold")
cell8i     = ps("C8I", fontSize=8, leading=11, fontName="Helvetica-Oblique",
                textColor=HexColor("#444"))
code8      = ps("Code8", fontSize=7.5, leading=10, fontName="Courier",
                textColor=HexColor("#1A237E"))
tbl_hdr_p  = ps("TH", fontSize=8, leading=10, fontName="Helvetica-Bold",
                textColor=colors.white)
desc_p     = ps("Desc", fontSize=8, leading=11, fontName="Helvetica-Oblique",
                textColor=HexColor("#333"), leftIndent=6, spaceBefore=2, spaceAfter=4)
note_p     = ps("Note", fontSize=7.5, leading=10, fontName="Helvetica",
                textColor=HexColor("#555"))

def P(text, style=cell8): return Paragraph(str(text), style)
def B(text):              return Paragraph(str(text), cell8b)
def Code(text):           return Paragraph(str(text), code8)

# ── Generic table builder ────────────────────────────────────────────────────
def make_table(headers, rows, col_widths, row_colors=None):
    hdr_row = [P(h, tbl_hdr_p) for h in headers]
    data = [hdr_row]
    for row in rows:
        data.append([c if hasattr(c, 'wrap') else P(c) for c in row])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND",    (0,0), (-1,0), C_NAV),
        ("LINEBELOW",     (0,0), (-1,0), 1.5, C_MID),
        ("ROWBACKGROUND", (0,1), (-1,-1), [C_ROW_NORM, C_ROW_ALT]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
    ]
    if row_colors:
        for idx, bg in row_colors.items():
            cmds.append(("BACKGROUND", (0, idx), (-1, idx), bg))
    t.setStyle(TableStyle(cmds))
    return t

# ── Section banner ───────────────────────────────────────────────────────────
def section_banner(title, color=C_ACCENT):
    d = [[P(title, section_p)]]
    t = Table(d, colWidths=[doc.width])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), color),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t

# ── Collection card header ───────────────────────────────────────────────────
def collection_card(num, name, pg_table, purpose, color=C_TEAL):
    left = f"<b>{num}. Collection: {name}</b>"
    right = f"PostgreSQL link: <font name='Courier'>{pg_table}</font>"
    d = [[P(left, ps("LC", fontSize=13, fontName="Helvetica-Bold",
                      textColor=color)),
          P(right, ps("RC", fontSize=9, fontName="Helvetica",
                       textColor=HexColor("#555")))]]
    t = Table(d, colWidths=[doc.width * 0.55, doc.width * 0.45])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), C_LIGHT),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("LINEBELOW",    (0,0), (-1,-1), 1.2, color),
    ]))
    return t

# ── STORY ─────────────────────────────────────────────────────────────────────
story = []
W = doc.width

# ═══════════════════════════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════════════════════════
cover = [["HR System — ChromaDB\nVector Database Structure"]]
cover_t = Table(cover, colWidths=[W])
cover_t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), C_NAV),
    ("TEXTCOLOR",    (0,0), (-1,-1), colors.white),
    ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 26),
    ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ("TOPPADDING",   (0,0), (-1,-1), 20),
    ("BOTTOMPADDING",(0,0), (-1,-1), 20),
]))
story.append(cover_t)
story.append(Spacer(1, 5*mm))

sub = [["3 Collections  ·  OpenAI text-embedding-3-small  ·  LangChain + ChromaDB ≥ 1.5.5  ·  Generated 2026-04-11"]]
sub_t = Table(sub, colWidths=[W])
sub_t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), HexColor("#0D1560")),
    ("TEXTCOLOR",    (0,0), (-1,-1), HexColor("#9FA8DA")),
    ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
    ("FONTSIZE",     (0,0), (-1,-1), 9.5),
    ("ALIGN",        (0,0), (-1,-1), "CENTER"),
    ("TOPPADDING",   (0,0), (-1,-1), 6),
    ("BOTTOMPADDING",(0,0), (-1,-1), 6),
]))
story.append(sub_t)
story.append(Spacer(1, 7*mm))

# ── Legend ───────────────────────────────────────────────────────────────────
leg = [[
    P("<font color='#00897B'>■</font>  hr_policies collection", cell8),
    P("<font color='#E65100'>■</font>  company_culture collection", cell8),
    P("<font color='#6A1B9A'>■</font>  job_descriptions collection", cell8),
    P("All collections use cosine similarity (HNSW default)", cell8),
]]
leg_t = Table(leg, colWidths=[W*0.22, W*0.22, W*0.22, W*0.34])
leg_t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,-1), C_LIGHT),
    ("GRID",         (0,0), (-1,-1), 0.3, C_BORDER),
    ("TOPPADDING",   (0,0), (-1,-1), 4),
    ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
]))
story.append(leg_t)
story.append(Spacer(1, 6*mm))

# ── TOC ──────────────────────────────────────────────────────────────────────
toc_items = [
    ("1",  "Collection Overview",             "All 3 collections at a glance"),
    ("2",  "hr_policies",                     "Leave, attendance & payroll rules"),
    ("3",  "company_culture",                 "Handbook, conduct & values"),
    ("4",  "job_descriptions",                "Role specs for recruitment screening"),
    ("5",  "Document & Chunk Schema",         "documents / metadatas / ids structure"),
    ("6",  "Chunking Configuration",          "RecursiveCharacterTextSplitter settings"),
    ("7",  "Embedding Configuration",         "OpenAI text-embedding-3-small setup"),
    ("8",  "ChromaDB Client Configuration",   "HTTP vs local mode, ports, paths"),
    ("9",  "RAG Query Patterns",              "Tools, k values, retriever setup"),
    ("10", "Seeding & Initialization",        "Startup flow, idempotency, file routing"),
    ("11", "API Integration Points",          "Endpoints that hit ChromaDB"),
    ("12", "PostgreSQL ↔ ChromaDB Link",      "HRPolicy.chroma_doc_id bridge"),
    ("13", "Error Handling & Fallbacks",      "Graceful degradation when Chroma offline"),
    ("14", "Knowledge Status Endpoint",       "GET /api/knowledge/status response"),
    ("15", "Dependencies & Versions",         "Required packages"),
]

toc_hdr = [P(h, tbl_hdr_p) for h in ["#", "Section", "Description"]]
toc_data = [toc_hdr] + [
    [P(n, cell8b), P(t, cell8b), P(d, cell8i)]
    for n, t, d in toc_items
]
toc_t = Table(toc_data, colWidths=[W*0.05, W*0.30, W*0.65], repeatRows=1)
toc_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), C_NAV),
    ("LINEBELOW",     (0,0), (-1,0), 1.5, C_MID),
    ("ROWBACKGROUND", (0,1), (-1,-1), [C_ROW_NORM, C_ROW_ALT]),
    ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0), (-1,-1), 3),
    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ("LEFTPADDING",   (0,0), (-1,-1), 5),
]))
toc_title = Paragraph("Table of Contents", ps("TOCH", fontSize=13,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceAfter=5))
story.append(KeepTogether([toc_title, toc_t]))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — COLLECTION OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(section_banner("1. Collection Overview", C_NAV))
story.append(Spacer(1, 4*mm))

overview_rows = [
    [B("hr_policies"),      Code("hr_policies"),
     P("Leave, attendance, payroll & general HR policies"),
     P("RecursiveCharacterTextSplitter\nchunk_size=600, overlap=80"),
     P("text-embedding-3-small\n(OpenAI)"),
     P("k=3"), P("hr_policies.txt, leave_policy.txt, …")],
    [B("company_culture"),  Code("company_culture"),
     P("Company handbook, values, code of conduct, disciplinary process"),
     P("RecursiveCharacterTextSplitter\nchunk_size=600, overlap=80"),
     P("text-embedding-3-small\n(OpenAI)"),
     P("k=3"), P("hr_handbook.txt, culture*.txt")],
    [B("job_descriptions"), Code("job_descriptions"),
     P("Job specifications for AI recruitment screening & culture-fit"),
     P("RecursiveCharacterTextSplitter\nchunk_size=600, overlap=80"),
     P("text-embedding-3-small\n(OpenAI)"),
     P("k=2"), P("job*.txt, *description*.txt")],
]
overview_t = make_table(
    ["Collection Name (Python)", "ChromaDB Name", "Purpose",
     "Chunking Strategy", "Embedding Model", "Default k", "Source Files"],
    overview_rows,
    [W*0.14, W*0.13, W*0.22, W*0.15, W*0.12, W*0.06, W*0.18],
    row_colors={1: C_TEAL_LT, 2: C_ORANGE_LT, 3: C_PURPLE_LT}
)
story.append(overview_t)
story.append(Spacer(1, 5*mm))

# Distance / HNSW note
hnsw_rows = [
    [B("Distance Metric"),    P("Cosine Similarity"), P("ChromaDB HNSW default — no explicit configuration set in codebase")],
    [B("Vector Dimensions"),  P("1536"),              P("Dimension of text-embedding-3-small output vectors")],
    [B("Index Type"),         P("HNSW"),              P("Hierarchical Navigable Small World graph (ChromaDB default)"),],
    [B("Persistence"),        P("Docker HTTP / Local file"), P("HTTP: chromadb.HttpClient(host, port=8100)   |   Local: PersistentClient(path='./chroma_db')")],
]
story.append(Paragraph("HNSW & Storage Configuration", ps("SH2", fontSize=11,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceBefore=4, spaceAfter=4)))
hnsw_t = make_table(["Parameter", "Value", "Notes"], hnsw_rows,
                     [W*0.18, W*0.18, W*0.64])
story.append(hnsw_t)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — hr_policies COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(collection_card("2", "hr_policies", "hr_policies",
             "HR leave rules, attendance policy, payroll entitlements", C_TEAL))
story.append(Paragraph(
    "Stores chunked HR policy documents. Queried by the Leave Agent before approving/rejecting requests "
    "and by the Chat Agent when employees ask policy questions.",
    desc_p))

# Document schema
story.append(Paragraph("Document Schema", ps("SH3", fontSize=10, fontName="Helvetica-Bold",
    textColor=C_TEAL, spaceBefore=4, spaceAfter=3)))
schema_rows = [
    [B("ids"),        P("String"),  P("Auto-generated UUID by ChromaDB"),
     P("Linked to HRPolicy.chroma_doc_id in PostgreSQL"),
     Code("e3b0c44298fc1c14...")],
    [B("documents"),  P("String (Text chunk)"), P("Up to 600 characters of raw policy text"),
     P("Preserves structure: headings, bullet points, section numbers"),
     Code("ANNUAL LEAVE (AL)\n──────────────────\nEntitlement: 14 working days...")],
    [B("metadatas"),  P("Dict"),    P("file (String) — source filename"),
     P("Additional fields can be added at index time via metadata param"),
     Code('{"file": "leave_policy.txt"}')],
    [B("embeddings"), P("List[float] len=1536)"), P("OpenAI text-embedding-3-small vector"),
     P("Stored internally by ChromaDB — not directly accessible in app code"), Code("[0.012, -0.034, …]")],
]
story.append(make_table(
    ["Field", "Type", "Description", "Notes", "Example Value"],
    schema_rows,
    [W*0.11, W*0.15, W*0.22, W*0.27, W*0.25]
))
story.append(Spacer(1, 4*mm))

# Metadata fields detail
story.append(Paragraph("Metadata Fields Detail", ps("SH3", fontSize=10, fontName="Helvetica-Bold",
    textColor=C_TEAL, spaceBefore=2, spaceAfter=3)))
meta_rows = [
    [B("file"), P("String"), P("NOT NULL"), P('Source filename. e.g. "leave_policy.txt", "attendance_policy.txt"'),
     P("Used to identify which policy document a chunk came from")],
]
story.append(make_table(
    ["Field", "Type", "Nullable", "Description", "Usage"],
    meta_rows,
    [W*0.10, W*0.08, W*0.09, W*0.37, W*0.36]
))
story.append(Spacer(1, 4*mm))

# Leave types indexed
story.append(Paragraph("Leave Types Stored in hr_policies Collection", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_TEAL, spaceBefore=2, spaceAfter=3)))
lt_rows = [
    [B("AL"), P("Annual Leave"),       P("14"),  P("3 working days"), P("Up to 7 days"),       P("No"),  P("Yes")],
    [B("SL"), P("Sick Leave"),         P("7"),   P("Same day"),       P("Not allowed"),         P("Yes, if >2 days"), P("Yes")],
    [B("CL"), P("Casual Leave"),       P("7"),   P("1 day"),          P("Not allowed"),         P("No"),  P("Yes")],
    [B("ML"), P("Maternity Leave"),    P("84"),  P("4 weeks"),        P("N/A"),                 P("Yes"), P("Yes (female)")],
    [B("PL"), P("Paternity Leave"),    P("3"),   P("1 week"),         P("N/A"),                 P("No"),  P("Yes (male)")],
    [B("NPL"),P("No-Pay Leave"),       P("—"),   P("1 week"),         P("Not allowed"),         P("No"),  P("No")],
]
story.append(make_table(
    ["Code", "Leave Type", "Max Days/Year", "Notice Required",
     "Carry-Over", "Document Required", "Paid"],
    lt_rows,
    [W*0.07, W*0.16, W*0.12, W*0.14, W*0.14, W*0.17, W*0.10],
    row_colors={1: C_TEAL_LT, 3: C_TEAL_LT, 5: C_TEAL_LT}
))

# Query tool
story.append(Spacer(1, 4*mm))
story.append(Paragraph("Query Tools Using This Collection", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_TEAL, spaceBefore=2, spaceAfter=3)))
qt_rows = [
    [Code("search_hr_policy(query)"),        P("k=3"), P("Chat Agent, Leave Agent"),
     P('search_hr_policy("how many annual leave days do I get?")')],
    [Code("get_leave_type_policy(code)"),     P("k=3"), P("Leave Agent"),
     P('get_leave_type_policy("AL")  →  query: "AL leave policy entitlement rules conditions"')],
    [Code("_check_policy_rag(code, days)"),   P("k=3"), P("Leave API endpoint"),
     P('_check_policy_rag("SL", 3)  →  returns policy text or hardcoded fallback')],
]
story.append(make_table(
    ["Tool / Function", "k", "Used By", "Example Call"],
    qt_rows,
    [W*0.25, W*0.04, W*0.18, W*0.53]
))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — company_culture COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(collection_card("3", "company_culture", "hr_policies (category=CONDUCT/GENERAL)",
             "Company handbook, values, conduct rules, disciplinary procedures", C_ORANGE))
story.append(Paragraph(
    "Stores company handbook chunks. Queried when employees ask about workplace culture, "
    "conduct rules, disciplinary process, resignation policy, or dress code.",
    desc_p))

story.append(Paragraph("Document Schema", ps("SH3", fontSize=10, fontName="Helvetica-Bold",
    textColor=C_ORANGE, spaceBefore=4, spaceAfter=3)))
cc_schema = [
    [B("ids"),        P("String"),             P("Auto-generated UUID by ChromaDB"),
     P("No explicit PostgreSQL link for culture chunks — managed separately"),
     Code("7f3a1b9c4d2e…")],
    [B("documents"),  P("String (Text chunk)"), P("Up to 600 characters of handbook text"),
     P("Covers values, conduct, dress code, digital policy, disciplinary steps"),
     Code("DISCIPLINARY PROCESS\nLevel 1 — Verbal Warning\n  Issued for: minor policy violations…")],
    [B("metadatas"),  P("Dict"),                P("file (String) — source filename"),
     P("Routing: filenames containing 'handbook', 'culture', or 'conduct' go here"),
     Code('{"file": "hr_handbook.txt"}')],
    [B("embeddings"), P("List[float] (len=1536)"), P("OpenAI text-embedding-3-small vector"),
     P("Stored internally by ChromaDB"), Code("[−0.021, 0.098, …]")],
]
story.append(make_table(
    ["Field", "Type", "Description", "Notes", "Example Value"],
    cc_schema,
    [W*0.11, W*0.15, W*0.22, W*0.27, W*0.25]
))
story.append(Spacer(1, 4*mm))

story.append(Paragraph("Topics Indexed in company_culture", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_ORANGE, spaceBefore=2, spaceAfter=3)))
topics = [
    [B("Company Values"),           P("Integrity, Innovation, Teamwork, Excellence, Respect"),
     P("Core values stated in hr_handbook.txt")],
    [B("Code of Conduct"),          P("Professionalism, respect, confidentiality, conflict of interest"),
     P("General conduct rules for all employees")],
    [B("Dress Code"),               P("Business casual Mon-Thu, casual Fri, formal for client visits"),
     P("Uniform / appearance guidelines")],
    [B("Digital Conduct"),          P("Email, internet, social media, data security policies"),
     P("IT and digital usage guidelines")],
    [B("Disciplinary Process"),     P("Level 1: Verbal Warning → Level 2: Written Warning → Level 3: Final Warning → Level 4: Termination"),
     P("Progressive discipline framework")],
    [B("Probation Policy"),         P("6-month probation for all new hires; review at end of period"),
     P("New employee onboarding rules")],
    [B("Resignation & Notice"),     P("1 month notice required; 2 weeks for less than 1 year service"),
     P("Offboarding requirements")],
    [B("Health & Safety"),          P("Emergency procedures, fire drills, incident reporting"),
     P("Workplace safety obligations")],
    [B("Recruitment Process"),      P("8-step process: Job posting → Applications → Screening → AI Interview → Shortlist → HR Interview → Offer → Onboarding"),
     P("Hiring pipeline overview")],
    [B("Performance Management"),   P("Monthly check-ins, quarterly reviews, annual appraisal"),
     P("Review cycle and KPI framework")],
]
story.append(make_table(
    ["Topic", "Content Summary", "Notes"],
    topics,
    [W*0.20, W*0.42, W*0.38],
    row_colors={i+1: C_ORANGE_LT for i in range(0, 10, 2)}
))
story.append(Spacer(1, 4*mm))

story.append(Paragraph("Query Tools Using This Collection", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_ORANGE, spaceBefore=2, spaceAfter=3)))
cc_qt = [
    [Code("search_company_culture(query)"), P("k=3"), P("Chat Agent"),
     P('"What is the dress code?" / "What happens in a disciplinary process?"')],
    [Code("search_hr_policy(query)"),       P("k=3"), P("Chat Agent (fallback)"),
     P("General policy search may also surface culture chunks")],
]
story.append(make_table(
    ["Tool / Function", "k", "Used By", "Example Query"],
    cc_qt,
    [W*0.25, W*0.04, W*0.15, W*0.56]
))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — job_descriptions COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(collection_card("4", "job_descriptions", "job_postings (ai_interview_questions / culture_keywords)",
             "Job specifications for AI recruitment screening & culture-fit scoring", C_PURPLE))
story.append(Paragraph(
    "Stores job specification chunks used by the Recruitment Agent to match candidate resumes, "
    "conduct AI interviews, and compute culture-fit scores.",
    desc_p))

story.append(Paragraph("Document Schema", ps("SH3", fontSize=10, fontName="Helvetica-Bold",
    textColor=C_PURPLE, spaceBefore=4, spaceAfter=3)))
jd_schema = [
    [B("ids"),        P("String"),             P("Auto-generated UUID by ChromaDB"),
     P("May link to JobPosting.id in PostgreSQL via metadata field"),
     Code("9a2f6d1c8b4e…")],
    [B("documents"),  P("String (Text chunk)"), P("Up to 600 characters of job spec text"),
     P("Contains role title, responsibilities, requirements, culture keywords"),
     Code("SOFTWARE ENGINEER\nRequirements: 3+ years Python, REST API design,\nFastAPI or Django…")],
    [B("metadatas"),  P("Dict"),                P("file (String) — source filename"),
     P("Routing: filenames containing 'job' or 'description' go here"),
     Code('{"file": "job_software_engineer.txt"}')],
    [B("embeddings"), P("List[float] (len=1536)"), P("OpenAI text-embedding-3-small vector"),
     P("Used for resume-to-JD cosine similarity scoring"), Code("[0.043, −0.017, …]")],
]
story.append(make_table(
    ["Field", "Type", "Description", "Notes", "Example Value"],
    jd_schema,
    [W*0.11, W*0.15, W*0.22, W*0.27, W*0.25]
))
story.append(Spacer(1, 4*mm))

story.append(Paragraph("Recruitment AI Scoring Using This Collection", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_PURPLE, spaceBefore=2, spaceAfter=3)))
scores = [
    [B("ai_resume_score"),    P("0–100"), P("Cosine similarity between resume embedding and JD chunks"),
     P("job_applications.ai_resume_score")],
    [B("ai_interview_score"), P("0–100"), P("Average score of AI interview Q&A answers vs JD requirements"),
     P("job_applications.ai_interview_score")],
    [B("ai_culture_fit"),     P("0–100"), P("Cosine similarity using culture_keywords from JobPosting"),
     P("job_applications.ai_culture_fit")],
    [B("ai_overall_score"),   P("0–100"), P("Weighted average: resume (40%) + interview (40%) + culture (20%)"),
     P("job_applications.ai_overall_score")],
]
story.append(make_table(
    ["Score Field", "Range", "How ChromaDB Is Used", "Stored In"],
    scores,
    [W*0.18, W*0.07, W*0.42, W*0.33],
    row_colors={1: C_PURPLE_LT, 3: C_PURPLE_LT}
))
story.append(Spacer(1, 4*mm))

story.append(Paragraph("Query Tools Using This Collection", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_PURPLE, spaceBefore=2, spaceAfter=3)))
jd_qt = [
    [Code("search_job_description(query)"), P("k=2"), P("Recruitment Agent"),
     P('"Software Engineer Python FastAPI" / role title or skill keywords')],
]
story.append(make_table(
    ["Tool / Function", "k", "Used By", "Example Query"],
    jd_qt,
    [W*0.25, W*0.04, W*0.18, W*0.53]
))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — CHUNKING + EMBEDDING CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(section_banner("5 & 6. Document / Chunk Schema and Chunking Configuration", C_NAV))
story.append(Spacer(1, 4*mm))

# Document structure
story.append(Paragraph("ChromaDB Document Structure (All Collections)", ps("SH3", fontSize=11,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceBefore=2, spaceAfter=3)))
doc_struct = [
    [B("ids"),        P("List[str]"),          P("REQUIRED"),
     P("One UUID string per chunk. Auto-generated by ChromaDB or provided by LangChain."),
     P("Linked to HRPolicy.chroma_doc_id in PostgreSQL (hr_policies only)")],
    [B("documents"),  P("List[str]"),          P("REQUIRED"),
     P("The raw text content of each chunk (≤ 600 chars). LangChain stores page_content here."),
     P("Used as the text passed to the embedding model and returned to the LLM")],
    [B("metadatas"),  P("List[Dict]"),         P("OPTIONAL"),
     P("One dict per chunk. Always contains {'file': <filename>}. Extra fields can be added."),
     P("Returned alongside documents — LLM uses source metadata in responses")],
    [B("embeddings"), P("List[List[float]]"),  P("AUTO"),
     P("1536-dimensional float vector from text-embedding-3-small. Stored by ChromaDB."),
     P("Never directly accessed in app code — ChromaDB handles query-time comparison")],
]
story.append(make_table(
    ["ChromaDB Field", "Python Type", "Required?", "Description", "App Usage"],
    doc_struct,
    [W*0.12, W*0.13, W*0.09, W*0.34, W*0.32]
))
story.append(Spacer(1, 5*mm))

# Chunking
story.append(Paragraph("Chunking Configuration (RecursiveCharacterTextSplitter)", ps("SH3", fontSize=11,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceBefore=2, spaceAfter=3)))
chunk_rows = [
    [B("chunk_size"),     Code("600"),    P("Characters"),
     P("Maximum characters per chunk. Applies to ALL three collections."),
     P("Balances context richness vs retrieval precision")],
    [B("chunk_overlap"),  Code("80"),     P("Characters"),
     P("Overlap between adjacent chunks to preserve sentence context across boundaries."),
     P("~13% overlap ratio — standard for policy documents")],
    [B("Splitter type"),  Code("Recursive"), P("Strategy"),
     P("Tries \\n\\n → \\n → space → char. Preserves paragraphs where possible."),
     P("Better than fixed-size for structured policy text")],
    [B("File loaders"),   Code("TextLoader / PyPDFLoader"), P("Per file type"),
     P("TextLoader for .txt (UTF-8). PyPDFLoader for .pdf files."),
     P("Both return List[Document] with page_content and metadata")],
    [B("Add method"),     Code("store.add_documents(chunks)"), P("LangChain API"),
     P("LangChain Chroma wrapper embeds and inserts all chunks in one call."),
     P("Triggers OpenAI API call per chunk for embedding generation")],
]
story.append(make_table(
    ["Parameter", "Value", "Unit", "Description", "Rationale"],
    chunk_rows,
    [W*0.14, W*0.18, W*0.10, W*0.32, W*0.26]
))
story.append(Spacer(1, 5*mm))

# Embedding
story.append(Paragraph("7. Embedding Configuration", ps("SH3", fontSize=11,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceBefore=2, spaceAfter=3)))
emb_rows = [
    [B("Model"),          Code("text-embedding-3-small"), P("OpenAI API"),
     P("Used for ALL three collections. Consistent embedding space across queries.")],
    [B("Vector dimensions"), Code("1536"),              P("Fixed"),
     P("Output dimension of text-embedding-3-small.")],
    [B("API Key"),        Code("OPENAI_API_KEY env var"), P("Environment"),
     P("Set via .env file or Docker compose environment block.")],
    [B("LangChain class"),Code("OpenAIEmbeddings(model='text-embedding-3-small')"), P("langchain-openai"),
     P("Wraps OpenAI API. Passed as embedding_function to Chroma().")],
    [B("Query embedding"),Code("Same model"),           P("At query time"),
     P("Queries are embedded with the same model before cosine similarity search.")],
]
story.append(make_table(
    ["Parameter", "Value", "Source", "Notes"],
    emb_rows,
    [W*0.15, W*0.32, W*0.12, W*0.41]
))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — CLIENT CONFIG + QUERY PATTERNS + SEEDING
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(section_banner("8. ChromaDB Client Configuration", C_NAV))
story.append(Spacer(1, 4*mm))

client_rows = [
    [B("CHROMA_HOST"),       Code("CHROMA_HOST env"), Code("localhost"),
     P("Hostname for Docker HTTP mode. Empty string = local mode."), P("HTTP mode only")],
    [B("CHROMA_PORT"),       Code("CHROMA_PORT env"), Code("8100"),
     P("TCP port for the ChromaDB HTTP server in Docker."), P("HTTP mode only")],
    [B("CHROMA_PERSIST_PATH"),Code("CHROMA_PERSIST_DIR env"), Code("./chroma_db"),
     P("File system path for persistent local storage."), P("Local mode only")],
    [B("Client class (HTTP)"),Code("chromadb.HttpClient"), P("—"),
     P("Used when deployed with Docker Compose. Connects to a standalone Chroma container."), P("Production")],
    [B("Client class (local)"),Code("chromadb.PersistentClient"), P("—"),
     P("Used for local development. Stores data on disk at CHROMA_PERSIST_PATH."), P("Development")],
]
story.append(make_table(
    ["Config Key", "Env Variable / Class", "Default", "Description", "Mode"],
    client_rows,
    [W*0.18, W*0.22, W*0.10, W*0.35, W*0.15]
))
story.append(Spacer(1, 5*mm))

story.append(section_banner("9. RAG Query Patterns", C_ACCENT))
story.append(Spacer(1, 4*mm))

query_rows = [
    [Code("search_hr_policy(query)"),      Code("hr_policies"),      Code("3"),
     P("Returns top 3 policy chunks as JSON with rank, content, source"),
     P("Chat Agent, Leave Agent")],
    [Code("search_company_culture(query)"),Code("company_culture"),  Code("3"),
     P("Returns top 3 handbook chunks. Used for conduct / culture questions"),
     P("Chat Agent")],
    [Code("search_job_description(query)"),Code("job_descriptions"), Code("2"),
     P("Returns top 2 JD chunks. Used for resume scoring and AI interviews"),
     P("Recruitment Agent")],
    [Code("get_leave_type_policy(code)"),  Code("hr_policies"),      Code("3"),
     P("Builds targeted query: '{code} leave policy entitlement rules conditions'"),
     P("Leave Agent")],
    [Code("_check_policy_rag(code, days)"),Code("hr_policies"),      Code("3"),
     P("Low-level function with hardcoded fallback if ChromaDB unavailable"),
     P("Leave API /leave/apply")],
]
story.append(make_table(
    ["Tool / Function", "Collection", "k", "Return Format / Behaviour", "Called By"],
    query_rows,
    [W*0.24, W*0.15, W*0.04, W*0.35, W*0.22]
))
story.append(Spacer(1, 5*mm))

story.append(section_banner("10. Seeding & Initialization", C_ACCENT))
story.append(Spacer(1, 4*mm))

seed_rows = [
    [B("Entry points"),        P("app/main.py → seed_policies()\nhr_agent_system/main.py → seed_all_policies()"),
     P("Both called at application startup (FastAPI lifespan)")],
    [B("Idempotency check"),   Code("collection.count() > 5  (or > 10)"),
     P("Skips seeding if collection already has enough chunks — prevents duplicate inserts on restart")],
    [B("File discovery"),      Code("glob('*.txt') + glob('*.pdf')"),
     P("Scans: backend/app/hr_agent_system/rag/sample_policies/")],
    [B("Routing logic"),       P("filename contains 'handbook'/'culture'/'conduct' → company_culture\n"
                                  "filename contains 'job'/'description' → job_descriptions\n"
                                  "everything else → hr_policies"),
     P("Simple string-match classifier — no ML routing")],
    [B("Currently seeded"),    P("leave_policy.txt (~5-6 chunks) → hr_policies\n"
                                  "hr_handbook.txt (~7-8 chunks) → company_culture"),
     P("~12-14 total chunks at fresh startup")],
    [B("Metadata added"),      Code('doc.metadata["file"] = filename'),
     P("Applied to every chunk before add_documents() call")],
]
story.append(make_table(
    ["Step / Parameter", "Value / Code", "Notes"],
    seed_rows,
    [W*0.18, W*0.40, W*0.42]
))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — API INTEGRATION + PG LINK + FALLBACKS + STATUS + DEPS
# ═══════════════════════════════════════════════════════════════════════════════
story.append(PageBreak())
story.append(section_banner("11. API Integration Points", C_NAV))
story.append(Spacer(1, 4*mm))

api_rows = [
    [Code("POST /api/sessions/{id}/message"), Code("hr_policies"),
     Code("search_hr_policy()"),
     P("Employee chat — answers policy questions via RAG + LLM")],
    [Code("POST /api/quick"),                 Code("company_culture"),
     Code("search_company_handbook()"),
     P("Quick one-off chat question without creating a session")],
    [Code("GET /api/knowledge/status"),       P("ALL"),
     Code("collection.count()"),
     P("Returns chunk counts per collection — health-check endpoint")],
    [Code("POST /api/leave/apply"),           Code("hr_policies"),
     Code("_check_policy_rag(code, days)"),
     P("Checks leave policy before Leave Agent makes approval decision")],
    [Code("Recruitment Agent (internal)"),    Code("job_descriptions"),
     Code("search_job_description()"),
     P("Used during AI screening stage of job application pipeline")],
]
story.append(make_table(
    ["API Endpoint / Agent", "Collection Used", "ChromaDB Tool Called", "Purpose"],
    api_rows,
    [W*0.26, W*0.13, W*0.22, W*0.39]
))
story.append(Spacer(1, 5*mm))

story.append(section_banner("12. PostgreSQL ↔ ChromaDB Link", C_ACCENT))
story.append(Spacer(1, 4*mm))
pg_rows = [
    [B("HRPolicy.chroma_doc_id"), P("String(200), UNIQUE, nullable"),
     P("Stores the ChromaDB UUID for the first chunk of this policy document"),
     P("Allows PostgreSQL → ChromaDB lookup to check if a document is already indexed")],
    [B("HRPolicy.is_indexed"),    P("Boolean, default=False"),
     P("Set to True once all chunks have been added to ChromaDB"),
     P("Used by seeder idempotency check and admin dashboard")],
    [B("HRPolicy.indexed_at"),    P("Text (ISO datetime), nullable"),
     P("Timestamp of when the document was indexed into ChromaDB"),
     P("Audit trail for policy indexing operations")],
    [B("HRPolicy.chunk_count"),   P("Integer, nullable"),
     P("Number of chunks created from this policy document"),
     P("Stored for reporting; helps estimate retrieval coverage")],
]
story.append(make_table(
    ["PostgreSQL Column", "Type", "Description", "Purpose"],
    pg_rows,
    [W*0.22, W*0.20, W*0.30, W*0.28]
))
story.append(Spacer(1, 5*mm))

story.append(section_banner("13. Error Handling & Fallbacks", C_ACCENT))
story.append(Spacer(1, 3*mm))
fb_rows = [
    [B("Leave policy fallback"), P("_check_policy_rag() wraps ChromaDB call in try/except"),
     P("If ChromaDB is unavailable, returns hardcoded rules: AL=14 days, SL=7 days, CL=7 days, ML=84 days, PL=3 days")],
    [B("Chat RAG fallback"),     P("LangChain retriever exception caught by Chat Agent"),
     P("Agent responds from LLM training knowledge only, notes policy data may be unavailable")],
    [B("Seeding fallback"),      P("seed_policies() wrapped in try/except at startup"),
     P("Application starts normally even if ChromaDB is not reachable — policies seeded lazily on first use")],
    [B("Collection missing"),    P("get_or_create_collection() used everywhere"),
     P("Collections are created automatically on first access — no manual setup required")],
]
story.append(make_table(
    ["Scenario", "Handling Mechanism", "Fallback Behaviour"],
    fb_rows,
    [W*0.18, W*0.35, W*0.47]
))
story.append(Spacer(1, 5*mm))

story.append(section_banner("14 & 15. Knowledge Status Endpoint & Dependencies", C_NAV))
story.append(Spacer(1, 4*mm))

status_rows = [
    [Code("GET /api/knowledge/status"), Code("200 OK"),
     Code('{"status":"ok","collections":{"hr_policies":{"loaded":true,"chunks":12},'
          '"company_culture":{"loaded":true,"chunks":8},'
          '"job_descriptions":{"loaded":true,"chunks":0}}}'),
     P("Used by admin dashboard to verify ChromaDB health")],
]
story.append(make_table(
    ["Endpoint", "Status", "Response Body", "Purpose"],
    status_rows,
    [W*0.18, W*0.07, W*0.50, W*0.25]
))
story.append(Spacer(1, 4*mm))

story.append(Paragraph("Python Package Dependencies", ps("SH3", fontSize=10,
    fontName="Helvetica-Bold", textColor=C_NAV, spaceBefore=2, spaceAfter=3)))
dep_rows = [
    [Code("chromadb"),                  Code("≥ 1.5.5"),   P("Core vector database client (HTTP and local modes)")],
    [Code("langchain"),                 Code("≥ 1.2.10"),  P("Agent framework — tools, chains, runnable interface")],
    [Code("langchain-chroma"),          Code("≥ 1.1.0"),   P("LangChain ↔ ChromaDB integration (Chroma wrapper class)")],
    [Code("langchain-community"),       Code("≥ 0.4.1"),   P("TextLoader, PyPDFLoader, document loaders")],
    [Code("langchain-openai"),          Code("≥ 1.1.11"),  P("OpenAIEmbeddings, ChatOpenAI wrappers")],
    [Code("langchain-text-splitters"),  Code("≥ 1.1.1"),   P("RecursiveCharacterTextSplitter")],
    [Code("openai"),                    Code("≥ 2.26.0"),  P("Direct OpenAI API client (embeddings + LLM calls)")],
]
story.append(make_table(
    ["Package", "Min Version", "Role in ChromaDB Pipeline"],
    dep_rows,
    [W*0.22, W*0.12, W*0.66]
))

# ── Build ─────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF generated: {OUTPUT_PATH}")
