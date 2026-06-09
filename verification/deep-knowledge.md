# Enabling Environment Toolbox - Deep Technical Knowledge

Comprehensive architectural and technical documentation extracted from source code.
Generated: 2026-05-26

---

## 1. Database Schema

Database: PostgreSQL 16 with pgvector extension. Database name: `ee_toolbox`.

### 1.1 Table: `tools` (Primary entity)

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| title | Text | NOT NULL | - | Required |
| summary | Text | NULL | - | LLM-generated summary |
| what_it_does | Text | NULL | - | LLM-generated description |
| when_to_use_it | Text | NULL | - | LLM-generated usage guidance |
| who_its_for | Text | NULL | - | LLM-generated audience description |
| pillars | Text[] (ARRAY) | NULL | - | Multi-value taxonomy |
| domains | Text[] (ARRAY) | NULL | - | Multi-value taxonomy |
| type | Text | NULL | - | Single-value taxonomy |
| stage | Text | NULL | - | Single-value taxonomy |
| target_users | Text[] (ARRAY) | NULL | - | Multi-value taxonomy |
| geography | Text[] (ARRAY) | NULL | - | Multi-value taxonomy |
| authors | Text[] (ARRAY) | NULL | - | Parsed from source metadata |
| date_published | Date | NULL | - | Supports YYYY, YYYY-MM, YYYY-MM-DD |
| source_url | Text | NULL | - | Original document URL |
| source_organization | Text | NULL | - | Publishing organization |
| cover_image_url | Text | NULL | - | Tool cover image URL |
| embedding | vector(1536) | NULL | - | OpenAI text-embedding-3-small |
| average_rating | Numeric(3,2) | NOT NULL | 0 | Computed from user_ratings |
| rating_count | Integer | NOT NULL | 0 | Count of ratings |
| view_count | Integer | NOT NULL | 0 | Page view counter |
| cgspace_id | Text | NULL (UNIQUE) | - | Deduplication key |
| relevance_score | Numeric(3,2) | NULL | - | Classifier confidence |
| is_visible | Boolean | NOT NULL | true | Soft-delete / hide flag |
| created_at | Timestamp w/tz | NOT NULL | now() | Auto-set |
| updated_at | Timestamp w/tz | NOT NULL | now() | Auto-updated via ORM onupdate |

**Indexes on `tools`:**

| Index Name | Type | Columns / Expression | Notes |
|------------|------|---------------------|-------|
| ix_tools_pillars | GIN | pillars | Array overlap queries |
| ix_tools_domains | GIN | domains | Array overlap queries |
| ix_tools_target_users | GIN | target_users | Array overlap queries |
| ix_tools_geography | GIN | geography | Array overlap queries |
| ix_tools_type | B-tree | type | Equality filtering |
| ix_tools_stage | B-tree | stage | Equality filtering |
| ix_tools_embedding | HNSW | embedding vector_cosine_ops | m=16, ef_construction=64 |
| ix_tools_fulltext | GIN | to_tsvector('english', coalesce(title,'') \|\| ' ' \|\| coalesce(summary,'')) | Full-text keyword search |

**Vector Embedding Details:**
- Column type: `vector(1536)` from pgvector extension
- Dimensions: 1536
- Model: OpenAI `text-embedding-3-small`
- Index: HNSW with cosine distance operator (`vector_cosine_ops`)
- HNSW parameters: m=16, ef_construction=64
- Distance operator used in queries: `<=>` (cosine distance)
- Similarity formula: `1 - (embedding <=> query_vector)`

### 1.2 Table: `user_ratings`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| tool_id | UUID | NOT NULL | - | FK -> tools.id |
| user_identifier | Text | NOT NULL | - | Email or session-based ID |
| rating | SmallInteger | NOT NULL | - | CHECK: 1-5 |
| created_at | Timestamp w/tz | NOT NULL | now() | |
| updated_at | Timestamp w/tz | NOT NULL | now() | |

**Constraints:**
- UNIQUE(tool_id, user_identifier) -- named `uq_rating_tool_user` -- enables upsert
- CHECK(rating >= 1 AND rating <= 5) -- named `ck_rating_range`

### 1.3 Table: `search_logs`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| session_id | Text | NULL | - | From X-Session-ID header |
| query_text | Text | NULL | - | User's search query |
| query_type | Text | NULL | - | "semantic", "faceted", or "chat" |
| filters_used | JSONB | NULL | - | Filters applied (catalog only) |
| results_count | Integer | NULL | - | Number of results returned |
| results_tool_ids | UUID[] (ARRAY) | NULL | - | IDs of returned tools |
| created_at | Timestamp w/tz | NOT NULL | now() | |

### 1.4 Table: `tool_views`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| tool_id | UUID | NOT NULL | - | FK -> tools.id |
| session_id | Text | NULL | - | From X-Session-ID header |
| referrer | Text | NULL | - | "chat", "catalog", or "direct" |
| created_at | Timestamp w/tz | NOT NULL | now() | |

### 1.5 Table: `user_sessions`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| session_id | Text | NOT NULL (UNIQUE) | - | Client-generated UUID |
| user_email | Text | NULL | - | From email capture |
| started_at | Timestamp w/tz | NOT NULL | now() | |
| last_active_at | Timestamp w/tz | NOT NULL | now() | |
| user_agent | Text | NULL | - | Browser user-agent |
| ip_address | Text | NULL | - | Client IP |

### 1.6 Table: `email_captures`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| email | Text | NOT NULL (UNIQUE) | - | Captured email address |
| created_at | Timestamp w/tz | NOT NULL | now() | |

### 1.7 Table: `prompt_versions`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| prompt_name | Text | NOT NULL | - | e.g. "chat_system", "relevance_classification", "metadata_extraction" |
| version | Integer | NOT NULL | - | Auto-incremented per prompt_name |
| prompt_text | Text | NOT NULL | - | Full prompt template |
| model | Text | NULL | - | Target LLM model |
| is_active | Boolean | NOT NULL | false | Only one active per prompt_name |
| notes | Text | NULL | - | Change notes |
| created_at | Timestamp w/tz | NOT NULL | now() | |
| created_by | Text | NULL | - | Author identifier |

