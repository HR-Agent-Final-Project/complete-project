import {
  Employee, AttendanceRecord, LeaveRequest, PerformanceRecord,
  Job, Applicant, Conversation, Notification,
  EmployeeDashboardStats, HRDashboardStats, ManagementDashboardStats,
  LeaveBalance, ReportData,
} from '../types';

// Read from .env — set REACT_APP_USE_MOCK=false to use the real backend
export const USE_MOCK = process.env.REACT_APP_USE_MOCK === 'true';

// ─── Employees ────────────────────────────────────────────────────────────────
export const mockEmployees: Employee[] = [
  { id: 1, employee_id: 'EMP001', name: 'Kasun Perera', email: 'kasun.perera@hragent.lk', phone: '0771234567', department: 'Engineering', position: 'Senior Software Engineer', role: 'employee', status: 'active', joined_date: '2021-03-15', manager: 'Nimal Silva', salary: 120000 },
  { id: 2, employee_id: 'EMP002', name: 'Dilani Fernando', email: 'dilani.fernando@hragent.lk', phone: '0772345678', department: 'Human Resources', position: 'HR Manager', role: 'hr_admin', status: 'active', joined_date: '2019-07-01', manager: 'CEO', salary: 145000 },
  { id: 3, employee_id: 'EMP003', name: 'Nimal Rajapaksa', email: 'nimal.rajapaksa@hragent.lk', phone: '0773456789', department: 'Finance', position: 'Finance Analyst', role: 'employee', status: 'active', joined_date: '2022-01-10', manager: 'Suresh Bandara', salary: 95000 },
  { id: 4, employee_id: 'EMP004', name: 'Priya Wickramasinghe', email: 'priya.w@hragent.lk', phone: '0774567890', department: 'Marketing', position: 'Marketing Specialist', role: 'employee', status: 'on_leave', joined_date: '2020-11-20', manager: 'Amali De Silva', salary: 85000 },
  { id: 5, employee_id: 'EMP005', name: 'Suresh Bandara', email: 'suresh.bandara@hragent.lk', phone: '0775678901', department: 'Finance', position: 'CFO', role: 'management', status: 'active', joined_date: '2018-05-05', manager: 'CEO', salary: 250000 },
  { id: 6, employee_id: 'EMP006', name: 'Amali De Silva', email: 'amali.desilva@hragent.lk', phone: '0776789012', department: 'Marketing', position: 'Marketing Director', role: 'management', status: 'active', joined_date: '2018-09-12', manager: 'CEO', salary: 220000 },
  { id: 7, employee_id: 'EMP007', name: 'Roshan Gunasekara', email: 'roshan.g@hragent.lk', phone: '0777890123', department: 'Engineering', position: 'DevOps Engineer', role: 'employee', status: 'active', joined_date: '2022-06-01', manager: 'Kasun Perera', salary: 105000 },
  { id: 8, employee_id: 'EMP008', name: 'Sanduni Jayawardena', email: 'sanduni.j@hragent.lk', phone: '0778901234', department: 'Engineering', position: 'QA Engineer', role: 'employee', status: 'active', joined_date: '2021-09-15', manager: 'Kasun Perera', salary: 90000 },
  { id: 9, employee_id: 'EMP009', name: 'Chamara Dissanayake', email: 'chamara.d@hragent.lk', phone: '0779012345', department: 'Sales', position: 'Sales Executive', role: 'employee', status: 'inactive', joined_date: '2020-03-01', manager: 'Amali De Silva', salary: 75000 },
  { id: 10, employee_id: 'EMP010', name: 'Ishara Rathnayake', email: 'ishara.r@hragent.lk', phone: '0770123456', department: 'Human Resources', position: 'HR Executive', role: 'employee', status: 'active', joined_date: '2023-02-14', manager: 'Dilani Fernando', salary: 70000 },
];

// ─── Attendance ───────────────────────────────────────────────────────────────
const today = new Date().toISOString().split('T')[0];
export const mockAttendance: AttendanceRecord[] = mockEmployees.filter(e => e.status === 'active').map((emp, i) => ({
  id: emp.id,
  employee_id: emp.id,
  employee_name: emp.name,
  date: today,
  check_in: i % 5 === 0 ? undefined : `${8 + (i % 2)}:${i % 3 === 0 ? '45' : '00'}`,
  check_out: i % 5 === 0 ? undefined : `17:${i % 2 === 0 ? '30' : '00'}`,
  hours: i % 5 === 0 ? 0 : 8.5 - (i % 2) * 0.5,
  status: i % 5 === 0 ? 'absent' : i % 3 === 0 ? 'late' : 'present',
}));

export const mockAttendanceMonthly = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
  present: 40 + Math.floor(Math.random() * 10),
  absent: 2 + Math.floor(Math.random() * 5),
  late: 1 + Math.floor(Math.random() * 4),
}));

