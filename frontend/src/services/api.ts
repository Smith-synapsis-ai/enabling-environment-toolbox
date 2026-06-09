import type {
  Metrics,
  ChatRequest,
  ChatResponse,
  CatalogSearchRequest,
  CatalogSearchResponse,
  SemanticSearchRequest,
  SemanticSearchResponse,
  ToolDetail,
  RateRequest,
  RatingsResponse,
  AdminToolsResponse,
  ToolCreate,
  Facets,
  WikiToolDetail,
} from '../types';
import { tools, getToolById, getAllTools } from '../data/tools';

// ---------------------------------------------------------------------------
// Session helper (still used by other parts of the app)
// ---------------------------------------------------------------------------

function getSessionId(): string {
  let sessionId = localStorage.getItem('ee-session-id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem('ee-session-id', sessionId);
  }
  return sessionId;
}

// ---------------------------------------------------------------------------
// Helper: compute facet counts from a filtered set of tools
// ---------------------------------------------------------------------------

function computeFacets(filtered: WikiToolDetail[]): Facets {
  const facets: Facets = {
    pillars: {},
    domains: {},
    type: {},
    stage: {},
    target_users: {},
    geography: {},
  };

  for (const tool of filtered) {
    // Pillars
    for (const p of tool.pillars) {
      facets.pillars[p] = (facets.pillars[p] || 0) + 1;
    }
    // Domains
    for (const d of tool.domains) {
      facets.domains[d] = (facets.domains[d] || 0) + 1;
    }
    // Type
    if (tool.type) {
      facets.type[tool.type] = (facets.type[tool.type] || 0) + 1;
    }
    // Stage
    if (tool.stage) {
      facets.stage[tool.stage] = (facets.stage[tool.stage] || 0) + 1;
    }
    // Target users
    for (const u of tool.target_users) {
      facets.target_users[u] = (facets.target_users[u] || 0) + 1;
    }
    // Geography
    for (const g of tool.geography) {
      facets.geography[g] = (facets.geography[g] || 0) + 1;
    }
  }

  return facets;
}

// ---------------------------------------------------------------------------
// Helper: simple keyword matching
// ---------------------------------------------------------------------------

function matchesKeyword(tool: WikiToolDetail, keyword: string): boolean {
  const lower = keyword.toLowerCase();
  return (
    tool.title.toLowerCase().includes(lower) ||
    tool.summary.toLowerCase().includes(lower) ||
    tool.what_it_does.toLowerCase().includes(lower) ||
    tool.who_its_for.toLowerCase().includes(lower) ||
    tool.when_to_use_it.toLowerCase().includes(lower)
  );
}

// ---------------------------------------------------------------------------
// Public API — same function signatures as before
// ---------------------------------------------------------------------------

export async function fetchMetrics(): Promise<Metrics> {
  const allTools = getAllTools();
  const uniqueCountries = new Set<string>();
  let frameworkCount = 0;

  for (const tool of allTools) {
    for (const g of tool.geography) {
      uniqueCountries.add(g);
    }
    if (
      tool.type === 'Framework' ||
      tool.pillars.length > 0
    ) {
      frameworkCount++;
    }
  }

  return {
    total_tools: allTools.length,
    total_frameworks: frameworkCount,
    geography_coverage: uniqueCountries.size,
    total_searches: 0,
    avg_rating: 0,
  };
}

export async function sendChatMessage(_data: ChatRequest): Promise<ChatResponse> {
  return {
    conversation_id: crypto.randomUUID(),
    message:
      'The AI chat assistant is not yet connected in this version. ' +
      'Please use the catalog search to browse and filter tools, or try the semantic search.',
    tools_recommended: null,
    conversation_complete: false,
  };
}

