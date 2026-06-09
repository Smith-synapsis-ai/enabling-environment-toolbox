"""
Build the test dataset from the ee-toolbox-v2 items.ts data.

Maps v2 pillar/domain/type/geography names to the correct taxonomy values
and writes the test set to pipeline/test_data/extraction_test_set.json.
"""

import json
import os

# ── Pillar Mapping ────────────────────────────────────────────────────────────
# v2 name -> list of correct taxonomy pillar names
PILLAR_MAP = {
    "Policy & Institutional": ["Policy and Regulatory"],
    "Gender & Social Inclusion": ["Gender Equality and Social Inclusion"],
    "Financial Services & M&E": ["Monitoring, Evaluation and Learning"],
    "Market Systems & Digital": ["Market Systems"],
    "Digital & Innovation": ["Digital and Financial Services"],
    "Digital": ["Digital and Financial Services"],
    "Market Systems": ["Market Systems"],
}

# ── Domain (Enabler) Mapping ─────────────────────────────────────────────────
DOMAIN_MAP = {
    "Scaling of Innovation": "Scaling Innovation",
    "Improved Agri-Food Systems": "Agri-food Systems",
    "Climate & Natural Resources": "Climate Resilience",
    "Climate Resilience": "Climate Resilience",
}

# ── Type Mapping ──────────────────────────────────────────────────────────────
TYPE_MAP = {
    "Framework": "Framework",
    "Method": "Method",
    "Tool": "Tool",
    "Approach": "Method",      # closest valid type
    "Scorecard": "Scorecard",
    "Guidelines": "Guide",     # closest valid type
}

# ── Stage Mapping ─────────────────────────────────────────────────────────────
STAGE_MAP = {
    "Established and field-tested": "Established and field-tested",
    "Emerging": "Prototype",   # closest valid stage
    "Pilot": "Prototype",     # closest valid stage
}

# ── Region to Geography Mapping ──────────────────────────────────────────────
REGION_MAP = {
    "East Africa": "Africa",
    "West Africa": "Africa",
    "Southern Africa": "Africa",
    "Sub-Saharan Africa": "Africa",
    "South Asia": "Asia",
    "Southeast Asia": "Asia",
    "Latin America": "Latin America",
    "MENA": "MENA",
    "Europe": "Europe",
    "Central Asia": "Asia",
    "Global": "Global",
}


def map_pillars(v2_pillars: list[str]) -> list[str]:
    """Map v2 pillar names to taxonomy pillar names."""
    result = []
    for p in v2_pillars:
        mapped = PILLAR_MAP.get(p, [])
        for m in mapped:
            if m not in result:
                result.append(m)
    return result


def map_domains(v2_enablers: list[str]) -> list[str]:
    """Map v2 enabler names to taxonomy domain names."""
    result = []
    for e in v2_enablers:
        mapped = DOMAIN_MAP.get(e, None)
        if mapped and mapped not in result:
            result.append(mapped)
    return result


def map_type(v2_type: str) -> str:
    """Map v2 type to taxonomy type."""
    return TYPE_MAP.get(v2_type, v2_type)


def map_stage(v2_stage: str) -> str:
    """Map v2 stage to taxonomy stage."""
    return STAGE_MAP.get(v2_stage, v2_stage)


def map_geography(regions: list[str], countries: list[str]) -> list[str]:
    """Map v2 regions/countries to taxonomy geography values."""
    result = []
    for r in regions:
        mapped = REGION_MAP.get(r, None)
        if mapped and mapped not in result:
            result.append(mapped)
    # If no regions mapped, try to infer from countries
    if not result and countries:
        result.append("Global")
    return result


