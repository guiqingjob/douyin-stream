import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SyncSection } from './SyncSection'

describe('SyncSection', () => {
  it('renders schedule info and toggle', () => {
    render(
      <SyncSection
        scheduleTask={{ task_id: '1', task_type: 'scan_all_following', cron_expr: '0 2 * * *', enabled: true, update_time: '' }}
        onToggle={vi.fn()}
        onFullSync={vi.fn()}
        douyinReady={true}
      />
    )

    expect(screen.getByText('定时同步')).toBeInTheDocument()
    expect(screen.getByText('每天 02:00 自动同步全部创作者')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '立即同步所有创作者' })).toBeEnabled()
  })

  it('disables sync button when douyin not ready', () => {
    render(
      <SyncSection
        scheduleTask={null}
        onToggle={vi.fn()}
        onFullSync={vi.fn()}
        douyinReady={false}
      />
    )

    expect(screen.getByRole('button', { name: '立即同步所有创作者' })).toBeDisabled()
    expect(screen.getByText('先添加抖音账号 Cookie 再执行同步。')).toBeInTheDocument()
  })

  it('calls onToggle when toggle is clicked', () => {
    const onToggle = vi.fn()
    render(
      <SyncSection
        scheduleTask={{ task_id: '1', task_type: 'scan_all_following', cron_expr: '0 2 * * *', enabled: false, update_time: '' }}
        onToggle={onToggle}
        onFullSync={vi.fn()}
        douyinReady={true}
      />
    )

    fireEvent.click(screen.getByRole('switch'))
    expect(onToggle).toHaveBeenCalledWith(true)
  })

  it('calls onFullSync when sync button clicked', () => {
    const onFullSync = vi.fn()
    render(
      <SyncSection
        scheduleTask={null}
        onToggle={vi.fn()}
        onFullSync={onFullSync}
        douyinReady={true}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: '立即同步所有创作者' }))
    expect(onFullSync).toHaveBeenCalled()
  })
})
