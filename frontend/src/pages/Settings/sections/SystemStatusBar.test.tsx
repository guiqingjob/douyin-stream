import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SystemStatusBar } from './SystemStatusBar'

describe('SystemStatusBar', () => {
  it('renders all status indicators', () => {
    render(
      <SystemStatusBar
        douyinReady={true}
        douyinCookieSource="pool"
        douyinAccountsCount={2}
        qwenReady={true}
        qwenAccountsCount={1}
        bilibiliReady={false}
        bilibiliAccountsCount={0}
        canRunPipeline={true}
        canDownload={true}
      />
    )

    expect(screen.getByText('系统状态')).toBeInTheDocument()
    expect(screen.getByText(/抖音: 账号池 \(2\)/)).toBeInTheDocument()
    expect(screen.getByText(/Qwen: 账号池 \(1\)/)).toBeInTheDocument()
    expect(screen.getByText('B站: 未配置')).toBeInTheDocument()
    expect(screen.getByText('可下载+转写')).toBeInTheDocument()
  })

  it('shows douyin config file source when not from pool', () => {
    render(
      <SystemStatusBar
        douyinReady={true}
        douyinCookieSource="config"
        douyinAccountsCount={0}
        qwenReady={false}
        qwenAccountsCount={0}
        bilibiliReady={false}
        bilibiliAccountsCount={0}
        canRunPipeline={false}
        canDownload={true}
      />
    )

    expect(screen.getByText('抖音: 配置文件')).toBeInTheDocument()
    expect(screen.getByText('仅可下载')).toBeInTheDocument()
  })

  it('shows not ready states', () => {
    render(
      <SystemStatusBar
        douyinReady={false}
        douyinCookieSource="none"
        douyinAccountsCount={0}
        qwenReady={false}
        qwenAccountsCount={0}
        bilibiliReady={false}
        bilibiliAccountsCount={0}
        canRunPipeline={false}
        canDownload={false}
      />
    )

    expect(screen.getByText('抖音: 未配置')).toBeInTheDocument()
    expect(screen.getByText('Qwen: 未配置')).toBeInTheDocument()
    expect(screen.getByText('未就绪')).toBeInTheDocument()
  })
})
