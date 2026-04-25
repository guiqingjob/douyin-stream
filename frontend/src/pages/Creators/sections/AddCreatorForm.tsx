import { Loader2, Plus, TriangleAlert } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface AddCreatorFormProps {
  newCreatorUrl: string;
  setNewCreatorUrl: (v: string) => void;
  isAdding: boolean;
  onSubmit: (e: React.FormEvent) => void;
  canDownloadAny: boolean;
  autoTranscribe: boolean;
  qwenReady: boolean;
  douyinReady: boolean;
  bilibiliReady: boolean;
}

export function AddCreatorForm({
  newCreatorUrl,
  setNewCreatorUrl,
  isAdding,
  onSubmit,
  canDownloadAny,
  autoTranscribe,
  qwenReady,
  douyinReady,
  bilibiliReady,
}: AddCreatorFormProps) {
  return (
    <div className="w-full">
      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <Input
          icon={<Plus className="size-4" />}
          placeholder="粘贴抖音 / B站主页链接添加创作者"
          value={newCreatorUrl}
          onChange={(e) => setNewCreatorUrl(e.target.value)}
          disabled={isAdding}
          rightElement={
            <Button
              variant="primary"
              size="sm"
              disabled={!newCreatorUrl.trim() || isAdding}
              onClick={() => {}}
              type="submit"
            >
              {isAdding ? <Loader2 className="size-4 animate-spin" /> : '添加'}
            </Button>
          }
        />
      </form>

      {!canDownloadAny && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm leading-6 text-destructive mt-4">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>还没有配置可用下载账号（抖音 / B站），同步和下载无法工作。请先去设置页添加。</span>
        </div>
      )}
      {canDownloadAny && autoTranscribe && !qwenReady && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-warning/20 bg-warning/10 px-4 py-3 text-sm leading-6 text-warning mt-4">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>下载链路可用，但自动转写还需补齐 Qwen Cookie。</span>
        </div>
      )}
      {!douyinReady && bilibiliReady && (
        <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-warning/20 bg-warning/10 px-4 py-3 text-sm leading-6 text-warning mt-4">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>当前仅 B站下载链路可用；抖音创作者同步仍需补齐抖音 Cookie。</span>
        </div>
      )}
    </div>
  );
}