**Constraints:**
- UNIQUE(prompt_name, version) -- named `uq_prompt_name_version`
- Partial unique index: `ix_prompt_active_unique ON prompt_versions (prompt_name) WHERE is_active = true` -- enforces one active prompt per name

### 1.8 Table: `prompt_eval_results`

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | UUID | NOT NULL | gen_random_uuid() | Primary key |
| prompt_version_id | UUID | NOT NULL | - | FK -> prompt_versions.id |
| input_data | JSONB | NULL | - | Test input |
| output_data | JSONB | NULL | - | LLM output |
| expected_output | JSONB | NULL | - | Ground truth |
| is_correct | Boolean | NULL | - | Pass/fail |
| score | Numeric(5,4) | NULL | - | Quality score |
| latency_ms | Integer | NULL | - | Response time |
| model_used | Text | NULL | - | Actual model used |
| tokens_input | Integer | NULL | - | Input token count |
| tokens_output | Integer | NULL | - | Output token count |
| cost_usd | Numeric(10,6) | NULL | - | Estimated cost |
| notes | Text | NULL | - | |
| evaluated_at | Timestamp w/tz | NULL | - | |
| evaluated_by | Text | NULL | - | |

### 1.9 Relationships Diagram (textual)

```
prompt_versions ----< prompt_eval_results (prompt_version_id FK)
tools ----< user_ratings (tool_id FK)
tools ----< tool_views (tool_id FK)
search_logs (standalone - references tool IDs in array but no FK)
user_sessions (standalone)
email_captures (standalone)
```

---

## 2. API Routes - Full Inventory

Base URL: `/api` prefix for all routes. FastAPI app at `backend/app/main.py`.

### 2.1 Health Check (no prefix)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/health` | None | - | `{status, database}` | Tests DB connectivity |

### 2.2 Search Router (`/api/search/...`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| POST | `/api/search/semantic` | None | SemanticSearchRequest | SemanticSearchResponse | pgvector cosine similarity |
| POST | `/api/search/catalog` | None | CatalogSearchRequest | CatalogSearchResponse | Faceted SQL filter + keyword |

**SemanticSearchRequest:**
- `query: str` (required, min_length=1) -- natural language search query
- `top_n: int` (default=10, 1-100) -- max results
- `min_similarity: float` (default=0.3, 0.0-1.0) -- minimum cosine similarity threshold

**SemanticSearchResponse:**
- `query: str`
- `total_results: int`
- `results: list[ToolSearchResult]` -- each includes `similarity` score

**CatalogSearchRequest:**
- `pillars: list[str] | None` -- filter by pillar overlap (array && operator)
- `domains: list[str] | None` -- filter by domain overlap
- `type: str | None` -- exact match filter
- `stage: str | None` -- exact match filter
- `target_users: list[str] | None` -- filter by overlap
- `geography: list[str] | None` -- filter by overlap
- `keyword: str | None` -- PostgreSQL full-text search (plainto_tsquery)
- `page: int` (default=1, ge=1)
- `page_size: int` (default=20, 1-100)
- `sort_by: "relevance" | "date" | "rating"` (default="relevance")

**CatalogSearchResponse:**
- `total: int` -- total matching count
- `page: int`
- `page_size: int`
- `results: list[ToolSearchResult]`
- `facets: FacetCounts` -- counts per taxonomy dimension (computed with cross-filter logic)

### 2.3 Chat Router (`/api/chat`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| POST | `/api/chat` | None | ChatRequest | ChatResponse | Multi-turn conversation |

**ChatRequest:**
- `message: str` (required, min_length=1) -- user message text
- `conversation_id: str | None` -- omit to start new conversation

**ChatResponse:**
- `conversation_id: str` -- always returned (generated if new)
- `message: str` -- assistant's text response
- `tools_recommended: list[ToolRecommendation] | None` -- up to 5 tools
- `conversation_complete: bool` -- always false currently

**ToolRecommendation:**
- `id: UUID`
- `title: str`
- `explanation: str` -- truncated summary (max 200 chars)
- `similarity: float`

### 2.4 Tools Router (`/api/tools/...`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/api/tools/{tool_id}` | None | - | ToolRead | Full tool detail; query param `ref` for referrer tracking |
| POST | `/api/tools/{tool_id}/rate` | None | RatingRequest | RatingResponse | Upsert rating, recalculates aggregates |
| GET | `/api/tools/{tool_id}/ratings` | None | - | RatingResponse | Get aggregate rating + distribution |

**RatingRequest:**
- `rating: int` (required, 1-5)
- `user_id: str` (required, min_length=1)

**RatingResponse:**
- `tool_id: UUID`
- `average: float`
- `count: int`
- `distribution: dict[str, int]` -- {"1": n, "2": n, "3": n, "4": n, "5": n}

### 2.5 Metrics Router (`/api/metrics`)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/api/metrics` | None | - | MetricsResponse | Cached for 5 minutes |

**MetricsResponse:**
- `total_tools: int` -- count of visible tools
- `total_frameworks: int` -- count where type='Framework'
- `geography_coverage: int` -- count of distinct geography values
- `total_searches: int` -- count of search_logs rows
- `avg_rating: float` -- average of tools with rating_count > 0

### 2.6 Admin Router (`/api/admin/...`) -- All require Bearer token

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| POST | `/api/admin/login` | None | LoginRequest | LoginResponse | Returns bearer token |
| GET | `/api/admin/tools` | Bearer token | - | AdminToolsResponse | Lists ALL tools (incl hidden) |
| POST | `/api/admin/tools` | Bearer token | ToolCreate | ToolRead (201) | Create new tool |
| PUT | `/api/admin/tools/{tool_id}` | Bearer token | ToolUpdate | ToolRead | Partial update |
| DELETE | `/api/admin/tools/{tool_id}` | Bearer token | - | DeleteResponse | Hard delete (cascades ratings) |

**Query Parameters for GET /api/admin/tools:**
- `page: int` (default=1, ge=1)
- `page_size: int` (default=50, 1-200)
- `keyword: str | None` -- ILIKE on title and summary
- `sort_by: str` (default="title") -- "title", "date", or "type"

**LoginRequest:**
- `username: str`
- `password: str`

