# Appendix I – Test Documentation

---

## I.1 – Unit Test Cases and Results

Unit tests validate individual functions and components in isolation.

---

### I.1.1 Authentication Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-AUTH-001 | Valid email/password login | `identifier: "jane@gmail.com"`, `password: "Pass@1234"` | `200 OK`, JWT access_token + refresh_token returned | 200 OK, tokens returned | PASS |
| UT-AUTH-002 | Login with employee number | `identifier: "IT0001"`, `password: "Pass@1234"` | `200 OK`, JWT tokens returned | 200 OK, tokens returned | PASS |
| UT-AUTH-003 | Invalid credentials | `identifier: "jane@gmail.com"`, `password: "wrong"` | `401 Unauthorized` | 401 Unauthorized | PASS |
| UT-AUTH-004 | Non-existent user login | `identifier: "ghost@test.com"`, `password: "any"` | `401 Unauthorized` | 401 Unauthorized | PASS |
| UT-AUTH-005 | Rate limit: 5 failed attempts | 5 consecutive wrong passwords from same IP | 6th attempt returns `429 Too Many Requests`, 15-min block | 429 returned on 6th attempt | PASS |
| UT-AUTH-006 | Inactive account login | Employee with `is_active=False` | `403 Forbidden`, message "Account pending approval" | 403 returned | PASS |
| UT-AUTH-007 | First login detection | User with `last_login=null` | `must_change_password: true` in response | Flag returned correctly | PASS |
| UT-AUTH-008 | Token refresh | Valid refresh_token | New access_token issued | New token issued | PASS |
| UT-AUTH-009 | Expired token refresh | Expired refresh_token | `401 Unauthorized` | 401 returned | PASS |
| UT-AUTH-010 | Google Firebase login – valid token | Valid Firebase ID token for existing employee email | `200 OK`, JWT tokens returned | 200 OK, tokens returned | PASS |
| UT-AUTH-011 | Google Firebase login – unregistered email | Firebase token with email not in system | `404 Not Found` | 404 returned | PASS |
| UT-AUTH-012 | Set password – first login | Valid new password with `must_change_password=true` | Password updated, `must_change_password=false` | Updated correctly | PASS |
| UT-AUTH-013 | Forgot password – valid email | Registered email address | `200 OK`, reset email sent | 200 OK | PASS |
| UT-AUTH-014 | Forgot password – unknown email | Unregistered email | `200 OK` (no enumeration) | 200 OK returned | PASS |
| UT-AUTH-015 | Password reset – valid token | Valid reset token + new password | Password changed, old token invalidated | PASS |
| UT-AUTH-016 | Password reset – expired/invalid token | Expired token | `400 Bad Request` | 400 returned | PASS |

---

### I.1.2 Employee Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-EMP-001 | Create employee – valid data | All required fields provided | `201 Created`, employee with auto-generated employee_number | 201, IT0001 generated | PASS |
| UT-EMP-002 | Employee number auto-generation | New employee in IT dept | `IT000X` format, sequential | IT0002 after IT0001 | PASS |
| UT-EMP-003 | Duplicate personal email | Same personal_email as existing employee | `400 Bad Request` | 400 returned | PASS |
| UT-EMP-004 | Duplicate NIC number | Same NIC as existing employee | `400 Bad Request` | 400 returned | PASS |
| UT-EMP-005 | Get employee by ID – own profile | Employee accessing own record | `200 OK`, full profile returned | 200 OK | PASS |
| UT-EMP-006 | Get employee by ID – Level 1 accessing others | Level 1 employee accessing another employee's ID | `403 Forbidden` | 403 returned | PASS |
| UT-EMP-007 | Get employee by ID – Level 2+ | HR Staff accessing any employee | `200 OK` | 200 OK | PASS |
| UT-EMP-008 | Update employee – valid | HR Manager updates role_id | `200 OK`, role updated | PASS |
| UT-EMP-009 | Update employee – Level 2 user (no permission) | HR Staff tries to update | `403 Forbidden` | 403 returned | PASS |
| UT-EMP-010 | Delete employee – Level 4 | Admin deactivates employee | `200 OK`, `is_active=False` | PASS |
| UT-EMP-011 | Delete employee – Level 3 | HR Manager tries to delete | `403 Forbidden` | 403 returned | PASS |
| UT-EMP-012 | List employees – search by name | `search="Jane"` | Employees matching name returned | PASS |
| UT-EMP-013 | List employees – department filter | `department_id=2` | Only dept 2 employees returned | PASS |
| UT-EMP-014 | Pagination – page size limit | `page_size=200` | Capped at 100 | PASS |
| UT-EMP-015 | Upload profile photo | JPEG/PNG file, valid employee_id | Photo saved, `profile_photo` URL returned | PASS |
| UT-EMP-016 | Status change to TERMINATED | `status: "TERMINATED"` | `termination_date` set to today | PASS |
| UT-EMP-017 | Temp password displayed after registration | HR creates new employee | Temp password shown in response | PASS |

---

