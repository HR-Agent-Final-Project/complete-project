import React, { useState } from 'react';
import { Download, FileText, BarChart2 } from 'lucide-react';
import { ReportType, ReportData } from '../types';
import { reportsApi } from '../services/api';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoInput, NeoSelect } from '../components/ui/NeoInput';

const reportTypes: { value: ReportType; label: string }[] = [
  { value: 'attendance', label: 'Attendance Report' },
  { value: 'leave', label: 'Leave Report' },
  { value: 'performance', label: 'Performance Report' },
  { value: 'headcount', label: 'Headcount Report' },
];

export const Reports = () => {
  const today = new Date().toISOString().split('T')[0];
  const monthStart = today.slice(0, 7) + '-01';

  const [type, setType] = useState<ReportType>('attendance');
  const [from, setFrom] = useState(monthStart);
  const [to, setTo] = useState(today);
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const result = await reportsApi.generate(type, from, to);
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => {
    if (!data) return;
    const csv = [data.headers, ...data.rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${type}-report-${from}-${to}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Reports & Analytics"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Reports' }]}
      />

      {/* Controls */}
      <NeoCard className="flex flex-col sm:flex-row gap-4 items-end flex-wrap">
        <div className="sm:w-64">
          <NeoSelect
            label="Report Type"
            value={type}
            onChange={e => setType(e.target.value as ReportType)}
            options={reportTypes}
          />
        </div>
        <NeoInput label="From Date" type="date" value={from} onChange={e => setFrom(e.target.value)} className="sm:w-44" />
        <NeoInput label="To Date" type="date" value={to} onChange={e => setTo(e.target.value)} className="sm:w-44" />
        <NeoButton variant="primary" icon={<BarChart2 size={16} />} onClick={generate} loading={loading}>
          Generate
        </NeoButton>
        {data && (
          <NeoButton variant="secondary" icon={<Download size={16} />} onClick={exportCSV}>
            Export CSV
          </NeoButton>
        )}
      </NeoCard>

      {/* Summary Cards */}
      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {Object.entries(data.summary).map(([key, value]) => (
              <NeoCard key={key} color="bg-white" padding="p-3">
                <p className="font-mono text-xs uppercase tracking-wider text-gray-500">{key.replace(/_/g, ' ')}</p>
                <p className="font-display font-bold text-xl mt-1">{value}</p>
              </NeoCard>
            ))}
          </div>

          {/* Data Table */}
          <NeoCard>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-bold text-lg capitalize">{type} Report</h3>
              <span className="font-mono text-xs text-gray-500">{from} → {to}</span>
            </div>
            <div className="overflow-x-auto border-2 border-neo-black">
              <table className="neo-table">
                <thead>
                  <tr>{data.headers.map(h => <th key={h}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {data.rows.map((row, i) => (
                    <tr key={i}>{row.map((cell, j) => <td key={j} className="font-mono text-sm">{cell}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </NeoCard>
        </>
      )}

      {!data && !loading && (
        <NeoCard color="bg-neo-yellow/20" className="flex flex-col items-center justify-center py-16 gap-3">
          <FileText size={48} className="text-neo-black/30" />
          <p className="font-display font-bold text-lg text-neo-black/50">Select a report type and date range, then click Generate</p>
        </NeoCard>
      )}
    </div>
  );
};
