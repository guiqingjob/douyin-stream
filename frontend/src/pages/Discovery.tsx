import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Search } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { TaskStatusBanner } from '@/components/layout/TaskStatusBanner';
import { PageHeader } from '@/components/ui/PageHeader';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { AppleEmptyState } from '@/components/ui/AppleEmptyState';
import { Badge } from '@/components/ui/badge';
import { PageShell } from '@/components/layout/PageShell';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { LocalTranscribeSection } from './Discovery/sections/LocalTranscribeSection';
import { VideoPreviewSection } from './Discovery/sections/VideoPreviewSection';
import { useDiscoveryActions } from './Discovery/useDiscoveryActions';

export default function Discovery() {
  const [url, setUrl] = useState('');
  const activeTaskId = useStore((s) => s.activeTaskId);
  const setActiveTaskId = useStore((s) => s.setActiveTaskId);
  const tasks = useStore((s) => s.tasks);
  const settings = useStore((s) => s.settings);
  const storeFetchCreators = useStore((s) => s.fetchCreators);

  const douyinReady = settings?.status_summary.douyin_ready ?? false;
  const qwenReady = settings?.status_summary.can_transcribe ?? false;
  const canDownload = douyinReady;
  const canRunPipeline = douyinReady && qwenReady;

  const {
    isFetching,
    metadata,
    selectedUrls,
    isFollowingCreator,
    isFollowed,
    resultMsg,
    confirmDialogOpen,
    localDir,
    isScanning,
    scannedFiles,
    selectedLocalFiles,
    deleteAfterTranscribe,
    activeTask,
    taskState,
    taskMessage,
    taskError,
    handleFetch,
    handleConfirmFetch,
    handleToggleSelect,
    handleToggleAll,
    handleProcessBatch,
    handleDownloadBatch,
    handleFollowCreator,
    handleSelectFolder,
    handleToggleLocalFile,
    handleLocalTranscribe,
    setConfirmDialogOpen,
    setDeleteAfterTranscribe,
  } = useDiscoveryActions({
    url,
    tasks,
    activeTaskId,
    setActiveTaskId,
    storeFetchCreators,
  });

  return (
    <PageShell variant="default">
      <div className="flex flex-col gap-6">
        <PageHeader
          title="发现"
          description="预览抖音主页视频，勾选后按需下载或转写。"
        />

        <div className="w-full">
          <form onSubmit={handleFetch} className="flex items-center gap-2">
            <Input
              icon={<Search className="size-4" />}
              placeholder="粘贴抖音主页链接，例如 douyin.com/user/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={isFetching || !!activeTask}
              rightElement={
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!url.trim() || isFetching || !!activeTask}
                  type="submit"
                >
                  {isFetching ? <Loader2 className="size-4 animate-spin" /> : '获取预览'}
                </Button>
              }
            />
          </form>

          {(!douyinReady || !canRunPipeline) && (
            <div className="flex flex-wrap items-center gap-2 mt-3">
              {!douyinReady && <Badge tone="destructive">缺少抖音账号 Cookie</Badge>}
              {douyinReady && !qwenReady && <Badge tone="warning">转写待补齐 Qwen Cookie</Badge>}
              <Link to="/settings" className="text-xs text-primary hover:underline">去设置页补齐</Link>
            </div>
          )}

          <div className="flex items-center gap-3 my-6">
            <div className="h-px flex-1 bg-border/60" />
            <span className="text-xs text-muted-foreground font-medium">或</span>
            <div className="h-px flex-1 bg-border/60" />
          </div>

          <LocalTranscribeSection
            localDir={localDir}
            isScanning={isScanning}
            scannedFiles={scannedFiles}
            selectedLocalFiles={selectedLocalFiles}
            deleteAfterTranscribe={deleteAfterTranscribe}
            setDeleteAfterTranscribe={setDeleteAfterTranscribe}
            onSelectFolder={handleSelectFolder}
            onToggleFile={handleToggleLocalFile}
            onTranscribe={handleLocalTranscribe}
            qwenReady={qwenReady}
            activeTask={!!activeTask}
          />
        </div>

        {activeTask && (
          <TaskStatusBanner
            title={taskState === 'running' ? '后台任务正在执行' : taskState === 'success' ? '任务已完成' : '任务执行异常'}
            message={taskMessage || '后台已接收任务，请等待进度更新。'}
            tone={taskState === 'running' ? 'running' : taskState === 'success' ? 'success' : 'error'}
            error={taskState === 'failed' || taskState === 'stale' ? taskError : undefined}
          />
        )}

        {resultMsg && !activeTask && (
          <TaskStatusBanner
            title={resultMsg.type === 'success' ? '操作已完成' : '操作失败'}
            message={resultMsg.text}
            tone={resultMsg.type === 'success' ? 'success' : 'error'}
            error={resultMsg.error}
          />
        )}

        {isFetching && (
          <section className="w-full space-y-6">
            <div className="flex items-center gap-4 rounded-lg border border-border/60 bg-muted p-4">
              <div className="size-14 shrink-0 rounded-[var(--radius-card)] skeleton-shimmer" />
              <div className="flex-1 space-y-3">
                <div className="h-5 w-32 rounded-lg skeleton-shimmer" />
                <div className="h-4 w-24 rounded-lg skeleton-shimmer" />
              </div>
              <div className="h-9 w-32 rounded-lg skeleton-shimmer" />
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="rounded-lg border border-border/60 bg-muted overflow-hidden">
                  <div className="aspect-[3/4] skeleton-shimmer" />
                  <div className="p-3 space-y-2">
                    <div className="h-3 w-full rounded-lg skeleton-shimmer" />
                    <div className="h-3 w-2/3 rounded-lg skeleton-shimmer" />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {metadata && (
          <VideoPreviewSection
            metadata={metadata}
            selectedUrls={selectedUrls}
            onToggleSelect={handleToggleSelect}
            onToggleAll={handleToggleAll}
            onFollowCreator={handleFollowCreator}
            isFollowingCreator={isFollowingCreator}
            isFollowed={isFollowed}
            canDownload={canDownload}
            canRunPipeline={canRunPipeline}
            onDownloadBatch={handleDownloadBatch}
            onProcessBatch={handleProcessBatch}
          />
        )}

        {!metadata && !isFetching && (
          <div className="w-full">
            <AppleEmptyState
              icon={<Search className="size-8 stroke-[1.5]" />}
              title="粘贴主页链接开始预览"
              description="勾选感兴趣的视频后再执行下载或转写。"
            />
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmDialogOpen}
        onOpenChange={setConfirmDialogOpen}
        title="确认获取新预览"
        description={`获取新预览将清除已选的 ${selectedUrls.size} 个视频，确定继续吗？`}
        confirmLabel="继续"
        onConfirm={handleConfirmFetch}
      />
    </PageShell>
  );
}
