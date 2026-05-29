# TuitionSmart — Teacher Dashboard (Next.js)
## Part 1: Student Management + Fee Report

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
| Tables | TanStack Table |
| Charts | Recharts |
| Modals | Radix UI Dialog (via shadcn) |
| Notifications | Sonner (toast) |
| State | Zustand |

---

## Design Tokens (Tailwind Config)

```ts
// tailwind.config.ts
colors: {
  brand: {
    navy:    '#1A3A6E',  // primary dark blue
    blue:    '#2E6BC4',  // accent blue
    light:   '#E8F0FB',  // light blue bg
  },
  status: {
    success: '#16A34A',
    danger:  '#DC2626',
    warning: '#D97706',
    info:    '#2E6BC4',
  },
  neutral: {
    900: '#1E293B',
    500: '#64748B',
    200: '#E2E8F0',
    100: '#F1F5F9',
  }
}
```

---

## Global Layout

### File: `app/(teacher)/layout.tsx`

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar (260px fixed)    │   Main Content Area          │
│  ┌───────────────────┐    │   ┌──────────────────────┐   │
│  │ TuitionSmart logo │    │   │  Top Bar             │   │
│  │ ─────────────── │    │   │  [Breadcrumb] [Bell] [Avatar] │
│  │ Dashboard        │    │   ├──────────────────────┤   │
│  │ My Classes       │    │   │                      │   │
│  │ Students ◄ active│    │   │   Page Content       │   │
│  │ Attendance       │    │   │                      │   │
│  │ Marks & Notes    │    │   │                      │   │
│  │ Fee Report       │    │   │                      │   │
│  │ Exams            │    │   │                      │   │
│  │ Analytics        │    │   │                      │   │
│  │ ─────────────── │    │   │                      │   │
│  │ Settings         │    │   │                      │   │
│  │ Logout           │    │   └──────────────────────┘   │
│  └───────────────────┘    │                              │
└─────────────────────────────────────────────────────────┘
```

**Sidebar specs:**
- Background: `#1A3A6E`
- Logo area: 64px height, white "TuitionSmart" text + cap icon
- Nav items: 44px height, 12px horizontal padding, 8px border-radius
- Active item: `#2E6BC4` background, white text, left border 3px white
- Inactive item: `rgba(255,255,255,0.6)` text, hover `rgba(255,255,255,0.1)` bg
- Divider: `rgba(255,255,255,0.15)`
- Collapsed state (mobile): icon-only 64px width

**Top bar specs:**
- Height: 64px
- Background: `#FFFFFF`
- Bottom border: `1px solid #E2E8F0`
- Left: breadcrumb (page title + parent)
- Right: notification bell (badge count) + avatar dropdown

---

---

# Section 1: Student Management

## Route: `/teacher/students`

---

### Page: Student List

**File:** `app/(teacher)/students/page.tsx`

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Students                                    [+ Add Student]  │
│  Manage your enrolled students                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 48          │  │ 92%         │  │ 3           │         │
│  │ Total       │  │ Avg Attend. │  │ At Risk     │         │
│  │ Students    │  │ This Month  │  │ (< 75%)     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  [Search students...]  [Class ▼]  [Status ▼]  [Export CSV]  │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ☐  Avatar  Name          Class    Attend.  Status  ⋮   │ │
│  │ ☐  [A]    Aiden Perera   Grade 10  95%    Active   ⋮   │ │
│  │ ☐  [B]    Bianca Silva   Grade 11  78%    Active   ⋮   │ │
│  │ ☐  [C]    Carlos Mendes  Grade 10  62%    At Risk  ⋮   │ │
│  │ ☐  [D]    Diana Raj      Grade 12  88%    Active   ⋮   │ │
│  └─────────────────────────────────────────────────────────┘ │
│  Showing 1–20 of 48    [← Prev]  1  2  3  [Next →]          │
└──────────────────────────────────────────────────────────────┘
```

#### Component Breakdown

**Stats Cards Row**

```tsx
// components/students/StudentStatsRow.tsx
interface StatCard {
  label: string
  value: string | number
  icon: LucideIcon
  color: 'blue' | 'green' | 'red' | 'amber'
  trend?: { value: number; label: string }
}
```

- Card: white bg, 12px radius, `shadow-sm`, 20px padding
- Icon circle: 40px, colored bg at 10% opacity, colored icon
- Value: 28px, bold, `#1E293B`
- Label: 13px, `#64748B`
- Trend: small arrow + % text, green if positive

