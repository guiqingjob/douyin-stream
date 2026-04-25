import { NavLink } from 'react-router-dom';
import { Compass, Users, Settings, Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';
import { TaskMonitorPanel } from '@/components/layout/TaskMonitorPanel';

interface SidebarProps {
  listContent?: React.ReactNode;
}

function SidebarItem({
  icon: Icon,
  label,
  href,
  badge,
}: {
  icon: typeof Compass;
  label: string;
  href: string;
  badge?: number;
}) {
  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 h-8 px-3 rounded-md cursor-pointer select-none transition-colors duration-200',
          isActive
            ? 'bg-primary/10 text-primary font-medium'
            : 'hover:bg-foreground/[0.03] text-foreground font-medium'
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            className={cn(
              'size-5 shrink-0',
              isActive ? 'text-primary' : 'text-muted-foreground'
            )}
          />
          <span className="text-[14px]">
            {label}
          </span>
          {badge != null && badge > 0 && (
            <span className="ml-auto size-4 min-w-4 rounded-md bg-destructive text-destructive-foreground text-[10px] font-bold flex items-center justify-center">
              {badge > 99 ? '99+' : badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const cycle = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };
  const icon = theme === 'light' ? <Sun className="size-4" /> : theme === 'dark' ? <Moon className="size-4" /> : <Monitor className="size-4" />;
  const label = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '系统';
  return (
    <button
      onClick={cycle}
      className="flex items-center gap-3 h-8 px-3 rounded-md cursor-pointer select-none transition-colors duration-200 hover:bg-foreground/[0.03] text-foreground font-medium w-full"
      aria-label={`当前主题: ${label}，点击切换`}
    >
      {icon}
      <span className="text-[14px]">主题 · {label}</span>
    </button>
  );
}

export default function Sidebar({ listContent }: SidebarProps) {
  return (
    <aside className="w-[260px] h-full overflow-y-auto flex-shrink-0 flex flex-col apple-glass-sidebar border-r border-sidebar-border">
      {/* Header */}
      <div className="shrink-0 h-12 px-4 flex items-center">
        <h1 className="text-[17px] font-semibold text-sidebar-foreground tracking-tight">Media Tools</h1>
      </div>

      {/* Primary Nav */}
      <nav className="px-3 py-1 space-y-1">
        <SidebarItem icon={Compass} label="发现" href="/discover" />
        <SidebarItem icon={Users} label="创作者" href="/creators" />
        <SidebarItem icon={Settings} label="设置" href="/settings" />
      </nav>

      {/* Divider */}
      <div className="mx-3 my-2 h-px bg-sidebar-border" />

      {/* Theme Toggle */}
      <div className="px-3 py-1">
        <ThemeToggle />
      </div>

      {/* Divider */}
      <div className="mx-3 my-2 h-px bg-sidebar-border" />

      {/* Contextual List */}
      <div className="px-3 py-1 space-y-1">
        <TaskMonitorPanel />
        {listContent && (
          <div className="px-3 mb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
            关注创作者
          </div>
        )}
        {listContent}
      </div>
    </aside>
  );
}
