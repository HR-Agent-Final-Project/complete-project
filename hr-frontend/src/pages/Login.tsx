import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, Eye, EyeOff, User, ShieldCheck, ArrowRight, Sparkles, Fingerprint, BarChart3, Clock, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../services/api';
import { NeoButton } from '../components/ui/NeoButton';
import { useNotifications } from '../context/NotificationContext';

type LoginMode = 'employee' | 'hr';

/* ── Decorative shapes ── */
const Circle = ({ size, color, className }: { size: number; color: string; className?: string }) => (
  <div
    className={`absolute rounded-full border-[3px] border-neo-black pointer-events-none ${className}`}
    style={{ width: size, height: size, backgroundColor: color }}
  />
);
const Square = ({ size, color, className, rotate = 0 }: { size: number; color: string; className?: string; rotate?: number }) => (
  <div
    className={`absolute border-[3px] border-neo-black pointer-events-none ${className}`}
    style={{ width: size, height: size, backgroundColor: color, transform: `rotate(${rotate}deg)` }}
  />
);

/* ── Feature card ── */
const FeatureChip = ({ icon, label }: { icon: React.ReactNode; label: string }) => (
  <div className="flex items-center gap-2 px-3 py-2 bg-white border-2 border-neo-black shadow-neo-sm">
    <span className="text-neo-black">{icon}</span>
    <span className="font-mono text-[11px] font-bold text-neo-black whitespace-nowrap">{label}</span>
  </div>
);