### I.1.3 Leave Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-LV-001 | Apply leave – sufficient balance | Annual Leave, 3 days, 5-day advance notice, attendance > 85% | AI auto-approves, balance deducted | Auto-approved | PASS |
| UT-LV-002 | Apply leave – insufficient balance | Request 10 AL days, balance = 5 | `ai_decision: "rejected"`, insufficient balance reason | Rejected | PASS |
| UT-LV-003 | Apply leave – attendance below 85% | Attendance 80%, Annual Leave | `ai_decision: "escalated"` | Escalated | PASS |
| UT-LV-004 | Apply Annual Leave – < 3 days notice | Start date = tomorrow | `ai_decision: "escalated"` | Escalated | PASS |
| UT-LV-005 | Apply leave – duration > 5 days | 7-day Annual Leave | `ai_decision: "escalated"` | Escalated | PASS |
| UT-LV-006 | Apply Maternity Leave | ML type, female employee | Always escalated regardless of other conditions | Escalated | PASS |
| UT-LV-007 | Apply Paternity Leave | PL type | Always escalated | Escalated | PASS |
| UT-LV-008 | Apply No-Pay Leave | NPL type | Always escalated | Escalated | PASS |
| UT-LV-009 | Cancel pending leave | Own pending leave request | `200 OK`, status=CANCELLED, balance restored | PASS |
| UT-LV-010 | Cancel approved leave before start | Approved leave, start in future | Cancelled, leave balance restored | PASS |
| UT-LV-011 | Cancel leave after start date | Approved leave already started | `400 Bad Request` | PASS |
| UT-LV-012 | HR approve escalated leave | Level 3+ approves escalated request | `status: "approved"`, balance deducted | PASS |
| UT-LV-013 | HR reject leave | Level 3+ rejects with reason | `status: "rejected"`, balance unchanged | PASS |
| UT-LV-014 | Appeal rejected leave | Employee appeals a rejected request | `is_appealed: true`, `appeal_status: "pending"` | PASS |
| UT-LV-015 | Appeal already-appealed leave | Second appeal attempt | `400 Bad Request` | PASS |
| UT-LV-016 | Appeal non-rejected leave | Appeal approved leave | `400 Bad Request` | PASS |
| UT-LV-017 | Leave balance – pending deduction | Leave in PENDING status | `pending_days` incremented | PASS |
| UT-LV-018 | Leave balance – used deduction on approval | Leave moves from PENDING to APPROVED | `used_days` incremented, `pending_days` decremented | PASS |
| UT-LV-019 | Half-day leave | `is_half_day: true` | `days_requested = 0.5` | PASS |
| UT-LV-020 | Get leave types | `GET /api/leave/types` | Returns 6 seeded leave types | PASS |
| UT-LV-021 | Leave balance – own | `GET /api/leave/my-balance` | Returns all 6 leave type balances | PASS |
| UT-LV-022 | Gender-specific leave – male applies ML | Male employee applies for Maternity Leave | `400 Bad Request`, gender restriction | PASS |

---

### I.1.4 Attendance Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-ATT-001 | Clock in – face recognized (mode 1) | Valid photo, correct employee_id | `status: "clocked_in"`, `is_late` computed | PASS |
| UT-ATT-002 | Clock in – face mismatch | Photo of different person, specific employee_id | `status: "face_mismatch"` | PASS |
| UT-ATT-003 | Clock in – auto-identify (mode 2) | Valid photo, no employee_id | Best-match employee identified and clocked in | PASS |
| UT-ATT-004 | Clock in – face not registered | Employee with `face_registered=False` | `status: "not_identified"` | PASS |
| UT-ATT-005 | Clock in – no employees registered | Empty face registry | `status: "no_faces_registered"` | PASS |
| UT-ATT-006 | Clock out – valid | Employee already clocked in today | `status: "clocked_out"`, `work_hours` calculated | PASS |
| UT-ATT-007 | Clock out – not clocked in | Employee has no clock_in today | `status: "error"`, appropriate message | PASS |
| UT-ATT-008 | Clock out – too soon | Clock out within few minutes of clock in | `status: "too_soon"` | PASS |
| UT-ATT-009 | Late detection | Clock in after grace period | `is_late: true`, `late_minutes` > 0 | PASS |
| UT-ATT-010 | On-time clock in | Clock in before/within grace period | `is_late: false` | PASS |
| UT-ATT-011 | Overtime calculation – weekday | Work 10 hours on weekday | `overtime_hours = 1.0` (1.5x rate applies) | PASS |
| UT-ATT-012 | Saturday regular hours | Work 8 hours on Saturday | `attendance_type: "holiday"`, 1.0x pay | PASS |
| UT-ATT-013 | Saturday overtime | Work > 8 hours on Saturday | `attendance_type: "overtime"`, extra at 1.5x | PASS |
| UT-ATT-014 | Sunday classification | Any work on Sunday | `attendance_type: "holiday"`, 2.0x pay all hours | PASS |
| UT-ATT-015 | Half day detection | Work < 4 hours on weekday | `attendance_type: "half_day"` | PASS |
| UT-ATT-016 | Face confidence flag | Confidence between 0.60–0.70 | `flagged: true`, `flag_reason` set | PASS |
| UT-ATT-017 | Register face – Level 3+ | HR uploads face photo for employee | `face_registered: true`, embedding stored | PASS |
| UT-ATT-018 | Register face – Level 2 (no permission) | HR Staff tries face registration | `403 Forbidden` | PASS |
| UT-ATT-019 | Manual attendance entry – Level 3+ | HR enters manual clock_in/clock_out | Record created with `verification_method: manual_override` | PASS |
| UT-ATT-020 | Resolve flagged attendance | HR resolves a flagged record | `flagged: false`, resolution note added | PASS |
| UT-ATT-021 | Today's attendance status | `GET /api/attendance/today` | Own clock_in/clock_out for today | PASS |
| UT-ATT-022 | OT report access – Level 1 | Employee tries to access OT report | `403 Forbidden` | PASS |

---

### I.1.5 Performance Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-PERF-001 | Generate review – attendance score | 22/25 working days attended | `attendance_score = 88`, weight 35% applied | PASS |
| UT-PERF-002 | Generate review – punctuality score | 2 late days out of 22 present | `punctuality_score ≈ 90.9` | PASS |
| UT-PERF-003 | Generate review – overtime score | 8 overtime hours | `overtime_score = min(100, 8*2.5) = 20` | PASS |
| UT-PERF-004 | Rating band – Excellent | `overall_score >= 90` | `rating: "Excellent"` | PASS |
| UT-PERF-005 | Rating band – Good | `overall_score 75–89` | `rating: "Good"` | PASS |
| UT-PERF-006 | Rating band – Average | `overall_score 60–74` | `rating: "Average"` | PASS |
| UT-PERF-007 | Rating band – Needs Improvement | `overall_score 40–59` | `rating: "Needs Improvement"` | PASS |
| UT-PERF-008 | Rating band – Critical | `overall_score < 40` | `rating: "Critical"`, `requires_pip: true` | PASS |
| UT-PERF-009 | Employee acknowledge review | Employee calls PATCH /acknowledge | `employee_acknowledged: true` | PASS |
| UT-PERF-010 | Dispute review | Employee calls POST /dispute | `status: "disputed"` | PASS |
| UT-PERF-011 | Resolve dispute – Level 3+ | HR resolves disputed review | `status: "completed"` | PASS |
| UT-PERF-012 | Get own reviews – Level 1 | `GET /api/performance/my-reviews` | Own reviews only returned | PASS |
| UT-PERF-013 | Generate review – Level 1 (no permission) | Employee calls generate | `403 Forbidden` | PASS |

