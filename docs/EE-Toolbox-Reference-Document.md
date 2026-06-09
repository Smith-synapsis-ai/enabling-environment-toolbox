# Enabling Environments Toolbox
## Comprehensive Architecture & Reference Document

**Version:** 1.0
**Date:** May 2026
**Status:** Production
**Prepared for:** CGIAR Enabling Environments Initiative

---

## 1. Executive Overview

The Enabling Environments Toolbox is an AI-powered web application that helps agricultural development practitioners discover relevant tools, frameworks, and methods for scaling innovation in enabling environments. It combines a curated database of 92 tools with AI-guided discovery through conversational search, semantic vector search, and faceted catalog browsing.

The application is built as a modern full-stack web application with a React frontend, Python FastAPI backend, and PostgreSQL database with vector search capabilities. It is deployed on AWS using infrastructure-as-code and automated CI/CD pipelines.

**Key Numbers:**
- 92 curated tools with full metadata and vector embeddings
- 5 thematic pillars and 3 cross-cutting domains
- 10 tool types, 4 maturity stages, 8 geographic regions
- 18 API endpoints across 6 functional groups
- 4 AWS CloudFormation stacks in production

---

## 2. System Architecture Overview

The system follows a three-tier architecture pattern with a clear separation between the presentation layer (React SPA), business logic layer (FastAPI backend), and data layer (PostgreSQL with pgvector). A separate data pipeline handles tool ingestion and enrichment.

[DIAGRAM: High-Level System Architecture]

```
                    USERS (Browser)
                         |
                    HTTPS (TLS 1.3)
                         |
          +--------------+--------------+
          |                             |
    AWS Amplify                  AWS ALB (HTTPS)
    (CDN + SPA hosting)         (Load Balancer)
          |                             |
    React Frontend              ECS Fargate Container
    ee-toolbox.                 api-ee-toolbox.
    synapsis-analytics.com      synapsis-analytics.com
          |                             |
          |                      FastAPI Backend
          |                      (Port 8099)
          |                             |
          |                      +------+------+
          |                      |             |
          |               PostgreSQL 16    External LLMs
          |               + pgvector       (Anthropic Claude,
          |               (AWS RDS)         OpenAI Embeddings)
          |                      |
          +-------> REST API <---+
```

The frontend communicates exclusively through REST API calls to the backend. The backend handles all business logic, LLM interactions, and database operations. External LLM services (Anthropic Claude for conversation, OpenAI for embeddings) are called only from the backend, never from the frontend.

---

## 3. Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite build tool
- Tailwind CSS for styling
- React Router for navigation
- Lucide React for icons
- No external state management library (React hooks only)

**Backend:**
- Python 3.11+ with FastAPI
- SQLAlchemy ORM with async support (asyncpg driver)
- Alembic for database migrations
- Anthropic SDK for Claude LLM integration
- OpenAI SDK for text embeddings
- Pydantic for request/response validation

**Database:**
- PostgreSQL 16 with pgvector extension
- HNSW index for approximate nearest neighbor search
- GIN indexes for array overlap queries and full-text search

**Infrastructure:**
- AWS ECS Fargate (backend container)
- AWS RDS PostgreSQL (managed database)
- AWS Amplify (frontend hosting with CDN)
- AWS ALB with ACM certificates (HTTPS termination)
- AWS Secrets Manager (credentials)
- GitHub Actions CI/CD with OIDC authentication

---

## 4. Data Pipeline Architecture

The data pipeline transforms raw document metadata into enriched, searchable tool records through a four-stage process. Each stage uses different AI capabilities to classify relevance, extract structured metadata, generate vector embeddings, and store the results.

[DIAGRAM: Four-Stage Data Pipeline]

```
  RAW DOCUMENT METADATA
  (title, abstract, authors, date, URL)
           |
           v
  +------------------+
  | STAGE 1: CLASSIFY |
  | (Claude LLM)      |
  | Relevance scoring  |
  | 100% accuracy on   |
  | 49-item test set   |
  +--------+---------+
           |
     relevant?
    /         \
  NO           YES
  |              |
  v              v
SKIP      +------------------+
          | STAGE 2: EXTRACT  |
          | (Claude LLM)      |
          | Metadata extraction|
          | Taxonomy validation|
          | Fuzzy matching     |
          +--------+---------+
                   |
                   v
          +------------------+
          | STAGE 3: EMBED   |
          | (OpenAI)          |
          | text-embedding-   |
          | 3-small           |
          | 1536 dimensions   |
          +--------+---------+
                   |
                   v
          +------------------+
          | STAGE 4: STORE   |
          | (PostgreSQL)      |
          | Upsert with       |
          | deduplication     |
          | (cgspace_id key)  |
          +------------------+
                   |
                   v
          SEARCHABLE TOOL
          (with embedding)
```

