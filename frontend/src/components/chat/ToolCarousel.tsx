import { useRef, useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ToolCard from './ToolCard';
import type { ToolSearchResult } from '../../types';

interface ToolCarouselProps {
  tools: ToolSearchResult[];
  onToolClick: (tool: ToolSearchResult) => void;
}

export default function ToolCarousel({ tools, onToolClick }: ToolCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 1);
  }, []);

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (el) {
      el.addEventListener('scroll', checkScroll);
      return () => el.removeEventListener('scroll', checkScroll);
    }
  }, [checkScroll, tools]);

  const scroll = (direction: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    const amount = 280;
    el.scrollBy({ left: direction === 'left' ? -amount : amount, behavior: 'smooth' });
  };

  // Handle keyboard arrow key scrolling within the carousel
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      scroll('left');
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      scroll('right');
    }
  }, []);

  if (tools.length === 0) return null;

  return (
    <div className="relative">
      <h3 className="text-white text-sm font-semibold mb-3 px-2">
        Recommended Tools ({tools.length})
      </h3>

      <div className="relative">
        {canScrollLeft && (
          <button
            onClick={() => scroll('left')}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-cgiar-dark/80 hover:bg-cgiar-dark rounded-full flex items-center justify-center text-white shadow-lg transition-colors"
            aria-label="Scroll left"
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </button>
        )}

        <div
          ref={scrollRef}
          className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 px-1"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          tabIndex={0}
          role="region"
          aria-label="Recommended tools carousel"
          onKeyDown={handleKeyDown}
        >
          {tools.map(tool => (
            <ToolCard
              key={tool.id}
              tool={tool}
              onClick={() => onToolClick(tool)}
            />
          ))}
        </div>

        {canScrollRight && (
          <button
            onClick={() => scroll('right')}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 bg-cgiar-dark/80 hover:bg-cgiar-dark rounded-full flex items-center justify-center text-white shadow-lg transition-colors"
            aria-label="Scroll right"
          >
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