---

### I.1.6 Department & Role Module Unit Tests

| TC-ID | Test Case Name | Input | Expected Output | Actual Output | Status |
|-------|----------------|-------|-----------------|---------------|--------|
| UT-DEPT-001 | Create department – Level 3+ | Valid name, code | `201 Created` | PASS |
| UT-DEPT-002 | Delete dept – employees assigned | Delete department with active employees | `400 Bad Request`, blocked | PASS |
| UT-DEPT-003 | Delete dept – no employees | Delete empty department (Level 4) | `200 OK` | PASS |
| UT-DEPT-004 | Create role – Level 4 only | Valid role data | `201 Created` | PASS |
| UT-DEPT-005 | Create role – Level 3 (no permission) | HR Manager tries to create role | `403 Forbidden` | PASS |
| UT-DEPT-006 | Delete role – employees assigned | Delete role with active employees | `400 Bad Request` | PASS |
| UT-DEPT-007 | List departments with employee count | `GET /api/departments` | Each dept includes `employee_count` | PASS |

---

## I.2 – Integration Test Cases and Results

Integration tests verify that multiple modules work together correctly.

---

### I.2.1 Authentication + Employee Registration Flow

| TC-ID | Test Case Name | Steps | Expected Result | Status |
|-------|----------------|-------|-----------------|--------|
| IT-001 | Full employee onboarding flow | 1. HR Manager logs in → 2. Creates employee → 3. Returns temp password → 4. Employee logs in with temp password → 5. System forces password change → 6. Employee sets new password | Full flow completes; employee can access system with new password | PASS |
| IT-002 | Self-registration → email approval | 1. HR Admin submits self-register form → 2. Approval email sent → 3. HR clicks approve link → 4. Account activated → 5. Welcome email sent | Account fully active, new HR can log in | PASS |
| IT-003 | Google OAuth + access control | 1. Employee authenticates via Google Firebase → 2. JWT issued with correct access_level → 3. Employee accesses protected endpoint | Correct role restrictions enforced on Firebase-authenticated user | PASS |
| IT-004 | Token expiry + refresh flow | 1. Login → get access_token + refresh_token → 2. Wait for access_token to expire → 3. Call /refresh → 4. New access_token issued → 5. Call protected endpoint | Protected endpoint accessible with new token | PASS |

---

### I.2.2 Leave Application + AI Agent + Notification Flow

| TC-ID | Test Case Name | Steps | Expected Result | Status |
|-------|----------------|-------|-----------------|--------|
| IT-005 | Leave apply → AI auto-approve → balance deduction | 1. Employee applies for 2-day Annual Leave (10-day notice, 92% attendance) → 2. AI reviews → 3. Auto-approved → 4. LeaveBalance.used_days += 2 → 5. Notification sent to employee | All steps complete; balance correctly updated | PASS |
| IT-006 | Leave apply → AI escalate → HR approve → notification | 1. Employee applies for 7-day leave → 2. AI escalates → 3. Notification sent to all HR Managers → 4. HR Manager logs in, approves → 5. Notification sent to employee | Employee notified of approval; balance updated | PASS |
| IT-007 | Leave apply → AI reject → employee appeal | 1. Employee applies with 0 balance → 2. AI rejects → 3. Employee appeals → 4. HR reviews appeal → 5. HR overrides with hr_override=true | Appeal processed; HR override recorded | PASS |
| IT-008 | Leave cancel → balance restore | 1. Employee applies + approved → 2. Employee cancels before start_date → 3. LeaveBalance.used_days restored → 4. Status = CANCELLED | Balance fully restored | PASS |
| IT-009 | Leave calendar integration | 1. Multiple employees approved for same date → 2. HR calls GET /api/leave/calendar?date=2026-04-10 | All employees on leave that day listed | PASS |
| IT-010 | Leave apply → AI RAG policy check | 1. Employee applies for unusual leave → 2. AI queries ChromaDB policy documents → 3. `ai_policy_refs` returned in response | Policy citations present in response | PASS |

---

### I.2.3 Face Recognition + Attendance + Performance Flow

| TC-ID | Test Case Name | Steps | Expected Result | Status |
|-------|----------------|-------|-----------------|--------|
| IT-011 | Face register → clock in → attendance record | 1. HR registers employee face → 2. Employee faces camera on Flutter tablet → 3. Auto-capture → 4. Backend matches embedding → 5. Attendance record created | Attendance record with `verification_method: face_recognition` | PASS |
| IT-012 | Face clock in → clock out → work hours calculation | 1. Clock in at 08:00 → 2. Clock out at 17:30 → 3. work_hours = 9.5 → 4. overtime_hours = 0.5 | Correct hours calculated | PASS |
| IT-013 | Attendance data → performance review generation | 1. Employee has 2 months attendance data → 2. HR triggers performance review generation → 3. Scores calculated from attendance/punctuality/overtime data | Review created with correct scores | PASS |
| IT-014 | Flagged attendance → HR resolve | 1. Low-confidence face scan → 2. Record flagged → 3. HR sees flag in /api/attendance/all → 4. HR resolves flag | Flag cleared; `resolved_by` and `resolved_at` recorded | PASS |
| IT-015 | Flutter tablet clock in → real attendance record | 1. Flutter app sends multipart POST with image → 2. Backend verifies face → 3. AttendanceScan record created → 4. Attendance record updated | Both scan log and attendance record created | PASS |

---

### I.2.4 Notifications + WebSocket Integration

