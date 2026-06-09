# Frontend Build Task — Enabling Environment Toolbox

## Overview

Build a complete React + Vite + TypeScript + Tailwind CSS frontend for the CGIAR Enabling Environment Toolbox. The backend is running at `http://localhost:8099` with 92 tools loaded.

## Project Location

- Frontend root: `/Users/smithai/workspace/ee-toolbox-app/frontend/`
- Hero background image: `/Users/smithai/workspace/ee-toolbox-app/frontend/hero-bg.png` (copy to `public/` after scaffolding)
- CGIAR logo: Create a simple SVG or use text-based logo. The mockup shows a leaf icon + "CGIAR" text in white.

## Design Requirements (from mockups)

### Color Palette
- **Primary dark green:** `#1B3B2F` (very dark forest green, almost black-green) — used for overlays, headers
- **Secondary green:** `#2D5A3D` — for hover states, active elements
- **Accent green:** `#4CAF50` — for buttons, links, active states  
- **Dark overlay on hero:** rgba(20, 50, 35, 0.75) — semi-transparent dark green over the hero image
- **White text:** `#FFFFFF` for text on dark backgrounds
- **Light gray:** `#F5F5F5` for content area backgrounds
- **Card backgrounds:** White with subtle shadow
- **Type badge colors:** Different colors per tool type (e.g., Method=blue, Framework=green, Toolkit=orange, etc.)

### Typography
- Sans-serif font family (Inter or system fonts)
- Hero title: Large bold (~3rem), "Enabling Environment"
- Tagline: Lighter weight, "The tools, the cases, the science"

## Backend API Reference

All endpoints at `http://localhost:8099`:

### GET /api/metrics
Response: `{ total_tools: number, total_frameworks: number, geography_coverage: number, total_searches: number, avg_rating: number }`

### POST /api/chat
Request: `{ message: string, conversation_id?: string }`
Response: `{ conversation_id: string, message: string, tools_recommended: Array<{id: string, title: string, explanation: string, similarity: number}> | null, conversation_complete: boolean }`

### POST /api/search/catalog
Request: `{ pillars?: string[], domains?: string[], type?: string, stage?: string, target_users?: string[], geography?: string[], keyword?: string, page?: number, page_size?: number, sort_by?: "relevance"|"date"|"rating" }`
Response: `{ total: number, page: number, page_size: number, results: ToolSearchResult[], facets: { pillars: {}, domains: {}, type: {}, stage: {}, target_users: {}, geography: {} } }`

### POST /api/search/semantic
Request: `{ query: string, top_n?: number, min_similarity?: number }`
Response: `{ query: string, total_results: number, results: ToolSearchResult[] }`

### GET /api/tools/{id}
Response: Full ToolRead object with all fields.

### POST /api/tools/{id}/rate
Request: `{ rating: number (1-5), user_id: string }`

### GET /api/tools/{id}/ratings
Response: `{ tool_id: string, average: number, count: number, distribution: {"1": n, "2": n, "3": n, "4": n, "5": n} }`

### ToolSearchResult fields:
```
id, title, summary, what_it_does, when_to_use_it, who_its_for,
pillars: string[], domains: string[], type: string, stage: string,
target_users: string[], geography: string[], source_url: string,
cover_image_url: string | null, average_rating: number, rating_count: number,
similarity: number
```

### Full ToolRead fields (from GET /api/tools/{id}):
```
All ToolSearchResult fields plus:
authors: string[], date_published: string, source_organization: string,
cgspace_id: string, relevance_score: number, is_visible: boolean,
view_count: number, created_at: string, updated_at: string
```

## Pages & Components to Build

### 1. Homepage (`/`)

**Layout (matches mockup 1):**
- **Header:** Fixed top bar with CGIAR logo (left) and nav links (right): Home, About, Tutorial, Search by Catalog
- **Hero section:** Full-viewport height with:
  - Background image (`hero-bg.png`) with dark green overlay
  - Dot carousel navigation (bottom-right) for background image switching (just use the one image for now with placeholder dots)
  - Large white title "Enabling Environment" with a small grid icon
  - Tagline "The tools, the cases, the science"
  - Chat input bar centered: white rounded input with placeholder "Describe your project or problem. A few follow-up questions will help us find the most relevant tools and evidence." and a send button (circle with arrow)
  - Metrics bar at the very bottom: showing 3 stats from `/api/metrics` — "{total_tools} tools", "{total_frameworks} frameworks", "{geography_coverage} countries"

### 2. Chat Interface (overlays on homepage when user sends first message)

