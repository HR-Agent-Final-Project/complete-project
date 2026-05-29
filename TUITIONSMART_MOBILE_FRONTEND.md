# TuitionSmart Mobile App — Frontend Development Prompt

---

## Project Overview

Build the complete frontend for **TuitionSmart**, an AI-powered Learning Management System mobile application designed for private tuition centers, tutors, students, and parents. The app must be built in **Flutter** (for cross-platform iOS & Android) or **React Native**, covering all modules described below with pixel-perfect UI consistency.

---

## Brand Identity & Design System

### Color Palette

| Token | Hex | Usage |
|---|---|---|
| Primary Navy | `#1A3A6E` | Headers, nav bar, primary buttons |
| Accent Blue | `#2E6BC4` | Interactive elements, links, active states |
| Light Blue | `#E8F0FB` | Card backgrounds, selected states, chips |
| Warning Amber | `#F59E0B` | Pending, late, warnings |
| Success Green | `#16A34A` | Present, paid, passed |
| Danger Red | `#DC2626` | Absent, unpaid, failed, errors |
| Neutral Dark | `#1E293B` | Primary text |
| Neutral Mid | `#64748B` | Secondary text, placeholders |
| Neutral Light | `#F1F5F9` | Page backgrounds, dividers |
| White | `#FFFFFF` | Card surfaces, input fields |

### Typography

| Style | Size | Weight | Color |
|---|---|---|---|
| Heading Large | 24px | 700 | `#1A3A6E` |
| Heading Medium | 18px | 600 | `#1E293B` |
| Heading Small | 15px | 600 | `#1E293B` |
| Body Regular | 14px | 400 | `#1E293B` |
| Body Small | 12px | 400 | `#64748B` |
| Labels/Tags | 11px | 500 | uppercase, letter-spacing 0.5px |

Font Family: `Inter` (fallback: `Poppins`)

### Spacing System

Base unit: **4px** — use multiples of 4 only (8, 12, 16, 20, 24, 32, 48)

### Border Radius

| Element | Radius |
|---|---|
| Cards | 12px |
| Buttons | 10px |
| Input fields | 8px |
| Chips/Tags | 20px (pill) |
| Avatars | 50% (circle) |

### Shadows

- Card: `0px 2px 12px rgba(0,0,0,0.08)`
- Modal: `0px 8px 32px rgba(0,0,0,0.16)`

### Iconography

Use `Lucide Icons` or `Heroicons` — line style, stroke width 1.5, 20px default size.

---

## App Architecture & Navigation

### Role-Based Navigation

| Role | Bottom Nav Tabs |
|---|---|
| Student | Home \| Classes \| Recordings \| Exams \| AI Chat |
| Tutor | Home \| My Classes \| Attendance \| Marks \| More |
| Parent | Home \| Attendance \| Marks \| Fees \| Calendar |
| Admin | Home \| Students \| Tutors \| Reports \| Settings |

### Bottom Navigation Bar Specs

- Active tab: filled icon + label in `#2E6BC4`, underline indicator
- Inactive tab: outline icon + label in `#94A3B8`
- Background: `#FFFFFF`, top border `1px solid #E2E8F0`
- Height: 64px + safe area inset

---

## Screen Designs — All Modules

---

### 1. Onboarding & Authentication

#### Splash Screen

- Full-screen gradient background: `#1A3A6E` → `#2E6BC4` (top to bottom)
- Centered white logo: bold "TuitionSmart" wordmark + graduation cap icon above
- Tagline: "Smart Learning. Real Results." — white, 14px, weight 300
- Loading spinner at bottom in white

#### Login Screen

