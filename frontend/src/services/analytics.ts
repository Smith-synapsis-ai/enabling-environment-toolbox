// ---------------------------------------------------------------------------
// Analytics API client — admin dashboard endpoints
// ---------------------------------------------------------------------------

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function getAdminToken(): string {
  const token = localStorage.getItem('admin-token');
  if (!token) throw new Error('Not authenticated');
  return token;
}

async function adminRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAdminToken()}`,
    ...((options?.headers as Record<string, string>) || {}),
  };
  const fullUrl = `${API_BASE}${url}`;
  const response = await fetch(fullUrl, { ...options, headers });
  if (response.status === 401) {
    localStorage.removeItem('admin-token');
    window.location.reload();
    throw new Error('Session expired');
  }
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`API error ${response.status}: ${errorText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface OverviewData {
  period_days: number;
  total_users: number;
  active_users: number;
  total_searches: number;
  total_views: number;
  total_ratings: number;
  total_emails: number;
  total_chats: number;
  total_tools: number;
}

export interface TimeseriesPoint {
  date: string;
  value: number;
}

export interface TimeseriesData {
  period_days: number;
  granularity: string;
  metric: string;
  data: TimeseriesPoint[];
}

export interface TopTool {
  tool_id: string;
  title: string;
  views: number;
  ratings_count: number;
  avg_rating: number;
  searches: number;
}

export interface TopToolsData {
  period_days: number;
  sort_by: string;
  tools: TopTool[];
}

export interface SearchTerm {
  query_text: string;
  count: number;
  avg_results: number;
}

export interface SearchTermsData {
  period_days: number;
  terms: SearchTerm[];
}

export interface GeographyEntry {
  geography: string;
  tool_count: number;
  view_count: number;
}

export interface GeographyData {
  period_days: number;
  geographies: GeographyEntry[];
}

export interface FunnelStage {
  stage: string;
  count: number;
}

export interface EngagementFunnelData {
  period_days: number;
  stages: FunnelStage[];
}

export interface SessionEntry {
  session_id: string;
  started_at: string;
  last_active_at: string;
  user_email: string | null;
  user_type: string | null;
  is_bot: boolean;
  user_agent: string;
  search_count: number;
  view_count: number;
  rating_count: number;
}

export interface SessionsData {
  period_days: number;
  total: number;
  limit: number;
  offset: number;
  sessions: SessionEntry[];
}

export interface PathwayStage {
  stage: string;
  count: number;
  description: string;
}

export interface PathwayCompletionData {
  period_days: number;
  stages: PathwayStage[];
}

export interface MauMonth {
  month: string;
  mau: number;
  mom_growth_pct: number | null;
}

export interface MauGrowthData {
  months: MauMonth[];
}

export interface PulseSurveyScore {
  question_key: string;
  avg_score: number;
  response_count: number;
}

export interface PulseSurveyScoresData {
  period_days: number;
  scores: PulseSurveyScore[];
  overall_avg: number;
}

export interface TrafficSource {
  utm_source: string;
  utm_medium: string;
  session_count: number;
}

export interface TrafficSourcesData {
  period_days: number;
  sources: TrafficSource[];
}

export interface SuggestionUptakeData {
  period_days: number;
  sessions_with_search: number;
  sessions_with_search_then_view: number;
  uptake_pct: number;
}

export interface BrokenLinkTool {
  tool_id: string;
  title: string;
  source_url: string;
}

export interface BrokenLinksData {
  note: string;
  total: number;
  tools: BrokenLinkTool[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function fetchOverview(days: number): Promise<OverviewData> {
  return adminRequest<OverviewData>(
    `/api/admin/analytics/overview?days=${days}`,
  );
}

export async function fetchTimeseries(
  days: number,
  granularity: string,
  metric: string,
): Promise<TimeseriesData> {
  return adminRequest<TimeseriesData>(
    `/api/admin/analytics/timeseries?days=${days}&granularity=${granularity}&metric=${metric}`,
  );
}

export async function fetchTopTools(
  days: number,
  limit?: number,
  sortBy?: string,
): Promise<TopToolsData> {
  const params = new URLSearchParams({ days: String(days) });
  if (limit !== undefined) params.set('limit', String(limit));
  if (sortBy !== undefined) params.set('sort_by', sortBy);
  return adminRequest<TopToolsData>(
    `/api/admin/analytics/top-tools?${params}`,
  );
}

export async function fetchSearchTerms(
  days: number,
  limit?: number,
): Promise<SearchTermsData> {
  const params = new URLSearchParams({ days: String(days) });
  if (limit !== undefined) params.set('limit', String(limit));
  return adminRequest<SearchTermsData>(
    `/api/admin/analytics/search-terms?${params}`,
  );
}

export async function fetchGeography(days: number): Promise<GeographyData> {
  return adminRequest<GeographyData>(
    `/api/admin/analytics/geography?days=${days}`,
  );
}

export async function fetchEngagementFunnel(
  days: number,
): Promise<EngagementFunnelData> {
  return adminRequest<EngagementFunnelData>(
    `/api/admin/analytics/engagement-funnel?days=${days}`,
  );
}

export async function fetchSessions(
  days: number,
  limit?: number,
  offset?: number,
): Promise<SessionsData> {
  const params = new URLSearchParams({ days: String(days) });
  if (limit !== undefined) params.set('limit', String(limit));
  if (offset !== undefined) params.set('offset', String(offset));
  return adminRequest<SessionsData>(
    `/api/admin/analytics/sessions?${params}`,
  );
}

export async function fetchPathwayCompletion(
  days: number,
): Promise<PathwayCompletionData> {
  return adminRequest<PathwayCompletionData>(
    `/api/admin/analytics/pathway-completion?days=${days}`,
  );
}

export async function fetchMauGrowth(): Promise<MauGrowthData> {
  return adminRequest<MauGrowthData>('/api/admin/analytics/mau-growth');
}

export async function fetchPulseSurveyScores(
  days: number,
): Promise<PulseSurveyScoresData> {
  return adminRequest<PulseSurveyScoresData>(
    `/api/admin/analytics/pulse-survey-scores?days=${days}`,
  );
}

export async function fetchTrafficSources(
  days: number,
): Promise<TrafficSourcesData> {
  return adminRequest<TrafficSourcesData>(
    `/api/admin/analytics/traffic-sources?days=${days}`,
  );
}

export async function fetchSuggestionUptake(
  days: number,
): Promise<SuggestionUptakeData> {
  return adminRequest<SuggestionUptakeData>(
    `/api/admin/analytics/suggestion-uptake?days=${days}`,
  );
}

export async function fetchBrokenLinks(): Promise<BrokenLinksData> {
  return adminRequest<BrokenLinksData>('/api/admin/analytics/broken-links');
}

export async function downloadExport(days: number): Promise<void> {
  const token = getAdminToken();
  const fullUrl = `${API_BASE}/api/admin/analytics/export?days=${days}&format=xlsx`;
  const response = await fetch(fullUrl, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    localStorage.removeItem('admin-token');
    window.location.reload();
    throw new Error('Session expired');
  }
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`Export failed: ${errorText}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ee-toolbox-analytics-${days}d.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// C6 Wave A — durable KPI / survey / system-health / token-usage / governance
// ---------------------------------------------------------------------------

async function publicRequest<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`API error ${response.status}: ${errorText}`);
  }
  return response.json();
}

// ---- C4 KPI access events (public, durable Postgres) ----

export interface KpiData {
  kpi_access_events: number;
  kpi_target: number;
  kpi_progress_pct: number;
  counts_by_event: Record<string, number>;
}

export async function fetchKpi(): Promise<KpiData> {
  return publicRequest<KpiData>('/api/events/kpi');
}

// ---- C5 pulse-survey (public, durable Postgres — canonical source) ----

export interface SurveyRecent {
  score: number | null;
  comment: string | null;
  session_id: string | null;
  created_at: string | null;
}

export interface SurveyData {
  total_responses: number;
  average_score: number;
  score_distribution: Record<string, number>;
  recent: SurveyRecent[];
}

export async function fetchSurvey(): Promise<SurveyData> {
  return publicRequest<SurveyData>('/api/events/survey');
}

// ---- System health (admin) ----

export interface SystemHealthData {
  status: string;
  session_store_sqlite: {
    state: string;
    path: string;
    restore_failed: boolean;
    restore_failed_detail: string | null;
  };
  durable_store_postgres: {
    connected: boolean;
    analytics_events?: number;
    token_usage?: number;
    error?: string;
  };
}

export async function fetchSystemHealth(): Promise<SystemHealthData> {
  return adminRequest<SystemHealthData>('/api/admin/system/health');
}

// ---- Token usage (admin) ----

export interface TokenByModel {
  model: string;
  runs: number;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
}

export interface TokenSummary {
  runs: number;
  total_cost_usd: number;
  avg_cost_per_query_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
  total_cache_creation_tokens: number;
  total_turns: number;
  benchmark_low_usd: number;
  benchmark_high_usd: number;
  by_model: TokenByModel[];
}

export async function fetchTokenSummary(): Promise<TokenSummary> {
  return adminRequest<TokenSummary>('/api/admin/token-usage/summary');
}

export interface TokenRow {
  session_id: string | null;
  turn: number | null;
  created_at: string | null;
  orchestrator_model: string | null;
  subagent_model: string | null;
  num_turns: number | null;
  duration_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_tokens: number | null;
  cache_creation_tokens: number | null;
  total_cost_usd: number | null;
  is_error: boolean | null;
}

export interface TokenRecentData {
  rows: TokenRow[];
  limit: number;
}

export async function fetchTokenRecent(limit = 50): Promise<TokenRecentData> {
  return adminRequest<TokenRecentData>(`/api/admin/token-usage/recent?limit=${limit}`);
}

// ---- Governance review queue (admin) ----

export interface Proposal {
  id: string;
  tool_id: string | null;
  proposal_type: string;
  submitted_by: string | null;
  provenance: string | null;
  proposed_fields: Record<string, unknown>;
  status: string;
  reviewer_notes: string | null;
  reviewed_by: string | null;
  submitted_at: string;
  reviewed_at: string | null;
}

export interface ProposalListData {
  total: number;
  proposals: Proposal[];
}

export async function fetchProposals(status?: string): Promise<ProposalListData> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : '';
  return adminRequest<ProposalListData>(`/api/admin/governance/proposals${qs}`);
}

export async function approveProposal(id: string): Promise<unknown> {
  return adminRequest(`/api/admin/governance/proposals/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function rejectProposal(id: string, notes?: string): Promise<unknown> {
  return adminRequest(`/api/admin/governance/proposals/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewer_notes: notes || null }),
  });
}

// ---------------------------------------------------------------------------
// Pulse survey submission (public endpoint — no admin auth)
// ---------------------------------------------------------------------------

export async function submitPulseSurvey(
  sessionId: string,
  questionKey: string,
  score: number,
): Promise<void> {
  const fullUrl = `${API_BASE}/api/pulse-survey`;
  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      question_key: questionKey,
      score,
    }),
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Unknown error');
    throw new Error(`Survey submission failed: ${errorText}`);
  }
}