def infer_target_users(title: str, description: str, pillars: list[str]) -> list[str]:
    """Infer target users from the tool description and pillars."""
    users = []
    text = (title + " " + description).lower()

    if any(w in text for w in ["policy", "regulatory", "regulation", "governance", "trade"]):
        users.append("Policymaker")
        users.append("Government agencies")
    if any(w in text for w in ["research", "breeding", "assessment", "diagnostic"]):
        users.append("Researcher")
    if any(w in text for w in ["practitioner", "implementation", "field", "community",
                                "extension", "advisory"]):
        users.append("Development Practitioner")
    if any(w in text for w in ["farmer", "field school", "rural"]):
        users.append("Farmers and Agro-pastoralists")
    if any(w in text for w in ["market", "agribusiness", "value chain", "business model"]):
        users.append("Agribusiness")
    if any(w in text for w in ["monitor", "evaluat", "m&e", "melia", "impact"]):
        users.append("Monitoring and Evaluation specialists")
    if any(w in text for w in ["scaling", "innovation", "program", "project"]):
        users.append("Project and program managers")
    if any(w in text for w in ["gender", "women", "social inclusion", "participatory"]):
        if "Community leaders" not in users:
            users.append("Community leaders")
    if any(w in text for w in ["finance", "investment", "funder", "donor"]):
        users.append("Funders and Donors")
    if any(w in text for w in ["digital", "ict", "mobile", "technology"]):
        users.append("Private sector entities")
    if any(w in text for w in ["extension", "advisory service"]):
        if "Extension services" not in users:
            users.append("Extension services")
    if any(w in text for w in ["irrigation"]):
        users.append("Irrigation scheme managers")

    return users if users else []


# ── The 25 tools from items.ts ────────────────────────────────────────────────
# Each tool is specified with its v2 data fields

