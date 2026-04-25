import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DeleteConfirmDialogs } from './DeleteConfirmDialogs'

describe('DeleteConfirmDialogs', () => {
  const defaultProps = {
    deletingDouyinId: null as string | null,
    setDeletingDouyinId: vi.fn(),
    onDeleteDouyin: vi.fn(),
    deletingQwenId: null as string | null,
    setDeletingQwenId: vi.fn(),
    onDeleteQwen: vi.fn(),
    deletingBilibiliId: null as string | null,
    setDeletingBilibiliId: vi.fn(),
    onDeleteBilibili: vi.fn(),
  }

  it('does not render any dialog when no deletion is pending', () => {
    render(<DeleteConfirmDialogs {...defaultProps} />)
    expect(screen.queryByText('移除抖音账号')).not.toBeInTheDocument()
    expect(screen.queryByText('移除 Qwen 账号')).not.toBeInTheDocument()
    expect(screen.queryByText('移除B站账号')).not.toBeInTheDocument()
  })

  it('renders douyin delete dialog when deletingDouyinId is set', () => {
    render(<DeleteConfirmDialogs {...defaultProps} deletingDouyinId="douyin-123" />)
    expect(screen.getByText('移除抖音账号')).toBeInTheDocument()
    expect(screen.getByText(/确定要从账号池中移除这个抖音账号吗/)).toBeInTheDocument()
  })

  it('renders qwen delete dialog when deletingQwenId is set', () => {
    render(<DeleteConfirmDialogs {...defaultProps} deletingQwenId="qwen-456" />)
    expect(screen.getByText('移除 Qwen 账号')).toBeInTheDocument()
    expect(screen.getByText(/确定要从账号池中移除这个 Qwen 账号吗/)).toBeInTheDocument()
  })

  it('renders bilibili delete dialog when deletingBilibiliId is set', () => {
    render(<DeleteConfirmDialogs {...defaultProps} deletingBilibiliId="bili-789" />)
    expect(screen.getByText('移除B站账号')).toBeInTheDocument()
    expect(screen.getByText(/确定要从账号池中移除这个B站账号吗/)).toBeInTheDocument()
  })

  it('calls onDeleteDouyin when confirm clicked', () => {
    const onDeleteDouyin = vi.fn()
    render(<DeleteConfirmDialogs {...defaultProps} deletingDouyinId="douyin-123" onDeleteDouyin={onDeleteDouyin} />)
    fireEvent.click(screen.getByRole('button', { name: '移除' }))
    expect(onDeleteDouyin).toHaveBeenCalledWith('douyin-123')
  })
})