// ─── Leave ────────────────────────────────────────────────────────────────────
export const mockLeaveRequests: LeaveRequest[] = [
  { id: 1, employee_id: 1, employee_name: 'Kasun Perera', leave_type: 'annual', from_date: '2026-03-20', to_date: '2026-03-22', days: 3, reason: 'Family vacation', status: 'approved', created_at: '2026-03-10', reviewed_by: 'Dilani Fernando', reviewed_at: '2026-03-11' },
  { id: 2, employee_id: 4, employee_name: 'Priya Wickramasinghe', leave_type: 'sick', from_date: '2026-03-13', to_date: '2026-03-15', days: 3, reason: 'Fever and flu', status: 'pending', created_at: '2026-03-12' },
  { id: 3, employee_id: 7, employee_name: 'Roshan Gunasekara', leave_type: 'casual', from_date: '2026-03-18', to_date: '2026-03-18', days: 1, reason: 'Personal work', status: 'pending', created_at: '2026-03-12' },
  { id: 4, employee_id: 8, employee_name: 'Sanduni Jayawardena', leave_type: 'annual', from_date: '2026-04-01', to_date: '2026-04-05', days: 5, reason: 'New year holidays', status: 'approved', created_at: '2026-03-05', reviewed_by: 'Dilani Fernando', reviewed_at: '2026-03-06' },
  { id: 5, employee_id: 10, employee_name: 'Ishara Rathnayake', leave_type: 'sick', from_date: '2026-03-10', to_date: '2026-03-11', days: 2, reason: 'Medical appointment', status: 'rejected', created_at: '2026-03-09', reviewed_by: 'Dilani Fernando', reviewed_at: '2026-03-09' },
  { id: 6, employee_id: 3, employee_name: 'Nimal Rajapaksa', leave_type: 'casual', from_date: '2026-03-25', to_date: '2026-03-25', days: 1, reason: 'Attend a wedding', status: 'pending', created_at: '2026-03-12' },
];

export const mockLeaveBalance: LeaveBalance = {
  annual: 14, annual_used: 5,
  sick: 7, sick_used: 2,
  casual: 7, casual_used: 1,
};

// ─── Performance ──────────────────────────────────────────────────────────────
export const mockPerformance: PerformanceRecord[] = mockEmployees.filter(e => e.role === 'employee').map((emp, i) => ({
  id: emp.id,
  employee_id: emp.id,
  employee_name: emp.name,
  department: emp.department,
  period: 'Q1 2026',
  punctuality: 75 + Math.floor(Math.random() * 25),
  task_completion: 70 + Math.floor(Math.random() * 30),
  attendance_rate: 80 + Math.floor(Math.random() * 20),
  overtime_hours: Math.floor(Math.random() * 20),
  overall_score: 72 + Math.floor(Math.random() * 28),
  evaluated_by: 'Dilani Fernando',
  evaluated_at: '2026-03-01',
  notes: i % 2 === 0 ? 'Excellent performance this quarter.' : 'Needs improvement in task delivery timelines.',
}));

// ─── Recruitment ──────────────────────────────────────────────────────────────
export const mockJobs: Job[] = [
  { id: 1, title: 'Full Stack Developer', department: 'Engineering', description: 'Build and maintain web applications using React and Node.js.', requirements: '3+ years experience, React, Node.js, PostgreSQL', posted_date: '2026-03-01', status: 'active', applications_count: 12, salary_range: 'LKR 100,000 - 150,000' },
  { id: 2, title: 'HR Executive', department: 'Human Resources', description: 'Support HR operations including recruitment and payroll.', requirements: '2+ years HR experience, PQHRM preferred', posted_date: '2026-02-20', status: 'active', applications_count: 8, salary_range: 'LKR 60,000 - 80,000' },
  { id: 3, title: 'Digital Marketing Analyst', department: 'Marketing', description: 'Drive digital marketing campaigns and analytics.', requirements: '2+ years in digital marketing, Google Analytics, Meta Ads', posted_date: '2026-02-15', status: 'active', applications_count: 15, salary_range: 'LKR 70,000 - 95,000' },
  { id: 4, title: 'Data Analyst', department: 'Finance', description: 'Analyze financial data and generate insights.', requirements: 'SQL, Python, Power BI, 2+ years experience', posted_date: '2026-01-10', status: 'closed', applications_count: 20, salary_range: 'LKR 90,000 - 120,000' },
];

export const mockApplicants: Applicant[] = [
  { id: 1, job_id: 1, name: 'Tharaka Wijesinghe', email: 'tharaka@gmail.com', phone: '0771112233', applied_date: '2026-03-03', status: 'interview', ai_score: 87, interview_status: 'scheduled' },
  { id: 2, job_id: 1, name: 'Malsha Rodrigo', email: 'malsha.r@gmail.com', phone: '0772223344', applied_date: '2026-03-04', status: 'screening', ai_score: 72, interview_status: 'pending' },
  { id: 3, job_id: 1, name: 'Chathura Herath', email: 'chathura.h@gmail.com', phone: '0773334455', applied_date: '2026-03-05', status: 'applied', ai_score: 65, interview_status: 'pending' },
  { id: 4, job_id: 2, name: 'Sachini Kumari', email: 'sachini.k@gmail.com', phone: '0774445566', applied_date: '2026-02-22', status: 'offered', ai_score: 91, interview_status: 'completed' },
  { id: 5, job_id: 2, name: 'Dilan Madusanka', email: 'dilan.m@gmail.com', phone: '0775556677', applied_date: '2026-02-23', status: 'rejected', ai_score: 48, interview_status: 'completed' },
];