TOOLS = [
    {
        "id": "scaling-scan",
        "title": "Scaling Scan",
        "description": "Systematically assess readiness and potential of innovations to scale within agri-food systems.",
        "fullDescription": [
            "The Scaling Scan is a practical framework developed to help teams and organizations assess the readiness and potential of agricultural innovations to scale within complex agri-food systems. It provides a structured methodology for evaluating both the innovation itself and the enabling environment in which it operates.",
            "Drawing on decades of research and field experience across sub-Saharan Africa, South Asia, and Southeast Asia, the Scaling Scan framework enables practitioners to identify critical bottlenecks, assess institutional capacity, and develop targeted strategies for scaling agricultural innovations effectively.",
            "The framework consists of ten scaling ingredients, each of which represents a key factor determining whether an innovation can grow from pilot to significant scale. By systematically scoring each ingredient, teams can identify priority areas for investment and intervention.",
            "The Scaling Scan has been applied in over 40 countries across multiple CGIAR centers, and has been used to guide scaling strategies for innovations ranging from improved seed varieties to digital advisory services.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Ethiopia", "Uganda", "Bangladesh", "India", "Vietnam", "Colombia"],
        "regions": ["East Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2019,
        "authors": ["Larry Cooley", "Johannes Linn", "CIMMYT Scaling Team"],
    },
    {
        "id": "scaling-readiness",
        "title": "Scaling Readiness Assessment",
        "description": "Determine the readiness level of innovations and their enabling environment for scaling investments.",
        "fullDescription": [
            "The Scaling Readiness Assessment provides a rapid yet rigorous methodology for determining whether an agricultural innovation and its surrounding enabling environment are ready for scaling investments.",
            "Scaling Readiness synthesizes evidence across five readiness dimensions: technical maturity, demand validation, business model viability, enabling environment fitness, and organizational capacity.",
            "The assessment process generates a Readiness Score and a detailed readiness profile that can be used to make go/no-go scaling decisions.",
            "Scaling Readiness has been applied to over 150 agricultural innovations across the CGIAR portfolio.",
        ],
        "type": "Approach",
        "pillars": ["Policy & Institutional", "Financial Services & M&E"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Ethiopia", "Nigeria", "India", "Vietnam", "Guatemala"],
        "regions": ["East Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2020,
        "authors": ["Marc Schut", "Cees Leeuwis", "Wageningen University & CGIAR"],
    },
    {
        "id": "melia-framework",
        "title": "MELIA Framework",
        "description": "Monitoring, Evaluation, Learning, and Impact Assessment framework for agricultural research-for-development programs.",
        "fullDescription": [
            "The MELIA (Monitoring, Evaluation, Learning, and Impact Assessment) Framework provides a comprehensive system for tracking the performance and impact of agricultural research-for-development programs.",
            "MELIA integrates four interconnected functions: real-time monitoring of outputs and outcomes, periodic evaluations of program effectiveness, systematic learning processes for adaptive management, and rigorous impact assessment.",
            "The framework emphasizes theory-of-change-based planning, contribution analysis, and participatory evaluation methods.",
            "Originally developed for CGIAR research programs, MELIA has been adopted by national agricultural research systems and development organizations in over 25 countries.",
        ],
        "type": "Framework",
        "pillars": ["Financial Services & M&E"],
        "enablers": ["Scaling of Innovation", "Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "Tanzania", "India", "Bangladesh", "Colombia", "Nigeria"],
        "regions": ["East Africa", "South Asia", "Latin America", "West Africa"],
        "year": 2018,
        "authors": ["CGIAR Advisory Services", "ISDC"],
    },
    {
        "id": "policy-landscape-mapping",
        "title": "Policy Landscape Mapping Tool",
        "description": "Visualize and analyze the policy ecosystem affecting agricultural innovation adoption and scaling.",
        "fullDescription": [
            "Policy Landscape Mapping is a systematic method for identifying, analyzing, and visualizing the full range of policies, regulations, and institutional arrangements that shape the enabling environment for agricultural innovation.",
            "The method combines desk-based policy analysis with stakeholder consultations to produce comprehensive maps of the policy ecosystem.",
            "By visualizing policy interactions and identifying gaps, Policy Landscape Mapping helps innovators and policymakers understand how different policy domains interact.",
            "The method has been used extensively across East and West Africa to support policy reform processes.",
        ],
        "type": "Method",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Nigeria", "Ghana", "Tanzania", "Rwanda", "Mozambique", "Zambia"],
        "regions": ["West Africa", "East Africa", "Southern Africa"],
        "year": 2017,
        "authors": ["IFAD Policy Division", "CGIAR Research Program on Policies, Institutions and Markets"],
    },
    {
        "id": "gender-transformative-framework",
        "title": "Gender Transformative Approach Framework",
        "description": "Design and implement interventions that address root causes of gender inequality in agricultural systems.",
        "fullDescription": [
            "The Gender Transformative Approach (GTA) Framework provides a structured methodology for designing and implementing agricultural interventions that move beyond gender-sensitivity to actively address the structural causes of gender inequality within food systems.",
            "The framework integrates gender analysis across the full project cycle.",
            "Field applications across sub-Saharan Africa and South Asia have demonstrated that gender transformative approaches can increase women's participation in agricultural value chains by up to 40%.",
        ],
        "type": "Framework",
        "pillars": ["Gender & Social Inclusion", "Policy & Institutional"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "Mali", "Senegal", "Bangladesh", "Nepal", "Philippines"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia"],
        "year": 2019,
        "authors": ["Rhiannon Pyburn", "Anouka van Eerdewijk", "KIT Royal Tropical Institute"],
    },
    {
        "id": "digital-agriculture-assessment",
        "title": "Digital Agriculture Assessment Tool",
        "description": "Evaluate digital infrastructure readiness and identify opportunities for digital agricultural services.",
        "fullDescription": [
            "The Digital Agriculture Assessment Tool (DAAT) provides a comprehensive framework for evaluating the digital infrastructure landscape and identifying high-value opportunities for digital agricultural services.",
            "The tool generates a Digital Agriculture Readiness Index that can be used to prioritize investments.",
            "Piloted across 15 countries in Africa and Asia.",
        ],
        "type": "Tool",
        "pillars": ["Digital", "Market Systems"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Emerging",
        "countries": ["Kenya", "Tanzania", "Rwanda", "Ghana", "India", "Indonesia", "Philippines"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia"],
        "year": 2021,
        "authors": ["World Bank Digital Development", "CTA"],
    },
    {
        "id": "market-systems-analysis",
        "title": "Market Systems Analysis",
        "description": "Map and understand market dynamics that influence agricultural innovation uptake and sustainability.",
        "fullDescription": [
            "Market Systems Analysis (MSA) is a methodology for understanding the complex systems of actors, rules, and relationships that shape how agricultural markets function.",
            "The methodology builds on the Making Markets Work for the Poor (M4P) approach.",
            "MSA has been applied extensively across East Africa and South Asia to design market systems development programs.",
        ],
        "type": "Method",
        "pillars": ["Market Systems"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Uganda", "Kenya", "Ethiopia", "Bangladesh", "Pakistan", "Myanmar"],
        "regions": ["East Africa", "South Asia", "Southeast Asia"],
        "year": 2016,
        "authors": ["Springfield Centre", "Alliance of Bioversity International and CIAT"],
    },
    {
        "id": "institutional-capacity",
        "title": "Institutional Capacity Assessment",
        "description": "Evaluate organizational readiness and capacity gaps for scaling agricultural innovations.",
        "fullDescription": [
            "The Institutional Capacity Assessment (ICA) Framework provides a structured approach to evaluating the organizational systems, processes, and capabilities needed to effectively scale agricultural innovations.",
            "The ICA Framework examines seven core domains of organizational capacity.",
            "The framework has been validated through application in over 60 agricultural organizations across Africa, Asia, and Latin America.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional", "Financial Services & M&E"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Emerging",
        "countries": ["Ethiopia", "Uganda", "Nigeria", "Senegal", "India", "Cambodia"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia"],
        "year": 2020,
        "authors": ["CGIAR System Organization", "ISDC"],
    },
    {
        "id": "climate-smart-policy",
        "title": "Climate-Smart Policy Toolkit",
        "description": "Develop and evaluate policies that support climate-resilient agricultural practices.",
        "fullDescription": [
            "The Climate-Smart Policy Toolkit provides governments and development organizations with practical resources for designing, evaluating, and implementing policies that support the adoption of climate-smart agricultural practices.",
            "The toolkit has been developed through collaboration across multiple CGIAR centers and has been applied in 20 countries.",
        ],
        "type": "Tool",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Climate Resilience"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "Ghana", "Mali", "Cambodia", "Vietnam", "Colombia", "Peru"],
        "regions": ["East Africa", "West Africa", "Southeast Asia", "Latin America"],
        "year": 2018,
        "authors": ["FAO Climate-Smart Agriculture Unit", "CCAFS"],
    },
    {
        "id": "innovation-readiness",
        "title": "Innovation Scaling Readiness Assessment",
        "description": "Determine the readiness of innovations and enabling environments for scaling.",
        "fullDescription": [
            "The Innovation Scaling Readiness Assessment (ISRA) provides a rapid yet rigorous methodology for determining whether an agricultural innovation and its surrounding enabling environment are ready for scaling investments.",
            "ISRA synthesizes evidence across five readiness dimensions.",
            "ISRA has been applied to over 150 agricultural innovations across the CGIAR portfolio.",
        ],
        "type": "Approach",
        "pillars": ["Policy & Institutional", "Financial Services & M&E"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Emerging",
        "countries": ["Kenya", "Ethiopia", "Nigeria", "India", "Vietnam", "Guatemala"],
        "regions": ["East Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2021,
        "authors": ["CGIAR Research Program on Policies, Institutions and Markets"],
    },
    {
        "id": "nutrition-sensitive",
        "title": "Nutrition-Sensitive Agriculture Framework",
        "description": "Integrate nutrition objectives into agricultural programming and policy design.",
        "fullDescription": [
            "The Nutrition-Sensitive Agriculture Framework provides guidance for designing agricultural interventions that explicitly contribute to improved nutrition outcomes.",
            "The framework identifies six agricultural-nutrition pathways.",
            "Piloted across 12 countries in Africa and Asia.",
        ],
        "type": "Framework",
        "pillars": ["Gender & Social Inclusion", "Market Systems"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Bangladesh", "Ethiopia", "Zambia", "Nepal", "Nigeria", "Tanzania"],
        "regions": ["South Asia", "East Africa", "West Africa", "Southern Africa"],
        "year": 2017,
        "authors": ["IFAD", "FAO Nutrition Division", "A4NH"],
    },
    {
        "id": "participatory-rural-appraisal",
        "title": "Participatory Rural Appraisal Toolkit",
        "description": "Engage communities in collaborative assessment and planning for agricultural development.",
        "fullDescription": [
            "The Participatory Rural Appraisal (PRA) Toolkit provides a comprehensive set of facilitation methods for engaging rural communities in collaborative assessment, analysis, and planning.",
            "PRA methods empower community members to share their knowledge.",
            "Used extensively across CGIAR programs.",
        ],
        "type": "Method",
        "pillars": ["Gender & Social Inclusion", "Policy & Institutional"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["India", "Kenya", "Uganda", "Bangladesh", "Nepal", "Tanzania", "Ghana"],
        "regions": ["South Asia", "East Africa", "West Africa"],
        "year": 2015,
        "authors": ["Robert Chambers", "CGIAR Research Program on Dryland Systems"],
    },
    {
        "id": "ict4ag-assessment",
        "title": "ICT4Ag Assessment Framework",
        "description": "Assess information and communication technology solutions for agricultural value chain improvement.",
        "fullDescription": [
            "The ICT4Ag Assessment Framework provides a structured approach to evaluating how information and communication technologies can improve agricultural value chain performance.",
            "The framework has been used to design and evaluate ICT4Ag programs in 18 countries.",
        ],
        "type": "Framework",
        "pillars": ["Digital", "Market Systems"],
        "enablers": ["Scaling of Innovation"],
        "stage": "Emerging",
        "countries": ["Kenya", "Ghana", "India", "Philippines", "Vietnam", "Colombia"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2020,
        "authors": ["CTA", "CABI", "CGIAR Platform for Big Data in Agriculture"],
    },
    {
        "id": "seed-system-toolkit",
        "title": "Seed System Development Toolkit",
        "description": "Strengthen national seed systems through policy reform, quality assurance, and market development.",
        "fullDescription": [
            "The Seed System Development Toolkit provides comprehensive guidance for strengthening national seed systems.",
            "Developed through collaboration between CGIAR breeding programs and national seed authorities in 15 countries.",
        ],
        "type": "Tool",
        "pillars": ["Policy & Institutional", "Market Systems"],
        "enablers": ["Improved Agri-Food Systems", "Scaling of Innovation"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Tanzania", "Uganda", "Ethiopia", "Nigeria", "Ghana", "Zambia"],
        "regions": ["East Africa", "West Africa", "Southern Africa"],
        "year": 2018,
        "authors": ["Alliance of Bioversity International and CIAT", "CIMMYT Seed Systems"],
    },
    {
        "id": "ag-finance-readiness",
        "title": "Agricultural Finance Readiness Tool",
        "description": "Assess enabling conditions for agricultural financial services including fintech and insurance.",
        "fullDescription": [
            "The Agricultural Finance Readiness Tool (AFRT) helps governments, financial institutions, and development partners assess the enabling conditions for agricultural financial services.",
            "The tool has been applied in 10 countries across Africa and Asia.",
        ],
        "type": "Tool",
        "pillars": ["Financial Services & M&E", "Digital"],
        "enablers": ["Scaling of Innovation", "Improved Agri-Food Systems"],
        "stage": "Emerging",
        "countries": ["Nigeria", "Kenya", "Tanzania", "India", "Vietnam", "Philippines", "Myanmar"],
        "regions": ["West Africa", "East Africa", "South Asia", "Southeast Asia"],
        "year": 2022,
        "authors": ["World Bank Agriculture Finance Unit", "CGAP"],
    },
    {
        "id": "land-governance",
        "title": "Land Governance Assessment Framework",
        "description": "Assess and improve land governance systems critical for agricultural investment and food security.",
        "fullDescription": [
            "The Land Governance Assessment Framework (LGAF) provides a comprehensive diagnostic tool for assessing the quality of land governance.",
            "LGAF has been implemented in over 40 countries globally.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional", "Gender & Social Inclusion"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "Tanzania", "Uganda", "Nigeria", "India", "Vietnam", "Colombia"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2016,
        "authors": ["World Bank Land Unit", "Klaus Deininger"],
    },
    {
        "id": "watershed-management",
        "title": "Watershed Management Framework",
        "description": "Plan and implement integrated watershed management for climate-resilient agricultural landscapes.",
        "fullDescription": [
            "The Watershed Management Framework provides guidance for planning, implementing, and monitoring integrated watershed management interventions.",
            "Applied across the Ethiopian highlands, Indian dryland systems, and Central American hillsides.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Climate Resilience", "Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "India", "Nepal", "Kenya", "Guatemala", "Colombia"],
        "regions": ["East Africa", "South Asia", "Latin America"],
        "year": 2017,
        "authors": ["IWMI", "ICRISAT Watershed Program"],
    },
    {
        "id": "value-chain-analysis",
        "title": "Value Chain Analysis Toolkit",
        "description": "Map agricultural value chains to identify constraints, opportunities, and intervention points.",
        "fullDescription": [
            "The Value Chain Analysis Toolkit provides a comprehensive methodology for mapping, analyzing, and upgrading agricultural value chains.",
            "Used extensively across CGIAR commodity programs.",
        ],
        "type": "Method",
        "pillars": ["Market Systems"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Uganda", "Ghana", "Nigeria", "Bangladesh", "Vietnam", "Colombia"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2016,
        "authors": ["FAO", "Alliance of Bioversity International and CIAT"],
    },
    {
        "id": "agroecology-scorecard",
        "title": "Agroecology Transition Scorecard",
        "description": "Measure progress toward agroecological farming practices at farm and landscape levels.",
        "fullDescription": [
            "The Agroecology Transition Scorecard provides a standardized methodology for measuring the extent to which farming systems are adopting agroecological principles.",
            "Developed in collaboration with FAO and validated across 20 countries.",
        ],
        "type": "Scorecard",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Climate Resilience", "Improved Agri-Food Systems"],
        "stage": "Emerging",
        "countries": ["India", "Ethiopia", "Senegal", "Colombia", "Philippines", "Tanzania"],
        "regions": ["South Asia", "East Africa", "West Africa", "Latin America", "Southeast Asia"],
        "year": 2022,
        "authors": ["FAO Agroecology Unit", "Alliance of Bioversity International and CIAT"],
    },
    {
        "id": "climate-vulnerability",
        "title": "Climate Vulnerability Assessment Framework",
        "description": "Assess agricultural system vulnerability to climate change and prioritize adaptation investments.",
        "fullDescription": [
            "The Climate Vulnerability Assessment Framework (CVAF) provides a structured methodology for assessing the vulnerability of agricultural systems to climate change.",
            "Developed by CCAFS and applied across 25 countries, the framework has informed national adaptation plans and guided over $500 million in climate adaptation investments for agriculture.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional", "Financial Services & M&E"],
        "enablers": ["Climate Resilience"],
        "stage": "Established and field-tested",
        "countries": ["Ethiopia", "Kenya", "Nigeria", "Bangladesh", "India", "Nepal", "Vietnam", "Colombia"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia", "Latin America"],
        "year": 2018,
        "authors": ["CCAFS", "CIAT Climate Change Team"],
    },
    {
        "id": "irrigation-governance",
        "title": "Irrigation Governance Assessment",
        "description": "Evaluate and improve governance systems for sustainable irrigation management.",
        "fullDescription": [
            "The Irrigation Governance Assessment provides a diagnostic framework for evaluating the governance arrangements that determine the sustainability, equity, and efficiency of irrigation systems.",
            "Developed by IWMI and applied in 12 countries across Africa and South Asia.",
        ],
        "type": "Framework",
        "pillars": ["Policy & Institutional"],
        "enablers": ["Climate Resilience", "Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["India", "Nepal", "Bangladesh", "Ethiopia", "Tanzania", "Ghana", "Zambia"],
        "regions": ["South Asia", "East Africa", "West Africa", "Southern Africa"],
        "year": 2019,
        "authors": ["IWMI", "FAO Land and Water Division"],
    },
    {
        "id": "farmer-field-school",
        "title": "Farmer Field School Implementation Guide",
        "description": "Design and implement farmer field schools for participatory agricultural learning and innovation.",
        "fullDescription": [
            "The Farmer Field School (FFS) Implementation Guide provides comprehensive guidance for designing, implementing, and scaling farmer-led learning programs.",
            "With over 30 years of experience across 90 countries.",
        ],
        "type": "Approach",
        "pillars": ["Gender & Social Inclusion", "Policy & Institutional"],
        "enablers": ["Scaling of Innovation", "Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Uganda", "Tanzania", "Ethiopia", "India", "Bangladesh", "Philippines", "Vietnam"],
        "regions": ["East Africa", "South Asia", "Southeast Asia"],
        "year": 2016,
        "authors": ["FAO Plant Production and Protection Division"],
    },
    {
        "id": "gender-responsive-breeding",
        "title": "Gender-Responsive Plant Breeding Method",
        "description": "Integrate gender analysis into plant breeding processes to develop varieties that meet diverse user needs.",
        "fullDescription": [
            "The Gender-Responsive Plant Breeding Method provides a structured approach for integrating gender analysis into all stages of the plant breeding process.",
            "Piloted across CGIAR breeding programs for rice, beans, cassava, and wheat.",
        ],
        "type": "Method",
        "pillars": ["Gender & Social Inclusion"],
        "enablers": ["Improved Agri-Food Systems", "Scaling of Innovation"],
        "stage": "Pilot",
        "countries": ["Uganda", "Tanzania", "Nigeria", "Bangladesh", "India", "Philippines"],
        "regions": ["East Africa", "West Africa", "South Asia", "Southeast Asia"],
        "year": 2022,
        "authors": ["CGIAR Gender and Breeding Initiative", "Hale Tufan", "Cornell University"],
    },
    {
        "id": "cbnrm-toolkit",
        "title": "Community-Based Natural Resource Management Toolkit",
        "description": "Empower communities to sustainably manage natural resources for agricultural livelihoods.",
        "fullDescription": [
            "The Community-Based Natural Resource Management (CBNRM) Toolkit provides practical guidance for establishing and strengthening community governance systems for natural resources.",
            "Applied across dryland and pastoral systems in East Africa and South Asia.",
        ],
        "type": "Tool",
        "pillars": ["Policy & Institutional", "Gender & Social Inclusion"],
        "enablers": ["Climate Resilience", "Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Tanzania", "Ethiopia", "India", "Nepal", "Uganda"],
        "regions": ["East Africa", "South Asia"],
        "year": 2018,
        "authors": ["ILRI", "ICRISAT", "WorldFish"],
    },
    {
        "id": "postharvest-loss",
        "title": "Post-Harvest Loss Reduction Guide",
        "description": "Comprehensive guidance for reducing food losses in agricultural value chains.",
        "fullDescription": [
            "The Post-Harvest Loss Reduction Guide provides comprehensive technical and institutional guidance for reducing food losses across agricultural value chains.",
            "The guide has been used in 18 countries and contributed to average loss reductions of 30%.",
        ],
        "type": "Guidelines",
        "pillars": ["Market Systems", "Digital"],
        "enablers": ["Improved Agri-Food Systems"],
        "stage": "Established and field-tested",
        "countries": ["Kenya", "Tanzania", "Nigeria", "Ghana", "Ethiopia", "India", "Bangladesh"],
        "regions": ["East Africa", "West Africa", "South Asia"],
        "year": 2019,
        "authors": ["FAO Save Food Initiative", "CIMMYT Post-Harvest Program"],
    },
]


def build_test_entry(tool: dict) -> dict:
    """Build a test entry from a v2 tool."""
    # Build input
    full_text = " ".join(tool["fullDescription"])
    input_data = {
        "title": tool["title"],
        "authors": ", ".join(tool["authors"]),
        "date": str(tool["year"]),
        "abstract": tool["description"],
        "full_text": full_text,
    }

    # Build expected output
    pillars = map_pillars(tool["pillars"])
    domains = map_domains(tool["enablers"])
    tool_type = map_type(tool["type"])
    stage = map_stage(tool["stage"])
    geography = map_geography(tool["regions"], tool["countries"])
    target_users = infer_target_users(tool["title"], tool["description"], pillars)

    expected = {
        "pillars": pillars,
        "domains": domains,
        "type": tool_type,
        "stage": stage,
        "target_users": target_users,
        "geography": geography,
    }

    return {"id": tool["id"], "input": input_data, "expected": expected}


def main():
    test_set = []
    for tool in TOOLS:
        entry = build_test_entry(tool)
        test_set.append(entry)
        print(f"  {entry['id']}: pillars={entry['expected']['pillars']}, "
              f"domains={entry['expected']['domains']}, type={entry['expected']['type']}, "
              f"stage={entry['expected']['stage']}")

    out_path = os.path.join(
        os.path.dirname(__file__), "test_data", "extraction_test_set.json"
    )
    with open(out_path, "w") as f:
        json.dump(test_set, f, indent=2)

    print(f"\nWrote {len(test_set)} test entries to {out_path}")


if __name__ == "__main__":
    main()