**Auth mechanism:** In-memory token store. `ADMIN_USERNAME` and `ADMIN_PASSWORD` from environment variables. Token is a UUID generated on successful login. Validated via `Authorization: Bearer <token>` header. No expiry (in-memory, lost on restart).

### 2.7 Prompt Store Endpoints (in main.py, no separate router)

| Method | Path | Auth | Request Body | Response | Notes |
|--------|------|------|-------------|----------|-------|
| GET | `/api/prompts` | None | - | list[PromptVersionRead] | All prompts, ordered by name then version desc |
| GET | `/api/prompts/{name}/active` | None | - | PromptVersionRead | Active prompt for given name |
| POST | `/api/prompts` | None | PromptVersionCreate | PromptVersionRead (201) | Auto-increments version |
| PUT | `/api/prompts/{prompt_id}/activate` | None | - | PromptVersionRead | Activates one, deactivates others with same name |

### 2.8 Session Tracking

All API requests pass through `SessionMiddleware` which extracts the `X-Session-ID` header and attaches it to `request.state.session_id`. Search and view events are logged asynchronously via `BackgroundTasks` using `TrackingService`.

---

## 3. Chat Service Flow

File: `backend/app/services/chat_service.py`

### 3.1 Architecture Overview

- **LLM:** Anthropic Claude (default: `claude-sonnet-4-20250514`, configurable via `DEFAULT_MODEL` env var)
- **Client:** `anthropic.AsyncAnthropic` (singleton, lazy-initialized)
- **Conversation Store:** In-memory Python dict: `conversations: dict[str, list[dict]]`
- **System Prompt:** Loaded from DB (`prompt_versions` where `prompt_name='chat_system'` and `is_active=true`), falls back to hardcoded `FALLBACK_SYSTEM_PROMPT`
- **Configuration:** `LLM_TIMEOUT=120s`, `MAX_TOKENS=4096`

### 3.2 Multi-Turn Conversation Flow

```
User sends message
       |
       v
get_or_create_conversation(conversation_id)
  - If existing ID found in memory dict, reuse its message history
  - Otherwise create new UUID + empty message list
       |
       v
Append user message to history: {role: "user", content: ...}
       |
       v
Fetch system prompt from DB (or use fallback)
       |
       v
Call Anthropic Messages API:
  - system = system_prompt
  - messages = full conversation history (user + assistant only)
  - model = from DB prompt or DEFAULT_MODEL
  - max_tokens = 4096
  - timeout = 120s
       |
       v
Check response for SEARCH trigger  <--------+
  |                                          |
  +-- No trigger found                      |
  |   - Append assistant response to history |
  |   - Return ChatResponse (no tools)       |
  |                                          |
  +-- Trigger found (<!--SEARCH:{...}-->)    |
      |                                      |
      v                                      |
  Extract search query from JSON             |
  Remove trigger from visible text           |
      |                                      |
      v                                      |
  Execute semantic search (pgvector)         |
    - Generate query embedding               |
    - SELECT with cosine distance            |
    - Filter: embedding IS NOT NULL          |
    -         AND is_visible = true           |
    - Top 8 results, min similarity 0.25     |
      |                                      |
      v                                      |
  Format results as text block               |
  Append to conversation as [SYSTEM] message |
      |                                      |
      v                                      |
  Second Anthropic API call                  |
    - Same system prompt + full history      |
    - Includes search results context        |
      |                                      |
      v                                      |
  Build ToolRecommendation objects           |
    - Top 5 results from search              |
    - explanation = summary[:200]            |
  Append assistant response to history       |
  Return ChatResponse with tools_recommended |
```

### 3.3 SEARCH Marker Pattern

- **Regex:** `<!--SEARCH:\s*(\{.*?\})\s*-->` (DOTALL mode)
- **Format:** `<!--SEARCH:{"query": "refined search query"}-->`
- The LLM is instructed to output this exact pattern on its own line when it has enough context
- The trigger is stripped from the visible response before returning to the user
- Any accidental search triggers in the final response are also stripped

### 3.4 Decision Logic: Clarifying Questions vs Recommendations

The LLM (via the system prompt) decides when to ask clarifying questions vs search:
1. On first user message: ask 2-3 clarifying questions about context, geography, stage, stakeholders
2. If the request is very specific from the start: may search after just 1 clarifying question
3. Once enough context is gathered: output the `<!--SEARCH:...-->` trigger
4. The search query synthesizes the entire conversation into a search-optimized natural-language query

### 3.5 How Tool Recommendations Are Generated

1. Search results come from pgvector cosine similarity (top 8, min 0.25 similarity)
2. Results are formatted as a text block with all metadata fields per tool
3. The LLM receives these as `[SYSTEM]` context and generates personalized explanations
4. The code builds `ToolRecommendation` objects from the top 5 search results
5. Each recommendation includes: id, title, explanation (summary[:200]), similarity score

---

## 4. Data Pipeline Stages

### 4.1 Pipeline Overview

```
Raw document metadata (dict)
       |
       v
  Stage 1: CLASSIFY (classifier.py)
    - Input: title, authors, date, abstract, doc_type, url
    - LLM call with active "relevance_classification" prompt
    - Output: {relevant: bool, confidence: float, reasoning: str}
    - If not relevant -> status="skipped_irrelevant", stop
       |
       v
  Stage 2: EXTRACT (extractor.py)
    - Input: title, authors, date, abstract, full_text
    - LLM call with active "metadata_extraction" prompt
    - Output: structured JSON with taxonomy fields
    - Validated against taxonomy (fuzzy matching, corrections)
       |
       v
  Stage 3: EMBED (embeddings.py)
    - Input: title, summary, what_it_does, when_to_use_it, who_its_for
    - Concatenate text fields (newline-separated)
    - OpenAI text-embedding-3-small -> 1536-dim vector
    - Non-fatal: if embedding fails, tool stored without it
       |
       v
  Stage 4: STORE (ingest.py)
    - Input: raw item + extraction + relevance_score + embedding
    - Derive cgspace_id (explicit > URL path > SHA-256 hash)
    - INSERT ... ON CONFLICT (cgspace_id) DO UPDATE (idempotent upsert)
    - Output: tool UUID
```

### 4.2 Stage 1: Classify (pipeline/classifier.py)

