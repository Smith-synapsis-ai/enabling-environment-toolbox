# Tool Provenance Report: Enabling Environments Toolbox

**Date:** 2026-05-26
**Database:** 92 tools in `ee_toolbox.tools` table
**Data source code:** `pipeline/bulk_load.py` (initial commit 63e2acd)
**Seed snapshot:** `data/seed.sql` (pg_dump committed at 970b866)

---

## Executive Summary

**None of the 92 tools are "real" database records scraped or imported from actual repositories.** All 92 were authored by an AI agent (Claude) during the initial build of the EE Toolbox application. They fall into three tiers of authenticity:

| Category | Count | Description |
|----------|-------|-------------|
| A. Inspired by real tools | ~22 | Named after real CGIAR/international tools; real author names; plausible organizations; BUT fabricated URLs and AI-written metadata |
| B. Plausible composites | ~24 | Titles and organizations reference real entities but tool does not map 1:1 to a real publication; fabricated URLs |
| C. Purely generated | 46 | Hardcoded in `generate_additional_items()` in `bulk_load.py`; entirely fabricated to fill taxonomy gaps |

**Key finding:** ALL metadata (summary, what_it_does, when_to_use_it, who_its_for) across all 92 tools was authored by the AI agent that built the application. None of it was extracted from real documents via the LLM extraction pipeline.

---

## How the 92 Tools Were Created

### Data loading pipeline

The file `pipeline/bulk_load.py` (line 2 docstring) states explicitly:

> "Loads 34 tools + 12 stories from the v2 PoC data and generates ~45
> additional realistic items to achieve 90+ tools with full metadata
> and embeddings."

The loading process in `main()` works as follows:

1. **Load v2 data** from `/tmp/v2_items.json` -- a JSON file containing tools and stories from a prior "v2 proof-of-concept" application
2. **Map v2 tools** (34 items) through `map_v2_tool()` which translates v2 field names to the new schema
3. **Map v2 stories** (12 items) through `map_v2_story()` -- these become type="Brief" with no source_url
4. **Generate 46 additional items** via `generate_additional_items()` -- a function containing ~850 lines of hardcoded Python dicts
5. **Insert all 92 items** into the database with upsert
6. **Generate embeddings** for all 92 using OpenAI text-embedding-3-small

### The v2 PoC data (`/tmp/v2_items.json`)

This file is NOT in the repository. It was a transient file loaded during the initial database population. Based on the mapping code:

- **v2 tools** (34 items): Had fields like `fullDescription`, `keyFeatures`, `howToUse`, `pillars`, `enablers`, `regions`, `type`, `stage`, `year`, `url`, `authors`, `source`, `aiSummary`
- **v2 stories** (12 items): Had fields like `description`, `subtitle`, `innovationType`, `fullNarrative`, `keyOutcomes`, `lessonsLearned`, `region`, `year`

The v2 data itself was also AI-generated for a prior proof-of-concept. Evidence:
- The `source_organization` field for most v2 tools is "CG Space" (a generic label, not a real org name)
- Many URLs use the pattern `https://cgspace.cgiar.org/<slug>` (e.g., `/scaling-scan`, `/gender-transformative`) which are NOT real CGSpace handle URLs (real ones use `/handle/NNNNN/NNNNN` or `/items/UUID`)
- The `what_it_does` and `when_to_use_it` fields for v2 tools were derived mechanically from `keyFeatures` and `howToUse` arrays using string joins, not from the LLM extraction pipeline

### The seed.sql file

`data/seed.sql` is a `pg_dump` of the database after `bulk_load.py` was run. It was committed to git to enable Docker deployment without re-running the bulk load. It contains the same 92 tools.

---

## Category A: Inspired by Real Tools (~22 tools)

These tools are named after real, well-known CGIAR or international development tools. The author names are real people or real organizations. However, the URLs are fabricated (do not resolve to the actual tool pages), and the metadata text was written by the AI.

### Examples with verification:

