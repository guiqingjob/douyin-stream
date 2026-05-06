import { useState, useEffect, useRef } from 'react';
import { Search, X, FileText, User, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface SearchResult {
  type: 'asset' | 'creator' | 'task';
  id: string;
  title: string;
  subtitle?: string;
  status?: string;
}

interface SearchBarProps {
  onSelect?: (result: SearchResult) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    
    const fetchResults = async () => {
      try {
        const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(fetchResults, 200);
    return () => clearTimeout(debounce);
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (results.length > 0 && onSelect) {
      onSelect(results[0]);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    setQuery('');
    setIsOpen(false);
    onSelect?.(result);
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'asset':
        return <FileText className="w-4 h-4 text-blue-500" />;
      case 'creator':
        return <User className="w-4 h-4 text-green-500" />;
      case 'task':
        return <Clock className="w-4 h-4 text-orange-500" />;
      default:
        return <Search className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'asset':
        return '素材';
      case 'creator':
        return '创作者';
      case 'task':
        return '任务';
      default:
        return '';
    }
  };

  return (
    <div className="relative w-full max-w-md">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="搜索素材、创作者、任务..."
            className={cn(
              "h-9 pl-9 pr-9",
              "rounded-[var(--radius-button)]",
              "border border-border/60",
              "bg-background/80 backdrop-blur-sm",
              "placeholder:text-muted-foreground/60",
              "focus:outline-none focus:ring-2 focus:ring-primary/30",
              "transition-all duration-200",
              "hover:border-border"
            )}
          />
          {query && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 h-6 w-6"
              onClick={() => {
                setQuery('');
                setResults([]);
              }}
            >
              <X className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </form>

      {isOpen && (query || loading) && (
        <div
          ref={dropdownRef}
          className={cn(
            "absolute top-full left-0 right-0 mt-2",
            "max-h-80 overflow-auto",
            "bg-background border border-border/60 rounded-[var(--radius-card)]",
            "shadow-lg shadow-black/5",
            "apple-shadow-md",
            "z-50",
            "apple-fade-in"
          )}
        >
          {loading ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              搜索中...
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground text-sm">
              未找到相关结果
            </div>
          ) : (
            <div className="py-1">
              {results.map((result, index) => (
                <button
                  key={`${result.type}-${result.id}-${index}`}
                  className={cn(
                    "w-full px-3 py-2.5",
                    "flex items-center gap-3",
                    "text-left",
                    "hover:bg-accent/50",
                    "transition-colors",
                    "cursor-pointer"
                  )}
                  onClick={() => handleResultClick(result)}
                >
                  {getIcon(result.type)}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {result.title}
                    </div>
                    {result.subtitle && (
                      <div className="text-xs text-muted-foreground truncate">
                        {result.subtitle}
                      </div>
                    )}
                  </div>
                  <div className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    "bg-muted/50 text-muted-foreground"
                  )}>
                    {getTypeLabel(result.type)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}