- **Prompt source:** Active `relevance_classification` prompt from `prompt_versions` table
- **Template substitution:** Manually replaces `{title}`, `{authors}`, `{date}`, `{abstract}`, `{doc_type}`, `{url}` placeholders
- **LLM call:** Uses shared `pipeline.llm.call_llm()` function
- **JSON parsing:** Three-tier extraction (direct parse -> markdown fence -> regex for `"relevant"` key)
- **Output fields:** `relevant` (bool), `confidence` (0.0-1.0), `reasoning` (str), `latency_ms`, `model`, `prompt_version_id`, `raw_response`, `error`

### 4.3 Stage 2: Extract (pipeline/extractor.py)

- **Prompt source:** Active `metadata_extraction` prompt from `prompt_versions` table
- **Template substitution:** Replaces `{title}`, `{authors}`, `{date}`, `{abstract}`, `{full_text}` placeholders
- **LLM call:** Direct Anthropic SDK (`anthropic.Anthropic.messages.create`)
- **JSON parsing:** Markdown fence extraction, fallback to brace-matching
- **Taxonomy validation:** Calls `pipeline.taxonomy.validate_extraction()` which does:
  - Exact match, case-insensitive match, then fuzzy match (difflib, cutoff=0.75)
  - Invalid values are removed with warnings
  - Corrected values logged as warnings
- **Output:** Cleaned dict with all taxonomy fields + `_prompt_version_id`, `_latency_ms`, `_model`, `_warnings`

### 4.4 Stage 3: Embed (pipeline/embeddings.py)

- **Model:** OpenAI `text-embedding-3-small`
- **Dimensions:** 1536
- **Input construction:** Concatenate (title, summary, what_it_does, when_to_use_it, who_its_for) with newline separators. Empty fields are excluded.
- **API:** `openai.OpenAI().embeddings.create(input=text, model="text-embedding-3-small")`
- **Validation:** Verifies output is exactly 1536 dimensions
- **Storage format:** `"[v1,v2,...,v1536]"` cast to `::vector` in SQL
- **Backfill function:** `backfill_embeddings(force=False)` can regenerate all missing or all embeddings

### 4.5 Stage 4: Store (pipeline/ingest.py)

- **Deduplication key:** `cgspace_id` (derived from explicit field, CGSpace URL path, or SHA-256 of title)
- **SQL strategy:** `INSERT ... ON CONFLICT (cgspace_id) DO UPDATE SET ...` -- fully idempotent
- **Database driver:** psycopg2 (synchronous, not the async backend driver)
- **Fields stored:** All taxonomy fields, metadata, embedding, relevance_score, is_visible=true
- **Returns:** UUID of inserted/updated row

### 4.6 Batch Processor (pipeline/batch_processor.py)

**Configuration (`BatchConfig`):**
- `batch_id`: Auto-generated timestamp-based ID
- `max_retries`: 3 (per stage)
- `retry_base_delay`: 2.0 seconds (exponential backoff: delay * 2^attempt)
- `llm_delay`: 1.0 second minimum between LLM calls
- `embedding_delay`: 0.2 seconds minimum between embedding calls
- `llm_concurrency`: 1-5 worker threads (clamped)
- `mock_mode`: Synthetic responses for infrastructure testing
- `state_dir`: Directory for progress/state/report files

**Concurrency model:**
- `ThreadPoolExecutor` with configurable workers (1-5)
- `threading.Lock` for shared counters, rate-limit timestamps, file writes
- Each worker runs the full 4-stage pipeline for one item

**Resumability mechanism:**
- **progress.json:** Real-time progress snapshot (status, counts, ETA, items/minute)
- **batch_state.json:** Full state with `processed_ids` set and per-item results
- **batch_report.json:** Final report with latency breakdowns and taxonomy distribution
- All files written atomically (write to temp file, then `os.replace()`)
- On resume: loads `batch_state.json`, rebuilds `processed_ids` set, skips already-processed items
- Handles `KeyboardInterrupt`: saves state and generates partial report

**Retry logic:**
- Per-stage exponential backoff: `base_delay * 2^attempt`
- Tracks total retries and retries-by-stage
- Embedding failure is non-fatal (tool stored without embedding)

**Mock mode:**
- Random relevance (70% relevant), random taxonomy values, random latencies
- No actual API calls (LLM or OpenAI)
- Generates fake UUIDs for tool_id
- Useful for testing batch infrastructure at scale

**Report output includes:**
- Summary: stored/skipped/failed counts, success rate, elapsed time
- Latency averages: per-stage (classify, extract, embed, store, total)
- Retry stats: total retries, retries by stage
- Failure reasons: error message -> count
- Taxonomy distribution: counts per pillar, domain, type, stage

---

## 5. Frontend Component Tree

### 5.1 Routing Structure

```
<BrowserRouter>
  <AppContent>
    <Header />                          (always visible, navigation bar)
    <main>
      <Routes>
        /           -> <HomePage>
        /about      -> <AboutPage>
        /tutorial   -> <TutorialPage>
        /catalog    -> <CatalogPage>
        /admin      -> <AdminPage>
      </Routes>
    </main>
    <EmailCaptureModal />               (global overlay, conditional)
  </AppContent>
</BrowserRouter>
```

### 5.2 Component Hierarchy

