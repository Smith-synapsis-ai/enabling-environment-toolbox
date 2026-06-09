# Task: Build CGIAR "Enabling Environment" (EE) Prototype React App

## Overview
Build a multi-page React web application that faithfully reproduces a Figma prototype for CGIAR's "Scaling for Impact" Enabling Environment Explorer. This is a knowledge platform that helps users explore tools, approaches, stories, and cases related to enabling environments for agricultural innovation scaling.

## Project Location
`/Users/smithai/workspace/ee-prototype/`

Images are already extracted to: `/Users/smithai/workspace/ee-prototype/public/images/`

## Tech Stack
- React 18+ with Vite
- React Router v6 for multi-page navigation
- Tailwind CSS for styling
- Lucide React for icons
- No backend needed — all data is hardcoded/mock

## Brand Identity (from Figma)
Based on the CGIAR "Scaling for Impact" visual identity:

### Colors
- **Primary Teal/Dark Green:** `#00524D` (header, primary buttons)
- **Primary Purple:** `#6B21A8` or similar (accent, "Scaling for Impact" label)
- **Light Teal:** `#E0F5F0` (tag backgrounds for change areas)
- **Light Purple:** `#F3E8FF` (tag backgrounds for impact areas)
- **Light Coral/Pink:** `#FCE4EC` (tag backgrounds for stages)
- **White:** `#FFFFFF` (card backgrounds)
- **Light Gray:** `#F8F9FA` (page background)
- **Dark Text:** `#1A1A2E` (headings)
- **Medium Text:** `#4A5568` (body text)
- **Green gradient** for map intensity: light mint → medium green → dark green → darkest green

### Typography
- Sans-serif font family (use Inter or system fonts)
- Clear hierarchy: large bold headings, medium subheadings, regular body

### Logo
- CGIAR logo is at: `public/images/cgiar-logo.png` (horizontal banner with wheat/grain icon, "CGIAR" text, and "SCALING FOR IMPACT" label)

## Pages to Build

### 1. Landing/Home Page (`/`)
**Header/Navbar:**
- Dark teal background (`#00524D`)
- CGIAR logo on the left
- Navigation links: Home, Explore, About
- Sticky header

**Hero Section:**
- Large hero image (use `hero-farmer.jpeg` or `hero-agriculture.jpeg`) with dark overlay
- Title: "Enabling Environment Explorer"
- Subtitle: "Discover tools, approaches, and real-world experiences for creating enabling environments that support agricultural innovation scaling across countries."
- CTA button: "Explore Tools & Cases" → links to /explore
- Secondary link: "Learn more about enabling environments"

**Key Stats Section:**
- Three stat cards in a row:
  - "8+ Tools & Approaches"
  - "6+ Stories & Cases"  
  - "20+ Countries"

**Featured Categories Section:**
- Title: "Explore by Change Area"
- Grid of 6 clickable cards for change areas:
  1. Policy & regulatory
  2. Digital & financial services
  3. Market access
  4. Monitoring, evaluation & learning
  5. Governance & coordination
  6. Gender and social inclusion
- Each card has a subtle teal/green gradient background and an icon

**Impact Areas Section:**
- Title: "Impact Areas"
- Three cards:
  1. Agri-food systems transformation
  2. Scaling innovation
  3. Climate resilience
- Each with a background image (use the agriculture photos) and overlay text

**Footer:**
- Dark teal background
- CGIAR logo
- Links: About, Contact, Terms, Privacy
- "© 2024 CGIAR Scaling for Impact"

### 2. Explorer Page (`/explore`) — THIS IS THE MAIN PAGE
This is the most detailed page, based on the high-resolution screenshot.

**Search Bar (top, full width):**
- Large search input with magnifying glass icon
- Placeholder: "Search by keyword, innovation, country, or challenge..."
- Functional filtering of results as user types

**Two-column layout below search:**

