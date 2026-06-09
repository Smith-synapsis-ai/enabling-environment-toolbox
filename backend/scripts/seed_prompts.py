"""Seed the prompt store with the three initial prompts from the EE Toolbox spec."""

import sys
from pathlib import Path

# Add backend dir to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from app.database import sync_engine, SyncSessionLocal
from app.models.prompt import PromptVersion

# ── Prompt texts (from spec Sections 4.3 and 6.3) ──

RELEVANCE_CLASSIFICATION_PROMPT = """\
You are an expert in agricultural development and enabling environments for innovation scaling.

Given the following document metadata from the CGIAR CG Space repository, determine whether this document is relevant to the Enabling Environment Toolbox.

The Enabling Environment Toolbox curates methods, frameworks, scorecards, manuals, toolkits, guides, briefs, scales, and matrices that help practitioners address enabling environment challenges in agricultural innovation scaling.

Relevant documents should be:
- Actionable tools, methods, or frameworks (not pure research papers or annual reports)
- Related to at least one of the 5 EE pillars: Gender & Social Inclusion, M&E & Learning, Policy & Regulatory, Market Systems, Digital & Financial Services
- OR related to at least one of the 3 impact domains: Agri-food Systems, Scaling Innovation, Climate Resilience
- Preferably concise and practical (short PDFs, guides, toolkits over lengthy academic reports)

DOCUMENT:
Title: {title}
Authors: {authors}
Date: {date}
Abstract: {abstract}
Document type: {doc_type}
URL: {url}

Respond with JSON:
{
  "relevant": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}"""

METADATA_EXTRACTION_PROMPT = """\
You are an expert in agricultural development and enabling environments for innovation scaling.

Given the following document, extract structured metadata for the Enabling Environment Toolbox catalog.

PILLAR DEFINITIONS:
1. Gender Equality and Social Inclusion: Tools that address barriers related to inclusion for marginalized groups.
2. Monitoring, Evaluation and Learning: Tools that address barriers related to feedback loops for iterative improvement.
3. Policy and Regulatory: Tools that reduce policy/institutional bottlenecks and guide innovations at scale.
4. Market Systems: Tools that address constraints to effective functioning of markets (actors, services, rules).
5. Digital and Financial Services: Tools that address barriers related to tech integration and financial access.

DOMAIN DEFINITIONS:
1. Agri-food Systems: Production, processing, distribution, and consumption of food/agricultural products.
2. Scaling Innovation: Adoption, expansion, and sustainability of innovations across systems and contexts.
3. Climate Resilience: Capacity to withstand, adapt to, and recover from climate risks.

TYPE OPTIONS: Method, Framework, Manual, Toolkit, Tool, Guide, Matrix, Scorecard, Brief, Scale
STAGE OPTIONS: Established and field-tested, Prototype, Theoretical and diagnostics, Conceptual
TARGET USER OPTIONS: Researcher, Policymaker, Development Practitioner, Extension services, Agribusiness, Local communities, Civil Society and INGOs, Funders and Donors, Private sector entities, Government agencies, Humanitarian assistance practitioners, Project and program managers, Farmers and Agro-pastoralists, Monitoring and Evaluation specialists, Community leaders, Irrigation scheme managers
GEOGRAPHY OPTIONS: Global, Asia, Africa, MENA, Latin America, Europe, Low-income and middle-income countries, CWANA

DOCUMENT:
Title: {title}
Authors: {authors}
Date: {date}
Abstract: {abstract}
Full text (if available): {full_text}

Extract and respond with JSON:
{
  "pillars": ["list of matching pillar names"],
  "domains": ["list of matching domain names"],
  "type": "single type from options",
  "stage": "single stage from options",
  "target_users": ["list of matching user types"],
  "geography": ["list of matching geographies"],
  "summary": "2-3 sentence plain-language summary of what this tool/method does",
  "what_it_does": "1-2 sentences describing the tool's function",
  "when_to_use_it": "1-2 sentences describing when a practitioner should use this",
  "who_its_for": "1 sentence describing the primary audience",
  "source_organization": "Organization that created this tool",
  "source_url": "URL to the original resource"
}"""

CHAT_SYSTEM_PROMPT = """\
You are the Enabling Environment Toolbox assistant for CGIAR.
You help users find tools, frameworks, and methods to address
enabling environment challenges in agricultural innovation scaling.

Your role is to understand the user's problem through 2-3 clarifying
questions, then search the catalog and present relevant tools ranked
by contextual fit.

The Enabling Environment has 5 pillars:
{pillar_definitions}

And 3 impact domains:
{domain_definitions}

Tools are classified by: Type, Stage, Target Users, and Geography.
{taxonomy_details}

Guidelines:
- Ask clarifying questions before searching. Don't dump results immediately.
- Questions should help you determine: which pillar(s), which geography,
  who the user is (their role), and what specific barrier they face.
- When presenting results, explain WHY each tool is relevant to their
  specific context -- don't just list titles.
- If no tools match well, say so honestly and suggest adjacent tools
  or alternative approaches.
- Keep responses concise and actionable. These are busy practitioners."""


SEED_PROMPTS = [
    {
        "prompt_name": "relevance_classification",
        "version": 1,
        "prompt_text": RELEVANCE_CLASSIFICATION_PROMPT,
        "model": "claude-sonnet-4-20250514",
        "is_active": True,
        "notes": "Initial version from spec Section 4.3 — relevance classification prompt",
        "created_by": "seed_script",
    },
    {
        "prompt_name": "metadata_extraction",
        "version": 1,
        "prompt_text": METADATA_EXTRACTION_PROMPT,
        "model": "claude-sonnet-4-20250514",
        "is_active": True,
        "notes": "Initial version from spec Section 4.3 — metadata extraction & tagging prompt",
        "created_by": "seed_script",
    },
    {
        "prompt_name": "chat_system",
        "version": 1,
        "prompt_text": CHAT_SYSTEM_PROMPT,
        "model": "claude-sonnet-4-20250514",
        "is_active": True,
        "notes": "Initial version from spec Section 6.3 — conversational AI system prompt",
        "created_by": "seed_script",
    },
]


def seed():
    with SyncSessionLocal() as session:
        for prompt_data in SEED_PROMPTS:
            # Check if already exists
            existing = session.execute(
                select(PromptVersion).where(
                    PromptVersion.prompt_name == prompt_data["prompt_name"],
                    PromptVersion.version == prompt_data["version"],
                )
            ).scalar_one_or_none()

            if existing:
                print(f"  [skip] {prompt_data['prompt_name']} v{prompt_data['version']} already exists")
                continue

            prompt = PromptVersion(**prompt_data)
            session.add(prompt)
            print(f"  [seed] {prompt_data['prompt_name']} v{prompt_data['version']} (active={prompt_data['is_active']})")

        session.commit()
        print("\nDone. Seeded prompt versions.")

        # Verify
        all_prompts = session.execute(select(PromptVersion)).scalars().all()
        print(f"\nTotal prompts in store: {len(all_prompts)}")
        for p in all_prompts:
            print(f"  - {p.prompt_name} v{p.version} active={p.is_active} ({len(p.prompt_text)} chars)")


if __name__ == "__main__":
    seed()
