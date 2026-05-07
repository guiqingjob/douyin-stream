import { useLocation, useNavigate } from 'react-router-dom';
import { useCallback, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from './Sidebar';
import { cn } from '@/lib/utils';
import { useShortcuts } from '@/hooks/useShortcuts';

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const goTo = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  useShortcuts({
    'g d': () => goTo('/discover'),
    'g c': () => goTo('/creators'),
    'g s': () => goTo('/settings'),
  }, { enabled: true });

  const pageTitle = (() => {
    if (location.pathname.startsWith('/discover')) return '发现';
    if (location.pathname.startsWith('/creators')) return '创作者';
    if (location.pathname.startsWith('/settings')) return '设置';
    return '';
  })();

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <header className="h-14 flex-shrink-0 px-4 sm:px-6 flex items-center gap-3 border-b border-border/40 apple-glass-bar">
          <button
            className="lg:hidden flex items-center justify-center size-9 rounded-[var(--radius-button)] hover:bg-secondary transition-colors"
            onClick={() => setSidebarOpen(true)}
            aria-label="打开侧边栏"
          >
            <Menu className="size-5 text-muted-foreground" />
          </button>
          <h2 className={cn(
            "text-title-3 font-semibold text-foreground tracking-tight",
            "apple-fade-in"
          )}>
            {pageTitle}
          </h2>
        </header>
        <div className="flex-1 min-h-0 overflow-auto" data-scroll-container="main">
          <div
            key={`${location.pathname}${location.search}`}
            className={cn(
              "h-full",
              "apple-slide-in-right"
            )}
          >
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