```
┌──────────────────────────────┐
│                              │
│    [Logo — 48px height]      │
│                              │
│   Welcome Back               │
│   Sign in to your account    │
│                              │
│  ┌──────────────────────┐    │
│  │ ✉ Email address      │    │
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ 🔒 Password      👁  │    │
│  └──────────────────────┘    │
│                              │
│              Forgot Password?│
│                              │
│  ┌──────────────────────┐    │
│  │       Sign In        │    │  ← #1A3A6E bg, white text, 52px
│  └──────────────────────┘    │
│                              │
│  Don't have an account?      │
│  Contact your center admin   │
└──────────────────────────────┘
```

- Card: white bg, 16px radius, 24px padding, on `#E8F0FB` background
- Input fields: white bg, `#E2E8F0` border, 48px height, focus → `#2E6BC4` border
- Password eye toggle shows/hides text
- Role chip auto-displayed after successful login

#### Face Registration Screen (Student Onboarding)

```
┌──────────────────────────────┐
│ ← Cancel                     │
│                              │
│    ┌────────────────────┐    │
│    │                    │    │
│    │   [Camera Feed]    │    │
│    │                    │    │
│    │    ┌────────┐      │    │  ← Oval guide, pulsing blue border
│    │    │        │      │    │
│    │    │  Face  │      │    │
│    │    └────────┘      │    │
│    │                    │    │
│    └────────────────────┘    │
│                              │
│  Position your face within   │
│  the frame                   │
│                              │
│  Look straight               │
│                              │
│    ● ● ○ ○ ○                 │  ← 5-photo progress
└──────────────────────────────┘
```

- Full-screen dark overlay camera view
- Oval face guide: animated pulsing border `#2E6BC4`
- Green flash animation on successful photo capture
- Instruction updates per angle: "Look straight" → "Turn slightly left" → etc.

---

### 2. Dashboard / Home Screens

#### Student Home

```
┌──────────────────────────────┐
│  Good Morning, Aiden 👋      │  ← gradient banner #1A3A6E → #2E6BC4
│  Monday, May 26 2026         │
│                         [👤] │
├──────────────────────────────┤
│  ┌─────────┐  ┌─────────┐   │
│  │  94%    │  │   3     │   │
│  │Attendance│  │ Classes │   │
│  │This Month│  │  Today  │   │
│  └─────────┘  └─────────┘   │
│  ┌─────────┐  ┌─────────┐   │
│  │   2     │  │  128    │   │
│  │ Pending │  │   AI    │   │
│  │  Exams  │  │Questions│   │
│  └─────────┘  └─────────┘   │
├──────────────────────────────┤
│  Today's Classes             │
│  ──────────────────────────  │
│  ┌──────────────────────┐    │
│  │ │ Mathematics  09:00 │    │  ← color-coded left border
│  │ │ Mr. Fernando       │    │
│  │ │            [Join]  │    │
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ │ Science      11:00 │    │
│  │ │ Ms. Perera         │    │
│  │ │            [Join]  │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Recent Recordings           │
│  ──────────────────────────  │
│  [▶] Algebra Basics — May 24 │
│  [▶] Cell Biology — May 23   │
└──────────────────────────────┘
```

- Banner: gradient, 180px height, white text
- Stat cards: white bg, 12px radius, shadow-sm, icon circle (40px, colored bg)
- Today's Classes: horizontal scroll cards
- Recent Recordings: vertical list with play icon

#### Tutor Home

```
┌──────────────────────────────┐
│  Good Morning, Mr. Silva     │  ← gradient banner
│  You have 4 classes today    │
│                         [👤] │
├──────────────────────────────┤
│  Quick Actions               │
│  ┌──────┐┌──────┐┌──────┐   │
│  │ Mark ││Upload││Start │   │
│  │ Att. ││Marks ││Class │   │
│  └──────┘└──────┘└──────┘   │
│  ┌──────┐                    │
│  │Create│                    │
│  │ Exam │                    │
│  └──────┘                    │
├──────────────────────────────┤
│  Today's Schedule            │
│  09:00  Mathematics Gr.10    │
│  11:00  Science Gr.11        │
│  14:00  Physics Gr.12        │
├──────────────────────────────┤
│  Pending Actions             │
│  ● 3 essays need grading     │
│  ● Attendance unmarked (2PM) │
│  ● 1 recording unconfirmed   │
├──────────────────────────────┤
│  Today's Attendance          │
│  [Donut chart — P/A/L]       │
└──────────────────────────────┘
```

