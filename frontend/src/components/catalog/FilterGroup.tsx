import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { FacetCounts } from '../../types';

interface FilterGroupProps {
  title: string;
  options: string[];
  selected: string[];
  facetCounts: FacetCounts;
  onToggle: (value: string) => void;
  type: 'checkbox' | 'radio';
  selectedValue?: string;
  onSelect?: (value: string) => void;
}

export default function FilterGroup({
  title,
  options,
  selected,
  facetCounts,
  onToggle,
  type,
  selectedValue,
  onSelect,
}: FilterGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="border-b border-gray-200 pb-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full py-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors"
        aria-expanded={isExpanded}
        aria-controls={`filter-group-${title.toLowerCase().replace(/\s+/g, '-')}`}
      >
        <span>{title}</span>
        {isExpanded ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
      </button>

      {isExpanded && (
        <div
          className="space-y-1 mt-1"
          id={`filter-group-${title.toLowerCase().replace(/\s+/g, '-')}`}
          role="group"
          aria-label={`${title} filter options`}
        >
          {options.map(option => {
            const count = facetCounts[option] ?? 0;
            const isSelected = type === 'radio' ? selectedValue === option : selected.includes(option);

            return (
              <label
                key={option}
                className={`flex items-center gap-2 py-1 px-1 rounded cursor-pointer text-sm transition-colors hover:bg-gray-50 ${
                  isSelected ? 'text-cgiar-green font-medium' : 'text-gray-600'
                }`}
              >
                <input
                  type={type}
                  checked={isSelected}
                  onChange={() => {
                    if (type === 'radio' && onSelect) {
                      onSelect(selectedValue === option ? '' : option);
                    } else {
                      onToggle(option);
                    }
                  }}
                  className="w-3.5 h-3.5 text-cgiar-accent focus:ring-cgiar-accent/50 border-gray-300 rounded"
                />
                <span className="flex-1 truncate">{option}</span>
                <span className="text-xs text-gray-600 flex-shrink-0">{count}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
