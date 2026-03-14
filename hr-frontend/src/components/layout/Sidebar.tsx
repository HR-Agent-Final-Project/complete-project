import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, CalendarCheck, FileText,
  TrendingUp, Briefcase, BarChart2, MessageSquare,
  Settings, LogOut, ChevronLeft, ChevronRight, Bot, X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  roles: UserRole[];
}

const navItems: NavItem[] = [
  { to: '/dashboard', icon: <LayoutDashboard size={18} />, label: 'Dashboard',  roles: ['employee', 'hr_admin', 'management'] },
  { to: '/employees', icon: <Users size={18} />,           label: 'Employees',  roles: ['hr_admin', 'management'] },
  { to: '/attendance', icon: <CalendarCheck size={18} />,  label: 'Attendance', roles: ['employee', 'hr_admin', 'management'] },
  { to: '/leave',      icon: <FileText size={18} />,       label: 'Leave',      roles: ['employee', 'hr_admin', 'management'] },
  { to: '/performance',icon: <TrendingUp size={18} />,     label: 'Performance',roles: ['employee', 'hr_admin', 'management'] },
  { to: '/recruitment',icon: <Briefcase size={18} />,      label: 'Recruitment',roles: ['hr_admin', 'management'] },
  { to: '/reports',    icon: <BarChart2 size={18} />,      label: 'Reports',    roles: ['hr_admin', 'management'] },
  { to: '/ai-chat',    icon: <MessageSquare size={18} />,  label: 'AI Chat',    roles: ['employee', 'hr_admin', 'management'] },
  { to: '/settings',   icon: <Settings size={18} />,       label: 'Settings',   roles: ['employee', 'hr_admin', 'management'] },
];

interface Props {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export const Sidebar = ({ mobileOpen, onMobileClose }: Props) => {
  const { role, logout, user } = useAuth();
  const navigate = useNavigate();
  // desktopCollapsed only applies on lg+ screens
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);

  const visible = navItems.filter(item => !role || item.roles.includes(role));

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <>
      {/* Mobile overlay backdrop */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-200 ${
          mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onMobileClose}
      />

      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-50
          flex flex-col bg-neo-black border-r-4 border-neo-black
          transition-all duration-200 flex-shrink-0
          w-64
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          md:w-16
          ${desktopCollapsed ? 'lg:w-16' : 'lg:w-56'}
        `}
      >
        {/* Logo + mobile close */}
        <div className="border-b-2 border-white/20 p-4 flex items-center justify-between gap-2 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 bg-neo-yellow border-2 border-white flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="text-neo-black" />
            </div>
            {/* Label: always on mobile (drawer), hidden on md, shown on lg unless desktop-collapsed */}
            <div className={`min-w-0 block md:hidden ${desktopCollapsed ? '' : 'lg:block'}`}>
              <span className="font-display font-bold text-white text-lg leading-none">HRAgent</span>
              <div className="h-0.5 bg-neo-yellow mt-0.5" />
            </div>
          </div>
          {/* Close button: mobile only */}
          <button
            onClick={onMobileClose}
            className="md:hidden p-1 border-2 border-white/30 text-white hover:bg-white/10 flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {visible.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `
                flex items-center gap-3 px-4 py-2.5 mx-2 mb-0.5 transition-all duration-100
                font-display font-semibold text-sm
                ${isActive
                  ? 'bg-neo-yellow text-neo-black border-2 border-neo-black shadow-neo-sm'
                  : 'text-white/70 hover:text-white hover:bg-white/10 border-2 border-transparent'
                }
                md:justify-center md:px-0
                ${desktopCollapsed ? 'lg:justify-center lg:px-0' : 'lg:justify-start lg:px-4'}
              `}
              title={item.label}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {/* Label visibility */}
              <span className={`block md:hidden ${desktopCollapsed ? '' : 'lg:block'}`}>
                {item.label}
              </span>
            </NavLink>
          ))}
        </nav>

        {/* User + Logout — hidden when icon-only */}
        <div className={`border-t-2 border-white/20 p-4 block md:hidden ${desktopCollapsed ? '' : 'lg:block'}`}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-neo-teal border-2 border-white flex items-center justify-center flex-shrink-0">
              <span className="font-display font-bold text-neo-black text-xs">
                {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || 'U'}
              </span>
            </div>
            <div className="min-w-0">
              <p className="font-display font-bold text-white text-xs truncate">{user?.name || 'User'}</p>
              <p className="font-mono text-white/50 text-xs truncate capitalize">{user?.role?.replace('_', ' ')}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-1.5 bg-neo-coral border-2 border-white text-neo-black font-display font-bold text-xs hover:translate-x-[1px] hover:translate-y-[1px] transition-all shadow-[2px_2px_0_0_white] hover:shadow-none"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>

        {/* Logout icon-only on md (tablet icon-only bar) */}
        <div className="hidden md:flex lg:hidden items-center justify-center p-3 border-t-2 border-white/20">
          <button
            onClick={handleLogout}
            className="p-2 bg-neo-coral border-2 border-white text-neo-black hover:opacity-80"
            title="Logout"
          >
            <LogOut size={14} />
          </button>
        </div>

        {/* Desktop collapse toggle — lg only */}
        <button
          onClick={() => setDesktopCollapsed(c => !c)}
          className="hidden lg:flex self-end m-2 p-1.5 bg-white/10 border-2 border-white/30 text-white hover:bg-white/20 transition-all"
          title={desktopCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {desktopCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>
    </>
  );
};