#### Parent Home

```
┌──────────────────────────────┐
│  Monitoring Aiden Perera     │  ← banner
│                         [🔔] │
├──────────────────────────────┤
│  ┌──────────────────────┐    │
│  │ Attendance  94%      │    │
│  │ ████████████░░░      │    │
│  │ This Month           │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Recent Marks                │
│  Mathematics  85/100  A      │
│  Science      78/100  B+     │
│  English      91/100  A+     │
├──────────────────────────────┤
│  ┌──────────────────────┐    │
│  │ ⚠ Outstanding Fees   │    │  ← amber if unpaid
│  │ LKR 5,000 — May 2026 │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Next Class                  │
│  Mathematics — Today 2:00PM  │
└──────────────────────────────┘
```

---

### 3. Attendance Module

#### Facial Recognition Screen (Tutor-triggered)

```
┌──────────────────────────────┐
│ ← Cancel         Mathematics │
│                              │
│  ┌────────────────────────┐  │
│  │                        │  │
│  │     [Camera Feed]      │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │  ✓ Aiden Perera  │  │  │  ← green box on recognition
│  │  └──────────────────┘  │  │
│  │                        │  │
│  └────────────────────────┘  │
│                              │
│  Recognized: Aiden Perera    │
│  Marked: Present ✓           │
│                              │
│  [Manual Override]           │
└──────────────────────────────┘
```

- Recognized: face box turns green, toast "Aiden Perera — Present"
- Unrecognized: face box turns red, prompt "Face not matched — Override?"
- Manual override: bottom sheet with student search + Present/Absent/Late buttons

#### Manual Attendance Screen

```
┌──────────────────────────────┐
│ ← Mathematics — May 26       │
│ Grade 10 • 32 students       │
│ [Search students...]         │
├──────────────────────────────┤
│  Aiden Perera                │
│  STU-001          [P][A][L]  │
│  ─────────────────────────── │
│  Bianca Silva                │
│  STU-002          [P][A][L]  │  ← P=green, A=red, L=amber (selected)
│  ─────────────────────────── │
│  Carlos Mendes               │
│  STU-003          [P][A][L]  │
├──────────────────────────────┤
│  28 of 32 marked             │
│  ████████████████████░░░░    │
│  [      Save Attendance    ] │
└──────────────────────────────┘
```

#### Attendance History Screen (Student/Parent)

```
┌──────────────────────────────┐
│ ← Attendance History         │
│ [All][Present][Absent][Late] │
│              [May 2026 ▼]   │
├──────────────────────────────┤
│  Mo Tu We Th Fr Sa Su        │
│   -   -  1  2  3  4   5      │
│   6   7  8  9 10 11  12      │  ← green/red/amber dots
│  13  14 15 16 17 18  19      │
│  20  21 22 23 24 25  26      │
├──────────────────────────────┤
│  Summary                     │
│  Present: 20  Absent: 2      │
│  Late: 1   Rate: 92%         │
├──────────────────────────────┤
│  May 24  Mathematics  ● P    │
│  May 22  Science      ● P    │
│  May 20  Mathematics  ● A    │
│  May 18  English      ● L    │
└──────────────────────────────┘
```

---

### 4. Online Class Delivery

#### Class List Screen

