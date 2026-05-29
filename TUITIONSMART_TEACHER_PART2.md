# TuitionSmart — Teacher Dashboard (Next.js)
## Part 2: Exam Management + Analytics

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Icons | Lucide React |
| Data Fetching | TanStack Query (React Query) |
| Forms | React Hook Form + Zod |
| Drag & Drop | @dnd-kit/core (question reordering) |
| Charts | Recharts |
| Date Picker | react-day-picker |
| Rich Text | Tiptap (essay question editor) |
| PDF Export | @react-pdf/renderer |

---

---

# Section 3: Exam Management

## Route: `/teacher/exams`

---

### Page: Exam List

**File:** `app/(teacher)/exams/page.tsx`

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Exams                                   [+ Create Exam]     │
│  Create and manage online examinations                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐│
│  │ 12         │  │ 2 LIVE     │  │ 5          │  │ 847    ││
│  │ Total Exams│  │ Active Now │  │ Pending    │  │Attempts││
│  │ This Term  │  │           │  │ Grading    │  │Total   ││
│  └────────────┘  └────────────┘  └────────────┘  └────────┘│
│                                                              │
│  [All ▼]  [Subject ▼]  [Status ▼]  [Search exams...]        │
│                                                              │
│  ● LIVE NOW                                                  │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ Mathematics Mid-Term        Grade 10 • 45 min left    │   │
│  │ 28 / 32 students submitted  [View Live] [End Exam]    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  Upcoming                                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Name              Subject  Class    Date       Status   │ │
│  │ Physics Chapter 4 Physics  Grade11  Jun 2      Scheduled│ │
│  │ English Essay     English  Grade10  Jun 5      Scheduled│ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Past Exams                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Name              Subject  Class    Date    Avg  Status │ │
│  │ Bio Mock Exam     Biology  Grade12  May 20  72%  Graded │ │
│  │ Chemistry Test    Chem     Grade11  May 15  85%  Graded │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

#### Live Exam Banner

```tsx
// components/exams/LiveExamBanner.tsx
// Only shows when there is an active exam
// Background: #FEF9C3 (light yellow) with left border #F59E0B (3px)
// Pulsing red dot indicator: animate-pulse
// Shows: Exam name, class, time remaining (live countdown)
// Shows: Submission progress bar "28/32 submitted"
// Buttons: [View Live Results] [End Exam Early] (danger, requires confirm dialog)
```

---

#### Exam Cards / Table

**Status chips:**
- `Scheduled`: blue chip, calendar icon
- `Live`:      green chip with pulsing dot, "In Progress"
- `Grading`:   amber chip, pencil icon
- `Graded`:    grey chip, check icon
- `Draft`:     dashed border chip, grey

**Row actions (⋮ menu):**
- Edit (only for Scheduled/Draft)
- Duplicate
- View Results
- Grade Submissions (only for Grading status)
- Export Results
- Delete (confirm dialog, only Draft)

---

### Page: Create / Edit Exam

**File:** `app/(teacher)/exams/new/page.tsx`
**File:** `app/(teacher)/exams/[examId]/edit/page.tsx`

#### Stepper Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Create Exam                                                 │
│                                                              │
│  ① Exam Details ──── ② Questions ──── ③ Settings ──── ④ Review │
│       ●                  ○               ○              ○    │
├──────────────────────────────────────────────────────────────┤
│  [Step content area — changes per step]                      │
├──────────────────────────────────────────────────────────────┤
│                        [Back]  [Continue →]                  │
└──────────────────────────────────────────────────────────────┘
```

Stepper:
- Active step: `#1A3A6E` circle with white number, bold label
- Completed step: `#16A34A` circle with check icon
- Upcoming step: `#E2E8F0` circle, grey label
- Connector line between steps: completed = green, upcoming = grey

---

#### Step 1: Exam Details

