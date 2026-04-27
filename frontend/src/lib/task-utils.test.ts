import { describe, it, expect } from 'vitest';
import {
  taskTypeLabel,
  parseTaskMessage,
  getTaskDisplayState,
  getTaskStatusLabel,
  getTaskMessage,
  getTaskError,
  sortTasks,
  formatRelativeTime,
  formatRelativeTimeShort,
  getTaskDuration,
  getTaskFilterCategory,
  filterTasksByCategory,
} from './task-utils';
import type { Task } from '@/types';

function makeTask(partial: Partial<Task> & { task_id: string }): Task {
  return {
    task_id: partial.task_id,
    task_type: partial.task_type || 'pipeline',
    status: partial.status || 'RUNNING',
    progress: partial.progress ?? 0,
    payload: partial.payload || '',
    error_msg: partial.error_msg,
    update_time: partial.update_time,
  };
}

describe('taskTypeLabel', () => {
  it('returns Chinese label for known types', () => {
    expect(taskTypeLabel('pipeline')).toBe('下载并转写');
    expect(taskTypeLabel('download')).toBe('仅下载');
    expect(taskTypeLabel('local_transcribe')).toBe('本地转写');
  });

  it('returns original type for unknown', () => {
    expect(taskTypeLabel('unknown_type')).toBe('unknown_type');
  });
});

describe('parseTaskMessage', () => {
  it('extracts msg from JSON payload', () => {
    expect(parseTaskMessage(JSON.stringify({ msg: 'hello' }))).toBe('hello');
  });

  it('returns empty string for invalid JSON', () => {
    expect(parseTaskMessage('not json')).toBe('');
  });

  it('returns empty string for empty payload', () => {
    expect(parseTaskMessage('')).toBe('');
    expect(parseTaskMessage(undefined)).toBe('');
  });
});

describe('getTaskDisplayState', () => {
  it('returns running for active status', () => {
    expect(getTaskDisplayState(makeTask({ task_id: '1', status: 'RUNNING' }))).toBe('running');
    expect(getTaskDisplayState(makeTask({ task_id: '2', status: 'PENDING' }))).toBe('running');
  });

  it('returns paused for PAUSED', () => {
    expect(getTaskDisplayState(makeTask({ task_id: '1', status: 'PAUSED' }))).toBe('paused');
  });

  it('returns success for completed', () => {
    expect(getTaskDisplayState(makeTask({ task_id: '1', status: 'COMPLETED' }))).toBe('success');
  });

  it('returns failed for failed', () => {
    expect(getTaskDisplayState(makeTask({ task_id: '1', status: 'FAILED' }))).toBe('failed');
  });

  it('returns stale for stale running tasks', () => {
    const old = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    expect(getTaskDisplayState(makeTask({ task_id: '1', status: 'RUNNING', update_time: old }))).toBe('stale');
  });
});

describe('getTaskStatusLabel', () => {
  it('returns Chinese labels', () => {
    expect(getTaskStatusLabel(makeTask({ task_id: '1', status: 'COMPLETED' }))).toBe('已完成');
    expect(getTaskStatusLabel(makeTask({ task_id: '1', status: 'FAILED' }))).toBe('失败');
  });
});

describe('getTaskMessage', () => {
  it('prefers payload msg', () => {
    const t = makeTask({ task_id: '1', payload: JSON.stringify({ msg: 'hello' }), error_msg: 'err' });
    expect(getTaskMessage(t)).toBe('hello');
  });

  it('falls back to error_msg', () => {
    const t = makeTask({ task_id: '1', error_msg: 'err' });
    expect(getTaskMessage(t)).toBe('err');
  });
});

describe('getTaskError', () => {
  it('returns stale message for stale tasks', () => {
    const old = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    const t = makeTask({ task_id: '1', status: 'RUNNING', update_time: old });
    expect(getTaskError(t)).toContain('长时间没有更新');
  });

  it('returns error_msg for failed tasks', () => {
    const t = makeTask({ task_id: '1', status: 'FAILED', error_msg: 'oops' });
    expect(getTaskError(t)).toBe('oops');
  });
});

describe('sortTasks', () => {
  it('sorts by update_time descending', () => {
    const t1 = makeTask({ task_id: '1', update_time: '2026-01-01T00:00:00Z' });
    const t2 = makeTask({ task_id: '2', update_time: '2026-01-02T00:00:00Z' });
    const sorted = sortTasks([t1, t2]);
    expect(sorted[0].task_id).toBe('2');
    expect(sorted[1].task_id).toBe('1');
  });
});

describe('formatRelativeTime', () => {
  it('handles just now', () => {
    expect(formatRelativeTime(new Date().toISOString())).toBe('刚刚');
  });

  it('handles minutes ago', () => {
    const d = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelativeTime(d)).toBe('5 分钟前');
  });

  it('handles null', () => {
    expect(formatRelativeTime(null)).toBe('暂无记录');
  });
});

describe('formatRelativeTimeShort', () => {
  it('returns empty for null', () => {
    expect(formatRelativeTimeShort(null)).toBe('');
  });

  it('formats without spaces', () => {
    const d = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelativeTimeShort(d)).toBe('5分钟前');
  });
});

describe('getTaskDuration', () => {
  it('returns empty when no timestamp', () => {
    expect(getTaskDuration(makeTask({ task_id: '1' }))).toBe('');
  });

  it('shows elapsed for running tasks', () => {
    const t = makeTask({ task_id: '1', status: 'RUNNING', update_time: new Date(Date.now() - 30_000).toISOString() });
    expect(getTaskDuration(t)).toContain('进行中');
  });
});

describe('getTaskFilterCategory', () => {
  it('classifies task types', () => {
    expect(getTaskFilterCategory('download')).toBe('download');
    expect(getTaskFilterCategory('creator_sync_incremental')).toBe('download');
    expect(getTaskFilterCategory('pipeline')).toBe('transcribe');
    expect(getTaskFilterCategory('full_sync_incremental')).toBe('sync');
    expect(getTaskFilterCategory('unknown')).toBe('all');
  });
});

describe('filterTasksByCategory', () => {
  it('returns all for all category', () => {
    const tasks = [makeTask({ task_id: '1', task_type: 'download' }), makeTask({ task_id: '2', task_type: 'pipeline' })];
    expect(filterTasksByCategory(tasks, 'all')).toHaveLength(2);
  });

  it('filters by category', () => {
    const tasks = [makeTask({ task_id: '1', task_type: 'download' }), makeTask({ task_id: '2', task_type: 'pipeline' })];
    expect(filterTasksByCategory(tasks, 'download')).toHaveLength(1);
    expect(filterTasksByCategory(tasks, 'download')[0].task_id).toBe('1');
  });
});