| Tool | Real? | Author accuracy | URL status |
|------|-------|----------------|------------|
| Scaling Scan | YES - real CIMMYT tool | Larry Cooley & Johannes Linn are real (Co-Chairs of Scaling CoP) | `cgspace.cgiar.org/scaling-scan` returns 404 |
| Scaling Readiness Assessment | YES - real CGIAR approach | Marc Schut & Cees Leeuwis are the real developers at Wageningen/CGIAR | `cgspace.cgiar.org/scaling-readiness` returns 404 |
| Land Governance Assessment Framework | YES - real World Bank tool (LGAF) | Klaus Deininger is the real lead author | `worldbank.org/lgaf` returns 200 (but URL path is simplified) |
| Gender Transformative Approach Framework | YES - real CGIAR framework | Rhiannon Pyburn & Anouka van Eerdewijk are real researchers at KIT | `cgspace.cgiar.org/gender-transformative` returns 404 |
| Farmer Field School Implementation Guide | YES - real FAO program | FAO Plant Production division is correct | `fao.org/farmer-field-schools` returns 200 |
| Women's Empowerment in Agriculture Index (WEAI) Toolkit | YES - real IFPRI index (since 2012) | IFPRI & USAID Feed the Future are correct | `cgspace.cgiar.org/weai-toolkit` returns 404 |
| Participatory Rural Appraisal Toolkit | YES - PRA is a real methodology | Robert Chambers is the real pioneer | `cgspace.cgiar.org/pra-toolkit` returns 404 |
| Climate-Smart Policy Toolkit | PARTIAL - CSA is a real FAO program | FAO CSA Unit & CCAFS are real | `fao.org/climate-smart-agriculture` returns 200 (generic page) |

### Full list of Category A tools (v2 tools with real-world referents):

1. Scaling Scan
2. Scaling Readiness Assessment
3. Land Governance Assessment Framework
4. Gender Transformative Approach Framework
5. Farmer Field School Implementation Guide
6. Participatory Rural Appraisal Toolkit
7. Climate-Smart Policy Toolkit
8. Value Chain Analysis Toolkit
9. Market Systems Analysis
10. Inclusive Agribusiness Model Canvas
11. MELIA Framework
12. Innovation Scaling Readiness Assessment
13. ICT4Ag Assessment Framework
14. Institutional Capacity Assessment
15. Integrated Pest Management Adoption Framework
16. Irrigation Governance Assessment
17. Seed System Development Toolkit
18. Watershed Management Framework
19. Gender-Responsive Plant Breeding Method
20. Climate Vulnerability Assessment Framework
21. Post-Harvest Loss Reduction Guide
22. Rural Advisory Services Assessment

### Key characteristic:
- Source organization is often "CG Space" (14 tools) -- a placeholder rather than the actual publishing org
- URLs use simplified slug patterns, not real CGSpace handle URLs
- Metadata text is well-written but not sourced from actual publications

---

## Category B: Plausible Composites (~24 tools)

These are v2 tools and stories that reference real organizations and topic areas but do not correspond 1:1 to specific published tools. They are composites or hypothetical entries.

### V2 tools with external URLs (12 tools):
These have URLs pointing to organization websites (not CGSpace), but the specific URL paths are fabricated:

1. Agricultural Finance Readiness Tool (worldbank.org/ag-finance-readiness - 404)
2. Agricultural Knowledge and Innovation Systems (AKIS) Toolkit (fao.org/akis-toolkit - 404)
3. Agricultural Mechanization Policy Toolkit (cimmyt.org/mechanization-policy - 404)
4. Agricultural Trade Policy Analyzer (ifad.org/trade-policy - 404)
5. Agroecology Transition Scorecard (fao.org/agroecology/scorecard - 404)
6. Bio-Fertilizer Scaling Approach (iita.org/biofertilizer-scaling - 404)
7. Community-Based Natural Resource Management Toolkit (ilri.org/cbnrm - 404)
8. Digital Agriculture Assessment Tool (worldbank.org/digital-agriculture - 404)
9. Food Safety Regulatory Assessment (ilri.org/food-safety - 404)
10. Nutrition-Sensitive Agriculture Framework (ifad.org/nutrition-sensitive - 403)
11. Policy Landscape Mapping Tool (ifad.org/policy-landscape - 404)
12. Small-Scale Aquaculture Governance Guidelines (worldfishcenter.org/governance - 200)