**Student Table**

```tsx
// components/students/StudentTable.tsx
columns: [
  { id: 'select', header: Checkbox, cell: Checkbox },
  { id: 'name', header: 'Name', cell: AvatarNameCell },
  { id: 'studentId', header: 'ID' },
  { id: 'class', header: 'Class' },
  { id: 'attendance', header: 'Attendance', cell: AttendanceBadge },
  { id: 'status', header: 'Status', cell: StatusBadge },
  { id: 'actions', header: '', cell: ActionsMenu },
]
```

**AvatarNameCell:**
- 32px avatar circle (initials, colored bg based on name hash)
- If photo uploaded: show photo
- Name in bold 14px, student email below in 12px grey

**AttendanceBadge:**
- `>= 90%`: `bg-green-100 text-green-700`
- `75–89%`: `bg-amber-100 text-amber-700`
- `< 75%`: `bg-red-100 text-red-700` + warning icon

**StatusBadge:**
- Active: `bg-green-50 text-green-700 border border-green-200`
- Inactive: `bg-gray-100 text-gray-500`
- At Risk: `bg-red-50 text-red-700 border border-red-200`

**ActionsMenu (⋮ dropdown):**
- View Profile
- Edit Student
- View Attendance
- View Marks
- Send Message
- Deactivate

**Filter Bar:**
- Search: input with search icon, `placeholder="Search by name or ID..."`
- Class filter: `Select` dropdown — All Classes / Grade 10 / Grade 11 / Grade 12
- Status filter: `Select` dropdown — All / Active / At Risk / Inactive
- Export: ghost button with Download icon

**Bulk Actions Bar (shown when rows selected):**
- Slides in from bottom, fixed position
- Shows: "X students selected" | [Send Notification] [Export Selected] [Deactivate]

---

### Page: Student Profile

**File:** `app/(teacher)/students/[studentId]/page.tsx`

```
┌──────────────────────────────────────────────────────────────┐
│  ← Students / Aiden Perera                                   │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────────┐│
│  │  [Avatar 80px]      │  │ Aiden Perera          [Edit]   ││
│  │  Aiden Perera       │  │ Student ID: STU-2024-001        ││
│  │  Grade 10 • Active  │  │ Class: Grade 10 Mathematics     ││
│  │                     │  │ Enrolled: Jan 2024              ││
│  │  [Send Message]     │  │ Parent: Mrs. Perera             ││
│  └─────────────────────┘  └─────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  [Attendance] [Marks] [Exams] [Fees] [Notes]  ← tabs        │
├──────────────────────────────────────────────────────────────┤
│  Tab content area (see below per tab)                        │
└──────────────────────────────────────────────────────────────┘
```

**Profile Header Card:**
- White bg, 12px radius, shadow-sm
- Left section (1/3): avatar (80px circle), name (20px bold), class + status badge
- Right section (2/3): detail grid — ID, Class, Enrolled Date, Parent Name
- Edit button: top-right, ghost style

**Tab: Attendance**
- Month selector (prev/next arrows + month-year label)
- Mini calendar heatmap:
  - 7-column grid (Mon–Sun)
  - Each day cell 36px: green (present), red (absent), amber (late), grey (no class)
  - Hover tooltip: "Present — Mathematics, May 12"
- Below calendar: attendance summary row
  - Present: X days | Absent: X days | Late: X days | Rate: XX%
- Detailed log table: Date | Class | Status | Marked By | Time

**Tab: Marks**
- Subject filter tabs
- Marks timeline: vertical list of assessments
  - Assessment name + date on left
  - Score bar (progress bar) in middle
  - Score value "85/100" + grade badge on right

**Tab: Exams**
- List of exams taken
- Columns: Exam Name | Date | Score | Grade | Status (Graded/Pending)

**Tab: Fees**
- Monthly fee status list (reuses FeeStatusList component)

**Tab: Notes**
- Files accessible to this student