**Stage 1 - Classify:** Uses Claude with a versioned prompt to determine if a document is relevant to the Enabling Environments framework. Returns a confidence score (0-1) and reasoning. Achieves 100% accuracy on the 49-item evaluation set.

**Stage 2 - Extract:** Uses Claude with a separate versioned prompt to extract structured metadata: summary, what_it_does, when_to_use_it, who_its_for, plus taxonomy classifications (pillars, domains, type, stage, target_users, geography). All taxonomy values are validated with three-tier matching (exact, case-insensitive, fuzzy).

**Stage 3 - Embed:** Generates a 1536-dimensional vector embedding using OpenAI's text-embedding-3-small model. The embedding captures the semantic meaning of the tool by concatenating its title, summary, and descriptive fields. This is non-fatal --- if embedding generation fails, the tool is still stored without it.

**Stage 4 - Store:** Inserts or updates the tool record in PostgreSQL using an idempotent upsert keyed on cgspace_id (derived from the source URL or a hash of the title).

### Batch Processing at Scale

For processing large volumes of documents, the BatchProcessor class provides production-grade orchestration:

[DIAGRAM: Batch Processor Architecture]

```
  INPUT: List of documents (up to 1000+)
              |
              v
  +------------------------+
  | BATCH PROCESSOR         |
  |                         |
  | ThreadPoolExecutor      |
  | (1-5 concurrent workers)|
  |                         |
  | Per-worker pipeline:    |
  | classify -> extract ->  |
  | embed -> store          |
  |                         |
  | Rate limiting:          |
  | - LLM: 1 call/sec      |
  | - Embeddings: 5 calls/s |
  |                         |
  | Retry: exponential      |
  | backoff (base 2s, max 3)|
  +----------+--------------+
             |
    +--------+--------+
    |        |        |
    v        v        v
 progress  state    report
 .json     .json    .json
 (live)   (resume) (final)
```

**Resumability:** If processing is interrupted (crash, Ctrl+C, timeout), the batch can be resumed from where it left off. The processor saves its state atomically to `batch_state.json` after each item, tracking which document IDs have been processed. On resume, it loads this state and skips already-processed items.

---

## 5. Database Schema

The database consists of 8 application tables plus 1 Alembic migration tracking table. The central entity is the `tools` table, which stores all tool metadata and vector embeddings.

[DIAGRAM: Entity Relationship Diagram]

```
  +-------------------+        +-------------------+
  | prompt_versions   |        | prompt_eval_      |
  | (LLM prompts)     |------>| results            |
  | id (PK)           |  1:N  | (evaluation data)  |
  | prompt_name       |        | prompt_version_id  |
  | version           |        | is_correct         |
  | prompt_text       |        | score              |
  | is_active         |        | latency_ms         |
  +-------------------+        +-------------------+

  +-------------------+        +-------------------+
  |      tools        |------->| user_ratings      |
  | (core entity)     |  1:N   | (1-5 stars)       |
  | id (PK, UUID)     |        | tool_id (FK)      |
  | title             |        | user_identifier   |
  | summary           |        | rating (1-5)      |
  | what_it_does      |        +-------------------+
  | when_to_use_it    |
  | who_its_for       |        +-------------------+
  | pillars[]         |------->| tool_views        |
  | domains[]         |  1:N   | (view tracking)   |
  | type              |        | tool_id (FK)      |
  | stage             |        | session_id        |
  | target_users[]    |        | referrer          |
  | geography[]       |        +-------------------+
  | embedding (1536d) |
  | average_rating    |
  | view_count        |        +-------------------+
  | cgspace_id (UQ)   |        | search_logs       |
  | is_visible        |        | (search tracking) |
  +-------------------+        | query_text        |
                               | query_type        |
  +-------------------+        | filters_used      |
  | user_sessions     |        | results_count     |
  | (session tracking)|        +-------------------+
  | session_id (UQ)   |
  | user_email        |        +-------------------+
  | user_agent        |        | email_captures    |
  +-------------------+        | (lead capture)    |
                               | email (UQ)        |
                               +-------------------+
```

### Index Strategy

The database uses specialized indexes optimized for different query patterns:

