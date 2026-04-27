import { ExternalLink, Download, HardDriveDownload, Loader2, RefreshCcw, Trash2, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatRelativeTime, getTaskDisplayState, getTaskError, getTaskMessage } from '@/lib/task-utils';
import type { Creator, Task } from '@/lib/api';

interface CreatorCardProps {
  creator: Creator;
  tasks: Task[];
  downloadingCreators: Record<string, 'incremental' | 'full' | null>;
  isDeleting: boolean;
  onDownload: (uid: string, nickname: string, mode: 'incremental' | 'full') => void;
  onTranscribe: (uid: string, nickname: string) => void;
  transcribingUids: Set<string>;
  onDelete: (uid: string) => void;
  settings?: {
    status_summary?: {
      douyin_ready?: boolean;
      bilibili_accounts_count?: number;
      douyin_primary_configured?: boolean;
      douyin_cookie_source?: 'config' | 'pool' | 'none' | string;
    };
  } | null;
}

function getCreatorPlatform(creator: Creator): 'douyin' | 'bilibili' | 'local' {
  if (creator.platform === 'bilibili' || creator.uid.startsWith('bilibili:')) return 'bilibili';
  if (creator.platform === 'local' || creator.uid.startsWith('local:')) return 'local';
  return 'douyin';
}

function findRelatedTask(creator: Creator, tasks: Task[]) {
  const keywords = [creator.uid, creator.nickname].filter(Boolean) as string[];
  return tasks.find((task) => {
    if (!task.task_type.startsWith('creator_sync_')) return false;
    const haystacks = [task.payload || '', task.error_msg || ''];
    return keywords.some((keyword) => haystacks.some((value) => value.includes(keyword)));
  });
}

export function CreatorCard({
  creator,
  tasks,
  downloadingCreators,
  isDeleting,
  onDownload,
  onTranscribe,
  transcribingUids,
  onDelete,
  settings,
}: CreatorCardProps) {
  const platform = getCreatorPlatform(creator);
  const isBusy = !!downloadingCreators[creator.uid];
  const relatedTask = findRelatedTask(creator, tasks);
  const taskState = relatedTask ? getTaskDisplayState(relatedTask) : null;
  const taskMessage = relatedTask ? getTaskMessage(relatedTask) : '';
  const taskError = relatedTask ? getTaskError(relatedTask) : '';

  const douyinReady = settings?.status_summary?.douyin_ready ?? false;
  const bilibiliReady = (settings?.status_summary?.bilibili_accounts_count ?? 0) > 0;
  const douyinPrimaryConfigured = settings?.status_summary?.douyin_primary_configured ?? false;
  const douyinCookieSource = settings?.status_summary?.douyin_cookie_source ?? 'none';

  const creatorReady = platform === 'bilibili' ? bilibiliReady : platform === 'local' ? false : douyinReady;

  const statusBadge = platform === 'local'
    ? { label: '本地素材', tone: 'default' as const }
    : !creatorReady
      ? {
          label: platform === 'bilibili' ? '缺少B站账号' : '缺少抖音账号',
          tone: 'destructive' as const,
        }
      : isBusy || taskState === 'running'
        ? { label: '同步中', tone: 'secondary' as const }
        : taskState === 'failed' || taskState === 'stale'
          ? creator.last_fetch_time
            ? { label: '同步异常', tone: 'destructive' as const }
            : { label: '首次同步失败', tone: 'destructive' as const }
          : creator.last_fetch_time
            ? { label: '可同步', tone: 'secondary' as const }
            : { label: '待首次同步', tone: 'default' as const };

  return (
    <div className={cn('rounded-[var(--radius-card)] border border-border/60 bg-card p-5 apple-shadow-md transition-all duration-200 hover:-translate-y-[1px]', isDeleting && 'opacity-0 scale-95')}>
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-[var(--radius-card)] bg-secondary text-xl font-semibold text-foreground">
          {(creator.nickname || creator.uid).charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[15px] font-semibold text-foreground line-clamp-1">
              {creator.nickname || creator.uid}
            </span>
            {creator.homepage_url && (
              <a
                href={creator.homepage_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                title="打开主页"
              >
                <ExternalLink className="size-3.5" />
              </a>
            )}
            <Badge tone={statusBadge.tone}>{statusBadge.label}</Badge>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs">
            <span className="text-muted-foreground">
              素材 <strong className="text-foreground font-medium tabular-nums">{creator.asset_count || 0}</strong>
            </span>
            <span className="text-muted-foreground">
              已转写 <strong className="text-foreground font-medium tabular-nums">{creator.transcript_completed_count || 0}</strong>
            </span>
            <span className="text-muted-foreground">
              待处理 <strong className="text-foreground font-medium tabular-nums">{creator.transcript_pending_count || 0}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Task info */}
      <div className="mt-4">
        <div className="h-[52px] flex items-center justify-between px-3 rounded-lg transition-colors duration-200 hover:bg-muted/40">
          <span className="text-sm text-muted-foreground">上次同步</span>
          <span className="text-sm text-foreground/75 tabular-nums">{formatRelativeTime(creator.last_fetch_time)}</span>
        </div>
      </div>
      {taskMessage && taskMessage !== '暂无详细信息' && (
        <div className="text-sm leading-6 text-foreground/75 mt-1">{taskMessage}</div>
      )}
      {taskError && (
        <div className="rounded-[var(--radius-card)] border border-destructive/20 bg-destructive/10 p-3 text-xs leading-6 text-destructive mt-2">
          {taskError}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-2 mt-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onDownload(creator.uid, creator.nickname, 'incremental')}
          disabled={!creatorReady || isBusy || platform === 'local'}
          className="flex-1"
        >
          {downloadingCreators[creator.uid] === 'incremental' ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
          增量
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onDownload(creator.uid, creator.nickname, 'full')}
          disabled={!creatorReady || isBusy || platform === 'local'}
          className="flex-1"
        >
          {downloadingCreators[creator.uid] === 'full' ? <Loader2 className="size-4 animate-spin" /> : <HardDriveDownload className="size-4" />}
          全量
        </Button>
        {(creator.transcript_pending_count ?? 0) > 0 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onTranscribe(creator.uid, creator.nickname)}
            disabled={transcribingUids.has(creator.uid)}
            className="flex-1"
          >
            {transcribingUids.has(creator.uid) ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
            转写
          </Button>
        )}
      </div>

      {/* Footer */}
      <div className="h-[52px] mt-3 flex items-center justify-between px-3 rounded-lg text-xs text-muted-foreground transition-colors duration-200 hover:bg-muted/40">
        <div className="flex items-center gap-1.5">
          <RefreshCcw className="size-3.5" />
          {platform === 'local'
            ? '本地导入素材不支持远程同步'
            : !creatorReady
              ? platform === 'bilibili'
                ? '请先配置B站账号'
                : '请先配置抖音账号'
              : platform === 'bilibili'
                ? `使用B站账号池 (${settings?.status_summary?.bilibili_accounts_count ?? 0})`
                : douyinPrimaryConfigured
                  ? '使用主 Cookie'
                  : douyinCookieSource === 'pool'
                    ? '使用账号池 Cookie'
                    : '使用可用配置'}
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onDelete(creator.uid)}
          className="h-7 px-2 text-xs"
        >
          <Trash2 className="size-3.5" />
          删除
        </Button>
      </div>
    </div>
  );
}