---

### Modal: Add / Edit Student

**File:** `components/students/StudentFormModal.tsx`

```
┌─────────────────────────────────────────┐
│ Add New Student                     [✕] │
├─────────────────────────────────────────┤
│ Profile Photo                           │
│ [Upload Photo] or drag & drop           │
│                                         │
│ Full Name *          Student ID *       │
│ [_______________]    [_______________]  │
│                                         │
│ Date of Birth        Gender             │
│ [_______________]    [Select ▼]        │
│                                         │
│ Class / Grade *      Subject *          │
│ [Select ▼]           [Select ▼]        │
│                                         │
│ Parent Name          Parent Phone       │
│ [_______________]    [_______________]  │
│                                         │
│ Parent Email                            │
│ [_______________]                       │
│                                         │
│ Monthly Fee (LKR)    Fee Start Month    │
│ [_______________]    [_______________]  │
│                                         │
│ Notes (optional)                        │
│ [_______________________________]       │
│                                         │
│          [Cancel]  [Save Student]       │
└─────────────────────────────────────────┘
```

- Zod schema validation on all required fields
- Photo upload: `react-dropzone`, preview immediately
- Submit shows loading spinner in button, disables form
- On success: toast "Student added successfully", close modal, refetch table

---

---

# Section 2: Fee Report

## Route: `/teacher/fees`

---

### Page: Fee Overview

**File:** `app/(teacher)/fees/page.tsx`

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Fee Report                          [Month ▼] [Export PDF]  │
│  Track and manage student fee payments                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────┐│
│  │ LKR 124,500  │ │ LKR 98,000  │ │ LKR 26,500  │ │ 79% ││
│  │ Total Owed   │ │ Collected   │ │ Outstanding │ │Rate ││
│  └──────────────┘ └──────────────┘ └──────────────┘ └─────┘│
│                                                              │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │  Monthly Collection      │  │  Payment Status Split    │ │
│  │  [Bar chart]             │  │  [Donut chart]           │ │
│  │                          │  │  Paid 79% / Unpaid 21%   │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
│                                                              │
│  Student Fee Status                                          │
│  [Search...]  [Class ▼]  [Status ▼]  [Mark All Paid]        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Name         Class    Amount   Status      Action       │ │
│  │ Aiden Perera Grade 10 LKR 5000 ● Paid      [View]      │ │
│  │ Bianca Silva Grade 11 LKR 5500 ● Partial   [Update]    │ │
│  │ Carlos Mendes Grade10 LKR 5000 ● Unpaid    [Mark Paid] │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

#### Summary Cards

```tsx
// components/fees/FeeSummaryCards.tsx
const cards = [
  { label: 'Total Owed',    value: 'LKR 124,500', icon: Banknote,     color: 'blue'  },
  { label: 'Collected',     value: 'LKR 98,000',  icon: CheckCircle,  color: 'green' },
  { label: 'Outstanding',   value: 'LKR 26,500',  icon: AlertCircle,  color: 'red'   },
  { label: 'Collection Rate', value: '79%',        icon: TrendingUp,   color: 'amber' },
]
```

---

#### Bar Chart — Monthly Collection

```tsx
// components/fees/MonthlyCollectionChart.tsx
// Recharts BarChart
// X-axis: last 6 months (Jan, Feb, Mar...)
// Y-axis: LKR amount
// Two bars per month:
//   - Bar 1 (dark blue #1A3A6E): Total Expected
//   - Bar 2 (light blue #2E6BC4): Collected
// Legend below chart
// Tooltip: "March 2026 — Expected: LKR 124,500 | Collected: LKR 110,000"
// Chart height: 240px
```

---

#### Donut Chart — Payment Status Split

```tsx
// components/fees/PaymentStatusChart.tsx
// Recharts PieChart (donut — innerRadius 60, outerRadius 90)
// Segments:
//   - Paid:    #16A34A
//   - Partial: #D97706
//   - Unpaid:  #DC2626
// Center label: collection rate % (large text)
// Legend: right side, color dot + label + count
```

---

#### Fee Status Table

