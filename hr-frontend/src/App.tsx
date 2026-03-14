import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { Layout } from './components/layout/Layout';
import { ChatWidget } from './components/chat/ChatWidget';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Employees } from './pages/Employees';
import { EmployeeProfile } from './pages/EmployeeProfile';
import { Attendance } from './pages/Attendance';
import { Leave } from './pages/Leave';
import { Performance } from './pages/Performance';
import { Recruitment } from './pages/Recruitment';
import { Reports } from './pages/Reports';
import { AIChat } from './pages/AIChat';
import { Settings } from './pages/Settings';

// ─── Auth Guard ───────────────────────────────────────────────────────────────
const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

// ─── App Shell ────────────────────────────────────────────────────────────────
const AppShell = () => (
  <Layout>
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/employees" element={<Employees />} />
      <Route path="/employees/:id" element={<EmployeeProfile />} />
      <Route path="/attendance" element={<Attendance />} />
      <Route path="/leave" element={<Leave />} />
      <Route path="/performance" element={<Performance />} />
      <Route path="/recruitment" element={<Recruitment />} />
      <Route path="/reports" element={<Reports />} />
      <Route path="/ai-chat" element={<AIChat />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
    <ChatWidget />
  </Layout>
);

// ─── Router Root ──────────────────────────────────────────────────────────────
const AppRoutes = () => {
  const { isAuthenticated } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />} />
      <Route path="/*" element={
        <PrivateRoute>
          <AppShell />
        </PrivateRoute>
      } />
    </Routes>
  );
};

// ─── Root ──────────────────────────────────────────────────────────────────────
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <AppRoutes />
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
