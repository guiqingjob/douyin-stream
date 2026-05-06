import { CheckSquare, Square, Users } from 'lucide-react';
import { VirtuosoGrid } from 'react-virtuoso';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import type { DouyinMetadataResponse } from '@/lib/api';

interface VideoPreviewSectionProps {
  metadata: DouyinMetadataResponse;
  selectedUrls: Set<string>;
  onToggleSelect: (url: string) => void;
  onToggleAll: () => void;
  onFollowCreator: () => void;
  isFollowingCreator: boolean;
  isFollowed: boolean;
  canDownload: boolean;
  canRunPipeline: boolean;
  onDownloadBatch: () => void;
  onProcessBatch: () => void;
}

export function VideoPreviewSection({
  metadata,
  selectedUrls,
  onToggleSelect,
  onToggleAll,
  onFollowCreator,
  isFollowingCreator,
  isFollowed,
  canDownload,
  canRunPipeline,
  onDownloadBatch,
  onProcessBatch,
}: VideoPreviewSectionProps) {
  return (
    <section className="w-full space-y-6 flex-1 flex flex-col min-h-0">
      {/* Creator Info */}
      <div className="flex items-center gap-4 rounded-lg border border-border/60 bg-muted p-4">
        <div className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-secondary text-lg font-semibold text-foreground">
          {metadata.creator.nickname?.charAt(0) || 'D'}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-lg font-semibold text-foreground">{metadata.creator.nickname}</div>
          <div className="mt-1 text-sm text-muted-foreground">{metadata.videos.length} 条视频 / 已选 {selectedUrls.size} 条</div>
        </div>
        <Button
          onClick={onFollowCreator}
          disabled={isFollowingCreator || isFollowed}
          variant={isFollowed ? 'secondary' : 'primary'}
          size="sm"
        >
          {isFollowingCreator ? <Loader2 className="size-4 animate-spin" /> : null}
          {isFollowed ? '已在列表中' : '加入创作者列表'}
        </Button>
      </div>

      {/* Video Grid */}
      <VirtuosoGrid
        style={{ flex: '1 1 auto', minHeight: 0, width: '100%' }}
        data={metadata.videos}
        listClassName="grid grid-cols-2 gap-4 pb-28 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
        itemContent={(_index, video) => {
          const isSelected = selectedUrls.has(video.video_url);
          return (
            <Button
              key={video.aweme_id}
              variant="secondary"
              type="button"
              onClick={() => onToggleSelect(video.video_url)}
              className={cn(
                'group relative h-auto w-full cursor-pointer overflow-hidden rounded-[var(--radius-card)] border border-border/60 bg-card p-0 text-left transition-all duration-200 hover:-translate-y-[1px] hover:apple-shadow-md',
                isSelected
                  ? 'border-primary/50 bg-primary/5'
                  : 'border-border/60 bg-muted hover:bg-secondary'
              )}
            >
              <div className="relative aspect-[3/4] bg-muted">
                {video.cover_url ? (
                  <img src={video.cover_url} alt="Cover" className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-muted-foreground/40">
                    <Users className="size-8" />
                  </div>
                )}
                <div
                  className={cn(
                    'absolute right-2.5 top-2.5 flex h-6 w-6 items-center justify-center rounded-md transition-all duration-200',
                    isSelected
                      ? 'bg-primary text-primary-foreground'
                      : 'scale-90 border border-border/60 bg-background/80 backdrop-blur-sm group-hover:scale-100'
                  )}
                >
                  {isSelected && <CheckSquare className="size-3.5" />}
                </div>
              </div>
              <div className="p-3">
                <p className="line-clamp-2 text-xs leading-snug text-foreground/70">{video.desc || 'Untitled Video'}</p>
              </div>
            </Button>
          );
        }}
      />

      {/* Floating Action Bar */}
      <div className="fixed bottom-8 left-[calc(50%+8rem)] z-10 flex -translate-x-1/2 justify-center max-sm:bottom-20">
        <div className="flex items-center gap-4 rounded-lg apple-floating-bar py-3 pl-3 pr-3 apple-shadow-md">
          <Button
            variant="ghost"
            size="iconSm"
            onClick={onToggleAll}
            className="text-muted-foreground hover:bg-secondary hover:text-foreground"
            title={metadata.videos.length > 0 && metadata.videos.every((v) => selectedUrls.has(v.video_url)) ? '取消全选' : '全选'}
          >
            {metadata.videos.length > 0 && metadata.videos.every((v) => selectedUrls.has(v.video_url))
              ? <CheckSquare className="size-5" />
              : <Square className="size-5" />}
          </Button>
          <span className="text-sm font-medium text-foreground">{selectedUrls.size} 条已选择</span>
          <Button
            variant="secondary"
            size="sm"
            onClick={onDownloadBatch}
            disabled={selectedUrls.size === 0 || !canDownload}
          >
            仅下载
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onProcessBatch}
            disabled={selectedUrls.size === 0 || !canRunPipeline}
          >
            下载并转写
          </Button>
        </div>
      </div>
    </section>
  );
}