```tsx
// components/fees/FeeTable.tsx
columns: [
  { id: 'name',    header: 'Student',  cell: AvatarNameCell },
  { id: 'class',   header: 'Class' },
  { id: 'amount',  header: 'Amount',   cell: CurrencyCell },
  { id: 'paid',    header: 'Paid',     cell: CurrencyCell },
  { id: 'balance', header: 'Balance',  cell: BalanceCell },
  { id: 'status',  header: 'Status',   cell: FeeStatusBadge },
  { id: 'dueDate', header: 'Due Date' },
  { id: 'actions', header: '',         cell: FeeActionCell },
]
```

**FeeStatusBadge:**
- Paid:    `bg-green-50 text-green-700 border-green-200` + check icon
- Partial: `bg-amber-50 text-amber-700 border-amber-200` + half icon
- Unpaid:  `bg-red-50 text-red-700 border-red-200` + x icon
- Overdue: `bg-red-100 text-red-800 border-red-300` + clock icon (bold)

**FeeActionCell:**
- Paid: [View Receipt] button (ghost)
- Partial: [Update Payment] button (amber outline)
- Unpaid: [Mark Paid] button (green filled) + [Send Reminder] icon button

---

### Drawer: Update Payment

**File:** `components/fees/UpdatePaymentDrawer.tsx`

Slides in from right (480px wide on desktop, full-screen on mobile)

```
┌─────────────────────────────────┐
│ ← Update Payment                │
│ Bianca Silva — May 2026         │
├─────────────────────────────────┤
│ Fee Amount: LKR 5,500           │
│ Previously Paid: LKR 2,000      │
│ Outstanding: LKR 3,500          │
│                                 │
│ Payment Type                    │
│ ○ Full Payment    ○ Partial     │
│                                 │
│ Amount Received (LKR) *         │
│ [_________________________]     │
│                                 │
│ Payment Date *                  │
│ [_________________________]     │
│                                 │
│ Payment Method                  │
│ [Cash ▼]                        │
│                                 │
│ Reference / Notes               │
│ [_________________________]     │
│                                 │
│ [Cancel]      [Save Payment]    │
├─────────────────────────────────┤
│ Payment History                 │
│ Mar 15 — LKR 2,000 — Cash      │
└─────────────────────────────────┘
```

- Payment type toggle affects amount field (full auto-fills outstanding amount)
- Payment history list at bottom (collapsible)
- On save: optimistic update in table, toast confirmation

---

### Page: Fee Detail Per Student

**File:** `app/(teacher)/fees/[studentId]/page.tsx`

```
┌──────────────────────────────────────────────────────────┐
│ ← Fee Report / Aiden Perera                              │
├──────────────────────────────────────────────────────────┤
│ [Student mini profile card — name, class, contact]       │
├──────────────────────────────────────────────────────────┤
│ Fee Summary: Total Paid | Total Owed | Last Payment Date │
├──────────────────────────────────────────────────────────┤
│ Month      Amount    Paid      Balance  Status     Action│
│ May 2026   5,000     5,000     0        ● Paid          │
│ Apr 2026   5,000     5,000     0        ● Paid          │
│ Mar 2026   5,000     2,000     3,000    ● Partial  [Upd]│
│ Feb 2026   5,000     0         5,000    ● Unpaid   [Pay]│
├──────────────────────────────────────────────────────────┤
│ [+ Add Fee Record]              [Download Statement]     │
└──────────────────────────────────────────────────────────┘
```

- Clicking a paid month shows payment receipt details in an accordion
- Download Statement: generates PDF with header, student info, monthly table, total

---

### Page: Fee Report Export

**File:** `components/fees/ExportReportModal.tsx`

```
┌────────────────────────────────────┐
│ Export Fee Report              [✕] │
├────────────────────────────────────┤
│ Report Type                        │
│ ○ Full Class Report                │
│ ○ Individual Student               │
│ ○ Outstanding Only                 │
│                                    │
│ Class / Grade                      │
│ [All Classes ▼]                    │
│                                    │
│ Period                             │
│ [May 2026 ▼]  to  [May 2026 ▼]   │
│                                    │
│ Format                             │
│ ○ PDF   ○ CSV   ○ Excel            │
│                                    │
│ Include:                           │
│ ☑ Payment history breakdown        │
│ ☑ Outstanding balances             │
│ ☐ Student contact info             │
│                                    │
│       [Cancel]  [Generate Report]  │
└────────────────────────────────────┘
```

