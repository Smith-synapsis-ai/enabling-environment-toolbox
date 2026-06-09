"""Generate synthetic CG Space items for batch processing tests.

Produces realistic agricultural research items in the format expected by the
EE Toolbox ingestion pipeline.  Approximately 70% of items are relevant
(tools, frameworks, methods, guides) and 30% are irrelevant (pure research
papers, annual reports, budget documents).

Usage::

    # As a module
    from pipeline.generate_test_data import generate_items, save_items
    items = generate_items(1000)
    save_items(items, "pipeline/test_data/synthetic_1k.json")

    # Standalone
    python -m pipeline.generate_test_data --count 1000 --output pipeline/test_data/synthetic_1k.json
"""

import argparse
import json
import os
import random as _stdlib_random
from typing import Optional


# ---------------------------------------------------------------------------
# Vocabulary pools
# ---------------------------------------------------------------------------

CGIAR_CENTERS = [
    "IFPRI",
    "CIMMYT",
    "IRRI",
    "ICRISAT",
    "ILRI",
    "WorldFish",
    "ICARDA",
    "CIP",
    "IITA",
    "Alliance of Bioversity International and CIAT",
    "IWMI",
    "CIFOR-ICRAF",
    "AfricaRice",
]

PARTNER_ORGS = [
    "FAO",
    "World Bank",
    "USAID",
    "GIZ",
    "DFID",
    "IFAD",
    "UNDP",
    "WFP",
    "CGAP",
    "GSMA",
    "KIT Royal Tropical Institute",
    "Wageningen University",
    "Cornell University",
    "Michigan State University",
    "University of Reading",
    "OECD",
    "African Development Bank",
    "Asian Development Bank",
]

RESEARCHER_FIRST_NAMES = [
    "Arun", "Maria", "Kebede", "Fatima", "Raj", "Grace", "Pierre",
    "Ngoc", "Sarah", "David", "Amina", "Carlos", "Priya", "John",
    "Mei", "Hassan", "Elena", "Kwame", "Luz", "Ahmed", "Beatrice",
    "Fernando", "Deepa", "Solomon", "Nadia", "Peter", "Olga",
    "Ibrahim", "Anna", "Ravi", "Comfort", "Jean-Pierre", "Linh",
    "Martha", "Suresh", "Claudia", "Abdi", "Rosa", "Tao", "Janet",
]

RESEARCHER_LAST_NAMES = [
    "Singh", "Muriuki", "Nguyen", "Garcia", "Deshpande", "Osei",
    "Tanaka", "Martinez", "Patel", "Adeyemi", "Schmidt", "Kim",
    "Wangari", "Lopez", "Choudhury", "Diallo", "Okello", "Silva",
    "Kumari", "Mensah", "Chen", "Bello", "Sharma", "Abera",
    "Nkomo", "Ramirez", "Gupta", "Banda", "Tran", "Mwangi",
    "De Leeuw", "Coulibaly", "Joshi", "Owusu", "Ahmad", "Tessema",
]

REGIONS = [
    "East Africa",
    "West Africa",
    "Southern Africa",
    "Sub-Saharan Africa",
    "South Asia",
    "Southeast Asia",
    "Central Asia",
    "Latin America",
    "Central America",
    "Andean Region",
    "MENA",
    "Sahel",
    "Indo-Gangetic Plain",
    "Mekong Delta",
    "Horn of Africa",
    "Great Lakes Region",
]

COUNTRIES = [
    "Kenya", "Ethiopia", "Tanzania", "Uganda", "Rwanda", "Malawi",
    "Mozambique", "Ghana", "Nigeria", "Senegal", "Mali", "Burkina Faso",
    "Niger", "Bangladesh", "India", "Nepal", "Myanmar", "Vietnam",
    "Cambodia", "Philippines", "Indonesia", "Peru", "Colombia",
    "Guatemala", "Honduras", "Morocco", "Tunisia", "Egypt", "Jordan",
    "Pakistan", "Sri Lanka", "Madagascar", "Zambia", "Zimbabwe",
]

