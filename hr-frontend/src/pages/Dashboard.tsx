import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Users, CalendarCheck, FileText, TrendingUp,
  Clock, Plus, CheckSquare, BarChart2,
} from 'lucide-react';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoButton } from '../components/ui/NeoButton';
import { StatusBadge } from '../components/ui/StatusBadge';
import { SkeletonCard } from '../components/ui/SkeletonCard';
import { dashboardApi, leaveApi } from '../services/api';
import {
  EmployeeDashboardStats, HRDashboardStats, ManagementDashboardStats, LeaveRequest,
} from '../types';
import { useNavigate } from 'react-router-dom';

// ─── Stat Card ────────────────────────────────────────────────────────────────
const StatCard = ({ label, value, sub, color = 'bg-white', icon }: {
  label: string; value: string | number; sub?: string; color?: string; icon?: React.ReactNode;
}) => (
  <NeoCard color={color} className="flex flex-col gap-1 min-w-0">
    <div className="flex items-center justify-between">
      <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60 font-semibold">{label}</p>
      {icon && <span className="text-neo-black/40">{icon}</span>}
    </div>
    <p className="font-display font-bold text-3xl text-neo-black">{value}</p>
    {sub && <p className="font-mono text-xs text-gray-500">{sub}</p>}
  </NeoCard>
);