```
┌──────────────────────────────┐
│ My Classes                   │
│ [Upcoming][Live Now][Past]   │
├──────────────────────────────┤
│  ● LIVE NOW                  │
│  ┌──────────────────────┐    │
│  │ Mathematics          │    │  ← pulsing red LIVE badge
│  │ Mr. Fernando         │    │
│  │ 09:00 – 10:30        │    │
│  │ 28 participants      │    │
│  │          [Join Now →]│    │  ← green button
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Upcoming                    │
│  ┌──────────────────────┐    │
│  │ Science              │    │
│  │ Ms. Perera           │    │
│  │ Today 11:00 AM       │    │
│  │ Starts in 1h 20m     │    │
│  │              [Join]  │    │  ← disabled, enabled 5min before
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Past                        │
│  May 24 • Mathematics        │
│  Mr. Fernando  [View Recording]│
└──────────────────────────────┘
```

#### Post-Class Recording Confirmation (Tutor)

```
┌──────────────────────────────┐
│  Class Ended                 │
│  ──────────────────────────  │
│  Name this recording before  │
│  publishing to students      │
│                              │
│  ┌──────────────────────┐    │
│  │ Algebra — Chapter 5  │    │  ← pre-filled, editable
│  └──────────────────────┘    │
│                              │
│  Subject: Mathematics        │
│  Date: May 26, 2026          │
│                              │
│  [Skip for Now]              │
│  [Save & Publish           ] │
└──────────────────────────────┘
```

Bottom sheet, slides up from bottom, drag handle at top.

---

### 5. Class Recordings

#### Recordings Library

```
┌──────────────────────────────┐
│ Recordings                   │
│ [Search recordings...]       │
│ [All][Maths][Science][Eng.]  │
├──────────────────────────────┤
│  ┌──────────────────────┐    │
│  │ [▶ Thumbnail]    MATH│    │  ← subject color badge
│  │ Algebra — Chapter 5  │    │
│  │ Mr. Fernando         │    │
│  │ May 24, 2026 • 1h 20m│    │
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ [▶ Thumbnail]     SCI│    │
│  │ Cell Biology Part 2  │    │
│  │ Ms. Perera           │    │
│  │ May 23, 2026 • 52min │    │
│  └──────────────────────┘    │
└──────────────────────────────┘
```

#### Recording Player Screen

- Full-screen landscape video player
- Controls: play/pause, seek bar, volume, quality selector, fullscreen
- Portrait mode below player: lesson name, subject chip, tutor name, date
- Related recordings list at bottom (horizontal scroll)

---

### 6. AI Academic Assistant

#### AI Chat Screen

```
┌──────────────────────────────┐
│ ✦ AI Tutor          #1A3A6E │
│ [All][Maths][Science][Eng.]  │
├──────────────────────────────┤
│                              │
│      ┌──────────────────┐    │
│      │ What is the      │    │  ← student msg, blue bg, right
│      │ derivative of x²?│    │
│      └──────────────────┘    │
│                              │
│  [✦]┌────────────────────┐   │
│     │ Great question!    │   │  ← AI msg, grey bg, left
│     │ The derivative of  │   │
│     │ x² is 2x.          │   │
│     │                    │   │
│     │ Step-by-step:      │   │
│     │ 1. Apply power rule│   │
│     │ 2. d/dx(xⁿ) = nxⁿ⁻¹│   │
│     │ 3. d/dx(x²) = 2x  │   │
│     └────────────────────┘   │
│                              │
│  AI answers are guidance     │
│  only. Verify with tutor.    │
├──────────────────────────────┤
│  [📷]  Ask a question...  [→]│
└──────────────────────────────┘
```

- Student bubbles: right-aligned, `#2E6BC4` bg, white text, 16px radius (top-right 4px)
- AI bubbles: left-aligned, `#F1F5F9` bg, `#1E293B` text, 16px radius (top-left 4px)
- AI avatar: small `✦` sparkle in `#1A3A6E` circle, 28px, left of AI bubble
- Step-by-step: numbered list with clear line breaks
- Image upload: opens camera/gallery for textbook photo upload
- Disclaimer: small grey bar above input, always visible
- AI-007 compliance: declines non-academic queries with "I can only help with academic questions"

---

### 7. Test Marks & Notes

#### My Marks Screen (Student)

