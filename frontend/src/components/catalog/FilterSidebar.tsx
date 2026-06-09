import { Search, XCircle } from 'lucide-react';
import FilterGroup from './FilterGroup';
import type { Facets } from '../../types';
import { PILLARS, DOMAINS, TYPES, STAGES, TARGET_USERS, GEOGRAPHIES } from '../../types';

interface Filters {
  pillars: string[];
  domains: string[];
  type: string;
  stage: string;
  target_users: string[];
  geography: string[];
  keyword: string;
}

interface FilterSidebarProps {
  filters: Filters;
  facets: Facets;
  onToggleArray: (key: 'pillars' | 'domains' | 'target_users' | 'geography', value: string) => void;
  onUpdateFilter: (key: keyof Filters, value: string | string[]) => void;
  onClear: () => void;
}

export default function FilterSidebar({
  filters,
  facets,
  onToggleArray,
  onUpdateFilter,
  onClear,
}: FilterSidebarProps) {
  const hasActiveFilters = filters.pillars.length > 0 ||
    filters.domains.length > 0 ||
    filters.type !== '' ||
    filters.stage !== '' ||
    filters.target_users.length > 0 ||
    filters.geography.length > 0 ||
    filters.keyword !== '';

  return (
    <aside className="w-full lg:w-64 flex-shrink-0" aria-label="Filter tools">
      {/* Keyword search */}
      <div className="mb-4">
        <label htmlFor="catalog-search" className="sr-only">Search tools by keyword</label>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" aria-hidden="true" />
          <input
            id="catalog-search"
            type="text"
            value={filters.keyword}
            onChange={(e) => onUpdateFilter('keyword', e.target.value)}
            placeholder="Search tools..."
            className="w-full pl-9 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cgiar-accent/30 focus:border-cgiar-accent transition-colors"
          />
        </div>
      </div>

      {/* Clear filters */}
      {hasActiveFilters && (
        <button
          onClick={onClear}
          className="flex items-center gap-1.5 text-sm text-cgiar-green hover:text-cgiar-dark mb-4 font-medium transition-colors"
        >
          <XCircle size={14} />
          Clear all filters
        </button>
      )}

      {/* Filter groups */}
      <div className="space-y-1">
        <FilterGroup
          title="Pillars"
          options={PILLARS}
          selected={filters.pillars}
          facetCounts={facets.pillars}
          onToggle={(v) => onToggleArray('pillars', v)}
          type="checkbox"
        />
        <FilterGroup
          title="Domains"
          options={DOMAINS}
          selected={filters.domains}
          facetCounts={facets.domains}
          onToggle={(v) => onToggleArray('domains', v)}
          type="checkbox"
        />
        <FilterGroup
          title="Type"
          options={TYPES}
          selected={[]}
          facetCounts={facets.type}
          onToggle={() => {}}
          type="radio"
          selectedValue={filters.type}
          onSelect={(v) => onUpdateFilter('type', v)}
        />
        <FilterGroup
          title="Stage"
          options={STAGES}
          selected={[]}
          facetCounts={facets.stage}
          onToggle={() => {}}
          type="radio"
          selectedValue={filters.stage}
          onSelect={(v) => onUpdateFilter('stage', v)}
        />
        <FilterGroup
          title="Target Users"
          options={TARGET_USERS}
          selected={filters.target_users}
          facetCounts={facets.target_users}
          onToggle={(v) => onToggleArray('target_users', v)}
          type="checkbox"
        />
        <FilterGroup
          title="Geography"
          options={GEOGRAPHIES}
          selected={filters.geography}
          facetCounts={facets.geography}
          onToggle={(v) => onToggleArray('geography', v)}
          type="checkbox"
        />
      </div>
    </aside>
  );
}
