"""Seed 8 tools missing from initial seed (low extraction quality records).

Revision ID: 004_seed_missing_8_tools
Revises: 003_pulse_survey
Create Date: 2026-06-12

These 8 records had content_richness in (Error, Minimal) + extraction_confidence == Low
and were excluded from the original seed.sql (which contains 92 records).
Adding them here brings the catalog to 100 tools.

Embeddings are NULL — generated on first use by the embedding pipeline.
All statements use ON CONFLICT (cgspace_id) DO NOTHING for idempotency.
IDs are deterministic uuid5 values of the CGSpace handle URL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "004_seed_missing_8_tools"
down_revision = "003_pulse_survey"
branch_labels = None
depends_on = None

_INSERTS = [
    # 10568-100101: Newton Fund PROPOSAL
    {
        "id": "203f408d-ead6-5418-959c-c854d16b863c",
        "cgspace_id": "10568-100101",
        "title": "Newton Fund PROPOSAL: Exploiting biodiversity in Brachiaria and Panicum tropical forage grasses using forward and reverse genetics to improve livelihoods and sustainability. Proposal original profo...",
        "summary": "No content was successfully scraped from the source URL Resource appears to be a Newton Fund proposal related to tropical forage grass biodiversity Focus seems to be on using forward and reverse genetics approaches",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": None,
        "pillars": ["Monitoring, Evaluation and Learning"],
        "domains": ["Biodiversity"],
        "type": "Other",
        "stage": "Prototype",
        "target_users": None,
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100101",
        "source_organization": "International Center for Tropical Agriculture",
        "relevance_score": 0.70,
    },
    # 10568-100125: Forewarned is Forearmed
    {
        "id": "c8d8b1bb-1797-5c3e-ad18-2b3517892f9a",
        "cgspace_id": "10568-100125",
        "title": "Forewarned is Forearmed how Climate Information Services are Saving the Lives and Livelihoods of Senegalese Fisherfolk",
        "summary": "This success story documents how climate information services are being used to protect the lives and livelihoods of fisherfolk in Senegal. It appears to be part of a larger FAO publication showcasing climate services and safety nets initiatives under the CCAFS program.",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": "Development practitioners and policymakers interested in climate services for fishing communities",
        "pillars": ["Monitoring, Evaluation and Learning"],
        "domains": ["Climate Resilience"],
        "type": "Case Study",
        "stage": "Widely Deployed",
        "target_users": ["Development practitioners and policymakers interested in climate services for fishing communities"],
        "geography": ["Senegal", "Africa", "Western Africa"],
        "source_url": "https://hdl.handle.net/10568/100125",
        "source_organization": "Food and Agriculture Organization of the United Nations",
        "relevance_score": 0.70,
    },
    # 10568-100243: G-FEAST focus group guide
    {
        "id": "2e6702c8-d930-5e03-8b71-e1f3094be5d8",
        "cgspace_id": "10568-100243",
        "title": "Gendered Feed Assessment Tool (G-FEAST) focus group discussion guide",
        "summary": "The Gendered Feed Assessment Tool (G-FEAST) focus group discussion guide is a methodological tool designed to assess livestock feeding practices through a gender lens. It provides structured guidance for conducting focus group discussions to understand how gender dynamics influence feed-related decision-making and practices in livestock systems.",
        "what_it_does": "Provides structured guidance for conducting focus group discussions to assess livestock feeding practices with attention to gender roles and decision-making patterns.",
        "when_to_use_it": None,
        "who_its_for": "Scientists and researchers conducting livestock feed assessments",
        "pillars": ["Gender Equality and Social Inclusion", "Monitoring, Evaluation and Learning"],
        "domains": ["Livestock", "Agri-Food Systems"],
        "type": "Guidelines",
        "stage": "Prototype",
        "target_users": ["Scientists and researchers conducting livestock feed assessments"],
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100243",
        "source_organization": "International Livestock Research Institute",
        "relevance_score": 0.70,
    },
    # 10568-100244: G-FEAST individual farmer questionnaire
    {
        "id": "6e9601e9-4f97-5e54-8a1f-2b2c8753878b",
        "cgspace_id": "10568-100244",
        "title": "Gendered Feed Assessment Tool (G-FEAST) individual farmer interview questionnaire",
        "summary": "The Gendered Feed Assessment Tool (G-FEAST) individual farmer interview questionnaire is a data collection instrument designed to assess livestock feeding practices through a gender lens. It enables researchers and practitioners to gather information about how men and women farmers differently engage with livestock feed resources, decision-making, and management practices.",
        "what_it_does": "The tool uses structured individual interviews to collect gender-disaggregated data on livestock feeding practices and decision-making processes.",
        "when_to_use_it": None,
        "who_its_for": "Researchers and development practitioners working on livestock systems",
        "pillars": ["Gender Equality and Social Inclusion", "Monitoring, Evaluation and Learning"],
        "domains": ["Livestock"],
        "type": "Tool",
        "stage": "Prototype",
        "target_users": ["Researchers and development practitioners working on livestock systems"],
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100244",
        "source_organization": "International Livestock Research Institute",
        "relevance_score": 0.70,
    },
    # 10568-100373: Africa RISING Photo Report Malawi
    {
        "id": "205303b9-8bbe-5df8-9118-71ba99468a3f",
        "cgspace_id": "10568-100373",
        "title": "Photo report on the Africa RISING Program Learning Event in Malawi, 5-8 February 2019",
        "summary": "This is a photo report documenting the Africa RISING Program Learning Event held in Malawi from February 5-8, 2019. The resource appears to be a visual documentation of program activities, learnings, and outcomes from this multi-stakeholder learning event focused on agricultural development in Africa.",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": "Scientists and agricultural development practitioners",
        "pillars": ["Monitoring, Evaluation and Learning"],
        "domains": ["Agri-Food Systems", "Livestock"],
        "type": "Report",
        "stage": "Prototype",
        "target_users": ["Scientists and agricultural development practitioners"],
        "geography": ["Malawi", "Africa"],
        "source_url": "https://hdl.handle.net/10568/100373",
        "source_organization": "International Livestock Research Institute",
        "relevance_score": 0.70,
    },
    # 10568-100488: Livestock headwinds
    {
        "id": "c3f39278-c6e5-5ed6-8b65-daad58fae212",
        "cgspace_id": "10568-100488",
        "title": "Livestock headwinds: Help or hindrance to sustainable development?",
        "summary": "This appears to be a presentation examining the complex relationship between livestock systems and sustainable development goals. The resource explores whether livestock production serves as a help or hindrance to achieving sustainable development outcomes.",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": "Scientists and researchers",
        "pillars": ["Monitoring, Evaluation and Learning"],
        "domains": ["Livestock", "Agri-Food Systems"],
        "type": "Presentation",
        "stage": "Prototype",
        "target_users": ["Scientists and researchers"],
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100488",
        "source_organization": "International Livestock Research Institute",
        "relevance_score": 0.70,
    },
    # 10568-100562: Digitising farmer cooperatives
    {
        "id": "61c736cc-08be-5a84-b50d-d50db1455012",
        "cgspace_id": "10568-100562",
        "title": "Digitising farmer cooperatives to improve their financial and operational efficiency",
        "summary": "This resource documents the digitization of farmer cooperatives to enhance their financial and operational efficiency. It appears to be an experience capitalization piece that explores how digital technologies and ICT solutions can transform cooperative management and business operations in agricultural contexts.",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": "Development practitioners working with farmer cooperatives",
        "pillars": ["Digital and Financial Services", "Monitoring, Evaluation and Learning"],
        "domains": ["Agri-Food Systems", "Value Chains"],
        "type": "Case Study",
        "stage": "Prototype",
        "target_users": ["Development practitioners working with farmer cooperatives"],
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100562",
        "source_organization": "Technical Centre for Agricultural and Rural Cooperation",
        "relevance_score": 0.70,
    },
    # 10568-100592: Gender and digitalisation
    {
        "id": "0f1112b2-18e6-537c-948d-113fce4be8c5",
        "cgspace_id": "10568-100592",
        "title": "Gender and digitalisation supporting women in agribusiness",
        "summary": "This resource examines the intersection of gender and digitalization in supporting women's participation in agribusiness. It appears to focus on how digital technologies can be leveraged to address gender-specific barriers and enhance women's roles in agricultural value chains.",
        "what_it_does": None,
        "when_to_use_it": None,
        "who_its_for": "Development practitioners working on gender and digitalization in agriculture",
        "pillars": ["Gender Equality and Social Inclusion", "Digital and Financial Services", "Market Systems"],
        "domains": ["Agri-Food Systems", "Value Chains"],
        "type": "Other",
        "stage": "Prototype",
        "target_users": ["Development practitioners working on gender and digitalization in agriculture"],
        "geography": None,
        "source_url": "https://hdl.handle.net/10568/100592",
        "source_organization": "CTA (Technical Centre for Agricultural and Rural Cooperation)",
        "relevance_score": 0.70,
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for t in _INSERTS:
        conn.execute(
            sa.text(
                """
                INSERT INTO public.tools (
                    id, title, summary, what_it_does, when_to_use_it, who_its_for,
                    pillars, domains, type, stage, target_users, geography,
                    authors, date_published, source_url, source_organization,
                    cover_image_url, embedding, average_rating, rating_count, view_count,
                    cgspace_id, relevance_score, is_visible, created_at, updated_at
                ) VALUES (
                    CAST(:id AS uuid),
                    :title,
                    :summary,
                    :what_it_does,
                    :when_to_use_it,
                    :who_its_for,
                    CAST(:pillars AS text[]),
                    CAST(:domains AS text[]),
                    :type,
                    :stage,
                    CAST(:target_users AS text[]),
                    CAST(:geography AS text[]),
                    NULL,
                    NULL,
                    :source_url,
                    :source_organization,
                    NULL,
                    NULL,
                    0, 0, 0,
                    :cgspace_id,
                    :relevance_score,
                    true,
                    now(), now()
                )
                ON CONFLICT (cgspace_id) DO NOTHING
                """
            ),
            {
                "id": t["id"],
                "title": t["title"],
                "summary": t["summary"],
                "what_it_does": t["what_it_does"],
                "when_to_use_it": t["when_to_use_it"],
                "who_its_for": t["who_its_for"],
                "pillars": t["pillars"],
                "domains": t["domains"],
                "type": t["type"],
                "stage": t["stage"],
                "target_users": t["target_users"],
                "geography": t["geography"],
                "source_url": t["source_url"],
                "source_organization": t["source_organization"],
                "cgspace_id": t["cgspace_id"],
                "relevance_score": t["relevance_score"],
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    cgspace_ids = [t["cgspace_id"] for t in _INSERTS]
    conn.execute(
        sa.text("DELETE FROM public.tools WHERE cgspace_id = ANY(CAST(:ids AS text[]))"),
        {"ids": cgspace_ids},
    )