```
┌─────────────────────────────────────────────────────────────┐
│  Exam Name *                                                 │
│  [Mathematics Mid-Term Examination________________]         │
│                                                             │
│  Subject *                    Class / Grade *               │
│  [Mathematics ▼]              [Grade 10 ▼]                  │
│                                                             │
│  Start Date & Time *          End Date & Time *             │
│  [Jun 10, 2026  09:00 AM]     [Jun 10, 2026  10:30 AM]      │
│                                                             │
│  Duration (minutes) *         Total Marks                   │
│  [90          ]               [100         ]                │
│                                                             │
│  Instructions (shown to students before exam starts)        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Read all questions carefully. Show working for...   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Pass Mark (optional)                                       │
│  [50          ]  (50% pass threshold)                       │
└─────────────────────────────────────────────────────────────┘
```

---

#### Step 2: Questions

```
┌──────────────────────────────────────────────────────────────┐
│  Questions (8 added — 100 marks)      [+ Add Question]       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ⠿  Q1  [MCQ]    What is the derivative of x²?     10 marks │
│          Option A: 2x ✓  B: x²  C: 2  D: x            [⋮] │
│                                                              │
│  ⠿  Q2  [MCQ]    Which of the following is prime?  10 marks │
│          Option A: 4  B: 6  C: 7 ✓  D: 9              [⋮] │
│                                                              │
│  ⠿  Q3  [SHORT]  Explain integration by parts.     20 marks │
│          Manual grading required                       [⋮] │
│                                                              │
│  ⠿  Q4  [ESSAY]  Discuss the applications of...   30 marks │
│          Manual grading required                       [⋮] │
│                                                              │
│  ⠿  Q5  [T/F]    The derivative of a constant is 0. 5 marks│
│          Correct answer: True                          [⋮] │
│                                                              │
│  Total: 75 / 100 marks assigned                             │
│  ⚠ 25 marks not yet assigned to questions                   │
└──────────────────────────────────────────────────────────────┘
```

- Drag handle (⠿) on left — questions are drag-to-reorder via `@dnd-kit`
- Question type chip: color-coded — MCQ (blue), Short (amber), Essay (purple), T/F (green)
- Marks shown per question
- Actions menu (⋮): Edit, Duplicate, Delete
- Warning banner if total question marks ≠ exam total marks

---

#### Question Editor — Slide-over Panel (right side)

**File:** `components/exams/QuestionEditorPanel.tsx`

Width: 480px, slides in from right, overlay

```
┌────────────────────────────────────┐
│ Question Editor               [✕]  │
├────────────────────────────────────┤
│ Question Type                      │
│ [MCQ ▼] (MCQ / T/F / Short / Essay)│
│                                    │
│ Question Text *                    │
│ ┌──────────────────────────────┐  │
│ │ What is the derivative of x²?│  │
│ └──────────────────────────────┘  │
│ [+ Insert image/formula]           │
│                                    │
│ ── FOR MCQ ──────────────────────  │
│ Option A  [2x                ]  ◉  │
│ Option B  [x²                ]  ○  │
│ Option C  [2                 ]  ○  │
│ Option D  [x                 ]  ○  │
│ (◉ = correct answer)               │
│ [+ Add Option]                     │
│                                    │
│ ── FOR TRUE/FALSE ────────────────  │
│ Correct Answer: [True ▼]           │
│                                    │
│ ── FOR SHORT / ESSAY ─────────────  │
│ Model Answer (for tutor reference) │
│ [___________________________]      │
│ Max word count (optional)          │
│ [_______________]                  │
│                                    │
│ Marks for this question *          │
│ [10]                               │
│                                    │
│ Explanation (shown after grading)  │
│ [___________________________]      │
│                                    │
│ [Cancel]       [Save Question]     │
└────────────────────────────────────┘
```

---

#### Step 3: Settings