| Index Type | Used For | Columns |
|------------|----------|---------|
| HNSW (pgvector) | Semantic similarity search | embedding (vector_cosine_ops, m=16, ef=64) |
| GIN (array) | Pillar/domain/geography filtering | pillars, domains, target_users, geography |
| GIN (full-text) | Keyword search | to_tsvector(title + summary) |
| B-tree | Type/stage exact matching | type, stage |

---

## 6. API Architecture

The backend exposes 18 REST API endpoints organized into 6 functional groups. All endpoints return JSON responses and accept JSON request bodies where applicable.

[DIAGRAM: API Endpoint Map]

```
  FastAPI Application (port 8099)
  |
  +-- /health                          GET    [Public]  Health check
  |
  +-- /api/search/
  |   +-- /semantic                    POST   [Public]  Vector similarity search
  |   +-- /catalog                     POST   [Public]  Faceted catalog search
  |
  +-- /api/chat                        POST   [Public]  AI conversation
  |
  +-- /api/tools/
  |   +-- /{id}                        GET    [Public]  Tool detail
  |   +-- /{id}/rate                   POST   [Public]  Submit rating
  |   +-- /{id}/ratings               GET    [Public]  Get rating stats
  |
  +-- /api/metrics                     GET    [Public]  Platform metrics
  |
  +-- /api/prompts/
  |   +-- /                            GET    [Public]  List all prompts
  |   +-- /{name}/active               GET    [Public]  Active prompt
  |   +-- /                            POST   [Public]  Create prompt version
  |   +-- /{id}/activate               PUT    [Public]  Activate prompt
  |
  +-- /api/admin/
      +-- /login                       POST   [Public]  Get auth token
      +-- /tools                       GET    [Auth]    List all tools
      +-- /tools                       POST   [Auth]    Create tool
      +-- /tools/{id}                  PUT    [Auth]    Update tool
      +-- /tools/{id}                  DELETE [Auth]    Delete tool
```

### Cross-Cutting Concerns

**Session Tracking:** All requests pass through SessionMiddleware, which extracts an X-Session-ID header. Search events, tool views, and chat interactions are logged asynchronously via BackgroundTasks, ensuring tracking never slows down the user-facing response.

**CORS:** Configured to allow requests from the frontend domains.

**Error Handling:** Standard FastAPI exception handlers return structured error responses with appropriate HTTP status codes.

---

## 7. Search Architecture

The application supports two distinct search paradigms: semantic search (AI-powered similarity matching) and catalog search (traditional faceted filtering).

### Semantic Search Flow

[DIAGRAM: Semantic Search Flow]

```
  User query: "tools for gender-responsive M&E"
                    |
                    v
            OpenAI API call
            text-embedding-3-small
                    |
                    v
            1536-dim query vector
                    |
                    v
        pgvector HNSW index scan
        cosine distance (<=>)
        92 tool embeddings
                    |
                    v
        Similarity = 1 - distance
        Filter: similarity >= 0.3
        Order: highest similarity first
        Limit: top 10
                    |
                    v
        Ranked results with scores
        e.g., WEAI Toolkit (0.49),
        Gender Value Chains (0.54)
```

### Catalog Search with Cross-Filter Facets

[DIAGRAM: Catalog Search with Facets]

```
  User applies filters:
  Pillar = "MEL", Domain = "Climate"
              |
              v
    Build dynamic WHERE clause
    is_visible = true
    AND pillars && '{MEL}'
    AND domains && '{Climate}'
              |
              v
    +-------- Execute 3 queries --------+
    |              |                     |
    v              v                     v
  Count          Paginated           Facet counts
  total          results             (cross-filter)
  matching       (LIMIT/OFFSET)
                                     For each dimension:
                                     apply ALL OTHER filters
                                     but NOT this dimension's
                                     filter, then count values
              |
              v
    Response: {
      total: 8,
      results: [...],
      facets: {
        pillars: {MEL: 8, GESI: 3, ...},
        domains: {Climate: 8, Agri: 5, ...},
        type: {Framework: 3, Tool: 2, ...}
      }
    }
```

The cross-filter facet approach ensures users always see accurate counts of what they would find if they toggled a specific filter, preventing "dead end" filter combinations.

---

## 8. AI Chat Conversation Flow

The conversational AI system uses a multi-turn architecture where Claude serves as an intelligent intermediary between the user and the tool database.

[DIAGRAM: AI Chat Multi-Turn Flow]

