import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GlobalSettingsSection } from './GlobalSettingsSection'

describe('GlobalSettingsSection', () => {
  const defaultProps = {
    autoTranscribe: true,
    onToggleAutoTranscribe: vi.fn(),
    autoDeleteVideo: false,
    onToggleAutoDelete: vi.fn(),
    exportFormat: 'md',
    onChangeExportFormat: vi.fn(),
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

  it('shows export format value', () => {
    render(<GlobalSettingsSection {...defaultProps} exportFormat="docx" />)
    expect(screen.getByText('DOCX')).toBeInTheDocument()
  })

  it('calls onToggleAutoTranscribe when toggle clicked', () => {
    const onToggle = vi.fn()
    render(<GlobalSettingsSection {...defaultProps} onToggleAutoTranscribe={onToggle} />)
    const toggles = screen.getAllByRole('switch')
    fireEvent.click(toggles[0])
    expect(onToggle).toHaveBeenCalled()
  })

  it('calls onChangeExportFormat when format changed', () => {
    const onChange = vi.fn()
    render(<GlobalSettingsSection {...defaultProps} onChangeExportFormat={onChange} />)
    fireEvent.click(screen.getByText('DOCX'))
    expect(onChange).toHaveBeenCalledWith('docx')
  })
})
