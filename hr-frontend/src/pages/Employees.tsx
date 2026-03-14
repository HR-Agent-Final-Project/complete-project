import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Edit2, Copy, CheckCircle, Camera } from 'lucide-react';
import { Employee } from '../types';
import { employeeApi, departmentApi, roleApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoInput, NeoSelect } from '../components/ui/NeoInput';
import { NeoModal } from '../components/ui/NeoModal';
import { NeoCard } from '../components/ui/NeoCard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable, Column } from '../components/ui/DataTable';
import { useNotifications } from '../context/NotificationContext';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Dept { id: number; name: string; code: string }
interface Role { id: number; title: string; access_level: number }

interface RegisterForm {
  // Personal
  first_name: string;
  last_name: string;
  personal_email: string;
  phone_number: string;
  nic_number: string;
  date_of_birth: string;
  gender: string;
  // Address
  address: string;
  city: string;
  district: string;
  // Employment
  department_id: string;
  role_id: string;
  employment_type: string;
  // Financial
  base_salary: string;
  bank_account: string;
  bank_name: string;
  // Preferences
  language_pref: string;
}

const BLANK_FORM: RegisterForm = {
  first_name: '', last_name: '', personal_email: '', phone_number: '',
  nic_number: '', date_of_birth: '', gender: '',
  address: '', city: '', district: '',
  department_id: '', role_id: '', employment_type: 'full_time',
  base_salary: '', bank_account: '', bank_name: '',
  language_pref: 'en',
};

