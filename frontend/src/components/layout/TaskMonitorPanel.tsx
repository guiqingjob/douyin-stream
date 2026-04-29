import { useState, useEffect, useMemo } from 'react';
import { Activity, AlertTriangle, Clock3, Loader2, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';
import {
  getTaskDisplayState,
  sortTasks,
  filterTasksByCategory,
  type TaskFilterCategory,
} from '@/lib/task-utils';
import { useTaskActions } from '@/hooks/useTaskActions';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { TaskItem } from './TaskMonitorPanel/TaskItem';

const FILTER_TABS: { key: TaskFilterCategory; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'download', label: '下载' },
  { key: 'transcribe', label: '转写' },
  { key: 'sync', label: '同步' },
];

export function TaskMonitorPanel() {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<TaskFilterCategory>('all');
  const [, setTick] = useState(0);
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const rawTasks = useStore((state) => state.tasks);
  const fetchInitialTasks = useStore((state) => state.fetchInitialTasks);
  const allTasks = useMemo(() => sortTasks(rawTasks), [rawTasks]);
  const { handleClearHistory, handleRetry } = useTaskActions();

  // 打开对话框时，如果还没有加载任务，主动拉取一次
  useEffect(() => {
    if (open && rawTasks.length === 0) {
      fetchInitialTasks();
    }
  }, [open, rawTasks.length, fetchInitialTasks]);

  // Tick every 10s to refresh durations
  useEffect(() => {
    if (!open) return;
    const interval = setInterval(() => setTick((t) => t + 1), 10_000);
    return () => clearInterval(interval);
  }, [open]);

  const filteredTasks = useMemo(() => filterTasksByCategory(allTasks, filter), [allTasks, filter]);

  const activeTasks = useMemo(() => allTasks.filter((task) => {
    const state = getTaskDisplayState(task);
    return state === 'running' || state === 'paused';
  }), [allTasks]);
  const failedTasks = useMemo(() => allTasks.filter((task) => {
    const state = getTaskDisplayState(task);
    return state === 'failed' || state === 'stale';
  }), [allTasks]);

  const triggerCaption = useMemo(() =>
    activeTasks.length > 0
      ? `${activeTasks.length} 个任务进行中`
      : failedTasks.length > 0
        ? `最近 ${failedTasks.length} 个任务异常`
        : '后台空闲',
    [activeTasks.length, failedTasks.length],
  );

  const hasNonRunning = useMemo(() => allTasks.some((t) => {
    const state = getTaskDisplayState(t);
    return state !== 'running' && state !== 'paused';
  }), [allTasks]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="flex w-full items-center gap-3 rounded-[var(--radius-card)] p-3 text-left transition-all duration-200 hover:bg-secondary/60 group apple-list-item">
        <div className="relative flex size-9 shrink-0 items-center justify-center rounded-xl bg-secondary/70">
          <Activity className="size-4 text-foreground/60 group-hover:text-foreground/80" />
          {activeTasks.length > 0 && (
            <span className="absolute right-1.5 top-1.5 size-2 rounded-md bg-primary animate-pulse" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-foreground/85">任务中心</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{triggerCaption}</div>
        </div>
        {activeTasks.length > 0 ? (
          <Loader2 className="size-4 text-primary animate-spin" />
        ) : failedTasks.length > 0 ? (
          <AlertTriangle className="size-4 text-warning" />
        ) : (
          <Clock3 className="size-4 text-muted-foreground/70" />
        )}
      </DialogTrigger>

      <DialogContent className="flex max-h-[85vh] flex-col gap-0 overflow-hidden rounded-[var(--radius-card)] border border-border/60 bg-card p-0 apple-shadow-md sm:max-w-[680px]">
        <DialogHeader className="shrink-0 border-b border-border/60 px-6 py-4 pr-12">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2.5 text-[15px] font-semibold">
              <div className="flex size-8 items-center justify-center rounded-md bg-primary/10">
                <Activity className="size-4 text-primary" />
              </div>
              任务中心
            </DialogTitle>
            {hasNonRunning && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearHistory}
                className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <Trash2 className="size-3.5" />
                清除历史
              </Button>
            )}
          </div>
        </DialogHeader>

        <div className="shrink-0 grid grid-cols-4 gap-3 border-b border-border/60 px-6 py-4">
          {[
            { label: '进行中', value: activeTasks.length, tone: 'text-primary' },
            { label: '成功', value: allTasks.filter((t) => getTaskDisplayState(t) === 'success').length, tone: 'text-success' },
            { label: '失败', value: failedTasks.length, tone: 'text-destructive' },
            { label: '总计', value: allTasks.length, tone: 'text-foreground' },
          ].map((item) => (
            <div key={item.label} className="rounded-[var(--radius-card)] border border-border/60 bg-card p-3">
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className={cn('mt-1 text-lg font-semibold', item.tone)}>{item.value}</div>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div className="shrink-0 border-b border-border/60 px-6 py-3">
          <div className="inline-flex rounded-[var(--radius-card)] border border-border/60 bg-muted p-1">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={cn(
                  'h-8 rounded-md px-3 text-xs font-medium transition-all duration-200',
                  filter === tab.key
                    ? 'bg-background text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06)]'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          {filteredTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="flex size-12 items-center justify-center rounded-[var(--radius-card)] bg-muted">
                <Clock3 className="size-5 text-muted-foreground/40" />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {filter === 'all' ? '还没有后台任务' : '没有相关任务'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredTasks.map((task) => (
                <TaskItem
                  key={task.task_id}
                  task={task}
                  onRetry={handleRetry}
                  isExpanded={expandedTasks.has(task.task_id)}
                  onToggleExpand={(taskId) => {
                    setExpandedTasks((prev) => {
                      const next = new Set(prev);
                      if (next.has(taskId)) next.delete(taskId);
                      else next.add(taskId);
                      return next;
                    });
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