CROPS = [
    "rice", "wheat", "maize", "sorghum", "millet", "cassava",
    "sweet potato", "potato", "groundnut", "cowpea", "chickpea",
    "lentil", "soybean", "banana", "plantain", "yam", "teff",
    "barley", "beans", "pigeon pea", "sesame", "sunflower",
]

LIVESTOCK = [
    "cattle", "poultry", "goats", "sheep", "pigs", "camels",
    "dairy cows", "indigenous chicken", "small ruminants",
]

# -- Topics and modifiers for relevant items --

RELEVANT_TOOL_TOPICS = [
    "Climate-Smart Agriculture",
    "Participatory Seed System",
    "Gender-Responsive Value Chain",
    "Nutrition-Sensitive Agriculture",
    "Digital Extension Services",
    "Agricultural Policy Reform",
    "Market Systems Development",
    "Smallholder Financial Inclusion",
    "Irrigation Governance",
    "Agroforestry Scaling",
    "Food Safety Regulation",
    "Livestock Value Chain",
    "Post-Harvest Loss Reduction",
    "Soil Health Management",
    "Integrated Pest Management",
    "Agricultural Innovation Platform",
    "Rural Advisory Services",
    "Water Resource Management",
    "Farmer Organization Strengthening",
    "Agricultural Trade Policy",
    "Climate Vulnerability Assessment",
    "Inclusive Agribusiness",
    "Land Governance",
    "Drought Resilience",
    "Food Systems Transformation",
    "One Health Agriculture",
    "Aquaculture Sustainability",
    "Pastoralist Livelihood",
    "Digital Agriculture",
    "Agricultural Mechanization",
    "Seed Quality Assurance",
    "Youth Agripreneurship",
    "Social Inclusion Monitoring",
    "Conflict-Sensitive Programming",
    "Regenerative Agriculture",
    "Landscape Restoration",
    "Knowledge Transfer",
    "Multi-Stakeholder Platform",
    "Impact Evaluation",
    "Adaptive Management",
    "Theory of Change",
    "Climate Services",
    "Agricultural Insurance",
    "Greenhouse Gas Estimation",
    "Value Chain Finance",
    "Crop-Livestock Integration",
    "Agri-Food Innovation",
    "Scaling Readiness",
    "Enabling Environment Assessment",
    "Capacity Building",
]

RELEVANT_TOOL_TYPES_AND_NOUNS = [
    ("Framework", "Framework"),
    ("Framework", "Assessment Framework"),
    ("Method", "Method"),
    ("Method", "Methodology"),
    ("Method", "Approach"),
    ("Tool", "Tool"),
    ("Tool", "Diagnostic Tool"),
    ("Tool", "Decision Support Tool"),
    ("Guide", "Guide"),
    ("Guide", "Implementation Guide"),
    ("Guide", "Practical Guide"),
    ("Manual", "Manual"),
    ("Manual", "Field Manual"),
    ("Manual", "Training Manual"),
    ("Toolkit", "Toolkit"),
    ("Toolkit", "Practitioner Toolkit"),
    ("Scorecard", "Scorecard"),
    ("Scorecard", "Performance Scorecard"),
    ("Scale", "Assessment Scale"),
    ("Matrix", "Decision Matrix"),
    ("Brief", "Policy Brief"),
]

RELEVANT_ABSTRACT_TEMPLATES = [
    "A {doc_noun} for {action} in {context}. {method_sentence} {outcome_sentence}",
    "This {doc_noun} provides {what} for {who} working on {topic} in {region}. {method_sentence}",
    "Designed for {who}, this {doc_noun} enables {action} across {dimension}. {outcome_sentence}",
    "{action_cap} is critical for {goal}. This {doc_noun} provides {what} to {purpose}. {outcome_sentence}",
    "This {doc_noun} supports {who} in {action} by providing {what}. {method_sentence} {outcome_sentence}",
]