```
  User: "I need tools for monitoring
         agricultural programs in Africa"
              |
              v
  +-- TURN 1: Clarifying Questions ----+
  |                                     |
  |  System prompt instructs Claude to  |
  |  ask 2-3 clarifying questions about |
  |  context, geography, stakeholders   |
  |                                     |
  |  Claude: "Could you tell me:        |
  |  1) Your role and organization?     |
  |  2) Which specific programs?        |
  |  3) Key M&E challenges?"           |
  +-------------------------------------+
              |
              v
  User: "We're an INGO working with
         smallholder farmers in East Africa,
         need both qualitative and quantitative
         evaluation methods"
              |
              v
  +-- TURN 2: Search + Recommend ------+
  |                                     |
  |  Claude outputs search trigger:     |
  |  <!--SEARCH:{"query": "monitoring   |
  |  evaluation smallholder agriculture  |
  |  East Africa qualitative methods"}-->|
  |                                     |
  |  Backend detects trigger, runs      |
  |  semantic search (top 8 results)    |
  |                                     |
  |  Results injected back as context   |
  |  Second LLM call generates          |
  |  personalized recommendations       |
  |                                     |
  |  Response includes:                 |
  |  - Text explanation of each tool    |
  |  - tools_recommended[] (top 5)      |
  |  - ToolCarousel renders in UI       |
  +-------------------------------------+
```

The key innovation is the **search trigger pattern**: the LLM is instructed to output a specially formatted comment (`<!--SEARCH:{"query":"..."}-->`) when it has gathered enough context. The backend detects this pattern, executes a semantic search, and feeds the results back to the LLM for a second pass that generates contextual recommendations. This two-pass approach ensures recommendations are both semantically relevant and personalized to the user's specific context.

---

## 9. User Journey Maps

### Journey 1: AI-Guided Discovery

This is the primary user journey, designed for practitioners who know their problem but not which tools exist.

[DIAGRAM: AI-Guided Discovery User Journey]

```
  DISCOVER                    EXPLORE                    ACT
  --------                    -------                    ---

  Land on         Start       AI asks        Answer      View tool
  homepage  --->  chat   ---> clarifying --> questions -> recomm-
  (hero +         with        questions      with        endations
  metrics)        query                      context     (carousel)
                                                            |
                                                            v
                                                      Click tool
                                                      card
                                                            |
                                                            v
                                                      Detail panel
                                                      slides in:
                                                      - What it does
                                                      - When to use
                                                      - Who it's for
                                                      - Taxonomy tags
                                                            |
                                                            v
                                                      Rate tool ----> Email
                                                      (1-5 stars)    capture
                                                            |         modal
                                                            v         (after 2
                                                      Visit           tool
                                                      resource        views)
                                                      (external
                                                      link)
```

### Journey 2: Catalog Browsing

For users who prefer a structured, self-directed search experience.

[DIAGRAM: Catalog Browsing User Journey]

```
  BROWSE                      FILTER                     EXPLORE
  ------                      ------                     -------

  Navigate        See all     Apply         Results      Click
  to         ---> 92 tools -> pillar   ---> narrow  ---> tool
  /catalog        in grid     filter        (e.g.,       card
                  + sidebar   (checkbox)    20 tools)       |
                                                            v
                              Apply         Results      Detail
                              domain   ---> narrow       panel
                              filter        further      (same as
                              (stacks)      (e.g.,       AI journey)
                                            8 tools)        |
                              Change                        v
                              sort  ------> Reorder      Rate and
                              (date/        results      explore
                              rating)
```

### Journey 3: Admin Content Management

For administrators who manage the tool database without developer intervention.

[DIAGRAM: Admin Management Flow]

```
  AUTHENTICATE                MANAGE                     VERIFY
  ------------                ------                     ------

  Navigate        Login       View tool     Create/      Verify
  to         ---> with   ---> table    ---> Edit    ---> changes
  /admin          admin       (92 tools,    tool         in public
                  credentials  sortable,    (modal       catalog
                              searchable)   form)
                                   |
                                   v
                              Delete tool
                              (with
                              confirmation,
                              cascades
                              ratings)
```

---

## 10. AWS Infrastructure Architecture

The application runs on AWS in the eu-central-1 (Frankfurt) region, deployed across 4 CloudFormation stacks with automated CI/CD.

[DIAGRAM: AWS Infrastructure]

