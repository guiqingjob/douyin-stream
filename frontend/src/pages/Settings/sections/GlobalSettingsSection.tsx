import { Clock3, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Toggle } from '@/components/ui/toggle';
import { toast } from 'sonner';
import { cleanupMissingAssets } from '@/lib/api';
import { useStore } from '@/store/useStore';

interface GlobalSettingsSectionProps {
  autoTranscribe: boolean;
  onToggleAutoTranscribe: (value: boolean) => void;
  autoDeleteVideo: boolean;
  onToggleAutoDelete: (value: boolean) => void;
  concurrency: number;
  setConcurrency: (v: number) => void;
  isSavingConcurrency: boolean;
  onSaveConcurrency: () => void;
  refreshSettings: () => void;
}

export function GlobalSettingsSection({
  autoTranscribe,
  onToggleAutoTranscribe,
  autoDeleteVideo,
  onToggleAutoDelete,
  concurrency,
  setConcurrency,
  isSavingConcurrency,
  onSaveConcurrency,
  refreshSettings,
}: GlobalSettingsSectionProps) {
  return (
    <div className="w-full">
      <div className="rounded-[var(--radius-card)] border border-border/60 bg-card p-1">
        <div className="h-12 px-4 flex items-center gap-3 border-b border-border/60">
          <div className="size-5 rounded-sm bg-foreground flex items-center justify-center">
            <Clock3 className="size-4 text-white" />
          </div>
          <h3 className="text-[17px] font-semibold text-foreground">全局参数</h3>
        </div>
        <div className="px-4 py-3 space-y-3">
          <div className="text-[13px] text-muted-foreground">下载后的自动化行为和并发控制。</div>
          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-[13px] font-medium text-foreground">自动转写</div>
              <div className="text-xs text-muted-foreground">下载完成后自动调用 Qwen 转写。</div>
            </div>
            <Toggle checked={autoTranscribe} onChange={onToggleAutoTranscribe} />
          </div>
          <div className="flex items-center justify-between py-2 border-t border-border/60">
            <div>
              <div className="text-[13px] font-medium text-foreground">自动删除源视频</div>
              <div className="text-xs text-muted-foreground">转写完成后自动删除原始视频文件。</div>
            </div>
            <Toggle checked={autoDeleteVideo} onChange={onToggleAutoDelete} />
          </div>
          <div className="py-2 border-t border-border/60">
            <label className="text-[13px] font-medium text-foreground">并发数</label>
            <div className="mt-2 flex items-center gap-3">
              <Input
                value={concurrency.toString()}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10) || 1;
                  setConcurrency(Math.min(10, Math.max(1, val)));
                }}
                className="w-20"
              />
              <span className="text-xs text-muted-foreground">建议 3，确认稳定后可提高。</span>
            </div>
          </div>
          <div className="py-2 border-t border-border/60">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[13px] font-medium text-foreground">清理不存在素材</div>
                <div className="text-xs text-muted-foreground">删除本地文件已被删除的素材记录。</div>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={async () => {
                  try {
                    const result = await cleanupMissingAssets();
                    toast.success(`已清理 ${result.deleted} 条无效记录`);
                    useStore.getState().fetchCreators(true); refreshSettings();
                  } catch {
                    // interceptor already toasts;
                  }
                }}
              >
                <Trash2 className="size-4" />
                清理
              </Button>
            </div>
          </div>
          <div className="pt-2">
            <Button
              variant="primary"
              onClick={onSaveConcurrency}
              disabled={isSavingConcurrency}
            >
              {isSavingConcurrency && <Loader2 className="size-4 animate-spin" />}
              保存并发设置
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
