import type { Task } from '@/lib/api';
import type { TaskStage, TaskProgress } from '@/types';

const ACTIVE_STATUSES = new Set(['RUNNING', 'PENDING', 'PAUSED']);
const SUCCESS_STATUSES = new Set(['COMPLETED', 'SUCCESS']);
const PARTIAL_STATUSES = new Set(['PARTIAL_FAILED']);
const FAILURE_STATUSES = new Set(['FAILED', 'ERROR', 'CANCELLED']);
const STALE_MINUTES = 20;

export type DisplayTaskState = 'running' | 'success' | 'failed' | 'partial' | 'stale' | 'unknown' | 'paused';

export interface StageInfo {
  label: string;
  icon: string;
  color: 'primary' | 'success' | 'destructive' | 'muted';
}

const STAGE_CONFIG: Record<TaskStage, StageInfo> = {
  created: { label: '等待中', icon: '⏳', color: 'muted' },
  fetching: { label: '获取列表', icon: '📋', color: 'primary' },
  auditing: { label: '对账中', icon: '✔️', color: 'primary' },
  downloading: { label: '下载中', icon: '⬇️', color: 'primary' },
  transcribing: { label: '转写中', icon: '✍️', color: 'primary' },
  exporting: { label: '导出中', icon: '📤', color: 'primary' },
  completed: { label: '已完成', icon: '✅', color: 'success' },
  failed: { label: '失败', icon: '❌', color: 'destructive' },
  cancelled: { label: '已取消', icon: '🚫', color: 'muted' },
};

export function getStageInfo(stage: TaskStage): StageInfo {
  return STAGE_CONFIG[stage] || { label: stage, icon: '❓', color: 'muted' };
}

export function formatStageMessage(task: Task, progress?: TaskProgress | null): string {
  if (!progress) {
    return parseTaskMessage(task.payload) || '';
  }

  const { stage, download_progress, transcribe_progress } = progress;

  if (stage === 'fetching') {
    return '正在获取视频列表...';
  }

  if (stage === 'auditing') {
    const total = download_progress?.total || 0;
    const downloaded = download_progress?.downloaded || 0;
    const skipped = download_progress?.skipped || 0;
    return `对账中：发现 ${downloaded + skipped} 个本地已有，${total - downloaded - skipped} 个待下载`;
  }

  if (stage === 'downloading' && download_progress) {
    const { downloaded, total, current_video, current_index } = download_progress;
    const videoLabel = current_video ? `：${truncateText(current_video, 40)}` : '';
    return `正在下载 (${downloaded + 1}/${total})${videoLabel}`;
  }

  if (stage === 'transcribing' && transcribe_progress) {
    const { done, total, current_video, current_account } = transcribe_progress;
    const accountLabel = current_account ? ` [${current_account}]` : '';
    const videoLabel = current_video ? `：${truncateText(current_video, 40)}` : '';
    return `正在转写 (${done + 1}/${total})${accountLabel}${videoLabel}`;
  }

  if (stage === 'exporting') {
    return '正在导出字幕文件...';
  }

  if (stage === 'completed') {
    const dl = download_progress;
    const tp = transcribe_progress;
    const dlInfo = dl ? `下载 ${dl.downloaded} 个` : '';
    const tpInfo = tp ? `，转写 ${tp.done} 个` : '';
    if (dlInfo || tpInfo) {
      return `已完成：${dlInfo}${tpInfo}`;
    }
    return '已完成';
  }

  if (stage === 'failed') {
    const errors = progress.errors;
    if (errors.length > 0) {
      const lastError = errors[errors.length - 1];
      return `失败：${lastError.error || lastError.title || '未知错误'}`;
    }
    return '失败';
  }

  if (stage === 'cancelled') {
    return '已取消';
  }

  return parseTaskMessage(task.payload) || '';
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function getProgressPercent(task: Task, progress?: TaskProgress | null): number {
  if (progress?.overall_percent) {
    return Math.round(progress.overall_percent);
  }

  if (progress?.download_progress) {
    const { downloaded, skipped, total } = progress.download_progress;
    if (total > 0) {
      return Math.round(((downloaded + skipped) / total) * 100);
    }
  }

  return Math.round((task.progress || 0) * 100);
}

export function getProgressDetails(task: Task, progress?: TaskProgress | null): string {
  if (!progress) return '';

  const parts: string[] = [];

  if (progress.download_progress) {
    const { downloaded, skipped, failed } = progress.download_progress;
    if (downloaded > 0) parts.push(`下载完成 ${downloaded} 个`);
    if (skipped > 0) parts.push(`跳过 ${skipped} 个`);
    if (failed > 0) parts.push(`失败 ${failed} 个`);
  }

  if (progress.transcribe_progress) {
    const { done, skipped, failed } = progress.transcribe_progress;
    if (done > 0) parts.push(`转写完成 ${done} 个`);
    if (skipped > 0) parts.push(`转写跳过 ${skipped} 个`);
    if (failed > 0) parts.push(`转写失败 ${failed} 个`);
  }

  return parts.join('，');
}

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
    return '';
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
  if (ACTIVE_STATUSES.has(task.status)) {
    // 后端可能未及时更新状态，检测消息内容判断是否实际已完成
    const msg = parseTaskMessage(task.payload);
    if (msg.includes('全部下载完成') || msg.includes('下载完成') || msg.includes('全部转写完成') || msg.includes('转写完成')) {
      return 'success';
    }
    // 检查 pipeline_progress：下载任务所有视频已下载完成
    if (task.task_type === 'download') {
      try {
        const parsed = JSON.parse(task.payload);
        const pp = parsed?.pipeline_progress;
        if (pp?.download && typeof pp.download.done === 'number' && typeof pp.download.total === 'number'
            && pp.download.total > 0 && pp.download.done >= pp.download.total) {
          return 'success';
        }
      } catch { /* ignore */ }
    }
    return 'running';
  }
  if (SUCCESS_STATUSES.has(task.status)) return 'success';
  if (PARTIAL_STATUSES.has(task.status)) return 'partial';
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
      partial: '部分失败',
      failed: '失败',
      stale: '已过期',
      unknown: task.status,
    }[state] || task.status
  );
}

export function getTaskMessage(task: Task) {
  const msg = parseTaskMessage(task.payload) || task.error_msg || '';
  if (msg) return msg;
  // Completed tasks with no message is normal — don't show a confusing fallback
  if (task.status === 'COMPLETED' || task.status === 'SUCCESS') return '';
  return '暂无详细信息';
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
  const d = new Date(ts);
  return `${d.getMonth() + 1}-${d.getDate()}`;
}

export function getTaskDuration(task: Task): string {
  const ts = taskTimestamp(task);
  if (!ts) return '';

  const state = getTaskDisplayState(task);
  const now = Date.now();

  if (state === 'running') {
    const elapsed = now - ts;
    return `进行中 ${formatDurationMs(elapsed)}`;
  }

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
