import { useMemo, useState } from 'react';
import { CheckCircle2, ChevronDown, FileText, Loader2, MinusCircle, RotateCw, Trash2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';
import {
  getTaskDisplayState,
  getTaskDuration,
  getTaskError,
  getTaskMessage,
  getTaskStatusLabel,
  taskTypeLabel,
} from '@/lib/task-utils';
import { rerunTask, setAutoRetry, deleteTask, recoverAwemeAndTranscribe } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import type { Task } from '@/lib/api';

type TaskSubtask = {
  title: string;
  status: string;
  error?: string;
  aweme_id?: string;
  creator_uid?: string;
};

const EMPTY_SUBTASKS: TaskSubtask[] = [];

function parsePayload(payload?: string): Record<string, unknown> | null {
  if (!payload) return null;
  try {
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

interface TaskItemProps {
  task: Task;
  onRetry: (task: Task) => void;
  isExpanded: boolean;
  onToggleExpand: (taskId: string) => void;
}

export function TaskItem({ task, onRetry, isExpanded, onToggleExpand }: TaskItemProps) {
  const state = getTaskDisplayState(task);
  const message = getTaskMessage(task);
  const error = getTaskError(task);
  const duration = getTaskDuration(task);
  const isRunning = state === 'running';
  const isPaused = state === 'paused';
  const isFailed = state === 'failed' || state === 'stale';
  const hasParsedPayload = !!parsePayload(task.payload);

  return (
    <div className="rounded-[var(--radius-card)] border border-border/60 bg-card p-4 apple-shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-foreground">{taskTypeLabel(task.task_type)}</span>
            <Badge
              tone={
                state === 'running'
                  ? 'secondary'
                  : state === 'paused'
                    ? 'warning'
                    : state === 'success'
                      ? 'success'
                      : state === 'failed' || state === 'stale'
                        ? 'destructive'
                        : 'default'
              }
            >
              {getTaskStatusLabel(task)}
            </Badge>
            <TaskStageBadge task={task} isRunning={isRunning} />
            {duration && (
              <span className="text-[11px] text-muted-foreground tabular-nums">{duration}</span>
            )}
          </div>
          <div className="mt-1 text-xs font-mono text-muted-foreground/50">{task.task_id}</div>
        </div>
        <TaskActions
          task={task}
          state={state}
          isRunning={isRunning}
          isFailed={isFailed}
          hasParsedPayload={hasParsedPayload}
          onRetry={onRetry}
        />
      </div>

      {(isRunning || isPaused) && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{message}</span>
            <span className="font-medium text-primary tabular-nums">{Math.round((task.progress || 0) * 100)}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="relative h-full rounded-full bg-primary transition-all duration-500 ease-out apple-progress-bar"
              style={{ width: `${Math.max(2, (task.progress || 0) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {!isRunning && (
        <div className="mt-3 text-sm leading-6 text-muted-foreground">{message}</div>
      )}

      {error && (
        <div className="mt-3 rounded-[var(--radius-card)] border border-destructive/20 bg-destructive/10 p-3 text-xs leading-6 text-destructive whitespace-pre-wrap">
          {error}
        </div>
      )}

      <TaskStats task={task} />
      <TaskSubtasks task={task} isExpanded={isExpanded} onToggleExpand={onToggleExpand} />
    </div>
  );
}

function TaskStageBadge({ task, isRunning }: { task: Task; isRunning: boolean }) {
  const parsed = parsePayload(task.payload);
  const stage = parsed?.stage as string | undefined;
  if (!stage || !isRunning) return null;
  const stageLabel: Record<string, string> = {
    initializing: '初始化',
    downloading: '下载中',
    transcribing: '转写中',
    finalizing: '收尾中',
  };
  return (
    <span className="text-[11px] rounded-md bg-primary/10 px-2 py-0.5 text-primary">
      {stageLabel[stage] || stage}
    </span>
  );
}

function TaskActions({
  task,
  isRunning,
  isFailed,
  hasParsedPayload,
  onRetry,
}: {
  task: Task;
  state: string;
  isRunning: boolean;
  isFailed: boolean;
  hasParsedPayload: boolean;
  onRetry: (task: Task) => void;
}) {
  return (
    <div className="mt-0.5 flex items-center gap-2">
      {isFailed && hasParsedPayload && (
        <>
          <button
            onClick={() => onRetry(task)}
            className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
            title="重试（新建任务）"
          >
            <RotateCw className="size-3.5" />
            重试
          </button>
          <button
            onClick={async () => {
              try {
                await rerunTask(task.task_id);
                toast.success('任务已重新运行');
              } catch {
                // interceptor already toasts
              }
            }}
            className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
            title="用同一任务ID重新运行（断点续传）"
          >
            <RotateCw className="size-3.5" />
            继续
          </button>
          <button
            onClick={async () => {
              try {
                await setAutoRetry(task.task_id, true);
                toast.success('已启用自动重试');
              } catch {
                // interceptor already toasts
              }
            }}
            className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
            title="失败后自动重试"
          >
            <RotateCw className="size-3.5" />
            自动
          </button>
        </>
      )}
      {isRunning && <Loader2 className="size-4 animate-spin text-primary" />}
      {getTaskDisplayState(task) === 'success' && <CheckCircle2 className="size-4 text-success" />}
      {isFailed && <XCircle className="size-4 text-destructive" />}
      <button
        onClick={async () => {
          try {
            await deleteTask(task.task_id);
            const { fetchInitialTasks } = useStore.getState();
            await fetchInitialTasks();
            toast.success('任务已删除');
          } catch {
            // interceptor already toasts
          }
        }}
        className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors duration-200 hover:bg-destructive/10 hover:text-destructive"
        title="删除任务"
      >
        <Trash2 className="size-3.5" />
      </button>
    </div>
  );
}

function TaskStats({ task }: { task: Task }) {
  const parsed = parsePayload(task.payload);
  const summary = parsed?.result_summary as { success?: number; failed?: number; total?: number } | undefined;
  if (!summary || summary.total == null) return null;
  return (
    <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
      <span className="flex items-center gap-1">
        <CheckCircle2 className="size-3 text-success" />
        {summary.success || 0}
      </span>
      {summary.failed ? (
        <span className="flex items-center gap-1">
          <XCircle className="size-3 text-destructive" />
          {summary.failed}
        </span>
      ) : null}
      <span>共 {summary.total} 个</span>
    </div>
  );
}

function TaskSubtasks({
  task,
  isExpanded,
  onToggleExpand,
}: {
  task: Task;
  isExpanded: boolean;
  onToggleExpand: (taskId: string) => void;
}) {
  const parsed = useMemo(() => parsePayload(task.payload), [task.payload]);
  const subtasks = useMemo(() => {
    const raw = parsed?.subtasks;
    if (!Array.isArray(raw)) return EMPTY_SUBTASKS;
    return raw as TaskSubtask[];
  }, [parsed]);
  const [recoveringAwemeId, setRecoveringAwemeId] = useState<string | null>(null);
  const creatorUidFromPayload =
    typeof parsed?.creator_uid === 'string'
      ? parsed.creator_uid
      : typeof parsed?.uid === 'string'
        ? parsed.uid
        : undefined;
  const missingItems = useMemo(() => {
    const raw = parsed?.missing_items;
    if (!Array.isArray(raw)) return [];
    return raw.filter((item) => item && typeof item === 'object' && !Array.isArray(item)) as Array<{
      aweme_id?: unknown;
      title?: unknown;
    }>;
  }, [parsed]);

  const enhancedSubtasks = useMemo(() => {
    if (!subtasks.length) return [];
    if (!missingItems.length && !creatorUidFromPayload) return subtasks;
    const byTitle = new Map<string, string[]>();
    for (const item of missingItems) {
      const title = typeof item.title === 'string' ? item.title : '';
      const awemeId = typeof item.aweme_id === 'string' ? item.aweme_id : '';
      if (!title || !awemeId) continue;
      const list = byTitle.get(title) ?? [];
      list.push(awemeId);
      byTitle.set(title, list);
    }

    const usedByTitle = new Map<string, number>();

    return subtasks.map((sub) => {
      if (sub.status !== 'manual_required') {
        return creatorUidFromPayload && !sub.creator_uid ? { ...sub, creator_uid: creatorUidFromPayload } : sub;
      }

      let awemeId = sub.aweme_id;
      if (!awemeId && sub.title) {
        const list = byTitle.get(sub.title);
        if (list && list.length) {
          const used = usedByTitle.get(sub.title) ?? 0;
          awemeId = list[Math.min(used, list.length - 1)];
          usedByTitle.set(sub.title, used + 1);
        }
      }

      return {
        ...sub,
        aweme_id: awemeId,
        creator_uid: sub.creator_uid ?? creatorUidFromPayload,
      };
    });
  }, [creatorUidFromPayload, missingItems, subtasks]);

  if (subtasks.length === 0) return null;
  const completed = subtasks.filter((s) => s.status === 'completed').length;
  const skipped = subtasks.filter((s) => s.status === 'skipped').length;
  const failed = subtasks.filter((s) => s.status === 'failed').length;
  return (
    <div className="mt-3">
      <button
        onClick={() => onToggleExpand(task.task_id)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronDown className={cn('size-3.5 transition-transform', isExpanded ? 'rotate-180' : '')} />
        <FileText className="size-3" />
        详情 {completed}/{subtasks.length}
        {skipped > 0 && <span className="text-[10px] text-muted-foreground/60">(跳过 {skipped})</span>}
        {failed > 0 && <span className="text-[10px] text-destructive/70">(失败 {failed})</span>}
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-1 max-h-48 overflow-y-auto rounded-[var(--radius-card)] border border-border/40 bg-muted/30 p-2">
          {enhancedSubtasks.map((sub, idx) => {
            const canRecover = sub.status === 'manual_required' && !!sub.creator_uid && !!sub.aweme_id;
            const isRecovering = !!sub.aweme_id && recoveringAwemeId === sub.aweme_id;
            return (
            <div
              key={idx}
              className="flex items-start gap-2 px-2 py-1.5 rounded-md text-xs"
              title={sub.error || ''}
            >
              {sub.status === 'completed' ? (
                <CheckCircle2 className="size-3.5 text-success shrink-0 mt-0.5" />
              ) : sub.status === 'skipped' ? (
                <MinusCircle className="size-3.5 text-muted-foreground shrink-0 mt-0.5" />
              ) : sub.status === 'pending' ? (
                <Loader2 className="size-3.5 text-primary shrink-0 mt-0.5 animate-spin" />
              ) : (
                <XCircle className="size-3.5 text-destructive shrink-0 mt-0.5" />
              )}
              <div className="min-w-0 flex-1">
                <span className={cn(
                  'block truncate',
                  sub.status === 'completed' ? 'text-foreground/80' :
                  sub.status === 'skipped' ? 'text-muted-foreground' :
                  sub.status === 'pending' ? 'text-primary' :
                  'text-destructive'
                )}>
                  {sub.title || '未命名'}
                </span>
                {sub.error && (
                  <span className="block truncate text-[10px] text-destructive/80 mt-0.5">{sub.error}</span>
                )}
              </div>
              {sub.status === 'manual_required' && (
                <button
                  disabled={!canRecover || isRecovering}
                  onClick={async () => {
                    const creatorUid = sub.creator_uid || creatorUidFromPayload;
                    const awemeId = sub.aweme_id;
                    if (!creatorUid || !awemeId) {
                      toast.error('缺少补齐所需参数（creator_uid / aweme_id）');
                      return;
                    }
                    try {
                      setRecoveringAwemeId(awemeId);
                      await recoverAwemeAndTranscribe(creatorUid, awemeId, sub.title || '');
                      const { fetchInitialTasks } = useStore.getState();
                      await fetchInitialTasks();
                      toast.success('已创建补齐任务');
                    } catch {
                      // interceptor already toasts
                    } finally {
                      setRecoveringAwemeId(null);
                    }
                  }}
                  className={cn(
                    'flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-medium text-primary transition-colors duration-200',
                    canRecover && !isRecovering ? 'hover:bg-primary/10' : 'cursor-not-allowed opacity-50'
                  )}
                  title={canRecover ? '创建补齐并转写任务' : '缺少 aweme_id 或 creator_uid，无法创建补齐任务'}
                >
                  {isRecovering ? <Loader2 className="size-3 animate-spin" /> : <RotateCw className="size-3" />}
                  补齐并转写
                </button>
              )}
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