**Layout (matches mockup 2):**
- When user submits a message, the hero transforms:
  - Title/tagline move to top-left, smaller
  - Chat conversation appears on the LEFT side of the screen
  - Messages alternate: user messages (right-aligned, slightly lighter bg) and AI messages (left-aligned)
  - The AI will ask 2-3 clarifying questions before returning results
  - Chat input remains at the bottom
- When `tools_recommended` array is returned in the chat response:
  - Tool cards appear as a horizontal carousel on the RIGHT side
  - Cards show: cover image (or colored placeholder), type badge, title, truncated summary
  - Arrow buttons for carousel navigation
  - Clicking a card opens the detail panel

### 3. Tool Detail Panel (slide-in from right)

**Layout (matches mockup 3):**
- When a tool card is clicked, a detail panel slides in from the right (~60% width)
- The chat stays visible on the left (~40%)
- Detail panel contains:
  - Cover image at top (or large colored placeholder if no image)
  - Type badge (color-coded)
  - Tool title (large)
  - Summary paragraph
  - "What it does" section with content
  - "When to use it" section
  - "Who it's for" section
  - Action buttons: "Visit Resource" (links to source_url), "Share" (copy link)
  - Star rating widget (see below)
  - Close/back button (X in top-right, or back arrow)
- Fetch full tool data from `GET /api/tools/{id}`

### 4. Search by Catalog Page (`/catalog`)

**Layout:**
- Header (same as homepage)
- Left sidebar (~250px) with filter groups:
  - Keyword search input at top
  - Expandable filter sections for each taxonomy dimension:
    - **Pillars:** Gender Equality and Social Inclusion, Monitoring Evaluation and Learning, Policy and Regulatory, Market Systems, Digital and Financial Services
    - **Domains:** Agri-food Systems, Scaling Innovation, Climate Resilience
    - **Type:** Method, Framework, Manual, Toolkit, Tool, Guide, Matrix, Scorecard, Brief, Scale
    - **Stage:** Established and field-tested, Prototype, Theoretical and diagnostics, Conceptual
    - **Target Users:** (16 values — see taxonomy below)
    - **Geography:** Global, Asia, Africa, MENA, Latin America, Europe, Low-income and middle-income countries, CWANA
  - Each filter shows checkboxes with counts from facet data
  - "Clear filters" button
- Right content area:
  - Sort dropdown (relevance, date, rating)
  - Results count
  - Grid of tool cards (3 columns on desktop, 2 on tablet, 1 on mobile)
  - Each card: type badge, title, summary (truncated), pillars tags, rating stars
  - Clicking a card navigates to tool detail (can use a modal or dedicated route)
  - Pagination at bottom
- Connect to `POST /api/search/catalog`
- Filters update the request and re-fetch results
- Facet counts update dynamically from response

### 5. About Page (`/about`)

Simple content page with:
- Header
- Section explaining what Enabling Environment means
- The 5 pillars with descriptions
- The 3 domains with descriptions
- CGIAR attribution

### 6. Tutorial Page (`/tutorial`)

Simple page with:
- Header
- Placeholder for tutorial video (gray box with play icon)
- Step-by-step text guide:
  1. Describe your challenge
  2. Answer clarifying questions
  3. Browse recommended tools
  4. Explore tool details

### 7. Star Rating Widget

Component used in tool detail panel:
- 5 stars displayed
- Shows current average and count: "4.2 (15 ratings)"
- On hover, stars highlight up to the hovered star
- On click, submits rating via `POST /api/tools/{id}/rate`
- `user_id` can be a generated UUID stored in localStorage
- After submitting, refetch ratings from `GET /api/tools/{id}/ratings`
- Visual feedback: filled stars for average, highlighted on hover

### 8. Email Capture Modal

- Appears once per session (check sessionStorage for `email_captured` flag)
- Shows after 30 seconds or after viewing 2 tools (whichever comes first)
- Modal with:
  - "Stay updated on new tools and resources"
  - Email input with validation
  - Submit button
  - Close/dismiss button
- On submit: store in sessionStorage, close modal
- On dismiss: set sessionStorage flag so it doesn't reappear
- Dark green themed, matches overall design

## File Structure