```
┌──────────────────────────────┐
│ My Marks                     │
│ [All][Maths][Science][Eng.]  │
├──────────────────────────────┤
│  Mathematics Mid-Term        │
│  May 20, 2026                │
│  ┌──────────────────────┐    │
│  │  85 / 100    Grade A │    │
│  │  ████████████████░░░ │    │
│  └──────────────────────┘    │
│  ─────────────────────────── │
│  Science Chapter Test        │
│  May 15, 2026                │
│  ┌──────────────────────┐    │
│  │  72 / 100    Grade B+│    │
│  │  ██████████████░░░░░ │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Performance Trend           │
│  [Line chart — last 5 exams] │
└──────────────────────────────┘
```

- Grade badge: A+ (dark green), B (blue), C (amber), D/F (red)
- Progress bar fill matches grade color
- Line chart: simple sparkline for score trend over time

#### Notes Repository Screen

```
┌──────────────────────────────┐
│ Study Notes                  │
│ [Maths][Science][English]    │
├──────────────────────────────┤
│  Lesson: Algebra Chapter 5   │
│  ──────────────────────────  │
│  [PDF] Algebra Notes.pdf     │
│  May 24 • 2.4 MB   [↓]      │
│                              │
│  [IMG] Formula Sheet.png     │
│  May 24 • 840 KB   [↓]      │
│  ─────────────────────────── │
│  Lesson: Quadratic Equations │
│  ──────────────────────────  │
│  [DOC] Practice Problems.doc │
│  May 20 • 1.1 MB   [↓]      │
└──────────────────────────────┘
```

- File type icon: PDF (red), DOCX (blue), image (green)
- Download button saves to device downloads folder

---

### 8. Fee Management

#### Fee Status Screen (Student/Parent)

```
┌──────────────────────────────┐
│ Fee Status                   │
├──────────────────────────────┤
│  ┌──────────────────────┐    │
│  │  May 2026            │    │
│  │                      │    │
│  │  OUTSTANDING         │    │  ← amber if unpaid, green if paid
│  │  LKR 5,000           │    │
│  │                      │    │
│  │  Due: May 31, 2026   │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Payment History             │
│  ──────────────────────────  │
│  Apr 2026  LKR 5,000  ● Paid │
│  Mar 2026  LKR 2,000  ● Part.│  ← partial amber
│  Feb 2026  LKR 5,000  ● Paid │
│  Jan 2026  LKR 5,000  ● Paid │
└──────────────────────────────┘
```

#### Fee Management Screen (Admin/Tutor)

```
┌──────────────────────────────┐
│ Fee Management  [May 2026 ▼] │
│ [Search student...]          │
│ [All][Paid][Unpaid][Partial] │
├──────────────────────────────┤
│  Aiden Perera    ● Paid      │
│  Grade 10        LKR 5,000   │
│                  [View]      │
│  ─────────────────────────── │
│  Bianca Silva    ● Partial   │
│  Grade 11        LKR 5,500   │
│                  [Update]    │
│  ─────────────────────────── │
│  Carlos Mendes   ● Unpaid    │
│  Grade 10        LKR 5,000   │
│  [Remind] [Mark Paid]        │
└──────────────────────────────┘
```

---

### 9. Online Examination System

#### Exam List Screen (Student)

```
┌──────────────────────────────┐
│ Exams                        │
│ [Upcoming][Active][Completed]│
├──────────────────────────────┤
│  ● ACTIVE NOW                │
│  ┌──────────────────────┐    │
│  │ Mathematics Mid-Term │    │
│  │ Ends in: 00:44:32    │    │
│  │ Grade 10 • 100 marks │    │
│  │    [Continue Exam →] │    │  ← green CTA
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Upcoming                    │
│  Physics Chapter 4           │
│  Jun 2 • 9:00 AM • 60 min   │
│  Starts in 6 days            │
│  ─────────────────────────── │
│  English Essay Test          │
│  Jun 5 • 10:00 AM • 90 min  │
│  Starts in 9 days            │
├──────────────────────────────┤
│  Completed                   │
│  Bio Mock Exam — May 20      │
│  Score: 78/100 — Grade B+   │
│  [View Results]              │
└──────────────────────────────┘
```