```
App
 +-- BrowserRouter
      +-- AppContent
           +-- Header (layout/Header.tsx) - Navigation with logo, links
           +-- Routes
           |    +-- / -> HomePage
           |    |       +-- [!isActive] HeroSection (home/HeroSection.tsx) - Landing hero with chat input
           |    |       +-- [isActive] ChatInterface (chat/ChatInterface.tsx)
           |    |       |                +-- ChatMessage (chat/ChatMessage.tsx) - Individual message bubbles
           |    |       |                +-- ToolCarousel (chat/ToolCarousel.tsx) - Horizontal scroll of recommended tools
           |    |       |                |    +-- ToolCard (chat/ToolCard.tsx) - Card for each recommended tool
           |    |       |                +-- ChatInput (chat/ChatInput.tsx) - Text input + send button
           |    |       +-- [selectedToolId] ToolDetailPanel (tool/ToolDetailPanel.tsx)
           |    |                            +-- TypeBadge (common/TypeBadge.tsx)
           |    |                            +-- StarRating (tool/StarRating.tsx)
           |    |                            +-- LoadingSpinner (common/LoadingSpinner.tsx)
           |    +-- /about -> AboutPage
           |    +-- /tutorial -> TutorialPage
           |    +-- /catalog -> CatalogPage (pages/CatalogPage.tsx)
           |    |                +-- CatalogPageComponent (catalog/CatalogPage.tsx)
           |    |                     +-- FilterSidebar (catalog/FilterSidebar.tsx)
           |    |                     |    +-- FilterGroup (catalog/FilterGroup.tsx) - Per-dimension filter
           |    |                     +-- CatalogResults (catalog/CatalogResults.tsx) - Grid of tool cards
           |    |                     +-- Pagination (catalog/Pagination.tsx)
           |    |                     +-- [selectedToolId] ToolDetailPanel
           |    +-- /admin -> AdminPage
           |                  +-- [!authenticated] LoginForm
           |                  +-- [authenticated] AdminPanel
           |                       +-- [modalOpen] ToolModal (create/edit form)
           +-- EmailCaptureModal (common/EmailCaptureModal.tsx)
```

### 5.3 State Management

**No external state library.** State management uses React hooks (useState, useCallback, useEffect) with custom hooks:

**`useChat` hook** (`hooks/useChat.ts`):
- State: `messages[]`, `conversationId`, `isLoading`, `error`, `isActive`, `recommendedTools[]`, `conversationComplete`
- `sendMessage(content)`: Appends user message, calls API, appends assistant message, extracts tool recommendations
- `resetChat()`: Clears all state to initial values
- Conversation starts inactive (shows HeroSection), becomes active on first message

**`useCatalogSearch` hook** (`hooks/useCatalogSearch.ts`):
- State: `filters`, `results[]`, `facets`, `total`, `page`, `pageSize`, `sortBy`, `loading`, `error`
- Auto-searches on `filters`, `page`, or `sortBy` changes (via useEffect)
- `updateFilter(key, value)`: Sets filter and resets to page 1
- `toggleArrayFilter(key, value)`: Toggles item in array filter
- `clearFilters()`: Resets all filters to empty defaults
- `updateSort(sort)`: Changes sort order and resets to page 1

**`useMetrics` hook** (`hooks/useMetrics.ts`): Fetches platform-wide metrics for MetricsBar.

### 5.4 EmailCaptureModal Trigger Conditions

The modal appears when ANY of these conditions are met (and `sessionStorage.email_captured` is not set):

1. **Time-based:** 30 seconds after page load (setTimeout)
2. **Engagement-based:** After the user has viewed 2+ tool detail panels (`toolViewCount >= 2`)

The `toolViewCount` is tracked at the App level via `handleToolViewed` callback, passed down through HomePage and CatalogPage, and incremented by ToolDetailPanel when it successfully loads a tool.

**Dismissal:** Sets `sessionStorage.email_captured = 'true'` so it does not reappear in the same browser session. User can dismiss via close button, backdrop click, Escape key, or "No thanks" button.

### 5.5 API Client (`services/api.ts`)

- Base URL: `VITE_API_BASE_URL` env var (empty for local dev with Vite proxy)
- Session tracking: Auto-generates UUID stored in `localStorage['ee-session-id']`, sent as `X-Session-ID` header
- Admin auth: Bearer token stored in `localStorage['admin-token']`
- All requests include `Content-Type: application/json`

---

## 6. AWS Infrastructure

### 6.1 Stack 1: Database (`ee-toolbox-database.yaml`)

**Resources created:**

| Resource | Type | Key Properties |
|----------|------|---------------|
| DBSubnetGroup | AWS::RDS::DBSubnetGroup | 3 subnets across eu-central-1a/b/c |
| DBSecret | AWS::SecretsManager::Secret | Username: "eetoolbox", auto-generated 32-char password |
| RDSSecurityGroup | AWS::EC2::SecurityGroup | No ingress rules (added by app stack) |
| DBInstance | AWS::RDS::DBInstance | PostgreSQL 16.6, db.t4g.micro, 20GB gp3, not publicly accessible, DB name: ee_toolbox |

**Outputs exported:**
- `ee-toolbox-DBEndpoint` -- RDS endpoint address
- `ee-toolbox-DBPort` -- RDS port
- `ee-toolbox-DBSecretArn` -- Secrets Manager ARN
- `ee-toolbox-RDSSecurityGroupId` -- SG ID for cross-stack ingress rules

### 6.2 Stack 2: Application (`ee-toolbox-app.yaml`)

**Parameters received:**
- `DBEndpoint`, `DBSecretArn`, `RDSSecurityGroupId` (from database stack)
- `VpcId`, `SubnetIds`, `CertificateArn` (VPC/network)
- `ImageTag` (Docker image SHA)
- `AnthropicApiKey`, `OpenAIApiKey`, `AdminPassword` (secrets)

**Resources created:**

| Resource | Type | Key Properties |
|----------|------|---------------|
| ApiKeysSecret | AWS::SecretsManager::Secret | Stores Anthropic + OpenAI API keys as JSON |
| ECSCluster | AWS::ECS::Cluster | Name: ee-toolbox-cluster, Container Insights enabled |
| LogGroup | AWS::Logs::LogGroup | /ecs/ee-toolbox-backend, 14-day retention |
| TaskExecutionRole | AWS::IAM::Role | ECS task execution + Secrets Manager read + ECR pull + CloudWatch Logs |
| TaskRole | AWS::IAM::Role | Application-level AWS calls (currently empty) |
| ALBSecurityGroup | AWS::EC2::SecurityGroup | Ingress: 80 and 443 from 0.0.0.0/0 |
| ECSSecurityGroup | AWS::EC2::SecurityGroup | Ingress: 8099 from ALB SG only |
| RDSIngressFromECS | AWS::EC2::SecurityGroupIngress | Adds rule to RDS SG: 5432 from ECS SG |
| ALB | AWS::ElasticLoadBalancingV2::LoadBalancer | Internet-facing, application type |
| TargetGroup | AWS::ElasticLoadBalancingV2::TargetGroup | Port 8099, HTTP, IP target type, /health check |
| HTTPSListener | AWS::ElasticLoadBalancingV2::Listener | Port 443, HTTPS with ACM certificate, forwards to target group |
| HTTPListener | AWS::ElasticLoadBalancingV2::Listener | Port 80, HTTP -> HTTPS redirect (301) |
| TaskDefinition | AWS::ECS::TaskDefinition | Fargate, 512 CPU / 1024 MB memory, container port 8099 |
| ECSService | AWS::ECS::Service | 1 desired task, Fargate, public IP, 120s health check grace |
| APIDNSRecord | AWS::Route53::RecordSet | api-ee-toolbox.synapsis-analytics.com -> ALB alias |

