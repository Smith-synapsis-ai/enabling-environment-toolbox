import { useState, useCallback, useEffect } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import FilterSidebar from './FilterSidebar';
import CatalogResults from './CatalogResults';
import Pagination from './Pagination';
import LoadingSpinner from '../common/LoadingSpinner';
import ToolDetailPanel from '../tool/ToolDetailPanel';
import { useCatalogSearch } from '../../hooks/useCatalogSearch';
import type { ToolSearchResult } from '../../types';

interface CatalogPageProps {
  onToolViewed?: () => void;
}

export default function CatalogPage({ onToolViewed }: CatalogPageProps) {
  const {
    filters,
    results,
    facets,
    total,
    page,
    pageSize,
    sortBy,
    loading,
    error,
    setPage,
    updateFilter,
    toggleArrayFilter,
    clearFilters,
    updateSort,
  } = useCatalogSearch();

  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // On mount: read ?q= query param and pre-fill keyword filter (for tool deep-links from chat)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const qParam = params.get('q');
    if (qParam) {
      updateFilter('keyword', qParam);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToolClick = useCallback((tool: ToolSearchResult) => {
    setSelectedToolId(tool.id);
  }, []);

  return (
    <div className="min-h-screen bg-cgiar-light pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Search by Catalog</h1>
          <p className="text-sm text-gray-500 mt-1">
            Browse and filter the complete collection of enabling environment tools.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Mobile filter toggle */}
          <button
            onClick={() => setMobileFiltersOpen(!mobileFiltersOpen)}
            className="lg:hidden flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700"
            aria-expanded={mobileFiltersOpen}
            aria-controls="filter-sidebar"
          >
            {mobileFiltersOpen ? <X size={16} /> : <SlidersHorizontal size={16} />}
            {mobileFiltersOpen ? 'Hide Filters' : 'Show Filters'}
          </button>

          {/* Sidebar */}
          <div id="filter-sidebar" className={`${mobileFiltersOpen ? 'block' : 'hidden'} lg:block`}>
            <FilterSidebar
              filters={filters}
              facets={facets}
              onToggleArray={toggleArrayFilter}
              onUpdateFilter={updateFilter}
              onClear={clearFilters}
            />
          </div>

          {/* Results area */}
          <div className="flex-1 min-w-0">
            {/* Results header */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500" aria-live="polite" aria-atomic="true">
                {loading ? 'Searching...' : `${total} tool${total !== 1 ? 's' : ''} found`}
              </p>
              <select
                value={sortBy}
                onChange={(e) => updateSort(e.target.value as 'relevance' | 'date' | 'rating')}
                className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-cgiar-accent/30 text-gray-600"
                aria-label="Sort tools by"
              >
                <option value="relevance">Sort by Relevance</option>
                <option value="date">Sort by Date</option>
                <option value="rating">Sort by Rating</option>
              </select>
            </div>

            {/* Loading state */}
            {loading && (
              <div className="flex justify-center py-16">
                <LoadingSpinner size={32} message="Loading tools..." />
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 mb-4">
                {error}
              </div>
            )}

            {/* Results grid */}
            {!loading && !error && (
              <>
                <CatalogResults results={results} onToolClick={handleToolClick} />
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={total}
                  onPageChange={setPage}
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Tool detail panel */}
      {selectedToolId && (
        <ToolDetailPanel
          toolId={selectedToolId}
          onClose={() => setSelectedToolId(null)}
          onToolViewed={onToolViewed}
        />
      )}
    </div>
  );
}