### V2 stories (12 items):
All have type="Brief", no source_url, and represent case-study narratives rather than tools:

1. Agricultural Finance Innovation in Southeast Asia
2. Bio-Fertilizer Scaling in West Africa
3. Climate Adaptation in the Sahel
4. Digital Extension Services in South Asia
5. Digital Market Access in Latin America
6. Gender-Inclusive Value Chains in West Africa
7. Irrigation Governance Reform in South Asia
8. Mechanization Policy in Southern Africa
9. Nutrition-Sensitive Agriculture in Bangladesh
10. Post-Harvest Technology Adoption in Sub-Saharan Africa
11. Seed System Reform in East Africa
12. Soil Health Monitoring in East Africa

---

## Category C: Purely Generated (46 tools)

These 46 tools are hardcoded as Python dicts in `bulk_load.py::generate_additional_items()` (lines 278-1121). The function's docstring states:

> "Generate ~45 additional realistic tool entries covering taxonomy gaps."

They were created to ensure the database had coverage across all:
- 5 pillars (Gender, MEL, Policy, Market, Digital)
- 3 domains (Agri-food, Scaling, Climate)
- 10 types (Method, Framework, Manual, Toolkit, Tool, Guide, Matrix, Scorecard, Brief, Scale)
- 4 stages (Established, Prototype, Conceptual, Theoretical)
- Multiple geographies (including underrepresented MENA, Europe, Latin America)

### Distinguishing characteristics:
- All use `cgspace.cgiar.org/<descriptive-slug>` URLs (all return 404)
- Organizations are real CGIAR centers and partners, but tool-org pairings are fabricated
- Author names are organizational units (e.g., "ILRI One Health Program", "IWMI Nutrition-Water Nexus Team") rather than individual researchers
- Metadata is the most detailed and consistent -- it was written specifically for this purpose

### Full list:

1. Women's Empowerment in Agriculture Index (WEAI) Toolkit
2. Inclusive Design Matrix for Agricultural Technologies
3. Youth Agripreneurship Assessment Scale
4. Social Inclusion Monitoring Toolkit
5. Outcome Harvesting for Agricultural Research Manual
6. Theory of Change Development Guide for Agricultural Programs
7. Contribution Analysis Framework for Agricultural Impact
8. Adaptive Management Toolkit for Agricultural Programs
9. Mobile Agricultural Advisory Services Design Manual
10. Digital Financial Services for Agriculture Guide
11. Agricultural Data Governance Framework
12. Smallholder Market Access Scorecard
13. Agricultural Cooperative Strengthening Manual
14. Regulatory Impact Assessment for Agriculture
15. Multi-Stakeholder Platform Facilitation Guide
16. Climate-Smart Agriculture Prioritization Framework
17. Drought Resilience Assessment Tool
18. Greenhouse Gas Emissions Estimation Guide for Agriculture
19. Climate Services for Agriculture Toolkit
20. Innovation Portfolio Management Method
21. Public-Private Partnership Design Toolkit for Agriculture
22. Water-Energy-Food Nexus Assessment for MENA
23. Dryland Agriculture Transformation Guide
24. Saline Agriculture Adaptation Framework
25. Agri-Food Innovation Ecosystem Mapping Tool
26. Sustainable Intensification Assessment Framework
27. European Agricultural Knowledge Transfer Matrix
28. Indigenous Knowledge Integration Toolkit
29. Landscape Restoration Decision Support Tool
30. Food Systems Transformation Assessment Method
31. Behavioral Insights for Agricultural Technology Adoption
32. Regenerative Agriculture Transition Framework
33. One Health Approach for Agricultural Systems
34. Agricultural Extension Methods Comparison Matrix
35. Livestock Value Chain Gender Toolkit
36. Farmer Organization Maturity Scale
37. Nutrition-Sensitive Value Chain Manual
38. Agricultural Insurance Product Design Guide
39. Pastoralist Livelihood Resilience Scorecard
40. Foresight and Scenario Planning Toolkit for Agriculture
41. Sustainable Land Management Decision Brief
42. Aquaculture Sustainability Assessment Scorecard
43. Digital Literacy Assessment for Rural Communities
44. Conflict-Sensitive Agriculture Programming Guide
45. Participatory Varietal Selection Methodology
46. Nutrition-Sensitive Irrigation Toolkit

