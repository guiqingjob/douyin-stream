import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GlobalSettingsSection } from './GlobalSettingsSection'

describe('GlobalSettingsSection', () => {
  const defaultProps = {
    autoTranscribe: true,
    onToggleAutoTranscribe: vi.fn(),
    autoDeleteVideo: false,
    onToggleAutoDelete: vi.fn(),
    concurrency: 3,
    setConcurrency: vi.fn(),
    isSavingConcurrency: false,
    onSaveConcurrency: vi.fn(),
    refreshSettings: vi.fn(),
  }

  it('renders all settings', () => {
    render(<GlobalSettingsSection {...defaultProps} />)
    expect(screen.getByText('全局参数')).toBeInTheDocument()
    expect(screen.getByText('自动转写')).toBeInTheDocument()
    expect(screen.getByText('自动删除源视频')).toBeInTheDocument()
    expect(screen.getByText('并发数')).toBeInTheDocument()
    expect(screen.getByText('清理不存在素材')).toBeInTheDocument()
  })

  it('shows concurrency value', () => {
    render(<GlobalSettingsSection {...defaultProps} concurrency={5} />)
    const input = screen.getByDisplayValue('5')
    expect(input).toBeInTheDocument()
  })

  it('calls onToggleAutoTranscribe when toggle clicked', () => {
    const onToggle = vi.fn()
    render(<GlobalSettingsSection {...defaultProps} onToggleAutoTranscribe={onToggle} />)
    const toggles = screen.getAllByRole('switch')
    fireEvent.click(toggles[0])
    expect(onToggle).toHaveBeenCalled()
  })

  it('calls onSaveConcurrency when save button clicked', () => {
    const onSave = vi.fn()
    render(<GlobalSettingsSection {...defaultProps} onSaveConcurrency={onSave} />)
    fireEvent.click(screen.getByRole('button', { name: /保存并发设置/ }))
    expect(onSave).toHaveBeenCalled()
  })
})