RELEVANT_ACTIONS = [
    "assessing the enabling environment for agricultural innovation",
    "strengthening institutional capacity for scaling",
    "designing gender-responsive agricultural programs",
    "evaluating market system performance",
    "monitoring climate adaptation outcomes",
    "integrating nutrition objectives into agricultural investments",
    "improving policy coherence for food security",
    "building resilience of smallholder farming systems",
    "scaling digital financial services for rural populations",
    "facilitating multi-stakeholder dialogue on food systems",
    "evaluating innovation readiness for scaling investments",
    "assessing water governance and irrigation management",
    "strengthening farmer organizations and cooperatives",
    "designing inclusive agricultural value chains",
    "tracking progress toward sustainable development goals",
    "promoting climate-smart agricultural practices",
    "improving post-harvest management and food safety",
    "supporting youth engagement in agricultural entrepreneurship",
    "assessing land tenure and governance systems",
    "designing agricultural knowledge and innovation systems",
]

RELEVANT_METHODS = [
    "Uses a multi-criteria scoring approach validated across multiple countries.",
    "Combines participatory methods with quantitative indicators for comprehensive assessment.",
    "Integrates stakeholder analysis with evidence-based benchmarking.",
    "Applies a stage-gate methodology for systematic evaluation.",
    "Draws on field-tested protocols from programs across Africa and Asia.",
    "Employs mixed-methods diagnostics combining surveys, key informant interviews, and secondary data.",
    "Provides standardized indicators aligned with international reporting frameworks.",
    "Uses a modular design allowing adaptation to different country contexts.",
    "Incorporates gender-disaggregated data collection and analysis protocols.",
    "Leverages digital tools for real-time data collection and visualization.",
]

RELEVANT_OUTCOMES = [
    "Field-tested in over 15 countries across three continents.",
    "Applied successfully by development organizations and government agencies in multiple regions.",
    "Generates actionable recommendations for program design and policy reform.",
    "Provides benchmarks for tracking progress over time.",
    "Enables evidence-based decision-making for resource allocation.",
    "Supports adaptive management through regular monitoring and feedback cycles.",
    "Improves targeting of interventions to reach the most vulnerable populations.",
    "Strengthens accountability and learning in agricultural development programs.",
    "Facilitates coordination among diverse stakeholders in agricultural innovation systems.",
    "Contributes to improved food security and nutrition outcomes for smallholder households.",
]

RELEVANT_WHATS = [
    "structured assessment tools and indicators",
    "practical guidance and decision-support frameworks",
    "diagnostic instruments and benchmarking templates",
    "step-by-step implementation protocols",
    "participatory assessment methods and scoring rubrics",
    "monitoring indicators and data collection instruments",
    "analytical frameworks and evaluation criteria",
    "facilitation guides and stakeholder engagement tools",
    "policy analysis instruments and reform roadmaps",
    "training modules and capacity building resources",
]

RELEVANT_WHOS = [
    "policymakers and government agencies",
    "development practitioners and program managers",
    "researchers and monitoring specialists",
    "extension services and farmer organizations",
    "civil society organizations and INGOs",
    "private sector actors and agribusinesses",
    "funders and development investors",
    "community leaders and local institutions",
]

RELEVANT_CONTEXTS = [
    "smallholder farming systems",
    "agricultural value chains",
    "food systems transformation initiatives",
    "climate adaptation programming",
    "rural development programs",
    "agricultural innovation scaling",
    "food security interventions",
    "agricultural policy reform processes",
    "market systems development programs",
    "resilience building initiatives",
]

RELEVANT_DIMENSIONS = [
    "productivity, sustainability, and equity dimensions",
    "governance, capacity, and market access pillars",
    "environmental, economic, and social sustainability criteria",
    "absorptive, adaptive, and transformative resilience capacities",
    "policy, institutional, and market enabling conditions",
    "food availability, access, utilization, and stability domains",
]

RELEVANT_GOALS = [
    "achieving food security and improved nutrition",
    "scaling agricultural innovations to reach millions of smallholders",
    "building climate resilience in vulnerable farming communities",
    "transforming food systems for sustainability and equity",
    "strengthening enabling environments for agricultural development",
    "promoting inclusive economic growth in rural areas",
]

