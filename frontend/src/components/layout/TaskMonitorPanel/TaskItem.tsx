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
import { cancelTask, rerunTask, setAutoRetry, deleteTask, recoverAwemeAndTranscribe } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import type { Task } from '@/lib/api';
import type { PipelineProgress } from '@/types';

type TaskSubtask = {
  title: string;
  status: string;
  error?: string;
  reason?: string;
  aweme_id?: string;
  creator_uid?: string;
};

const EMPTY_SUBTASKS: TaskSubtask[] = [];

type TaskPayload = {
  msg?: string;
  stage?: string;
  pipeline_progress?: PipelineProgress;
  subtasks?: unknown;
  missing_items?: unknown;
  result_summary?: unknown;
  uid?: string;
  creator_uid?: string;
};

function parsePayload(payload?: string): TaskPayload | null {
  if (!payload) return null;
  try {
    const parsed = JSON.parse(payload);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    return parsed as TaskPayload;
  } catch {
    return null;
  }
}

function buildTaskCenterProgressLine(task: Task, parsed: TaskPayload | null) {
  const pp = parsed?.pipeline_progress;
  const list = pp?.list ?? { done: 1, total: 1 };
  const listOk = list.total > 0 && list.done >= list.total;

  const missingFromPayload = Array.isArray(parsed?.missing_items) ? parsed?.missing_items.length : 0;
  const auditMissing = pp?.audit?.missing ?? missingFromPayload;

  const download = pp?.download ?? { done: 0, total: 1 };
  const transcribe = pp?.transcribe ?? { done: 0, total: 0 };
  const exportPp = pp?.export;
  const exportDone = exportPp?.done ?? (task.status === 'COMPLETED' ? 1 : 0);
  const exportTotal = exportPp?.total ?? 1;
  const exportFile = exportPp?.file ?? null;
  const exportStatus = exportPp?.status ?? null;

  const parts = [
    `列表 ${list.done}/${list.total}${listOk ? ' ✓' : ''}`,
    `对账 缺 ${auditMissing}`,
    `下载 ${download.done}/${download.total}`,
    `转写 ${transcribe.done}/${transcribe.total}`,
    `导出 ${exportDone}/${exportTotal}`,
  ];

  const meta = [exportFile ? String(exportFile) : '', exportStatus != null ? String(exportStatus) : '']
    .filter(Boolean)
    .join(' ');
  if (meta) parts.push(meta);
  return parts.join(' ');
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
  const parsed = useMemo(() => parsePayload(task.payload), [task.payload]);
  const showTaskCenterProgress =
    task.task_type === 'pipeline' || task.task_type === 'download' || task.task_type.startsWith('creator_sync_');
  const taskCenterProgressLine = showTaskCenterProgress ? buildTaskCenterProgressLine(task, parsed) : '';

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
            {duration && (
              <span className="text-[11px] text-muted-foreground tabular-nums">{duration}</span>
            )}
          </div>
          <div className="mt-1 text-xs font-mono text-muted-foreground/50">{task.task_id}</div>
        </div>
        <TaskActions
          task={task}
          isRunning={isRunning}
          isPaused={isPaused}
          isFailed={isFailed}
          onRetry={onRetry}
        />
      </div>

      {(isRunning || isPaused) && (
        <div className="mt-3 space-y-2">
          {showTaskCenterProgress ? (
            <div className="space-y-1 text-xs">
              <div className="text-muted-foreground">{message}</div>
              <div className="text-muted-foreground tabular-nums">{taskCenterProgressLine}</div>
            </div>
          ) : (
            <>
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
            </>
          )}
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

function TaskActions({
  task,
  isRunning,
  isPaused,
  isFailed,
  onRetry,
}: {
  task: Task;
  isRunning: boolean;
  isPaused: boolean;
  isFailed: boolean;
  onRetry: (task: Task) => void;
}) {
  const autoRetryEnabled = !!task.auto_retry;
  const canStop = isRunning || isPaused;

  return (
    <div className="mt-0.5 flex items-center gap-2">
      {isFailed && (
        <button
          onClick={() => onRetry(task)}
          className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
          title="重试（重新提交一个新任务）"
        >
          <RotateCw className="size-3.5" />
          重试
        </button>
      )}

      {isPaused && (
        <button
          onClick={async () => {
            try {
              await rerunTask(task.task_id);
              const { fetchInitialTasks } = useStore.getState();
              await fetchInitialTasks();
              toast.success('任务已恢复运行');
            } catch {
              // interceptor already toasts
            }
          }}
          className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
          title="恢复此任务（继续使用同一任务ID）"
        >
          <RotateCw className="size-3.5" />
          恢复
        </button>
      )}

      {isFailed && (
        <button
          onClick={async () => {
            const next = !autoRetryEnabled;
            try {
              await setAutoRetry(task.task_id, next);
              const { fetchInitialTasks } = useStore.getState();
              await fetchInitialTasks();
              toast.success(next ? '自动重试已启用' : '自动重试已关闭');
            } catch {
              // interceptor already toasts
            }
          }}
          className="flex h-8 items-center rounded-md px-3 text-xs font-medium text-primary transition-colors duration-200 hover:bg-primary/10"
          title="失败/过期后自动重试"
        >
          自动重试: {autoRetryEnabled ? '开' : '关'}
        </button>
      )}

      {canStop && (
        <button
          onClick={async () => {
            try {
              await cancelTask(task.task_id);
              const { fetchInitialTasks } = useStore.getState();
              await fetchInitialTasks();
              toast.success('任务已停止');
            } catch {
              // interceptor already toasts
            }
          }}
          className="flex h-8 items-center rounded-md px-3 text-xs font-medium text-muted-foreground transition-colors duration-200 hover:bg-muted hover:text-foreground"
          title="停止任务"
        >
          停止
        </button>
      )}

      {isRunning && <Loader2 className="size-4 animate-spin text-primary" />}
      {getTaskDisplayState(task) === 'success' && <CheckCircle2 className="size-4 text-success" />}
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
        className="flex h-8 items-center gap-1 rounded-md px-3 text-xs font-medium text-destructive transition-colors duration-200 hover:bg-destructive/10"
        title="删除任务（不可恢复）"
      >
        <Trash2 className="size-3.5" />
        删除
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
      reason?: unknown;
    }>;
  }, [parsed]);

  const enhancedSubtasks = useMemo(() => {
    if (!subtasks.length) return [];
    if (!missingItems.length && !creatorUidFromPayload) return subtasks;
    const byTitle = new Map<string, Array<{ awemeId: string; reason?: string }>>();
    for (const item of missingItems) {
      const title = typeof item.title === 'string' ? item.title : '';
      const awemeId = typeof item.aweme_id === 'string' ? item.aweme_id : '';
      const reason = typeof item.reason === 'string' ? item.reason : '';
      if (!title || !awemeId) continue;
      const list = byTitle.get(title) ?? [];
      list.push({ awemeId, reason: reason || undefined });
      byTitle.set(title, list);
    }

    const usedByTitle = new Map<string, number>();

    return subtasks.map((sub) => {
      if (sub.status !== 'manual_required') {
        return creatorUidFromPayload && !sub.creator_uid ? { ...sub, creator_uid: creatorUidFromPayload } : sub;
      }

      let awemeId = sub.aweme_id;
      let reason =
        typeof sub.reason === 'string' && sub.reason
          ? sub.reason
          : typeof sub.error === 'string' && sub.error
            ? sub.error
            : undefined;
      if (!awemeId && sub.title) {
        const list = byTitle.get(sub.title);
        if (list && list.length) {
          const used = usedByTitle.get(sub.title) ?? 0;
          const selected = list[Math.min(used, list.length - 1)];
          awemeId = selected?.awemeId;
          if (!reason && selected?.reason) reason = selected.reason;
          usedByTitle.set(sub.title, used + 1);
        }
      }

      return {
        ...sub,
        aweme_id: awemeId,
        creator_uid: sub.creator_uid ?? creatorUidFromPayload,
        reason,
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
            const manualReason =
              sub.status === 'manual_required'
                ? typeof sub.reason === 'string' && sub.reason
                  ? sub.reason
                  : typeof sub.error === 'string' && sub.error
                    ? sub.error
                    : undefined
                : undefined;
            const isCorruptFile = manualReason === 'corrupt_file';
            const reasonLabel = isCorruptFile ? '文件异常' : '';
            const actionLabel = isCorruptFile ? '重下并转写' : '补齐并转写';
            const successToast = isCorruptFile ? '已创建重下并转写任务' : '已创建补齐任务';
            const actionTitle = isCorruptFile ? '创建重下并转写任务' : '创建补齐并转写任务';
            const shouldShowErrorText = !!sub.error && !(sub.status === 'manual_required' && sub.error === 'corrupt_file');
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
                <div className="flex min-w-0 items-center gap-1.5">
                  <span
                    className={cn(
                      'block truncate',
                      sub.status === 'completed'
                        ? 'text-foreground/80'
                        : sub.status === 'skipped'
                          ? 'text-muted-foreground'
                          : sub.status === 'pending'
                            ? 'text-primary'
                            : 'text-destructive'
                    )}
                  >
                    {sub.title || '未命名'}
                  </span>
                  {reasonLabel && (
                    <span className="shrink-0 rounded-md bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium text-destructive">
                      {reasonLabel}
                    </span>
                  )}
                </div>
                {shouldShowErrorText && (
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
                      toast.success(successToast);
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
                  title={canRecover ? actionTitle : '缺少 aweme_id 或 creator_uid，无法创建补齐任务'}
                >
                  {isRecovering ? <Loader2 className="size-3 animate-spin" /> : <RotateCw className="size-3" />}
                  {actionLabel}
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