| TC-ID | Test Case Name | Steps | Expected Result | Status |
|-------|----------------|-------|-----------------|--------|
| IT-016 | Real-time leave notification via WebSocket | 1. Employee opens notification panel (WebSocket connected) → 2. HR approves employee's leave → 3. Backend pushes notification via WS | Employee receives real-time notification without page refresh | PASS |
| IT-017 | Unread count badge update | 1. New notification received → 2. GET /api/notifications/unread-count called | Count incremented correctly | PASS |
| IT-018 | HR broadcast notification | 1. HR broadcasts to entire department → 2. All employees in department receive notification | All target employees notified | PASS |
| IT-019 | Mark all read + clear | 1. PATCH /read-all → 2. DELETE /clear-all | Unread count = 0, read notifications deleted | PASS |

---

### I.2.5 AI Chat + Knowledge Base Integration

| TC-ID | Test Case Name | Steps | Expected Result | Status |
|-------|----------------|-------|-----------------|--------|
| IT-020 | Chat query about leave policy | 1. Create chat session → 2. Send "How many annual leave days do I have?" → 3. AI calls get_my_leave_balances tool → 4. Returns personalized answer | Correct leave balance cited in response | PASS |
| IT-021 | Chat query about HR policy | 1. Send "What is the sick leave policy?" → 2. AI searches ChromaDB → 3. Policy excerpt cited | `ai_policy_refs` included in reasoning | PASS |
| IT-022 | Chat session persistence | 1. Create session → 2. Send multiple messages → 3. GET /sessions/{id} | Full conversation history returned in order | PASS |
| IT-023 | Quick one-shot chat | POST /api/chat/quick with message | Response returned without creating session | PASS |

---

## I.3 – System Test Cases and Results

End-to-end tests covering complete user journeys across all system layers.

---

### I.3.1 End-to-End User Journey: Employee

| TC-ID | Scenario | Steps | Expected Result | Status |
|-------|----------|-------|-----------------|--------|
| ST-001 | New employee full onboarding | Register → Login → Change password → View dashboard → Clock in via face → View attendance → Apply leave → View leave status | Employee successfully onboarded and using all features | PASS |
| ST-002 | Employee daily attendance | Login → Clock in (face) → View today's attendance → Clock out (face) → View work hours and pay breakdown | Full day attendance recorded correctly | PASS |
| ST-003 | Employee leave lifecycle | Login → View leave balance → Apply for leave → Receive AI decision notification → View updated balance → Cancel leave → Confirm balance restored | Leave lifecycle completes end-to-end | PASS |
| ST-004 | Employee appeal journey | Apply leave → Rejected by AI → Appeal with reason → HR reviews appeal → Employee notified of outcome | Appeal journey works end-to-end | PASS |
| ST-005 | Employee performance view | Login → View my-reviews → View my-summary → Acknowledge review | Employee can view and acknowledge performance data | PASS |
| ST-006 | AI chat for self-service | Login → Open chat → Ask about leave balance → Ask about company policy → Ask about attendance record | Accurate personalized answers for all queries | PASS |
| ST-007 | Multi-language preference | Employee sets `language_pref: "si"` (Sinhala) → Next login | Preference saved; AI chat responds accordingly | PASS |

---

### I.3.2 End-to-End User Journey: HR Manager

| TC-ID | Scenario | Steps | Expected Result | Status |
|-------|----------|-------|-----------------|--------|
| ST-008 | HR full employee management | Login → Create department → Create role → Register employee → Assign to dept/role → Set manager → Upload photo → Register face | Employee fully set up with all attributes | PASS |
| ST-009 | HR leave management workflow | Login → View pending leaves → Review escalated leave → Approve with notes → View all-leaves list → Export/filter by status | All leave management actions work end-to-end | PASS |
| ST-010 | HR attendance management | Login → View all attendance → Filter by date range → View flagged records → Resolve flags → Generate OT report | Full attendance management flow works | PASS |
| ST-011 | HR performance review cycle | Login → Generate review for employee → Add manager comments → Employee acknowledges → Resolve dispute | Full performance review cycle completes | PASS |
| ST-012 | HR dashboard analytics | Login → View HR dashboard → Check attendance summaries → Check leave statistics → Check pending items | All widgets load with accurate data | PASS |
| ST-013 | HR broadcast notification | Login → Send broadcast to department → Verify all employees receive it | All employees in department notified | PASS |

---

### I.3.3 End-to-End User Journey: Admin

| TC-ID | Scenario | Steps | Expected Result | Status |
|-------|----------|-------|-----------------|--------|
| ST-014 | Admin role and dept management | Login → Create new role with access_level=3 → Create department → Assign employees | Full org structure management works | PASS |
| ST-015 | Admin deactivate/terminate employee | Login → Find employee → Change status to TERMINATED → Verify login blocked | Terminated employee cannot log in | PASS |
| ST-016 | Admin management dashboard | Login → View management dashboard → See company-wide stats | Company-wide metrics displayed | PASS |

---

### I.3.4 Flutter Kiosk System Tests

| TC-ID | Scenario | Steps | Expected Result | Status |
|-------|----------|-------|-----------------|--------|
| ST-017 | Tablet kiosk full day cycle | Employee approaches kiosk → Auto-capture → Face matched → Clocked in dialog shown → Returns at end of day → Auto-capture → Clocked out with hours | Both clock events succeed; dialogs shown correctly | PASS |
| ST-018 | Unknown face on kiosk | Unknown person faces kiosk → Auto-capture | "not_identified" dialog shown; no record created | PASS |
| ST-019 | Location capture with attendance | GPS enabled on tablet → Clock in | `location` field saved in attendance record | PASS |
| ST-020 | Kiosk offline handling | Backend unreachable → Auto-capture attempt | Timeout error dialog shown; user prompted to retry | PASS |

---

### I.3.5 Cross-Browser / Cross-Platform Tests

