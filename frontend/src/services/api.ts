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
} from '../types';

function getSessionId(): string {
  let sessionId = localStorage.getItem('ee-session-id');
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem('ee-session-id', sessionId);
  }
  return sessionId;
}

// API base URL: empty string for local dev (Vite proxy handles /api),
// set VITE_API_BASE_URL for production (e.g., https://api-ee-toolbox.synapsis-analytics.com)
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function getUtmHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const source = sessionStorage.getItem('ee-utm-source');
  const medium = sessionStorage.getItem('ee-utm-medium');
  const campaign = sessionStorage.getItem('ee-utm-campaign');
  if (source) headers['X-UTM-Source'] = source;
  if (medium) headers['X-UTM-Medium'] = medium;
  if (campaign) headers['X-UTM-Campaign'] = campaign;
  return headers;
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Session-ID': getSessionId(),
    ...getUtmHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };

  const fullUrl = `${API_BASE}${url}`;
  const response = await fetch(fullUrl, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json();
}

export async function fetchMetrics(): Promise<Metrics> {
  return request<Metrics>('/api/metrics');
}

export async function sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function searchCatalog(data: CatalogSearchRequest): Promise<CatalogSearchResponse> {
  return request<CatalogSearchResponse>('/api/search/catalog', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function searchSemantic(data: SemanticSearchRequest): Promise<SemanticSearchResponse> {
  return request<SemanticSearchResponse>('/api/search/semantic', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchTool(id: string): Promise<ToolDetail> {
  return request<ToolDetail>(`/api/tools/${id}`);
}

export async function rateTool(id: string, data: RateRequest): Promise<void> {
  await request<unknown>(`/api/tools/${id}/rate`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchRatings(id: string): Promise<RatingsResponse> {
  return request<RatingsResponse>(`/api/tools/${id}/ratings`);
}

// ---------------------------------------------------------------------------
// Admin API
// ---------------------------------------------------------------------------

function getAdminToken(): string | null {
  return localStorage.getItem('admin-token');
}

function adminHeaders(): Record<string, string> {
  const token = getAdminToken();
  if (!token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${token}` };
}

export async function adminLogin(
  username: string,
  password: string
): Promise<{ token: string }> {
  return request<{ token: string }>('/api/admin/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function fetchAdminTools(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  sort_by?: string;
}): Promise<AdminToolsResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  if (params.keyword) query.set('keyword', params.keyword);
  if (params.sort_by) query.set('sort_by', params.sort_by);
  const qs = query.toString();
  return request<AdminToolsResponse>(`/api/admin/tools${qs ? `?${qs}` : ''}`, {
    headers: adminHeaders(),
  });
}

export async function createTool(data: ToolCreate): Promise<ToolDetail> {
  return request<ToolDetail>('/api/admin/tools', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: adminHeaders(),
  });
}

export async function updateTool(
  id: string,
  data: Partial<ToolCreate>
): Promise<ToolDetail> {
  return request<ToolDetail>(`/api/admin/tools/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: adminHeaders(),
  });
}

export async function deleteTool(id: string): Promise<void> {
  await request<unknown>(`/api/admin/tools/${id}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  });
}

// ---------------------------------------------------------------------------
// Email Capture
// ---------------------------------------------------------------------------

export async function captureEmail(email: string, sessionId: string): Promise<void> {
  await request<unknown>('/api/email-capture', {
    method: 'POST',
    body: JSON.stringify({ email, session_id: sessionId }),
  });
}

// ---------------------------------------------------------------------------
// Tool Save / Bookmark
// ---------------------------------------------------------------------------

export async function saveTool(toolId: string): Promise<void> {
  await request<unknown>(`/api/tools/${toolId}/save`, { method: 'POST' });
}

export async function unsaveTool(toolId: string): Promise<void> {
  await request<unknown>(`/api/tools/${toolId}/save`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Exported helpers
// ---------------------------------------------------------------------------

export { getSessionId };
