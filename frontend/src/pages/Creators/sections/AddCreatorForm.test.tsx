import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AddCreatorForm } from './AddCreatorForm'

describe('AddCreatorForm', () => {
  const defaultProps = {
    newCreatorUrl: '',
    setNewCreatorUrl: vi.fn(),
    isAdding: false,
    onSubmit: vi.fn((e) => e.preventDefault()),
    canDownloadAny: true,
    autoTranscribe: false,
    qwenReady: true,
    douyinReady: true,
    bilibiliReady: false,
  }

  it('renders input and add button', () => {
    render(<AddCreatorForm {...defaultProps} />)
    expect(screen.getByPlaceholderText('粘贴抖音 / B站主页链接添加创作者')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '添加' })).toBeInTheDocument()
  })

  it('disables add button when url is empty', () => {
    render(<AddCreatorForm {...defaultProps} />)
    expect(screen.getByRole('button', { name: '添加' })).toBeDisabled()
  })

  it('enables add button when url is filled', () => {
    render(<AddCreatorForm {...defaultProps} newCreatorUrl="https://douyin.com/user/123" />)
    expect(screen.getByRole('button', { name: '添加' })).toBeEnabled()
  })

  it('shows warning when no download account configured', () => {
    render(<AddCreatorForm {...defaultProps} canDownloadAny={false} />)
    expect(screen.getByText(/还没有配置可用下载账号/)).toBeInTheDocument()
  })

  it('calls onSubmit when form is submitted', () => {
    const onSubmit = vi.fn((e) => e.preventDefault())
    const { container } = render(<AddCreatorForm {...defaultProps} onSubmit={onSubmit} newCreatorUrl="test-url" />)
    const form = container.querySelector('form')
    expect(form).not.toBeNull()
    fireEvent.submit(form!)
    expect(onSubmit).toHaveBeenCalled()
  })
})
