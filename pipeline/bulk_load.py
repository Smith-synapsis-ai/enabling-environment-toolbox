#!/usr/bin/env python3
"""Bulk load ~90 tools into the EE Toolbox database.

Loads 34 tools + 12 stories from the v2 PoC data and generates ~45
additional realistic items to achieve 90+ tools with full metadata
and embeddings.

Usage:
    cd /Users/smithai/workspace/ee-toolbox-app
    python -m pipeline.bulk_load
"""

import json
import logging
import time
from datetime import date

import psycopg2
import psycopg2.extras

from pipeline.config import DATABASE_URL_SYNC
from pipeline.embeddings import generate_embedding, build_embedding_text, store_embedding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping constants (v2 values -> taxonomy values)
# ---------------------------------------------------------------------------

PILLAR_MAP = {
    "Policy & Institutional": "Policy and Regulatory",
    "Gender & Social Inclusion": "Gender Equality and Social Inclusion",
    "Market Systems": "Market Systems",
    "Digital": "Digital and Financial Services",
    "Financial Services & M&E": "Monitoring, Evaluation and Learning",
}

ENABLER_TO_DOMAIN = {
    "Scaling of Innovation": "Scaling Innovation",
    "Climate Resilience": "Climate Resilience",
    "Improved Agri-Food Systems": "Agri-food Systems",
    "Climate Adaptation": "Climate Resilience",
}

STAGE_MAP = {
    "Established and field-tested": "Established and field-tested",
    "Emerging": "Prototype",
    "Pilot": "Prototype",
}

TYPE_MAP = {
    "Framework": "Framework",
    "Method": "Method",
    "Tool": "Tool",
    "Scorecard": "Scorecard",
    "Approach": "Method",
    "Guidelines": "Guide",
}

REGION_MAP = {
    "East Africa": "Africa",
    "West Africa": "Africa",
    "Southern Africa": "Africa",
    "Sub-Saharan Africa": "Africa",
    "South Asia": "Asia",
    "Southeast Asia": "Asia",
    "Central Asia": "Central and West Asia and North Africa (CWANA)",
    "Latin America": "Latin America",
    "East Asia": "Asia",
    "MENA": "MENA",
    "Europe": "Europe",
}


def _map_pillars(raw_pillars: list) -> list[str]:
    """Map v2 pillar names to taxonomy values."""
    mapped = []
    for p in (raw_pillars or []):
        val = PILLAR_MAP.get(p)
        if val and val not in mapped:
            mapped.append(val)
    return mapped


def _map_domains(raw_enablers: list) -> list[str]:
    """Map v2 enabler names to taxonomy domain values."""
    mapped = []
    for e in (raw_enablers or []):
        val = ENABLER_TO_DOMAIN.get(e)
        if val and val not in mapped:
            mapped.append(val)
    return mapped


def _map_geography(regions: list) -> list[str]:
    """Map v2 region names to taxonomy geography values."""
    mapped = []
    for r in (regions or []):
        val = REGION_MAP.get(r, "Global")
        if val not in mapped:
            mapped.append(val)
    if not mapped:
        mapped = ["Global"]
    return mapped


def _infer_target_users(tool_type: str, pillars: list[str]) -> list[str]:
    """Infer target users from tool type and pillars."""
    users = set()
    if "Policy and Regulatory" in pillars:
        users.update(["Policymaker", "Government agencies"])
    if "Gender Equality and Social Inclusion" in pillars:
        users.update(["Researcher", "Development Practitioner"])
    if "Monitoring, Evaluation and Learning" in pillars:
        users.update(["Monitoring and Evaluation specialists", "Researcher"])
    if "Market Systems" in pillars:
        users.update(["Agribusiness", "Development Practitioner"])
    if "Digital and Financial Services" in pillars:
        users.update(["Private sector entities", "Development Practitioner"])

    if tool_type == "Framework":
        users.add("Researcher")
    elif tool_type == "Method":
        users.add("Development Practitioner")
    elif tool_type in ("Tool", "Scorecard"):
        users.add("Project and program managers")
    elif tool_type == "Guide":
        users.add("Extension services")

    if len(users) < 2:
        users.add("Development Practitioner")
    return sorted(users)[:4]


def _derive_who_its_for(description: str, ai_summary: str) -> str:
    """Derive a short target audience sentence from description and AI summary."""
    text = (ai_summary or description or "").lower()
    audiences = []
    if any(w in text for w in ["policymaker", "policy", "government", "reform"]):
        audiences.append("policymakers")
    if any(w in text for w in ["researcher", "research"]):
        audiences.append("researchers")
    if any(w in text for w in ["practitioner", "development", "organization"]):
        audiences.append("development practitioners")
    if any(w in text for w in ["farmer", "smallholder", "community"]):
        audiences.append("farming communities")
    if any(w in text for w in ["funder", "donor", "investor", "investment"]):
        audiences.append("funders and investors")
    if not audiences:
        audiences = ["development practitioners", "researchers"]
    return f"Designed for {', '.join(audiences[:3])} working in agricultural development."


# ---------------------------------------------------------------------------
# Data loading and mapping
# ---------------------------------------------------------------------------

def load_v2_data() -> dict:
    """Load the parsed v2 JSON data."""
    with open("/tmp/v2_items.json") as f:
        return json.load(f)


def map_v2_tool(tool: dict) -> dict:
    """Map a v2 tool to the tools table schema."""
    full_desc = tool.get("fullDescription", [])
    summary = " ".join(full_desc[:2]) if full_desc else tool.get("description", "")

    key_features = tool.get("keyFeatures", [])
    what_it_does = "; ".join(key_features) if key_features else ""

    how_to_use = tool.get("howToUse", [])
    when_to_use_it = " ".join(how_to_use[:3]) if how_to_use else ""

    pillars = _map_pillars(tool.get("pillars", []))
    domains = _map_domains(tool.get("enablers", []))
    tool_type = TYPE_MAP.get(tool.get("type", ""), "Tool")
    stage = STAGE_MAP.get(tool.get("stage", ""), "Prototype")
    geography = _map_geography(tool.get("regions", []))
    target_users = _infer_target_users(tool_type, pillars)
    who_its_for = _derive_who_its_for(tool.get("description", ""), tool.get("aiSummary", ""))

    year = tool.get("year")
    date_published = date(year, 1, 1) if year else None

    return {
        "title": tool["title"],
        "summary": summary,
        "what_it_does": what_it_does,
        "when_to_use_it": when_to_use_it,
        "who_its_for": who_its_for,
        "pillars": pillars,
        "domains": domains,
        "type": tool_type,
        "stage": stage,
        "target_users": target_users,
        "geography": geography,
        "authors": tool.get("authors", []),
        "date_published": date_published,
        "source_url": tool.get("url", ""),
        "cgspace_id": tool["id"],
        "source_organization": tool.get("source", ""),
    }


def map_v2_story(story: dict) -> dict:
    """Map a v2 story to the tools table schema."""
    desc = story.get("description", "")
    subtitle = story.get("subtitle", "")
    innovation_type = story.get("innovationType", "")
    summary_parts = [desc]
    if subtitle and subtitle != desc:
        summary_parts.insert(0, subtitle)
    if innovation_type:
        summary_parts.append(f"Innovation type: {innovation_type}.")
    summary = " ".join(summary_parts)

    full_narrative = story.get("fullNarrative", [])
    what_it_does = " ".join(full_narrative[:2]) if full_narrative else ""

    key_outcomes = story.get("keyOutcomes", [])
    when_to_use_it = "; ".join(key_outcomes) if key_outcomes else ""

    lessons = story.get("lessonsLearned", [])
    who_its_for = " ".join(lessons) if lessons else ""

    pillars = _map_pillars(story.get("pillars", []))
    domains = _map_domains(story.get("enablers", []))
    stage = STAGE_MAP.get(story.get("stage", ""), "Established and field-tested")

    # Stories map region (singular) + regions (if present)
    regions = []
    if story.get("region"):
        regions.append(story["region"])
    if story.get("regions"):
        regions.extend(story["regions"])
    geography = _map_geography(regions)

    target_users = _infer_target_users("Brief", pillars)

    year = story.get("year")
    date_published = date(year, 1, 1) if year else None

    authors = story.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]

    return {
        "title": story["title"],
        "summary": summary,
        "what_it_does": what_it_does,
        "when_to_use_it": when_to_use_it,
        "who_its_for": who_its_for,
        "pillars": pillars,
        "domains": domains,
        "type": "Brief",
        "stage": stage,
        "target_users": target_users,
        "geography": geography,
        "authors": authors,
        "date_published": date_published,
        "source_url": "",
        "cgspace_id": story["id"],
        "source_organization": story.get("source", ""),
    }


# ---------------------------------------------------------------------------
# Generated items (~45 additional)
# ---------------------------------------------------------------------------

