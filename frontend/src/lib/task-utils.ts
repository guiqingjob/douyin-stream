import type { Task } from '@/lib/api';

const ACTIVE_STATUSES = new Set(['RUNNING', 'PENDING', 'PAUSED']);
const SUCCESS_STATUSES = new Set(['COMPLETED', 'SUCCESS']);
const FAILURE_STATUSES = new Set(['FAILED', 'ERROR', 'CANCELLED']);
const STALE_MINUTES = 20;

export type DisplayTaskState = 'running' | 'success' | 'failed' | 'stale' | 'unknown' | 'paused';

export function taskTypeLabel(type: string) {
  return (
    {
      pipeline: '下载并转写',
      download: '仅下载',
      local_transcribe: '本地转写',
      creator_sync_incremental: '创作者增量同步',
      creator_sync_full: '创作者全量同步',
      full_sync_incremental: '全量增量同步',
      full_sync_full: '全量全量同步',
      scan_all_following: '定时同步',
    }[type] || type
  );
}

export function parseTaskMessage(payload?: string) {
  if (!payload) return '';
  try {
    const parsed = JSON.parse(payload);
    if (typeof parsed?.msg === 'string') return parsed.msg;
  } catch {
    // ignore
  }
  return '';
}

export function taskTimestamp(task: Task) {
  const raw = task.update_time;
  if (!raw) return null;
  const value = new Date(raw).getTime();
  return Number.isFinite(value) ? value : null;
}

export function isTaskStale(task: Task, now = Date.now()) {
  if (!ACTIVE_STATUSES.has(task.status)) return false;
  const ts = taskTimestamp(task);
  if (!ts) return false;
  return now - ts > STALE_MINUTES * 60 * 1000;
}

export function getTaskDisplayState(task: Task): DisplayTaskState {
  if (task.status === 'PAUSED') return 'paused';
  if (isTaskStale(task)) return 'stale';
  if (ACTIVE_STATUSES.has(task.status)) return 'running';
  if (SUCCESS_STATUSES.has(task.status)) return 'success';
  if (FAILURE_STATUSES.has(task.status)) return 'failed';
  return 'unknown';
}

export function getTaskStatusLabel(task: Task) {
  const state = getTaskDisplayState(task);
  return (
    {
      running: '进行中',
      paused: '已暂停',
      success: '已完成',
      failed: '失败',
      stale: '已过期',
      unknown: task.status,
    }[state] || task.status
  );
}

export function getTaskMessage(task: Task) {
  return parseTaskMessage(task.payload) || task.error_msg || '暂无详细信息';
}

export function getTaskError(task: Task) {
  if (isTaskStale(task)) {
    return '这个任务长时间没有更新，通常意味着浏览器或后台进程已经中断。建议重新发起。';
  }
  return task.error_msg || '';
}

export function sortTasks(tasks: Task[]) {
  return [...tasks].sort((a, b) => {
    const at = taskTimestamp(a) || 0;
    const bt = taskTimestamp(b) || 0;
    return bt - at;
  });
}

export function formatRelativeTime(value?: string | null) {
  if (!value) return '暂无记录';
  const ts = new Date(value).getTime();
  if (!Number.isFinite(ts)) return '暂无记录';

  const diff = Date.now() - ts;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diff < minute) return '刚刚';
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`;
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`;
  return `${Math.floor(diff / day)} 天前`;
}

/** Short format for tight spaces (e.g. sidebar list item second line). Keeps within ~120px horizontal budget. */
export function formatRelativeTimeShort(value?: string | null) {
  if (!value) return '';
  const ts = new Date(value).getTime();
  if (!Number.isFinite(ts)) return '';

  const diff = Date.now() - ts;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diff < minute) return '刚刚';
  if (diff < hour) return `${Math.floor(diff / minute)}分钟前`;
  if (diff < day) {
    const h = Math.floor(diff / hour);
    return h === 1 ? '1小时前' : `${h}小时前`;
  }
  if (diff < 2 * day) return '昨天';
  if (diff < 7 * day) return `${Math.floor(diff / day)}天前`;
  // For older dates: show month-day like "5-15" to stay narrow
  const d = new Date(ts);
  return `${d.getMonth() + 1}-${d.getDate()}`;
}

export function getTaskDuration(task: Task): string {
  const ts = taskTimestamp(task);
  if (!ts) return '';

  const state = getTaskDisplayState(task);
  const now = Date.now();

  // For running tasks: time elapsed since update_time (approximation of start)
  // For completed/failed: show how long ago it finished
  if (state === 'running') {
    const elapsed = now - ts;
    return `进行中 ${formatDurationMs(elapsed)}`;
  }

  // For finished tasks, show time elapsed since finish
  const elapsed = now - ts;
  return formatDurationMs(elapsed) + '前';
}

function formatDurationMs(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}秒`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min < 60) return sec > 0 ? `${min}分${sec}秒` : `${min}分`;
  const hr = Math.floor(min / 60);
  const remainMin = min % 60;
  return remainMin > 0 ? `${hr}小时${remainMin}分` : `${hr}小时`;
}

export type TaskFilterCategory = 'all' | 'download' | 'transcribe' | 'sync';

export function getTaskFilterCategory(taskType: string): TaskFilterCategory {
  if (taskType === 'download' || taskType.startsWith('creator_sync')) return 'download';
  if (taskType === 'pipeline' || taskType === 'local_transcribe') return 'transcribe';
  if (taskType.startsWith('full_sync') || taskType === 'scan_all_following') return 'sync';
  return 'all';
}

export function filterTasksByCategory(tasks: Task[], category: TaskFilterCategory): Task[] {
  if (category === 'all') return tasks;
  return tasks.filter((t) => getTaskFilterCategory(t.task_type) === category);
}
