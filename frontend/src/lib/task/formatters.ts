import type { Task } from '@/lib/api';

export function taskTimestamp(task: Task) {
  const raw = task.update_time;
  if (!raw) return null;
  const value = new Date(raw).getTime();
  return Number.isFinite(value) ? value : null;
}

export function truncateText(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
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

export function formatDurationMs(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}秒`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min < 60) return sec > 0 ? `${min}分${sec}秒` : `${min}分`;
  const hr = Math.floor(min / 60);
  const remainMin = min % 60;
  return remainMin > 0 ? `${hr}小时${remainMin}分` : `${hr}小时`;
}