```
┌─────────────────────────────────────────────────────────────┐
│  Exam Behaviour                                             │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Shuffle question order for each student     [Toggle ●] │ │
│  │ Shuffle MCQ option order                    [Toggle ●] │ │
│  │ Allow students to review answers after exam [Toggle ○] │ │
│  │ Show correct answers after grading          [Toggle ○] │ │
│  │ Auto-publish results when grading complete  [Toggle ●] │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Anti-Cheat                                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Detect tab switching / focus loss           [Toggle ●] │ │
│  │ Warn on first detection, flag on second     [Toggle ●] │ │
│  │ Max allowed focus losses before auto-submit  [3]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Notifications                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Notify students when exam is published      [Toggle ●] │ │
│  │ Send reminder 30 min before exam starts     [Toggle ●] │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

- Each setting: label on left, description in smaller grey text below label, toggle on right
- Toggle on: `#2E6BC4` track, white thumb
- Toggle off: `#CBD5E1` track

---

#### Step 4: Review & Publish

```
┌─────────────────────────────────────────────────────────────┐
│  Review Your Exam                                           │
│                                                             │
│  ┌───────────────────┬────────────────────────────────────┐ │
│  │ Exam Name         │ Mathematics Mid-Term Exam          │ │
│  │ Subject           │ Mathematics — Grade 10             │ │
│  │ Date & Time       │ Jun 10, 2026 — 9:00 AM to 10:30 AM│ │
│  │ Duration          │ 90 minutes                         │ │
│  │ Total Marks       │ 100 marks (8 questions)            │ │
│  │ Pass Mark         │ 50 marks                           │ │
│  │ Students          │ 32 enrolled                        │ │
│  └───────────────────┴────────────────────────────────────┘ │
│                                                             │
│  Question Breakdown                                         │
│  MCQ: 5 questions (50 marks)                               │
│  Short Answer: 2 questions (30 marks)                      │
│  Essay: 1 question (20 marks)                              │  │
│                                                             │
│  ✓ All marks assigned (100/100)                            │
│  ✓ Start time is in the future                             │
│  ✓ 32 students will be notified                            │
│                                                             │
│  [← Back to Edit]       [Save as Draft]  [Publish Exam →]  │
└─────────────────────────────────────────────────────────────┘
```

- Checklist items green when passing, red with message if failing
- Publish requires all checklist green
- Publish confirmation dialog: "This will notify 32 students immediately. Continue?"

---

### Page: Live Exam Monitor