**Container configuration:**
- Image: `{AccountId}.dkr.ecr.eu-central-1.amazonaws.com/ee-toolbox-backend:{ImageTag}`
- Port: 8099
- Environment variables: DATABASE_URL (asyncpg), DATABASE_URL_SYNC (psycopg2), ADMIN_PASSWORD, CORS_ORIGINS, DEFAULT_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY
- Health check: Python urllib hitting localhost:8099/health
- Logs: awslogs driver to CloudWatch

**Security group chain:**
```
Internet -> ALB SG (443/80) -> ECS SG (8099) -> RDS SG (5432)
```

**Outputs exported:**
- `ee-toolbox-ALBDnsName`
- `ee-toolbox-APIUrl` = https://api-ee-toolbox.synapsis-analytics.com
- `ee-toolbox-ECRRepositoryUri`
- `ee-toolbox-ECSClusterName`
- `ee-toolbox-ECSServiceName`

### 6.3 Stack 3: Frontend (`ee-toolbox-frontend.yaml`)

**Resources created:**

| Resource | Type | Key Properties |
|----------|------|---------------|
| AmplifyApp | AWS::Amplify::App | Name: ee-toolbox, SPA rewrite rule (/<*> -> /index.html), VITE_API_BASE_URL env var |
| AmplifyBranch | AWS::Amplify::Branch | Branch: main, auto-build disabled (deployed via CI/CD) |
| AmplifyDomain | AWS::Amplify::Domain | Custom domain: ee-toolbox.synapsis-analytics.com mapped to main branch |

**Outputs exported:**
- `ee-toolbox-AmplifyAppId`
- `ee-toolbox-AmplifyDefaultDomain`
- `ee-toolbox-FrontendUrl` = https://ee-toolbox.synapsis-analytics.com

### 6.4 CI/CD Pipeline (`.github/workflows/deploy.yml`)

**Trigger:** Push to `main` branch or manual `workflow_dispatch`

**OIDC Authentication:**
- Permissions: `id-token: write`, `contents: read`
- Uses `aws-actions/configure-aws-credentials@v4` with `role-to-assume` from `AWS_DEPLOY_ROLE_ARN` secret
- No static credentials -- GitHub OIDC identity federation with AWS IAM

**Pipeline Steps (sequential):**

```
1. Checkout code
2. Configure AWS credentials (OIDC)
3. Verify AWS account
4. Setup Node.js 20, npm ci, build frontend
   - VITE_API_BASE_URL=https://api-ee-toolbox.synapsis-analytics.com npm run build
5. Clean up failed CloudFormation stacks
   - Handles: ROLLBACK_COMPLETE, DELETE_FAILED, CREATE_FAILED, stuck IN_PROGRESS
   - Polls for up to 5 minutes for IN_PROGRESS stacks
6. Deploy database stack (CloudFormation deploy)
7. Get database stack outputs (endpoint, secret ARN, SG ID)
8. Login to ECR
9. Ensure ECR repository exists (create if missing)
10. Build and push Docker image
    - Tags: {sha} and latest
11. Look up VPC subnets and ACM certificate
12. Deploy app stack (CloudFormation)
    - First time: create-stack (bypasses changeset hooks)
    - Updates: deploy with --no-fail-on-empty-changeset
13. Force new ECS deployment
14. Wait for backend health (poll /health up to 8 minutes, 48 x 10s)
15. Seed database
    - Runs ECS task with override: python /app/backend/scripts/seed_db.py
    - Waits up to 10 minutes for task completion
    - Checks exit code, fetches logs on failure
    - Non-blocking: continues deployment even if seed fails
16. Deploy frontend stack (CloudFormation)
17. Deploy to Amplify
    - Creates ZIP of frontend/dist
    - Creates Amplify deployment, uploads ZIP, starts deployment
    - Polls for SUCCEED status (up to 5 minutes)
18. Print deployment summary with URLs
```

**URLs:**
- Backend API: https://api-ee-toolbox.synapsis-analytics.com
- Frontend: https://ee-toolbox.synapsis-analytics.com
- Health check: https://api-ee-toolbox.synapsis-analytics.com/health

---

## 7. User Journey Flows

### 7.1 AI-Guided Discovery Flow

```
User lands on / (HomePage)
       |
       v
HeroSection displayed (hero image carousel, tagline, chat input)
       |
       v
User types a question and presses Enter/Send
       |
       v
useChat.sendMessage() -> isActive becomes true
HeroSection replaced by ChatInterface
       |
       v
User message appears in chat (ChatMessage, role=user)
Loading indicator shown (isLoading=true)
       |
       v
API POST /api/chat (first turn, no conversation_id)
       |
       v
Assistant responds with clarifying questions (ChatMessage, role=assistant)
conversation_id is now set for subsequent turns
       |
       v
User answers clarifying questions -> sends another message
       |
       v
API POST /api/chat (with conversation_id)
  - LLM outputs <!--SEARCH:{query}--> trigger
  - Backend executes semantic search
  - Second LLM call generates personalized recommendations
       |
       v
Response includes tools_recommended[]
ChatInterface shows assistant message + ToolCarousel
  - ToolCarousel: horizontal scrollable row of ToolCard components
  - Each ToolCard shows: title, type badge, summary snippet, similarity score
       |
       v
User clicks a ToolCard -> handleToolSelect(tool) -> sets selectedToolId
       |
       v
ToolDetailPanel slides in from right (60% width on desktop)
  - Fetches full tool data via GET /api/tools/{tool_id}
  - Shows: cover image, type badge, title, authors, date, organization
  - Sections: summary, what_it_does, when_to_use_it, who_its_for
  - Tags: pillars, domains, geography
  - StarRating component for interactive rating
  - "Visit Resource" link + "Share" button
  - onToolViewed() increments toolViewCount in App
       |
       v
User can rate tool (1-5 stars)
  - POST /api/tools/{tool_id}/rate
  - Aggregates recalculated server-side
       |
       v
User closes panel (X, Escape, or backdrop click) -> returns to chat
User can continue conversation or click "New chat" (resetChat)
       |
       v
After viewing 2+ tools, EmailCaptureModal may appear
```