```
  GITHUB REPOSITORY
  (Smith-synapsis-ai/ee-toolbox-app)
          |
          | Push to main
          v
  GITHUB ACTIONS CI/CD
  (OIDC authentication)
          |
          | Deploy via CloudFormation
          v
  +------ AWS ACCOUNT (Sandbox) ------+
  |                                    |
  |  Route 53 DNS                      |
  |  *.synapsis-analytics.com          |
  |       |              |             |
  |       v              v             |
  |  CloudFront     Application        |
  |  (Amplify CDN)  Load Balancer      |
  |       |         (ALB, HTTPS)       |
  |       |              |             |
  |       v              v             |
  |  AWS Amplify    ECS Fargate        |
  |  (React SPA)    (FastAPI           |
  |  ee-toolbox.     container)        |
  |  synapsis-       api-ee-toolbox.   |
  |  analytics.com   synapsis-         |
  |                  analytics.com     |
  |                      |             |
  |                      v             |
  |                 RDS PostgreSQL      |
  |                 16 + pgvector       |
  |                 (db.t4g.micro)      |
  |                      |             |
  |                 Secrets Manager     |
  |                 (DB + API creds)    |
  |                                    |
  |  ECR Repository                    |
  |  (Docker images)                   |
  |                                    |
  |  CloudWatch Logs                   |
  |  (14-day retention)                |
  +------------------------------------+
```

### Security Architecture

[DIAGRAM: Network Security Chain]

```
  Internet
      |
      v
  ALB Security Group
  (Ingress: 80, 443 from 0.0.0.0/0)
      |
      v
  ECS Security Group
  (Ingress: 8099 from ALB SG only)
      |
      v
  RDS Security Group
  (Ingress: 5432 from ECS SG only)
```

Each layer only accepts traffic from the layer directly above it. The RDS instance is not publicly accessible and has no direct internet connectivity. All secrets (database credentials, API keys) are stored in AWS Secrets Manager and injected as environment variables into the ECS task definition.

### CI/CD Pipeline

[DIAGRAM: CI/CD Pipeline Steps]

```
  Push to main
      |
      v
  1. Checkout code
  2. OIDC auth to AWS
  3. Build frontend (npm ci + build)
  4. Clean up any failed stacks
  5. Deploy database stack (CloudFormation)
  6. Build + push Docker image to ECR
  7. Deploy application stack (CloudFormation)
  8. Force new ECS deployment
  9. Wait for backend health (poll /health, up to 8 min)
  10. Seed database (run ECS task)
  11. Deploy frontend stack (CloudFormation)
  12. Upload frontend to Amplify
  13. Print deployment summary with URLs
```

The pipeline is fully automated and uses OIDC federation (no static AWS credentials). A push to the main branch triggers the entire build-test-deploy cycle.

---

## 11. Taxonomy Framework

The Enabling Environments framework organizes tools across multiple classification dimensions, allowing users to find tools relevant to their specific context.

[DIAGRAM: Taxonomy Framework - Pillars and Domains]

```
                    ENABLING ENVIRONMENTS TOOLBOX
                    Taxonomy Classification System

  PILLARS (thematic focus areas):
  +--------------------+  +--------------------+  +--------------------+
  | Gender Equality    |  | Monitoring,        |  | Policy and         |
  | and Social         |  | Evaluation and     |  | Regulatory         |
  | Inclusion (GESI)   |  | Learning (MEL)     |  |                    |
  +--------------------+  +--------------------+  +--------------------+
  +--------------------+  +--------------------+
  | Market             |  | Digital and        |
  | Systems            |  | Financial Services |
  +--------------------+  +--------------------+

  DOMAINS (cross-cutting application areas):
  +--------------------+  +--------------------+  +--------------------+
  | Agri-food          |  | Scaling            |  | Climate            |
  | Systems            |  | Innovation         |  | Resilience         |
  +--------------------+  +--------------------+  +--------------------+

  TYPES (10):  Method | Framework | Manual | Toolkit | Tool |
               Guide | Matrix | Scorecard | Brief | Scale

  STAGES (4): Established | Prototype | Theoretical | Conceptual

  GEOGRAPHY (8): Global | Africa | Asia | MENA |
                 Latin America | Europe | LMICs | CWANA
```

Each tool can belong to multiple pillars, multiple domains, and serve multiple geographic regions, while having a single type and maturity stage. This multi-dimensional classification enables rich filtering and discovery.

---

## 12. Frontend Page Architecture

The frontend consists of 5 main pages with shared components for navigation, tool details, and user engagement.

[DIAGRAM: Frontend Page Map and Component Architecture]

