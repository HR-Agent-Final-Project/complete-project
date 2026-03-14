import React, { useState, useRef, useEffect } from 'react';
import { Bell, ChevronDown, LogOut, Settings, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

interface Props {
  title: string;
  onMenuClick: () => void;
}

export const TopBar = ({ title, onMenuClick }: Props) => {
  const { user, logout } = useAuth();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const navigate = useNavigate();
  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen]   = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef  = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (userRef.current  && !userRef.current.contains(e.target as Node))  setUserOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || 'U';

  return (
    <header className="h-14 border-b border-neo-black/10 bg-white flex items-center justify-between px-3 md:px-6 flex-shrink-0 gap-2">
      {/* Left: hamburger (mobile/tablet) + title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="md:hidden p-2 border-2 border-neo-black bg-white hover:bg-neo-yellow transition-colors flex-shrink-0"
          aria-label="Open navigation"
        >
          <Menu size={18} />
        </button>
        <h1 className="font-display font-bold text-lg md:text-xl text-neo-black truncate">{title}</h1>
      </div>

      {/* Right: notifications + user menu */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setNotifOpen(o => !o)}
            className="relative p-2 border-2 border-neo-black bg-white hover:bg-neo-yellow transition-colors shadow-neo-sm"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-neo-coral border-2 border-neo-black text-neo-black text-[9px] font-bold flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-12 w-[min(320px,calc(100vw-16px))] bg-white border-2 border-neo-black shadow-neo-lg z-50">
              <div className="flex items-center justify-between p-3 border-b-2 border-neo-black bg-neo-yellow">
                <span className="font-display font-bold text-sm">Notifications</span>
                <button onClick={markAllRead} className="font-mono text-xs underline hover:no-underline">Mark all read</button>
              </div>
              <div className="max-h-72 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="p-4 text-center font-mono text-sm text-gray-500">No notifications</p>
                ) : notifications.slice(0, 6).map(n => (
                  <div
                    key={n.id}
                    onClick={() => markRead(n.id)}
                    className={`p-3 border-b border-black/10 cursor-pointer hover:bg-neo-yellow/20 ${!n.read ? 'bg-neo-yellow/10' : ''}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-display font-semibold text-xs text-neo-black">{n.title}</p>
                        <p className="font-mono text-xs text-gray-600 mt-0.5">{n.message}</p>
                      </div>
                      {!n.read && <div className="w-2 h-2 bg-neo-coral border border-neo-black mt-1 flex-shrink-0" />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div ref={userRef} className="relative">
          <button
            onClick={() => setUserOpen(o => !o)}
            className="flex items-center gap-2 px-2 md:px-3 py-1.5 border-2 border-neo-black bg-white hover:bg-neo-yellow transition-colors shadow-neo-sm"
          >
            <div className="w-7 h-7 bg-neo-teal border-2 border-neo-black flex items-center justify-center">
              <span className="font-display font-bold text-neo-black text-xs">{initials}</span>
            </div>
            <span className="font-display font-semibold text-sm hidden sm:block">{user?.name?.split(' ')[0]}</span>
            <ChevronDown size={14} />
          </button>

          {userOpen && (
            <div className="absolute right-0 top-12 w-48 bg-white border-2 border-neo-black shadow-neo z-50">
              <div className="p-3 border-b-2 border-neo-black">
                <p className="font-display font-bold text-sm">{user?.name}</p>
                <p className="font-mono text-xs text-gray-500 capitalize">{user?.role?.replace('_', ' ')}</p>
              </div>
              <button
                onClick={() => { setUserOpen(false); navigate('/settings'); }}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-neo-yellow/30 font-display text-sm font-semibold"
              >
                <Settings size={14} /> Settings
              </button>
              <button
                onClick={() => { logout(); navigate('/login'); }}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-neo-coral/30 font-display text-sm font-semibold text-neo-coral border-t-2 border-neo-black"
              >
                <LogOut size={14} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