### 7.2 Catalog Browsing Flow

```
User navigates to /catalog
       |
       v
CatalogPage renders with useCatalogSearch hook
Auto-fires initial search (empty filters, page 1, sort=relevance)
       |
       v
Layout: FilterSidebar (left) + CatalogResults grid (right)
       |
       +-- FilterSidebar:
       |     - Keyword text input
       |     - Expandable FilterGroup for each dimension:
       |       Pillars, Domains, Type, Stage, Target Users, Geography
       |     - Each FilterGroup shows checkboxes with facet counts
       |     - Facet counts update based on cross-filter logic
       |     - "Clear all" button
       |
       +-- Sort dropdown (Relevance / Date / Rating)
       |
       +-- CatalogResults: grid of tool cards
       |     - Each card shows: title, type badge, summary, pillars tags
       |     - Click opens ToolDetailPanel
       |
       +-- Pagination: Previous/Next with page indicator
       |
       v
User applies filters (toggleArrayFilter) or types keyword
  -> Resets to page 1
  -> Auto-triggers search via useEffect
  -> POST /api/search/catalog with filters
  -> Updates results, facets, and total count
       |
       v
User clicks a tool card -> ToolDetailPanel opens (same as AI flow)
User can rate, share, or visit the resource
```

### 7.3 Admin Management Flow

```
User navigates to /admin
       |
       v
AdminPage checks localStorage['admin-token']
       |
  +-- No token -> LoginForm displayed
  |     - Username + password form
  |     - POST /api/admin/login
  |     - On success: stores token in localStorage, sets authenticated=true
  |     - On failure: shows "Invalid credentials" error
  |
  +-- Token exists -> AdminPanel displayed
        |
        v
  AdminPanel loads tools: GET /api/admin/tools?page=1&page_size=50&sort_by=title
  (Includes hidden tools, unlike public endpoints)
        |
        v
  Interface:
    - Search input (keyword filter)
    - Sort dropdown (Title / Date / Type)
    - "+ Add New Tool" button
    - Table with columns: Title, Type, Stage, Pillars, Published, Visible, Actions
    - Pagination (Previous/Next)
        |
        +-- Click row -> Opens ToolModal in edit mode
        |     - Pre-populated form with all tool fields
        |     - Checkboxes for array fields (pillars, domains, target_users, geography)
        |     - Dropdowns for type and stage
        |     - "Update Tool" button
        |     - PUT /api/admin/tools/{tool_id}
        |
        +-- Click "+ Add New Tool" -> Opens ToolModal in create mode
        |     - Empty form
        |     - "Create Tool" button
        |     - POST /api/admin/tools
        |
        +-- Click "Delete" on a row -> Confirmation dialog
        |     - DELETE /api/admin/tools/{tool_id}
        |     - Hard delete (cascades ratings first)
        |
        +-- Token expiry/invalidation -> 401 response -> auto-logout
        |
        +-- "Logout" link -> removes token, shows LoginForm
```

---

## 8. Data Model - Tool Schema

### 8.1 SQLAlchemy Model (`backend/app/models/tool.py`)

All fields with their Python types, database types, and whether they are required:

| Field | Python Type | DB Type | Required | Server Default | Notes |
|-------|------------|---------|----------|---------------|-------|
| id | uuid.UUID | UUID | Auto | gen_random_uuid() | Primary key |
| title | str | Text | YES | - | Only required field |
| summary | str \| None | Text | No | - | LLM-generated |
| what_it_does | str \| None | Text | No | - | LLM-generated |
| when_to_use_it | str \| None | Text | No | - | LLM-generated |
| who_its_for | str \| None | Text | No | - | LLM-generated |
| pillars | list[str] \| None | Text[] | No | - | ARRAY column |
| domains | list[str] \| None | Text[] | No | - | ARRAY column |
| type | str \| None | Text | No | - | Single taxonomy value |
| stage | str \| None | Text | No | - | Single taxonomy value |
| target_users | list[str] \| None | Text[] | No | - | ARRAY column |
| geography | list[str] \| None | Text[] | No | - | ARRAY column |
| authors | list[str] \| None | Text[] | No | - | ARRAY column |
| date_published | date \| None | Date | No | - | |
| source_url | str \| None | Text | No | - | |
| source_organization | str \| None | Text | No | - | |
| cover_image_url | str \| None | Text | No | - | |
| embedding | (Vector) | vector(1536) | No | - | pgvector, not mapped as Python type |
| average_rating | float | Numeric(3,2) | Auto | 0 | Recomputed on rating |
| rating_count | int | Integer | Auto | 0 | Recomputed on rating |
| view_count | int | Integer | Auto | 0 | |
| cgspace_id | str \| None | Text | No (UNIQUE) | - | Deduplication key |
| relevance_score | float \| None | Numeric(3,2) | No | - | Classifier confidence |
| is_visible | bool | Boolean | Auto | true | Soft-visibility flag |
| created_at | datetime | Timestamp w/tz | Auto | now() | |
| updated_at | datetime | Timestamp w/tz | Auto | now() | onupdate=func.now() |

### 8.2 Pydantic Schemas (`backend/app/schemas/tool.py`)

**ToolCreate** (for POST /api/admin/tools):
- `title: str` -- REQUIRED
- All other fields optional (same as ToolBase)
- `is_visible: bool = True` (defaults to visible)

**ToolUpdate** (for PUT /api/admin/tools/{id}):
- ALL fields optional (including title)
- Uses `model_dump(exclude_unset=True)` for partial updates

