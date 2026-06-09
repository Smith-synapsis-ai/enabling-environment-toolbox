import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { CatalogSearchRequest, CatalogSearchResponse, Facets, ToolSearchResult } from '../types';
import { searchCatalog } from '../services/api';

interface Filters {
  pillars: string[];
  domains: string[];
  type: string;
  stage: string;
  target_users: string[];
  geography: string[];
  keyword: string;
}

const emptyFilters: Filters = {
  pillars: [],
  domains: [],
  type: '',
  stage: '',
  target_users: [],
  geography: [],
  keyword: '',
};

const emptyFacets: Facets = {
  pillars: {},
  domains: {},
  type: {},
  stage: {},
  target_users: {},
  geography: {},
};

interface CatalogState {
  filters: Filters;
  results: ToolSearchResult[];
  facets: Facets;
  total: number;
  page: number;
  pageSize: number;
  sortBy: 'relevance' | 'date' | 'rating';
  loading: boolean;
  error: string | null;
  initialized: boolean; // true after first successful fetch
  setPage: (page: number) => void;
  updateFilter: (key: keyof Filters, value: string | string[]) => void;
  toggleArrayFilter: (key: 'pillars' | 'domains' | 'target_users' | 'geography', value: string) => void;
  clearFilters: () => void;
  updateSort: (sort: 'relevance' | 'date' | 'rating') => void;
}

const CatalogContext = createContext<CatalogState | null>(null);

export function CatalogProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [results, setResults] = useState<ToolSearchResult[]>([]);
  const [facets, setFacets] = useState<Facets>(emptyFacets);
  const [total, setTotal] = useState(0);
  const [page, setPageState] = useState(1);
  const [pageSize] = useState(12);
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'rating'>('relevance');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Cache: store results keyed by serialized request
  const cache = useRef<Map<string, CatalogSearchResponse>>(new Map());

  const search = useCallback(async (
    currentFilters: Filters,
    currentPage: number,
    currentSort: 'relevance' | 'date' | 'rating'
  ) => {
    const request: CatalogSearchRequest = {
      page: currentPage,
      page_size: pageSize,
      sort_by: currentSort,
    };

    if (currentFilters.pillars.length > 0) request.pillars = currentFilters.pillars;
    if (currentFilters.domains.length > 0) request.domains = currentFilters.domains;
    if (currentFilters.type) request.type = currentFilters.type;
    if (currentFilters.stage) request.stage = currentFilters.stage;
    if (currentFilters.target_users.length > 0) request.target_users = currentFilters.target_users;
    if (currentFilters.geography.length > 0) request.geography = currentFilters.geography;
    if (currentFilters.keyword) request.keyword = currentFilters.keyword;

    const cacheKey = JSON.stringify(request);

    // Check cache first
    if (cache.current.has(cacheKey)) {
      const cached = cache.current.get(cacheKey)!;
      setResults(cached.results);
      setFacets(cached.facets);
      setTotal(cached.total);
      setInitialized(true);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await searchCatalog(request);
      cache.current.set(cacheKey, response);
      setResults(response.results);
      setFacets(response.facets);
      setTotal(response.total);
      setInitialized(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    search(filters, page, sortBy);
  }, [filters, page, sortBy, search]);

  const setPage = useCallback((p: number) => setPageState(p), []);

  const updateFilter = useCallback((key: keyof Filters, value: string | string[]) => {
    setPageState(1);
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const toggleArrayFilter = useCallback((key: 'pillars' | 'domains' | 'target_users' | 'geography', value: string) => {
    setPageState(1);
    setFilters(prev => {
      const arr = prev[key];
      const next = arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value];
      return { ...prev, [key]: next };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setPageState(1);
    setFilters(emptyFilters);
  }, []);

  const updateSort = useCallback((sort: 'relevance' | 'date' | 'rating') => {
    setPageState(1);
    setSortBy(sort);
  }, []);

  return (
    <CatalogContext.Provider value={{
      filters, results, facets, total, page, pageSize, sortBy,
      loading, error, initialized,
      setPage, updateFilter, toggleArrayFilter, clearFilters, updateSort,
    }}>
      {children}
    </CatalogContext.Provider>
  );
}

export function useCatalogContext() {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalogContext must be used within CatalogProvider');
  return ctx;
}
