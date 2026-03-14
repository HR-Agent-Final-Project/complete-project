import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Mail, Phone, Calendar, User } from 'lucide-react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip,
} from 'recharts';
import { Employee, AttendanceRecord, LeaveRequest, PerformanceRecord } from '../types';
import { employeeApi, attendanceApi, leaveApi, performanceApi } from '../services/api';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoButton } from '../components/ui/NeoButton';
import { StatusBadge } from '../components/ui/StatusBadge';
import { PageHeader } from '../components/ui/PageHeader';
import { SkeletonCard } from '../components/ui/SkeletonCard';

type Tab = 'overview' | 'attendance' | 'leave' | 'performance';

const DEPT_COLORS: Record<string, string> = {
  Engineering: 'bg-neo-blue',
  'Human Resources': 'bg-neo-teal',
  Finance: 'bg-neo-yellow',
  Marketing: 'bg-neo-coral',
  Sales: 'bg-neo-blue',
};

export const EmployeeProfile = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [performance, setPerformance] = useState<PerformanceRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.allSettled([
      employeeApi.get(parseInt(id)),
      attendanceApi.list(),
      leaveApi.all(),
      performanceApi.list(),
    ]).then(([empR, attR, lvsR, perfR]) => {
      if (empR.status === 'fulfilled') setEmployee(empR.value);
      if (attR.status === 'fulfilled') setAttendance(attR.value.filter(a => a.employee_id === parseInt(id!)));
      if (lvsR.status === 'fulfilled') setLeaves(lvsR.value.filter(l => l.employee_id === parseInt(id!)));
      if (perfR.status === 'fulfilled') setPerformance(perfR.value.find(p => p.employee_id === parseInt(id!)) || null);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="flex flex-col gap-4">
      <SkeletonCard className="h-32" />
      <div className="grid grid-cols-2 gap-4">
        <SkeletonCard /><SkeletonCard />
      </div>
    </div>
  );

  if (!employee) return (
    <NeoCard color="bg-neo-coral">
      <p className="font-display font-bold">Employee not found.</p>
    </NeoCard>
  );

  const avatarColor = DEPT_COLORS[employee.department] || 'bg-neo-blue';
  const initials = employee.name.split(' ').map(n => n[0]).join('').slice(0, 2);

  const radarData = performance ? [
    { metric: 'Punctuality', value: performance.punctuality },
    { metric: 'Tasks', value: performance.task_completion },
    { metric: 'Attendance', value: performance.attendance_rate },
    { metric: 'Overtime', value: Math.min(performance.overtime_hours * 5, 100) },
    { metric: 'Overall', value: performance.overall_score },
  ] : [];

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'attendance', label: 'Attendance' },
    { key: 'leave', label: 'Leave History' },
    { key: 'performance', label: 'Performance' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={employee.name}
        breadcrumbs={[{ label: 'Employees' }, { label: employee.name }]}
        action={
          <NeoButton variant="secondary" icon={<ArrowLeft size={16} />} onClick={() => navigate('/employees')}>
            Back
          </NeoButton>
        }
      />

      {/* Header Card */}
      <NeoCard shadow="lg" className="flex flex-col sm:flex-row gap-4 items-start">
        <div className={`w-20 h-20 ${avatarColor} border-4 border-neo-black flex items-center justify-center flex-shrink-0 shadow-neo`}>
          <span className="font-display font-bold text-3xl text-neo-black">{initials}</span>
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="font-display font-bold text-2xl text-neo-black">{employee.name}</h2>
              <p className="font-mono text-sm text-gray-600">{employee.position} · {employee.department}</p>
              <p className="font-mono text-xs text-gray-400 mt-1">ID: {employee.employee_id}</p>
            </div>
            <StatusBadge status={employee.status} className="text-sm px-3 py-1" />
          </div>
          <div className="flex flex-wrap gap-4 mt-3">
            <span className="flex items-center gap-1 font-mono text-xs text-gray-600"><Mail size={12} />{employee.email}</span>
            <span className="flex items-center gap-1 font-mono text-xs text-gray-600"><Phone size={12} />{employee.phone}</span>
            <span className="flex items-center gap-1 font-mono text-xs text-gray-600"><Calendar size={12} />Joined {employee.joined_date}</span>
          </div>
        </div>
      </NeoCard>

      {/* Tabs */}
      <div className="flex border-2 border-neo-black overflow-x-auto">
        {tabs.map((t, i) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-shrink-0 px-3 md:px-4 py-2 font-display font-bold text-sm border-neo-black transition-all
              ${i > 0 ? 'border-l-2' : ''}
              ${tab === t.key ? 'bg-neo-yellow' : 'bg-white hover:bg-neo-yellow/30'}
            `}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <NeoCard>
            <h3 className="font-display font-bold text-base mb-3 border-b-2 border-neo-black pb-2">Contact Details</h3>
            {[
              { icon: <Mail size={14} />, label: 'Email', value: employee.email },
              { icon: <Phone size={14} />, label: 'Phone', value: employee.phone },
              { icon: <User size={14} />, label: 'Manager', value: employee.manager || 'N/A' },
            ].map(d => (
              <div key={d.label} className="flex items-center gap-3 py-2 border-b border-black/10 last:border-0">
                <span className="text-gray-400">{d.icon}</span>
                <span className="font-mono text-xs text-gray-500 w-16">{d.label}</span>
                <span className="font-mono text-sm text-neo-black">{d.value}</span>
              </div>
            ))}
          </NeoCard>
          <NeoCard>
            <h3 className="font-display font-bold text-base mb-3 border-b-2 border-neo-black pb-2">Employment Details</h3>
            {[
              { label: 'Department', value: employee.department },
              { label: 'Position', value: employee.position },
              { label: 'Role', value: employee.role.replace('_', ' ') },
              { label: 'Joined', value: employee.joined_date },
              { label: 'Salary', value: employee.salary ? `LKR ${employee.salary.toLocaleString()}` : 'Confidential' },
            ].map(d => (
              <div key={d.label} className="flex items-center gap-3 py-2 border-b border-black/10 last:border-0">
                <span className="font-mono text-xs text-gray-500 w-24 capitalize">{d.label}</span>
                <span className="font-mono text-sm text-neo-black capitalize">{d.value}</span>
              </div>
            ))}
          </NeoCard>
        </div>
      )}

      {tab === 'attendance' && (
        <NeoCard>
          <h3 className="font-display font-bold text-base mb-4">Attendance Records</h3>
          {attendance.length === 0 ? (
            <p className="font-mono text-sm text-gray-500 text-center py-8">No attendance records found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="neo-table">
                <thead><tr><th>Date</th><th>Check In</th><th>Check Out</th><th>Hours</th><th>Status</th></tr></thead>
                <tbody>
                  {attendance.map(a => (
                    <tr key={a.id}>
                      <td className="font-mono text-sm">{a.date}</td>
                      <td className="font-mono text-sm">{a.check_in || '—'}</td>
                      <td className="font-mono text-sm">{a.check_out || '—'}</td>
                      <td className="font-mono text-sm">{a.hours ? `${a.hours}h` : '—'}</td>
                      <td><StatusBadge status={a.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </NeoCard>
      )}

      {tab === 'leave' && (
        <NeoCard>
          <h3 className="font-display font-bold text-base mb-4">Leave History</h3>
          {leaves.length === 0 ? (
            <p className="font-mono text-sm text-gray-500 text-center py-8">No leave requests found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="neo-table">
                <thead><tr><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Reason</th><th>Status</th></tr></thead>
                <tbody>
                  {leaves.map(l => (
                    <tr key={l.id}>
                      <td className="font-mono text-sm capitalize">{l.leave_type}</td>
                      <td className="font-mono text-sm">{l.from_date}</td>
                      <td className="font-mono text-sm">{l.to_date}</td>
                      <td className="font-mono text-sm">{l.days}</td>
                      <td className="font-mono text-xs max-w-xs truncate">{l.reason}</td>
                      <td><StatusBadge status={l.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </NeoCard>
      )}

      {tab === 'performance' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <NeoCard>
            <h3 className="font-display font-bold text-base mb-4">Performance Metrics — {performance?.period || 'N/A'}</h3>
            {performance ? (
              <div className="flex flex-col gap-3">
                {[
                  { label: 'Punctuality', value: performance.punctuality, color: 'bg-neo-teal' },
                  { label: 'Task Completion', value: performance.task_completion, color: 'bg-neo-blue' },
                  { label: 'Attendance Rate', value: performance.attendance_rate, color: 'bg-neo-yellow' },
                  { label: 'Overall Score', value: performance.overall_score, color: 'bg-neo-coral' },
                ].map(m => (
                  <div key={m.label}>
                    <div className="flex justify-between mb-1">
                      <span className="font-mono text-xs font-semibold uppercase tracking-wider">{m.label}</span>
                      <span className="font-mono text-xs font-bold">{m.value}/100</span>
                    </div>
                    <div className="h-4 bg-gray-100 border-2 border-neo-black">
                      <div className={`h-full ${m.color}`} style={{ width: `${m.value}%` }} />
                    </div>
                  </div>
                ))}
                {performance.notes && (
                  <div className="mt-2 p-3 bg-neo-yellow/20 border-2 border-neo-black">
                    <p className="font-mono text-xs">{performance.notes}</p>
                  </div>
                )}
              </div>
            ) : <p className="font-mono text-sm text-gray-500 py-8 text-center">No performance data available.</p>}
          </NeoCard>

          {performance && (
            <NeoCard>
              <h3 className="font-display font-bold text-base mb-4">Radar Chart</h3>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <Radar dataKey="value" fill="#00C9B1" fillOpacity={0.4} stroke="#00C9B1" strokeWidth={2} />
                  <Tooltip contentStyle={{ border: '2px solid #0A0A0A', fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
                </RadarChart>
              </ResponsiveContainer>
            </NeoCard>
          )}
        </div>
      )}
    </div>
  );
};
