import React, { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { AttendanceRecord } from '../types';
import { attendanceApi } from '../services/api';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoInput, NeoSelect } from '../components/ui/NeoInput';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable, Column } from '../components/ui/DataTable';

const statusOptions = [
  { value: 'all', label: 'All Status' },
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
];

export const Attendance = () => {
  const today = new Date().toISOString().split('T')[0];
  const [date, setDate] = useState(today);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [filtered, setFiltered] = useState<AttendanceRecord[]>([]);
  const [status, setStatus] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    attendanceApi.list(date).then(data => { setRecords(data); }).finally(() => setLoading(false));
  }, [date]);

  useEffect(() => {
    if (status === 'all') setFiltered(records);
    else setFiltered(records.filter(r => r.status === status));
  }, [records, status]);

  const summary = {
    present: records.filter(r => r.status === 'present').length,
    absent: records.filter(r => r.status === 'absent').length,
    late: records.filter(r => r.status === 'late').length,
    total: records.length,
  };

  const exportCSV = () => {
    const headers = ['Employee ID', 'Employee Name', 'Check In', 'Check Out', 'Hours', 'Status', 'Check-in Lat', 'Check-in Lng', 'Check-out Lat', 'Check-out Lng'];
    const rows = filtered.map(r => [r.employee_number || '', r.employee_name, r.check_in || '', r.check_out || '', r.hours || '', r.status, r.latitude || '', r.longitude || '', r.checkout_latitude || '', r.checkout_longitude || '']);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `attendance-${date}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const columns: Column<AttendanceRecord>[] = [
    {
      key: 'employee_number', header: 'Employee ID',
      render: r => <span className="font-mono text-xs text-gray-500">{r.employee_number || '—'}</span>,
    },
    {
      key: 'employee_name', header: 'Name',
      render: r => <span className="font-display font-semibold text-sm">{r.employee_name || '—'}</span>,
    },
    { key: 'check_in', header: 'Check In', render: r => <span className="font-mono text-sm">{r.check_in || '—'}</span> },
    { key: 'check_out', header: 'Check Out', render: r => <span className="font-mono text-sm">{r.check_out || '—'}</span> },
    { key: 'hours', header: 'Hours', render: r => <span className="font-mono text-sm">{r.hours ? `${r.hours}h` : '—'}</span> },
    { key: 'status', header: 'Status', render: r => <StatusBadge status={r.status} /> },
    {
      key: 'location', header: 'Check-in GPS',
      render: r => r.latitude && r.longitude
        ? <a href={`https://maps.google.com/?q=${r.latitude},${r.longitude}`} target="_blank" rel="noreferrer" className="font-mono text-xs text-blue-600 underline">{r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}</a>
        : <span className="font-mono text-sm text-gray-400">—</span>,
    },
    {
      key: 'checkout_latitude', header: 'Check-out GPS',
      render: r => r.checkout_latitude && r.checkout_longitude
        ? <a href={`https://maps.google.com/?q=${r.checkout_latitude},${r.checkout_longitude}`} target="_blank" rel="noreferrer" className="font-mono text-xs text-blue-600 underline">{r.checkout_latitude.toFixed(5)}, {r.checkout_longitude.toFixed(5)}</a>
        : <span className="font-mono text-sm text-gray-400">—</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Attendance"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Attendance' }]}
        action={
          <NeoButton variant="secondary" icon={<Download size={16} />} onClick={exportCSV}>
            Export CSV
          </NeoButton>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <NeoCard color="bg-white" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-gray-500">Total</p>
          <p className="font-display font-bold text-2xl">{summary.total}</p>
        </NeoCard>
        <NeoCard color="bg-neo-teal" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Present</p>
          <p className="font-display font-bold text-2xl">{summary.present}</p>
        </NeoCard>
        <NeoCard color="bg-neo-coral" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Absent</p>
          <p className="font-display font-bold text-2xl">{summary.absent}</p>
        </NeoCard>
        <NeoCard color="bg-neo-yellow" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Late</p>
          <p className="font-display font-bold text-2xl">{summary.late}</p>
        </NeoCard>
      </div>

      {/* Filters */}
      <NeoCard className="flex flex-col sm:flex-row gap-3 items-end">
        <NeoInput
          label="Date"
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          className="sm:w-44"
        />
        <div className="sm:w-48">
          <NeoSelect
            label="Status Filter"
            value={status}
            onChange={e => setStatus(e.target.value)}
            options={statusOptions}
          />
        </div>
      </NeoCard>

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        emptyMessage="No attendance records for this date."
      />
    </div>
  );
};
