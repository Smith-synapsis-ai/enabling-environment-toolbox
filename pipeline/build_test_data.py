"""Script to build the relevance classification test dataset.

Parses the tools from items.ts as positive examples and adds
synthetic negative examples.
"""

import json
import re
import sys


def parse_tools_from_typescript(filepath: str) -> list[dict]:
    """Parse tool entries from the items.ts TypeScript file.

    Extracts title, description, type, authors, year, and url for each tool.
    """
    with open(filepath, "r") as f:
        content = f.read()

    # Extract the tools array - everything between "export const tools: Tool[] = [" and the closing "]"
    tools_match = re.search(
        r"export\s+const\s+tools:\s+Tool\[\]\s*=\s*\[(.*?)\n\]\s*\n",
        content,
        re.DOTALL,
    )
    if not tools_match:
        print("ERROR: Could not find tools array in file.")
        sys.exit(1)

    tools_text = tools_match.group(1)

    # Split into individual tool objects by finding each { ... } block at the top level
    tools = []
    depth = 0
    current_start = None

    for i, char in enumerate(tools_text):
        if char == "{" and depth == 0:
            current_start = i
            depth = 1
        elif char == "{":
            depth += 1
        elif char == "}" and depth == 1:
            depth = 0
            if current_start is not None:
                tool_text = tools_text[current_start : i + 1]
                tools.append(tool_text)
                current_start = None
        elif char == "}":
            depth -= 1

    parsed_tools = []
    for tool_text in tools:
        # Extract fields using regex
        title = _extract_string_field(tool_text, "title")
        description = _extract_string_field(tool_text, "description")
        tool_type = _extract_string_field(tool_text, "type")
        url = _extract_string_field(tool_text, "url")
        year = _extract_number_field(tool_text, "year")
        authors = _extract_array_field(tool_text, "authors")

        if title:
            parsed_tools.append(
                {
                    "title": title,
                    "abstract": description or "",
                    "doc_type": tool_type or "Tool",
                    "authors": ", ".join(authors) if authors else "Unknown",
                    "date": str(year) if year else "Unknown",
                    "url": url or "",
                    "expected_relevant": True,
                }
            )

    return parsed_tools


def _extract_string_field(text: str, field_name: str) -> str:
    """Extract a string field value from a JS object literal."""
    # Match: fieldName: 'value' or fieldName: "value"
    pattern = rf"{field_name}:\s*['\"](.+?)['\"]"
    match = re.search(pattern, text)
    if match:
        # Unescape JS string escapes
        return match.group(1).replace("\\'", "'").replace('\\"', '"')
    return ""


def _extract_number_field(text: str, field_name: str) -> int:
    """Extract a numeric field value from a JS object literal."""
    pattern = rf"{field_name}:\s*(\d+)"
    match = re.search(pattern, text)
    if match:
        return int(match.group(1))
    return 0


def _extract_array_field(text: str, field_name: str) -> list[str]:
    """Extract a string array field from a JS object literal."""
    pattern = rf"{field_name}:\s*\[(.*?)\]"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        array_text = match.group(1)
        items = re.findall(r"['\"](.+?)['\"]", array_text)
        return items
    return []


