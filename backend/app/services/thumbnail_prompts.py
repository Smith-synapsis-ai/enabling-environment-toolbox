"""Thumbnail illustration-prompt templating (C6 Wave B / Thread 3).

Builds a per-tool image-generation prompt grounded in the tool's REAL catalog
metadata — NOT a generic stock prompt. Inspired by the docx-illustrate skill's
illustration-prompt approach: highly specific, abstract/iconographic, and
EXPLICITLY text-free (gpt-image renders garbled text on small images).

The same template is used by the admin batch-trigger (to store the prompt on
the job row) and by the controlled agent/CI generation path (which reads the
stored prompt and calls the image_generate MCP tool). Keeping it server-side
guarantees the review grid shows exactly the prompt that produced each image.
"""

from __future__ import annotations

# type -> visual motif (keeps the 100 thumbnails visually differentiated yet
# consistent). Falls back to a neutral motif for unknown types.
_TYPE_MOTIF = {
    "Framework": "interlocking geometric blocks forming a structured framework",
    "Method": "a sequence of flowing process arrows and connected steps",
    "Manual": "an open guide / layered checklist pages",
    "Guideline": "an open guide / layered checklist pages",
    "Guide": "an open guide / layered checklist pages",
    "Dataset": "a grid of connected data nodes and subtle bar/line motifs",
    "Tool": "a stylised modular toolkit of simple abstract instruments",
    "Toolkit": "a stylised modular toolkit of simple abstract instruments",
    "Platform": "interconnected network nodes on a clean surface",
    "Report": "layered document planes with abstract chart accents",
    "Assessment": "a balanced gauge / scoring dial composition",
    "Index": "a balanced gauge / scoring dial composition",
    "Case Study": "a focused magnifier over an abstract landscape",
    "Training": "abstract growth / learning arcs rising upward",
}

# primary domain -> accent colour direction (paired with CGIAR green base)
_DOMAIN_ACCENT = {
    "Climate Resilience": "soft teal and warm amber accents",
    "Agri-food Systems": "wheat-gold and fresh green accents",
    "Gender and Inclusion": "soft violet and coral accents",
    "Nutrition and Health": "warm red and leaf-green accents",
    "Markets and Value Chains": "deep blue and orange accents",
    "Digital and Data": "electric blue and cyan accents",
    "Water and Land": "aqua-blue and earthy-brown accents",
    "Policy and Institutions": "slate-blue and gold accents",
}

_DEFAULT_MOTIF = "a clean abstract emblem of simple connected shapes"
_DEFAULT_ACCENT = "muted sage and soft gold accents"


def _first(seq: object) -> str | None:
    if isinstance(seq, (list, tuple)) and seq:
        return str(seq[0])
    if isinstance(seq, str) and seq.strip():
        return seq.strip()
    return None


def build_thumbnail_prompt(
    *,
    title: str | None,
    type_: str | None,
    pillars: object = None,
    domains: object = None,
    summary: str | None = None,
) -> str:
    """Return a templated, text-free, abstract thumbnail prompt for one tool."""
    motif = _TYPE_MOTIF.get((type_ or "").strip(), _DEFAULT_MOTIF)
    primary_domain = _first(domains)
    primary_pillar = _first(pillars)
    accent = _DOMAIN_ACCENT.get(primary_domain or "", _DEFAULT_ACCENT)

    theme_bits = []
    if primary_domain:
        theme_bits.append(primary_domain)
    if primary_pillar:
        theme_bits.append(primary_pillar)
    theme = " and ".join(theme_bits) if theme_bits else "agricultural enabling environments"

    type_phrase = (type_ or "resource").strip().lower()

    return (
        f"A clean, minimal, abstract flat-vector thumbnail illustration for a CGIAR "
        f"enabling-environment {type_phrase}, themed around {theme}. "
        f"Central motif: {motif}. "
        f"Corporate flat illustration style, deep CGIAR green (#033529) as the base "
        f"with {accent}, smooth gradients, soft shadows, centered balanced composition "
        f"on a light neutral background. "
        f"Iconographic and symbolic only — ABSOLUTELY NO text, no words, no letters, "
        f"no numbers, no logos, no watermarks. "
        f"Suitable as a small catalog card thumbnail; uncluttered and legible at small size."
    )
