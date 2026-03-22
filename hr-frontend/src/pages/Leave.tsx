import React, { useEffect, useState } from 'react';
import { Check, X as XIcon, Send, Bot, Users, AlertCircle, Clock } from 'lucide-react';
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
  { value: 'annual',    label: 'Annual Leave'    },
  { value: 'sick',      label: 'Sick Leave'       },
  { value: 'casual',    label: 'Casual Leave'     },
  { value: 'maternity', label: 'Maternity Leave'  },
  { value: 'paternity', label: 'Paternity Leave'  },
];

const INITIAL_FORM = {
  leave_type: 'annual' as LeaveType,
  from_date: '',
  to_date: '',
  reason: '',
};

// ─── AI Decision Result ───────────────────────────────────────────────────────
interface AIResult {
  ai_decision: 'approved' | 'rejected' | 'escalated';
  ai_reasoning: string;
  days: number;
  leave_type: string;
  next_step: string;
}

const AIDecisionModal = ({ result, onClose }: { result: AIResult; onClose: () => void }) => {
  const isApproved  = result.ai_decision === 'approved';
  const isEscalated = result.ai_decision === 'escalated';

  const config = isApproved
    ? { bg: 'bg-neo-teal', icon: <Check size={32} />, title: 'Leave Approved!', subtitle: 'Instantly approved by AI Agent' }
    : isEscalated
    ? { bg: 'bg-neo-yellow', icon: <Users size={32} />, title: 'Sent to HR Department', subtitle: 'Requires HR Manager review' }
    : { bg: 'bg-neo-coral', icon: <XIcon size={32} />, title: 'Leave Rejected', subtitle: 'Could not be approved' };

  return (
    <NeoModal open onClose={onClose} title="Leave Request Result">
      <div className="flex flex-col gap-5">

        {/* Decision Banner */}
        <div className={`${config.bg} border-2 border-neo-black p-5 flex items-center gap-4`}>
          <div className="shrink-0">{config.icon}</div>
          <div>
            <p className="font-display font-black text-xl">{config.title}</p>
            <p className="font-mono text-sm">{config.subtitle}</p>
          </div>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-3">
          <div className="border-2 border-neo-black p-3">
            <p className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-1">Leave Type</p>
            <p className="font-display font-bold capitalize">{result.leave_type}</p>
          </div>
          <div className="border-2 border-neo-black p-3">
            <p className="font-mono text-xs uppercase tracking-wider text-gray-500 mb-1">Duration</p>
            <p className="font-display font-bold">{result.days} day{result.days !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {/* AI Reasoning */}
        <div className="border-2 border-neo-black p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bot size={16} />
            <p className="font-mono text-xs uppercase tracking-wider font-bold">AI Reasoning</p>
          </div>
          <p className="font-mono text-sm text-gray-700 leading-relaxed">{result.ai_reasoning}</p>
        </div>

        {/* Next Step */}
        {isEscalated && (
          <div className="border-2 border-neo-black bg-neo-yellow p-4 flex gap-3">
            <AlertCircle size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-mono text-xs uppercase tracking-wider font-bold mb-1">What Happens Next</p>
              <p className="font-mono text-sm">{result.next_step || 'Your request has been forwarded to the HR department for manual review. You will be notified once a decision is made.'}</p>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t-2 border-neo-black">
          <NeoButton variant="primary" onClick={onClose}>Done</NeoButton>
        </div>
      </div>
    </NeoModal>
  );
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

// ─── Apply Leave Form (shared) ────────────────────────────────────────────────
const ApplyLeaveModal = ({
  open, onClose, onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: (result: AIResult) => void;
}) => {
  const { addNotification } = useNotifications();
  const [form, setForm]     = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.from_date) e.from_date = 'Required';
    if (!form.to_date)   e.to_date   = 'Required';
    if (form.from_date && form.to_date && form.from_date > form.to_date)
      e.to_date = 'Must be after from date';
    if (!form.reason.trim()) e.reason = 'Required';
    return e;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      const days = Math.ceil(
        (new Date(form.to_date).getTime() - new Date(form.from_date).getTime()) / 86400000
      ) + 1;
      const res: any = await leaveApi.apply({ ...form, days, employee_name: 'Me' });
      setForm(INITIAL_FORM);
      onClose();
      onSuccess(res);
    } catch (err: any) {
      addNotification('error', 'Failed', err?.response?.data?.detail ?? 'Could not apply for leave.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <NeoModal open={open} onClose={onClose} title="Request Leave">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">

        {/* Info banner */}
        <div className="flex gap-2 border-2 border-neo-black bg-gray-50 p-3">
          <Bot size={16} className="shrink-0 mt-0.5 text-neo-teal" />
          <p className="font-mono text-xs text-gray-600">
            Simple leaves (≤5 days, good attendance) are <strong>auto-approved by AI</strong>.
            Complex leaves are <strong>sent to HR</strong> for review.
          </p>
        </div>

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
          <NeoButton type="button" variant="secondary" onClick={onClose}>Cancel</NeoButton>
          <NeoButton type="submit" variant="primary" loading={saving} icon={<Send size={14} />}>
            Submit Request
          </NeoButton>
        </div>
      </form>
    </NeoModal>
  );
};

// ─── Employee Leave View ──────────────────────────────────────────────────────
const EmployeeLeave = () => {
  const { addNotification } = useNotifications();
  const [requests, setRequests]   = useState<LeaveRequest[]>([]);
  const [balance, setBalance]     = useState<LeaveBalance | null>(null);
  const [loading, setLoading]     = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [aiResult, setAiResult]   = useState<AIResult | null>(null);
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
      addNotification('success', 'Leave Cancelled', `Leave request #${id} has been cancelled.`);
      loadData();
    } catch (err: any) {
      addNotification('error', 'Cancel Failed', err?.response?.data?.detail ?? 'Could not cancel leave.');
    } finally {
      setCancelling(null);
    }
  };

  const handleSuccess = (result: AIResult) => {
    setAiResult(result);
    loadData();
  };

  const columns: Column<LeaveRequest>[] = [
    { key: 'leave_type', header: 'Type',   render: r => <span className="font-mono text-sm capitalize">{r.leave_type}</span> },
    { key: 'from_date',  header: 'From',   render: r => <span className="font-mono text-sm">{r.from_date}</span> },
    { key: 'to_date',    header: 'To',     render: r => <span className="font-mono text-sm">{r.to_date}</span> },
    { key: 'days',       header: 'Days',   render: r => <span className="font-mono text-sm">{r.days}</span> },
    { key: 'reason',     header: 'Reason', render: r => <span className="font-mono text-xs truncate max-w-xs block">{r.reason}</span> },
    { key: 'status',     header: 'Status', render: r => (
      <div className="flex items-center gap-2">
        <StatusBadge status={r.status} />
        {r.status === 'escalated' && (
          <span className="font-mono text-xs text-neo-yellow border border-neo-black px-1 flex items-center gap-1">
            <Clock size={10} /> HR Review
          </span>
        )}
      </div>
    )},
    { key: 'id', header: 'Actions', render: r => {
      const canCancel =
        r.status === 'pending' ||
        r.status === 'escalated' ||
        (r.status === 'approved' && new Date(r.from_date) > new Date());
      return canCancel ? (
        <NeoButton variant="danger" size="sm" icon={<XIcon size={14} />}
          loading={cancelling === r.id} onClick={() => handleCancel(r.id)}>Cancel</NeoButton>
      ) : null;
    }},
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leave Management"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Leave' }]}
        action={
          <NeoButton variant="primary" icon={<Send size={16} />} onClick={() => setModalOpen(true)}>
            Request Leave
          </NeoButton>
        }
      />

      {/* How it works banner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border-2 border-neo-black bg-neo-teal p-4 flex gap-3 items-start">
          <Bot size={22} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-display font-bold">Simple Leave → AI Auto-Approved</p>
            <p className="font-mono text-xs mt-1">≤ 5 days · Good attendance · Enough balance · Sufficient notice</p>
          </div>
        </div>
        <div className="border-2 border-neo-black bg-neo-yellow p-4 flex gap-3 items-start">
          <Users size={22} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-display font-bold">Complex Leave → Sent to HR</p>
            <p className="font-mono text-xs mt-1">{'> 5 days · Low attendance · Maternity / Paternity / Special types'}</p>
          </div>
        </div>
      </div>

      {/* Balance */}
      {balance && (
        <NeoCard>
          <h3 className="font-display font-bold text-lg mb-4">Leave Balance</h3>
          <div className="flex flex-col gap-4">
            <BalanceBar label="Annual Leave"  total={balance.annual} used={balance.annual_used} color="bg-neo-teal" />
            <BalanceBar label="Sick Leave"    total={balance.sick}   used={balance.sick_used}   color="bg-neo-coral" />
            <BalanceBar label="Casual Leave"  total={balance.casual} used={balance.casual_used} color="bg-neo-yellow" />
          </div>
        </NeoCard>
      )}

      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">My Leave Requests</h3>
        <DataTable columns={columns} data={requests} loading={loading} emptyMessage="No leave requests yet." />
      </NeoCard>

      <ApplyLeaveModal open={modalOpen} onClose={() => setModalOpen(false)} onSuccess={handleSuccess} />
      {aiResult && <AIDecisionModal result={aiResult} onClose={() => setAiResult(null)} />}
    </div>
  );
};

// ─── HR Leave View ────────────────────────────────────────────────────────────
const HRLeave = () => {
  const { addNotification } = useNotifications();
  const { user } = useAuth();
  const [pending, setPending]       = useState<LeaveRequest[]>([]);
  const [all, setAll]               = useState<LeaveRequest[]>([]);
  const [balance, setBalance]       = useState<LeaveBalance | null>(null);
  const [loading, setLoading]       = useState(true);
  const [processing, setProcessing] = useState<number | null>(null);
  const [cancelling, setCancelling] = useState<number | null>(null);
  const [modalOpen, setModalOpen]   = useState(false);
  const [aiResult, setAiResult]     = useState<AIResult | null>(null);

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

  const handleCancel = async (id: number) => {
    setCancelling(id);
    try {
      await leaveApi.cancel(id);
      addNotification('success', 'Leave Cancelled', `Leave request #${id} cancelled. Balance restored if applicable.`);
      loadData();
    } catch (err: any) {
      addNotification('error', 'Cancel Failed', err?.response?.data?.detail ?? 'Could not cancel leave.');
    } finally {
      setCancelling(null);
    }
  };

  const historyColumns: Column<LeaveRequest>[] = [
    { key: 'employee_name', header: 'Employee', render: (r: any) => (
      <div className="flex flex-col">
        <span className="font-mono text-xs text-gray-400">{r.employee_number ?? `#${r.employee_id}`}</span>
        <span className="font-mono text-sm font-semibold">{r.employee_name || '—'}</span>
      </div>
    )},
    { key: 'leave_type', header: 'Type',   render: r => <span className="capitalize font-mono text-sm">{r.leave_type}</span> },
    { key: 'from_date',  header: 'From',   render: r => <span className="font-mono text-sm">{r.from_date}</span> },
    { key: 'to_date',    header: 'To',     render: r => <span className="font-mono text-sm">{r.to_date}</span> },
    { key: 'days',       header: 'Days',   render: r => <span className="font-mono text-sm">{r.days}</span> },
    { key: 'status',     header: 'Status', render: r => <StatusBadge status={r.status} /> },
    { key: 'id',         header: 'Actions', render: r => {
      // HR/management can cancel their own approved leave before it starts
      const isOwn      = r.employee_id === user?.id;
      const notStarted = new Date(r.from_date) > new Date();
      const canCancel  =
        isOwn && (
          r.status === 'pending' ||
          r.status === 'escalated' ||
          (r.status === 'approved' && notStarted)
        );
      return canCancel ? (
        <NeoButton variant="danger" size="sm" icon={<XIcon size={14} />}
          loading={cancelling === r.id} onClick={() => handleCancel(r.id)}>Cancel</NeoButton>
      ) : null;
    }},
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Leave Management"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Leave' }]}
        action={
          <NeoButton variant="primary" icon={<Send size={16} />} onClick={() => setModalOpen(true)}>
            Request Leave
          </NeoButton>
        }
      />

      {/* Escalated / Pending Approvals */}
      <div>
        <h3 className="font-display font-bold text-xl mb-4 flex items-center gap-2">
          <Users size={20} />
          Pending HR Approvals
          <span className="text-neo-coral">({pending.length})</span>
        </h3>
        {loading ? (
          <div className="grid gap-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="skeleton h-24 border-2 border-neo-black" />
            ))}
          </div>
        ) : pending.length === 0 ? (
          <NeoCard color="bg-neo-teal">
            <p className="font-display font-bold text-center py-4">All caught up! No pending leaves.</p>
          </NeoCard>
        ) : (
          <div className="grid gap-3">
            {pending.map(l => (
              <NeoCard key={l.id} className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-display font-bold text-base">{l.employee_name}</p>
                    <span className="font-mono text-xs text-gray-500 capitalize border border-neo-black px-1.5">{l.leave_type}</span>
                    {l.status === 'escalated' && (
                      <span className="font-mono text-xs bg-neo-yellow border border-neo-black px-1.5">Escalated by AI</span>
                    )}
                  </div>
                  <p className="font-mono text-sm text-gray-600">{l.from_date} → {l.to_date} ({l.days} days)</p>
                  <p className="font-mono text-xs text-gray-500 mt-1 italic">"{l.reason}"</p>
                </div>
                <div className="flex gap-2">
                  <NeoButton variant="teal" size="sm" icon={<Check size={14} />}
                    loading={processing === l.id} onClick={() => handleAction(l.id, 'approve')}>Approve</NeoButton>
                  <NeoButton variant="danger" size="sm" icon={<XIcon size={14} />}
                    loading={processing === l.id} onClick={() => handleAction(l.id, 'reject')}>Reject</NeoButton>
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
            <BalanceBar label="Sick Leave"   total={balance.sick}   used={balance.sick_used}   color="bg-neo-coral" />
            <BalanceBar label="Casual Leave" total={balance.casual} used={balance.casual_used} color="bg-neo-yellow" />
          </div>
        </NeoCard>
      )}

      {/* All Requests */}
      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">All Leave Requests</h3>
        <DataTable columns={historyColumns} data={all} loading={loading} emptyMessage="No leave requests found." />
      </NeoCard>

      <ApplyLeaveModal open={modalOpen} onClose={() => setModalOpen(false)} onSuccess={r => { setAiResult(r); loadData(); }} />
      {aiResult && <AIDecisionModal result={aiResult} onClose={() => setAiResult(null)} />}
    </div>
  );
};

// ─── Main ─────────────────────────────────────────────────────────────────────
export const Leave = () => {
  const { role } = useAuth();
  if (role === 'hr_admin' || role === 'management') return <HRLeave />;
  return <EmployeeLeave />;
};
