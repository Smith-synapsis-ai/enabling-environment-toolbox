export interface Metrics {
  total_tools: number;
  total_frameworks: number;
  geography_coverage: number;
  total_searches: number;
  avg_rating: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ToolRecommendation {
  id: string;
  title: string;
  explanation: string;
  similarity: number;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  tools_recommended: ToolRecommendation[] | null;
  conversation_complete: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tools_recommended?: ToolRecommendation[] | null;
}

export interface ToolSearchResult {
  id: string;
  cgspace_id: string | null;
  title: string;
  summary: string;
  what_it_does: string;
  when_to_use_it: string;
  who_its_for: string;
  pillars: string[];
  domains: string[];
  type: string;
  stage: string;
  target_users: string[];
  geography: string[];
  source_url: string;
  cover_image_url: string | null;
  average_rating: number;
  rating_count: number;
  similarity: number;
}

export interface ToolDetail extends ToolSearchResult {
  authors: string[];
  date_published: string;
  source_organization: string;
  cgspace_id: string;
  relevance_score: number | null;
  is_visible: boolean;
  view_count: number;
  created_at: string;
  updated_at: string;
}

export interface WikiToolDetail extends ToolDetail {
  how_it_works_steps: string[] | null;
  how_it_works_duration: string | null;
  how_it_works_inputs: string | null;
  requirements_technical: string | null;
  requirements_human: string | null;
  requirements_institutional: string | null;
  expected_direct_outputs: string | null;
  expected_impact: string | null;
  expected_evidence: string | null;
  practical_examples: Array<{ location: string; description: string; key_result: string }>;
  limitations: string;
  key_takeaways: string[];
  full_citation: string;
  content_richness: string;
  extraction_confidence: string;
}

export interface CatalogSearchRequest {
  pillars?: string[];
  domains?: string[];
  type?: string;
  stage?: string;
  target_users?: string[];
  geography?: string[];
  keyword?: string;
  page?: number;
  page_size?: number;
  sort_by?: 'relevance' | 'date' | 'rating';
}

export interface FacetCounts {
  [key: string]: number;
}

export interface Facets {
  pillars: FacetCounts;
  domains: FacetCounts;
  type: FacetCounts;
  stage: FacetCounts;
  target_users: FacetCounts;
  geography: FacetCounts;
}

export interface CatalogSearchResponse {
  total: number;
  page: number;
  page_size: number;
  results: ToolSearchResult[];
  facets: Facets;
}

export interface SemanticSearchRequest {
  query: string;
  top_n?: number;
  min_similarity?: number;
}

export interface SemanticSearchResponse {
  query: string;
  total_results: number;
  results: ToolSearchResult[];
}

export interface RateRequest {
  rating: number;
  user_id: string;
}

export interface RatingDistribution {
  '1': number;
  '2': number;
  '3': number;
  '4': number;
  '5': number;
}

export interface RatingsResponse {
  tool_id: string;
  average: number;
  count: number;
  distribution: RatingDistribution;
}

export interface AdminToolsResponse {
  total: number;
  page: number;
  page_size: number;
  tools: ToolDetail[];
}

export interface ToolCreate {
  title: string;
  summary?: string;
  what_it_does?: string;
  when_to_use_it?: string;
  who_its_for?: string;
  pillars?: string[];
  domains?: string[];
  type?: string;
  stage?: string;
  target_users?: string[];
  geography?: string[];
  authors?: string[];
  date_published?: string;
  source_url?: string;
  source_organization?: string;
  cover_image_url?: string;
  cgspace_id?: string;
  relevance_score?: number | null;
  is_visible?: boolean;
}

export const TYPE_COLORS: Record<string, string> = {
  'Method': '#1565C0',
  'Framework': '#2E7D32',
  'Manual': '#C24400',
  'Toolkit': '#7B1FA2',
  'Tool': '#00695C',
  'Guide': '#5D4037',
  'Matrix': '#455A64',
  'Scorecard': '#C62828',
  'Brief': '#F57F17',
  'Scale': '#AD1457',
  'Academic Paper': '#1565C0',
  'Report': '#0D47A1',
  'Training Manual': '#C24400',
  'Case Study': '#6A1B9A',
  'Guidelines': '#00838F',
  'Presentation': '#BF360C',
  'Program Description': '#33691E',
  'Policy Brief': '#F57F17',
  'Other': '#566875',
};

/** Returns true if the TYPE_COLOR for this type needs dark text instead of white for WCAG AA contrast */
export function typeBadgeNeedsDarkText(type: string): boolean {
  // The amber/yellow badges (#F57F17) are too light for white text (only ~2.65:1);
  // they use dark text instead to clear WCAG AA's 4.5:1 for small text.
  return type === 'Brief' || type === 'Policy Brief';
}

export const PILLARS = [
  'Policy & Regulatory',
  'Gender Equality & Social Inclusion',
  'Market Systems',
  'Digital',
  'Financial Services',
  'M&E & Learning',
  'Climate Resilience',
  'Scaling Innovations',
];

export const DOMAINS = [
  'Agri-food Systems',
  'Scaling Innovation',
  'Climate Resilience',
];

export const TYPES = [
  'Academic Paper', 'Report', 'Training Manual', 'Framework',
  'Case Study', 'Guidelines', 'Tool', 'Presentation',
  'Program Description', 'Policy Brief', 'Other',
  'Method', 'Manual', 'Toolkit', 'Guide', 'Matrix',
  'Scorecard', 'Brief', 'Scale',
];

export const STAGES = [
  'Established and field-tested',
  'Prototype',
  'Theoretical and diagnostics',
  'Conceptual',
];

export const TARGET_USERS = [
  'Researcher',
  'Policymaker',
  'Development Practitioner',
  'Extension services',
  'Agribusiness',
  'Local communities',
  'Civil Society and INGOs',
  'Funders and Donors',
  'Private sector entities',
  'Government agencies',
  'Humanitarian assistance practitioners',
  'Project and program managers',
  'Farmers and Agro-pastoralists',
  'Monitoring and Evaluation specialists',
  'Community leaders',
  'Irrigation scheme managers',
];

export const GEOGRAPHIES = [
  'Global',
  'Asia',
  'Africa',
  'MENA',
  'Latin America',
  'Europe',
  'Low-income and middle-income countries',
  'Central and West Asia and North Africa (CWANA)',
];