**File:** `app/(teacher)/exams/[examId]/live/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│  ● LIVE  Mathematics Mid-Term    Time Remaining: 44:32       │
│                               [End Exam]  [Auto-refresh ●]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 32       │  │ 28       │  │ 4        │  │ 2        │   │
│  │ Enrolled │  │ Submitted│  │ In Prog. │  │ Flagged  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  Submission Progress ████████████████░░░  28 / 32 (87.5%)  │
│                                                              │
│  Student Status Grid                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [✓ Aiden]   [✓ Bianca]  [⏳ Carlos] [✓ Diana]         │  │
│  │ [⚠ Ethan]  [✓ Fatima]  [✓ George]  [⏳ Hannah]        │  │
│  │ (✓ submitted, ⏳ in progress, ⚠ flagged, ✗ not started)│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Flags & Incidents                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ⚠ Ethan Myers — Tab switch detected at 9:23 AM        │  │
│  │ ⚠ Ethan Myers — Second focus loss at 9:35 AM          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

- Auto-refresh every 15 seconds (polling or SSE)
- Student status grid: 32px avatar chips, color-coded
  - Green check: submitted
  - Blue hourglass: in progress
  - Red warning: flagged
  - Grey: not started
- Flag table: timestamp, student, incident type, action ([Warn Student] [Dismiss])
- End Exam button: danger style, requires confirmation

---

### Page: Grade Submissions

**File:** `app/(teacher)/exams/[examId]/grade/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ Grade: Mathematics Mid-Term            [Publish All Results] │
│ 28 submissions — 12 graded — 16 pending                      │
├──────────────────────────────────────────────────────────────┤
│ Student List (left panel 30%)  │  Answer Review (right 70%) │
│                                │                            │
│ ● Aiden Perera    ✓ Graded     │  Q1 — MCQ — 10 marks       │
│ ● Bianca Silva    ● Grading    │  Question: What is x²..    │
│   Carlos Mendes   ○ Pending    │  Student answer: [A] 2x    │
│   Diana Raj       ○ Pending    │  Correct: [A] ✓  Auto: 10/10│
│                                │                            │
│                                │  Q3 — Short — 20 marks     │
│                                │  Question: Explain...      │
│                                │  Student answer:           │
│                                │  "Integration by parts..." │
│                                │  ┌─────────────────────┐  │
│                                │  │ Score: [  ] / 20    │  │
│                                │  │ Feedback (optional): │  │
│                                │  │ [_______________]   │  │
│                                │  └─────────────────────┘  │
│                                │                            │
│                                │  [← Prev Student]  [Next→]│
│                                │  [Save & Continue]         │
└──────────────────────────────────────────────────────────────┘
```

- Left panel: student list with grading status badges
- Right panel: full submission view
  - MCQ/T-F: show auto-graded result, teacher can override
  - Short/Essay: text area display + manual score input + feedback input
- Score input: number field with max mark shown (`[__] / 20`)
- "Save & Continue" auto-advances to next ungraded student
- Progress bar at top: X / 28 graded

---

### Page: Exam Results

**File:** `app/(teacher)/exams/[examId]/results/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│ Results: Mathematics Mid-Term              [Export Results]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 72%      │  │ 85       │  │ 52       │  │ 24/28    │   │
│  │ Avg Score│  │ Highest  │  │ Lowest   │  │ Pass Rate│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  Score Distribution (Bar chart)                             │
│  [0-40] [41-50] [51-60] [61-70] [71-80] [81-90] [91-100]   │
│    1      2       3       5       8       6       3          │
│                                                              │
│  Question Analysis                                           │
│  Q1: 95% correct | Q2: 78% | Q3: Avg 14/20 | Q4: Avg 22/30 │
│                                                              │
│  Student Results Table                                       │
│  Name          Score    Grade  Status    Flags   Actions    │
│  Aiden Perera  92/100   A+     ✓ Pass    —       [View]     │
│  Bianca Silva  78/100   B+     ✓ Pass    —       [View]     │
│  Carlos Mendes 48/100   D      ✗ Fail    ⚠1      [View]     │
└──────────────────────────────────────────────────────────────┘
```

---

---

# Section 4: Analytics

## Route: `/teacher/analytics`

---

### Page: Analytics Dashboard

**File:** `app/(teacher)/analytics/page.tsx`

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Analytics                  [This Month ▼] [Class ▼] [Export]│
│  Performance insights across your classes                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 91.2%    │  │ 74%      │  │ 85/100   │  │ 3        │   │
│  │ Avg      │  │ Fee      │  │ Avg Exam │  │ At Risk  │   │
│  │ Attend.  │  │ Collect. │  │ Score    │  │ Students │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌────────────────────────────────┐  ┌─────────────────────┐│
│  │ Attendance Trend (Line Chart)  │  │ Score Distribution  ││
│  │ Last 6 months attendance %     │  │ (Histogram)         ││
│  │ By class or all combined       │  │ Across all exams    ││
│  └────────────────────────────────┘  └─────────────────────┘│
│                                                              │
│  ┌────────────────────────────────┐  ┌─────────────────────┐│
│  │ Exam Performance by Subject    │  │ Fee Collection Rate ││
│  │ (Grouped Bar Chart)            │  │ (Line chart by month││
│  │ Math / Science / English       │  │ + target line)      ││
│  └────────────────────────────────┘  └─────────────────────┘│
│                                                              │
│  At-Risk Students                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Name         Attend.  Last Exam  Fees      Risk Reason  │ │
│  │ Carlos Mendes  62%     48/100    Overdue   Low attend.  │ │
│  │ Hannah Soto    70%     55/100    Partial   Weak perf.   │ │
│  │ Ian Park       68%     —         Unpaid    Multiple     │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

#### Summary Cards

Same `StatCard` component from Part 1 — 4 cards in a row.

```tsx
const analyticsCards = [
  { label: 'Avg Attendance',    value: '91.2%', icon: Users,       color: 'blue'  },
  { label: 'Fee Collection',    value: '74%',   icon: Banknote,    color: 'green' },
  { label: 'Avg Exam Score',    value: '85/100',icon: BookOpen,    color: 'blue'  },
  { label: 'At-Risk Students',  value: '3',     icon: AlertTriangle, color: 'red' },
]
```

---

#### Chart 1: Attendance Trend (Line Chart)

```tsx
// components/analytics/AttendanceTrendChart.tsx
// Recharts LineChart
// X-axis: months (Jan → Jun 2026)
// Y-axis: percentage 0–100%
// Lines: one per class (Grade 10, 11, 12) — each different color
//   Grade 10: #1A3A6E
//   Grade 11: #2E6BC4
//   Grade 12: #7C3AED
// Reference line at 75%: dashed red — "Minimum threshold"
// Tooltip: "May 2026 — Grade 10: 94% | Grade 11: 88%"
// Legend at bottom
// Height: 280px
// Dots on data points, hover enlarge
```

---

#### Chart 2: Score Distribution (Histogram)

```tsx
// components/analytics/ScoreDistributionChart.tsx
// Recharts BarChart
// X-axis: score ranges [0-40, 41-50, 51-60, 61-70, 71-80, 81-90, 91-100]
// Y-axis: number of students
// Bar fill: gradient #2E6BC4 → #1A3A6E
// Tooltip: "71–80 range: 8 students"
// Reference area: 0–50 shaded red (fail zone), 50+ shaded green (pass zone)
// Height: 200px
```

---

#### Chart 3: Exam Performance by Subject (Grouped Bar)

```tsx
// components/analytics/SubjectPerformanceChart.tsx
// Recharts BarChart with groupMode="group"
// X-axis: subjects (Mathematics, Science, English, Physics)
// Y-axis: average score (0–100)
// Two bars per subject:
//   Bar 1 (dark): This month's average
//   Bar 2 (light): Last month's average (for comparison)
// Target line: 70 (expected minimum) — dashed amber
// Legend: This Month / Last Month / Target
// Height: 260px
```

---

#### Chart 4: Fee Collection Rate (Line Chart)

```tsx
// components/analytics/FeeCollectionChart.tsx
// Recharts LineChart
// X-axis: months (Jan → Jun)
// Y-axis: percentage 0–100%
// Line 1 (blue): actual collection rate each month
// Line 2 (dashed amber): target collection rate (100%)
// Area fill below line 1: semi-transparent blue
// Tooltip: "April 2026: 82% collected (LKR 98,000 / 120,000)"
// Height: 200px
```

---

#### At-Risk Students Table

```tsx
// components/analytics/AtRiskTable.tsx
// Students flagged as at-risk:
//   Attendance < 75% OR
//   Last exam score < 50% OR
//   Outstanding unpaid fees > 1 month