def get_negative_examples() -> list[dict]:
    """Return 15 synthetic negative examples."""
    negatives = [
        {
            "title": "Genome-Wide Association Study for Rice Blast Resistance in Indica Cultivars",
            "abstract": "We conducted a genome-wide association study (GWAS) involving 380 indica rice accessions to identify quantitative trait loci (QTL) associated with resistance to Magnaporthe oryzae. Using 45,000 single nucleotide polymorphisms, we identified 14 significant loci on chromosomes 1, 4, 6, and 11, including three novel resistance genes. These findings advance our understanding of the genetic architecture of blast resistance and offer targets for marker-assisted breeding programs.",
            "doc_type": "Journal Article",
            "authors": "Raj Kumar Singh, Pham Thi Bich Ngoc, Hideaki Takahashi",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/134521",
            "expected_relevant": False,
        },
        {
            "title": "Annual Report 2024: International Maize and Wheat Improvement Center",
            "abstract": "This annual report summarizes CIMMYT's research outputs, financial performance, partnerships, and organizational developments during fiscal year 2024. Highlights include the release of 12 new wheat varieties, expansion of the Seeds of Discovery project, and progress on the Sustainable Intensification framework across 15 countries in sub-Saharan Africa and South Asia.",
            "doc_type": "Report",
            "authors": "CIMMYT Communications Team",
            "date": "2024",
            "url": "https://cgspace.cgiar.org/handle/10568/140001",
            "expected_relevant": False,
        },
        {
            "title": "Phylogenetic Analysis of Trypanosoma Species in East African Cattle",
            "abstract": "This study presents a comprehensive phylogenetic analysis of Trypanosoma species isolated from 1,200 cattle across Kenya, Tanzania, and Uganda. Using mitochondrial DNA sequencing and maximum likelihood phylogenetic inference, we identified three distinct clades of T. congolense and evidence of genetic recombination between T. vivax populations. Results have implications for understanding parasite evolution and designing targeted diagnostic tools.",
            "doc_type": "Journal Article",
            "authors": "Grace Muriuki, John Osoro, Peter de Leeuw",
            "date": "2022",
            "url": "https://cgspace.cgiar.org/handle/10568/131245",
            "expected_relevant": False,
        },
        {
            "title": "Effect of Nitrogen Fertilization Rates on Wheat Yield: A Meta-Analysis of 47 Field Trials",
            "abstract": "We conducted a meta-analysis of 47 field trials across the Indo-Gangetic Plain to quantify the yield response of wheat to varying nitrogen fertilization rates (0-200 kg N/ha). The analysis revealed a mean yield response of 22 kg grain per kg N applied, with diminishing returns above 120 kg N/ha. Soil organic carbon content was the strongest predictor of yield response variability across sites.",
            "doc_type": "Journal Article",
            "authors": "Arun Joshi, Meena Kumari, H.S. Gupta",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/135678",
            "expected_relevant": False,
        },
        {
            "title": "Proceedings of the 15th International Symposium on Rice Genetics",
            "abstract": "These proceedings compile 127 papers presented at the 15th International Symposium on Rice Genetics held in Manila, Philippines, covering advances in rice genomics, molecular breeding, functional genomics, and bioinformatics. Topics include CRISPR-Cas9 gene editing for disease resistance, genomic selection for grain quality traits, and pan-genome analysis of wild rice species.",
            "doc_type": "Conference Paper",
            "authors": "International Rice Research Institute",
            "date": "2024",
            "url": "https://cgspace.cgiar.org/handle/10568/141000",
            "expected_relevant": False,
        },
        {
            "title": "Transcriptomic Profiling of Drought Response in Sorghum: Implications for Breeding Programs",
            "abstract": "We performed RNA sequencing on drought-stressed and well-watered sorghum plants at three developmental stages to identify differentially expressed genes involved in drought tolerance. Analysis of 24,000 transcripts revealed 3,847 differentially expressed genes, with enrichment in ABA signaling, osmotic adjustment, and root architecture pathways. We identified 15 candidate genes for marker-assisted selection in drought tolerance breeding.",
            "doc_type": "Journal Article",
            "authors": "Kebede Muleta, Ana Maria Correa, Santosh Deshpande",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/136789",
            "expected_relevant": False,
        },
        {
            "title": "Spatial Distribution of Aflatoxin Contamination in Groundnut Markets of Gujarat State",
            "abstract": "This study mapped aflatoxin contamination levels across 45 groundnut markets in Gujarat State, India, during two consecutive post-harvest seasons. Using ELISA and HPLC methods, we found that 38% of samples exceeded the 20 ppb regulatory limit, with contamination levels highest in markets lacking cold storage infrastructure. Results highlight the need for improved post-harvest storage and market infrastructure to reduce consumer exposure.",
            "doc_type": "Working Paper",
            "authors": "Farid Waliyar, Hari Sudini, Pooja Bhatnagar-Mathur",
            "date": "2022",
            "url": "https://cgspace.cgiar.org/handle/10568/132456",
            "expected_relevant": False,
        },
        {
            "title": "Estimating Evapotranspiration from Remote Sensing Data in the Nile Basin",
            "abstract": "We developed and validated a remote sensing-based evapotranspiration estimation model for the Nile Basin using MODIS and Landsat imagery calibrated against 28 eddy covariance flux tower measurements. The model achieved R-squared values of 0.87 for daily ET estimation and provides spatially explicit ET maps at 250m resolution. The methodology enables improved water resource monitoring across data-scarce regions of the basin.",
            "doc_type": "Journal Article",
            "authors": "Wuletawu Abera, Petra Schmitter, Teklu Erkossa",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/137890",
            "expected_relevant": False,
        },
        {
            "title": "Consumer Preferences for Orange-Fleshed Sweet Potato in Urban Rwanda",
            "abstract": "Using a discrete choice experiment with 600 urban consumers in Kigali, we analyzed willingness to pay for orange-fleshed sweet potato (OFSP) products compared to traditional white-fleshed varieties. Results indicate a 15-23% price premium for OFSP when nutritional benefits are communicated through labeling, with education level and presence of children under five as significant determinants of willingness to pay.",
            "doc_type": "Working Paper",
            "authors": "Jan Low, Kirimi Sindi, Vivian Atakos",
            "date": "2022",
            "url": "https://cgspace.cgiar.org/handle/10568/133567",
            "expected_relevant": False,
        },
        {
            "title": "Genetic Diversity of Indigenous Chicken Breeds in Ethiopia: Microsatellite Analysis",
            "abstract": "We assessed the genetic diversity and population structure of five indigenous chicken ecotypes from Ethiopia using 30 microsatellite markers genotyped across 480 individuals. Average heterozygosity ranged from 0.52 to 0.71 across populations. STRUCTURE analysis identified three distinct genetic clusters corresponding to highland, lowland, and Rift Valley ecotypes. Results inform conservation priorities and utilization strategies for indigenous poultry genetic resources.",
            "doc_type": "Journal Article",
            "authors": "Tadelle Dessie, Olivier Hanotte, Solomon Abegaz",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/138901",
            "expected_relevant": False,
        },
        {
            "title": "Optimizing Harvest Time for Maximum Starch Content in Cassava Varieties",
            "abstract": "Field trials across three agro-ecological zones in Nigeria evaluated the starch content dynamics of six improved cassava varieties harvested at monthly intervals from 8 to 16 months after planting. Peak starch content occurred at 12-14 months for most varieties, with significant genotype-by-environment interactions. Results provide variety-specific harvest time recommendations for maximizing industrial starch yields.",
            "doc_type": "Journal Article",
            "authors": "Elizabeth Parkes, Peter Kulakow, Chiedozie Egesi",
            "date": "2022",
            "url": "https://cgspace.cgiar.org/handle/10568/134012",
            "expected_relevant": False,
        },
        {
            "title": "Modeling Soil Carbon Dynamics Under Different Tillage Systems",
            "abstract": "Using the RothC soil carbon model calibrated with data from 12 long-term tillage experiments across Sub-Saharan Africa, we simulated soil organic carbon dynamics under conventional tillage, minimum tillage, and no-till systems over 30-year time horizons. Results indicate that no-till systems can sequester 0.3-0.8 t C/ha/year in the top 30 cm, with highest rates in humid climates with high biomass inputs.",
            "doc_type": "Journal Article",
            "authors": "Christian Thierfelder, Muluneh Tamiru, Isaiah Nyagumbo",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/139234",
            "expected_relevant": False,
        },
        {
            "title": "Pathogenicity Testing of Fusarium Species on Banana Cultivars in Central America",
            "abstract": "We tested the pathogenicity of 45 Fusarium isolates representing six species complexes on 12 banana cultivars under controlled greenhouse conditions. Fusarium odoratissimum TR4 caused severe wilt symptoms in all Cavendish cultivars within 8 weeks, while certain FHIA and Musa balbisiana-derived hybrids showed resistance. Molecular characterization confirmed the presence of SIX effector genes in all highly pathogenic isolates.",
            "doc_type": "Journal Article",
            "authors": "Miguel Dita, Fernando Garcia-Bastidas, Gert Kema",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/140345",
            "expected_relevant": False,
        },
        {
            "title": "Historical Analysis of Rainfall Patterns in the Indo-Gangetic Plain",
            "abstract": "Using 65 years of daily rainfall records from 142 weather stations, we analyzed trends in monsoon onset, duration, total rainfall, and extreme precipitation events across the Indo-Gangetic Plain. Results show a significant delay in monsoon onset (3.2 days per decade), increased frequency of dry spells within the monsoon season, and a 12% increase in extreme precipitation events, with implications for agricultural planning and water management.",
            "doc_type": "Working Paper",
            "authors": "P.K. Aggarwal, Pramod K. Joshi, A.K. Sikka",
            "date": "2022",
            "url": "https://cgspace.cgiar.org/handle/10568/135456",
            "expected_relevant": False,
        },
        {
            "title": "Nutritional Composition of Wild Edible Plants in Western Kenya",
            "abstract": "We analyzed the macro and micronutrient composition of 32 wild edible plant species commonly consumed in Western Kenya using standard AOAC proximate analysis and ICP-MS for mineral content. Several species showed exceptionally high iron (up to 45 mg/100g), zinc (up to 12 mg/100g), and beta-carotene content, suggesting significant potential for addressing micronutrient deficiencies through promotion of traditional food systems.",
            "doc_type": "Journal Article",
            "authors": "Mary Abukutsa-Onyango, Stepha McMullin, Ramni Jamnadass",
            "date": "2023",
            "url": "https://cgspace.cgiar.org/handle/10568/141567",
            "expected_relevant": False,
        },
    ]
    return negatives


def build_test_set():
    """Build and save the complete test dataset."""
    items_path = "/Users/smithai/workspace/ee-toolbox-v2/src/data/items.ts"

    print("Parsing tools from items.ts...")
    positives = parse_tools_from_typescript(items_path)
    print(f"  Found {len(positives)} positive examples (tools)")

    print("Adding synthetic negative examples...")
    negatives = get_negative_examples()
    print(f"  Added {len(negatives)} negative examples")

    test_set = positives + negatives
    print(f"  Total test set size: {len(test_set)}")

    output_path = "/Users/smithai/workspace/ee-toolbox-app/pipeline/test_data/relevance_test_set.json"
    with open(output_path, "w") as f:
        json.dump(test_set, f, indent=2)

    print(f"  Saved to: {output_path}")
    return test_set


if __name__ == "__main__":
    build_test_set()
