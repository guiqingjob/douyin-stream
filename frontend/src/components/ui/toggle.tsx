import { cn } from '@/lib/utils';

export function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        if (disabled) return;
        onChange(!checked);
      }}
      className={cn(
        'relative inline-flex h-7 w-12 items-center rounded-full p-[2px] transition-all duration-200 spring-transition outline-none',
        'focus-visible:ring-2 focus-visible:ring-ring/40',
        !disabled && 'hover:ring-2 hover:ring-primary/20',
        disabled && 'cursor-not-allowed opacity-50',
        checked ? 'bg-primary' : 'bg-muted border border-border/60'
      )}
    >
      <span
        className={cn(
          'inline-block size-6 rounded-full bg-background shadow-sm transition-all duration-200 spring-transition',
          checked ? 'translate-x-[20px]' : 'translate-x-0'
        )}
      />
    </button>
  );
}