export const Login = () => {
  const { login } = useAuth();
  const { addNotification } = useNotifications();
  const navigate = useNavigate();

  const [mode, setMode]       = useState<LoginMode>('employee');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword]     = useState('');
  const [showPw, setShowPw]   = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const switchMode = (m: LoginMode) => {
    setMode(m);
    setIdentifier('');
    setPassword('');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier || !password) { setError('Please fill in all fields.'); return; }
    setLoading(true);
    setError('');
    try {
      const { access_token, user, must_change_password } = await authApi.login(identifier, password);
      login(access_token, user);
      if (must_change_password) {
        addNotification('warning', 'Action Required', 'Please change your temporary password before continuing.');
        navigate('/settings', { state: { forceChangePassword: true } });
      } else {
        addNotification('success', 'Welcome back!', `Logged in as ${user.name}`);
        navigate('/dashboard');
      }
    } catch (err: any) {
      const st     = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (st === 429)      setError(detail || 'Too many attempts. Try again later.');
      else if (st === 403) setError(detail || 'Account pending approval.');
      else                 setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isEmployee = mode === 'employee';

  return (
    <div className="min-h-screen bg-neo-bg flex flex-col overflow-hidden">
      {/* ── Top nav ── */}
      <nav className="flex items-center justify-between px-5 md:px-8 py-4 border-b-2 border-neo-black/10 relative z-20">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-neo-yellow border-2 border-neo-black shadow-neo-sm flex items-center justify-center rounded-sm">
            <Bot size={18} className="text-neo-black" />
          </div>
          <div>
            <span className="font-display font-bold text-lg text-neo-black leading-none">HRAgent</span>
            <span className="hidden sm:inline font-mono text-[10px] text-neo-black/40 ml-2 uppercase tracking-widest">AI-Powered</span>
          </div>
        </div>
        <Link to="/register" className="font-display font-bold text-xs text-neo-black border-2 border-neo-black px-4 py-1.5 bg-white
          shadow-neo-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] hover:bg-neo-yellow transition-all">
          Sign Up
        </Link>
      </nav>

      {/* ── Main content ── */}
      <div className="flex-1 flex items-center justify-center px-4 py-6 md:py-8 relative">

        {/* Background decorative shapes — hidden on small screens */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.12] hidden md:block">
          <Circle size={200} color="#FFE135" className="-top-16 -left-16" />
          <Circle size={120} color="#00C9B1" className="top-1/4 -right-8" />
          <Square size={80} color="#FF6B6B" className="bottom-20 left-12" rotate={15} />
          <Circle size={60} color="#4D96FF" className="top-16 right-1/4" />
          <Square size={50} color="#FFE135" className="bottom-1/3 right-16" rotate={-20} />
          <Circle size={90} color="#FF6B6B" className="-bottom-10 right-1/3" />
          <Square size={40} color="#00C9B1" className="top-1/2 left-1/4" rotate={45} />
        </div>

        <div className="w-full max-w-6xl flex flex-col lg:flex-row items-center gap-8 lg:gap-16 relative z-10">

          {/* ── Left side — Hero + Images ── */}
          <div className="flex-1 max-w-xl w-full">
            {/* Mobile: compact hero */}
            <div className="text-center lg:text-left">
              <h1 className="font-display font-bold text-4xl md:text-5xl lg:text-6xl text-neo-black leading-[1.1]">
                Welcome
                <br />
                <span className="relative inline-block">
                  To HR World!
                  <span className="absolute -bottom-1 left-0 w-full h-3 bg-neo-yellow/60 -z-10" />
                </span>
              </h1>
              <p className="font-mono text-sm md:text-base text-neo-black/50 mt-3 md:mt-4 max-w-md mx-auto lg:mx-0 leading-relaxed">
                Sign in to manage your workforce with intelligent automation and AI-powered tools.
              </p>
            </div>

            {/* ── Mobile image strip (visible < lg) ── */}
            <div className="flex gap-3 mt-6 lg:hidden overflow-x-auto pb-2 -mx-1 px-1">
              <div className="w-28 h-36 flex-shrink-0 border-2 border-neo-black shadow-neo-sm overflow-hidden">
                <img src="/group.jpg" alt="Team" className="w-full h-full object-cover" />
              </div>
              <div className="w-28 h-36 flex-shrink-0 border-2 border-neo-black shadow-neo-sm overflow-hidden mt-4">
                <img src="/meatting.jpg" alt="Meeting" className="w-full h-full object-cover" />
              </div>
              <div className="w-28 h-36 flex-shrink-0 border-2 border-neo-black shadow-neo-sm overflow-hidden">
                <img src="/talk.jpg" alt="Discussion" className="w-full h-full object-cover" />
              </div>
              <div className="w-28 h-36 flex-shrink-0 border-2 border-neo-black shadow-neo-sm overflow-hidden mt-4">
                <img src={isEmployee ? '/watching.jpg' : '/Digital Workshop.jpg'} alt="Work" className="w-full h-full object-cover" />
              </div>
            </div>

            {/* ── Desktop image collage (visible >= lg) ── */}
            <div className="relative mt-10 hidden lg:block">
              {/* Decorative accents */}
              <Circle size={48} color="#FFE135" className="-top-5 -left-5 shadow-neo-sm z-10" />
              <Circle size={32} color="#00C9B1" className="bottom-8 -right-4 shadow-neo-sm z-10" />
              <Square size={28} color="#FF6B6B" className="-bottom-3 left-20 shadow-neo-sm z-10" rotate={20} />

              <div className="flex gap-4 relative">
                {/* Column 1 */}
                <div className="flex flex-col gap-4">
                  <div className="w-44 h-52 border-[3px] border-neo-black overflow-hidden shadow-neo">
                    <img src="/group.jpg" alt="Team collaboration" className="w-full h-full object-cover hover:scale-105 transition-transform duration-500" />
                  </div>
                  <div className="w-44 h-28 border-[3px] border-neo-black overflow-hidden shadow-neo bg-neo-yellow flex items-center justify-center">
                    <div className="text-center p-3">
                      <p className="font-display font-black text-2xl">500+</p>
                      <p className="font-mono text-[10px] font-bold uppercase tracking-wider">Employees</p>
                    </div>
                  </div>
                </div>

                {/* Column 2 — offset */}
                <div className="flex flex-col gap-4 mt-10">
                  <div className="w-44 h-40 border-[3px] border-neo-black overflow-hidden shadow-neo">
                    <img src="/meatting.jpg" alt="Team meeting" className="w-full h-full object-cover hover:scale-105 transition-transform duration-500" />
                  </div>
                  <div className="w-44 h-40 border-[3px] border-neo-black overflow-hidden shadow-neo">
                    <img src={isEmployee ? '/watching.jpg' : '/Digital Workshop.jpg'} alt="Working" className="w-full h-full object-cover hover:scale-105 transition-transform duration-500" />
                  </div>
                </div>

                {/* Column 3 */}
                <div className="flex flex-col gap-4 -mt-2">
                  <div className="w-44 h-48 border-[3px] border-neo-black overflow-hidden shadow-neo">
                    <img src="/talk.jpg" alt="Discussion" className="w-full h-full object-cover hover:scale-105 transition-transform duration-500" />
                  </div>
                  <div className="w-44 h-32 border-[3px] border-neo-black overflow-hidden shadow-neo bg-neo-teal flex items-center justify-center">
                    <div className="text-center p-3">
                      <Fingerprint size={28} className="mx-auto mb-1" />
                      <p className="font-mono text-[10px] font-bold uppercase tracking-wider">Face Recognition</p>
                      <p className="font-mono text-[9px] text-neo-black/60">Attendance</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Feature chips — desktop */}
            <div className="hidden lg:flex flex-wrap gap-2 mt-6">
              <FeatureChip icon={<Sparkles size={12} />} label="AI Assistant" />
              <FeatureChip icon={<BarChart3 size={12} />} label="Smart Analytics" />
              <FeatureChip icon={<Clock size={12} />} label="Attendance" />
              <FeatureChip icon={<Users size={12} />} label="Team Management" />
            </div>
          </div>

          {/* ── Right side — Login card ── */}
          <div className="w-full max-w-md">
            {/* Mode toggle */}
            <div className="flex gap-2 mb-5">
              <button
                type="button"
                onClick={() => switchMode('employee')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 font-display font-bold text-sm border-2 border-neo-black transition-all
                  ${isEmployee
                    ? 'bg-neo-yellow shadow-none translate-x-[2px] translate-y-[2px]'
                    : 'bg-white shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none'}`}
              >
                <User size={15} />
                Employee
              </button>
              <button
                type="button"
                onClick={() => switchMode('hr')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 font-display font-bold text-sm border-2 border-neo-black transition-all
                  ${!isEmployee
                    ? 'bg-neo-black text-neo-yellow shadow-none translate-x-[2px] translate-y-[2px]'
                    : 'bg-white shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none'}`}
              >
                <ShieldCheck size={15} />
                HR / Manager
              </button>
            </div>

            {/* Login card */}
            <div className="bg-white border-[3px] border-neo-black shadow-neo-lg">
              {/* Card header */}
              <div className={`px-6 py-4 border-b-[3px] border-neo-black relative overflow-hidden
                ${isEmployee ? 'bg-neo-yellow/20' : 'bg-neo-black'}`}>
                {/* Mini decorative shapes in header */}
                <Circle size={40} color={isEmployee ? '#FFE135' : '#00C9B1'}
                  className="-top-3 -right-3 opacity-30 !border-2" />
                <Square size={24} color={isEmployee ? '#00C9B1' : '#FFE135'}
                  className="bottom-1 right-10 opacity-20 !border-2" rotate={15} />

                <div className="relative z-10">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 border-2 border-neo-black flex items-center justify-center rounded-full
                      ${isEmployee ? 'bg-neo-yellow' : 'bg-neo-yellow'}`}>
                      {isEmployee ? <User size={18} /> : <ShieldCheck size={18} />}
                    </div>
                    <div>
                      <h2 className={`font-display font-bold text-lg ${isEmployee ? 'text-neo-black' : 'text-neo-yellow'}`}>
                        {isEmployee ? 'Employee Sign In' : 'HR / Manager Sign In'}
                      </h2>
                      <p className={`font-mono text-[11px] ${isEmployee ? 'text-neo-black/50' : 'text-white/40'}`}>
                        {isEmployee ? 'Use your Employee ID to sign in' : 'Use your email address to sign in'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
                <div>
                  <label className="font-mono font-semibold text-[11px] uppercase tracking-wider text-neo-black/60 mb-2 block">
                    {isEmployee ? 'Employee ID' : 'Email Address'}
                  </label>
                  <div className="relative">
                    <input
                      key={mode}
                      type={isEmployee ? 'text' : 'email'}
                      value={identifier}
                      onChange={e => setIdentifier(e.target.value)}
                      className="w-full border-2 border-neo-black/15 bg-neo-bg/50 px-4 py-3 font-mono text-sm outline-none
                        focus:border-neo-yellow focus:bg-white transition-all placeholder:text-gray-300"
                      placeholder={isEmployee ? 'e.g. IT0001' : 'you@company.com'}
                      autoComplete="off"
                    />
                  </div>
                </div>

                <div>
                  <label className="font-mono font-semibold text-[11px] uppercase tracking-wider text-neo-black/60 mb-2 block">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPw ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      className="w-full border-2 border-neo-black/15 bg-neo-bg/50 px-4 py-3 pr-12 font-mono text-sm outline-none
                        focus:border-neo-yellow focus:bg-white transition-all placeholder:text-gray-300"
                      placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
                      autoComplete="new-password"
                    />
                    <button type="button" onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-300 hover:text-neo-black transition-colors">
                      {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="bg-neo-coral/10 border-2 border-neo-coral px-4 py-2.5 flex items-start gap-2">
                    <div className="w-1.5 h-1.5 bg-neo-coral rounded-full mt-1.5 flex-shrink-0" />
                    <p className="font-mono text-xs text-neo-coral font-semibold">{error}</p>
                  </div>
                )}

                <NeoButton
                  type="submit"
                  size="lg"
                  loading={loading}
                  className={`w-full mt-1 ${!isEmployee ? '!bg-neo-black !border-neo-black !text-neo-yellow' : ''}`}
                  variant="primary"
                  icon={<ArrowRight size={18} />}
                >
                  Sign In
                </NeoButton>

                {!isEmployee && (
                  <p className="text-center font-mono text-xs text-gray-400">
                    New HR staff?{' '}
                    <Link to="/register" className="text-neo-black font-bold underline underline-offset-2 hover:text-neo-yellow transition-colors">
                      Request Account
                    </Link>
                  </p>
                )}
              </form>
            </div>

            {/* Mobile feature chips */}
            <div className="flex flex-wrap gap-2 mt-4 justify-center lg:hidden">
              <FeatureChip icon={<Sparkles size={12} />} label="AI Assistant" />
              <FeatureChip icon={<BarChart3 size={12} />} label="Analytics" />
              <FeatureChip icon={<Clock size={12} />} label="Attendance" />
            </div>

            {/* Trust indicator */}
            <div className="flex items-center justify-center gap-3 mt-5">
              <div className="flex -space-x-2">
                {['/group.jpg', '/talk.jpg', '/meatting.jpg'].map((src, i) => (
                  <div key={i} className="w-7 h-7 rounded-full border-2 border-white overflow-hidden shadow-sm">
                    <img src={src} alt="" className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
              <p className="font-mono text-[10px] text-neo-black/40">
                Trusted by <span className="font-bold text-neo-black/60">500+</span> employees
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="text-center py-4 border-t-2 border-neo-black/10 relative z-20">
        <p className="font-mono text-[11px] text-gray-400">
          University of Vocational Technology, Sri Lanka &mdash; FYP 2026
        </p>
      </footer>
    </div>
  );
};