// ─── Employee Dashboard ───────────────────────────────────────────────────────
const EmployeeDashboard = () => {
  const { user } = useAuth();
  const { addNotification } = useNotifications();
  const [stats, setStats] = useState<EmployeeDashboardStats | null>(null);
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(false);
  const navigate = useNavigate();

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

  useEffect(() => {
    Promise.allSettled([dashboardApi.employeeStats(), leaveApi.myRequests()])
      .then(([s, l]) => {
        if (s.status === 'fulfilled') setStats(s.value);
        if (l.status === 'fulfilled') setLeaves(l.value);
      })
      .finally(() => setLoading(false));
  }, []);

  const markAttendance = async () => {
    setMarking(true);
    try {
      await new Promise(r => setTimeout(r, 600));
      addNotification('success', 'Attendance Marked', 'Your attendance for today has been recorded.');
    } finally {
      setMarking(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Welcome Banner */}
      <div className="relative bg-white border-2 border-neo-black/10 overflow-hidden rounded-sm">
        {/* Yellow accent circles */}
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full bg-neo-yellow/20 pointer-events-none" />
        <div className="absolute -bottom-4 left-1/3 w-24 h-24 rounded-full bg-neo-yellow/15 pointer-events-none" />

        <div className="relative p-6 md:p-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <div className="flex items-center gap-5">
            {/* Profile image area */}
            <div className="relative flex-shrink-0 hidden sm:block">
              <div className="w-20 h-20 rounded-full bg-neo-yellow/30 absolute -top-1 -left-1" />
              <div className="w-20 h-20 border-2 border-neo-black overflow-hidden relative rounded-full">
                <img src="/group.jpg" alt="" className="w-full h-full object-cover" />
              </div>
            </div>
            <div>
              <p className="font-mono text-xs text-neo-black/40 uppercase tracking-wider">{greeting}</p>
              <h2 className="font-display font-bold text-3xl md:text-4xl text-neo-black mt-1">
                {user?.name?.split(' ')[0]}!
              </h2>
              <p className="font-mono text-sm text-neo-black/50 mt-1">{user?.department} · {user?.position}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />) : <>
          <StatCard label="Leave Balance" value={`${stats?.leave_balance ?? 0} days`} sub="Annual leave remaining" color="bg-white" icon={<FileText size={20} />} />
          <StatCard label="Attendance" value={`${stats?.attendance_rate ?? 0}%`} sub="This month" color="bg-neo-teal" icon={<CalendarCheck size={20} />} />
          <StatCard label="Pending Requests" value={stats?.pending_requests ?? 0} sub="Awaiting approval" color="bg-white" icon={<Clock size={20} />} />
          <StatCard label="Next Payday" value={stats?.next_payday ? new Date(stats.next_payday).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : 'N/A'} sub="Salary date" color="bg-neo-yellow" icon={<TrendingUp size={20} />} />
        </>}
      </div>

      {/* Recent Leave Requests */}
      <NeoCard>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-lg">Recent Leave Requests</h3>
          <NeoButton variant="secondary" size="sm" onClick={() => navigate('/leave')}>View All</NeoButton>
        </div>
        <div className="overflow-x-auto">
          <table className="neo-table">
            <thead><tr><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Status</th></tr></thead>
            <tbody>
              {leaves.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-6 font-mono text-sm text-gray-500">No leave requests</td></tr>
              ) : leaves.map(l => (
                <tr key={l.id}>
                  <td className="capitalize font-mono text-sm">{l.leave_type}</td>
                  <td className="font-mono text-sm">{l.from_date}</td>
                  <td className="font-mono text-sm">{l.to_date}</td>
                  <td className="font-mono text-sm">{l.days}</td>
                  <td><StatusBadge status={l.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </NeoCard>
    </div>
  );
};

// ─── HR Dashboard ─────────────────────────────────────────────────────────────
const HRDashboard = () => {
  const [stats, setStats] = useState<HRDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activityFeed, setActivityFeed] = useState<any[]>([]);
  const [attendanceTrends, setAttendanceTrends] = useState<any[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardApi.hrStats().then(setStats).finally(() => setLoading(false));
    dashboardApi.activityFeed().then(setActivityFeed).catch(() => {});
    dashboardApi.attendanceTrends().then(setAttendanceTrends).catch(() => {});
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {/* HR Welcome Banner */}
      <div className="relative bg-white border-2 border-neo-black/10 overflow-hidden rounded-sm">
        <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full bg-neo-yellow/20 pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-28 h-28 rounded-full bg-neo-teal/10 pointer-events-none" />
        <div className="relative p-6 md:p-8 flex flex-col sm:flex-row sm:items-center gap-6">
          <div className="flex items-center gap-5 flex-1">
            <div className="relative flex-shrink-0 hidden sm:block">
              <div className="w-20 h-20 rounded-full bg-neo-yellow/30 absolute -top-1 -left-1" />
              <div className="w-20 h-20 border-2 border-neo-black overflow-hidden relative rounded-full">
                <img src="/talk.jpg" alt="" className="w-full h-full object-cover" />
              </div>
            </div>
            <div>
              <p className="font-mono text-xs text-neo-black/40 uppercase tracking-wider">HR Dashboard</p>
              <h2 className="font-display font-bold text-2xl md:text-3xl text-neo-black mt-1">
                Workforce <span className="relative">Overview<span className="absolute -bottom-1 left-0 w-full h-2 bg-neo-yellow/40 -z-10" /></span>
              </h2>
              <p className="font-mono text-sm text-neo-black/50 mt-1">Manage your team efficiently with real-time insights</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />) : <>
          <StatCard label="Total Employees" value={stats?.total_employees ?? 0} sub="All active staff" color="bg-neo-blue" icon={<Users size={20} />} />
          <StatCard label="Today Present" value={stats?.today_present ?? 0} sub={`of ${stats?.total_employees} employees`} color="bg-neo-teal" icon={<CalendarCheck size={20} />} />
          <StatCard label="Pending Leaves" value={stats?.pending_leaves ?? 0} sub="Awaiting review" color="bg-neo-yellow" icon={<FileText size={20} />} />
          <StatCard label="Open Positions" value={stats?.open_positions ?? 0} sub="Active job listings" color="bg-white" icon={<TrendingUp size={20} />} />
        </>}
      </div>

      {/* Quick Actions */}
      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Add Employee', icon: <Plus size={18} />, to: '/employees', color: 'primary' as const },
            { label: 'Approve Leaves', icon: <CheckSquare size={18} />, to: '/leave', color: 'teal' as const },
            { label: 'Generate Report', icon: <BarChart2 size={18} />, to: '/reports', color: 'secondary' as const },
            { label: 'Post Job', icon: <FileText size={18} />, to: '/recruitment', color: 'secondary' as const },
          ].map(a => (
            <NeoButton key={a.label} variant={a.color} icon={a.icon} onClick={() => navigate(a.to)} className="w-full py-3 flex-col gap-1 h-auto">
              {a.label}
            </NeoButton>
          ))}
        </div>
      </NeoCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Activity Feed */}
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Recent Activity</h3>
          <div className="flex flex-col gap-2">
            {activityFeed.length === 0
              ? <p className="font-mono text-xs text-gray-400 text-center py-4">No recent activity.</p>
              : activityFeed.map((a: any) => (
              <div key={a.id} className={`flex items-start gap-3 p-2 border-l-4 ${
                a.type === 'success' ? 'border-neo-teal bg-neo-teal/5' :
                a.type === 'error' ? 'border-neo-coral bg-neo-coral/5' :
                a.type === 'warning' ? 'border-neo-yellow bg-neo-yellow/5' :
                'border-neo-blue bg-neo-blue/5'
              }`}>
                <div className="flex-1 min-w-0">
                  <p className="font-display font-bold text-xs text-neo-black">{a.action}</p>
                  <p className="font-mono text-xs text-gray-500 truncate">{a.detail}</p>
                </div>
                <span className="font-mono text-xs text-gray-400 flex-shrink-0">{a.time}</span>
              </div>
            ))}
          </div>
        </NeoCard>

        {/* Attendance Chart */}
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Attendance Overview (30 days)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={attendanceTrends} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0A0A0A20" />
              <XAxis dataKey="label" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
              <YAxis tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
              <Tooltip contentStyle={{ border: '2px solid #0A0A0A', fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
              <Bar dataKey="present" fill="#00C9B1" stroke="#0A0A0A" strokeWidth={1} name="Present" />
              <Bar dataKey="absent" fill="#FF6B6B" stroke="#0A0A0A" strokeWidth={1} name="Absent" />
            </BarChart>
          </ResponsiveContainer>
        </NeoCard>
      </div>
    </div>
  );
};