**ToolRead** (response schema):
- Inherits all ToolBase fields
- Adds computed/auto fields: `id`, `average_rating`, `rating_count`, `view_count`, `created_at`, `updated_at`
- `model_config = {"from_attributes": True}` for ORM compatibility

---

## 9. Search Architecture

### 9.1 Semantic Search (POST /api/search/semantic)

**Pipeline:**
```
1. Receive query string from request body
2. Generate query embedding:
   - Call OpenAI text-embedding-3-small (offloaded to thread via asyncio.to_thread)
   - Returns 1536-dim float vector
3. Format as pgvector literal: "[v1,v2,...,v1536]"
4. Execute SQL:
   SELECT ... , 1 - (embedding <=> CAST(:vec AS vector)) AS similarity
   FROM tools
   WHERE embedding IS NOT NULL AND is_visible = true
   ORDER BY embedding <=> CAST(:vec AS vector)
   LIMIT :limit
5. Filter results: skip rows where similarity < min_similarity (default 0.3)
6. Return ToolSearchResult list with similarity scores
7. Log search in background (TrackingService.log_search)
```

**Key details:**
- Distance operator: `<=>` is pgvector's cosine distance
- Similarity = `1 - cosine_distance` (so 1.0 = identical, 0.0 = orthogonal)
- Uses HNSW index for approximate nearest neighbor search
- Default min_similarity threshold: 0.3
- Default top_n: 10 (max 100)

### 9.2 Pipeline Search (pipeline/search.py)

Synchronous version of semantic search used in the pipeline package:
- Same query embedding generation
- Same SQL with cosine distance
- Uses psycopg2 (sync) instead of asyncpg
- Returns `SearchResult` dataclass objects
- Includes `print_search_results()` for CLI display

### 9.3 Catalog Search (POST /api/search/catalog)

**Pipeline:**
```
1. Build dynamic WHERE clause from filters:
   - is_visible = true (always)
   - pillars && CAST(:pillars AS text[])     -- array overlap (any match)
   - domains && CAST(:domains AS text[])     -- array overlap
   - type = :type                            -- exact match
   - stage = :stage                          -- exact match
   - target_users && CAST(:target_users AS text[]) -- array overlap
   - geography && CAST(:geography AS text[]) -- array overlap
   - to_tsvector('english', ...) @@ plainto_tsquery('english', :keyword) -- full-text search

2. Count total matching rows

3. Determine sort order:
   - "relevance": ts_rank() if keyword present, else title ASC
   - "date": date_published DESC NULLS LAST
   - "rating": average_rating DESC, rating_count DESC

4. Execute paginated query with LIMIT/OFFSET

5. Compute facet counts (see 9.4)

6. Log search in background
```

### 9.4 Facet Count Computation

Facet counts use a **cross-filter** approach: for each taxonomy dimension, the count query applies all filters EXCEPT the filter for that dimension. This gives users accurate counts of what they could see if they changed just one filter.

**Dimensions computed:**

| Dimension | Column Type | SQL Approach |
|-----------|------------|-------------|
| pillars | Text[] (array) | `SELECT val, COUNT(*) FROM tools, unnest(pillars) AS val WHERE ... GROUP BY val` |
| domains | Text[] (array) | Same unnest approach |
| type | Text (scalar) | `SELECT type AS val, COUNT(*) FROM tools WHERE ... AND type IS NOT NULL GROUP BY type` |
| stage | Text (scalar) | Same scalar approach |
| target_users | Text[] (array) | Same unnest approach |
| geography | Text[] (array) | Same unnest approach |

For each dimension:
1. Start with `is_visible = true`
2. Add keyword filter if present (always applied across all facets)
3. Add all OTHER dimension filters (skip the current dimension)
4. Run the appropriate SQL (unnest for arrays, group by for scalars)
5. Return `{value: count}` dict

---

## 10. Taxonomy

### 10.1 Pillars (5 values)

1. Gender Equality and Social Inclusion
2. Monitoring, Evaluation and Learning
3. Policy and Regulatory
4. Market Systems
5. Digital and Financial Services

### 10.2 Domains (3 values)

1. Agri-food Systems
2. Scaling Innovation
3. Climate Resilience

### 10.3 Types (10 values)

1. Method
2. Framework
3. Manual
4. Toolkit
5. Tool
6. Guide
7. Matrix
8. Scorecard
9. Brief
10. Scale

### 10.4 Stages (4 values)

1. Established and field-tested
2. Prototype
3. Theoretical and diagnostics
4. Conceptual

### 10.5 Target Users (16 values)

1. Researcher
2. Policymaker
3. Development Practitioner
4. Extension services
5. Agribusiness
6. Local communities
7. Civil Society and INGOs
8. Funders and Donors
9. Private sector entities
10. Government agencies
11. Humanitarian assistance practitioners
12. Project and program managers
13. Farmers and Agro-pastoralists
14. Monitoring and Evaluation specialists
15. Community leaders
16. Irrigation scheme managers

### 10.6 Geography (8 values)

1. Global
2. Asia
3. Africa
4. MENA
5. Latin America
6. Europe
7. Low-income and middle-income countries
8. Central and West Asia and North Africa (CWANA)

### 10.7 Taxonomy Validation

The `pipeline/taxonomy.py` module provides validation with three levels of matching:

1. **Exact match:** Value is in the valid set as-is
2. **Case-insensitive match:** Value matches after lowering both sides
3. **Fuzzy match:** Uses `difflib.get_close_matches()` with cutoff=0.75

Invalid values are removed entirely. Corrected values generate warning messages. Array fields are deduplicated. Non-string values generate warnings.

### 10.8 Type Color Mapping (Frontend)

Each tool type has an assigned color for UI badges:

| Type | Hex Color |
|------|----------|
| Method | #1565C0 (blue) |
| Framework | #2E7D32 (green) |
| Manual | #E65100 (deep orange) |
| Toolkit | #7B1FA2 (purple) |
| Tool | #00695C (teal) |
| Guide | #5D4037 (brown) |
| Matrix | #455A64 (blue-grey) |
| Scorecard | #C62828 (red) |
| Brief | #F57F17 (amber) |
| Scale | #AD1457 (pink) |

Note: "Brief" uses dark text on its badge (for WCAG AA contrast), all others use white text.