**Left column — "Explore by geography":**
- A simplified SVG world map showing colored markers/regions
- Legend: 1-6 (light mint), 7-12 (medium green), 13-20 (darker green), 20+ (darkest green)
- Caption: "Data based on curated CGIAR tools and documented reform experiences across countries."
- Clicking on a region could filter results (optional interactivity)

**Right column — "Filter results":**
- **Country or region** dropdown (default: "All countries") with options: All countries, Sub-Saharan Africa, South Asia, Southeast Asia, Latin America, East Africa, West Africa
- **Change areas** as toggleable tag/pill buttons (teal colored):
  - Policy & regulatory
  - Digital & financial services
  - Market access
  - Monitoring, evaluation & learning
  - Governance & coordination
  - Gender and social inclusion
- **Impact areas** as toggleable tag/pill buttons (green colored):
  - Agri-food systems transformation
  - Scaling innovation
  - Climate resilience
- **Type** dropdown: All types, Framework, Method, Tool, Approach
- **Stage** dropdown: All stages, Established and field-tested, Emerging, Conceptual

**Results Summary Bar:**
- "Showing **8** tools & approaches · **6** stories & cases · **20** countries in current view"
- Numbers should update dynamically based on active filters

**Tab Navigation:**
- Three tabs: "All" (active by default, with a dark teal pill), "Tools & approaches", "Stories & cases"

**Results Grid (3 columns):**
Cards should have:
- Type label (small caps, colored): "FRAMEWORK" (purple), "METHOD" (teal), "TOOL" (green), "APPROACH" (blue)
- Title (bold, large)
- Description (2-3 lines, gray text)
- Tags at bottom (colored pills matching change areas, impact areas, and stage)

**Mock Data — At least 8 tools and 6 stories:**

Tools & Approaches:
1. **Scaling Scan** (FRAMEWORK) — "Systematically assess readiness and potential of innovations to scale within agri-food systems." Tags: Policy & regulatory, Governance & coordination, Scaling innovation, Established and field-tested
2. **Policy Landscape Mapping** (METHOD) — "Visualize and analyze the policy ecosystem affecting agricultural innovation adoption and scaling." Tags: Policy & regulatory, Governance & coordination, Agri-food systems transformation, Established and field-tested
3. **Gender Transformative Approach Framework** (FRAMEWORK) — "Design and implement interventions that address root causes of gender inequality in agricultural systems." Tags: Gender and social inclusion, Policy & regulatory, Agri-food systems transformation, Established and field-tested
4. **Digital Agriculture Assessment Tool** (TOOL) — "Evaluate digital infrastructure readiness and identify opportunities for digital agricultural services." Tags: Digital & financial services, Market access, Scaling innovation, Emerging
5. **Market Systems Analysis** (METHOD) — "Map and understand market dynamics that influence agricultural innovation uptake and sustainability." Tags: Market access, Digital & financial services, Agri-food systems transformation, Established and field-tested
6. **Institutional Capacity Assessment** (FRAMEWORK) — "Evaluate organizational readiness and capacity gaps for scaling agricultural innovations." Tags: Governance & coordination, Monitoring evaluation & learning, Scaling innovation, Emerging
7. **Climate-Smart Policy Toolkit** (TOOL) — "Develop and evaluate policies that support climate-resilient agricultural practices." Tags: Policy & regulatory, Climate resilience, Established and field-tested
8. **Innovation Scaling Readiness Assessment** (APPROACH) — "Determine the readiness of innovations and enabling environments for scaling." Tags: Scaling innovation, Governance & coordination, Emerging

