import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Notification, NotificationType } from '../types';
import { mockNotifications } from '../mock/data';

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (type: NotificationType, title: string, message: string) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  removeNotification: (id: string) => void;
  toasts: Toast[];
  dismissToast: (id: string) => void;
}

interface Toast {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addNotification = useCallback((type: NotificationType, title: string, message: string) => {
    const id = `n-${Date.now()}`;
    const notif: Notification = { id, type, title, message, read: false, created_at: new Date().toISOString() };
    setNotifications(prev => [notif, ...prev]);

    const toast: Toast = { id, type, title, message };
    setToasts(prev => [...prev, toast]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const markRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider value={{
      notifications, unreadCount, addNotification,
      markRead, markAllRead, removeNotification,
      toasts, dismissToast,
    }}>
      {children}
      <ToastContainer toasts={toasts} dismiss={dismissToast} />
    </NotificationContext.Provider>
  );
};

const typeStyles: Record<NotificationType, string> = {
  success: 'bg-neo-teal',
  error: 'bg-neo-coral',
  warning: 'bg-neo-yellow',
  info: 'bg-neo-blue text-white',
};

const ToastContainer = ({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: string) => void }) => (
  <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
    {toasts.map(t => (
      <div
        key={t.id}
        className={`toast-enter pointer-events-auto min-w-[280px] max-w-xs border-2 border-neo-black shadow-neo p-3 ${typeStyles[t.type]}`}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-display font-bold text-sm text-neo-black">{t.title}</p>
            <p className="font-mono text-xs text-neo-black mt-0.5">{t.message}</p>
          </div>
          <button onClick={() => dismiss(t.id)} className="text-neo-black font-bold text-lg leading-none hover:opacity-60">×</button>
        </div>
      </div>
    ))}
  </div>
);

export const useNotifications = () => {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationProvider');
  return ctx;
};