```
frontend/
  public/
    hero-bg.png
  src/
    main.tsx
    App.tsx
    index.css               (Tailwind imports + custom styles)
    vite-env.d.ts
    services/
      api.ts                (ALL API calls centralized here)
    hooks/
      useChat.ts            (chat state management)
      useMetrics.ts         (metrics fetching)
      useCatalogSearch.ts   (catalog search state + filters)
    components/
      layout/
        Header.tsx
        Footer.tsx (optional)
      home/
        HeroSection.tsx
        MetricsBar.tsx
        BackgroundCarousel.tsx
      chat/
        ChatInterface.tsx
        ChatMessage.tsx
        ChatInput.tsx
        ToolCarousel.tsx
        ToolCard.tsx
      tool/
        ToolDetailPanel.tsx
        StarRating.tsx
      catalog/
        CatalogPage.tsx
        FilterSidebar.tsx
        FilterGroup.tsx
        CatalogResults.tsx
        Pagination.tsx
      common/
        TypeBadge.tsx       (color-coded tool type badge)
        LoadingSpinner.tsx
        EmailCaptureModal.tsx
    pages/
      HomePage.tsx
      AboutPage.tsx
      TutorialPage.tsx
      CatalogPage.tsx
    types/
      index.ts              (TypeScript interfaces matching API schemas)
  package.json
  tsconfig.json
  tsconfig.app.json
  vite.config.ts
  tailwind.config.js
  postcss.config.js
  index.html
```

## Type Badge Color Map

Use these colors for tool type badges:
- Method → `#2196F3` (blue)
- Framework → `#4CAF50` (green)
- Manual → `#FF9800` (orange)
- Toolkit → `#9C27B0` (purple)
- Tool → `#00BCD4` (cyan)
- Guide → `#795548` (brown)
- Matrix → `#607D8B` (blue-gray)
- Scorecard → `#F44336` (red)
- Brief → `#FFC107` (amber)
- Scale → `#E91E63` (pink)

## Technical Requirements

1. **Scaffold with Vite:** `npm create vite@latest . -- --template react-ts` (run inside `/Users/smithai/workspace/ee-toolbox-app/frontend/`)
2. **Install deps:** React Router (`react-router-dom`), Tailwind CSS v3 with PostCSS, `@heroicons/react` for icons, `lucide-react` as alternative icons
3. **API proxy:** Configure Vite proxy to forward `/api` to `http://localhost:8099` (avoids CORS issues in dev)
4. **No mock data:** ALL data comes from live API calls. The backend is running.
5. **Error handling:** Show user-friendly error messages when API calls fail. Loading spinners during fetches.
6. **Responsive:** Desktop (3-col grid), tablet (2-col), mobile (1-col). Chat/detail split works on desktop; on mobile, detail takes full screen.
7. **Session ID:** Generate a UUID on first visit, store in localStorage, send as `X-Session-ID` header on all API requests.
8. **Smooth animations:** Slide-in for detail panel (CSS transition), fade for modals.

## Taxonomy Values (for filter sidebar)

### Pillars (5)
- Gender Equality and Social Inclusion
- Monitoring, Evaluation and Learning
- Policy and Regulatory
- Market Systems
- Digital and Financial Services

### Domains (3)
- Agri-food Systems
- Scaling Innovation
- Climate Resilience

### Type (10)
Method, Framework, Manual, Toolkit, Tool, Guide, Matrix, Scorecard, Brief, Scale

### Stage (4)
- Established and field-tested
- Prototype
- Theoretical and diagnostics
- Conceptual

### Target Users (16)
Researcher, Policymaker, Development Practitioner, Extension services, Agribusiness, Local communities, Civil Society and INGOs, Funders and Donors, Private sector entities, Government agencies, Humanitarian assistance practitioners, Project and program managers, Farmers and Agro-pastoralists, Monitoring and Evaluation specialists, Community leaders, Irrigation scheme managers

### Geography (8)
Global, Asia, Africa, MENA, Latin America, Europe, Low-income and middle-income countries, Central and West Asia and North Africa (CWANA)

## Build Steps

1. Scaffold the Vite project in `/Users/smithai/workspace/ee-toolbox-app/frontend/`
2. Install all dependencies
3. Set up Tailwind CSS
4. Create all type definitions
5. Create the API service layer
6. Build all components and pages
7. Set up React Router
8. Wire up all API integrations
9. Verify `npm run dev` starts without errors
10. Verify the homepage loads correctly

## IMPORTANT NOTES

- The frontend directory already has `hero-bg.png` and `.gitkeep` — scaffold the Vite project around these (delete `.gitkeep`)
- Run ALL commands inside `/Users/smithai/workspace/ee-toolbox-app/frontend/`
- After scaffolding, move `hero-bg.png` into `public/`
- The backend is LIVE at http://localhost:8099 — use it
- Use Tailwind CSS v3 (not v4) for broader compatibility
- DO NOT use shadcn/ui or any component library — build custom components with Tailwind