#### Exam Taking Screen

```
┌──────────────────────────────┐
│ Mathematics Mid-Term  00:44  │  ← timer red when < 10min
│ Q 3 of 8                     │
│ ████████░░░░░░░░░░░░░         │
├──────────────────────────────┤
│                              │
│  What is the derivative      │
│  of f(x) = x³ + 2x?         │
│                              │
│  ┌──────────────────────┐    │
│  │ ○  A) 3x² + 2        │    │
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ ○  B) x² + 2x        │    │
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ ●  C) 3x² + 2  ✓     │    │  ← selected = blue filled
│  └──────────────────────┘    │
│  ┌──────────────────────┐    │
│  │ ○  D) 3x³            │    │
│  └──────────────────────┘    │
│                              │
│  [⚑ Flag]                   │
├──────────────────────────────┤
│  [← Prev]  [Q Grid]  [Next→]│
└──────────────────────────────┘
```

**Anti-cheat overlay (when focus lost):**
```
┌──────────────────────────────┐
│  ⚠ Warning                   │
│  You left the exam screen.   │
│  This has been recorded.     │
│  Return to exam immediately. │
│  [Return to Exam]            │
└──────────────────────────────┘
```

**Question Grid:**
```
┌──────────────────────────────┐
│ Question Navigator        [✕]│
│                              │
│  [1✓][2✓][3●][4 ][5 ]       │  ← green=answered, blue=current
│  [6 ][7⚑][8 ]               │  ← amber=flagged, grey=unanswered
│                              │
│  ✓ Answered: 3               │
│  ○ Unanswered: 4             │
│  ⚑ Flagged: 1                │
│                              │
│  [Submit Exam]               │
└──────────────────────────────┘
```

#### Exam Results Screen

```
┌──────────────────────────────┐
│ ← Mathematics Mid-Term       │
│ Results — May 26, 2026       │
├──────────────────────────────┤
│  ┌──────────────────────┐    │
│  │       85 / 100       │    │  ← count-up animation on load
│  │       Grade A        │    │
│  │       ✓ PASSED       │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Q1  ✓  Correct    10/10    │
│  Q2  ✓  Correct    10/10    │
│  Q3  ✗  Incorrect   0/10    │  ← red, shows correct answer
│  Q4  ✓  Correct    10/10    │
│  Q5  ~  Partial    15/20    │  ← amber for partial
├──────────────────────────────┤
│  Tutor Feedback              │
│  "Good work on algebra.      │
│  Review integration rules."  │
└──────────────────────────────┘
```

---

### 10. Class Calendar & Scheduling

#### Calendar Screen

```
┌──────────────────────────────┐
│ Calendar       [Week][Month] │
│                              │
│  ← May 2026 →               │
│  Mo Tu We Th Fr Sa Su        │
│                          1   │
│   2   3  4   5  6   7   8   │
│   9  10 11  12 13  14  15   │  ← blue dot = class, amber = exam
│  16  17 18  19 20  21  22   │
│  23  24 25 [26] 27  28  29  │  ← today = #1A3A6E circle
│  30  31                     │
├──────────────────────────────┤
│  May 26 — Monday             │
│  ──────────────────────────  │
│  09:00  📘 Mathematics       │
│         Mr. Fernando         │
│         [Join Class]         │
│  11:00  🔬 Science           │
│         Ms. Perera           │
│         [Join Class]         │
│  14:00  📝 Physics Exam      │
│         60 min • 100 marks   │
│         [View Exam]          │
└──────────────────────────────┘
```

- Class dot: `#2E6BC4`
- Exam dot: `#F59E0B`
- Cancelled: `#DC2626` strikethrough
- Event detail bottom sheet on day tap