// ─── Management Dashboard ─────────────────────────────────────────────────────
const ManagementDashboard = () => {
  const [stats, setStats] = useState<ManagementDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [deptBreakdown, setDeptBreakdown] = useState<any[]>([]);
  const [attendanceTrends, setAttendanceTrends] = useState<any[]>([]);
  const [topPerformers, setTopPerformers] = useState<any[]>([]);

  useEffect(() => {
    dashboardApi.managementStats().then(setStats).finally(() => setLoading(false));
    dashboardApi.departmentBreakdown().then(setDeptBreakdown).catch(() => {});
    dashboardApi.attendanceTrends().then(setAttendanceTrends).catch(() => {});
    dashboardApi.topPerformers().then(setTopPerformers).catch(() => {});
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {/* Management Welcome Banner */}
      <div className="relative bg-white border-2 border-neo-black/10 overflow-hidden rounded-sm">
        <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full bg-neo-blue/15 pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-28 h-28 rounded-full bg-neo-yellow/15 pointer-events-none" />
        <div className="relative p-6 md:p-8 flex flex-col sm:flex-row sm:items-center gap-6">
          <div className="flex items-center gap-5 flex-1">
            <div className="relative flex-shrink-0 hidden sm:block">
              <div className="w-20 h-20 rounded-full bg-neo-blue/20 absolute -top-1 -left-1" />
              <div className="w-20 h-20 border-2 border-neo-black overflow-hidden relative rounded-full">
                <img src="/watching.jpg" alt="" className="w-full h-full object-cover" />
              </div>
            </div>
            <div>
              <p className="font-mono text-xs text-neo-black/40 uppercase tracking-wider">Management Dashboard</p>
              <h2 className="font-display font-bold text-2xl md:text-3xl text-neo-black mt-1">
                Strategic <span className="relative">Overview<span className="absolute -bottom-1 left-0 w-full h-2 bg-neo-blue/30 -z-10" /></span>
              </h2>
              <p className="font-mono text-sm text-neo-black/50 mt-1">Company-wide performance metrics and analytics</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />) : <>
          <StatCard label="Headcount" value={stats?.headcount ?? 0} sub="Total employees" color="bg-neo-blue" />
          <StatCard label="Attendance Rate" value={`${stats?.attendance_rate ?? 0}%`} sub="Company average" color="bg-neo-teal" />
          <StatCard label="Leave Utilization" value={`${stats?.leave_utilization ?? 0}%`} sub="Of total entitlement" color="bg-neo-yellow" />
          <StatCard label="Avg Performance" value={`${stats?.avg_performance_score ?? 0}/100`} sub="Q1 2026" color="bg-white" />
        </>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Department Breakdown */}
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Department Breakdown</h3>
          <table className="neo-table">
            <thead><tr><th>Department</th><th>Headcount</th><th>Attendance %</th></tr></thead>
            <tbody>
              {deptBreakdown.map((d: any) => (
                <tr key={d.department}>
                  <td className="font-display font-semibold text-sm">{d.department}</td>
                  <td className="font-mono text-sm">{d.headcount}</td>
                  <td className="font-mono text-sm">
                    <span className={`font-bold ${d.attendance_rate >= 90 ? 'text-neo-teal' : d.attendance_rate >= 80 ? 'text-neo-yellow' : 'text-neo-coral'}`}>
                      {d.attendance_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </NeoCard>

        {/* Monthly Trend */}
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Monthly Attendance Trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={attendanceTrends} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0A0A0A20" />
              <XAxis dataKey="label" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
              <YAxis tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
              <Tooltip contentStyle={{ border: '2px solid #0A0A0A', fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
              <Line type="monotone" dataKey="present" stroke="#00C9B1" strokeWidth={2} dot={false} name="Present" />
              <Line type="monotone" dataKey="absent" stroke="#FF6B6B" strokeWidth={2} dot={false} name="Absent" />
            </LineChart>
          </ResponsiveContainer>
        </NeoCard>
      </div>

      {/* Top Performers */}
      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">Top Performers — Q1 2026</h3>
        <div className="overflow-x-auto">
          <table className="neo-table">
            <thead><tr><th>#</th><th>Employee</th><th>Department</th><th>Score</th></tr></thead>
            <tbody>
              {topPerformers.map((p: any, i: number) => (
                <tr key={p.id}>
                  <td className="font-mono text-sm font-bold">{i + 1}</td>
                  <td className="font-display font-semibold text-sm">{p.employee_name}</td>
                  <td className="font-mono text-sm">{p.department}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-gray-200 border border-neo-black">
                        <div className="h-full bg-neo-teal" style={{ width: `${p.overall_score}%` }} />
                      </div>
                      <span className="font-mono text-xs font-bold w-10">{p.overall_score}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </NeoCard>
    </div>
  );
};

// ─── Main Dashboard ────────────────────────────────────────────────────────────
export const Dashboard = () => {
  const { role } = useAuth();
  if (role === 'hr_admin') return <HRDashboard />;
  if (role === 'management') return <ManagementDashboard />;
  return <EmployeeDashboard />;
};
