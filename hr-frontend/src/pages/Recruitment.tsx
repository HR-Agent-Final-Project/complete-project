import React, { useEffect, useState } from 'react';
import { Plus, Users, Calendar, ChevronRight } from 'lucide-react';
import { Job, Applicant } from '../types';
import { recruitmentApi } from '../services/api';
import { useNotifications } from '../context/NotificationContext';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoModal } from '../components/ui/NeoModal';
import { NeoInput, NeoSelect, NeoTextarea } from '../components/ui/NeoInput';
import { StatusBadge } from '../components/ui/StatusBadge';

const deptOptions = ['Engineering', 'Human Resources', 'Finance', 'Marketing', 'Sales'].map(d => ({ value: d, label: d }));

const AI_SCORE_COLOR = (score?: number) => {
  if (!score) return 'bg-gray-200';
  if (score >= 80) return 'bg-neo-teal';
  if (score >= 60) return 'bg-neo-yellow';
  return 'bg-neo-coral';
};

export const Recruitment = () => {
  const { addNotification } = useNotifications();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [applicantsLoading, setApplicantsLoading] = useState(false);
  const [newJobModal, setNewJobModal] = useState(false);
  const [form, setForm] = useState({
    title: '', department: 'Engineering', description: '', requirements: '', salary_range: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    recruitmentApi.listJobs().then(setJobs).finally(() => setLoading(false));
  }, []);

  const openJob = async (job: Job) => {
    setSelectedJob(job);
    setApplicantsLoading(true);
    try {
      const apps = await recruitmentApi.getApplicants(job.id);
      setApplicants(apps);
    } finally {
      setApplicantsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const created = await recruitmentApi.createJob({
        ...form, status: 'active', posted_date: new Date().toISOString().split('T')[0], applications_count: 0,
      });
      setJobs(prev => [created, ...prev]);
      setNewJobModal(false);
      setForm({ title: '', department: 'Engineering', description: '', requirements: '', salary_range: '' });
      addNotification('success', 'Job Posted', `${form.title} has been posted successfully.`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Recruitment"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Recruitment' }]}
        action={
          <NeoButton variant="primary" icon={<Plus size={16} />} onClick={() => setNewJobModal(true)}>
            Post New Job
          </NeoButton>
        }
      />

      {/* Job Stats */}
      <div className="grid grid-cols-3 gap-3">
        <NeoCard color="bg-neo-teal" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Active Jobs</p>
          <p className="font-display font-bold text-2xl">{jobs.filter(j => j.status === 'active').length}</p>
        </NeoCard>
        <NeoCard color="bg-neo-yellow" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Total Applicants</p>
          <p className="font-display font-bold text-2xl">{jobs.reduce((a, j) => a + j.applications_count, 0)}</p>
        </NeoCard>
        <NeoCard color="bg-white" padding="p-3">
          <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">Closed Jobs</p>
          <p className="font-display font-bold text-2xl">{jobs.filter(j => j.status === 'closed').length}</p>
        </NeoCard>
      </div>

      {/* Jobs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {loading ? Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="border-2 border-neo-black shadow-neo p-4 bg-white">
            <div className="skeleton h-5 w-2/3 mb-3 rounded" />
            <div className="skeleton h-3 w-1/2 mb-2 rounded" />
            <div className="skeleton h-3 w-1/3 rounded" />
          </div>
        )) : jobs.map(job => (
          <div key={job.id}
            className="border-2 border-neo-black shadow-neo bg-white hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo-sm transition-all cursor-pointer"
            onClick={() => openJob(job)}
          >
            <div className={`border-b-2 border-neo-black px-4 py-3 flex items-center justify-between ${job.status === 'active' ? 'bg-neo-teal' : 'bg-gray-200'}`}>
              <StatusBadge status={job.status} />
              <span className="font-mono text-xs">{job.department}</span>
            </div>
            <div className="p-4">
              <h3 className="font-display font-bold text-base mb-2">{job.title}</h3>
              <p className="font-mono text-xs text-gray-500 line-clamp-2 mb-3">{job.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 font-mono text-xs text-gray-500">
                    <Users size={12} />{job.applications_count} applicants
                  </span>
                  <span className="flex items-center gap-1 font-mono text-xs text-gray-500">
                    <Calendar size={12} />{job.posted_date}
                  </span>
                </div>
                <ChevronRight size={16} className="text-gray-400" />
              </div>
              {job.salary_range && (
                <p className="font-mono text-xs font-bold mt-2 border-t border-black/10 pt-2">{job.salary_range}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Applicants Modal */}
      <NeoModal
        open={!!selectedJob}
        onClose={() => setSelectedJob(null)}
        title={selectedJob?.title || ''}
        width="max-w-2xl"
        headerColor="bg-neo-teal"
      >
        {selectedJob && (
          <div className="flex flex-col gap-4">
            <div className="flex gap-4 flex-wrap">
              <div><p className="font-mono text-xs text-gray-500">Department</p><p className="font-display font-bold text-sm">{selectedJob.department}</p></div>
              <div><p className="font-mono text-xs text-gray-500">Posted</p><p className="font-display font-bold text-sm">{selectedJob.posted_date}</p></div>
              <div><p className="font-mono text-xs text-gray-500">Applicants</p><p className="font-display font-bold text-sm">{selectedJob.applications_count}</p></div>
              {selectedJob.salary_range && <div><p className="font-mono text-xs text-gray-500">Salary</p><p className="font-display font-bold text-sm">{selectedJob.salary_range}</p></div>}
            </div>
            <div className="border-t-2 border-neo-black pt-3">
              <h4 className="font-display font-bold text-base mb-3">Applicants</h4>
              {applicantsLoading ? (
                <div className="flex flex-col gap-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="skeleton h-12 rounded" />)}</div>
              ) : applicants.length === 0 ? (
                <p className="font-mono text-sm text-gray-500 text-center py-4">No applicants yet.</p>
              ) : (
                <div className="border-2 border-neo-black overflow-hidden">
                  <table className="neo-table">
                    <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>AI Score</th><th>Interview</th></tr></thead>
                    <tbody>
                      {applicants.map(a => (
                        <tr key={a.id}>
                          <td className="font-display font-semibold text-sm">{a.name}</td>
                          <td className="font-mono text-xs">{a.email}</td>
                          <td><StatusBadge status={a.status} /></td>
                          <td>
                            {a.ai_score !== undefined && (
                              <span className={`inline-block px-2 py-0.5 text-xs font-mono font-bold border-2 border-neo-black ${AI_SCORE_COLOR(a.ai_score)}`}>
                                {a.ai_score}
                              </span>
                            )}
                          </td>
                          <td><StatusBadge status={a.interview_status || 'pending'} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </NeoModal>

      {/* New Job Modal */}
      <NeoModal open={newJobModal} onClose={() => setNewJobModal(false)} title="Post New Job" width="max-w-lg">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <NeoInput label="Job Title" required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
          <NeoSelect label="Department" value={form.department}
            onChange={e => setForm(f => ({ ...f, department: e.target.value }))}
            options={deptOptions} />
          <NeoTextarea label="Description" required value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Job description..." />
          <NeoTextarea label="Requirements" value={form.requirements}
            onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))}
            placeholder="Required skills and experience..." />
          <NeoInput label="Salary Range (optional)" value={form.salary_range}
            onChange={e => setForm(f => ({ ...f, salary_range: e.target.value }))}
            placeholder="e.g. LKR 80,000 - 120,000" />
          <div className="flex gap-3 justify-end pt-2 border-t-2 border-neo-black">
            <NeoButton type="button" variant="secondary" onClick={() => setNewJobModal(false)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Post Job</NeoButton>
          </div>
        </form>
      </NeoModal>
    </div>
  );
};
