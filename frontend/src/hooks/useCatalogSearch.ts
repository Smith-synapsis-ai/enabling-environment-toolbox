import { useState, useCallback, useEffect } from 'react';
import type {
  CatalogSearchRequest,
  CatalogSearchResponse,
  Facets,
  ToolSearchResult,
} from '../types';
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

export function useCatalogSearch() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [results, setResults] = useState<ToolSearchResult[]>([]);
  const [facets, setFacets] = useState<Facets>(emptyFacets);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'rating'>('relevance');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (
    currentFilters: Filters,
    currentPage: number,
    currentSort: 'relevance' | 'date' | 'rating'
  ) => {
    setLoading(true);
    setError(null);

    try {
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

      const response: CatalogSearchResponse = await searchCatalog(request);

      setResults(response.results);
      setFacets(response.facets);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    search(filters, page, sortBy);
  }, [filters, page, sortBy, search]);

  const updateFilter = useCallback((key: keyof Filters, value: string | string[]) => {
    setPage(1);
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const toggleArrayFilter = useCallback((key: 'pillars' | 'domains' | 'target_users' | 'geography', value: string) => {
    setPage(1);
    setFilters(prev => {
      const arr = prev[key];
      const next = arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value];
      return { ...prev, [key]: next };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setPage(1);
    setFilters(emptyFilters);
  }, []);

  const updateSort = useCallback((sort: 'relevance' | 'date' | 'rating') => {
    setPage(1);
    setSortBy(sort);
  }, []);

  return {
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
  };
}
