import { ReactNode, useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/employees': 'Employees',
  '/attendance': 'Attendance',
  '/leave': 'Leave Management',
  '/performance': 'Performance',
  '/recruitment': 'Recruitment',
  '/reports': 'Reports & Analytics',
  '/ai-chat': 'AI Chat Agent',
  '/settings': 'Settings',
};

export const Layout = ({ children }: { children: ReactNode }) => {
  const location = useLocation();
  const path = '/' + location.pathname.split('/')[1];
  const title = pageTitles[path] || 'HRAgent';

  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Close mobile drawer on navigation
  useEffect(() => { setSidebarOpen(false); }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-neo-bg">
      <Sidebar mobileOpen={sidebarOpen} onMobileClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={title} onMenuClick={() => setSidebarOpen(o => !o)} />
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