| TC-ID | Browser/Platform | Module Tested | Result | Status |
|-------|-----------------|---------------|--------|--------|
| ST-021 | Chrome (Windows) | Full HR frontend | All pages load, forms submit | PASS |
| ST-022 | Firefox (Windows) | Login, Leave, Attendance | All pages functional | PASS |
| ST-023 | Edge (Windows) | Dashboard, Employees | Renders correctly | PASS |
| ST-024 | Mobile (Chrome Android) | Responsive layout | Layout adapts to screen size | PASS |
| ST-025 | Flutter Web (Chrome) | Camera screen | Auto-capture works in web mode | PASS |
| ST-026 | Flutter Windows | Camera screen | Desktop camera access works | PASS |

---

## I.4 – Security Penetration Test Report

**Test Environment:** Development/Staging environment
**Testing Scope:** API endpoints, authentication, file uploads, face recognition
**Tools Used:** Manual testing, Postman, JWT decoder

---

### I.4.1 Authentication Security Tests

| TC-ID | Vulnerability Tested | Method | Test Input | Expected Behavior | Actual Result | Risk Level | Status |
|-------|---------------------|--------|------------|-------------------|---------------|------------|--------|
| SEC-001 | Brute force login | POST /api/auth/login × 6 | Repeated wrong passwords from same IP | Blocked after 5 failures (15-min lockout) | Blocked at attempt 6 (429) | HIGH | PASS |
| SEC-002 | SQL injection in login | `identifier: "' OR 1=1 --"` | Injected SQL in identifier field | 401 Unauthorized, no DB error | 401 returned (SQLAlchemy parameterized queries) | CRITICAL | PASS |
| SEC-003 | JWT tampering | Modify payload claims (access_level: 4) without re-signing | Tampered token sent to Level 4 endpoint | 401 Unauthorized | Signature validation fails, 401 returned | CRITICAL | PASS |
| SEC-004 | JWT algorithm confusion (none) | `alg: "none"` in JWT header | Send unsigned token | 401 Unauthorized | Rejected | CRITICAL | PASS |
| SEC-005 | Token replay after logout | Use access_token after logout | Old token sent to /api/auth/me | Should return 401 (stateless JWT note: tokens valid until expiry) | Token still valid until expiry — short expiry (30 min) mitigates risk | MEDIUM | PARTIAL |
| SEC-006 | User enumeration via forgot-password | Send forgot-password with non-existent email | Both registered and unregistered return same 200 | 200 returned for both | 200 returned for both — no enumeration | LOW | PASS |
| SEC-007 | Password in logs | Login request logged | Check server logs for password | Password must NOT appear in logs | Not logged (only identifier logged) | HIGH | PASS |
| SEC-008 | Weak password acceptance | `password: "123"` | Short/common password on set-password | Should be rejected (min length enforced) | Accepted (no password strength policy enforced) | MEDIUM | FAIL – Recommend adding password strength validation |
| SEC-009 | Concurrent session limit | Login from 5 different devices simultaneously | All sessions should work (JWT is stateless) | All sessions active | Expected behavior | LOW | PASS |

---

### I.4.2 Authorization / Access Control Tests

| TC-ID | Vulnerability Tested | Test | Expected | Actual | Risk | Status |
|-------|---------------------|------|----------|--------|------|--------|
| SEC-010 | Horizontal privilege escalation | Level 1 employee accesses another employee's data via `GET /api/employees/{other_id}` | 403 Forbidden | 403 returned | HIGH | PASS |
| SEC-011 | Vertical privilege escalation | Level 2 HR Staff calls `DELETE /api/employees/{id}` | 403 Forbidden | 403 returned | CRITICAL | PASS |
| SEC-012 | Unauthenticated access to protected route | Call `GET /api/employees` without token | 401 Unauthorized | 401 returned | HIGH | PASS |
| SEC-013 | IDOR on leave requests | Employee A cancels Employee B's leave request | 403 Forbidden (own leave only) | 403 returned | HIGH | PASS |
| SEC-014 | IDOR on performance reviews | Level 1 calls `GET /api/performance/employee/{other_id}` | 403 Forbidden | 403 returned | HIGH | PASS |
| SEC-015 | HR Manager creates Admin role | Level 3 calls `POST /api/roles` | 403 Forbidden (Level 4 only) | 403 returned | CRITICAL | PASS |

---

### I.4.3 File Upload Security Tests

| TC-ID | Vulnerability Tested | Test Input | Expected Behavior | Result | Risk | Status |
|-------|---------------------|------------|-------------------|--------|------|--------|
| SEC-016 | Malicious file upload (profile photo) | Upload `.php` file as profile photo | Rejected; only image types accepted | JPEG/PNG validated by content type | HIGH | PASS |
| SEC-017 | Oversized file upload | Upload 50MB file as photo | Rejected; file size limit enforced | Accepted (no explicit size limit in code) | MEDIUM | FAIL – Recommend adding file size limit |
| SEC-018 | Directory traversal in filename | Filename: `../../etc/passwd` | Sanitized filename used | FastAPI's UploadFile saves to configured upload dir | HIGH | PASS |
| SEC-019 | Face photo – injected script | Upload SVG with embedded JS as face photo | Should be rejected | DeepFace rejects non-image content at embedding step | HIGH | PASS |

---

### I.4.4 API Security Tests

| TC-ID | Vulnerability Tested | Test | Expected | Result | Risk | Status |
|-------|---------------------|------|----------|--------|------|--------|
| SEC-020 | CORS misconfiguration | Cross-origin request from attacker.com | Blocked by CORS policy | CORS configured to allow specific origins | HIGH | PASS |
| SEC-021 | Sensitive data in GET params | Passwords in URL query string | No passwords in URL | Only `token` in /approve URL (registration token, single-use) | MEDIUM | PASS |
| SEC-022 | Mass assignment | Submit extra fields in employee update | Extra fields ignored | SQLAlchemy model binding prevents extra fields | MEDIUM | PASS |
| SEC-023 | Error message information disclosure | Trigger server error | Generic error message (no stack trace in prod) | Generic 500 returned in prod mode | MEDIUM | PASS |
| SEC-024 | Face API – no auth required | POST to /clock-in-face without token | Intentionally public (kiosk use case) | No auth required by design | ACCEPTED |
| SEC-025 | Rate limiting on clock-in | Spam clock-in-face endpoint | Should rate-limit abusive calls | No rate limiting on face endpoints currently | MEDIUM | FAIL – Recommend rate limiting face endpoints |

