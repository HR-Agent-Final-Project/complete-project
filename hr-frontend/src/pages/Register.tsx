import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, Eye, EyeOff, CheckCircle, Clock } from 'lucide-react';
import { authApi } from '../services/api';
import { NeoButton } from '../components/ui/NeoButton';
import { NeoInput } from '../components/ui/NeoInput';

type RequestedRole = 'hr_admin' | 'management';

const roleOptions: { value: RequestedRole; label: string; description: string }[] = [
  { value: 'hr_admin',    label: 'HR Admin',    description: 'Manage employees, leave & attendance' },
  { value: 'management',  label: 'Management',  description: 'Reports, analytics & oversight' },
];

export const Register = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    first_name:       '',
    last_name:        '',
    personal_email:   '',
    phone_number:     '',
    password:         '',
    confirm_password: '',
    requested_role:   'hr_admin' as RequestedRole,
  });
  const [showPw, setShowPw]           = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');
  const [submitted, setSubmitted]     = useState(false);

  const set = (field: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(f => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!form.first_name || !form.last_name || !form.personal_email || !form.password || !form.confirm_password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8 || !/[A-Z]/.test(form.password) || !/\d/.test(form.password)) {
      setError('Password must be at least 8 characters with one uppercase letter and one number.');
      return;
    }

    setLoading(true);
    try {
      await authApi.selfRegister({
        first_name:       form.first_name,
        last_name:        form.last_name,
        personal_email:   form.personal_email,
        password:         form.password,
        confirm_password: form.confirm_password,
        requested_role:   form.requested_role,
        phone_number:     form.phone_number || undefined,
      });
      setSubmitted(true);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors — flatten to readable string
        setError(detail.map((e: any) => e.msg ?? JSON.stringify(e)).join(' | '));
      } else if (!err?.response) {
        setError('Cannot reach the server. Is the backend running on port 8080?');
      } else {
        setError(`Error ${err.response.status}: ${JSON.stringify(err.response.data)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neo-bg flex items-center justify-center p-4">
      {/* Background pattern */}
      <div
        className="fixed inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage:
            'repeating-linear-gradient(45deg, #0A0A0A 0, #0A0A0A 1px, transparent 0, transparent 50%)',
          backgroundSize: '20px 20px',
        }}
      />

      <div className="w-full max-w-5xl relative">
        <div className="flex border-4 border-neo-black shadow-neo-lg overflow-hidden bg-white">
          {/* Left side — Image panel (hidden on mobile) */}
          <div className="hidden lg:block w-2/5 relative overflow-hidden">
            <img
              src="/meatting.jpg"
              alt="Meeting"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-neo-black/80 via-neo-black/30 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-neo-yellow border-4 border-white shadow-neo flex items-center justify-center">
                  <Bot size={24} className="text-neo-black" />
                </div>
                <div>
                  <h1 className="font-display font-bold text-3xl text-white leading-none">HRAgent</h1>
                  <div className="h-1 bg-neo-yellow mt-0.5 w-20" />
                </div>
              </div>
              <p className="font-display font-bold text-lg text-white leading-snug">
                Join Our HR Platform
              </p>
              <p className="font-mono text-xs text-white/70 mt-2">
                Register to manage your organization's workforce with AI-powered tools
              </p>
            </div>
          </div>

          {/* Right side — Form */}
          <div className="w-full lg:w-3/5 flex flex-col">
            {/* Mobile logo */}
            <div className="flex items-center gap-3 p-6 pb-0 lg:hidden">
              <div className="w-10 h-10 bg-neo-yellow border-3 border-neo-black shadow-neo flex items-center justify-center">
                <Bot size={20} className="text-neo-black" />
              </div>
              <div>
                <h1 className="font-display font-bold text-2xl text-neo-black leading-none">HRAgent</h1>
                <div className="h-0.5 bg-neo-yellow border-y border-neo-black mt-0.5" />
              </div>
            </div>

            {submitted ? (
              /* Pending Approval State */
              <>
                <div className="bg-neo-teal border-b-4 border-neo-black px-6 py-4 flex items-center gap-3">
                  <Clock size={20} className="text-neo-black" />
                  <div>
                    <h2 className="font-display font-bold text-xl text-neo-black">Pending Approval</h2>
                    <p className="font-mono text-xs text-neo-black/70 mt-0.5">Registration submitted successfully</p>
                  </div>
                </div>

                <div className="p-6 flex flex-col gap-4">
                  <div className="border-2 border-neo-black bg-neo-yellow/20 p-4">
                    <div className="flex items-start gap-3">
                      <CheckCircle size={20} className="text-neo-black mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="font-display font-bold text-sm text-neo-black">
                          Your request has been sent!
                        </p>
                        <p className="font-mono text-xs text-gray-600 mt-1">
                          An approval request has been emailed to{' '}
                          <span className="font-bold text-neo-black">hr.agent.automation@gmail.com</span>.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="border-2 border-neo-black p-4 flex flex-col gap-2">
                    <p className="font-mono font-semibold text-xs uppercase tracking-wider text-neo-black">What happens next?</p>
                    {[
                      'HR receives your approval request by email',
                      'They review your details and click the approval link',
                      'You receive a confirmation email once approved',
                      'You can then log in with your email and password',
                    ].map((step, i) => (
                      <div key={i} className="flex items-start gap-2 mt-1">
                        <span className="w-5 h-5 border-2 border-neo-black bg-neo-yellow flex items-center justify-center font-mono font-bold text-xs flex-shrink-0">
                          {i + 1}
                        </span>
                        <p className="font-mono text-xs text-gray-700">{step}</p>
                      </div>
                    ))}
                  </div>

                  <NeoButton variant="secondary" size="lg" className="w-full" onClick={() => navigate('/login')}>
                    Back to Login
                  </NeoButton>
                </div>
              </>
            ) : (
              /* Registration Form */
              <>
                <div className="bg-neo-yellow border-b-4 border-neo-black px-6 py-4">
                  <h2 className="font-display font-bold text-xl text-neo-black">Create Account</h2>
                  <p className="font-mono text-xs text-neo-black/70 mt-0.5">
                    HR Admin &amp; Management — requires approval
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
                  {/* Role selector */}
                  <div>
                    <p className="font-mono font-semibold text-xs uppercase tracking-wider text-neo-black mb-2">
                      Requested Role
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {roleOptions.map(r => (
                        <button
                          key={r.value}
                          type="button"
                          onClick={() => setForm(f => ({ ...f, requested_role: r.value }))}
                          className={`
                            p-3 border-2 border-neo-black text-left transition-all
                            ${form.requested_role === r.value
                              ? 'bg-neo-teal shadow-none translate-x-[2px] translate-y-[2px]'
                              : 'bg-white shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none'
                            }
                          `}
                        >
                          <p className="font-display font-bold text-xs text-neo-black">{r.label}</p>
                          <p className="font-mono text-xs text-gray-500 mt-0.5">{r.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Name row */}
                  <div className="grid grid-cols-2 gap-3">
                    <NeoInput
                      label="First Name *"
                      type="text"
                      value={form.first_name}
                      onChange={set('first_name')}
                      placeholder="Dilani"
                      autoComplete="given-name"
                    />
                    <NeoInput
                      label="Last Name *"
                      type="text"
                      value={form.last_name}
                      onChange={set('last_name')}
                      placeholder="Fernando"
                      autoComplete="family-name"
                    />
                  </div>

                  <NeoInput
                    label="Email Address *"
                    type="email"
                    value={form.personal_email}
                    onChange={set('personal_email')}
                    placeholder="you@example.com"
                    autoComplete="email"
                  />

                  <NeoInput
                    label="Phone Number"
                    type="tel"
                    value={form.phone_number}
                    onChange={set('phone_number')}
                    placeholder="077 123 4567"
                    autoComplete="tel"
                  />

                  {/* Password */}
                  <div>
                    <p className="font-mono font-semibold text-xs uppercase tracking-wider text-neo-black mb-1">
                      Password *
                    </p>
                    <div className="relative">
                      <input
                        type={showPw ? 'text' : 'password'}
                        value={form.password}
                        onChange={set('password')}
                        className="w-full border-2 border-neo-black bg-white px-3 py-2 pr-10 font-mono text-sm text-neo-black outline-none focus:ring-2 focus:ring-neo-yellow placeholder:text-gray-400"
                        placeholder="Min 8 chars, 1 uppercase, 1 number"
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPw(v => !v)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-neo-black"
                      >
                        {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <p className="font-mono font-semibold text-xs uppercase tracking-wider text-neo-black mb-1">
                      Confirm Password *
                    </p>
                    <div className="relative">
                      <input
                        type={showConfirm ? 'text' : 'password'}
                        value={form.confirm_password}
                        onChange={set('confirm_password')}
                        className="w-full border-2 border-neo-black bg-white px-3 py-2 pr-10 font-mono text-sm text-neo-black outline-none focus:ring-2 focus:ring-neo-yellow placeholder:text-gray-400"
                        placeholder="Re-enter password"
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirm(v => !v)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-neo-black"
                      >
                        {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {error && (
                    <div className="border-2 border-neo-coral bg-neo-coral/10 px-3 py-2">
                      <p className="font-mono text-xs text-neo-coral font-semibold">{error}</p>
                    </div>
                  )}

                  <NeoButton type="submit" variant="primary" size="lg" loading={loading} className="w-full mt-2">
                    Submit Registration
                  </NeoButton>

                  <p className="text-center font-mono text-xs text-gray-500">
                    Already have an account?{' '}
                    <Link to="/login" className="text-neo-black font-bold underline underline-offset-2">
                      Sign In
                    </Link>
                  </p>
                </form>
              </>
            )}
          </div>
        </div>

        <p className="text-center font-mono text-xs text-gray-400 mt-4">
          University of Vocational Technology, Sri Lanka — FYP 2026
        </p>
      </div>
    </div>
  );
};