---

## Metadata Generation Analysis

### How metadata fields were populated:

| Field | Category A (v2 tools) | Category B (v2 stories) | Category C (generated) |
|-------|----------------------|------------------------|----------------------|
| summary | Joined from v2 `fullDescription` array (first 2 elements) | Composed from v2 `description` + `subtitle` + `innovationType` | Written directly in Python dict |
| what_it_does | Joined from v2 `keyFeatures` array with semicolons | Joined from v2 `fullNarrative` array (first 2 elements) | Written directly in Python dict |
| when_to_use_it | Joined from v2 `howToUse` array (first 3 elements) | Joined from v2 `keyOutcomes` array with semicolons | Written directly in Python dict |
| who_its_for | Derived by `_derive_who_its_for()` -- keyword matching on description text | Joined from v2 `lessonsLearned` array | Written directly in Python dict |
| pillars | Mapped from v2 pillar names via PILLAR_MAP | Mapped from v2 pillar names via PILLAR_MAP | Written directly |
| domains | Mapped from v2 enabler names via ENABLER_TO_DOMAIN | Mapped from v2 enabler names via ENABLER_TO_DOMAIN | Written directly |
| target_users | Inferred by `_infer_target_users()` from type + pillars | Inferred by `_infer_target_users()` from pillars | Written directly |
| geography | Mapped from v2 regions via REGION_MAP | Mapped from v2 regions via REGION_MAP | Written directly |
| type | Mapped from v2 type via TYPE_MAP | Hardcoded as "Brief" | Written directly |
| stage | Mapped from v2 stage via STAGE_MAP | Mapped from v2 stage via STAGE_MAP | Written directly |
| relevance_score | NULL (91 tools) or 0.95 (1 tool: Scaling Scan) | NULL | NULL |
| embedding | Generated via OpenAI text-embedding-3-small | Generated via OpenAI text-embedding-3-small | Generated via OpenAI text-embedding-3-small |

### Critical point about the LLM extraction pipeline:

The `pipeline/ingest.py` and `pipeline/extractor.py` modules implement a real LLM-based extraction pipeline that:
1. Classifies document relevance via Claude
2. Extracts structured metadata via Claude using the `metadata_extraction` prompt
3. Generates embeddings
4. Stores results

**However, this pipeline was NOT used for any of the 92 tools in the database.** Evidence:
- 91 of 92 tools have `relevance_score = NULL` (the ingest pipeline always sets this)
- The `bulk_load.py` script bypasses the ingest pipeline entirely -- it uses direct SQL INSERT
- The `generate_test_data.py` module generates synthetic items for *testing* the pipeline, not for populating the database

---

## URL Verification Summary

| URL Pattern | Count | HTTP Status |
|-------------|-------|-------------|
| `cgspace.cgiar.org/<slug>` (not real handles) | 57 | All return 404 |
| `www.<org>.org/<slug>` (external) | 20 | ~3 return 200, ~17 return 404/403 |
| `alliancebioversityciat.org/<slug>` | 3 | Return 403 |
| No URL (stories/briefs) | 12 | N/A |

Only ~3 of 80 URLs resolve successfully, and even those land on generic pages rather than the specific tool described.

---

## Conclusions

1. **All 92 tools are synthetic.** They were created by the AI agent that built the application to populate the database for demonstration purposes.

2. **~22 tools reference real-world tools** by name and author, making the database partially accurate in its catalog of known CGIAR tools. However, the descriptive metadata, URLs, and organizational attributions are fabricated.

3. **The metadata is high-quality but fabricated.** The summary, what_it_does, when_to_use_it, and who_its_for fields read like genuine tool descriptions, but they were written by the AI, not extracted from actual documents.

4. **The real ingestion pipeline was never used** for these tools. The architecture supports real document ingestion via LLM classification + extraction, but the current data bypasses it entirely.

5. **The v2 PoC data source** (`/tmp/v2_items.json`) is not in the repository and was also AI-generated content from a prior prototype.

6. **All URLs are broken.** The CGSpace slug-style URLs are not real CGSpace handle paths. The external organization URLs point to non-existent pages in most cases.
