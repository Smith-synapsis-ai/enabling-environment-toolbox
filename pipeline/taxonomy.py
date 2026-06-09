"""
Taxonomy constants and validation for the Enabling Environment Toolbox.

Contains all valid taxonomy values from Ojong's Master Table and provides
validation functions for metadata extraction outputs.
"""

from difflib import get_close_matches
from typing import Any

# ── Valid Taxonomy Values ──────────────────────────────────────────────────────

PILLARS = {
    "Gender Equality and Social Inclusion",
    "Monitoring, Evaluation and Learning",
    "Policy and Regulatory",
    "Market Systems",
    "Digital and Financial Services",
}

DOMAINS = {
    "Agri-food Systems",
    "Scaling Innovation",
    "Climate Resilience",
}

TYPES = {
    "Method",
    "Framework",
    "Manual",
    "Toolkit",
    "Tool",
    "Guide",
    "Matrix",
    "Scorecard",
    "Brief",
    "Scale",
}

STAGES = {
    "Established and field-tested",
    "Prototype",
    "Theoretical and diagnostics",
    "Conceptual",
}

TARGET_USERS = {
    "Researcher",
    "Policymaker",
    "Development Practitioner",
    "Extension services",
    "Agribusiness",
    "Local communities",
    "Civil Society and INGOs",
    "Funders and Donors",
    "Private sector entities",
    "Government agencies",
    "Humanitarian assistance practitioners",
    "Project and program managers",
    "Farmers and Agro-pastoralists",
    "Monitoring and Evaluation specialists",
    "Community leaders",
    "Irrigation scheme managers",
}

GEOGRAPHY = {
    "Global",
    "Asia",
    "Africa",
    "MENA",
    "Latin America",
    "Europe",
    "Low-income and middle-income countries",
    "Central and West Asia and North Africa (CWANA)",
}

# ── Lookup maps for case-insensitive and fuzzy matching ────────────────────────

_PILLAR_LOWER = {p.lower(): p for p in PILLARS}
_DOMAIN_LOWER = {d.lower(): d for d in DOMAINS}
_TYPE_LOWER = {t.lower(): t for t in TYPES}
_STAGE_LOWER = {s.lower(): s for s in STAGES}
_TARGET_USER_LOWER = {u.lower(): u for u in TARGET_USERS}
_GEOGRAPHY_LOWER = {g.lower(): g for g in GEOGRAPHY}


def _find_closest(value: str, valid_set: set[str], lower_map: dict[str, str]) -> str | None:
    """Try exact match, case-insensitive match, then fuzzy match."""
    if value in valid_set:
        return value
    lower_val = value.lower()
    if lower_val in lower_map:
        return lower_map[lower_val]
    # Fuzzy match
    matches = get_close_matches(lower_val, lower_map.keys(), n=1, cutoff=0.75)
    if matches:
        return lower_map[matches[0]]
    return None


def _validate_array_field(
    values: list[Any], valid_set: set[str], lower_map: dict[str, str], field_name: str
) -> tuple[list[str], list[str]]:
    """Validate an array field, returning (clean_values, warnings)."""
    clean = []
    warnings = []
    if not isinstance(values, list):
        warnings.append(f"{field_name}: expected list, got {type(values).__name__}")
        return clean, warnings

    for v in values:
        if not isinstance(v, str):
            warnings.append(f"{field_name}: non-string value '{v}'")
            continue
        matched = _find_closest(v, valid_set, lower_map)
        if matched:
            if matched not in clean:
                clean.append(matched)
            if matched != v:
                warnings.append(f"{field_name}: corrected '{v}' -> '{matched}'")
        else:
            warnings.append(f"{field_name}: INVALID value '{v}' (removed)")
    return clean, warnings


def _validate_single_field(
    value: Any, valid_set: set[str], lower_map: dict[str, str], field_name: str
) -> tuple[str | None, list[str]]:
    """Validate a single-value field, returning (clean_value, warnings)."""
    warnings = []
    if value is None or value == "":
        return None, warnings
    if not isinstance(value, str):
        warnings.append(f"{field_name}: expected string, got {type(value).__name__}")
        return None, warnings

    matched = _find_closest(value, valid_set, lower_map)
    if matched:
        if matched != value:
            warnings.append(f"{field_name}: corrected '{value}' -> '{matched}'")
        return matched, warnings
    else:
        warnings.append(f"{field_name}: INVALID value '{value}' (set to None)")
        return None, warnings


def validate_extraction(data: dict) -> dict:
    """
    Validate an extraction result against the taxonomy.

    Returns a dict with:
      - 'data': the cleaned extraction data
      - 'warnings': list of validation warning strings
    """
    warnings = []
    cleaned = dict(data)  # shallow copy

    # Array fields
    for field_name, valid_set, lower_map in [
        ("pillars", PILLARS, _PILLAR_LOWER),
        ("domains", DOMAINS, _DOMAIN_LOWER),
        ("target_users", TARGET_USERS, _TARGET_USER_LOWER),
        ("geography", GEOGRAPHY, _GEOGRAPHY_LOWER),
    ]:
        if field_name in cleaned:
            clean_vals, field_warnings = _validate_array_field(
                cleaned[field_name], valid_set, lower_map, field_name
            )
            cleaned[field_name] = clean_vals
            warnings.extend(field_warnings)

    # Single-value fields
    for field_name, valid_set, lower_map in [
        ("type", TYPES, _TYPE_LOWER),
        ("stage", STAGES, _STAGE_LOWER),
    ]:
        if field_name in cleaned:
            clean_val, field_warnings = _validate_single_field(
                cleaned[field_name], valid_set, lower_map, field_name
            )
            cleaned[field_name] = clean_val
            warnings.extend(field_warnings)

    return {"data": cleaned, "warnings": warnings}
