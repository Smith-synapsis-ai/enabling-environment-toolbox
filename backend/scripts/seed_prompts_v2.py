"""Seed v2 prompt versions with Ojong's formal pillar and domain definitions."""

import sys
from pathlib import Path

# Add backend dir to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from app.database import sync_engine, SyncSessionLocal
from app.models.prompt import PromptVersion

# ── v2 Prompt texts with Ojong's formal pillar/domain definitions ──

RELEVANCE_CLASSIFICATION_V2_PROMPT = """\
You are an expert in agricultural development and enabling environments for innovation scaling.

Given the following document metadata from the CGIAR CG Space repository, determine whether this document is relevant to the Enabling Environment Toolbox.

The Enabling Environment Toolbox curates methods, frameworks, scorecards, manuals, toolkits, guides, briefs, scales, and matrices that help practitioners address enabling environment challenges in agricultural innovation scaling.

Relevant documents should be:
- Actionable tools, methods, or frameworks (not pure research papers or annual reports)
- Related to at least one of the 5 EE pillars: Gender & Social Inclusion, M&E & Learning, Policy & Regulatory, Market Systems, Digital & Financial Services
- OR related to at least one of the 3 impact domains: Agri-food Systems, Scaling Innovation, Climate Resilience
- Preferably concise and practical (short PDFs, guides, toolkits over lengthy academic reports)

PILLAR DEFINITIONS:
1. Gender Equality and Social Inclusion: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to inclusion for marginalized groups of people.
2. Monitoring, Evaluation and Learning: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to feedback loops for iterative improvement.
3. Policy and Regulatory: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can reduce policies and institutional bottlenecks and guide innovations at scale.
4. Market Systems: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can address constraints to effective functioning of markets such as market actors (producers, firms, consumers), supporting services (finance, infrastructure, information, logistics), and the formal and informal rules (policies, standards, norms) that shape market behavior and access.
5. Digital and Financial Services: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to technological integration and financial access using AI and digital tools to enhance scaling efficiency and adaptability as well as accessible, targeted financing opportunities.

DOMAIN DEFINITIONS:
1. Agri-food Systems: The integrated system through which food and agricultural products are produced, processed, distributed, and consumed, representing the primary level where enabling environment pillars translate into development outcomes (e.g., food security, livelihoods, and sustainability).
2. Scaling Innovation: The process through which innovations are adopted, expanded, and sustained across systems and contexts, translating enabling environment conditions into large-scale development outcomes.
3. Climate Resilience: The capacity of systems and populations to withstand, adapt to, and recover from climate risks, representing a critical outcome of effective enabling environment conditions and innovation scaling.

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

METADATA_EXTRACTION_V2_PROMPT = """\
You are an expert in agricultural development and enabling environments for innovation scaling.

Given the following document, extract structured metadata for the Enabling Environment Toolbox catalog.

PILLAR DEFINITIONS:
1. Gender Equality and Social Inclusion: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to inclusion for marginalized groups of people.
2. Monitoring, Evaluation and Learning: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to feedback loops for iterative improvement.
3. Policy and Regulatory: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can reduce policies and institutional bottlenecks and guide innovations at scale.
4. Market Systems: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can address constraints to effective functioning of markets such as market actors (producers, firms, consumers), supporting services (finance, infrastructure, information, logistics), and the formal and informal rules (policies, standards, norms) that shape market behavior and access.
5. Digital and Financial Services: These are methods, frameworks, scorecards, manuals, toolkit, guides, brief, scale, matrix that indicate how an innovation can close enabling environment barriers related to technological integration and financial access using AI and digital tools to enhance scaling efficiency and adaptability as well as accessible, targeted financing opportunities.

DOMAIN DEFINITIONS:
1. Agri-food Systems: The integrated system through which food and agricultural products are produced, processed, distributed, and consumed, representing the primary level where enabling environment pillars translate into development outcomes (e.g., food security, livelihoods, and sustainability).
2. Scaling Innovation: The process through which innovations are adopted, expanded, and sustained across systems and contexts, translating enabling environment conditions into large-scale development outcomes.
3. Climate Resilience: The capacity of systems and populations to withstand, adapt to, and recover from climate risks, representing a critical outcome of effective enabling environment conditions and innovation scaling.

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


SEED_PROMPTS_V2 = [
    {
        "prompt_name": "relevance_classification",
        "version": 2,
        "prompt_text": RELEVANCE_CLASSIFICATION_V2_PROMPT,
        "model": "claude-sonnet-4-20250514",
        "is_active": True,
        "notes": "v2 with Ojong's formal pillar/domain definitions from EE Toolbox review",
        "created_by": "seed_script_v2",
    },
    {
        "prompt_name": "metadata_extraction",
        "version": 2,
        "prompt_text": METADATA_EXTRACTION_V2_PROMPT,
        "model": "claude-sonnet-4-20250514",
        "is_active": True,
        "notes": "v2 with Ojong's formal pillar/domain definitions from EE Toolbox review",
        "created_by": "seed_script_v2",
    },
]


def seed_v2():
    with SyncSessionLocal() as session:
        for prompt_data in SEED_PROMPTS_V2:
            # Idempotency check — skip if v2 already exists
            existing = session.execute(
                select(PromptVersion).where(
                    PromptVersion.prompt_name == prompt_data["prompt_name"],
                    PromptVersion.version == prompt_data["version"],
                )
            ).scalar_one_or_none()

            if existing:
                print(
                    f"  [skip] {prompt_data['prompt_name']} v{prompt_data['version']} already exists"
                )
                continue

            # Deactivate all existing versions of this prompt before inserting v2
            deactivated = session.execute(
                text(
                    "UPDATE prompt_versions SET is_active = false WHERE prompt_name = :name"
                ),
                {"name": prompt_data["prompt_name"]},
            )
            print(
                f"  [deactivate] {prompt_data['prompt_name']} — {deactivated.rowcount} existing version(s) deactivated"
            )

            prompt = PromptVersion(**prompt_data)
            session.add(prompt)
            print(
                f"  [insert] {prompt_data['prompt_name']} v{prompt_data['version']} (active=True)"
            )

        session.commit()
        print("\nDone. v2 prompt versions committed.")

        # Verification summary
        all_prompts = session.execute(select(PromptVersion)).scalars().all()
        print(f"\nAll prompt versions in store ({len(all_prompts)} total):")
        for p in sorted(all_prompts, key=lambda x: (x.prompt_name, x.version)):
            active_marker = "*" if p.is_active else " "
            print(
                f"  [{active_marker}] {p.prompt_name} v{p.version} active={p.is_active} ({len(p.prompt_text)} chars)"
            )
        print("\n  * = currently active")


if __name__ == "__main__":
    seed_v2()