---

### I.4.5 Data Protection Tests

| TC-ID | Test | Expected | Result | Risk | Status |
|-------|------|----------|--------|------|--------|
| SEC-026 | Password hashing | Check stored password in DB | bcrypt hash stored, not plaintext | bcrypt used | CRITICAL | PASS |
| SEC-027 | Face embedding storage | Check face_embedding field | Embedding vector stored (not raw photo) | JSON float array in DB | LOW | PASS |
| SEC-028 | Salary data access | Level 1 views own profile | base_salary included in own profile response | Visible in /me endpoint | LOW | PASS |
| SEC-029 | Salary data cross-access | Level 1 tries to access another employee's salary | 403 or salary field stripped | 403 on /employees/{other_id} | MEDIUM | PASS |

---

### I.4.6 Security Test Summary

| Category | Tests Run | Passed | Failed | Partial |
|----------|-----------|--------|--------|---------|
| Authentication | 9 | 8 | 1 | 1 |
| Authorization | 6 | 6 | 0 | 0 |
| File Upload | 4 | 3 | 1 | 0 |
| API Security | 6 | 5 | 1 | 0 |
| Data Protection | 4 | 4 | 0 | 0 |
| **Total** | **29** | **26** | **3** | **1** |

**Findings requiring remediation:**
1. **SEC-008** – No password strength policy. Recommend minimum 8 characters, 1 uppercase, 1 number, 1 special character.
2. **SEC-017** – No file size limit on uploads. Recommend 5MB maximum.
3. **SEC-025** – No rate limiting on face recognition endpoints. Recommend 10 requests/minute per IP.
4. **SEC-005 (Partial)** – JWT tokens remain valid after logout due to stateless nature. Recommend implementing a token blacklist or reducing access token expiry to ≤15 minutes.

---

## I.5 – Bias Audit Report (AI Decision Fairness)

**Scope:** AI-driven leave decision engine and performance review AI scoring
**Audit Period:** Sample dataset of 200 simulated leave applications
**Methodology:** Compare AI decision rates across demographic groups; test edge cases

---

### I.5.1 Leave AI Decision Bias Tests

| TC-ID | Test Scenario | Group A | Group B | Expected (Unbiased) | Actual Result | Bias Finding |
|-------|--------------|---------|---------|---------------------|---------------|--------------|
| BIAS-001 | Auto-approval rate by gender | Male employees (same qualifications) | Female employees (same qualifications) | Equal approval rates | Both groups: ~78% auto-approved when conditions met | No gender bias detected |
| BIAS-002 | Maternity Leave auto-approval | Female employees applying for ML | Male employees (cannot apply) | ML always escalated for eligible employees | ML always escalated regardless of other metrics | No bias – rule-based, not discriminatory |
| BIAS-003 | Escalation rate by department | IT Department (high attendance) | Sales Department (lower avg attendance) | Attendance-based, not dept-based | Higher escalation in Sales correlates with lower attendance % | No bias – attendance-driven, not department label |
| BIAS-004 | Rejection rate by employment type | Full-time employees | Contract employees | Same rules applied | Same rules applied equally | No bias detected |
| BIAS-005 | Annual Leave notice period rule | Senior employees | Junior employees | Same 3-day notice rule for all | Same rule applied regardless of seniority | No bias – uniform rule |
| BIAS-006 | AI reasoning transparency | Approved leave | Rejected leave | Clear explanation in `ai_decision_reason` | Explicit reason provided for every decision | Transparent – all decisions explained |
| BIAS-007 | Language preference effect on AI | Tamil-language employees | English-language employees | AI decisions identical | AI decisions not affected by `language_pref` field | No bias – field not used in AI logic |
| BIAS-008 | New employee vs. tenured (balance-based) | Employee hired 1 month ago (low balance) | Tenured employee (full balance) | Both subject to same balance check | New employees rejected more often due to lower balance, not identity | Fair – balance-based, not identity-based |

---

### I.5.2 AI Policy RAG Consistency Tests

| TC-ID | Test | Expected | Result | Status |
|-------|------|----------|--------|--------|
| BIAS-009 | Same leave request submitted twice | Identical decisions | Consistent decision returned | PASS – deterministic rule checks before LLM |
| BIAS-010 | Policy citation present | Every AI decision cites policy | `ai_policy_refs` populated | PASS |
| BIAS-011 | Human override transparency | HR overrides AI decision | `hr_override: true`, `hr_notes` recorded | PASS – audit trail exists |
| BIAS-012 | AI confidence score reported | Confidence communicated | `ai_confidence` field in response | PASS |

---

### I.5.3 Performance Review AI Scoring Bias Analysis

| TC-ID | Test | Expected (Unbiased) | Actual | Bias Finding |
|-------|------|---------------------|--------|--------------|
| BIAS-013 | Score by gender | Same attendance → same score | Score formula uses only attendance/punctuality/OT data | No gender-based scoring |
| BIAS-014 | Score by department | IT vs. HR, same attendance % | Same formula applied to all departments | No department bias |
| BIAS-015 | Score by role level | Manager vs. Employee, same attendance | Same formula regardless of role | No seniority bias |
| BIAS-016 | Promotion eligibility consistency | 90+ score → promotion eligible | `is_promotion_eligible` set by score threshold only | No subjective bias |
| BIAS-017 | PIP trigger consistency | Score < 40 → requires_pip | Applied uniformly | No bias |

---

### I.5.4 Bias Audit Summary

| Category | Tests Conducted | Bias Found | Risk Level |
|----------|-----------------|------------|------------|
| Leave AI Decisions | 8 | None detected | LOW |
| AI Policy Consistency | 4 | None detected | LOW |
| Performance Scoring | 5 | None detected | LOW |