---

### 11. Parent Portal

#### Parent Dashboard

```
┌──────────────────────────────┐
│ [Aiden][Bianca]              │  ← child switcher chips
│ Monitoring Aiden Perera      │
│                         [🔔] │
├──────────────────────────────┤
│  Attendance                  │
│  ┌──────────────────────┐    │
│  │   [Donut 94%]        │    │  ← green/red/amber segments
│  │   22 Present         │    │
│  │   1 Absent  1 Late   │    │
│  └──────────────────────┘    │
├──────────────────────────────┤
│  Latest Marks                │
│  Mathematics  85/100    A    │
│  Science      78/100    B+   │
│  English      91/100    A+   │
├──────────────────────────────┤
│  Upcoming Exams              │
│  Physics — Jun 2 — 9:00 AM   │
├──────────────────────────────┤
│  Fee Status                  │
│  ⚠ LKR 5,000 Outstanding    │  ← amber card
│  May 2026 — Due May 31       │
└──────────────────────────────┘
```

#### Link Child Screen

```
┌──────────────────────────────┐
│ ← Link a Student             │
├──────────────────────────────┤
│  Enter your child's          │
│  Student Code provided by    │
│  the tuition center          │
│                              │
│  ┌──────────────────────┐    │
│  │  STU-2024-001        │    │  ← large, uppercase auto-format
│  └──────────────────────┘    │
│                              │
│  [    Link Student         ] │
│                              │
│  ─────── Linked Students ─── │
│  Aiden Perera  Grade 10 [✕] │
│  Bianca Silva  Grade 8  [✕] │
└──────────────────────────────┘
```

---

## Global UI Components

### Status Badges

| Status | Background | Text Color | Icon |
|---|---|---|---|
| Present / Paid / Pass | `#DCFCE7` | `#16A34A` | ✓ check |
| Absent / Unpaid / Fail | `#FEE2E2` | `#DC2626` | ✕ |
| Late / Partial / Pending | `#FEF3C7` | `#D97706` | ⚑ |
| Scheduled / Info | `#EFF6FF` | `#2E6BC4` | 📅 |

### Button Variants

| Variant | Background | Text | Border |
|---|---|---|---|
| Primary | `#1A3A6E` | White | — |
| Secondary | `#E8F0FB` | `#2E6BC4` | — |
| Danger | `#DC2626` | White | — |
| Ghost | Transparent | `#2E6BC4` | `1.5px #2E6BC4` |

All buttons: 10px radius, 52px height, ripple/splash on press.

### Toast Notifications

- Success: dark green bg, white text + check icon, slide-in from bottom
- Error: dark red bg, white text + X icon
- Warning: dark amber bg, white text + alert icon
- Auto-dismiss after 3 seconds

### Empty States

- Centered: icon (48px, grey line style) + heading (16px bold) + subtext (13px grey) + optional CTA button
- Used on all empty list screens

### Loading States

- Skeleton shimmer cards (grey animated gradient)
- Never use spinner alone for list content
- Pull-to-refresh on all scrollable list screens

### Bottom Sheets

- White bg, 20px top radius
- Drag handle: 36px wide, 4px tall, `#CBD5E1`, centered at top, 8px from top
- Backdrop: `rgba(0,0,0,0.4)`, tap to dismiss

---

## Animations & Transitions

| Trigger | Animation |
|---|---|
| Page push | Slide from right (300ms ease-out) |
| Bottom sheet | Slide up (250ms spring) |
| FAB appear | Scale in from 0.8 (200ms) |
| Chart data load | Animate in (300ms ease-out) |
| Attendance recognized | Green pulse on face frame |
| Exam submit | Confetti micro-animation |
| Timer < 10 min | Red pulse every second |
| Score reveal | Count-up from 0 to final |
| Toggle switch | Smooth slide (150ms) |

---

## Accessibility

