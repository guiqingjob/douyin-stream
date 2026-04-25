import { CheckSquare, Folder, Loader2, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import type { ScannedFile } from '@/lib/api';

interface LocalTranscribeSectionProps {
  localDir: string;
  isScanning: boolean;
  scannedFiles: ScannedFile[];
  selectedLocalFiles: Set<string>;
  deleteAfterTranscribe: boolean;
  setDeleteAfterTranscribe: (v: boolean) => void;
  onSelectFolder: () => void;
  onToggleFile: (path: string) => void;
  onTranscribe: () => void;
  qwenReady: boolean;
  activeTask: boolean;
}

export function LocalTranscribeSection({
  localDir,
  isScanning,
  scannedFiles,
  selectedLocalFiles,
  deleteAfterTranscribe,
  setDeleteAfterTranscribe,
  onSelectFolder,
  onToggleFile,
  onTranscribe,
  qwenReady,
  activeTask,
}: LocalTranscribeSectionProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          className="w-full"
          disabled={isScanning}
          onClick={onSelectFolder}
        >
          {isScanning ? <Loader2 className="size-4 animate-spin mr-2" /> : <Folder className="size-4 mr-2" />}
          {isScanning ? '扫描中...' : '选择文件夹'}
        </Button>
      </div>
      {localDir && (
        <div className="text-xs text-muted-foreground truncate">
          {localDir}
        </div>
      )}

      {scannedFiles.length > 0 && (
        <div className="space-y-2 mt-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              找到 {scannedFiles.length} 个音视频文件
            </span>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>转写后删除源文件</span>
              <Toggle checked={deleteAfterTranscribe} onChange={setDeleteAfterTranscribe} />
            </div>
          </div>
          <div className="rounded-[var(--radius-card)] border border-border/60 bg-card overflow-hidden">
            {scannedFiles.map((file) => (
              <Button
                key={file.path}
                variant="ghost"
                type="button"
                onClick={() => onToggleFile(file.path)}
                className="h-auto w-full justify-start gap-3 rounded-none border-b border-border/40 px-4 py-2.5 text-left hover:bg-muted/40 last:border-b-0"
              >
                {selectedLocalFiles.has(file.path) ? (
                  <CheckSquare className="size-4 text-primary" />
                ) : (
                  <Square className="size-4 text-muted-foreground/60" />
                )}
                <span className="text-sm truncate flex-1 text-foreground">{file.name}</span>
                <span className="text-xs text-muted-foreground shrink-0 tabular-nums">{file.size_mb} MB</span>
              </Button>
            ))}
          </div>
          <Button
            variant="primary"
            onClick={onTranscribe}
            disabled={selectedLocalFiles.size === 0 || !qwenReady || activeTask}
            className="w-full"
          >
            转写 {selectedLocalFiles.size} 个文件
          </Button>
        </div>
      )}
    </div>
  );
}