export async function searchCatalog(data: CatalogSearchRequest): Promise<CatalogSearchResponse> {
  let filtered = [...getAllTools()] as WikiToolDetail[];

  // Apply filters
  if (data.pillars && data.pillars.length > 0) {
    filtered = filtered.filter(t =>
      data.pillars!.some(p => t.pillars.includes(p))
    );
  }
  if (data.domains && data.domains.length > 0) {
    filtered = filtered.filter(t =>
      data.domains!.some(d => t.domains.includes(d))
    );
  }
  if (data.type) {
    filtered = filtered.filter(t => t.type === data.type);
  }
  if (data.stage) {
    filtered = filtered.filter(t => t.stage === data.stage);
  }
  if (data.target_users && data.target_users.length > 0) {
    filtered = filtered.filter(t =>
      data.target_users!.some(u => t.target_users.includes(u))
    );
  }
  if (data.geography && data.geography.length > 0) {
    filtered = filtered.filter(t =>
      data.geography!.some(g => t.geography.includes(g))
    );
  }
  if (data.keyword) {
    filtered = filtered.filter(t => matchesKeyword(t, data.keyword!));
  }

  // Compute facets from filtered results
  const facets = computeFacets(filtered);

  // Sort
  const sortBy = data.sort_by || 'relevance';
  if (sortBy === 'date') {
    filtered.sort((a, b) => {
      const da = a.date_published || '';
      const db = b.date_published || '';
      return db.localeCompare(da);
    });
  } else if (sortBy === 'rating') {
    filtered.sort((a, b) => b.average_rating - a.average_rating);
  }
  // 'relevance' keeps original order (or keyword match order)

  // Paginate
  const page = data.page || 1;
  const pageSize = data.page_size || 12;
  const start = (page - 1) * pageSize;
  const paged = filtered.slice(start, start + pageSize);

  return {
    total: filtered.length,
    page,
    page_size: pageSize,
    results: paged,
    facets,
  };
}

export async function searchSemantic(data: SemanticSearchRequest): Promise<SemanticSearchResponse> {
  const query = data.query.toLowerCase();
  const topN = data.top_n || 10;
  const allTools = getAllTools();

  // Simple keyword-based relevance scoring
  const scored = allTools
    .map(tool => {
      let score = 0;
      const fields = [tool.title, tool.summary, tool.what_it_does, tool.who_its_for, tool.when_to_use_it];
      for (const field of fields) {
        if (field.toLowerCase().includes(query)) {
          score += 1;
        }
      }
      // Boost title matches
      if (tool.title.toLowerCase().includes(query)) {
        score += 2;
      }
      return { tool: { ...tool, similarity: score / 5 }, score };
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topN);

  return {
    query: data.query,
    total_results: scored.length,
    results: scored.map(s => s.tool),
  };
}

export async function fetchTool(id: string): Promise<ToolDetail> {
  const tool = getToolById(id);
  if (!tool) {
    throw new Error(`Tool not found: ${id}`);
  }
  return tool;
}

export async function rateTool(_id: string, _data: RateRequest): Promise<void> {
  // No-op in static mode — rating is not persisted
}

export async function fetchRatings(id: string): Promise<RatingsResponse> {
  return {
    tool_id: id,
    average: 0,
    count: 0,
    distribution: { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0 },
  };
}

// ---------------------------------------------------------------------------
// Admin API — stubs (no backend in static mode)
// ---------------------------------------------------------------------------

export async function adminLogin(
  _username: string,
  _password: string
): Promise<{ token: string }> {
  throw new Error('Admin login is not available in static mode');
}

export async function fetchAdminTools(_params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  sort_by?: string;
}): Promise<AdminToolsResponse> {
  return {
    total: tools.length,
    page: 1,
    page_size: 20,
    tools: tools.slice(0, 20),
  };
}

export async function createTool(_data: ToolCreate): Promise<ToolDetail> {
  throw new Error('Tool creation is not available in static mode');
}

export async function updateTool(
  _id: string,
  _data: Partial<ToolCreate>
): Promise<ToolDetail> {
  throw new Error('Tool update is not available in static mode');
}

export async function deleteTool(_id: string): Promise<void> {
  throw new Error('Tool deletion is not available in static mode');
}

// ---------------------------------------------------------------------------
// Email Capture — no-op in static mode
// ---------------------------------------------------------------------------

export async function captureEmail(_email: string, _sessionId: string): Promise<void> {
  // No-op
}

// ---------------------------------------------------------------------------
// Tool Save / Bookmark — local-only in static mode
// ---------------------------------------------------------------------------

export async function saveTool(_toolId: string): Promise<void> {
  // No-op — save state is handled by localStorage in the component
}

export async function unsaveTool(_toolId: string): Promise<void> {
  // No-op — save state is handled by localStorage in the component
}

// ---------------------------------------------------------------------------
// Exported helpers
// ---------------------------------------------------------------------------

export { getSessionId };
