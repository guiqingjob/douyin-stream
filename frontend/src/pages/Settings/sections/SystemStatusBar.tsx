import { cn } from '@/lib/utils';

interface SystemStatusBarProps {
  douyinReady: boolean;
  douyinCookieSource: string;
  douyinAccountsCount: number;
  qwenReady: boolean;
  qwenAccountsCount: number;
  bilibiliReady: boolean;
  bilibiliAccountsCount: number;
  canRunPipeline: boolean;
  canDownload: boolean;
}

export function SystemStatusBar({
  douyinReady,
  douyinCookieSource,
  douyinAccountsCount,
  qwenReady,
  qwenAccountsCount,
  bilibiliReady,
  bilibiliAccountsCount,
  canRunPipeline,
  canDownload,
}: SystemStatusBarProps) {
  return (
    <div className="w-full">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span className="text-muted-foreground font-medium">系统状态</span>
        <span className="flex items-center gap-1.5 text-foreground">
          <span className={cn('size-2 rounded-md', douyinReady ? 'bg-success' : 'bg-destructive')} />
          {douyinReady
            ? douyinCookieSource === 'pool' ? `抖音: 账号池 (${douyinAccountsCount})` : '抖音: 配置文件'
            : '抖音: 未配置'}
        </span>
        <span className="flex items-center gap-1.5 text-foreground">
          <span className={cn('size-2 rounded-md', qwenReady ? 'bg-success' : 'bg-warning')} />
          {qwenReady
            ? qwenAccountsCount > 0
              ? `Qwen: 账号池 (${qwenAccountsCount})`
              : 'Qwen: 已配置'
            : 'Qwen: 未配置'}
        </span>
        <span className="flex items-center gap-1.5 text-foreground">
          <span className={cn('size-2 rounded-md', bilibiliReady ? 'bg-success' : 'bg-warning')} />
          {bilibiliReady
            ? `B站: 账号池 (${bilibiliAccountsCount})`
            : 'B站: 未配置'}
        </span>
        <span className="flex items-center gap-1.5 text-foreground">
          <span className={cn('size-2 rounded-md', canRunPipeline ? 'bg-success' : canDownload ? 'bg-warning' : 'bg-destructive')} />
          {canRunPipeline ? '可下载+转写' : canDownload ? '仅可下载' : '未就绪'}
        </span>
      </div>
    </div>
  );
}