Stories & Cases:
1. **Seed System Reform in East Africa** — "How policy reforms and institutional partnerships enabled improved seed varieties to reach 2 million smallholder farmers." Image: crops-rows.jpeg. Tags: Policy & regulatory, Agri-food systems transformation, East Africa
2. **Digital Extension Services in South Asia** — "Leveraging mobile platforms to deliver agricultural advisory services to remote farming communities." Image: scientist-lab.jpeg. Tags: Digital & financial services, Scaling innovation, South Asia
3. **Gender-Inclusive Value Chains in West Africa** — "Transforming market access for women producers through policy advocacy and institutional support." Image: field-worker.jpeg. Tags: Gender and social inclusion, Market access, West Africa
4. **Climate Adaptation in the Sahel** — "Building enabling environments for climate-resilient agriculture through multi-stakeholder governance." Image: hero-farmer.jpeg. Tags: Climate resilience, Governance & coordination, Sub-Saharan Africa
5. **Soil Health Monitoring Network** — "Establishing national soil testing infrastructure to support evidence-based farming decisions." Image: soil-samples.jpeg. Tags: Monitoring evaluation & learning, Agri-food systems transformation, East Africa
6. **Agricultural Finance Innovation** — "Creating regulatory frameworks that enable fintech solutions for smallholder agricultural lending." Image: petri-dishes.jpeg. Tags: Digital & financial services, Market access, Southeast Asia

### 3. Detail Page (`/tool/:id` and `/story/:id`)

**For Tools/Approaches:**
- Breadcrumb: Home > Explore > [Tool Name]
- Type badge (FRAMEWORK/METHOD/TOOL/APPROACH)
- Title (large)
- Full description (3-4 paragraphs of lorem-style text about the tool)
- **"Key Features"** section with 3-4 bullet points
- **"How to Use"** section with numbered steps
- **"Change Areas"** tag pills
- **"Impact Areas"** tag pills
- **"Stage"** badge
- **"Related Tools"** section with 2-3 card previews of other tools
- Sidebar: "Countries where applied" with a mini list

**For Stories/Cases:**
- Hero image (full width, with overlay)
- Title and subtitle
- Author/Region info
- Full narrative text (3-4 paragraphs)
- "Key Outcomes" section
- "Lessons Learned" section
- Tags
- Related stories

### 4. About Page (`/about`)
- Hero with background image
- Title: "About the Enabling Environment Explorer"
- Description of the platform's purpose
- "What is an Enabling Environment?" section
- "Change Areas" explained (grid of 6 cards with descriptions)
- "Impact Areas" explained
- Contact/feedback section

## Key Behaviors
1. **Filtering should work**: When users click change area / impact area pills on the Explorer page, the results should filter in real-time
2. **Search should work**: The search bar should filter results by matching title and description text
3. **Tabs should work**: Switching between All / Tools & approaches / Stories & cases should filter the displayed cards
4. **Responsive**: The app should look good on desktop (1440px), tablet, and mobile
5. **Smooth transitions**: Use subtle animations for tab switching, card hover effects
6. **Tag pills should be interactive**: Clicking a tag anywhere should activate that filter on the Explorer page

## Image Mapping
Photos to use for cards and heroes (all in `public/images/`):
- `hero-agriculture.jpeg` — crops in rows with trees (use for hero backgrounds)
- `hero-farmer.jpeg` — farmer silhouette with hoe (use for hero backgrounds)
- `soil-samples.jpeg` — petri dishes with soil (use for story cards)
- `field-worker.jpeg` — person in green field (use for story cards)
- `lab-scientist.jpeg` — scientist with lab equipment (use for story cards)
- `test-tubes.jpeg` — plant test tubes (use for story cards)
- `crops-rows.jpeg` — crops in rows (use for story cards)
- `scientist-lab.jpeg` — scientist with device (use for story cards)
- `farmer-hoe.jpeg` — farmer with hoe (smaller version)
- `petri-dishes.jpeg` — close-up petri dishes (use for story cards)
- `cgiar-logo.png` — CGIAR Scaling for Impact logo banner

## Setup & Run
After building:
```bash
cd /Users/smithai/workspace/ee-prototype
npm install
npm run dev -- --port 5180 --host
```

The app should be accessible at http://localhost:5180

## Quality Standards
- Clean, well-organized component structure
- Proper TypeScript types (use .tsx files)
- All filters, search, and navigation must be functional
- Visually faithful to the CGIAR brand identity
- The explorer page must closely match the screenshot I described above