```
  +------- SHARED LAYOUT -------+
  | Header (navigation bar)     |
  | Skip-to-content link (a11y) |
  +-----------------------------+
           |
  +--------+--------+--------+--------+--------+
  |        |        |        |        |        |
  v        v        v        v        v        v
 HOME    CATALOG   ABOUT   TUTORIAL  ADMIN   EMAIL
 PAGE    PAGE      PAGE    PAGE      PAGE    MODAL
  |        |                  |        |     (global)
  |        |                  |        |
  v        v                  v        v
 Hero    Filter    (static)  FAQ     Login
 Section Sidebar             Accord- Form
  |      + Grid              ion      |
  v        |                          v
 Chat      v                        Tool
 Inter-  Catalog                    Table
 face    Results                    + CRUD
  |      + Pagination               Modal
  v
 Tool      +--- SHARED COMPONENTS ---+
 Carousel  | ToolDetailPanel         |
  |        | StarRating              |
  v        | TypeBadge               |
 Tool      | LoadingSpinner          |
 Cards     +--------------------------+
```

### Accessibility Features

The application implements WCAG AA accessibility standards:
- Skip-to-content link for keyboard navigation
- aria-label on all interactive elements (25 instances across 14 files)
- role="dialog" on all 3 modal/overlay components
- aria-expanded on collapsible elements (FAQ, filters, mobile menu)
- Focus trap in EmailCaptureModal with Tab key cycling
- Escape key handling on all overlay panels
- prefers-reduced-motion media query to disable animations
- WCAG AA contrast ratios verified on all text

---

## 13. Local Development Environment

For local development and testing, the application runs with Docker-managed PostgreSQL and local development servers.

[DIAGRAM: Local Development Setup]

```
  DEVELOPER MACHINE
  +------------------------------------------+
  |                                          |
  |  Docker Container (port 5433)            |
  |  +------------------------------------+  |
  |  | PostgreSQL 16 + pgvector           |  |
  |  | Database: ee_toolbox               |  |
  |  | 92 tools with embeddings           |  |
  |  +------------------------------------+  |
  |           ^                              |
  |           |                              |
  |  Backend (port 8099)                     |
  |  +------------------------------------+  |
  |  | FastAPI + uvicorn                  |  |
  |  | cd backend && uvicorn app.main:app |  |
  |  +------------------------------------+  |
  |           ^                              |
  |           |                              |
  |  Frontend (port 5173)                    |
  |  +------------------------------------+  |
  |  | React + Vite dev server            |  |
  |  | cd frontend && npm run dev         |  |
  |  +------------------------------------+  |
  |                                          |
  +------------------------------------------+

  Quick start:
  1. docker compose up -d        (database)
  2. cd backend && uvicorn ...   (API)
  3. cd frontend && npm run dev  (UI)
```

---

## 14. Key URLs and Access Points

| Resource | URL | Notes |
|----------|-----|-------|
| Frontend (live) | https://ee-toolbox.synapsis-analytics.com | Production SPA |
| Frontend (Amplify) | https://main.d15pb16eb2gi8i.amplifyapp.com | Default Amplify URL |
| Backend API (live) | https://api-ee-toolbox.synapsis-analytics.com | Production API |
| API Health Check | https://api-ee-toolbox.synapsis-analytics.com/health | Should return {"status":"ok"} |
| Swagger Docs | https://api-ee-toolbox.synapsis-analytics.com/docs | Interactive API documentation |
| Admin Panel | https://ee-toolbox.synapsis-analytics.com/admin | Login: admin / admin123 |
| GitHub Repository | https://github.com/Smith-synapsis-ai/ee-toolbox-app | Source code |
| Frontend (local) | http://localhost:5173 | Development server |
| Backend (local) | http://localhost:8099 | Development server |
| Database (local) | localhost:5433 | PostgreSQL via Docker |

---

## 15. Verification Status

The application has been verified across 6 areas with 42 individual checks:

| Area | Checks | Result |
|------|--------|--------|
| Pipeline at Scale | 4/4 | All Pass |
| AWS Infrastructure | 9/9 | All Pass |
| Admin Panel CRUD | 7/7 | All Pass |
| About and Tutorial Pages | 3/3 | All Pass |
| Accessibility | 8/8 | All Pass |
| End-to-End User Journey | 10/10 | All Pass |
| Backend API Endpoints | 10/10 | All Pass |
| **Total** | **51/51** | **All Pass** |

All CloudFormation stacks are healthy. SSL certificates are valid through late 2026. Local and live environments show full data parity (92 tools, identical metrics).
