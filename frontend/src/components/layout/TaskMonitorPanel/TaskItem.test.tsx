import { describe, it, expect, vi } from 'vitest'
import { render, screen, within, fireEvent, waitFor } from '@testing-library/react'
import { TaskItem } from './TaskItem'

vi.mock('@/lib/api', () => ({
  cancelTask: vi.fn(),
  rerunTask: vi.fn(),
  setAutoRetry: vi.fn(),
  deleteTask: vi.fn(),
  recoverAwemeAndTranscribe: vi.fn(),
  retryCreatorTranscribeCleanup: vi.fn(async () => ({
    task_id: 'running-export-meta-1',
    deleted_count: 1,
    failed_count: 0,
    failed_paths: [],
    total_deleted_count: 2,
  })),
}))

vi.mock('@/store/useStore', () => {
  const fetchInitialTasks = vi.fn(async () => void 0)
  const useStore = (() => ({})) as unknown as { getState: () => { fetchInitialTasks: () => Promise<void> } }
  useStore.getState = () => ({ fetchInitialTasks })
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

  it('falls back to legacy progress bar when pipeline_progress missing', () => {
    render(
      <TaskItem
        task={{
          task_id: 'running-legacy-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.25,
          payload: JSON.stringify({ msg: 'x' }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={vi.fn()}
      />,
    )

    expect(screen.getByText('x')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
    expect(screen.queryByText(/列表/)).not.toBeInTheDocument()
  })

  it('shows remaining workload badge computed from pipeline_progress.download', () => {
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
              stage: 'download',
              list: { done: 58, total: 58 },
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

    expect(screen.getByText('剩余 2 条')).toBeInTheDocument()
    expect(screen.getByText(/下载 3\/5/)).toBeInTheDocument()
    expect(screen.getByText(/缺失 2/)).toBeInTheDocument()
  })

  it('renders -- instead of 0/0 when totals missing in pipeline_progress', () => {
    render(
      <TaskItem
        task={{
          task_id: 'running-missing-total-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.3,
          payload: JSON.stringify({
            msg: 'x',
            pipeline_progress: {
              stage: 'download',
              download: { done: 1, total: 0 },
            },
          }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={true}
        onToggleExpand={vi.fn()}
      />,
    )

    expect(screen.queryByText('0/0')).not.toBeInTheDocument()
    expect(screen.getAllByText('1/--').length).toBeGreaterThan(0)
  })

  it('toggles drawer when clicking collapsed row', () => {
    const onToggleExpand = vi.fn()
    render(
      <TaskItem
        task={{
          task_id: 'running-toggle-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.85,
          payload: JSON.stringify({
            msg: 'x',
            pipeline_progress: {
              stage: 'download',
              download: { done: 1, total: 3 },
            },
          }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={false}
        onToggleExpand={onToggleExpand}
      />
    )

    screen.getByRole('button', { name: /剩余 2 条/ }).click()
    expect(onToggleExpand).toHaveBeenCalledWith('running-toggle-1')
  })

  it('shows export file + status inside drawer export card', async () => {
    render(
      <TaskItem
        task={{
          task_id: 'running-export-meta-1',
          task_type: 'pipeline',
          status: 'RUNNING',
          progress: 0.85,
          payload: JSON.stringify({
            msg: 'x',
            pipeline_progress: {
              stage: 'download',
              list: { done: 58, total: 58 },
              audit: { missing: 2 },
              download: { done: 3, total: 5 },
              transcribe: { done: 1, total: 5 },
              export: { done: 0, total: 1, file: 'out.md', status: 'polling' },
            },
            cleanup_deleted_count: 1,
            cleanup_failed_count: 2,
            cleanup_failed_paths: [
              { path: '/tmp/a', reason: 'corrupt_file' },
              { path: '/tmp/b', reason: 'http_403' },
            ],
          }),
          error_msg: '',
          update_time: new Date().toISOString(),
        }}
        onRetry={vi.fn()}
        isExpanded={true}
        onToggleExpand={vi.fn()}
      />,
    )

    const exportCard = screen.getByTestId('task-center-export-card')
    expect(within(exportCard).getByText('out.md')).toBeInTheDocument()
    expect(within(exportCard).getByText('准备导出')).toBeInTheDocument()

    expect(screen.getByText('清理汇总')).toBeInTheDocument()
    expect(screen.getByText('成功 1 · 失败 2 · 共 3')).toBeInTheDocument()
    expect(screen.getByText('文件异常 × 1')).toBeInTheDocument()
    expect(screen.getByText('403 无权限 × 1')).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: '重试清理' })
    expect(retryButton).toBeEnabled()

    fireEvent.click(retryButton)

    const { retryCreatorTranscribeCleanup } = await import('@/lib/api')
    const { useStore } = await import('@/store/useStore')
    const { toast } = await import('sonner')

    await waitFor(() => {
      expect(vi.mocked(retryCreatorTranscribeCleanup)).toHaveBeenCalledWith('running-export-meta-1')
    })
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(useStore.getState().fetchInitialTasks).toHaveBeenCalled()
    })
  })

})
