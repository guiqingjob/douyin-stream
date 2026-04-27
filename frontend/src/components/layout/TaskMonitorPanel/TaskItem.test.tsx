import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TaskItem } from './TaskItem'

vi.mock('@/lib/api', () => ({
  cancelTask: vi.fn(),
  rerunTask: vi.fn(),
  setAutoRetry: vi.fn(),
  deleteTask: vi.fn(),
  recoverAwemeAndTranscribe: vi.fn(),
}))

vi.mock('@/store/useStore', () => {
  const useStore = (() => ({})) as unknown as { getState: () => { fetchInitialTasks: () => Promise<void> } }
  useStore.getState = () => ({ fetchInitialTasks: vi.fn(async () => void 0) })
  return { useStore }
})

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('TaskItem', () => {
  it('shows clarified controls for FAILED', () => {
    render(
      <TaskItem
        task={{
          task_id: 'failed-1',
          task_type: 'pipeline',
          status: 'FAILED',
          progress: 0,
          payload: JSON.stringify({ msg: 'x' }),
          auto_retry: 0,
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '自动重试: 关' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '恢复' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '停止' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument()
  })

  it('shows clarified controls for PAUSED', () => {
    render(
      <TaskItem
        task={{
          task_id: 'paused-1',
          task_type: 'pipeline',
          status: 'PAUSED',
          progress: 0.5,
          payload: JSON.stringify({ msg: 'x' }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: '恢复' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '停止' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '重试' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /自动重试:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument()
  })

  it('shows clarified controls for RUNNING', () => {
    render(
      <TaskItem
        task={{
          task_id: 'running-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.5,
          payload: JSON.stringify({ msg: 'x' }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: '停止' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '恢复' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '重试' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /自动重试:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument()
  })

  it('renders task-center progress line and export meta', () => {
    render(
      <TaskItem
        task={{
          task_id: 'running-export-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.85,
          payload: JSON.stringify({
            msg: 'x',
            pipeline_progress: {
              stage: 'export',
              list: { done: 1, total: 1 },
              audit: { missing: 2 },
              download: { done: 3, total: 5 },
              transcribe: { done: 1, total: 5 },
              export: { done: 0, total: 1, file: 'out.md', status: 'polling' },
            },
          }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={vi.fn()}
      />
    )

    expect(screen.getByText('列表 1/1 ✓ 对账 缺 2 下载 3/5 转写 1/5 导出 0/1 out.md polling')).toBeInTheDocument()
  })

  it('shows 文件异常 and 重下并转写 for corrupt_file manual_required', () => {
    render(
      <TaskItem
        task={{
          task_id: 't1',
          task_type: 'pipeline',
          status: 'FAILED',
          progress: 0,
          payload: JSON.stringify({
            msg: 'x',
            subtasks: [
              {
                title: 'v1',
                status: 'manual_required',
                error: 'corrupt_file',
                aweme_id: '123',
                creator_uid: 'douyin:1',
              },
            ],
          }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={true}
        onToggleExpand={vi.fn()}
      />
    )

    expect(screen.getByText('文件异常')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /重下并转写/ })).toBeInTheDocument()
    expect(screen.queryByText('补齐并转写')).not.toBeInTheDocument()
  })
})
