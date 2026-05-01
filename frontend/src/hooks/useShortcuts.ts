import { useEffect, useRef } from 'react';

type ShortcutHandler = (e: KeyboardEvent) => void;

export interface ShortcutMap {
  [key: string]: ShortcutHandler;
}

export interface ShortcutOptions {
  enabled?: boolean;
  /** If false, shortcuts still fire when focus is in an input/textarea. */
  ignoreEditable?: boolean;
}

/**
 * Bind keyboard shortcuts to the window while the component is mounted.
 *
 * Key syntax (case-insensitive for letters):
 *   - 'j', 'k', 'Enter', 'Escape', 'ArrowLeft', 'Delete', 'Backspace'
 *   - modifier prefixes: '$mod+a' ($mod = Meta on macOS, Ctrl elsewhere),
 *     'shift+x', 'shift+$mod+a'
 *
 * Handlers receive the raw KeyboardEvent and may call preventDefault().
 *
 * The `map` is read through a ref so callers can safely pass a new object
 * literal each render without forcing a window listener re-attach.
 */
export function useShortcuts(map: ShortcutMap, opts: ShortcutOptions = {}): void {
  const { enabled = true, ignoreEditable = true } = opts;
  const mapRef = useRef<ShortcutMap>(map);
  mapRef.current = map;

  useEffect(() => {
    if (!enabled) return;

    const isMac = typeof navigator !== 'undefined' && /Mac|iP(hone|od|ad)/.test(navigator.platform);

    const normalizeBinding = (binding: string): string => {
      const parts = binding.toLowerCase().split('+').map((p) => p.trim());
      const key = parts.pop() ?? '';
      parts.sort();
      return [...parts, key].join('+');
    };

    const normalizeEvent = (e: KeyboardEvent): string => {
      const mods: string[] = [];
      if (e.altKey) mods.push('alt');
      if (e.shiftKey) mods.push('shift');
      if (isMac ? e.metaKey : e.ctrlKey) mods.push('$mod');
      // Stray ctrl on mac (not $mod)
      if (isMac && e.ctrlKey) mods.push('ctrl');
      if (!isMac && e.metaKey) mods.push('meta');
      mods.sort();
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      return [...mods, key].join('+');
    };

    const handler = (e: KeyboardEvent) => {
      if ((e as unknown as { isComposing?: boolean }).isComposing) return;
      if (ignoreEditable) {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return;
      }
      const sig = normalizeEvent(e);
      const current = mapRef.current;
      for (const k of Object.keys(current)) {
        if (normalizeBinding(k) === sig) {
          current[k](e);
          return;
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [enabled, ignoreEditable]);
}