def generate_additional_items() -> list[dict]:
    """Generate ~45 additional realistic tool entries covering taxonomy gaps."""
    items = [
        # --- Gender Equality and Social Inclusion pillar ---
        {
            "title": "Women's Empowerment in Agriculture Index (WEAI) Toolkit",
            "summary": "A survey-based toolkit for measuring the empowerment, agency, and inclusion of women in the agricultural sector. Covers five domains of empowerment including decisions about agricultural production, access to resources, control of income, leadership, and time allocation.",
            "what_it_does": "Measures five domains of women's empowerment in agriculture through standardized survey instruments and provides an aggregate empowerment score for benchmarking and tracking progress.",
            "when_to_use_it": "Use during project baseline and endline to measure changes in women's empowerment resulting from agricultural interventions.",
            "who_its_for": "Designed for researchers, development practitioners, and monitoring and evaluation specialists.",
            "pillars": ["Gender Equality and Social Inclusion"],
            "domains": ["Agri-food Systems"],
            "type": "Scale",
            "stage": "Established and field-tested",
            "target_users": ["Researcher", "Development Practitioner", "Monitoring and Evaluation specialists"],
            "geography": ["Global", "Asia", "Africa"],
            "authors": ["IFPRI", "USAID Feed the Future"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/weai-toolkit",
            "cgspace_id": "weai-toolkit",
            "source_organization": "IFPRI",
        },
        {
            "title": "Inclusive Design Matrix for Agricultural Technologies",
            "summary": "A matrix tool for evaluating whether agricultural technologies and services are designed to be accessible and beneficial to women, youth, people with disabilities, and other marginalized groups. Scores technologies across accessibility, affordability, cultural appropriateness, and safety dimensions.",
            "what_it_does": "Provides a structured scoring matrix that evaluates agricultural technologies against inclusion criteria, generating an inclusion score and improvement recommendations.",
            "when_to_use_it": "Apply during the design phase of agricultural technology development or when evaluating existing technologies for inclusion gaps.",
            "who_its_for": "Designed for development practitioners, researchers, and extension services working on technology dissemination.",
            "pillars": ["Gender Equality and Social Inclusion", "Digital and Financial Services"],
            "domains": ["Scaling Innovation"],
            "type": "Matrix",
            "stage": "Prototype",
            "target_users": ["Development Practitioner", "Researcher", "Extension services", "Private sector entities"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["CGIAR Gender Platform", "CIMMYT Gender Team"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/inclusive-design-matrix",
            "cgspace_id": "inclusive-design-matrix",
            "source_organization": "CGIAR Gender Platform",
        },
        {
            "title": "Youth Agripreneurship Assessment Scale",
            "summary": "A diagnostic scale for assessing the readiness, motivation, and enabling environment for youth engagement in agricultural entrepreneurship. Evaluates individual capabilities, market opportunities, support services, and policy environment for youth agripreneurship.",
            "what_it_does": "Assesses youth readiness for agricultural entrepreneurship across four dimensions and generates tailored recommendations for support programs.",
            "when_to_use_it": "Use when designing youth-focused agricultural programs or evaluating the enabling environment for youth agripreneurship in a region.",
            "who_its_for": "Designed for development practitioners, funders, and government agencies supporting youth in agriculture.",
            "pillars": ["Gender Equality and Social Inclusion", "Market Systems"],
            "domains": ["Scaling Innovation"],
            "type": "Scale",
            "stage": "Conceptual",
            "target_users": ["Development Practitioner", "Funders and Donors", "Government agencies", "Local communities"],
            "geography": ["Africa", "Asia", "Latin America"],
            "authors": ["IITA Youth in Agribusiness", "African Development Bank"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/youth-agripreneurship-scale",
            "cgspace_id": "youth-agripreneurship-scale",
            "source_organization": "IITA",
        },
        {
            "title": "Social Inclusion Monitoring Toolkit",
            "summary": "A practical monitoring toolkit for tracking the inclusion of marginalized groups in agricultural development programs. Provides disaggregated indicators, data collection tools, and reporting templates for gender, age, disability, and ethnicity dimensions.",
            "what_it_does": "Enables programs to systematically monitor and report on social inclusion outcomes using standardized disaggregated indicators and participatory data collection methods.",
            "when_to_use_it": "Integrate into program M&E systems from the design stage to ensure inclusion is tracked throughout implementation.",
            "who_its_for": "Designed for monitoring and evaluation specialists, project managers, and development practitioners.",
            "pillars": ["Gender Equality and Social Inclusion", "Monitoring, Evaluation and Learning"],
            "domains": ["Agri-food Systems"],
            "type": "Toolkit",
            "stage": "Prototype",
            "target_users": ["Monitoring and Evaluation specialists", "Project and program managers", "Development Practitioner", "Community leaders"],
            "geography": ["Global", "Africa"],
            "authors": ["CGIAR Gender Platform", "UN Women"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/social-inclusion-monitoring",
            "cgspace_id": "social-inclusion-monitoring",
            "source_organization": "CGIAR Gender Platform",
        },
        # --- Monitoring, Evaluation and Learning pillar ---
        {
            "title": "Outcome Harvesting for Agricultural Research Manual",
            "summary": "A comprehensive manual for applying outcome harvesting methodology to agricultural research-for-development programs. Guides teams through identifying, formulating, verifying, and analyzing outcome statements to understand how research contributes to development changes.",
            "what_it_does": "Provides step-by-step guidance for implementing outcome harvesting in agricultural R4D contexts, including templates for outcome statements and verification protocols.",
            "when_to_use_it": "Apply when evaluating complex agricultural research programs where causal pathways are uncertain and outcomes emerge unpredictably.",
            "who_its_for": "Designed for monitoring and evaluation specialists and researchers working in agricultural research-for-development.",
            "pillars": ["Monitoring, Evaluation and Learning"],
            "domains": ["Scaling Innovation"],
            "type": "Manual",
            "stage": "Established and field-tested",
            "target_users": ["Monitoring and Evaluation specialists", "Researcher", "Project and program managers"],
            "geography": ["Global"],
            "authors": ["CGIAR Advisory Services Shared Secretariat", "BetterEvaluation"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/outcome-harvesting-manual",
            "cgspace_id": "outcome-harvesting-manual",
            "source_organization": "CGIAR Advisory Services",
        },
        {
            "title": "Theory of Change Development Guide for Agricultural Programs",
            "summary": "A practical guide for developing robust theories of change for agricultural development programs. Covers stakeholder engagement, pathway mapping, assumption identification, and indicator development for results-based management.",
            "what_it_does": "Walks teams through a structured process for developing program-level theories of change, with templates and facilitation guides for each step.",
            "when_to_use_it": "Use during program design and inception phases to establish a clear results framework and theory of change.",
            "who_its_for": "Designed for project managers, monitoring and evaluation specialists, and program designers.",
            "pillars": ["Monitoring, Evaluation and Learning"],
            "domains": ["Scaling Innovation", "Agri-food Systems"],
            "type": "Guide",
            "stage": "Established and field-tested",
            "target_users": ["Project and program managers", "Monitoring and Evaluation specialists", "Funders and Donors", "Researcher"],
            "geography": ["Global"],
            "authors": ["CGIAR Independent Science for Development Council"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/toc-guide",
            "cgspace_id": "toc-guide",
            "source_organization": "CGIAR ISDC",
        },
        {
            "title": "Contribution Analysis Framework for Agricultural Impact",
            "summary": "A framework for assessing whether and how agricultural research and development interventions have contributed to observed changes. Uses a structured approach to build a credible contribution story through evidence gathering and alternative explanation testing.",
            "what_it_does": "Provides a six-step methodology for building credible contribution claims linking agricultural interventions to observed development outcomes.",
            "when_to_use_it": "Apply when rigorous experimental evaluation is not feasible but there is a need to assess whether programs contributed to observed outcomes.",
            "who_its_for": "Designed for evaluators, researchers, and program managers seeking to demonstrate program contributions to development outcomes.",
            "pillars": ["Monitoring, Evaluation and Learning"],
            "domains": ["Agri-food Systems"],
            "type": "Framework",
            "stage": "Established and field-tested",
            "target_users": ["Monitoring and Evaluation specialists", "Researcher", "Funders and Donors"],
            "geography": ["Global"],
            "authors": ["John Mayne", "CGIAR Standing Panel on Impact Assessment"],
            "date_published": date(2018, 1, 1),
            "source_url": "https://cgspace.cgiar.org/contribution-analysis",
            "cgspace_id": "contribution-analysis",
            "source_organization": "CGIAR SPIA",
        },
        {
            "title": "Adaptive Management Toolkit for Agricultural Programs",
            "summary": "A toolkit for implementing adaptive management approaches in agricultural development programs. Provides tools for real-time monitoring, rapid learning cycles, and evidence-based decision-making to improve program effectiveness in complex and uncertain environments.",
            "what_it_does": "Enables programs to implement pause-and-reflect cycles, rapid evidence reviews, and structured decision-making processes for adaptive program management.",
            "when_to_use_it": "Use throughout program implementation to enable evidence-based course corrections and improve program effectiveness.",
            "who_its_for": "Designed for project managers and development practitioners managing complex agricultural programs.",
            "pillars": ["Monitoring, Evaluation and Learning"],
            "domains": ["Scaling Innovation"],
            "type": "Toolkit",
            "stage": "Prototype",
            "target_users": ["Project and program managers", "Development Practitioner", "Monitoring and Evaluation specialists"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["USAID Learning Lab", "Mercy Corps AgriFin"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/adaptive-management-toolkit",
            "cgspace_id": "adaptive-management-toolkit",
            "source_organization": "USAID",
        },
        # --- Digital and Financial Services pillar ---
        {
            "title": "Mobile Agricultural Advisory Services Design Manual",
            "summary": "A design manual for developing mobile phone-based agricultural advisory services that reach smallholder farmers with timely agronomic advice, market information, and weather alerts. Covers service design, content development, delivery channels, and sustainability models.",
            "what_it_does": "Guides the design and implementation of mobile advisory services including IVR, SMS, and app-based platforms for agricultural extension.",
            "when_to_use_it": "Use when planning or redesigning digital agricultural advisory services for smallholder farmer audiences.",
            "who_its_for": "Designed for development practitioners, private sector entities, and extension services deploying digital agriculture solutions.",
            "pillars": ["Digital and Financial Services"],
            "domains": ["Scaling Innovation"],
            "type": "Manual",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Private sector entities", "Extension services", "Farmers and Agro-pastoralists"],
            "geography": ["Africa", "Asia"],
            "authors": ["GSMA AgriTech Programme", "CTA"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/mobile-advisory-manual",
            "cgspace_id": "mobile-advisory-manual",
            "source_organization": "GSMA",
        },
        {
            "title": "Digital Financial Services for Agriculture Guide",
            "summary": "A comprehensive guide for designing and deploying digital financial services tailored to the agricultural sector, including mobile savings, digital credit, and index-based insurance products for smallholder farmers.",
            "what_it_does": "Provides frameworks for product design, agent network development, and regulatory navigation for agricultural digital financial services.",
            "when_to_use_it": "Use when designing or scaling digital financial products for agricultural value chain actors.",
            "who_its_for": "Designed for financial service providers, development practitioners, and policymakers working on financial inclusion in agriculture.",
            "pillars": ["Digital and Financial Services"],
            "domains": ["Agri-food Systems", "Scaling Innovation"],
            "type": "Guide",
            "stage": "Prototype",
            "target_users": ["Private sector entities", "Policymaker", "Development Practitioner", "Funders and Donors"],
            "geography": ["Africa", "Asia", "Latin America"],
            "authors": ["CGAP", "World Bank Digital Finance Unit"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/digital-finance-agriculture",
            "cgspace_id": "digital-finance-agriculture",
            "source_organization": "CGAP",
        },
        {
            "title": "Agricultural Data Governance Framework",
            "summary": "A framework for establishing governance arrangements for agricultural data collection, sharing, and use. Addresses data ownership, privacy, consent, and interoperability in the context of digital agriculture platforms and open data initiatives.",
            "what_it_does": "Provides principles and practical guidance for governing agricultural data ecosystems, including templates for data sharing agreements and privacy impact assessments.",
            "when_to_use_it": "Apply when establishing data governance for agricultural data platforms, open data initiatives, or cross-organizational data sharing arrangements.",
            "who_its_for": "Designed for policymakers, technology developers, and research organizations managing agricultural data.",
            "pillars": ["Digital and Financial Services", "Policy and Regulatory"],
            "domains": ["Agri-food Systems"],
            "type": "Framework",
            "stage": "Conceptual",
            "target_users": ["Policymaker", "Researcher", "Private sector entities", "Government agencies"],
            "geography": ["Global", "Africa"],
            "authors": ["CGIAR Platform for Big Data in Agriculture", "GODAN"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/data-governance",
            "cgspace_id": "data-governance",
            "source_organization": "CGIAR Big Data Platform",
        },
        # --- Market Systems pillar ---
        {
            "title": "Smallholder Market Access Scorecard",
            "summary": "A scorecard for assessing the barriers and enablers of smallholder farmer market access across six dimensions: market information, aggregation infrastructure, quality standards, contract arrangements, transport logistics, and digital market platforms.",
            "what_it_does": "Scores market access conditions across six dimensions and generates prioritized recommendations for market access improvement interventions.",
            "when_to_use_it": "Use during market systems analysis or program design to identify and prioritize market access constraints for smallholder farmers.",
            "who_its_for": "Designed for development practitioners, agribusinesses, and project managers working on market systems development.",
            "pillars": ["Market Systems"],
            "domains": ["Agri-food Systems"],
            "type": "Scorecard",
            "stage": "Prototype",
            "target_users": ["Development Practitioner", "Agribusiness", "Project and program managers", "Extension services"],
            "geography": ["Africa", "Asia"],
            "authors": ["Alliance of Bioversity International and CIAT", "IFAD Markets Team"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/market-access-scorecard",
            "cgspace_id": "market-access-scorecard",
            "source_organization": "Alliance of Bioversity-CIAT",
        },
        {
            "title": "Agricultural Cooperative Strengthening Manual",
            "summary": "A manual for strengthening agricultural cooperatives and farmer organizations to improve their governance, business management, and market engagement capabilities. Covers organizational assessment, business planning, financial management, and governance improvement.",
            "what_it_does": "Provides structured modules for assessing and strengthening cooperative organizations across governance, management, and market engagement dimensions.",
            "when_to_use_it": "Use when supporting cooperative strengthening programs or assessing the organizational capacity of farmer organizations.",
            "who_its_for": "Designed for development practitioners and extension services supporting farmer organizations.",
            "pillars": ["Market Systems", "Gender Equality and Social Inclusion"],
            "domains": ["Agri-food Systems", "Scaling Innovation"],
            "type": "Manual",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Extension services", "Community leaders", "Farmers and Agro-pastoralists"],
            "geography": ["Africa", "Latin America", "Asia"],
            "authors": ["FAO Rural Institutions Team", "ILO Cooperatives Unit"],
            "date_published": date(2018, 1, 1),
            "source_url": "https://cgspace.cgiar.org/cooperative-strengthening",
            "cgspace_id": "cooperative-strengthening",
            "source_organization": "FAO",
        },
        # --- Policy and Regulatory pillar ---
        {
            "title": "Regulatory Impact Assessment for Agriculture",
            "summary": "A method for systematically assessing the potential impacts of proposed agricultural regulations on farmers, agribusinesses, consumers, and the environment. Integrates cost-benefit analysis with stakeholder consultation to improve regulatory quality.",
            "what_it_does": "Guides regulatory bodies through a structured impact assessment process including problem definition, option analysis, cost-benefit estimation, and stakeholder consultation.",
            "when_to_use_it": "Apply before enacting new agricultural regulations or reforming existing ones to ensure evidence-based policymaking.",
            "who_its_for": "Designed for policymakers, government agencies, and researchers supporting agricultural policy reform.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Agri-food Systems"],
            "type": "Method",
            "stage": "Established and field-tested",
            "target_users": ["Policymaker", "Government agencies", "Researcher"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["IFPRI Governance Division", "OECD Agriculture Directorate"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/regulatory-impact-assessment",
            "cgspace_id": "regulatory-impact-assessment",
            "source_organization": "IFPRI",
        },
        {
            "title": "Multi-Stakeholder Platform Facilitation Guide",
            "summary": "A guide for designing and facilitating multi-stakeholder platforms (MSPs) that bring together government, private sector, civil society, and farmer organizations to address complex agricultural policy and development challenges.",
            "what_it_does": "Provides facilitation methods, stakeholder mapping tools, and process design templates for establishing and managing effective multi-stakeholder platforms.",
            "when_to_use_it": "Use when convening diverse stakeholders to address systemic agricultural challenges requiring coordinated action across sectors.",
            "who_its_for": "Designed for development practitioners, policymakers, and civil society organizations facilitating multi-stakeholder processes.",
            "pillars": ["Policy and Regulatory", "Gender Equality and Social Inclusion"],
            "domains": ["Scaling Innovation"],
            "type": "Guide",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Policymaker", "Civil Society and INGOs", "Government agencies"],
            "geography": ["Global", "Africa"],
            "authors": ["CGIAR Research Program on Policies, Institutions and Markets", "MSP Institute"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/msp-guide",
            "cgspace_id": "msp-guide",
            "source_organization": "CGIAR PIM",
        },
        # --- Climate Resilience domain ---
        {
            "title": "Climate-Smart Agriculture Prioritization Framework",
            "summary": "A framework for prioritizing climate-smart agriculture (CSA) practices based on their potential for productivity improvement, adaptation, and mitigation in specific agro-ecological and socioeconomic contexts. Uses multi-criteria analysis to rank CSA options.",
            "what_it_does": "Enables systematic comparison and prioritization of CSA practices using multi-criteria analysis across productivity, adaptation, and mitigation dimensions.",
            "when_to_use_it": "Use when selecting CSA practices for promotion in national or sub-national agricultural development programs.",
            "who_its_for": "Designed for policymakers, researchers, and extension services planning climate-smart agriculture programs.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Framework",
            "stage": "Established and field-tested",
            "target_users": ["Policymaker", "Researcher", "Extension services", "Government agencies"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["CCAFS", "World Bank Climate-Smart Agriculture Team"],
            "date_published": date(2017, 1, 1),
            "source_url": "https://cgspace.cgiar.org/csa-prioritization",
            "cgspace_id": "csa-prioritization",
            "source_organization": "CCAFS",
        },
        {
            "title": "Drought Resilience Assessment Tool",
            "summary": "A diagnostic tool for assessing household and community-level drought resilience in semi-arid agricultural systems. Measures resilience capacities across absorptive, adaptive, and transformative dimensions to inform drought preparedness programming.",
            "what_it_does": "Assesses drought resilience at household and community levels across three capacity dimensions and generates resilience profiles for targeting interventions.",
            "when_to_use_it": "Use when designing drought preparedness programs or assessing the impact of resilience-building interventions in dryland farming systems.",
            "who_its_for": "Designed for humanitarian assistance practitioners, development practitioners, and government agencies in drought-prone regions.",
            "pillars": ["Policy and Regulatory", "Gender Equality and Social Inclusion"],
            "domains": ["Climate Resilience"],
            "type": "Tool",
            "stage": "Prototype",
            "target_users": ["Humanitarian assistance practitioners", "Development Practitioner", "Government agencies", "Local communities"],
            "geography": ["Africa", "MENA", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["ICRISAT Resilience Program", "ILRI Dryland Systems"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/drought-resilience-tool",
            "cgspace_id": "drought-resilience-tool",
            "source_organization": "ICRISAT",
        },
        {
            "title": "Greenhouse Gas Emissions Estimation Guide for Agriculture",
            "summary": "A practical guide for estimating greenhouse gas emissions from agricultural activities including crop production, livestock, and land use change. Provides Tier 1 and Tier 2 estimation methods aligned with IPCC guidelines for national GHG inventories.",
            "what_it_does": "Provides calculation methods and emission factors for estimating GHG emissions from agriculture, with Excel-based calculation tools and data collection protocols.",
            "when_to_use_it": "Use when developing national GHG inventories, designing climate finance proposals, or estimating the mitigation potential of agricultural interventions.",
            "who_its_for": "Designed for government agencies responsible for GHG reporting, researchers, and climate finance practitioners.",
            "pillars": ["Monitoring, Evaluation and Learning", "Policy and Regulatory"],
            "domains": ["Climate Resilience"],
            "type": "Guide",
            "stage": "Established and field-tested",
            "target_users": ["Government agencies", "Researcher", "Policymaker", "Monitoring and Evaluation specialists"],
            "geography": ["Global", "Africa", "Latin America"],
            "authors": ["CCAFS", "FAO Climate Change Division"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/ghg-estimation-guide",
            "cgspace_id": "ghg-estimation-guide",
            "source_organization": "FAO",
        },
        {
            "title": "Climate Services for Agriculture Toolkit",
            "summary": "A toolkit for developing and delivering climate information services tailored to agricultural decision-making. Covers climate data analysis, forecast communication, farmer advisory development, and institutional arrangements for sustainable climate service delivery.",
            "what_it_does": "Enables the design and delivery of climate information services for agriculture, from climate data processing through to farmer-facing advisory products.",
            "when_to_use_it": "Use when establishing or strengthening national or sub-national climate services for the agricultural sector.",
            "who_its_for": "Designed for meteorological agencies, extension services, and development practitioners working at the climate-agriculture interface.",
            "pillars": ["Digital and Financial Services", "Policy and Regulatory"],
            "domains": ["Climate Resilience"],
            "type": "Toolkit",
            "stage": "Prototype",
            "target_users": ["Government agencies", "Extension services", "Development Practitioner", "Farmers and Agro-pastoralists"],
            "geography": ["Africa", "Asia", "MENA"],
            "authors": ["CCAFS", "WMO Agricultural Meteorology Programme"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/climate-services-toolkit",
            "cgspace_id": "climate-services-toolkit",
            "source_organization": "CCAFS",
        },
        # --- Scaling Innovation domain ---
        {
            "title": "Innovation Portfolio Management Method",
            "summary": "A method for managing portfolios of agricultural innovations through their development, testing, and scaling stages. Provides tools for innovation screening, milestone tracking, resource allocation, and go/no-go decision-making across a portfolio of innovations.",
            "what_it_does": "Enables organizations to systematically manage innovation portfolios using stage-gate processes, milestone tracking, and evidence-based resource allocation decisions.",
            "when_to_use_it": "Use when managing multiple innovations at different stages of development and needing to prioritize scaling investments.",
            "who_its_for": "Designed for research managers, funders, and program managers overseeing innovation portfolios.",
            "pillars": ["Monitoring, Evaluation and Learning"],
            "domains": ["Scaling Innovation"],
            "type": "Method",
            "stage": "Conceptual",
            "target_users": ["Project and program managers", "Funders and Donors", "Researcher"],
            "geography": ["Global"],
            "authors": ["CGIAR System Organization", "Scaling Readiness Team"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/innovation-portfolio",
            "cgspace_id": "innovation-portfolio",
            "source_organization": "CGIAR System Organization",
        },
        {
            "title": "Public-Private Partnership Design Toolkit for Agriculture",
            "summary": "A toolkit for designing effective public-private partnerships (PPPs) in agriculture that leverage private sector capabilities and public sector mandates to achieve development outcomes at scale. Covers partnership structuring, risk sharing, and performance management.",
            "what_it_does": "Provides templates and frameworks for structuring agricultural PPPs, including partnership agreements, risk allocation matrices, and performance monitoring systems.",
            "when_to_use_it": "Use when exploring or establishing public-private partnerships for scaling agricultural innovations or market development.",
            "who_its_for": "Designed for government agencies, private sector entities, and development practitioners facilitating agricultural PPPs.",
            "pillars": ["Market Systems", "Policy and Regulatory"],
            "domains": ["Scaling Innovation"],
            "type": "Toolkit",
            "stage": "Prototype",
            "target_users": ["Government agencies", "Private sector entities", "Development Practitioner", "Funders and Donors"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["World Bank PPP Advisory", "GIZ Agricultural Development"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/ppp-toolkit",
            "cgspace_id": "ppp-toolkit",
            "source_organization": "World Bank",
        },
        # --- Geographic coverage: MENA ---
        {
            "title": "Water-Energy-Food Nexus Assessment for MENA",
            "summary": "An assessment framework for analyzing water-energy-food nexus dynamics in water-scarce MENA region contexts. Integrates quantitative modeling with stakeholder analysis to identify nexus trade-offs and synergies for policy coherence.",
            "what_it_does": "Provides an integrated assessment methodology for understanding WEF nexus interactions and developing coherent policy recommendations for water-scarce agricultural systems.",
            "when_to_use_it": "Use when developing integrated water-energy-food policies or assessing the cross-sector impacts of agricultural investments in water-scarce regions.",
            "who_its_for": "Designed for policymakers, researchers, and government agencies in water-scarce agricultural regions.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Framework",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Policymaker", "Researcher", "Government agencies", "Irrigation scheme managers"],
            "geography": ["MENA", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["IWMI MENA Programme", "ICARDA"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/wef-nexus-mena",
            "cgspace_id": "wef-nexus-mena",
            "source_organization": "IWMI",
        },
        {
            "title": "Dryland Agriculture Transformation Guide",
            "summary": "A guide for transforming dryland agricultural systems in arid and semi-arid regions through integrated approaches combining improved germplasm, water harvesting, conservation agriculture, and market linkages. Draws on evidence from North Africa and Central Asia.",
            "what_it_does": "Provides an integrated package of technical options and institutional arrangements for sustainably intensifying dryland farming systems.",
            "when_to_use_it": "Use when designing agricultural development programs in semi-arid and arid regions with limited water resources.",
            "who_its_for": "Designed for development practitioners, extension services, and researchers working in dryland farming systems.",
            "pillars": ["Market Systems", "Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Guide",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Extension services", "Researcher", "Farmers and Agro-pastoralists"],
            "geography": ["MENA", "Central and West Asia and North Africa (CWANA)", "Africa"],
            "authors": ["ICARDA", "ICRISAT Dryland Systems"],
            "date_published": date(2018, 1, 1),
            "source_url": "https://cgspace.cgiar.org/dryland-transformation",
            "cgspace_id": "dryland-transformation",
            "source_organization": "ICARDA",
        },
        {
            "title": "Saline Agriculture Adaptation Framework",
            "summary": "A framework for adapting agricultural systems to increasing soil and water salinity in coastal and irrigated areas. Covers salt-tolerant crop selection, soil management practices, irrigation management, and institutional support for farmers dealing with salinity challenges.",
            "what_it_does": "Provides an integrated approach for managing agricultural salinity including crop selection tools, soil amendment guidelines, and irrigation management protocols.",
            "when_to_use_it": "Use when addressing salinity challenges in coastal deltas, irrigated areas, or regions affected by rising groundwater salinity.",
            "who_its_for": "Designed for extension services, irrigation scheme managers, and researchers working on salinity management.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Framework",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Extension services", "Irrigation scheme managers", "Researcher", "Farmers and Agro-pastoralists"],
            "geography": ["MENA", "Asia", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["ICBA", "ICARDA Water and Land Management"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/saline-agriculture",
            "cgspace_id": "saline-agriculture",
            "source_organization": "ICBA",
        },
        # --- Geographic coverage: Europe ---
        {
            "title": "Agri-Food Innovation Ecosystem Mapping Tool",
            "summary": "A tool for mapping and assessing the innovation ecosystem supporting agri-food sector development in European and transitional economy contexts. Evaluates the research, education, advisory, and entrepreneurship components of agricultural innovation systems.",
            "what_it_does": "Maps the components and linkages of agri-food innovation ecosystems and identifies gaps and opportunities for strengthening innovation support.",
            "when_to_use_it": "Use when assessing the innovation ecosystem supporting agri-food sector development or designing innovation support programs.",
            "who_its_for": "Designed for policymakers, researchers, and government agencies supporting agricultural innovation.",
            "pillars": ["Policy and Regulatory", "Market Systems"],
            "domains": ["Scaling Innovation"],
            "type": "Tool",
            "stage": "Conceptual",
            "target_users": ["Policymaker", "Researcher", "Government agencies", "Private sector entities"],
            "geography": ["Europe", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["FAO Regional Office for Europe and Central Asia", "EU SCAR"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/innovation-ecosystem-mapping",
            "cgspace_id": "innovation-ecosystem-mapping",
            "source_organization": "FAO",
        },
        {
            "title": "Sustainable Intensification Assessment Framework",
            "summary": "A framework for assessing the sustainability of agricultural intensification pathways across productivity, environmental, economic, social, and human dimensions. Developed for use in European and global contexts to evaluate trade-offs in intensification strategies.",
            "what_it_does": "Provides a five-domain assessment methodology for evaluating agricultural intensification sustainability and identifying trade-offs across productivity and environmental dimensions.",
            "when_to_use_it": "Use when evaluating or comparing agricultural intensification strategies for their sustainability across multiple dimensions.",
            "who_its_for": "Designed for researchers, policymakers, and agricultural planners assessing intensification pathways.",
            "pillars": ["Monitoring, Evaluation and Learning", "Policy and Regulatory"],
            "domains": ["Agri-food Systems"],
            "type": "Framework",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Researcher", "Policymaker", "Government agencies"],
            "geography": ["Europe", "Global"],
            "authors": ["Rothamsted Research", "CGIAR Research Program on Dryland Systems"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/sustainable-intensification",
            "cgspace_id": "sustainable-intensification",
            "source_organization": "Rothamsted Research",
        },
        {
            "title": "European Agricultural Knowledge Transfer Matrix",
            "summary": "A matrix tool for evaluating and comparing the effectiveness of different knowledge transfer mechanisms used in European agricultural advisory systems. Assesses mechanisms including demonstrations, farmer groups, digital platforms, and peer-to-peer learning.",
            "what_it_does": "Provides a structured comparison matrix for evaluating knowledge transfer approaches across effectiveness, reach, cost-efficiency, and inclusiveness criteria.",
            "when_to_use_it": "Use when designing or reforming agricultural knowledge transfer programs and selecting the most appropriate mechanisms for different contexts.",
            "who_its_for": "Designed for extension services, policymakers, and researchers working on agricultural advisory systems.",
            "pillars": ["Policy and Regulatory", "Digital and Financial Services"],
            "domains": ["Scaling Innovation"],
            "type": "Matrix",
            "stage": "Prototype",
            "target_users": ["Extension services", "Policymaker", "Researcher", "Government agencies"],
            "geography": ["Europe", "Global"],
            "authors": ["EU AKIS Network", "FAO Knowledge Management Division"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/knowledge-transfer-matrix",
            "cgspace_id": "knowledge-transfer-matrix",
            "source_organization": "EU AKIS Network",
        },
        # --- Geographic coverage: Latin America ---
        {
            "title": "Indigenous Knowledge Integration Toolkit",
            "summary": "A toolkit for integrating indigenous and traditional ecological knowledge into agricultural research and development programs in Latin American contexts. Provides ethical protocols, participatory methods, and documentation standards for respectful knowledge integration.",
            "what_it_does": "Provides ethical frameworks and participatory methods for documenting, validating, and integrating indigenous agricultural knowledge into research and extension programs.",
            "when_to_use_it": "Use when working with indigenous communities on agricultural development projects or when seeking to integrate traditional knowledge into modern agricultural practices.",
            "who_its_for": "Designed for researchers, development practitioners, and community leaders working with indigenous agricultural communities.",
            "pillars": ["Gender Equality and Social Inclusion", "Policy and Regulatory"],
            "domains": ["Agri-food Systems"],
            "type": "Toolkit",
            "stage": "Prototype",
            "target_users": ["Researcher", "Development Practitioner", "Community leaders", "Local communities"],
            "geography": ["Latin America", "Asia", "Africa"],
            "authors": ["Bioversity International", "CATIE"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/indigenous-knowledge-toolkit",
            "cgspace_id": "indigenous-knowledge-toolkit",
            "source_organization": "Bioversity International",
        },
        {
            "title": "Landscape Restoration Decision Support Tool",
            "summary": "A decision support tool for planning and prioritizing landscape restoration interventions in degraded agricultural landscapes. Uses spatial analysis combined with socioeconomic assessment to identify optimal restoration strategies for Latin American and tropical contexts.",
            "what_it_does": "Combines spatial data with socioeconomic analysis to generate restoration priority maps and intervention recommendations for degraded agricultural landscapes.",
            "when_to_use_it": "Use when planning landscape restoration programs or prioritizing areas and approaches for land rehabilitation investments.",
            "who_its_for": "Designed for government agencies, development practitioners, and environmental organizations working on landscape restoration.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Tool",
            "stage": "Prototype",
            "target_users": ["Government agencies", "Development Practitioner", "Civil Society and INGOs", "Researcher"],
            "geography": ["Latin America", "Africa"],
            "authors": ["CIAT Tropical Forages", "WRI"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/landscape-restoration",
            "cgspace_id": "landscape-restoration",
            "source_organization": "Alliance of Bioversity-CIAT",
        },
        # --- Stage: Theoretical and diagnostics ---
        {
            "title": "Food Systems Transformation Assessment Method",
            "summary": "A diagnostic method for assessing the readiness and potential of food systems for transformation toward greater sustainability, resilience, and equity. Examines food system drivers, components, and outcomes at national and sub-national levels.",
            "what_it_does": "Provides a comprehensive diagnostic framework for understanding food system dynamics and identifying leverage points for transformation interventions.",
            "when_to_use_it": "Use when conducting food systems analyses for national food system pathway development or when designing transformative food system interventions.",
            "who_its_for": "Designed for policymakers, researchers, and development practitioners working on food systems transformation.",
            "pillars": ["Policy and Regulatory", "Market Systems"],
            "domains": ["Agri-food Systems"],
            "type": "Method",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Policymaker", "Researcher", "Government agencies", "Civil Society and INGOs"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["CGIAR Foresight Initiative", "IFPRI"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/food-systems-assessment",
            "cgspace_id": "food-systems-assessment",
            "source_organization": "IFPRI",
        },
        {
            "title": "Behavioral Insights for Agricultural Technology Adoption",
            "summary": "A theoretical framework applying behavioral economics insights to understand and promote agricultural technology adoption by smallholder farmers. Covers cognitive biases, social norms, default effects, and nudge interventions in agricultural contexts.",
            "what_it_does": "Provides a theoretical framework and practical toolkit for designing behaviorally-informed agricultural extension and technology promotion programs.",
            "when_to_use_it": "Use when designing technology adoption promotion strategies or when standard approaches have failed to achieve expected adoption rates.",
            "who_its_for": "Designed for researchers, extension services, and development practitioners seeking to improve technology uptake.",
            "pillars": ["Digital and Financial Services", "Market Systems"],
            "domains": ["Scaling Innovation"],
            "type": "Framework",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Researcher", "Extension services", "Development Practitioner", "Project and program managers"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["CIMMYT Adoption Studies", "World Bank Behavioral Insights Team"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/behavioral-insights-ag",
            "cgspace_id": "behavioral-insights-ag",
            "source_organization": "CIMMYT",
        },
        # --- Stage: Conceptual ---
        {
            "title": "Regenerative Agriculture Transition Framework",
            "summary": "A conceptual framework for guiding the transition from conventional to regenerative agriculture practices at farm and landscape levels. Defines transition stages, principles, and monitoring indicators for regenerative agricultural systems.",
            "what_it_does": "Provides a stage-based transition model for regenerative agriculture with clear principles, practices, and monitoring indicators for each transition stage.",
            "when_to_use_it": "Use when designing regenerative agriculture programs or developing policies to support the transition from conventional to regenerative farming.",
            "who_its_for": "Designed for researchers, policymakers, and extension services interested in regenerative agriculture transitions.",
            "pillars": ["Policy and Regulatory", "Monitoring, Evaluation and Learning"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Framework",
            "stage": "Conceptual",
            "target_users": ["Researcher", "Policymaker", "Extension services", "Farmers and Agro-pastoralists"],
            "geography": ["Global", "Europe", "Latin America"],
            "authors": ["Alliance of Bioversity International and CIAT", "Wageningen University"],
            "date_published": date(2024, 1, 1),
            "source_url": "https://cgspace.cgiar.org/regenerative-ag-framework",
            "cgspace_id": "regenerative-ag-framework",
            "source_organization": "Alliance of Bioversity-CIAT",
        },
        {
            "title": "One Health Approach for Agricultural Systems",
            "summary": "A conceptual framework integrating human health, animal health, and environmental health perspectives into agricultural systems analysis and intervention design. Addresses antimicrobial resistance, zoonotic disease risks, and pesticide exposure in agricultural contexts.",
            "what_it_does": "Provides an integrated analytical framework for identifying and managing health risks at the human-animal-environment interface in agricultural systems.",
            "when_to_use_it": "Use when designing agricultural programs that need to consider health outcomes or when assessing health risks in agricultural value chains.",
            "who_its_for": "Designed for researchers, policymakers, and development practitioners working at the agriculture-health nexus.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Agri-food Systems"],
            "type": "Framework",
            "stage": "Conceptual",
            "target_users": ["Researcher", "Policymaker", "Government agencies", "Humanitarian assistance practitioners"],
            "geography": ["Global", "Asia", "Africa"],
            "authors": ["ILRI One Health Program", "WHO", "FAO"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/one-health-agriculture",
            "cgspace_id": "one-health-agriculture",
            "source_organization": "ILRI",
        },
        # --- Additional items for under-represented types ---
        {
            "title": "Agricultural Extension Methods Comparison Matrix",
            "summary": "A decision matrix for comparing and selecting agricultural extension methods based on reach, cost, effectiveness, inclusiveness, and sustainability criteria. Covers 15 extension approaches from traditional field visits to digital platforms.",
            "what_it_does": "Provides a structured comparison of 15 extension methods across five performance criteria, helping managers select the optimal mix of extension approaches.",
            "when_to_use_it": "Use when designing or reforming extension programs and needing to select among multiple delivery approaches.",
            "who_its_for": "Designed for extension services managers, policymakers, and program designers.",
            "pillars": ["Policy and Regulatory", "Digital and Financial Services"],
            "domains": ["Scaling Innovation"],
            "type": "Matrix",
            "stage": "Established and field-tested",
            "target_users": ["Extension services", "Policymaker", "Project and program managers"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["GFRAS", "FAO Research and Extension Unit"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/extension-methods-matrix",
            "cgspace_id": "extension-methods-matrix",
            "source_organization": "GFRAS",
        },
        {
            "title": "Livestock Value Chain Gender Toolkit",
            "summary": "A toolkit for analyzing and addressing gender inequalities in livestock value chains. Provides diagnostic tools, intervention design templates, and monitoring indicators specifically adapted for livestock production, processing, and marketing contexts.",
            "what_it_does": "Enables gender analysis of livestock value chains and provides intervention design guidance for improving women's participation and benefits in livestock systems.",
            "when_to_use_it": "Use when designing livestock development programs or conducting gender analyses of livestock value chains.",
            "who_its_for": "Designed for development practitioners, researchers, and extension services working in livestock systems.",
            "pillars": ["Gender Equality and Social Inclusion", "Market Systems"],
            "domains": ["Agri-food Systems"],
            "type": "Toolkit",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Researcher", "Extension services", "Community leaders"],
            "geography": ["Africa", "Asia", "MENA"],
            "authors": ["ILRI Gender Team", "CGIAR Gender Platform"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/livestock-gender-toolkit",
            "cgspace_id": "livestock-gender-toolkit",
            "source_organization": "ILRI",
        },
        {
            "title": "Farmer Organization Maturity Scale",
            "summary": "A scale instrument for assessing the organizational maturity of farmer organizations across governance, financial management, service delivery, advocacy, and sustainability dimensions. Provides benchmarks and development pathways for organizational strengthening.",
            "what_it_does": "Measures farmer organization maturity across five dimensions using a standardized scale, generating a maturity profile and improvement roadmap.",
            "when_to_use_it": "Use when assessing the capacity of farmer organizations or designing organizational strengthening programs.",
            "who_its_for": "Designed for development practitioners, farmer organization leaders, and funders supporting organizational development.",
            "pillars": ["Market Systems", "Gender Equality and Social Inclusion"],
            "domains": ["Scaling Innovation"],
            "type": "Scale",
            "stage": "Established and field-tested",
            "target_users": ["Development Practitioner", "Community leaders", "Funders and Donors", "Farmers and Agro-pastoralists"],
            "geography": ["Africa", "Latin America", "Asia"],
            "authors": ["IFAD Institutions Team", "AgriCord"],
            "date_published": date(2018, 1, 1),
            "source_url": "https://cgspace.cgiar.org/farmer-org-maturity-scale",
            "cgspace_id": "farmer-org-maturity-scale",
            "source_organization": "IFAD",
        },
        {
            "title": "Nutrition-Sensitive Value Chain Manual",
            "summary": "A manual for designing agricultural value chains that maximize nutrition outcomes by addressing nutrient retention during processing, storage, and distribution, and by promoting dietary diversity through product differentiation and marketing.",
            "what_it_does": "Provides guidance for analyzing nutritional quality along value chains and designing interventions that improve nutrient content and dietary diversity of food products.",
            "when_to_use_it": "Use when designing value chain programs with nutrition objectives or when analyzing the nutrition impacts of value chain interventions.",
            "who_its_for": "Designed for development practitioners, nutrition specialists, and agribusinesses working on nutrition-sensitive agriculture.",
            "pillars": ["Market Systems", "Gender Equality and Social Inclusion"],
            "domains": ["Agri-food Systems"],
            "type": "Manual",
            "stage": "Prototype",
            "target_users": ["Development Practitioner", "Agribusiness", "Researcher", "Project and program managers"],
            "geography": ["Africa", "Asia", "Low-income and middle-income countries"],
            "authors": ["A4NH", "FAO Nutrition Division"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/nutrition-value-chain-manual",
            "cgspace_id": "nutrition-value-chain-manual",
            "source_organization": "CGIAR A4NH",
        },
        {
            "title": "Agricultural Insurance Product Design Guide",
            "summary": "A guide for designing agricultural insurance products including index-based crop insurance, livestock insurance, and weather-index insurance suitable for smallholder farming contexts. Covers product design, pricing, distribution, and regulatory requirements.",
            "what_it_does": "Provides step-by-step guidance for designing, pricing, and distributing agricultural insurance products with a focus on index-based approaches suitable for smallholder farmers.",
            "when_to_use_it": "Use when developing agricultural insurance products or programs for smallholder farmers in developing countries.",
            "who_its_for": "Designed for insurance companies, development practitioners, and policymakers working on agricultural risk management.",
            "pillars": ["Digital and Financial Services", "Market Systems"],
            "domains": ["Climate Resilience"],
            "type": "Guide",
            "stage": "Established and field-tested",
            "target_users": ["Private sector entities", "Development Practitioner", "Policymaker", "Farmers and Agro-pastoralists"],
            "geography": ["Africa", "Asia", "Latin America", "Low-income and middle-income countries"],
            "authors": ["IFAD Risk Management", "IFC Agriculture Insurance"],
            "date_published": date(2019, 1, 1),
            "source_url": "https://cgspace.cgiar.org/ag-insurance-guide",
            "cgspace_id": "ag-insurance-guide",
            "source_organization": "IFAD",
        },
        {
            "title": "Pastoralist Livelihood Resilience Scorecard",
            "summary": "A scorecard for assessing the resilience of pastoralist livelihoods in dryland systems. Measures resilience across herd dynamics, mobility access, market integration, social networks, and natural resource governance dimensions.",
            "what_it_does": "Assesses pastoralist livelihood resilience across five dimensions using participatory methods, generating resilience profiles for program targeting and impact monitoring.",
            "when_to_use_it": "Use when designing pastoralist development programs or monitoring resilience-building interventions in pastoral areas.",
            "who_its_for": "Designed for humanitarian assistance practitioners, development practitioners, and government agencies working with pastoralist communities.",
            "pillars": ["Gender Equality and Social Inclusion", "Policy and Regulatory"],
            "domains": ["Climate Resilience"],
            "type": "Scorecard",
            "stage": "Prototype",
            "target_users": ["Humanitarian assistance practitioners", "Development Practitioner", "Government agencies", "Community leaders"],
            "geography": ["Africa", "MENA", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["ILRI Pastoralism Programme", "IUCN Dryland Ecosystems"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/pastoralist-resilience-scorecard",
            "cgspace_id": "pastoralist-resilience-scorecard",
            "source_organization": "ILRI",
        },
        {
            "title": "Foresight and Scenario Planning Toolkit for Agriculture",
            "summary": "A toolkit for conducting foresight exercises and scenario planning for agricultural systems, enabling stakeholders to explore plausible futures and develop robust strategies that perform well across multiple scenarios.",
            "what_it_does": "Provides facilitation guides and analytical tools for conducting scenario planning exercises that inform long-term agricultural strategy development.",
            "when_to_use_it": "Use when developing long-term agricultural strategies or when needing to test the robustness of plans against uncertain future conditions.",
            "who_its_for": "Designed for policymakers, researchers, and program managers engaged in long-term agricultural planning.",
            "pillars": ["Policy and Regulatory", "Monitoring, Evaluation and Learning"],
            "domains": ["Agri-food Systems", "Climate Resilience"],
            "type": "Toolkit",
            "stage": "Theoretical and diagnostics",
            "target_users": ["Policymaker", "Researcher", "Project and program managers", "Government agencies"],
            "geography": ["Global", "Africa"],
            "authors": ["CGIAR Foresight Initiative", "IFPRI Foresight Team"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/foresight-toolkit",
            "cgspace_id": "foresight-toolkit",
            "source_organization": "IFPRI",
        },
        {
            "title": "Sustainable Land Management Decision Brief",
            "summary": "A policy brief format tool summarizing evidence on sustainable land management practices for drylands, including conservation agriculture, agroforestry, and water harvesting. Presents cost-benefit analysis and adoption barriers for policymakers.",
            "what_it_does": "Synthesizes evidence on sustainable land management options and presents cost-benefit comparisons to inform policy decisions on land management investments.",
            "when_to_use_it": "Use when briefing policymakers on sustainable land management options or when making investment cases for land restoration programs.",
            "who_its_for": "Designed for policymakers, government agencies, and funders making decisions about land management investments.",
            "pillars": ["Policy and Regulatory"],
            "domains": ["Climate Resilience", "Agri-food Systems"],
            "type": "Brief",
            "stage": "Established and field-tested",
            "target_users": ["Policymaker", "Government agencies", "Funders and Donors"],
            "geography": ["Africa", "MENA", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["ICARDA Land Management", "GIZ Soil Protection"],
            "date_published": date(2020, 1, 1),
            "source_url": "https://cgspace.cgiar.org/slm-decision-brief",
            "cgspace_id": "slm-decision-brief",
            "source_organization": "ICARDA",
        },
        {
            "title": "Aquaculture Sustainability Assessment Scorecard",
            "summary": "A scorecard for assessing the environmental, economic, and social sustainability of small-scale aquaculture operations. Covers feed efficiency, water quality management, disease risk, profitability, and community impacts.",
            "what_it_does": "Provides a standardized scoring framework for assessing aquaculture sustainability across environmental, economic, and social dimensions with benchmarks for improvement.",
            "when_to_use_it": "Use when evaluating the sustainability of aquaculture operations or designing programs to improve aquaculture practices.",
            "who_its_for": "Designed for extension services, researchers, and development practitioners working in aquaculture development.",
            "pillars": ["Market Systems", "Monitoring, Evaluation and Learning"],
            "domains": ["Agri-food Systems"],
            "type": "Scorecard",
            "stage": "Prototype",
            "target_users": ["Extension services", "Researcher", "Development Practitioner", "Farmers and Agro-pastoralists"],
            "geography": ["Asia", "Africa"],
            "authors": ["WorldFish", "FAO Fisheries Division"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/aquaculture-sustainability-scorecard",
            "cgspace_id": "aquaculture-sustainability-scorecard",
            "source_organization": "WorldFish",
        },
        {
            "title": "Digital Literacy Assessment for Rural Communities",
            "summary": "A diagnostic tool for assessing digital literacy levels in rural farming communities, covering device familiarity, internet usage, digital financial services, and information evaluation skills. Generates targeted training recommendations.",
            "what_it_does": "Assesses digital literacy across four domains and generates community-level digital literacy profiles with tailored training program recommendations.",
            "when_to_use_it": "Use before deploying digital agricultural services or when designing digital literacy training programs for rural communities.",
            "who_its_for": "Designed for extension services, development practitioners, and digital service providers working in rural areas.",
            "pillars": ["Digital and Financial Services", "Gender Equality and Social Inclusion"],
            "domains": ["Scaling Innovation"],
            "type": "Tool",
            "stage": "Prototype",
            "target_users": ["Extension services", "Development Practitioner", "Local communities", "Private sector entities"],
            "geography": ["Africa", "Asia", "Low-income and middle-income countries"],
            "authors": ["CTA Digital4Agriculture", "GSMA Connected Women"],
            "date_published": date(2022, 1, 1),
            "source_url": "https://cgspace.cgiar.org/digital-literacy-assessment",
            "cgspace_id": "digital-literacy-assessment",
            "source_organization": "CTA",
        },
        {
            "title": "Conflict-Sensitive Agriculture Programming Guide",
            "summary": "A guide for designing and implementing agricultural development programs in conflict-affected and fragile contexts. Covers conflict analysis, do-no-harm principles, and adaptive programming approaches for agricultural interventions in unstable environments.",
            "what_it_does": "Provides conflict analysis tools, do-no-harm assessment checklists, and adaptive programming guidance for agricultural interventions in fragile and conflict-affected settings.",
            "when_to_use_it": "Use when designing or implementing agricultural programs in conflict-affected, post-conflict, or fragile state contexts.",
            "who_its_for": "Designed for humanitarian assistance practitioners, development practitioners, and program managers working in fragile contexts.",
            "pillars": ["Policy and Regulatory", "Gender Equality and Social Inclusion"],
            "domains": ["Agri-food Systems"],
            "type": "Guide",
            "stage": "Prototype",
            "target_users": ["Humanitarian assistance practitioners", "Development Practitioner", "Project and program managers", "Civil Society and INGOs"],
            "geography": ["Africa", "MENA", "Central and West Asia and North Africa (CWANA)"],
            "authors": ["FAO Resilience Programme", "Mercy Corps"],
            "date_published": date(2021, 1, 1),
            "source_url": "https://cgspace.cgiar.org/conflict-sensitive-agriculture",
            "cgspace_id": "conflict-sensitive-agriculture",
            "source_organization": "FAO",
        },
        {
            "title": "Participatory Varietal Selection Methodology",
            "summary": "A methodology for involving farmers directly in crop variety selection and testing processes to ensure that released varieties match farmer preferences and local growing conditions. Covers trial design, farmer evaluation protocols, and feedback integration into breeding programs.",
            "what_it_does": "Provides protocols for designing and managing participatory variety trials with farmer panels, including evaluation criteria, scoring methods, and data analysis procedures.",
            "when_to_use_it": "Use during the variety evaluation and release stages of crop breeding programs to ensure farmer preferences inform variety selection decisions.",
            "who_its_for": "Designed for plant breeders, researchers, and extension services involved in crop improvement programs.",
            "pillars": ["Gender Equality and Social Inclusion"],
            "domains": ["Agri-food Systems", "Scaling Innovation"],
            "type": "Method",
            "stage": "Established and field-tested",
            "target_users": ["Researcher", "Extension services", "Farmers and Agro-pastoralists", "Development Practitioner"],
            "geography": ["Global", "Africa", "Asia"],
            "authors": ["CIMMYT Breeding Program", "IRRI Social Sciences"],
            "date_published": date(2017, 1, 1),
            "source_url": "https://cgspace.cgiar.org/pvs-methodology",
            "cgspace_id": "pvs-methodology",
            "source_organization": "CIMMYT",
        },
        {
            "title": "Nutrition-Sensitive Irrigation Toolkit",
            "summary": "A toolkit integrating nutrition objectives into irrigation program design and management. Addresses how irrigation investments can maximize nutrition outcomes through dietary diversification, homestead food production, and gender-equitable water access.",
            "what_it_does": "Provides design guidance and monitoring tools for ensuring that irrigation investments contribute to improved nutrition outcomes alongside agricultural productivity gains.",
            "when_to_use_it": "Use when designing irrigation programs to ensure they contribute to nutrition objectives and equitable water access.",
            "who_its_for": "Designed for irrigation scheme managers, development practitioners, and government agencies planning irrigation investments.",
            "pillars": ["Gender Equality and Social Inclusion", "Policy and Regulatory"],
            "domains": ["Agri-food Systems", "Climate Resilience"],
            "type": "Toolkit",
            "stage": "Conceptual",
            "target_users": ["Irrigation scheme managers", "Development Practitioner", "Government agencies", "Farmers and Agro-pastoralists"],
            "geography": ["Asia", "Africa", "Low-income and middle-income countries"],
            "authors": ["IWMI Nutrition-Water Nexus Team", "IFPRI"],
            "date_published": date(2023, 1, 1),
            "source_url": "https://cgspace.cgiar.org/nutrition-irrigation-toolkit",
            "cgspace_id": "nutrition-irrigation-toolkit",
            "source_organization": "IWMI",
        },
    ]
    return items


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

UPSERT_SQL = """
INSERT INTO tools (
    title, summary, what_it_does, when_to_use_it, who_its_for,
    pillars, domains, type, stage,
    target_users, geography, authors,
    date_published, source_url, source_organization,
    cgspace_id, is_visible
)
VALUES (
    %(title)s, %(summary)s, %(what_it_does)s, %(when_to_use_it)s, %(who_its_for)s,
    %(pillars)s, %(domains)s, %(type)s, %(stage)s,
    %(target_users)s, %(geography)s, %(authors)s,
    %(date_published)s, %(source_url)s, %(source_organization)s,
    %(cgspace_id)s, true
)
ON CONFLICT (cgspace_id) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    what_it_does = EXCLUDED.what_it_does,
    when_to_use_it = EXCLUDED.when_to_use_it,
    who_its_for = EXCLUDED.who_its_for,
    pillars = EXCLUDED.pillars,
    domains = EXCLUDED.domains,
    type = EXCLUDED.type,
    stage = EXCLUDED.stage,
    target_users = EXCLUDED.target_users,
    geography = EXCLUDED.geography,
    authors = EXCLUDED.authors,
    date_published = EXCLUDED.date_published,
    source_url = EXCLUDED.source_url,
    source_organization = EXCLUDED.source_organization,
    is_visible = true,
    updated_at = now()
RETURNING id;
"""


def insert_tool(conn, tool: dict) -> str:
    """Insert/upsert a single tool record. Return the tool UUID."""
    cur = conn.cursor()
    try:
        cur.execute(UPSERT_SQL, tool)
        row = cur.fetchone()
        conn.commit()
        return str(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def generate_and_store_embedding(tool_id: str, tool: dict) -> bool:
    """Generate and store embedding for a tool. Return success."""
    try:
        text = build_embedding_text(
            title=tool.get("title", ""),
            summary=tool.get("summary", ""),
            what_it_does=tool.get("what_it_does", ""),
            when_to_use_it=tool.get("when_to_use_it", ""),
            who_its_for=tool.get("who_its_for", ""),
        )
        embedding = generate_embedding(text)
        store_embedding(tool_id, embedding)
        return True
    except Exception as exc:
        logger.error("Embedding failed for %s: %s", tool.get("title"), exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()

    # 1. Load and map v2 data
    logger.info("Loading v2 data from /tmp/v2_items.json ...")
    v2_data = load_v2_data()

    v2_tools = v2_data.get("tools", [])
    v2_stories = v2_data.get("stories", [])
    logger.info("Found %d v2 tools and %d v2 stories", len(v2_tools), len(v2_stories))

    mapped_tools = []
    for t in v2_tools:
        try:
            mapped_tools.append(map_v2_tool(t))
        except Exception as exc:
            logger.error("Failed to map v2 tool %s: %s", t.get("id"), exc)

    for s in v2_stories:
        try:
            mapped_tools.append(map_v2_story(s))
        except Exception as exc:
            logger.error("Failed to map v2 story %s: %s", s.get("id"), exc)

    logger.info("Mapped %d items from v2 data", len(mapped_tools))

    # 2. Generate additional items
    logger.info("Generating additional items ...")
    additional = generate_additional_items()
    logger.info("Generated %d additional items", len(additional))

    # 3. Combine all items
    all_items = mapped_tools + additional
    logger.info("Total items to load: %d", len(all_items))

    # 4. Insert all into DB
    logger.info("Connecting to database ...")
    conn = psycopg2.connect(DATABASE_URL_SYNC)

    inserted_count = 0
    failed_count = 0
    tool_ids = {}  # cgspace_id -> uuid

    for i, item in enumerate(all_items, 1):
        cgspace_id = item["cgspace_id"]
        try:
            tool_uuid = insert_tool(conn, item)
            tool_ids[cgspace_id] = tool_uuid
            inserted_count += 1
            if i % 10 == 0 or i == len(all_items):
                logger.info("  Inserted %d / %d items ...", i, len(all_items))
        except Exception as exc:
            logger.error("  FAILED to insert %s: %s", cgspace_id, exc)
            failed_count += 1

    conn.close()
    logger.info("Insert complete: %d succeeded, %d failed", inserted_count, failed_count)

    # 5. Generate embeddings for all
    logger.info("Generating embeddings for %d tools ...", len(tool_ids))
    embed_ok = 0
    embed_fail = 0

    for i, (cgspace_id, tool_uuid) in enumerate(tool_ids.items(), 1):
        # Find the matching item
        item = next((it for it in all_items if it["cgspace_id"] == cgspace_id), None)
        if item is None:
            continue
        t0 = time.time()
        success = generate_and_store_embedding(tool_uuid, item)
        elapsed_ms = int((time.time() - t0) * 1000)
        if success:
            embed_ok += 1
            if i % 10 == 0 or i == len(tool_ids):
                logger.info("  Embedded %d / %d (%dms) ...", i, len(tool_ids), elapsed_ms)
        else:
            embed_fail += 1

    logger.info("Embedding complete: %d succeeded, %d failed", embed_ok, embed_fail)

    # 6. Print summary stats
    total_elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("BULK LOAD SUMMARY")
    print("=" * 60)
    print(f"Total items processed:    {len(all_items)}")
    print(f"  - V2 tools mapped:      {len(v2_tools)}")
    print(f"  - V2 stories mapped:    {len(v2_stories)}")
    print(f"  - Generated items:      {len(additional)}")
    print(f"DB inserts succeeded:     {inserted_count}")
    print(f"DB inserts failed:        {failed_count}")
    print(f"Embeddings succeeded:     {embed_ok}")
    print(f"Embeddings failed:        {embed_fail}")
    print(f"Total time:               {total_elapsed:.1f}s")
    print()

    # 7. Run verification queries
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    conn = psycopg2.connect(DATABASE_URL_SYNC)
    cur = conn.cursor()

    # Total tools
    cur.execute("SELECT count(*) FROM tools;")
    total_db = cur.fetchone()[0]
    print(f"\nTotal tools in DB: {total_db}")

    # Embeddings
    cur.execute("SELECT count(*) FROM tools WHERE embedding IS NOT NULL;")
    with_emb = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM tools WHERE embedding IS NULL;")
    without_emb = cur.fetchone()[0]
    print(f"With embeddings:   {with_emb}")
    print(f"Without embeddings:{without_emb}")

    # Distribution by pillar
    print("\nDistribution by pillar:")
    cur.execute("""
        SELECT unnest(pillars) AS pillar, count(*)
        FROM tools GROUP BY pillar ORDER BY count(*) DESC;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} {row[1]}")

    # Distribution by domain
    print("\nDistribution by domain:")
    cur.execute("""
        SELECT unnest(domains) AS domain, count(*)
        FROM tools GROUP BY domain ORDER BY count(*) DESC;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} {row[1]}")

    # Distribution by type
    print("\nDistribution by type:")
    cur.execute("""
        SELECT type, count(*) FROM tools GROUP BY type ORDER BY count(*) DESC;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} {row[1]}")

    # Distribution by stage
    print("\nDistribution by stage:")
    cur.execute("""
        SELECT stage, count(*) FROM tools GROUP BY stage ORDER BY count(*) DESC;
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} {row[1]}")

    # Sample similarity search
    print("\n" + "=" * 60)
    print("SAMPLE SIMILARITY SEARCH")
    print("Query: 'monitoring and evaluation for agriculture'")
    print("=" * 60)

    from pipeline.embeddings import generate_embedding as gen_emb
    query_vec = gen_emb("monitoring and evaluation for agriculture")
    vec_literal = "[" + ",".join(str(v) for v in query_vec) + "]"

    cur.execute("""
        SELECT title, 1 - (embedding <=> %s::vector) AS similarity
        FROM tools
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT 5;
    """, (vec_literal, vec_literal))

    for rank, (title, sim) in enumerate(cur.fetchall(), 1):
        print(f"  {rank}. {title} (similarity: {sim:.4f})")

    cur.close()
    conn.close()
    print()


if __name__ == "__main__":
    main()
