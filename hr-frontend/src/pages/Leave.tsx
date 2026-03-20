import React, { useEffect, useState } from 'react';
import { Check, X as XIcon } from 'lucide-react';
import { LeaveRequest, LeaveBalance, LeaveType } from '../types';
import { leaveApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoInput, NeoSelect, NeoTextarea } from '../components/ui/NeoInput';
import { NeoModal } from '../components/ui/NeoModal';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable, Column } from '../components/ui/DataTable';

const leaveTypes: { value: LeaveType; label: string }[] = [
  { value: 'annual', label: 'Annual Leave' },
  { value: 'sick', label: 'Sick Leave' },
  { value: 'casual', label: 'Casual Leave' },
  { value: 'maternity', label: 'Maternity Leave' },
  { value: 'paternity', label: 'Paternity Leave' },
];

const INITIAL_FORM = {
  leave_type: 'annual' as LeaveType,
  from_date: '',
  to_date: '',
  reason: '',
};

// ─── Balance Bar ──────────────────────────────────────────────────────────────
const BalanceBar = ({ label, total, used, color }: { label: string; total: number; used: number; color: string }) => {
  const pct = total > 0 ? (used / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="font-mono text-xs uppercase tracking-wider font-semibold">{label}</span>
        <span className="font-mono text-xs font-bold">{total - used} / {total} days left</span>
      </div>
      <div className="h-5 bg-gray-100 border-2 border-neo-black">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

// ─── Employee Leave View ──────────────────────────────────────────────────────
const EmployeeLeave = () => {
  const { addNotification } = useNotifications();
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [balance, setBalance] = useState<LeaveBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [cancelling, setCancelling] = useState<number | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.allSettled([leaveApi.myRequests(), leaveApi.balance()])
      .then(([r, b]) => {
        if (r.status === 'fulfilled') setRequests(r.value);
        if (b.status === 'fulfilled') setBalance(b.value);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleCancel = async (id: number) => {
    setCancelling(id);
    try {
      await leaveApi.cancel(id);
      setRequests(prev => prev.map(l => l.id === id ? { ...l, status: 'cancelled' as any } : l));
      addNotification('success', 'Leave Cancelled', `Leave request #${id} has been cancelled.`);
      loadData();
    } catch (err: any) {
      addNotification('error', 'Cancel Failed', err?.response?.data?.detail ?? 'Could not cancel leave.');
    } finally {
      setCancelling(null);
    }
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.from_date) e.from_date = 'Required';
    if (!form.to_date) e.to_date = 'Required';
    if (form.from_date && form.to_date && form.from_date > form.to_date) e.to_date = 'Must be after from date';
    if (!form.reason.trim()) e.reason = 'Required';
    return e;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      const days = Math.ceil((new Date(form.to_date).getTime() - new Date(form.from_date).getTime()) / 86400000) + 1;
      await leaveApi.apply({ ...form, days, employee_name: 'Me' });
      setModalOpen(false);
      setForm(INITIAL_FORM);
      addNotification('success', 'Leave Applied', 'Your leave request has been submitted and reviewed by AI.');
      loadData();
    } catch (err: any) {
      addNotification('error', 'Failed', err?.response?.data?.detail ?? 'Could not apply for leave.');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<LeaveRequest>[] = [
    { key: 'leave_type', header: 'Type', render: r => <span className="font-mono text-sm capitalize">{r.leave_type}</span> },
    { key: 'from_date', header: 'From', render: r => <span className="font-mono text-sm">{r.from_date}</span> },
    { key: 'to_date', header: 'To', render: r => <span className="font-mono text-sm">{r.to_date}</span> },
    { key: 'days', header: 'Days', render: r => <span className="font-mono text-sm">{r.days}</span> },
    { key: 'reason', header: 'Reason', render: r => <span className="font-mono text-xs truncate max-w-xs block">{r.reason}</span> },
    { key: 'status', header: 'Status', render: r => <StatusBadge status={r.status} /> },
    { key: 'id', header: 'Actions', render: r => (
      (r.status === 'pending' || r.status === 'escalated') ? (
        <NeoButton
          variant="danger"
          size="sm"
          icon={<XIcon size={14} />}
          loading={cancelling === r.id}
          onClick={() => handleCancel(r.id)}
        >Cancel</NeoButton>
      ) : null
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leave Management"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Leave' }]}
        action={
          <NeoButton variant="primary" onClick={() => setModalOpen(true)}>Apply for Leave</NeoButton>
        }
      />

      {/* Balance */}
      {balance && (
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Leave Balance</h3>
          <div className="flex flex-col gap-4">
            <BalanceBar label="Annual Leave" total={balance.annual} used={balance.annual_used} color="bg-neo-teal" />
            <BalanceBar label="Sick Leave" total={balance.sick} used={balance.sick_used} color="bg-neo-coral" />
            <BalanceBar label="Casual Leave" total={balance.casual} used={balance.casual_used} color="bg-neo-yellow" />
          </div>
        </NeoCard>
      )}

      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">My Leave Requests</h3>
        <DataTable columns={columns} data={requests} loading={loading} emptyMessage="No leave requests yet." />
      </NeoCard>

      {/* Apply Modal */}
      <NeoModal open={modalOpen} onClose={() => setModalOpen(false)} title="Apply for Leave">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <NeoSelect
            label="Leave Type"
            value={form.leave_type}
            onChange={e => setForm(f => ({ ...f, leave_type: e.target.value as LeaveType }))}
            options={leaveTypes}
          />
          <div className="grid grid-cols-2 gap-3">
            <NeoInput label="From Date" type="date" value={form.from_date}
              onChange={e => { setForm(f => ({ ...f, from_date: e.target.value })); setErrors(er => ({ ...er, from_date: '' })); }}
              error={errors.from_date} />
            <NeoInput label="To Date" type="date" value={form.to_date}
              onChange={e => { setForm(f => ({ ...f, to_date: e.target.value })); setErrors(er => ({ ...er, to_date: '' })); }}
              error={errors.to_date} />
          </div>
          <NeoTextarea label="Reason" value={form.reason}
            onChange={e => { setForm(f => ({ ...f, reason: e.target.value })); setErrors(er => ({ ...er, reason: '' })); }}
            placeholder="Briefly explain your reason..."
            error={errors.reason} />
          <div className="flex gap-3 justify-end pt-2 border-t-2 border-neo-black">
            <NeoButton type="button" variant="secondary" onClick={() => setModalOpen(false)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Submit Request</NeoButton>
          </div>
        </form>
      </NeoModal>
    </div>
  );
};

// ─── HR Leave View ────────────────────────────────────────────────────────────
const HRLeave = () => {
  const { addNotification } = useNotifications();
  const [pending, setPending] = useState<LeaveRequest[]>([]);
  const [all, setAll] = useState<LeaveRequest[]>([]);
  const [balance, setBalance] = useState<LeaveBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const loadData = () => {
    setLoading(true);
    Promise.allSettled([leaveApi.pending(), leaveApi.all(), leaveApi.balance()])
      .then(([p, a, b]) => {
        if (p.status === 'fulfilled') setPending(p.value);
        if (a.status === 'fulfilled') setAll(a.value);
        if (b.status === 'fulfilled') setBalance(b.value);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleAction = async (id: number, action: 'approve' | 'reject') => {
    setProcessing(id);
    try {
      if (action === 'approve') await leaveApi.approve(id);
      else await leaveApi.reject(id);
      setPending(prev => prev.filter(l => l.id !== id));
      setAll(prev => prev.map(l => l.id === id ? { ...l, status: action === 'approve' ? 'approved' : 'rejected' } : l));
      addNotification('success', `Leave ${action === 'approve' ? 'Approved' : 'Rejected'}`, `Leave request #${id} has been ${action}d.`);
    } finally {
      setProcessing(null);
    }
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.from_date) e.from_date = 'Required';
    if (!form.to_date) e.to_date = 'Required';
    if (form.from_date && form.to_date && form.from_date > form.to_date) e.to_date = 'Must be after from date';
    if (!form.reason.trim()) e.reason = 'Required';
    return e;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      const days = Math.ceil((new Date(form.to_date).getTime() - new Date(form.from_date).getTime()) / 86400000) + 1;
      await leaveApi.apply({ ...form, days, employee_name: 'Me' });
      setModalOpen(false);
      setForm(INITIAL_FORM);
      addNotification('success', 'Leave Applied', 'Your leave request has been submitted and reviewed by AI.');
      loadData(); // Refresh all data
    } catch (err: any) {
      addNotification('error', 'Failed', err?.response?.data?.detail ?? 'Could not apply for leave.');
    } finally {
      setSaving(false);
    }
  };

  const historyColumns: Column<LeaveRequest>[] = [
    { key: 'employee_name', header: 'Employee' },
    { key: 'leave_type', header: 'Type', render: r => <span className="capitalize font-mono text-sm">{r.leave_type}</span> },
    { key: 'from_date', header: 'From', render: r => <span className="font-mono text-sm">{r.from_date}</span> },
    { key: 'to_date', header: 'To', render: r => <span className="font-mono text-sm">{r.to_date}</span> },
    { key: 'days', header: 'Days', render: r => <span className="font-mono text-sm">{r.days}</span> },
    { key: 'status', header: 'Status', render: r => <StatusBadge status={r.status} /> },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leave Management"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Leave' }]}
        action={
          <NeoButton variant="primary" onClick={() => setModalOpen(true)}>Apply for Leave</NeoButton>
        }
      />

      {/* Pending Cards */}
      <div>
        <h3 className="font-display font-bold text-xl mb-4">
          Pending Approvals <span className="text-neo-coral">({pending.length})</span>
        </h3>
        {loading ? (
          <div className="grid gap-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-24 border-2 border-neo-black" />)}</div>
        ) : pending.length === 0 ? (
          <NeoCard color="bg-neo-teal"><p className="font-display font-bold text-center py-4">All caught up! No pending leaves.</p></NeoCard>
        ) : (
          <div className="grid gap-3">
            {pending.map(l => (
              <NeoCard key={l.id} className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-display font-bold text-base">{l.employee_name}</p>
                    <span className="font-mono text-xs text-gray-500 capitalize border border-neo-black px-1.5">{l.leave_type}</span>
                  </div>
                  <p className="font-mono text-sm text-gray-600">{l.from_date} → {l.to_date} ({l.days} days)</p>
                  <p className="font-mono text-xs text-gray-500 mt-1 italic">"{l.reason}"</p>
                </div>
                <div className="flex gap-2">
                  <NeoButton
                    variant="teal"
                    size="sm"
                    icon={<Check size={14} />}
                    loading={processing === l.id}
                    onClick={() => handleAction(l.id, 'approve')}
                  >Approve</NeoButton>
                  <NeoButton
                    variant="danger"
                    size="sm"
                    icon={<XIcon size={14} />}
                    loading={processing === l.id}
                    onClick={() => handleAction(l.id, 'reject')}
                  >Reject</NeoButton>
                </div>
              </NeoCard>
            ))}
          </div>
        )}
      </div>

      {/* My Balance */}
      {balance && (
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">My Leave Balance</h3>
          <div className="flex flex-col gap-4">
            <BalanceBar label="Annual Leave" total={balance.annual} used={balance.annual_used} color="bg-neo-teal" />
            <BalanceBar label="Sick Leave" total={balance.sick} used={balance.sick_used} color="bg-neo-coral" />
            <BalanceBar label="Casual Leave" total={balance.casual} used={balance.casual_used} color="bg-neo-yellow" />
          </div>
        </NeoCard>
      )}

      {/* History */}
      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">All Leave Requests</h3>
        <DataTable columns={historyColumns} data={all} loading={loading} emptyMessage="No leave requests found." />
      </NeoCard>

      {/* Apply Modal */}
      <NeoModal open={modalOpen} onClose={() => setModalOpen(false)} title="Apply for Leave">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <NeoSelect
            label="Leave Type"
            value={form.leave_type}
            onChange={e => setForm(f => ({ ...f, leave_type: e.target.value as LeaveType }))}
            options={leaveTypes}
          />
          <div className="grid grid-cols-2 gap-3">
            <NeoInput label="From Date" type="date" value={form.from_date}
              onChange={e => { setForm(f => ({ ...f, from_date: e.target.value })); setErrors(er => ({ ...er, from_date: '' })); }}
              error={errors.from_date} />
            <NeoInput label="To Date" type="date" value={form.to_date}
              onChange={e => { setForm(f => ({ ...f, to_date: e.target.value })); setErrors(er => ({ ...er, to_date: '' })); }}
              error={errors.to_date} />
          </div>
          <NeoTextarea label="Reason" value={form.reason}
            onChange={e => { setForm(f => ({ ...f, reason: e.target.value })); setErrors(er => ({ ...er, reason: '' })); }}
            placeholder="Briefly explain your reason..."
            error={errors.reason} />
          <div className="flex gap-3 justify-end pt-2 border-t-2 border-neo-black">
            <NeoButton type="button" variant="secondary" onClick={() => setModalOpen(false)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Submit Request</NeoButton>
          </div>
        </form>
      </NeoModal>
    </div>
  );
};

// ─── Main ─────────────────────────────────────────────────────────────────────
export const Leave = () => {
  const { role } = useAuth();
  if (role === 'hr_admin' || role === 'management') return <HRLeave />;
  return <EmployeeLeave />;
};