// ─── Conversations ────────────────────────────────────────────────────────────
export const mockConversations: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Leave Balance Inquiry',
    last_message: 'You have 9 days of annual leave remaining.',
    updated_at: '2026-03-13T10:30:00Z',
    messages: [
      { id: 'm1', role: 'user', content: 'What is my leave balance?', timestamp: '2026-03-13T10:29:00Z' },
      { id: 'm2', role: 'assistant', content: 'You have 9 days of annual leave, 5 days of sick leave, and 6 days of casual leave remaining for 2026.', timestamp: '2026-03-13T10:30:00Z' },
    ],
  },
  {
    id: 'conv-2',
    title: 'Attendance Policy',
    last_message: 'The standard working hours are 8:30 AM to 5:30 PM.',
    updated_at: '2026-03-12T14:15:00Z',
    messages: [
      { id: 'm3', role: 'user', content: 'What are the working hours?', timestamp: '2026-03-12T14:14:00Z' },
      { id: 'm4', role: 'assistant', content: 'The standard working hours are 8:30 AM to 5:30 PM, Monday to Friday. Flexible work arrangements may be available with manager approval.', timestamp: '2026-03-12T14:15:00Z' },
    ],
  },
];

// ─── Notifications ────────────────────────────────────────────────────────────
export const mockNotifications: Notification[] = [
  { id: 'n1', type: 'success', title: 'Leave Approved', message: 'Your annual leave from Mar 20-22 has been approved.', read: false, created_at: '2026-03-11T09:00:00Z' },
  { id: 'n2', type: 'info', title: 'Performance Review', message: 'Q1 2026 performance evaluations are now available.', read: false, created_at: '2026-03-10T14:00:00Z' },
  { id: 'n3', type: 'warning', title: 'Attendance Alert', message: 'You were marked late on March 10, 2026.', read: true, created_at: '2026-03-10T08:55:00Z' },
  { id: 'n4', type: 'info', title: 'New Job Posting', message: 'A new Full Stack Developer position has been posted.', read: true, created_at: '2026-03-01T10:00:00Z' },
];

// ─── Dashboard Stats ──────────────────────────────────────────────────────────
export const mockEmployeeStats: EmployeeDashboardStats = {
  leave_balance: 9,
  attendance_rate: 94,
  pending_requests: 1,
  next_payday: '2026-03-31',
};

export const mockHRStats: HRDashboardStats = {
  total_employees: 10,
  today_present: 8,
  pending_leaves: 3,
  open_positions: 3,
};

export const mockManagementStats: ManagementDashboardStats = {
  headcount: 10,
  attendance_rate: 92,
  leave_utilization: 38,
  avg_performance_score: 81,
};

export const mockDepartmentBreakdown = [
  { department: 'Engineering', headcount: 3, attendance_rate: 95 },
  { department: 'Human Resources', headcount: 2, attendance_rate: 100 },
  { department: 'Finance', headcount: 2, attendance_rate: 90 },
  { department: 'Marketing', headcount: 2, attendance_rate: 85 },
  { department: 'Sales', headcount: 1, attendance_rate: 80 },
];

export const mockTopPerformers = mockPerformance.sort((a, b) => b.overall_score - a.overall_score).slice(0, 5);

export const mockActivityFeed = [
  { id: 1, action: 'Leave Approved', detail: 'Kasun Perera — Annual Leave (Mar 20-22)', time: '2 hours ago', type: 'success' },
  { id: 2, action: 'New Employee', detail: 'Ishara Rathnayake joined HR department', time: '1 day ago', type: 'info' },
  { id: 3, action: 'Leave Rejected', detail: 'Ishara Rathnayake — Sick Leave (Mar 10-11)', time: '2 days ago', type: 'error' },
  { id: 4, action: 'Job Posted', detail: 'Full Stack Developer — Engineering', time: '3 days ago', type: 'info' },
  { id: 5, action: 'Performance Review', detail: 'Q1 2026 evaluations completed', time: '5 days ago', type: 'success' },
  { id: 6, action: 'Attendance Flagged', detail: 'Roshan Gunasekara — Late arrival Mar 10', time: '6 days ago', type: 'warning' },
];

// ─── Reports ──────────────────────────────────────────────────────────────────
export const mockReportData: ReportData = {
  headers: ['Employee', 'Department', 'Present Days', 'Absent Days', 'Late Days', 'Attendance Rate'],
  rows: mockEmployees.map(emp => [
    emp.name, emp.department,
    20 + Math.floor(Math.random() * 5),
    Math.floor(Math.random() * 3),
    Math.floor(Math.random() * 4),
    `${88 + Math.floor(Math.random() * 12)}%`,
  ]),
  summary: {
    total_employees: 10,
    avg_attendance_rate: '91.5%',
    total_present_days: 215,
    total_absent_days: 18,
  },
};