// ─── Component ────────────────────────────────────────────────────────────────
export const Employees = () => {
  const navigate = useNavigate();
  const { role: userRole } = useAuth();
  const { addNotification } = useNotifications();

  const canManage = userRole === 'hr_admin' || userRole === 'management';

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [filtered, setFiltered]   = useState<Employee[]>([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState('');
  const [deptFilter, setDeptFilter] = useState('All');

  const [departments, setDepartments] = useState<Dept[]>([]);
  const [roles, setRoles]             = useState<Role[]>([]);

  // Modals
  const [addModal, setAddModal]         = useState(false);
  const [editEmployee, setEditEmployee] = useState<Employee | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Employee | null>(null);
  const [credentials, setCredentials]   = useState<{ employee_number: string; temp_password: string; email: string; email_sent: boolean } | null>(null);

  const [form, setForm] = useState<RegisterForm>(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Face / photo
  const photoInputRef = useRef<HTMLInputElement>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  // Copied state for credentials modal
  const [copied, setCopied] = useState<'id' | 'pw' | null>(null);

  // ── Load data ──
  useEffect(() => {
    Promise.allSettled([
      employeeApi.list(),
      departmentApi.list(),
      roleApi.list(),
    ]).then(([empRes, deptRes, roleRes]) => {
      if (empRes.status === 'fulfilled') { setEmployees(empRes.value); setFiltered(empRes.value); }
      if (deptRes.status === 'fulfilled') setDepartments(deptRes.value);
      if (roleRes.status === 'fulfilled') setRoles(roleRes.value);
    }).finally(() => setLoading(false));
  }, []);

  // ── Filter ──
  useEffect(() => {
    let result = employees;
    if (search) result = result.filter(e =>
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      e.email.toLowerCase().includes(search.toLowerCase()) ||
      e.employee_id?.toLowerCase().includes(search.toLowerCase())
    );
    if (deptFilter !== 'All') result = result.filter(e => e.department === deptFilter);
    setFiltered(result);
  }, [search, deptFilter, employees]);

  // ── Photo selection ──
  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const f = (key: keyof RegisterForm, val: string) =>
    setForm(prev => ({ ...prev, [key]: val }));

  // ── Register employee ──
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.first_name || !form.last_name || !form.personal_email) {
      addNotification('error', 'Validation Error', 'First name, last name, and email are required.');
      return;
    }
    setSaving(true);
    try {
      const payload: Record<string, any> = {
        first_name:      form.first_name.trim(),
        last_name:       form.last_name.trim(),
        personal_email:  form.personal_email.trim(),
        phone_number:    form.phone_number || undefined,
        nic_number:      form.nic_number || undefined,
        date_of_birth:   form.date_of_birth || undefined,
        gender:          form.gender || undefined,
        address:         form.address || undefined,
        city:            form.city || undefined,
        district:        form.district || undefined,
        department_id:   form.department_id ? parseInt(form.department_id) : undefined,
        role_id:         form.role_id ? parseInt(form.role_id) : undefined,
        employment_type: form.employment_type,
        base_salary:     form.base_salary ? parseFloat(form.base_salary) : undefined,
        bank_account:    form.bank_account || undefined,
        bank_name:       form.bank_name || undefined,
        language_pref:   form.language_pref,
      };

      const result = await employeeApi.register(payload);

      // Enroll face for biometric attendance if photo selected
      if (photoFile && result.employee_id) {
        try {
          const base64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve((reader.result as string).split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(photoFile);
          });
          await employeeApi.enrollFace(result.employee_id, base64);
        } catch (_) {}
      }

      // Reload employee list
      const fresh = await employeeApi.list();
      setEmployees(fresh);

      setAddModal(false);
      setForm(BLANK_FORM);
      setPhotoFile(null);
      setPhotoPreview(null);

      // Show credentials dialog
      setCredentials({
        employee_number: result.employee_number,
        temp_password:   result.temp_password,
        email:           result.email,
        email_sent:      result.email_sent ?? false,
      });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      addNotification('error', 'Registration Failed', detail || 'Could not register employee.');
    } finally {
      setSaving(false);
    }
  };

  // ── Edit employee ──
  const openEdit = (emp: Employee) => {
    const raw = emp as any;
    setForm({
      first_name:      emp.name.split(' ')[0] ?? '',
      last_name:       emp.name.split(' ').slice(1).join(' ') ?? '',
      personal_email:  emp.email,
      phone_number:    emp.phone ?? '',
      nic_number:      raw.nic_number ?? '',
      date_of_birth:   raw.date_of_birth ?? '',
      gender:          raw.gender ?? '',
      address:         emp.address ?? raw.address ?? '',
      city:            raw.city ?? '',
      district:        raw.district ?? '',
      department_id:   raw.department_id ? String(raw.department_id) : '',
      role_id:         raw.role_id ? String(raw.role_id) : '',
      employment_type: raw.employment_type ?? 'full_time',
      base_salary:     emp.salary ? String(emp.salary) : '',
      bank_account:    raw.bank_account ?? '',
      bank_name:       raw.bank_name ?? '',
      language_pref:   raw.language_pref ?? 'en',
    });
    setEditEmployee(emp);
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editEmployee) return;
    setSaving(true);
    try {
      const payload: Record<string, any> = {
        first_name:      form.first_name.trim(),
        last_name:       form.last_name.trim(),
        phone_number:    form.phone_number || undefined,
        address:         form.address || undefined,
        city:            form.city || undefined,
        district:        form.district || undefined,
        department_id:   form.department_id ? parseInt(form.department_id) : undefined,
        role_id:         form.role_id ? parseInt(form.role_id) : undefined,
        employment_type: form.employment_type,
        base_salary:     form.base_salary ? parseFloat(form.base_salary) : undefined,
        bank_account:    form.bank_account || undefined,
        bank_name:       form.bank_name || undefined,
        language_pref:   form.language_pref,
      };

      await employeeApi.update(editEmployee.id, payload);

      // Enroll face if a new photo was selected
      if (photoFile) {
        try {
          const base64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve((reader.result as string).split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(photoFile);
          });
          await employeeApi.enrollFace(editEmployee.id, base64);
        } catch (_) {}
      }

      const fresh = await employeeApi.list();
      setEmployees(fresh);
      setEditEmployee(null);
      setForm(BLANK_FORM);
      setPhotoFile(null);
      setPhotoPreview(null);
      addNotification('success', 'Employee Updated', `${form.first_name} ${form.last_name} updated successfully.`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      addNotification('error', 'Update Failed', detail || 'Could not update employee.');
    } finally {
      setSaving(false);
    }
  };

  // ── Delete employee ──
  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await employeeApi.delete(deleteTarget.id);
      setEmployees(prev => prev.filter(e => e.id !== deleteTarget.id));
      addNotification('success', 'Employee Removed', `${deleteTarget.name} has been removed from the system.`);
      setDeleteTarget(null);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      addNotification('error', 'Delete Failed', detail || 'Could not delete employee.');
    } finally {
      setDeleting(false);
    }
  };

  // ── Copy to clipboard ──
  const copyToClipboard = async (text: string, which: 'id' | 'pw') => {
    await navigator.clipboard.writeText(text);
    setCopied(which);
    setTimeout(() => setCopied(null), 2000);
  };

  // ── Table columns ──
  const columns: Column<Employee>[] = [
    { key: 'employee_id', header: 'ID', width: '100px',
      render: e => <span className="font-mono text-xs font-bold bg-neo-yellow px-1.5 py-0.5 border border-neo-black">{e.employee_id}</span> },
    { key: 'name', header: 'Name',
      render: e => (
        <div>
          <p className="font-display font-semibold text-sm">{e.name}</p>
          <p className="font-mono text-xs text-gray-500">{e.email}</p>
        </div>
      ),
    },
    { key: 'department', header: 'Department' },
    { key: 'position',   header: 'Position' },
    { key: 'status', header: 'Status', width: '100px',
      render: e => <StatusBadge status={e.status} /> },
    { key: 'actions', header: 'Actions', width: '140px',
      render: e => (
        <div className="flex gap-1" onClick={ev => ev.stopPropagation()}>
          <NeoButton size="sm" variant="secondary" onClick={() => navigate(`/employees/${e.id}`)}>View</NeoButton>
          {canManage && (
            <>
              <NeoButton size="sm" variant="secondary" onClick={() => openEdit(e)}>
                <Edit2 size={12} />
              </NeoButton>
              <NeoButton size="sm" variant="secondary" onClick={() => setDeleteTarget(e)}
                className="!border-neo-coral !text-neo-coral hover:!bg-neo-coral hover:!text-white">
                <Trash2 size={12} />
              </NeoButton>
            </>
          )}
        </div>
      ),
    },
  ];

  // ── Department options ──
  const deptOptions = [
    { value: '', label: 'Select department...' },
    ...departments.map(d => ({ value: String(d.id), label: d.name })),
  ];
  const roleOptions = [
    { value: '', label: 'Select role...' },
    ...roles.map(r => ({ value: String(r.id), label: r.title })),
  ];
  const filterDepts = ['All', ...departments.map(d => d.name)];

  // ── Shared form body (called as function, NOT as <Component/>) ──
  const formBody = (isEdit = false) => (
    <div className="flex flex-col gap-4 max-h-[75vh] overflow-y-auto pr-1">
      {/* Face Recognition Photo */}
      <div className="flex items-center gap-4 border-2 border-dashed border-neo-black p-3 bg-neo-yellow/10">
        <div className="relative w-20 h-20 border-2 border-neo-black bg-gray-100 overflow-hidden flex-shrink-0">
          {photoPreview
            ? <img src={photoPreview} className="w-full h-full object-cover" alt="face preview" />
            : <Camera size={28} className="absolute inset-0 m-auto text-gray-400" />}
        </div>
        <div>
          <p className="font-mono text-xs font-bold mb-0.5">Face Recognition Photo</p>
          <p className="font-mono text-xs text-gray-500 mb-2">Used for biometric attendance identification</p>
          <NeoButton type="button" size="sm" variant="secondary" onClick={() => photoInputRef.current?.click()}>
            {isEdit ? 'Change Face Photo' : 'Upload Face Photo'}
          </NeoButton>
          <input ref={photoInputRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={handlePhotoChange} />
          <p className="font-mono text-xs text-gray-400 mt-1">Clear face photo · JPEG or PNG · max 5 MB</p>
        </div>
      </div>

      {/* Section: Personal Information */}
      <div className="border-t-2 border-neo-black pt-3">
        <p className="font-display font-bold text-sm mb-3 bg-neo-yellow px-2 py-1 inline-block border-2 border-neo-black">Personal Information</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <NeoInput label="First Name *" value={form.first_name} onChange={e => f('first_name', e.target.value)} required />
          <NeoInput label="Last Name *"  value={form.last_name}  onChange={e => f('last_name',  e.target.value)} required />
          <NeoInput label="Personal Email *" type="email" value={form.personal_email} onChange={e => f('personal_email', e.target.value)} required />
          <NeoInput label="Phone Number" value={form.phone_number} onChange={e => f('phone_number', e.target.value)} placeholder="+94 771 234 567" />
          <NeoInput label="NIC Number" value={form.nic_number} onChange={e => f('nic_number', e.target.value)} placeholder="200012345678" />
          <NeoInput label="Date of Birth" type="date" value={form.date_of_birth} onChange={e => f('date_of_birth', e.target.value)} />
          <NeoSelect label="Gender" value={form.gender} onChange={e => f('gender', e.target.value)}
            options={[
              { value: '', label: 'Select...' },
              { value: 'male', label: 'Male' },
              { value: 'female', label: 'Female' },
              { value: 'other', label: 'Other' },
            ]} />
          <NeoSelect label="Language" value={form.language_pref} onChange={e => f('language_pref', e.target.value)}
            options={[
              { value: 'en', label: 'English' },
              { value: 'si', label: 'Sinhala' },
              { value: 'ta', label: 'Tamil' },
            ]} />
        </div>
      </div>

      {/* Section: Address */}
      <div className="border-t-2 border-neo-black pt-3">
        <p className="font-display font-bold text-sm mb-3 bg-neo-teal px-2 py-1 inline-block border-2 border-neo-black">Address</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="col-span-1 sm:col-span-2">
            <NeoInput label="Address" value={form.address} onChange={e => f('address', e.target.value)} placeholder="No. 123, Main Street" />
          </div>
          <NeoInput label="City"     value={form.city}     onChange={e => f('city',     e.target.value)} placeholder="Colombo" />
          <NeoInput label="District" value={form.district} onChange={e => f('district', e.target.value)} placeholder="Western" />
        </div>
      </div>

      {/* Section: Employment */}
      <div className="border-t-2 border-neo-black pt-3">
        <p className="font-display font-bold text-sm mb-3 bg-neo-yellow px-2 py-1 inline-block border-2 border-neo-black">Employment</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <NeoSelect label="Department" value={form.department_id} onChange={e => f('department_id', e.target.value)} options={deptOptions} />
          <NeoSelect label="Role / Position" value={form.role_id} onChange={e => f('role_id', e.target.value)} options={roleOptions} />
          <NeoSelect label="Employment Type" value={form.employment_type} onChange={e => f('employment_type', e.target.value)}
            options={[
              { value: 'full_time', label: 'Full Time' },
              { value: 'part_time', label: 'Part Time' },
              { value: 'contract',  label: 'Contract' },
              { value: 'intern',    label: 'Intern' },
            ]} />
        </div>
      </div>

      {/* Section: Financial */}
      <div className="border-t-2 border-neo-black pt-3">
        <p className="font-display font-bold text-sm mb-3 bg-white px-2 py-1 inline-block border-2 border-neo-black">Financial Details</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <NeoInput label="Basic Salary (LKR)" type="number" value={form.base_salary} onChange={e => f('base_salary', e.target.value)} placeholder="0.00" />
          <NeoInput label="Bank Name"    value={form.bank_name}    onChange={e => f('bank_name',    e.target.value)} placeholder="Bank of Ceylon" />
          <div className="col-span-1 sm:col-span-2">
            <NeoInput label="Bank Account Number" value={form.bank_account} onChange={e => f('bank_account', e.target.value)} placeholder="0001234567890" />
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Employees"
        breadcrumbs={[{ label: 'Dashboard' }, { label: 'Employees' }]}
        action={canManage ? (
          <NeoButton variant="primary" icon={<Plus size={16} />} onClick={() => { setForm(BLANK_FORM); setPhotoFile(null); setPhotoPreview(null); setAddModal(true); }}>
            Add Employee
          </NeoButton>
        ) : undefined}
      />

      {/* Filters */}
      <NeoCard className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <NeoInput placeholder="Search by name, email, or Employee ID..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="sm:w-48">
          <NeoSelect value={deptFilter} onChange={e => setDeptFilter(e.target.value)}
            options={filterDepts.map(d => ({ value: d, label: d }))} />
        </div>
      </NeoCard>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Total',    value: employees.length,                                   color: 'bg-white' },
          { label: 'Active',   value: employees.filter(e => e.status === 'active').length, color: 'bg-neo-teal' },
          { label: 'On Leave', value: employees.filter(e => e.status === 'on_leave').length, color: 'bg-neo-yellow' },
        ].map(s => (
          <NeoCard key={s.label} color={s.color} padding="p-3">
            <p className="font-mono text-xs uppercase tracking-wider text-neo-black/60">{s.label}</p>
            <p className="font-display font-bold text-2xl">{s.value}</p>
          </NeoCard>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        onRowClick={e => navigate(`/employees/${e.id}`)}
        emptyMessage="No employees match your search."
      />

      {/* ── Add Employee Modal ── */}
      <NeoModal open={addModal} onClose={() => setAddModal(false)} title="Register New Employee" width="max-w-2xl">
        <form onSubmit={handleRegister}>
          {formBody()}
          <div className="flex gap-3 justify-end pt-4 border-t-2 border-neo-black mt-4">
            <NeoButton type="button" variant="secondary" onClick={() => setAddModal(false)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Register Employee</NeoButton>
          </div>
        </form>
      </NeoModal>

      {/* ── Edit Employee Modal ── */}
      <NeoModal open={!!editEmployee} onClose={() => { setEditEmployee(null); setPhotoFile(null); setPhotoPreview(null); }} title={`Edit — ${editEmployee?.name}`} width="max-w-2xl">
        <form onSubmit={handleEdit}>
          {formBody(true)}
          <div className="flex gap-3 justify-end pt-4 border-t-2 border-neo-black mt-4">
            <NeoButton type="button" variant="secondary" onClick={() => setEditEmployee(null)}>Cancel</NeoButton>
            <NeoButton type="submit" variant="primary" loading={saving}>Save Changes</NeoButton>
          </div>
        </form>
      </NeoModal>

      {/* ── Delete Confirmation Modal ── */}
      <NeoModal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Confirm Deletion" width="max-w-sm">
        {deleteTarget && (
          <div className="flex flex-col gap-4">
            <div className="border-2 border-neo-coral bg-neo-coral/10 p-3">
              <p className="font-mono text-sm">
                You are about to <strong>permanently delete</strong> the account for:
              </p>
              <p className="font-display font-bold text-lg mt-1">{deleteTarget.name}</p>
              <p className="font-mono text-xs text-gray-500">{deleteTarget.employee_id} · {deleteTarget.email}</p>
              <p className="font-mono text-xs mt-2 text-neo-coral font-semibold">This action cannot be undone.</p>
            </div>
            <div className="flex gap-3 justify-end">
              <NeoButton variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</NeoButton>
              <NeoButton
                variant="primary"
                loading={deleting}
                onClick={handleDelete}
                className="!bg-neo-coral !border-neo-coral !text-white"
              >
                Delete Employee
              </NeoButton>
            </div>
          </div>
        )}
      </NeoModal>

      {/* ── Credentials Modal (shown after successful registration) ── */}
      <NeoModal open={!!credentials} onClose={() => setCredentials(null)} title="Employee Registered" width="max-w-md" headerColor="bg-neo-teal">
        {credentials && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle size={20} className="text-neo-teal" />
              <p className="font-display font-semibold">Registration successful!</p>
            </div>
            <p className="font-mono text-xs text-gray-600">
              Share these credentials with the employee. They must change the password on first login.
            </p>

            {credentials.email_sent ? (
              <div className="border-2 border-neo-teal bg-neo-teal/10 px-3 py-2">
                <p className="font-mono text-xs font-semibold text-neo-black">
                  ✓ Credentials emailed to <strong>{credentials.email}</strong>
                </p>
              </div>
            ) : (
              <div className="border-2 border-neo-yellow bg-neo-yellow/20 px-3 py-2">
                <p className="font-mono text-xs font-semibold">Email not configured — share credentials manually.</p>
              </div>
            )}

            <div className="border-2 border-neo-black">
              <div className="flex items-center justify-between px-4 py-3 border-b-2 border-neo-black bg-gray-50">
                <div>
                  <p className="font-mono text-xs text-gray-500 uppercase tracking-wide">Employee ID</p>
                  <p className="font-mono font-bold text-xl mt-0.5">{credentials.employee_number}</p>
                </div>
                <button onClick={() => copyToClipboard(credentials.employee_number, 'id')}
                  className="flex items-center gap-1 font-mono text-xs border-2 border-neo-black px-2 py-1 hover:bg-neo-yellow transition-colors">
                  {copied === 'id' ? <CheckCircle size={12} className="text-neo-teal" /> : <Copy size={12} />}
                  {copied === 'id' ? 'Copied' : 'Copy'}
                </button>
              </div>
              <div className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-mono text-xs text-gray-500 uppercase tracking-wide">Temp Password</p>
                  <p className="font-mono font-bold text-xl mt-0.5">{credentials.temp_password}</p>
                </div>
                <button onClick={() => copyToClipboard(credentials.temp_password, 'pw')}
                  className="flex items-center gap-1 font-mono text-xs border-2 border-neo-black px-2 py-1 hover:bg-neo-yellow transition-colors">
                  {copied === 'pw' ? <CheckCircle size={12} className="text-neo-teal" /> : <Copy size={12} />}
                  {copied === 'pw' ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>

            <div className="flex justify-end">
              <NeoButton variant="primary" onClick={() => setCredentials(null)}>Done</NeoButton>
            </div>
          </div>
        )}
      </NeoModal>
    </div>
  );
};
