# QA Verification Task: Enabling Environments Toolbox

## App URL
Open Safari or Chrome to: http://localhost:5177/

## Context
This is a React/TypeScript web app (Vite + FastAPI backend). The frontend is at port 5177, and it proxies `/api` to the backend at port 8099. The database has 92 real tools loaded.

## Verification Steps - Take a screenshot at EACH step

### Step 1: Homepage Verification
1. Navigate to http://localhost:5177/
2. Take a screenshot
3. Verify visually:
   - Background image visible (farmer photo with dark green overlay)
   - Title "Enabling Environment" visible
   - A tagline/subtitle visible
   - Metrics bar at the bottom showing numbers (should say 92 tools, ~21 frameworks, 8 countries)
   - A chat input field present

### Step 2: Navigation Links
1. Look for navigation links: "Search by Catalog", "About", "Tutorial"
2. Click "About" link — take screenshot, verify page loads
3. Click browser back or use the logo to return home
4. Click "Search by Catalog" — take screenshot, verify catalog page loads
5. Click browser back to return home
6. Note if any links are missing or broken

### Step 3: AI Chat Flow (CRITICAL)
1. On the homepage, find the chat input field
2. Type: "I need tools to help smallholder farmers participate in policy processes"
3. Submit the message (press Enter or click send button)
4. WAIT for the AI response (may take 5-15 seconds) — take screenshot once response appears
5. The AI should respond with clarifying questions. Read them.
6. Type an answer like: "I'm working in East Africa, specifically Kenya and Tanzania. The farmers are organized in cooperatives and we need tools for the consultation and design phase."
7. Submit and WAIT for the response — take screenshot
8. Verify: Does the response include actual tool recommendations with real tool names? Are there tool cards shown?

### Step 4: Tool Detail Panel
1. If tool cards appeared in Step 3, click on one of them
2. If no tool cards appeared, go to the catalog page and click any tool card
3. Take a screenshot of the tool detail panel
4. Verify it shows:
   - Tool title
   - Type badge (e.g., "Toolkit", "Framework", "Guide")
   - Description/summary
   - "What it does" section
   - "When to use it" section
   - "Who it's for" section
   - Close button (X or similar)
5. Click the close button — verify panel closes

### Step 5: Search by Catalog (Faceted Search)
1. Navigate to the catalog page (click "Search by Catalog" or go to the catalog route)
2. Take a screenshot showing the full catalog page
3. Verify:
   - Filter sidebar visible with dimension categories (pillars, domains, type, stage, target users, geography)
   - Tool cards displayed in the main area
   - Result count shown
4. Click a pillar filter (e.g., "Policy & Governance") — take screenshot
   - Verify results update (count should decrease)
   - Verify facet counts change
5. Try the keyword search box — type "monitoring" and submit — take screenshot
   - Verify results filter to show relevant tools
6. Try combining: keep the pillar filter AND the keyword — verify it narrows further
7. Check if pagination or "Load more" exists if results > page size
8. Check if sort options are available

### Step 6: Rating Widget
1. Open any tool detail panel (from catalog)
2. Look for a star rating component (5 stars)
3. Take a screenshot showing the rating area
4. Click to give it a 4-star rating
5. Take screenshot after rating — verify it was accepted (no error, maybe a count updates)

### Step 7: Final Summary
Take one final screenshot of the homepage and report:
- Overall visual quality (does it look professional/polished?)
- Any broken elements, empty states, or error messages you noticed
- Any console errors visible

## IMPORTANT NOTES
- The app is at http://localhost:5177/ (NOT 5173)
- Wait patiently for AI chat responses — they use real LLM calls
- Take screenshots at every key point for documentation
- If something fails, document WHAT failed specifically
