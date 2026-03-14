import React, { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';
import { PerformanceRecord, Employee } from '../types';
import { performanceApi, employeeApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoModal } from '../components/ui/NeoModal';
import { NeoInput, NeoSelect, NeoTextarea } from '../components/ui/NeoInput';
import { DataTable, Column } from '../components/ui/DataTable';

export const Performance = () => {
  const { role } = useAuth();
  const { addNotification } = useNotifications();
  const [records, setRecords] = useState<PerformanceRecord[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<PerformanceRecord | null>(null);
  const [addModal, setAddModal] = useState(false);
  const [form, setForm] = useState({
    employee_id: '', period: 'Q1 2026',
    punctuality: 80, task_completion: 80, attendance_rate: 90, overtime_hours: 5, notes: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    performanceApi.list().then(setRecords).finally(() => setLoading(false));
    employeeApi.list().then(setEmployees).catch(() => {});
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const emp = employees.find((e: Employee) => e.id === parseInt(form.employee_id));
      const overall = Math.round((form.punctuality + form.task_completion + form.attendance_rate) / 3);
      const created = await performanceApi.evaluate({
        ...form,
        employee_id: parseInt(form.employee_id),
        employee_name: emp?.name || 'Unknown',
        department: emp?.department || '',
        overall_score: overall,
        evaluated_by: 'HR Admin',
        evaluated_at: new Date().toISOString().split('T')[0],
      });
      setRecords(prev => [created, ...prev]);
      setAddModal(false);
      addNotification('success', 'Evaluation Added', 'Performance evaluation saved successfully.');
    } finally {
      setSaving(false);
    }
  };

  const chartData = records.map(r => ({
    name: r.employee_name.split(' ')[0],
    punctuality: r.punctuality,
    tasks: r.task_completion,
    attendance: r.attendance_rate,
    overall: r.overall_score,
  }));

  const radarData = selected ? [
    { metric: 'Punctuality', value: selected.punctuality },
    { metric: 'Tasks', value: selected.task_completion },
    { metric: 'Attendance', value: selected.attendance_rate },
    { metric: 'Overall', value: selected.overall_score },
  ] : [];

  const columns: Column<PerformanceRecord>[] = [
    { key: 'employee_name', header: 'Employee', render: r => <span className="font-display font-semibold text-sm">{r.employee_name}</span> },
    { key: 'department', header: 'Dept', render: r => <span className="font-mono text-xs">{r.department}</span> },
    { key: 'period', header: 'Period', render: r => <span className="font-mono text-xs">{r.period}</span> },
    {
      key: 'overall_score', header: 'Score',
      render: r => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-gray-200 border border-neo-black">
            <div className={`h-full ${r.overall_score >= 85 ? 'bg-neo-teal' : r.overall_score >= 70 ? 'bg-neo-yellow' : 'bg-neo-coral'}`}
              style={{ width: `${r.overall_score}%` }} />
          </div>
          <span className="font-mono text-sm font-bold">{r.overall_score}</span>
        </div>
      ),
    },
    {
      key: 'actions', header: '', width: '80px',
      render: r => <NeoButton size="sm" variant="secondary" onClick={ev => { ev.stopPropagation(); setSelected(r); }}>Detail</NeoButton>,
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Performance"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Performance' }]}
        action={role !== 'employee' ? (
          <NeoButton variant="primary" icon={<Plus size={16} />} onClick={() => setAddModal(true)}>Add Evaluation</NeoButton>
        ) : undefined}
      />

      {/* Team Bar Chart */}
      <NeoCard>
        <h3 className="font-display font-bold text-lg mb-4">Team Performance Comparison</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#0A0A0A20" />
            <XAxis dataKey="name" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
            <YAxis domain={[0, 100]} tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} />
            <Tooltip contentStyle={{ border: '2px solid #0A0A0A', fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
            <Bar dataKey="overall" fill="#FFE135" stroke="#0A0A0A" strokeWidth={1} name="Overall Score" />
            <Bar dataKey="tasks" fill="#00C9B1" stroke="#0A0A0A" strokeWidth={1} name="Tasks" />
          </BarChart>
        </ResponsiveContainer>
      </NeoCard>

      <DataTable columns={columns} data={records} loading={loading} onRowClick={setSelected} emptyMessage="No performance data." />

      {/* Detail Modal */}
      <NeoModal open={!!selected} onClose={() => setSelected(null)} title={`Performance — ${selected?.employee_name}`} width="max-w-lg">
        {selected && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <div>
                <p className="font-mono text-xs text-gray-500">Period</p>
                <p className="font-display font-bold">{selected.period}</p>
              </div>
              <div>
                <p className="font-mono text-xs text-gray-500">Overall Score</p>
                <p className="font-display font-bold text-2xl">{selected.overall_score}/100</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                <Radar dataKey="value" fill="#FFE135" fillOpacity={0.5} stroke="#0A0A0A" strokeWidth={2} />
                <Tooltip contentStyle={{ border: '2px solid #0A0A0A', fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
            {selected.notes && (
              <div className="border-2 border-neo-black bg-neo-yellow/20 p-3">
                <p className="font-mono text-xs">{selected.notes}</p>
              </div>
            )}
          </div>
        )}
      </NeoModal>

      {/* Add Evaluation Modal */}
      <NeoModal open={addModal} onClose={() => setAddModal(false)} title="Add Evaluation" width="max-w-lg">
        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          <NeoSelect
            label="Employee"
            value={form.employee_id}
            onChange={e => setForm(f => ({ ...f, employee_id: e.target.value }))}
            options={[
              { value: '', label: 'Select employee...' },
              ...employees.filter((e: Employee) => e.role === 'employee').map((e: Employee) => ({ value: String(e.id), label: e.name })),
            ]}
          />
          <NeoInput label="Period" value={form.period} onChange={e => setForm(f => ({ ...f, period: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: 'punctuality', label: 'Punctuality (0-100)' },
              { key: 'task_completion', label: 'Task Completion (0-100)' },
              { key: 'attendance_rate', label: 'Attendance Rate (0-100)' },
              { key: 'overtime_hours', label: 'Overtime Hours' },
            ].map(f => (
              <NeoInput key={f.key} label={f.label} type="number" min="0" max="100"
                value={(form as any)[f.key]}
                onChange={e => setForm(prev => ({ ...prev, [f.key]: parseInt(e.target.value) || 0 }))} />
            ))}
          </div>
          <NeoTextarea label="Notes (optional)" value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          <div className="flex gap-3 justify-end pt-2 border-t-2 border-neo-black">
            <NeoButton type="button" variant="secondary" onClick={() => setAddModal(false)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Save Evaluation</NeoButton>
          </div>
        </form>
      </NeoModal>
    </div>
  );
};
