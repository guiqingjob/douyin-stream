import { CheckCircle2, Loader2, TriangleAlert, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function TaskStatusBanner({
  title,
  message,
  tone,
  error,
}: {
  title: string;
  message: string;
  tone: 'running' | 'success' | 'warning' | 'error';
  error?: string;
}) {
  const toneMap = {
    running: {
      box: 'border-primary/20 bg-primary/10 text-foreground',
      icon: <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />,
    },
    success: {
      box: 'border-success/20 bg-success/10 text-foreground',
      icon: <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />,
    },
    warning: {
      box: 'border-warning/20 bg-warning/10 text-foreground',
      icon: <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />,
    },
    error: {
      box: 'border-destructive/20 bg-destructive/10 text-foreground',
      icon: <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" />,
    },
  }[tone];

  return (
    <div className={cn('rounded-[var(--radius-card)] border p-4', toneMap.box)}>
      <div className="flex items-start gap-3">
        {toneMap.icon}
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-foreground">{title}</div>
          <div className="mt-1 text-sm leading-6 text-foreground/75">{message}</div>
          {error && (
            <div className="mt-3 rounded-[var(--radius-card)] border border-destructive/20 bg-destructive/10 p-3 text-xs leading-6 text-destructive">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
