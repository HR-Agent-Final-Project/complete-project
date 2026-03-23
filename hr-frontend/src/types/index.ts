// ─── Auth ─────────────────────────────────────────────────────────────────────
export type UserRole = 'employee' | 'hr_admin' | 'management';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  department: string;
  position: string;
  avatar?: string;
  phone?: string;
  joined_date?: string;
  employee_id?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  role: UserRole | null;
}

// ─── Employee ─────────────────────────────────────────────────────────────────
export type EmployeeStatus = 'active' | 'on_leave' | 'inactive';

export interface Employee {
  id: number;
  employee_id: string;
  name: string;
  email: string;
  phone: string;
  department: string;
  position: string;
  role: UserRole;
  status: EmployeeStatus;
  joined_date: string;
  manager?: string;
  salary?: number;
  address?: string;
  emergency_contact?: string;
  // Extended fields from backend
  nic_number?: string;
  date_of_birth?: string;
  gender?: string;
  city?: string;
  district?: string;
  bank_account?: string;
  bank_name?: string;
  work_email?: string;
  face_registered?: boolean;
  profile_photo?: string;
  department_id?: number;
  role_id?: number;
  employment_type?: string;
  language_pref?: string;
  [key: string]: any;
}

// ─── Attendance ───────────────────────────────────────────────────────────────
export type AttendanceStatus = 'present' | 'absent' | 'late' | 'half_day';

export interface AttendanceRecord {
  id: number;
  employee_id: number;
  employee_number?: string;
  employee_name: string;
  date: string;
  check_in?: string;
  check_out?: string;
  hours?: number;
  status: AttendanceStatus;
  location?: string;
  latitude?: number;
  longitude?: number;
  checkout_latitude?: number;
  checkout_longitude?: number;
}

export interface AttendanceSummary {
  total_days: number;
  present: number;
  absent: number;
  late: number;
  attendance_rate: number;
}

// ─── Leave ────────────────────────────────────────────────────────────────────
export type LeaveType = 'annual' | 'sick' | 'casual' | 'maternity' | 'paternity';
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'escalated' | 'cancelled';

export interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  leave_type: LeaveType;
  from_date: string;
  to_date: string;
  days: number;
  reason: string;
  status: LeaveStatus;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface LeaveBalance {
  annual: number;
  annual_used: number;
  sick: number;
  sick_used: number;
  casual: number;
  casual_used: number;
}

// ─── Performance ──────────────────────────────────────────────────────────────
export interface PerformanceRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  department: string;
  period: string;
  punctuality: number;
  task_completion: number;
  attendance_rate: number;
  overtime_hours: number;
  overall_score: number;
  evaluated_by: string;
  evaluated_at: string;
  notes?: string;
}

// ─── Recruitment ──────────────────────────────────────────────────────────────
export type JobStatus = 'active' | 'closed' | 'draft';
export type ApplicantStatus = 'applied' | 'screening' | 'interview' | 'offered' | 'rejected';

export interface Job {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  posted_date: string;
  status: JobStatus;
  applications_count: number;
  salary_range?: string;
}

export interface Applicant {
  id: number;
  job_id: number;
  name: string;
  email: string;
  phone: string;
  applied_date: string;
  status: ApplicantStatus;
  ai_score?: number;
  interview_status?: 'pending' | 'scheduled' | 'completed';
  resume_url?: string;
}

// ─── Reports ──────────────────────────────────────────────────────────────────
export type ReportType = 'attendance' | 'leave' | 'performance' | 'headcount';

export interface ReportData {
  headers: string[];
  rows: (string | number)[][];
  summary: Record<string, string | number>;
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  title: string;
  last_message: string;
  updated_at: string;
  messages: ChatMessage[];
}

// ─── Notification ─────────────────────────────────────────────────────────────
export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
}

// ─── Dashboard Stats ──────────────────────────────────────────────────────────
export interface EmployeeDashboardStats {
  leave_balance: number;
  attendance_rate: number;
  pending_requests: number;
  next_payday: string;
}

export interface HRDashboardStats {
  total_employees: number;
  today_present: number;
  pending_leaves: number;
  open_positions: number;
}

export interface ManagementDashboardStats {
  headcount: number;
  attendance_rate: number;
  leave_utilization: number;
  avg_performance_score: number;
}
