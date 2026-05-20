import { AnimatePresence, motion } from 'framer-motion';
import { RefreshCw, Trash2 } from 'lucide-react';
import { Switch } from '@/components/ui/switch';

interface CreatorActionMenuModalProps {
  creator: { uid: string; nickname: string } | null;
  onClose: () => void;
  onSync: () => void;
  onFullSync: () => void;
  isAutoSync: boolean;
  onToggleAutoSync: () => void;
  onDelete: () => void;
}

export function CreatorActionMenuModal({
  creator,
  onClose,
  onSync,
  onFullSync,
  isAutoSync,
  onToggleAutoSync,
  onDelete,
}: CreatorActionMenuModalProps) {
  return (
    <AnimatePresence>
      {creator && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="bg-[var(--color-paper)] w-full sm:max-w-sm sm:mx-4 border border-[var(--color-hairline-strong)] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 border-b border-[var(--color-hairline)]">
              <div className="eyebrow mb-1">creator dossier</div>
              <div className="font-display text-[22px] text-[var(--color-bone)] truncate">{creator.nickname}</div>
            </div>
            <div>
              <button
                onClick={onSync}
                className="w-full flex items-center gap-4 px-5 py-4 hover:bg-[rgba(243,238,219,0.03)] transition-colors text-left border-b border-[var(--color-hairline-faint)] group"
              >
                <RefreshCw className="w-3.5 h-3.5 text-[var(--color-rust)]" />
                <span className="font-display text-[18px] text-[var(--color-bone)] group-hover:text-[var(--color-rust)] transition-colors">立即同步</span>
              </button>
              <button
                onClick={onFullSync}
                className="w-full flex items-center gap-4 px-5 py-4 hover:bg-[rgba(243,238,219,0.03)] transition-colors text-left border-b border-[var(--color-hairline-faint)] group"
              >
                <RefreshCw className="w-3.5 h-3.5 text-[var(--color-rust)]" />
                <span className="font-display text-[18px] text-[var(--color-bone)] group-hover:text-[var(--color-rust)] transition-colors">全量重拉</span>
              </button>
              <div className="w-full flex items-center justify-between px-5 py-4 border-b border-[var(--color-hairline-faint)]">
                <span className="font-display text-[18px] text-[var(--color-bone)]">自动同步</span>
                <Switch
                  checked={isAutoSync}
                  onCheckedChange={onToggleAutoSync}
                />
              </div>
              <button
                onClick={onDelete}
                className="w-full flex items-center gap-4 px-5 py-4 hover:bg-[rgba(178,89,80,0.08)] transition-colors text-left group"
              >
                <Trash2 className="w-3.5 h-3.5 text-[var(--color-iron)]" />
                <span className="font-display text-[18px] text-[var(--color-iron)]">删除创作者</span>
              </button>
            </div>
            <div className="p-3 border-t border-[var(--color-hairline)]">
              <button onClick={onClose} className="w-full btn-sharp">cancel · 取消</button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