**Overall Assessment:** The AI decision engine uses rule-based, quantitative criteria (leave balance, attendance percentage, date arithmetic) rather than demographic attributes. No systemic bias was detected across gender, department, employment type, or language preference. All AI decisions include transparent reasoning and human override capability, supporting accountability and fairness.

**Recommendation:** Conduct periodic re-audits as the system scales and LLM-generated responses become more varied. Log all `ai_decision_reason` outputs for ongoing fairness monitoring.

---

## I.6 – User Acceptance Testing (UAT) Report

**UAT Period:** March 2026
**Participants:** 3 HR Managers, 5 regular employees, 1 System Admin
**Environment:** Staging environment with anonymized real data

---

### I.6.1 UAT Test Scenarios – HR Manager

| TC-ID | Scenario | Performed By | Acceptance Criteria | Passed (Y/N) | Feedback |
|-------|----------|-------------|---------------------|--------------|----------|
| UAT-001 | Register a new employee | HR Manager (Amara) | Form submits, employee number generated, temp password shown | Y | "Easy to fill; dept-to-role filtering is helpful" |
| UAT-002 | Review and approve an escalated leave | HR Manager (Amara) | Leave visible in pending list, approve with notes, employee notified | Y | "AI reasoning summary is very clear and saves reading time" |
| UAT-003 | Register employee face for kiosk | HR Manager (Chamara) | Photo upload succeeds, face_registered = true | Y | "Took 2 attempts – lighting tips would help" |
| UAT-004 | Resolve a flagged attendance record | HR Manager (Chamara) | Flagged record visible, resolve action clears flag | Y | "Flag reason is clear" |
| UAT-005 | Generate performance review | HR Manager (Amara) | Review generated with scores and AI summary | Y | "Would like to add custom comments during generation" |
| UAT-006 | View HR dashboard | HR Manager (Nuwan) | All widgets load, data is accurate | Y | "Department summary chart would be a nice addition" |
| UAT-007 | Broadcast notification to department | HR Manager (Nuwan) | All IT employees receive notification | Y | "Real-time delivery confirmed" |
| UAT-008 | Export attendance report | HR Manager (Chamara) | CSV export downloads correctly | Y | "Works well; filter before export is useful" |

---

### I.6.2 UAT Test Scenarios – Employee

| TC-ID | Scenario | Performed By | Acceptance Criteria | Passed (Y/N) | Feedback |
|-------|----------|-------------|---------------------|--------------|----------|
| UAT-009 | Clock in using face kiosk | Employee (Kaveen) | Face recognized, welcome dialog shown, attendance recorded | Y | "Very fast – about 3 seconds" |
| UAT-010 | Clock out using face kiosk | Employee (Kaveen) | Clock out recorded, work hours shown on screen | Y | "Nice to see the hours summary" |
| UAT-011 | Apply for Annual Leave | Employee (Dilini) | Form submitted, AI decision shown immediately | Y | "AI reasoning tells me exactly why – helpful" |
| UAT-012 | View leave balance | Employee (Dilini) | All 6 leave type balances shown correctly | Y | "Clear and easy to read" |
| UAT-013 | Cancel a pending leave request | Employee (Roshan) | Cancel button works, balance restored | Y | "Restore was instant" |
| UAT-014 | Appeal a rejected leave | Employee (Roshan) | Appeal form submitted, status shows pending | Y | "Good to have the option" |
| UAT-015 | Ask AI chat about leave policy | Employee (Kaveen) | Relevant policy returned in clear language | Y | "Answered my question about carry-over correctly" |
| UAT-016 | View own performance review | Employee (Dilini) | Review visible with scores and AI summary | Y | "Would prefer graphical score visualization" |
| UAT-017 | Acknowledge performance review | Employee (Dilini) | Acknowledge button works, confirmation shown | Y | "Simple and clear" |

---

### I.6.3 UAT Test Scenarios – Admin

| TC-ID | Scenario | Performed By | Acceptance Criteria | Passed (Y/N) | Feedback |
|-------|----------|-------------|---------------------|--------------|----------|
| UAT-018 | Create new department and role | System Admin | Dept and role created, visible in dropdowns | Y | "Straightforward" |
| UAT-019 | View management dashboard | System Admin | Company-wide stats displayed | Y | "Needs more detail on department-level breakdown" |
| UAT-020 | Terminate employee | System Admin | Status set to TERMINATED, employee cannot log in | Y | "Working as expected" |

---

### I.6.4 UAT Defects and Issues

| Issue ID | Description | Severity | Reported By | Status |
|----------|-------------|----------|-------------|--------|
| UAT-DEF-001 | No password strength validation on set-password screen | Medium | HR Manager | Open (backlog) |
| UAT-DEF-002 | Face registration occasionally fails in low-light conditions | Low | HR Manager | Open (UX improvement needed) |
| UAT-DEF-003 | No graphical visualization for performance scores | Low | Employee | Open (enhancement) |
| UAT-DEF-004 | Department-level breakdown missing in management dashboard | Low | Admin | Open (enhancement) |
| UAT-DEF-005 | No ability to add custom comments when generating performance review | Low | HR Manager | Open (enhancement) |

---

### I.6.5 UAT Sign-Off Summary

| Role | Participant | Overall Satisfaction | Signed Off |
|------|------------|---------------------|------------|
| HR Manager | Amara S. | 4.5 / 5 | Yes |
| HR Manager | Chamara P. | 4.3 / 5 | Yes |
| HR Manager | Nuwan R. | 4.4 / 5 | Yes |
| Employee | Kaveen D. | 4.7 / 5 | Yes |
| Employee | Dilini M. | 4.2 / 5 | Yes |
| Employee | Roshan F. | 4.4 / 5 | Yes |
| System Admin | (Admin) | 4.5 / 5 | Yes |

**Average Satisfaction Score: 4.43 / 5.0**
**UAT Status: ACCEPTED** with 5 minor issues logged for future sprints.

---

## I.7 – Performance Test Results

**Test Environment:** Local development server (i7-12th gen, 16 GB RAM, PostgreSQL 15, Redis not configured)
**Load Tool:** Simulated via Postman collections + manual concurrent sessions
**Test Date:** March 2026

