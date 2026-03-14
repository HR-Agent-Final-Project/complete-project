import React, { useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Save, Upload, Bell, User, Lock, Shield, AlertTriangle, CheckCircle, Camera } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import { userApi, employeeApi } from '../services/api';
import { PageHeader } from '../components/ui/PageHeader';
import { NeoCard } from '../components/ui/NeoCard';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoInput } from '../components/ui/NeoInput';

type Tab = 'profile' | 'notifications' | 'system';

export const Settings = () => {
  const { user, login, token, role } = useAuth();
  const { addNotification } = useNotifications();
  const location = useLocation();

  // Detect forced password change (redirected from first login)
  const forceChangePassword = (location.state as any)?.forceChangePassword === true;

  const [tab, setTab] = useState<Tab>('profile');
  const [profile, setProfile] = useState({ name: user?.name || '', email: user?.email || '', phone: user?.phone || '' });
  const [passwords, setPasswords] = useState({ current: '', new_pw: '', confirm: '' });
  const [pwError, setPwError]     = useState('');
  const [pwSuccess, setPwSuccess] = useState(false);
  const [notifPrefs, setNotifPrefs] = useState({ email_leave: true, email_attendance: false, email_payslip: true, email_announcement: true });
  const [saving, setSaving]   = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  // Profile photo
  const photoRef = useRef<HTMLInputElement>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(user?.avatar || null);
  const [photoSaving, setPhotoSaving] = useState(false);

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await userApi.updateProfile(profile);
      if (token) login(token, { ...user!, ...updated });
      addNotification('success', 'Profile Updated', 'Your profile has been saved.');
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess(false);

    if (!passwords.current) { setPwError('Please enter your current password.'); return; }
    if (passwords.new_pw.length < 8) { setPwError('New password must be at least 8 characters.'); return; }
    if (!/[A-Z]/.test(passwords.new_pw)) { setPwError('New password must contain at least one uppercase letter.'); return; }
    if (!/[0-9]/.test(passwords.new_pw)) { setPwError('New password must contain at least one number.'); return; }
    if (passwords.new_pw !== passwords.confirm) { setPwError('New passwords do not match.'); return; }

    setSaving(true);
    try {
      await userApi.changePassword(passwords.current, passwords.new_pw, passwords.confirm);
      setPwSuccess(true);
      setPasswords({ current: '', new_pw: '', confirm: '' });
      addNotification('success', 'Password Changed', 'Your password has been updated. Please log in again.');
      // Log out after password change so they re-authenticate
      setTimeout(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }, 2000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setPwError(detail || 'Failed to change password. Check your current password and try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    setUploadedFiles(prev => [...prev, ...files.map(f => f.name)]);
    addNotification('success', 'Policy Uploaded', `${files.length} file(s) uploaded to the knowledge base.`);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setUploadedFiles(prev => [...prev, ...files.map(f => f.name)]);
    if (files.length) addNotification('success', 'Policy Uploaded', `${files.length} file(s) uploaded.`);
  };

  const handlePhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user?.id) return;
    setPhotoPreview(URL.createObjectURL(file));
    setPhotoSaving(true);
    try {
      const url = await employeeApi.uploadPhoto(user.id, file);
      if (token) login(token, { ...user!, avatar: url });
      addNotification('success', 'Photo Updated', 'Your profile photo has been changed.');
    } catch {
      addNotification('error', 'Upload Failed', 'Could not update profile photo.');
    } finally {
      setPhotoSaving(false);
    }
  };

  const tabs: { key: Tab; label: string; icon: React.ReactNode; roles?: string[] }[] = [
    { key: 'profile', label: 'Profile', icon: <User size={16} /> },
    { key: 'notifications', label: 'Notifications', icon: <Bell size={16} /> },
    { key: 'system', label: 'System', icon: <Shield size={16} />, roles: ['hr_admin', 'management'] },
  ];

  const Toggle = ({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) => (
    <div className="flex items-center justify-between py-2 border-b border-black/10 last:border-0">
      <span className="font-mono text-sm">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`w-12 h-6 border-2 border-neo-black transition-all relative ${checked ? 'bg-neo-teal' : 'bg-gray-200'}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 bg-white border-2 border-neo-black transition-all ${checked ? 'right-0.5' : 'left-0.5'}`} />
      </button>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto w-full relative">
      {/* Background image with yellow circle accents */}
      <div className="absolute -top-6 -right-6 w-64 h-64 rounded-full bg-neo-yellow/10 pointer-events-none hidden lg:block" />
      <div className="absolute top-1/3 -left-10 w-32 h-32 rounded-full bg-neo-teal/10 pointer-events-none hidden lg:block" />
      <div className="absolute bottom-20 right-10 w-20 h-20 rounded-full bg-neo-yellow/15 pointer-events-none hidden lg:block" />

      <div className="relative">
        <PageHeader title="Settings" breadcrumbs={[{ label: 'Dashboard' }, { label: 'Settings' }]} />
      </div>

      {/* Hero banner */}
      <div className="relative bg-white border-2 border-neo-black/10 overflow-hidden rounded-sm">
        <div className="absolute -top-8 -right-8 w-40 h-40 rounded-full bg-neo-yellow/20 pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-20 h-20 rounded-full bg-neo-teal/10 pointer-events-none" />
        <div className="relative p-6 flex items-center gap-5">
          <div className="relative flex-shrink-0 hidden sm:block">
            <div className="w-16 h-16 rounded-full bg-neo-yellow/30 absolute -top-1 -left-1" />
            <div className="w-16 h-16 border-2 border-neo-black overflow-hidden relative rounded-full">
              <img src="/watching.jpg" alt="" className="w-full h-full object-cover" />
            </div>
          </div>
          <div>
            <h2 className="font-display font-bold text-2xl text-neo-black">
              Account <span className="relative">Settings<span className="absolute -bottom-1 left-0 w-full h-2 bg-neo-yellow/40 -z-10" /></span>
            </h2>
            <p className="font-mono text-sm text-neo-black/50 mt-1">Manage your profile, security, and preferences</p>
          </div>
        </div>
      </div>

      {/* ── Forced password change banner ── */}
      {forceChangePassword && !pwSuccess && (
        <div className="border-4 border-neo-coral bg-neo-coral/10 p-4 flex items-start gap-3">
          <AlertTriangle size={22} className="text-neo-coral flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-display font-bold text-base text-neo-coral">Action Required — Change Your Password</p>
            <p className="font-mono text-sm mt-1">
              You are logged in with a <strong>temporary password</strong> issued by HR.
              You must set a new personal password before using the system.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-2 border-neo-black overflow-x-auto">
        {tabs.filter(t => !t.roles || (role && t.roles.includes(role))).map((t, i) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 font-display font-bold text-sm border-neo-black transition-all
              ${i > 0 ? 'border-l-2' : ''}
              ${tab === t.key ? 'bg-neo-yellow' : 'bg-white hover:bg-neo-yellow/30'}
            `}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {tab === 'profile' && (
        <div className="flex flex-col gap-4">
          <NeoCard>
            <div className="flex items-center gap-4 mb-6 pb-4 border-b-2 border-neo-black">
              <div className="relative group">
                <div className="w-16 h-16 border-4 border-neo-black overflow-hidden flex items-center justify-center bg-neo-teal">
                  {photoPreview
                    ? <img src={photoPreview} className="w-full h-full object-cover" alt="profile" />
                    : <span className="font-display font-bold text-2xl text-neo-black">
                        {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </span>
                  }
                </div>
                <button
                  type="button"
                  onClick={() => photoRef.current?.click()}
                  disabled={photoSaving}
                  className="absolute inset-0 bg-neo-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                >
                  <Camera size={18} className="text-white" />
                </button>
                <input ref={photoRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={handlePhotoChange} />
              </div>
              <div>
                <p className="font-display font-bold text-lg">{user?.name}</p>
                <p className="font-mono text-sm text-gray-500 capitalize">{user?.role?.replace('_', ' ')} · {user?.department}</p>
                <p className="font-mono text-xs text-gray-400">{user?.employee_id}</p>
                <button
                  type="button"
                  onClick={() => photoRef.current?.click()}
                  disabled={photoSaving}
                  className="font-mono text-xs text-neo-black underline underline-offset-2 mt-0.5 hover:text-neo-teal"
                >
                  {photoSaving ? 'Uploading…' : 'Change photo'}
                </button>
              </div>
            </div>
            <form onSubmit={saveProfile} className="flex flex-col gap-4">
              <h3 className="font-display font-bold text-base flex items-center gap-2"><User size={16} /> Profile Information</h3>
              <NeoInput label="Full Name" value={profile.name} onChange={e => setProfile(p => ({ ...p, name: e.target.value }))} />
              <NeoInput label="Email Address" type="email" value={profile.email} onChange={e => setProfile(p => ({ ...p, email: e.target.value }))} />
              <NeoInput label="Phone Number" value={profile.phone} onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))} />
              <NeoButton type="submit" variant="primary" icon={<Save size={16} />} loading={saving} className="w-fit">
                Save Changes
              </NeoButton>
            </form>
          </NeoCard>

          {/* Change Password card */}
          <NeoCard className={forceChangePassword && !pwSuccess ? 'ring-4 ring-neo-coral ring-offset-2' : ''}>
            <form onSubmit={savePassword} className="flex flex-col gap-4">
              <h3 className="font-display font-bold text-base flex items-center gap-2">
                <Lock size={16} />
                {forceChangePassword ? 'Set New Password (Required)' : 'Change Password'}
              </h3>

              {forceChangePassword && !pwSuccess && (
                <div className="border-2 border-neo-coral bg-neo-coral/10 px-3 py-2">
                  <p className="font-mono text-xs font-semibold text-neo-coral">
                    Enter the temporary password sent to your email, then choose a new password.
                  </p>
                </div>
              )}

              {pwSuccess && (
                <div className="border-2 border-neo-teal bg-neo-teal/10 px-3 py-2 flex items-center gap-2">
                  <CheckCircle size={16} className="text-neo-teal" />
                  <p className="font-mono text-xs font-semibold text-neo-black">
                    Password changed! Redirecting to login...
                  </p>
                </div>
              )}

              {pwError && (
                <div className="border-2 border-neo-coral bg-neo-coral/10 px-3 py-2">
                  <p className="font-mono text-xs font-semibold text-neo-coral">{pwError}</p>
                </div>
              )}

              <NeoInput
                label="Current / Temporary Password"
                type="password"
                value={passwords.current}
                onChange={e => setPasswords(p => ({ ...p, current: e.target.value }))}
                placeholder="Enter your current or temp password"
              />
              <NeoInput
                label="New Password"
                type="password"
                value={passwords.new_pw}
                onChange={e => setPasswords(p => ({ ...p, new_pw: e.target.value }))}
                placeholder="Min 8 chars, 1 uppercase, 1 number"
              />
              <NeoInput
                label="Confirm New Password"
                type="password"
                value={passwords.confirm}
                onChange={e => setPasswords(p => ({ ...p, confirm: e.target.value }))}
                placeholder="Repeat new password"
              />

              {/* Password strength hint */}
              {passwords.new_pw && (
                <div className="flex gap-2 flex-wrap">
                  {[
                    { ok: passwords.new_pw.length >= 8,          label: '8+ chars' },
                    { ok: /[A-Z]/.test(passwords.new_pw),        label: 'Uppercase' },
                    { ok: /[0-9]/.test(passwords.new_pw),        label: 'Number' },
                    { ok: passwords.new_pw === passwords.confirm && !!passwords.confirm, label: 'Passwords match' },
                  ].map(r => (
                    <span key={r.label}
                      className={`font-mono text-xs px-2 py-0.5 border-2 border-neo-black ${r.ok ? 'bg-neo-teal' : 'bg-gray-100 text-gray-400'}`}>
                      {r.ok ? '✓' : '○'} {r.label}
                    </span>
                  ))}
                </div>
              )}

              <NeoButton
                type="submit"
                variant={forceChangePassword ? 'primary' : 'secondary'}
                icon={<Lock size={16} />}
                loading={saving}
                className="w-fit"
                disabled={pwSuccess}
              >
                {forceChangePassword ? 'Set New Password' : 'Update Password'}
              </NeoButton>
            </form>
          </NeoCard>
        </div>
      )}

      {/* Notifications Tab */}
      {tab === 'notifications' && (
        <NeoCard>
          <h3 className="font-display font-bold text-base flex items-center gap-2 mb-4"><Bell size={16} /> Email Notifications</h3>
          <Toggle label="Leave request updates" checked={notifPrefs.email_leave} onChange={v => setNotifPrefs(p => ({ ...p, email_leave: v }))} />
          <Toggle label="Attendance alerts" checked={notifPrefs.email_attendance} onChange={v => setNotifPrefs(p => ({ ...p, email_attendance: v }))} />
          <Toggle label="Payslip available" checked={notifPrefs.email_payslip} onChange={v => setNotifPrefs(p => ({ ...p, email_payslip: v }))} />
          <Toggle label="Company announcements" checked={notifPrefs.email_announcement} onChange={v => setNotifPrefs(p => ({ ...p, email_announcement: v }))} />
          <NeoButton variant="primary" icon={<Save size={16} />} className="mt-4 w-fit"
            onClick={() => addNotification('success', 'Preferences Saved', 'Notification settings updated.')}>
            Save Preferences
          </NeoButton>
        </NeoCard>
      )}

      {/* System Tab (HR Admin / Management only) */}
      {tab === 'system' && (
        <NeoCard>
          <h3 className="font-display font-bold text-base flex items-center gap-2 mb-2"><Shield size={16} /> RAG Policy Documents</h3>
          <p className="font-mono text-xs text-gray-500 mb-4">Upload HR policy documents to enhance AI responses. Supported: PDF, DOCX, TXT</p>

          <div
            className={`border-4 border-dashed border-neo-black p-8 text-center cursor-pointer transition-all ${dragOver ? 'bg-neo-yellow/30' : 'bg-white hover:bg-neo-yellow/10'}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={32} className="mx-auto mb-3 text-neo-black/40" />
            <p className="font-display font-bold text-base">Drop files here or click to upload</p>
            <p className="font-mono text-xs text-gray-500 mt-1">PDF, DOCX, TXT up to 10MB each</p>
            <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.txt" className="hidden" onChange={handleFileInput} />
          </div>

          {uploadedFiles.length > 0 && (
            <div className="mt-4 border-2 border-neo-black">
              <div className="bg-neo-teal border-b-2 border-neo-black px-3 py-2">
                <p className="font-mono text-xs font-bold uppercase">Uploaded Files ({uploadedFiles.length})</p>
              </div>
              {uploadedFiles.map((f, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 border-b border-black/10 last:border-0">
                  <span className="font-mono text-sm">{f}</span>
                  <button onClick={() => setUploadedFiles(prev => prev.filter((_, j) => j !== i))}
                    className="text-neo-coral font-mono text-xs hover:underline">Remove</button>
                </div>
              ))}
            </div>
          )}
        </NeoCard>
      )}
    </div>
  );
};
