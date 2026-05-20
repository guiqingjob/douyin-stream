import { motion } from 'framer-motion';
import { Loader2, RefreshCw, MoreHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CreatorCardProps {
  creator: {
    uid: string;
    nickname?: string;
    auto_sync?: boolean | number;
    asset_count?: number;
    transcript_completed_count?: number;
  };
  isSyncing: boolean;
  isDeleting: boolean;
  onClick: () => void;
  onSync: (e: React.MouseEvent) => void;
  onMore: (e: React.MouseEvent) => void;
}

export function CreatorCard({
  creator,
  isSyncing,
  isDeleting,
  onClick,
  onSync,
  onMore,
}: CreatorCardProps) {
  return (
    <motion.div
      layout
      className="bg-[var(--color-ink)] p-5 cursor-pointer group hover:bg-[var(--color-paper)] transition-colors relative"
      onClick={onClick}
    >
      {/* Auto/manual badge */}
      <div className="flex justify-end mb-3">
        <span className={cn('text-[10px] tracking-[0.16em] uppercase', creator.auto_sync ? 'text-[var(--color-rust)]' : 'text-[var(--color-smoke)]')}>
          {creator.auto_sync ? '自动' : '手动'}
        </span>
      </div>

      {/* Name */}
      <div className="font-display text-[24px] text-[var(--color-bone)] leading-tight group-hover:text-[var(--color-rust)] transition-colors line-clamp-2 min-h-[60px]">
        {creator.nickname || '未命名'}
      </div>

      {/* Stats */}
      <div className="mt-4 pt-3 border-t border-[var(--color-hairline-faint)] flex items-baseline justify-between">
        <span className="text-[12px] text-[var(--color-ash)]">
          <span className="font-display text-[18px] text-[var(--color-bone)] tabular mr-1">{creator.asset_count || 0}</span>
          视频
        </span>
        <span className="text-[12px] text-[var(--color-ash)]">
          <span className="font-display text-[18px] text-[var(--color-rust)] tabular mr-1">{creator.transcript_completed_count || 0}</span>
          文稿
        </span>
      </div>

      {/* Hover actions */}
      <div className="absolute top-3 left-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onSync}
          disabled={isSyncing || isDeleting}
          className="w-7 h-7 flex items-center justify-center bg-[var(--color-vellum)] border border-[var(--color-hairline-strong)] hover:border-[var(--color-rust)] hover:text-[var(--color-rust)] transition-colors text-[var(--color-ash)]"
          title="同步"
        >
          {isSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
        </button>
        <button
          onClick={onMore}
          disabled={isDeleting}
          className="w-7 h-7 flex items-center justify-center bg-[var(--color-vellum)] border border-[var(--color-hairline-strong)] hover:border-[var(--color-rust)] hover:text-[var(--color-rust)] transition-colors text-[var(--color-ash)]"
          title="更多"
        >
          {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <MoreHorizontal className="w-3 h-3" />}
        </button>
      </div>
    </motion.div>
  );
}