# -- Irrelevant item vocabulary --

IRRELEVANT_DOC_TYPES = [
    "Journal Article",
    "Journal Article",
    "Journal Article",
    "Working Paper",
    "Conference Paper",
    "Report",
    "Book Chapter",
    "Thesis",
    "Dataset",
]

IRRELEVANT_TITLE_TEMPLATES = [
    "Genome-Wide Association Study of {trait} Resistance in {crop} Cultivars",
    "Transcriptomic Profiling of {stress} Response in {crop}: Implications for Breeding",
    "Phylogenetic Analysis of {organism} Species in {region} {livestock}",
    "Effect of {treatment} Rates on {crop} Yield: A Meta-Analysis of {n} Field Trials",
    "Genetic Diversity of Indigenous {livestock} Breeds in {country}: {method} Analysis",
    "Spatial Distribution of {contaminant} Contamination in {crop} Markets of {country}",
    "Optimizing {process} for Maximum {quality} in {crop} Varieties",
    "Modeling {process} Dynamics Under Different {system} Systems in {region}",
    "Consumer Preferences for {crop} Products in Urban {country}",
    "Estimating {measurement} from Remote Sensing Data in the {region}",
    "Historical Analysis of {measurement} Patterns in the {region}",
    "Nutritional Composition of {foodtype} in {region}",
    "Pathogenicity Testing of {organism} on {crop} Cultivars in {region}",
    "Proceedings of the {n}th International Symposium on {crop} Genetics",
    "CGIAR Annual Report {year}: {center}",
    "{center} Financial Statements and Audit Report {year}",
    "Board of Trustees Meeting Minutes: {center} {year}",
    "Protein Structure Prediction for {organism} Effector Genes Using AlphaFold",
    "Whole-Genome Sequencing of {crop} Landraces from {country}",
    "Soil Microbiome Characterization Under {crop} Monoculture in {region}",
    "Quantitative Trait Loci Mapping for {trait} in {crop}",
    "CRISPR-Cas9 Gene Editing for {trait} in {crop}: Progress and Challenges",
    "Molecular Markers for {trait} Screening in {crop} Breeding Programs",
    "Long-Term Trends in {measurement} Across {region}: A 50-Year Analysis",
]

IRRELEVANT_ABSTRACT_TEMPLATES = [
    "We conducted {method} involving {n} {organism} accessions to identify {target}. Using {technique}, we identified {finding}. These findings advance our understanding of {topic} and offer targets for {application}.",
    "This study presents {method} of {organism} isolated from {n} {source} across {region}. {technique_sentence} Results have implications for {application}.",
    "Using {n} years of {data_type} from {n2} {source}, we analyzed {target}. Results show {finding}, with implications for {application}.",
    "We performed {method} on {organism} at {n} developmental stages to identify {target}. Analysis of {n2} {unit} revealed {finding}. We identified {n3} candidate genes for {application}.",
    "Field trials across {n} agro-ecological zones in {country} evaluated {target}. {finding_sentence} Results provide {application}.",
    "This {doc_type} summarizes {center}'s research outputs, financial performance, partnerships, and organizational developments during fiscal year {year}. Highlights include {finding}.",
    "These proceedings compile {n} papers presented at the {n2}th International Symposium, covering advances in {topic}. Topics include {technique_list}.",
    "We assessed {target} using {technique} genotyped across {n} individuals. {finding_sentence} Results inform {application}.",
    "Using {technique}, we {method_verb} {target} across {n} sites in {region}. The model achieved {metric} and provides {application}.",
]

IRRELEVANT_METHODS_VOCAB = [
    "genome-wide association study",
    "RNA sequencing analysis",
    "phylogenetic analysis",
    "meta-analysis",
    "microsatellite genotyping",
    "whole-genome sequencing",
    "HPLC and ELISA methods",
    "maximum likelihood inference",
    "Bayesian clustering analysis",
    "remote sensing classification",
]