- Minimum touch target: 44 × 44px on all interactive elements
- All text passes WCAG AA contrast ratio minimum
- Support dynamic font size (system accessibility settings)
- Haptic feedback: button press, attendance mark, exam submit
- Screen reader labels on all icon-only buttons
- RTL layout structure prepared (even if not activated initially)

---

## Recommended Tech Stack

| Layer | Technology |
|---|---|
| Framework | Flutter (Dart) — single codebase iOS & Android |
| State Management | Riverpod or BLoC |
| Navigation | GoRouter |
| HTTP Client | Dio |
| Local Storage | Hive / SharedPreferences |
| Secure Storage | flutter_secure_storage (JWT tokens) |
| Camera / Face | camera + Google ML Kit Face Detection |
| Video Player | video_player + chewie |
| Charts | fl_chart |
| Calendar | table_calendar |
| Push Notifications | firebase_messaging |
| File Handling | file_picker + open_filex |
| Image Upload | image_picker |
| PDF Viewer | flutter_pdfview |

---

## Folder Structure

```
lib/
  main.dart
  app/
    router.dart                    ← GoRouter config (role-based routes)
    theme.dart                     ← colors, typography, component themes
  features/
    auth/
      login_screen.dart
      face_registration_screen.dart
    home/
      student_home_screen.dart
      tutor_home_screen.dart
      parent_home_screen.dart
    attendance/
      facial_recognition_screen.dart
      manual_attendance_screen.dart
      attendance_history_screen.dart
    classes/
      class_list_screen.dart
      recording_confirmation_sheet.dart
    recordings/
      recordings_library_screen.dart
      recording_player_screen.dart
    ai_chat/
      ai_chat_screen.dart
      chat_history_screen.dart
    marks/
      marks_screen.dart
      notes_screen.dart
    fees/
      fee_status_screen.dart
      fee_management_screen.dart
    exams/
      exam_list_screen.dart
      exam_taking_screen.dart
      exam_results_screen.dart
      question_grid_sheet.dart
    calendar/
      calendar_screen.dart
    parent/
      parent_dashboard_screen.dart
      link_child_screen.dart
  shared/
    widgets/
      stat_card.dart
      status_badge.dart
      avatar_widget.dart
      empty_state.dart
      loading_skeleton.dart
      bottom_sheet_handle.dart
      primary_button.dart
      toast_notification.dart
    models/
      student.dart
      attendance.dart
      exam.dart
      fee.dart
      recording.dart
    services/
      auth_service.dart
      attendance_service.dart
      exam_service.dart
      ai_chat_service.dart
      fee_service.dart
```

---

## API Contract (Mobile ↔ Backend)

### Authentication
```
POST  /api/auth/login              → { token, role, user }
POST  /api/auth/logout
POST  /api/auth/face/register      → upload face photos
POST  /api/auth/face/verify        → match face, return student info
```

### Attendance
```
GET   /api/attendance/:classId     → student roster
POST  /api/attendance              → submit attendance records
GET   /api/attendance/student/:id  → history by student
```

### Classes & Recordings
```
GET   /api/classes                 → list by role
GET   /api/classes/:id/join        → join link
GET   /api/recordings              → list by class
POST  /api/recordings/:id/confirm  → set lesson name, publish
```

### AI Chat
```
POST  /api/ai/chat                 → { message, subjectId } → { reply }
GET   /api/ai/chat/history         → past conversations
POST  /api/ai/chat/image           → upload question image → { reply }
```

### Exams
```
GET   /api/exams                   → list by role/status
GET   /api/exams/:id               → exam detail + questions
POST  /api/exams/:id/submit        → submit answers
GET   /api/exams/:id/results       → results for student
```

### Fees
```
GET   /api/fees/student/:id        → fee history
POST  /api/fees/payment            → record payment (tutor/admin)
```

### Calendar
```
GET   /api/calendar                → events by date range
```

---

*TuitionSmart Mobile App — Frontend Development Prompt | Version 1.0 | May 2026*
