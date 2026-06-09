# Enabling Environments Toolbox -- Executive Summary

**Date:** May 2026 | **Status:** Live in Production | **Prepared for:** CGIAR Leadership

---

## What It Is

The Enabling Environments Toolbox is an AI-powered web platform that helps agricultural development practitioners discover tools, frameworks, and methods for scaling innovation. Users can find relevant resources through conversational AI search, semantic (meaning-based) search, or traditional catalog browsing -- all backed by a curated and continuously expanding database of tools classified within the CGIAR Enabling Environments framework.

## Key Capabilities

- **AI-guided discovery** -- Users describe their needs in plain language; the system asks clarifying questions and returns personalized tool recommendations
- **Semantic search** -- Finds tools by meaning rather than keywords, surfacing relevant results even when terminology differs
- **Faceted catalog** -- Browse and filter all tools by thematic pillar, domain, type, maturity stage, geography, and target user
- **Analytics dashboard** -- Tracks engagement metrics (searches, views, ratings, user pathways) for reporting and optimization
- **Admin panel** -- Domain experts can add, edit, and remove tools through a visual interface without developer support
- **Automated data pipeline** -- Processes large document collections from CGSpace, classifying relevance and extracting metadata using AI, ready to scale to 41,000+ items

## Current Status

The platform is live and accessible:

- **Frontend:** https://ee-toolbox.synapsis-analytics.com
- **API:** https://api-ee-toolbox.synapsis-analytics.com
- **Admin Panel:** https://ee-toolbox.synapsis-analytics.com/admin
- **92 tools** loaded with full metadata, taxonomy classifications, and vector embeddings
- **51 of 51** verification checks passed across infrastructure, accessibility, API, and end-to-end user journeys

## Key Metrics

| Metric                        | Value         |
|-------------------------------|---------------|
| Classification accuracy       | 100%          |
| Tools loaded                  | 92            |
| API endpoints                 | 30            |
| Semantic search response time | ~596ms        |
| Catalog search response time  | 10--45ms      |
| Codebase size                 | ~21,800 lines |
| Accessibility standard        | WCAG AA       |

## What's Ready for the Team

- **Ojong** can manage tool content through the admin panel and review pipeline-flagged items for quality assurance
- **Samuel** can run the full 41,000-item CGSpace dataset through the pipeline; the system auto-publishes high-confidence items and flags borderline ones for expert review
- **Taisa** can use the analytics dashboard for stakeholder reporting and needs to provide final content (team bios, hero images, tutorial material)

## Next Steps

1. **Repository and IAM setup** -- Transfer the repo to the JLBKMVE GitHub organization and provision deploy roles in all four AWS accounts (DEV, TST, PRD)
2. **Full data ingestion** -- Run the 41,000-item CGSpace dataset through the classification and enrichment pipeline
3. **Content finalization** -- Team provides About page bios, tutorial content, and hero images
4. **Production migration** -- Move from the Sandbox account to the Production account with multi-environment CI/CD (develop to DEV, staging to TST, main to PRD)

## Architecture at a Glance

Users access a React web application hosted on AWS Amplify, which communicates with a FastAPI backend running on AWS ECS Fargate. The backend queries a PostgreSQL database with vector search capabilities (pgvector) for semantic matching and uses Anthropic Claude for AI-guided conversations. A separate data pipeline uses AI to classify, extract metadata from, and generate embeddings for source documents, storing them as searchable tool records. The entire infrastructure is defined as code (CloudFormation) and deployed automatically through GitHub Actions.

---

*Synapsis Analytics | May 2026*