IRRELEVANT_TECHNIQUES = [
    "45,000 single nucleotide polymorphisms",
    "mitochondrial DNA sequencing",
    "30 microsatellite markers",
    "MODIS and Landsat imagery",
    "ICP-MS for mineral content",
    "CRISPR-Cas9 gene editing",
    "pan-genome analysis",
    "RothC soil carbon model",
    "eddy covariance flux tower measurements",
    "next-generation sequencing",
]

IRRELEVANT_TRAITS = [
    "blast resistance", "drought tolerance", "heat tolerance",
    "rust resistance", "salt tolerance", "waterlogging tolerance",
    "insect resistance", "grain quality", "protein content",
    "starch content", "iron biofortification", "zinc biofortification",
]

IRRELEVANT_ORGANISMS = [
    "Fusarium", "Magnaporthe oryzae", "Trypanosoma", "Striga",
    "Xanthomonas", "Pyricularia", "Phytophthora", "Colletotrichum",
]

IRRELEVANT_CONTAMINANTS = [
    "aflatoxin", "pesticide residue", "heavy metal", "mycotoxin",
    "cadmium", "lead", "fumonisin",
]

IRRELEVANT_PROCESSES = [
    "nitrogen fertilization", "phosphorus application", "tillage",
    "irrigation scheduling", "harvest timing", "drying",
    "fermentation", "seed priming", "grafting",
]

IRRELEVANT_MEASUREMENTS = [
    "evapotranspiration", "rainfall", "soil carbon",
    "groundwater level", "surface temperature", "solar radiation",
    "crop water productivity", "soil organic matter",
]

IRRELEVANT_SYSTEMS = [
    "tillage", "cropping", "irrigation", "intercropping",
    "agroforestry", "conservation agriculture", "rotation",
]

