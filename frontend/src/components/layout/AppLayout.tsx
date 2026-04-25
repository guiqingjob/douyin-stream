import { useLocation } from 'react-router-dom';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppLayout() {
  const location = useLocation();

  const pageTitle = (() => {
    if (location.pathname.startsWith('/discover')) return '发现';
    if (location.pathname.startsWith('/creators')) return '创作者';
    if (location.pathname.startsWith('/settings')) return '设置';
    return '';
  })();

  return (
    <div className="flex h-full w-full overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <header className="h-12 flex-shrink-0 px-6 flex items-center border-b border-border/40 apple-glass-sidebar">
          <div className="text-[15px] font-semibold text-foreground tracking-tight">{pageTitle}</div>
        </header>
        <div className="flex-1 min-h-0 overflow-auto" data-scroll-container="main">
          <div
            key={`${location.pathname}${location.search}`}
            className="h-full animate-in fade-in slide-in-from-right-2 duration-150 ease-out"
          >
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