---

## Shared Components Used in Both Sections

### `components/ui/DataTable.tsx`
Generic TanStack Table wrapper with:
- Column sorting (click header)
- Pagination (10/20/50 per page selector)
- Row selection checkboxes
- Empty state slot
- Loading skeleton (5 shimmer rows)

### `components/ui/StatCard.tsx`
```tsx
interface StatCardProps {
  label: string
  value: string
  icon: LucideIcon
  color: 'blue' | 'green' | 'red' | 'amber'
  trend?: { direction: 'up' | 'down'; value: string }
  onClick?: () => void
}
```

### `components/ui/PageHeader.tsx`
```tsx
interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode   // buttons rendered top-right
  breadcrumb?: { label: string; href: string }[]
}
```

### `components/ui/EmptyState.tsx`
- Centered layout: icon (48px, grey) + heading + subtext + optional button
- Used in all empty tables and lists

---

## API Integration

### Student Management Endpoints

```ts
// lib/api/students.ts
GET    /api/teacher/students                  // list with filters
GET    /api/teacher/students/:id              // single profile
POST   /api/teacher/students                  // create
PUT    /api/teacher/students/:id              // update
DELETE /api/teacher/students/:id              // deactivate

GET    /api/teacher/students/:id/attendance   // attendance history
GET    /api/teacher/students/:id/marks        // marks history
GET    /api/teacher/students/:id/fees         // fee history
```

### Fee Endpoints

```ts
// lib/api/fees.ts
GET    /api/teacher/fees                      // list all with filters
GET    /api/teacher/fees/summary              // stats (total, collected, etc.)
GET    /api/teacher/fees/:studentId           // student fee history
POST   /api/teacher/fees/:studentId/payment   // record payment
PUT    /api/teacher/fees/:feeId               // update fee record
GET    /api/teacher/fees/export               // generate report (query params)
```

### React Query Hooks

```ts
// hooks/useStudents.ts
export const useStudents = (filters: StudentFilters) =>
  useQuery({ queryKey: ['students', filters], queryFn: () => fetchStudents(filters) })

export const useStudent = (id: string) =>
  useQuery({ queryKey: ['students', id], queryFn: () => fetchStudent(id) })

export const useCreateStudent = () =>
  useMutation({ mutationFn: createStudent, onSuccess: () => queryClient.invalidateQueries(['students']) })

// hooks/useFees.ts
export const useFees = (filters: FeeFilters) =>
  useQuery({ queryKey: ['fees', filters], queryFn: () => fetchFees(filters) })

export const useFeeSummary = (month: string) =>
  useQuery({ queryKey: ['fees', 'summary', month], queryFn: () => fetchFeeSummary(month) })

export const useRecordPayment = () =>
  useMutation({ mutationFn: recordPayment, onSuccess: () => queryClient.invalidateQueries(['fees']) })
```

---

## Folder Structure

```
app/
  (teacher)/
    students/
      page.tsx                    ← Student list
      [studentId]/
        page.tsx                  ← Student profile
    fees/
      page.tsx                    ← Fee overview
      [studentId]/
        page.tsx                  ← Student fee detail

components/
  students/
    StudentTable.tsx
    StudentStatsRow.tsx
    StudentFormModal.tsx
    StudentProfileHeader.tsx
    AttendanceTab.tsx
    MarksTab.tsx
  fees/
    FeeTable.tsx
    FeeSummaryCards.tsx
    MonthlyCollectionChart.tsx
    PaymentStatusChart.tsx
    UpdatePaymentDrawer.tsx
    ExportReportModal.tsx
  ui/
    DataTable.tsx
    StatCard.tsx
    PageHeader.tsx
    EmptyState.tsx
    StatusBadge.tsx

hooks/
  useStudents.ts
  useFees.ts

lib/
  api/
    students.ts
    fees.ts
  validations/
    student.schema.ts
    fee.schema.ts
```

---

*TuitionSmart — Teacher Dashboard Part 1 | Student Management + Fee Report | Next.js 14*