columns: [
  { id: 'name',       header: 'Student',    cell: AvatarNameCell },
  { id: 'attendance', header: 'Attendance', cell: AttendanceBadge },
  { id: 'lastExam',   header: 'Last Exam',  cell: ScoreBadge },
  { id: 'feeStatus',  header: 'Fee Status', cell: FeeStatusBadge },
  { id: 'riskReason', header: 'Risk Flags', cell: RiskFlagCell },
  { id: 'actions',    header: '',           cell: AtRiskActions },
]

// RiskFlagCell: shows icon chips — 🔴 Attendance 🔴 Performance 🔴 Fees
// AtRiskActions: [Contact Parent] [View Profile] buttons
```

---

### Page: Student Performance Deep-Dive

**File:** `app/(teacher)/analytics/students/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│  Student Performance                 [Class ▼] [Period ▼]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Search student...]                                         │
│                                                              │
│  Student Performance Table                                   │
│  Name          Attend.  Avg Score  Exams  Fee     Trend      │
│  Aiden Perera  95%      88/100     5/5    Paid    ↑ +4pts    │
│  Bianca Silva  78%      74/100     4/5    Partial → same     │
│  Carlos Mendes 62%      48/100     3/5    Overdue ↓ -8pts    │
│                                                              │
│  (Trend = change from previous period)                       │
│  ↑ green | → grey | ↓ red                                   │
└──────────────────────────────────────────────────────────────┘
```

---

### Page: Subject Analytics

**File:** `app/(teacher)/analytics/subjects/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│  Subject Analytics                   [Subject ▼] [Period ▼] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Mathematics — Grade 10                                      │
│                                                              │
│  ┌───────────────────────────────┐  ┌──────────────────────┐│
│  │ Exam Scores Over Time         │  │ Attendance by Month  ││
│  │ [Line chart — per exam date]  │  │ [Bar chart — monthly]││
│  └───────────────────────────────┘  └──────────────────────┘│
│                                                              │
│  Topic Weak Points (based on question analysis)             │
│  Q3: "Integration" — avg 60% correct                        │
│  Q7: "Trigonometry" — avg 55% correct                       │
│  Q9: "Calculus" — avg 48% correct                           │
│                                                              │
│  Recommendation                                             │
│  ⚠ Consider revisiting Calculus — 3 of last 5 exams show   │
│    below-average performance on calculus questions.         │
└──────────────────────────────────────────────────────────────┘
```

---

### Page: Reports Export

**File:** `app/(teacher)/analytics/reports/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│  Generate Reports                                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Student Progress│  │ Attendance      │  │ Exam Results│ │
│  │ Report          │  │ Report          │  │ Report      │ │
│  │ [Generate PDF]  │  │ [Generate PDF]  │  │[Generate PDF│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Fee Collection  │  │ At-Risk Students│                  │
│  │ Report          │  │ Report          │                  │
│  │ [Generate PDF]  │  │ [Generate PDF]  │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                              │
│  Custom Report Builder                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Include: ☑ Attendance  ☑ Marks  ☐ Fees  ☑ Exams      │  │
│  │ Class: [Grade 10 ▼]  Period: [May 2026 ▼]            │  │
│  │ Format: ○ PDF  ○ CSV  ○ Excel                         │  │
│  │                              [Generate Custom Report] │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

Report cards:
- White bg, 12px radius, shadow-sm
- Icon top (48px, colored)
- Report name in bold
- Description in grey small text
- [Generate PDF] button — primary style
- Shows "Last generated: May 25, 2026" below button

---

## API Integration

### Exam Endpoints

```ts
// lib/api/exams.ts
GET    /api/teacher/exams                          // list all exams
GET    /api/teacher/exams/:id                      // exam detail
POST   /api/teacher/exams                          // create exam
PUT    /api/teacher/exams/:id                      // update exam
DELETE /api/teacher/exams/:id                      // delete draft exam
POST   /api/teacher/exams/:id/publish              // publish exam
POST   /api/teacher/exams/:id/end                  // end live exam

GET    /api/teacher/exams/:id/submissions          // all submissions
GET    /api/teacher/exams/:id/submissions/:sid     // single submission
PUT    /api/teacher/exams/:id/submissions/:sid/grade // grade submission
POST   /api/teacher/exams/:id/results/publish      // publish all results
GET    /api/teacher/exams/:id/results              // results summary
GET    /api/teacher/exams/:id/live                 // live status (polling)
```

### Analytics Endpoints

```ts
// lib/api/analytics.ts
GET    /api/teacher/analytics/summary              // top-level KPIs
GET    /api/teacher/analytics/attendance           // trend data (by month)
GET    /api/teacher/analytics/exams                // score distributions, per-subject
GET    /api/teacher/analytics/fees                 // fee collection over time
GET    /api/teacher/analytics/at-risk              // at-risk student list
GET    /api/teacher/analytics/students             // per-student performance table
GET    /api/teacher/analytics/subjects/:id         // subject deep-dive data
POST   /api/teacher/analytics/reports/generate     // generate report PDF/CSV
```

### React Query Hooks

```ts
// hooks/useExams.ts
export const useExams = (filters: ExamFilters) =>
  useQuery({ queryKey: ['exams', filters], queryFn: () => fetchExams(filters) })

export const useExam = (id: string) =>
  useQuery({ queryKey: ['exams', id], queryFn: () => fetchExam(id) })

export const useLiveExam = (id: string) =>
  useQuery({
    queryKey: ['exams', id, 'live'],
    queryFn: () => fetchLiveExam(id),
    refetchInterval: 15000,  // poll every 15s
  })

export const useCreateExam = () =>
  useMutation({ mutationFn: createExam, onSuccess: () => queryClient.invalidateQueries(['exams']) })

export const useGradeSubmission = () =>
  useMutation({ mutationFn: gradeSubmission })

// hooks/useAnalytics.ts
export const useAnalyticsSummary = (filters: AnalyticsFilters) =>
  useQuery({ queryKey: ['analytics', 'summary', filters], queryFn: () => fetchSummary(filters) })

export const useAttendanceTrend = (filters: AnalyticsFilters) =>
  useQuery({ queryKey: ['analytics', 'attendance', filters], queryFn: () => fetchAttendanceTrend(filters) })

export const useAtRiskStudents = () =>
  useQuery({ queryKey: ['analytics', 'at-risk'], queryFn: fetchAtRisk })

export const useSubjectAnalytics = (subjectId: string, filters: AnalyticsFilters) =>
  useQuery({ queryKey: ['analytics', 'subjects', subjectId, filters], queryFn: () => fetchSubjectAnalytics(subjectId, filters) })
```

---

## Folder Structure

```
app/
  (teacher)/
    exams/
      page.tsx                        ← Exam list
      new/
        page.tsx                      ← Create exam (stepper)
      [examId]/
        edit/
          page.tsx                    ← Edit exam
        live/
          page.tsx                    ← Live monitor
        grade/
          page.tsx                    ← Grade submissions
        results/
          page.tsx                    ← Results overview
    analytics/
      page.tsx                        ← Main analytics dashboard
      students/
        page.tsx                      ← Student performance table
      subjects/
        page.tsx                      ← Subject analytics
      reports/
        page.tsx                      ← Report generator

components/
  exams/
    ExamListTable.tsx
    LiveExamBanner.tsx
    LiveExamMonitor.tsx
    ExamStepper.tsx
    steps/
      ExamDetailsStep.tsx
      QuestionsStep.tsx
      SettingsStep.tsx
      ReviewStep.tsx
    QuestionEditorPanel.tsx
    QuestionCard.tsx
    GradePanel.tsx
    ResultsSummary.tsx
  analytics/
    AttendanceTrendChart.tsx
    ScoreDistributionChart.tsx
    SubjectPerformanceChart.tsx
    FeeCollectionChart.tsx
    AtRiskTable.tsx
    AnalyticsSummaryCards.tsx
    ReportCard.tsx
    CustomReportBuilder.tsx

hooks/
  useExams.ts
  useAnalytics.ts

lib/
  api/
    exams.ts
    analytics.ts
  validations/
    exam.schema.ts
```

---

## Key Interaction Flows

### Create Exam Flow
1. Click [+ Create Exam] → navigate to `/teacher/exams/new`
2. Step 1: Fill exam details → [Continue]
3. Step 2: Add questions via slide-over panel, drag to reorder → [Continue]
4. Step 3: Configure settings toggles → [Continue]
5. Step 4: Review checklist → [Publish] or [Save as Draft]
6. On publish: success toast + redirect to exam detail page

### Grade Exam Flow
1. Exam reaches "Grading" status after close time
2. Badge shown on sidebar nav: "Exams (2)" — ungraded count
3. Click exam → [Grade Submissions] button
4. Left panel: student list, click student
5. Right panel: auto-graded shown, fill manual scores → [Save & Continue]
6. When all graded: [Publish Results] button → students notified

### Analytics Filter Flow
1. Period picker: This Week / This Month / Last 3 Months / Custom Range
2. Class filter: All / Grade 10 / Grade 11 / Grade 12
3. Subject filter (on subject pages): All / Mathematics / Science...
4. All charts update simultaneously on filter change (loading skeleton during fetch)

---

*TuitionSmart — Teacher Dashboard Part 2 | Exam Management + Analytics | Next.js 14*