IRRELEVANT_FOOD_TYPES = [
    "wild edible plants", "indigenous vegetables", "traditional cereals",
    "underutilized legumes", "fermented foods", "bush foods",
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _make_researchers(rng: _stdlib_random.Random, n: int = 2) -> str:
    """Generate a comma-separated string of n researcher names."""
    names = []
    for _ in range(n):
        first = rng.choice(RESEARCHER_FIRST_NAMES)
        last = rng.choice(RESEARCHER_LAST_NAMES)
        names.append(f"{first} {last}")
    return ", ".join(names)


def _make_authors_relevant(rng: _stdlib_random.Random) -> str:
    """Build an author string for a relevant item (center + researchers)."""
    center = rng.choice(CGIAR_CENTERS)
    n_researchers = rng.choice([1, 2, 2, 3])
    researchers = _make_researchers(rng, n_researchers)
    # Sometimes add a partner org.
    if rng.random() < 0.4:
        partner = rng.choice(PARTNER_ORGS)
        return f"{researchers}, {center}, {partner}"
    return f"{researchers}, {center}"


def _make_authors_irrelevant(rng: _stdlib_random.Random) -> str:
    """Build an author string for an irrelevant item."""
    n = rng.choice([2, 3, 3, 4])
    researchers = _make_researchers(rng, n)
    if rng.random() < 0.3:
        center = rng.choice(CGIAR_CENTERS)
        return f"{researchers}, {center}"
    return researchers


def _make_url(index: int, rng: _stdlib_random.Random) -> str:
    """Generate a CG Space URL."""
    handle_a = rng.randint(10000, 19999)
    handle_b = rng.randint(100000, 199999)
    return f"https://cgspace.cgiar.org/handle/{handle_a}/{handle_b}"


def _generate_relevant_item(
    index: int, rng: _stdlib_random.Random
) -> dict:
    """Generate a single relevant (tool/framework/guide) item."""
    topic = rng.choice(RELEVANT_TOOL_TOPICS)
    doc_type_raw, doc_noun = rng.choice(RELEVANT_TOOL_TYPES_AND_NOUNS)
    region = rng.choice(REGIONS)

    # Build title -- vary the pattern.
    title_patterns = [
        f"{topic} {doc_noun} for {region}",
        f"{topic} {doc_noun}",
        f"{doc_noun} for {topic} in {region}",
        f"{topic}: A {doc_noun} for Development Practitioners",
        f"{doc_noun} for {topic}",
        f"Strengthening {topic}: A Practical {doc_noun}",
        f"{topic} {doc_noun} for Smallholder Systems",
        f"{region} {topic} {doc_noun}",
    ]
    title = rng.choice(title_patterns)

    # Build abstract from templates.
    template = rng.choice(RELEVANT_ABSTRACT_TEMPLATES)
    abstract = template.format(
        doc_noun=doc_noun.lower(),
        action=rng.choice(RELEVANT_ACTIONS),
        action_cap=rng.choice(RELEVANT_ACTIONS).capitalize(),
        context=rng.choice(RELEVANT_CONTEXTS),
        method_sentence=rng.choice(RELEVANT_METHODS),
        outcome_sentence=rng.choice(RELEVANT_OUTCOMES),
        what=rng.choice(RELEVANT_WHATS),
        who=rng.choice(RELEVANT_WHOS),
        topic=topic.lower(),
        region=region,
        dimension=rng.choice(RELEVANT_DIMENSIONS),
        goal=rng.choice(RELEVANT_GOALS),
        purpose=rng.choice(RELEVANT_ACTIONS),
    )

    authors = _make_authors_relevant(rng)
    year = str(rng.randint(2015, 2024))

    return {
        "title": title,
        "abstract": abstract,
        "doc_type": doc_type_raw,
        "authors": authors,
        "date": year,
        "url": _make_url(index, rng),
        "cgspace_id": f"synthetic-{index:04d}",
    }


def _generate_irrelevant_item(
    index: int, rng: _stdlib_random.Random
) -> dict:
    """Generate a single irrelevant (pure research / admin) item."""
    doc_type = rng.choice(IRRELEVANT_DOC_TYPES)

    # Pick substitution values.
    crop = rng.choice(CROPS)
    country = rng.choice(COUNTRIES)
    region = rng.choice(REGIONS)
    livestock_str = rng.choice(LIVESTOCK)
    center = rng.choice(CGIAR_CENTERS)
    year_val = str(rng.randint(2015, 2024))
    n_val = str(rng.randint(20, 500))
    trait = rng.choice(IRRELEVANT_TRAITS)
    organism = rng.choice(IRRELEVANT_ORGANISMS)
    contaminant = rng.choice(IRRELEVANT_CONTAMINANTS)
    process = rng.choice(IRRELEVANT_PROCESSES)
    measurement = rng.choice(IRRELEVANT_MEASUREMENTS)
    system = rng.choice(IRRELEVANT_SYSTEMS)
    foodtype = rng.choice(IRRELEVANT_FOOD_TYPES)
    stress = rng.choice(["drought", "heat", "salinity", "cold", "flooding"])
    quality = rng.choice(["starch content", "protein yield", "oil content", "fiber quality"])
    treatment = rng.choice(["nitrogen fertilization", "phosphorus application", "potassium", "zinc foliar spray"])
    method_type = rng.choice(["microsatellite", "SNP", "AFLP", "SSR"])

    title_template = rng.choice(IRRELEVANT_TITLE_TEMPLATES)
    title = title_template.format(
        trait=trait,
        crop=crop,
        stress=stress,
        organism=organism,
        region=region,
        livestock=livestock_str,
        treatment=treatment,
        n=n_val,
        contaminant=contaminant,
        country=country,
        process=process,
        quality=quality,
        system=system,
        measurement=measurement,
        foodtype=foodtype,
        year=year_val,
        center=center,
        method=method_type,
    )

    # Build abstract.
    abstract_template = rng.choice(IRRELEVANT_ABSTRACT_TEMPLATES)
    technique = rng.choice(IRRELEVANT_TECHNIQUES)
    irr_method = rng.choice(IRRELEVANT_METHODS_VOCAB)
    n2_val = str(rng.randint(10, 200))
    n3_val = str(rng.randint(5, 30))

    abstract = abstract_template.format(
        method=irr_method,
        n=n_val,
        n2=n2_val,
        n3=n3_val,
        organism=crop,
        source=rng.choice(["weather stations", "field sites", "market locations", "farms", "households"]),
        region=region,
        technique=technique,
        technique_sentence=f"Using {technique}, we characterized genetic structure and diversity patterns.",
        finding=f"significant variation in {trait} across populations, with {rng.randint(3, 20)} distinct clusters identified",
        finding_sentence=f"Results revealed significant genotype-by-environment interactions for {trait}.",
        target=f"quantitative trait loci associated with {trait}",
        topic=f"the genetic architecture of {trait} in {crop}",
        application=f"marker-assisted breeding programs for improved {crop} varieties",
        data_type=rng.choice(["daily rainfall records", "temperature data", "soil samples", "yield records"]),
        doc_type=doc_type.lower(),
        center=center,
        year=year_val,
        country=country,
        metric=f"R-squared values of {rng.uniform(0.7, 0.95):.2f}",
        method_verb=rng.choice(["analyzed", "characterized", "mapped", "modeled", "evaluated"]),
        technique_list=f"{rng.choice(IRRELEVANT_TECHNIQUES)}, {rng.choice(IRRELEVANT_TECHNIQUES)}, and {rng.choice(IRRELEVANT_TECHNIQUES)}",
        unit=rng.choice(["transcripts", "markers", "accessions", "samples", "isolates"]),
    )

    authors = _make_authors_irrelevant(rng)

    return {
        "title": title,
        "abstract": abstract,
        "doc_type": doc_type,
        "authors": authors,
        "date": year_val,
        "url": _make_url(index, rng),
        "cgspace_id": f"synthetic-{index:04d}",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_items(n: int, seed: int = 42) -> list[dict]:
    """Generate *n* synthetic CG Space items.

    Approximately 70% of items will be relevant (tools, frameworks, guides,
    etc.) and 30% will be irrelevant (pure research, admin documents).

    Args:
        n: Number of items to generate.
        seed: Random seed for reproducibility.

    Returns:
        A list of item dicts matching the ingestion pipeline input format.
    """
    rng = _stdlib_random.Random(seed)

    # Decide which indices are relevant vs. irrelevant.
    # Build an ordered list, then shuffle so they're interleaved.
    n_relevant = int(n * 0.7)
    assignments = ["relevant"] * n_relevant + ["irrelevant"] * (n - n_relevant)
    rng.shuffle(assignments)

    items: list[dict] = []
    for i, assignment in enumerate(assignments):
        if assignment == "relevant":
            item = _generate_relevant_item(i, rng)
        else:
            item = _generate_irrelevant_item(i, rng)
        items.append(item)

    return items


def save_items(items: list[dict], path: str) -> None:
    """Write items to a JSON file, creating parent directories as needed.

    Args:
        items: List of item dicts to save.
        path: Output file path.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as fp:
        json.dump(items, fp, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} items to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic CG Space items for batch processing tests.",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=1000,
        help="Number of items to generate (default: 1000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="pipeline/test_data/synthetic_1k.json",
        help="Output JSON file path (default: pipeline/test_data/synthetic_1k.json).",
    )

    args = parser.parse_args()

    print(f"Generating {args.count} synthetic items (seed={args.seed})...")
    items = generate_items(args.count, seed=args.seed)

    # Print summary.
    relevant_count = sum(
        1 for item in items
        if item["doc_type"] not in {
            "Journal Article", "Conference Paper", "Thesis",
            "Dataset", "Book Chapter",
        }
        and "Annual Report" not in item.get("title", "")
        and "Financial Statements" not in item.get("title", "")
        and "Board of Trustees" not in item.get("title", "")
    )
    irrelevant_count = len(items) - relevant_count

    print(f"  Relevant items:   ~{relevant_count}")
    print(f"  Irrelevant items: ~{irrelevant_count}")

    # Count doc types.
    from collections import Counter
    doc_types = Counter(item["doc_type"] for item in items)
    print("\n  Doc type distribution:")
    for dt, count in doc_types.most_common():
        print(f"    {dt:25s} {count}")

    save_items(items, args.output)


if __name__ == "__main__":
    main()
