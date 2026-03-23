import axios from 'axios';
// types used in return signatures
import { USE_MOCK } from '../mock/data';
import * as mock from '../mock/data';
// types used in return signatures
import {
  User, Employee, AttendanceRecord, LeaveRequest, LeaveBalance,
  PerformanceRecord, Job, Applicant, Conversation, ChatMessage,
  ReportData, HRDashboardStats, EmployeeDashboardStats, ManagementDashboardStats,
} from '../types';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  res => res,
  err => {
    // Resolve cancelled requests with empty data so .finally() always fires
    if (axios.isCancel(err) || err.code === 'ERR_CANCELED' || err.message === 'Request aborted') {
      return Promise.resolve({ data: null, cancelled: true });
    }
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

const delay = (ms = 400) => new Promise(res => setTimeout(res, ms));

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Maps backend access_level (integer) to frontend UserRole string.
 *   1       → 'employee'
 *   2 or 3  → 'hr_admin'
 *   4+      → 'management'
 */
function accessLevelToRole(level: number): User['role'] {
  if (level >= 4) return 'management';
  if (level >= 2) return 'hr_admin';
  return 'employee';
}

/**
 * Converts the backend TokenResponse into the { access_token, user } shape
 * that the frontend AuthContext expects.
 */
function mapTokenResponse(data: any): { access_token: string; user: User; must_change_password: boolean } {
  const user: User = {
    id:          data.employee_id,
    name:        data.employee_name,
    email:       data.email,
    role:        accessLevelToRole(data.access_level),
    department:  data.department    ?? '',
    position:    data.role          ?? '',   // backend "role" field = job title
    avatar:      data.profile_photo ?? undefined,
  };
  return { access_token: data.access_token, user, must_change_password: data.must_change_password ?? false };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: async (identifier: string, password: string): Promise<{ access_token: string; user: User; must_change_password: boolean }> => {
    if (USE_MOCK) {
      await delay();
      const user = mock.mockEmployees.find(e => e.email === identifier || e.employee_id === identifier)
        || mock.mockEmployees[0];
      return { access_token: 'mock-token-' + Date.now(), user: { ...user, role: user.role }, must_change_password: false };
    }
    const res = await apiClient.post('/auth/login', { identifier, password });
    return mapTokenResponse(res.data);
  },

  selfRegister: async (data: {
    first_name: string;
    last_name: string;
    personal_email: string;
    password: string;
    confirm_password: string;
    requested_role: 'hr_admin' | 'management';
    phone_number?: string;
  }): Promise<{ message: string }> => {
    if (USE_MOCK) {
      await delay(600);
      return {
        message:
          'Registration submitted successfully. An approval request has been sent to hr.agent.automation@gmail.com. You will be able to log in once your account is approved.',
      };
    }
    const res = await apiClient.post('/auth/self-register', data);
    return res.data;
  },
};

// ─── Employees ────────────────────────────────────────────────────────────────
function mapEmployee(e: any): Employee {
  return {
    id: e.id,
    employee_id: e.employee_number ?? String(e.id),
    name: e.full_name ?? `${e.first_name ?? ''} ${e.last_name ?? ''}`.trim(),
    email: e.personal_email ?? e.work_email ?? '',
    phone: e.phone_number ?? '',
    department: e.department ?? '',
    position: e.role ?? '',
    role: e.access_level >= 4 ? 'management' : e.access_level >= 2 ? 'hr_admin' : 'employee',
    status: (e.status ?? 'active').toLowerCase() as any,
    joined_date: e.hire_date ?? '',
    salary: e.base_salary,
    address: e.address,
    // Extended fields stored on raw object for profile page
    ...(e.nic_number    !== undefined && { nic_number:    e.nic_number }),
    ...(e.date_of_birth !== undefined && { date_of_birth: e.date_of_birth }),
    ...(e.gender        !== undefined && { gender:        e.gender }),
    ...(e.city          !== undefined && { city:          e.city }),
    ...(e.district      !== undefined && { district:      e.district }),
    ...(e.bank_account  !== undefined && { bank_account:  e.bank_account }),
    ...(e.bank_name     !== undefined && { bank_name:     e.bank_name }),
    ...(e.manager_name  !== undefined && { manager:       e.manager_name }),
    ...(e.work_email    !== undefined && { work_email:    e.work_email }),
    ...(e.face_registered !== undefined && { face_registered: e.face_registered }),
    ...(e.profile_photo   !== undefined && { profile_photo:   e.profile_photo }),
    ...(e.department_id   !== undefined && { department_id:   e.department_id }),
    ...(e.role_id         !== undefined && { role_id:         e.role_id }),
    ...(e.employment_type !== undefined && { employment_type: e.employment_type }),
    ...(e.language_pref   !== undefined && { language_pref:   e.language_pref }),
  };
}

export const employeeApi = {
  list: async (): Promise<Employee[]> => {
    if (USE_MOCK) { await delay(); return mock.mockEmployees; }
    const res = await apiClient.get('/employees');
    if (!res.data) return [];
    const items: any[] = res.data.employees ?? res.data;
    return items.map(mapEmployee);
  },

  get: async (id: number): Promise<Employee> => {
    if (USE_MOCK) { await delay(); return mock.mockEmployees.find(e => e.id === id) || mock.mockEmployees[0]; }
    const res = await apiClient.get(`/employees/${id}`);
    return mapEmployee(res.data);
  },

  /** Register a new employee — returns { employee_number, temp_password, ... } */
  register: async (data: Record<string, any>): Promise<any> => {
    const res = await apiClient.post('/employees/register', data);
    return res.data;
  },

  update: async (id: number, data: Record<string, any>): Promise<any> => {
    const res = await apiClient.put(`/employees/${id}`, data);
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/employees/${id}`);
  },

  updateStatus: async (id: number, is_active: boolean, reason?: string): Promise<void> => {
    await apiClient.patch(`/employees/${id}/status`, { is_active, reason });
  },

  uploadPhoto: async (id: number, file: File): Promise<string> => {
    const form = new FormData();
    form.append('file', file);
    const res = await apiClient.post(`/employees/${id}/upload-photo`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data.profile_photo;
  },

  enrollFace: async (id: number, imageBase64: string): Promise<{ message: string }> => {
    const res = await apiClient.post(`/employees/${id}/enroll-face`, { image_base64: imageBase64 });
    return res.data;
  },

  // kept for legacy callers
  create: async (data: Partial<Employee>): Promise<Employee> => {
    if (USE_MOCK) { await delay(); return { ...mock.mockEmployees[0], ...data, id: Date.now() } as Employee; }
    const res = await apiClient.post('/employees/register', data);
    return mapEmployee(res.data.employee ?? res.data);
  },
};

// ─── Departments & Roles ──────────────────────────────────────────────────────
export const departmentApi = {
  list: async (): Promise<{ id: number; name: string; code: string }[]> => {
    const res = await apiClient.get('/departments');
    if (!res.data) return [];
    return res.data;
  },
};

export const roleApi = {
  list: async (): Promise<{ id: number; title: string; code: string; access_level: number }[]> => {
    const res = await apiClient.get('/roles');
    if (!res.data) return [];
    return res.data.map((r: any) => ({ id: r.id, title: r.title, code: r.code ?? '', access_level: r.access_level }));
  },
};

// ─── Attendance ───────────────────────────────────────────────────────────────
export const attendanceApi = {
  list: async (date?: string): Promise<AttendanceRecord[]> => {
    if (USE_MOCK) { await delay(); return mock.mockAttendance; }
    const params: Record<string, string> = {};
    if (date) { params.from_date = date; params.to_date = date; }
    const res = await apiClient.get('/attendance/all', { params });
    if (!res.data) return [];
    const items: any[] = res.data.records ?? res.data ?? [];
    return items.map((a: any) => ({
      id: a.id,
      employee_id: a.employee_id,
      employee_number: a.employee_number ?? '',
      employee_name: a.employee_name ?? a.employee?.full_name ?? '',
      date: a.work_date ?? a.date ?? '',
      check_in: a.clock_in,
      check_out: a.clock_out,
      hours: a.work_hours,
      status: a.is_absent ? 'absent' : a.is_late ? 'late' : 'present',
      location: a.location ?? '',
      latitude: a.latitude ?? null,
      longitude: a.longitude ?? null,
      checkout_latitude: a.checkout_latitude ?? null,
      checkout_longitude: a.checkout_longitude ?? null,
    }));
  },
  mark: async (): Promise<{ message: string }> => {
    if (USE_MOCK) { await delay(); return { message: 'Attendance marked successfully' }; }
    const res = await apiClient.post('/attendance/mark');
    return res.data;
  },
  monthly: async () => {
    if (USE_MOCK) { await delay(); return mock.mockAttendanceMonthly; }
    const res = await apiClient.get('/reports/attendance/trends', { params: { months: 6 } });
    if (!res.data) return [];
    const data: any[] = res.data.data ?? [];
    return data.map((d: any) => ({
      date: d.month,
      label: d.label,
      present: d.attendance_rate,
      absent: 100 - d.attendance_rate,
      late: d.late_count,
    }));
  },
};

// ─── Leave ────────────────────────────────────────────────────────────────────
export const leaveApi = {
  myRequests: async (): Promise<LeaveRequest[]> => {
    if (USE_MOCK) { await delay(); return mock.mockLeaveRequests.slice(0, 3); }
    const res = await apiClient.get('/leave/my-leaves');
    if (!res.data) return [];
    const items: any[] = res.data.leaves ?? res.data ?? [];
    return items.map((l: any) => ({
      id: l.id,
      employee_id: l.employee_id ?? 0,
      employee_name: l.employee_name ?? '',
      leave_type: l.leave_type ?? l.leave_type_id,
      from_date: l.start_date,
      to_date: l.end_date,
      days: l.days_requested ?? l.total_days,
      status: l.status,
      reason: l.reason,
      created_at: l.created_at ?? '',
    }));
  },
  pending: async (): Promise<LeaveRequest[]> => {
    if (USE_MOCK) { await delay(); return mock.mockLeaveRequests.filter(l => l.status === 'pending'); }
    const res = await apiClient.get('/leave/pending');
    if (!res.data) return [];
    const items: any[] = res.data.requests ?? res.data.leaves ?? res.data ?? [];
    return items.map((l: any) => ({
      id: l.id,
      employee_id: l.employee_id,
      employee_name: l.employee_name ?? l.employee?.full_name ?? '',
      leave_type: l.leave_type ?? l.leave_type_id,
      from_date: l.start_date,
      to_date: l.end_date,
      days: l.days_requested ?? l.total_days,
      reason: l.reason ?? '',
      status: l.status,
      created_at: l.created_at ?? '',
    }));
  },
  all: async (): Promise<LeaveRequest[]> => {
    if (USE_MOCK) { await delay(); return mock.mockLeaveRequests; }
    const res = await apiClient.get('/leave/all');
    if (!res.data) return [];
    const items: any[] = res.data.leaves ?? res.data.requests ?? res.data ?? [];
    return items.map((l: any) => ({
      id: l.id,
      employee_id: l.employee_id,
      employee_number: l.employee_number ?? null,
      employee_name: l.employee_name ?? l.employee?.full_name ?? '',
      leave_type: l.leave_type ?? l.leave_type_id,
      from_date: l.start_date,
      to_date: l.end_date,
      days: l.days_requested ?? l.total_days,
      reason: l.reason ?? '',
      status: l.status,
      created_at: l.created_at ?? '',
    }));
  },
  balance: async (): Promise<LeaveBalance> => {
    if (USE_MOCK) { await delay(); return mock.mockLeaveBalance; }
    const res = await apiClient.get('/leave/my-balance');
    if (!res.data) return { annual: 0, annual_used: 0, sick: 0, sick_used: 0, casual: 0, casual_used: 0 };
    const balances: any[] = res.data.balances ?? [];
    const find = (code: string) => balances.find((b: any) => b.code === code || b.leave_type?.toLowerCase().includes(code));
    const annual = find('AL') || find('annual') || {};
    const sick   = find('SL') || find('sick')   || {};
    const casual = find('CL') || find('casual')  || {};
    return {
      annual:      annual.total_days     ?? 0,
      annual_used: annual.used_days      ?? 0,
      sick:        sick.total_days       ?? 0,
      sick_used:   sick.used_days        ?? 0,
      casual:      casual.total_days     ?? 0,
      casual_used: casual.used_days      ?? 0,
    };
  },
  types: async (): Promise<any[]> => {
    const res = await apiClient.get('/leave/types');
    return res.data?.types ?? [];
  },
  apply: async (data: Partial<LeaveRequest>): Promise<LeaveRequest> => {
    if (USE_MOCK) { await delay(); return { ...mock.mockLeaveRequests[0], ...data, id: Date.now(), status: 'pending' } as LeaveRequest; }
    // Map frontend field names to backend schema
    const payload: any = {
      start_date: data.from_date,
      end_date: data.to_date,
      reason: data.reason ?? '',
      is_half_day: false,
    };
    // Resolve leave_type string to leave_type_id
    if (typeof data.leave_type === 'number') {
      payload.leave_type_id = data.leave_type;
    } else {
      // Fetch types to find the ID
      const types = await leaveApi.types();
      const typeMap: Record<string, string> = {
        annual: 'AL', sick: 'SL', casual: 'CL',
        maternity: 'ML', paternity: 'PL', 'no pay': 'NPL',
      };
      const code = typeMap[(data.leave_type ?? '').toLowerCase()] ?? (data.leave_type ?? '').toUpperCase();
      const found = types.find((t: any) => t.code === code || t.name?.toLowerCase().includes((data.leave_type ?? '').toLowerCase()));
      payload.leave_type_id = found?.id ?? 1;
    }
    const res = await apiClient.post('/leave/apply', payload);
    return {
      id: res.data.leave_id ?? res.data.id,
      leave_type: res.data.leave_type ?? data.leave_type,
      from_date: data.from_date,
      to_date: data.to_date,
      days: res.data.days ?? data.days,
      reason: data.reason,
      status: res.data.status ?? 'pending',
      ai_decision: res.data.ai_decision,
      ai_reasoning: res.data.ai_reasoning,
      next_step: res.data.next_step,
    } as any;
  },
  approve: async (id: number): Promise<void> => {
    if (USE_MOCK) { await delay(); return; }
    await apiClient.post(`/leave/${id}/approve`, {});
  },
  reject: async (id: number, reason?: string): Promise<void> => {
    if (USE_MOCK) { await delay(); return; }
    await apiClient.post(`/leave/${id}/reject`, { reason: reason ?? '' });
  },
  cancel: async (id: number, reason?: string): Promise<void> => {
    if (USE_MOCK) { await delay(); return; }
    await apiClient.post(`/leave/${id}/cancel`, { reason: reason ?? '' });
  },
};

// ─── Performance ──────────────────────────────────────────────────────────────
export const performanceApi = {
  list: async (): Promise<PerformanceRecord[]> => {
    if (USE_MOCK) { await delay(); return mock.mockPerformance; }
    const res = await apiClient.get('/performance/all');
    if (!res.data) return [];
    const items: any[] = res.data.reviews ?? res.data ?? [];
    return items.map((p: any) => ({
      id: p.id,
      employee_id: p.employee_id,
      employee_name: p.employee?.full_name ?? '',
      department: p.employee?.department ?? '',
      period: p.period_start ? `${p.period_start} – ${p.period_end}` : '',
      punctuality: p.overall_score ?? 0,
      task_completion: p.overall_score ?? 0,
      attendance_rate: p.overall_score ?? 0,
      overtime_hours: 0,
      overall_score: p.overall_score ?? 0,
      evaluated_by: p.reviewer?.full_name ?? '',
      evaluated_at: p.created_at ?? '',
      notes: p.notes,
    }));
  },
  evaluate: async (data: Partial<PerformanceRecord>): Promise<PerformanceRecord> => {
    if (USE_MOCK) { await delay(); return { ...mock.mockPerformance[0], ...data, id: Date.now() } as PerformanceRecord; }
    const res = await apiClient.post(`/performance/generate/${data.employee_id}`, {
      period_type: 'monthly',
    });
    const p = res.data;
    return {
      id: p.id,
      employee_id: p.employee_id,
      employee_name: p.employee?.full_name ?? '',
      department: p.employee?.department ?? '',
      period: p.period_start ? `${p.period_start} – ${p.period_end}` : '',
      punctuality: p.overall_score ?? 0,
      task_completion: p.overall_score ?? 0,
      attendance_rate: p.overall_score ?? 0,
      overtime_hours: 0,
      overall_score: p.overall_score ?? 0,
      evaluated_by: p.reviewer?.full_name ?? '',
      evaluated_at: p.created_at ?? '',
      notes: p.notes,
    };
  },
};

// ─── Recruitment ──────────────────────────────────────────────────────────────
export const recruitmentApi = {
  listJobs: async (): Promise<Job[]> => {
    if (USE_MOCK) { await delay(); return mock.mockJobs; }
    const res = await apiClient.get('/recruitment/jobs', { params: { active_only: false } });
    if (!res.data) return [];
    return (res.data ?? []).map((j: any) => ({
      id: j.id,
      title: j.title,
      department: j.department ?? '',
      description: j.description ?? '',
      requirements: j.requirements ?? '',
      salary_range: j.salary_range ?? '',
      status: j.status ?? 'active',
      posted_date: j.posted_date ?? '',
      applications_count: j.applications_count ?? 0,
    }));
  },
  createJob: async (data: Partial<Job>): Promise<Job> => {
    if (USE_MOCK) { await delay(); return { ...mock.mockJobs[0], ...data, id: Date.now() } as Job; }
    const res = await apiClient.post('/recruitment/jobs', data);
    return {
      id: res.data.id,
      title: res.data.title,
      department: res.data.department ?? '',
      description: res.data.description ?? '',
      requirements: res.data.requirements ?? '',
      salary_range: res.data.salary_range ?? '',
      status: res.data.status ?? 'active',
      posted_date: res.data.posted_date ?? '',
      applications_count: 0,
    };
  },
  getApplicants: async (jobId: number): Promise<Applicant[]> => {
    if (USE_MOCK) { await delay(); return mock.mockApplicants.filter(a => a.job_id === jobId); }
    const res = await apiClient.get(`/recruitment/jobs/${jobId}/applicants`);
    return (res.data ?? []).map((a: any) => ({
      id: a.id,
      job_id: a.job_id,
      name: a.name ?? '',
      email: a.email ?? '',
      status: a.status ?? 'applied',
      ai_score: a.ai_score,
      interview_status: a.interview_status,
    }));
  },
};

// ─── Reports ──────────────────────────────────────────────────────────────────
export const reportsApi = {
  generate: async (type: string, from: string, _to: string): Promise<ReportData> => {
    if (USE_MOCK) { await delay(600); return mock.mockReportData; }
    const period = from.slice(0, 7); // YYYY-MM
    const res = await apiClient.post('/reports/generate', { report_type: type, period });
    const content = res.data.content ?? {};
    const headers = ['Metric', 'Value'];
    const rows: (string | number)[][] = Object.entries(content)
      .filter(([, v]) => typeof v !== 'object')
      .map(([k, v]) => [k.replace(/_/g, ' '), String(v)]);
    const summary: Record<string, string | number> = {};
    rows.slice(0, 4).forEach(([k, v]) => { summary[String(k)] = v; });
    return { headers, rows, summary };
  },
};

// ─── Chat ─────────────────────────────────────────────────────────────────────

/** Shape returned by sendMessage — used by ChatWidget and AIChat. */
export interface ChatSendResult {
  response: string;
  conversation_id: string;
  sources: string[];
}

export const chatApi = {
  /**
   * Send a chat message.
   * - No conversationId  → POST /chat/quick   (auto-creates a session)
   * - With conversationId → POST /chat/sessions/{id}/message
   */
  sendMessage: async (message: string, conversationId?: string): Promise<ChatSendResult> => {
    if (USE_MOCK) {
      await delay(800);
      const responses = [
        'Based on our HR policies, your annual leave balance is 9 days remaining for this year.',
        'The attendance policy states employees should check in by 8:30 AM. Late arrivals after 8:45 AM are marked as late.',
        'To apply for leave, go to the Leave Management section and submit a request with your preferred dates.',
        'Your performance review for Q1 2026 shows an overall score of 85/100. Great work this quarter!',
        'According to the company handbook, overtime pay is calculated at 1.5× the hourly rate.',
      ];
      return {
        response: responses[Math.floor(Math.random() * responses.length)],
        conversation_id: conversationId || `conv-${Date.now()}`,
        sources: [],
      };
    }

    if (!conversationId) {
      // First message — backend auto-creates a session
      const res = await apiClient.post('/chat/quick', { message });
      return {
        response:        res.data.response,
        conversation_id: String(res.data.session_id),
        sources:         res.data.sources || [],
      };
    } else {
      // Continue an existing session
      const res = await apiClient.post(`/chat/sessions/${conversationId}/message`, { message });
      return {
        response:        res.data.response,
        conversation_id: String(res.data.session_id),
        sources:         res.data.sources || [],
      };
    }
  },

  /** List all chat sessions (for the sidebar). */
  getConversations: async (): Promise<Conversation[]> => {
    if (USE_MOCK) { await delay(); return mock.mockConversations; }
    const res = await apiClient.get('/chat/sessions');
    return (res.data as any[]).map(s => ({
      id:           String(s.id),
      title:        s.title || 'Untitled Chat',
      last_message: s.message_count ? `${s.message_count} message${s.message_count !== 1 ? 's' : ''}` : 'No messages yet',
      updated_at:   s.created_at,
      messages:     [],  // loaded on demand via getSession()
    }));
  },

  /** Load a full session including all messages (called when opening history). */
  getSession: async (sessionId: string): Promise<{ id: string; title: string; messages: ChatMessage[] }> => {
    if (USE_MOCK) {
      const conv = mock.mockConversations.find(c => c.id === sessionId);
      return { id: sessionId, title: conv?.title || '', messages: conv?.messages || [] };
    }
    const res = await apiClient.get(`/chat/sessions/${sessionId}`);
    return {
      id:       String(res.data.id),
      title:    res.data.title || 'Untitled Chat',
      messages: (res.data.messages as any[]).map(m => ({
        id:        String(m.id),
        role:      m.role as 'user' | 'assistant',
        content:   m.content,
        timestamp: m.created_at,
      })),
    };
  },

  /** Soft-delete (deactivate) a chat session. */
  deleteSession: async (sessionId: string): Promise<void> => {
    if (USE_MOCK) { await delay(); return; }
    await apiClient.delete(`/chat/sessions/${sessionId}`);
  },

  /** Voice chat — send audio blob, get transcript + AI response + TTS audio. */
  sendVoice: async (audioBlob: Blob, sessionId?: string): Promise<{
    session_id: string;
    transcript: string;
    response: string;
    sources: string[];
    audio_base64: string | null;
  }> => {
    if (USE_MOCK) {
      await delay(1500);
      return {
        session_id: sessionId || `conv-${Date.now()}`,
        transcript: 'What is my leave balance?',
        response: 'Based on our HR policies, your annual leave balance is 9 days remaining.',
        sources: [],
        audio_base64: null,
      };
    }
    const form = new FormData();
    form.append('audio', audioBlob, 'recording.webm');
    if (sessionId) form.append('session_id', sessionId);
    const res = await apiClient.post('/chat/voice', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return {
      session_id: String(res.data.session_id),
      transcript: res.data.transcript,
      response: res.data.response,
      sources: res.data.sources || [],
      audio_base64: res.data.audio_base64 || null,
    };
  },
};

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const dashboardApi = {
  employeeStats: async (): Promise<EmployeeDashboardStats> => {
    if (USE_MOCK) { await delay(); return mock.mockEmployeeStats; }
    const res = await apiClient.get('/dashboard/employee');
    return res.data;
  },
  hrStats: async (): Promise<HRDashboardStats> => {
    if (USE_MOCK) { await delay(); return mock.mockHRStats; }
    const res = await apiClient.get('/dashboard/hr');
    return res.data;
  },
  managementStats: async (): Promise<ManagementDashboardStats> => {
    if (USE_MOCK) { await delay(); return mock.mockManagementStats; }
    const res = await apiClient.get('/dashboard/management');
    return res.data;
  },
  attendanceTrends: async () => {
    if (USE_MOCK) { await delay(); return mock.mockAttendanceMonthly; }
    const res = await apiClient.get('/reports/attendance/trends', { params: { months: 6 } });
    return (res.data.data ?? []).map((d: any) => ({
      date: d.month, label: d.label,
      present: d.attendance_rate, absent: 100 - d.attendance_rate,
    }));
  },
  departmentBreakdown: async () => {
    if (USE_MOCK) { await delay(); return mock.mockDepartmentBreakdown; }
    const res = await apiClient.get('/reports/headcount');
    const byDept: Record<string, number> = res.data.by_department ?? {};
    return Object.entries(byDept).map(([department, headcount]) => ({
      department, headcount, attendance_rate: 0,
    }));
  },
  topPerformers: async () => {
    if (USE_MOCK) { await delay(); return mock.mockTopPerformers; }
    try {
      const res = await apiClient.get('/performance/team');
      return (res.data.top_performers ?? []).map((p: any) => ({
        id: p.employee_id,
        employee_name: p.employee_name,
        department: p.department ?? '',
        overall_score: p.score ?? 0,
      }));
    } catch { return []; }
  },
  activityFeed: async () => {
    if (USE_MOCK) { await delay(); return mock.mockActivityFeed; }
    const res = await apiClient.get('/notifications/', { params: { limit: 6 } });
    const items: any[] = res.data ?? [];
    return items.map((n: any) => ({
      id: n.id,
      action: n.title ?? '',
      detail: n.message ?? '',
      time: n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
      type: n.priority === 'high' ? 'error' : n.type?.includes('approved') ? 'success' : 'info',
    }));
  },
};

// ─── User Profile ─────────────────────────────────────────────────────────────
export const userApi = {
  updateProfile: async (data: Partial<User>): Promise<User> => {
    if (USE_MOCK) { await delay(); return { ...mock.mockEmployees[0], ...data } as User; }
    const res = await apiClient.put('/employees/me', data);
    return res.data;
  },

  changePassword: async (current_password: string, new_password: string, confirm_password: string): Promise<{ message: string }> => {
    const res = await apiClient.post('/auth/set-password', {
      temp_password:    current_password,
      new_password,
      confirm_password,
    });
    return res.data;
  },
};