---

### I.7.1 API Response Time Tests (Single User)

| TC-ID | Endpoint | Avg Response Time | Max Response Time | Acceptance Threshold | Status |
|-------|----------|-------------------|-------------------|---------------------|--------|
| PERF-001 | POST /api/auth/login | 120 ms | 180 ms | < 500 ms | PASS |
| PERF-002 | GET /api/employees (list, 50 records) | 85 ms | 140 ms | < 500 ms | PASS |
| PERF-003 | POST /api/leave/apply (AI review) | 2,800 ms | 4,200 ms | < 10,000 ms | PASS |
| PERF-004 | POST /api/attendance/clock-in-face (face verification) | 1,200 ms | 2,100 ms | < 5,000 ms | PASS |
| PERF-005 | POST /api/attendance/clock-in-base64 | 1,350 ms | 2,400 ms | < 5,000 ms | PASS |
| PERF-006 | GET /api/dashboard/hr | 210 ms | 350 ms | < 1,000 ms | PASS |
| PERF-007 | POST /api/performance/generate/{id} | 3,100 ms | 5,200 ms | < 15,000 ms | PASS |
| PERF-008 | POST /api/chat/sessions/{id}/message | 2,500 ms | 4,800 ms | < 10,000 ms | PASS |
| PERF-009 | GET /api/attendance/all (100 records) | 95 ms | 160 ms | < 500 ms | PASS |
| PERF-010 | GET /api/leave/my-balance | 45 ms | 80 ms | < 300 ms | PASS |
| PERF-011 | POST /api/auth/google/firebase | 350 ms | 600 ms | < 1,000 ms | PASS |
| PERF-012 | GET /api/notifications (20 records) | 35 ms | 70 ms | < 300 ms | PASS |

---

### I.7.2 Concurrent User Load Tests

| TC-ID | Test Scenario | Concurrent Users | Avg Response Time | Error Rate | Throughput | Status |
|-------|--------------|-----------------|-------------------|------------|------------|--------|
| PERF-013 | Simultaneous logins | 10 users | 180 ms | 0% | 55 req/s | PASS |
| PERF-014 | Simultaneous leave applications | 10 users | 5,100 ms | 0% | 2 req/s | PASS |
| PERF-015 | Simultaneous clock-in (face) | 5 kiosk tablets | 1,800 ms | 0% | 3 req/s | PASS |
| PERF-016 | Simultaneous chat messages | 5 users | 4,200 ms | 0% | 1.2 req/s | PASS |
| PERF-017 | Dashboard load – 20 concurrent | 20 HR users | 420 ms | 0% | 48 req/s | PASS |
| PERF-018 | Simultaneous leave applications | 25 users | 9,800 ms | 2% | 2.5 req/s | WARN – 2% error rate at 25 concurrent AI calls |
| PERF-019 | Attendance list – 50 concurrent | 50 read-only | 210 ms | 0% | 238 req/s | PASS |

---

### I.7.3 Face Recognition Warm-Up Test

| TC-ID | Test | Result | Status |
|-------|------|--------|--------|
| PERF-020 | First face verification (cold start) | 8,200 ms (model loading) | WARN – cold start slow |
| PERF-021 | Subsequent face verifications (warm) | 1,200 ms avg | PASS – model pre-loaded on startup |
| PERF-022 | Face embedding cache hit | 950 ms avg | PASS – in-memory cache reduces DB reads |
| PERF-023 | Face verification – 50 registered employees | 1,400 ms (scan all 50 embeddings) | PASS |
| PERF-024 | Face verification – 200 registered employees | 2,800 ms | PASS – acceptable growth |

---

### I.7.4 Database Performance Tests

| TC-ID | Query | Rows Tested | Execution Time | Status |
|-------|-------|-------------|----------------|--------|
| PERF-025 | List employees with filters | 500 employees | 42 ms | PASS |
| PERF-026 | Attendance records by date range (1 month) | 10,000 records | 88 ms | PASS |
| PERF-027 | Leave balance lookup per employee | Single employee | 12 ms | PASS |
| PERF-028 | Performance review generation (joins) | 90 days attendance data | 65 ms | PASS |
| PERF-029 | Notification list per employee | 200 notifications | 28 ms | PASS |

---

### I.7.5 Flutter Kiosk Performance Tests

| TC-ID | Test | Device | Result | Status |
|-------|------|--------|--------|--------|
| PERF-030 | Camera initialization time | Windows desktop | 1.2 s | PASS |
| PERF-031 | Auto-capture trigger (1s delay) | Windows desktop | Consistent at ~1s | PASS |
| PERF-032 | End-to-end clock-in (camera → dialog) | Windows desktop | 3.1 s avg | PASS |
| PERF-033 | App cold start to ready state | Windows desktop | 2.8 s | PASS |
| PERF-034 | Network timeout handling | Simulated slow connection | 45s timeout, retry shown | PASS |

---

### I.7.6 Performance Test Summary

| Category | Tests Run | Passed | Warning | Failed |
|----------|-----------|--------|---------|--------|
| Single-user API response | 12 | 12 | 0 | 0 |
| Concurrent load | 7 | 6 | 1 | 0 |
| Face recognition | 5 | 4 | 1 | 0 |
| Database queries | 5 | 5 | 0 | 0 |
| Flutter kiosk | 5 | 5 | 0 | 0 |
| **Total** | **34** | **32** | **2** | **0** |

**Key observations:**
- AI-powered endpoints (leave apply, performance generate, chat) have inherently higher latency (2–5 seconds) due to LLM calls. This is within acceptable thresholds and communicated to users via loading states in the frontend.
- **PERF-018 Warning:** At 25 simultaneous leave applications, 2% error rate observed. Recommend adding a queue (e.g., Celery + Redis) for AI leave processing at scale.
- **PERF-020 Warning:** Face recognition model cold start is 8 seconds. Mitigated by pre-loading on server startup (implemented).
- All read-only endpoints perform well under concurrent load (< 250 ms at 50 users).

---

*End of Appendix I – Test Documentation*
