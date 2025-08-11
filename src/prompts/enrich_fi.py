#!/usr/bin/env python3
"""
Finnish news enrichment prompt templates
"""

FINNISH_ENRICHMENT_SYSTEM = """You are an analyst for Paranoid Models. Write crisp, data-informed analysis."""

FINNISH_ENRICHMENT_TEMPLATE = """Context:
- Headline: {title}
- Source: {source_name} ({source_url})
- Published: {published_at}
- Raw summary: {summary_raw}
- Category guess: {category_guess}
- Country: {origin_country}

Task:
Produce a structured enrichment JSON with:
- kicker: 4–8 words, punchy, no title repeat
- lede: 240–400 chars, what/why-now/so-what
- why_it_matters: 2–4 bullets, concrete impacts; include at least one number (%, €, kpl)
- analysis: 600–900 words, argument > narrative > evidence; cite figures; avoid fluff
- cta: human-like next step (readers' POV), 8–12 words
- tags: 3–6 slugs (e.g. "nato", "energia", "euribor")
- local_fi:
   - If origin_country = "FI": deepen the Finland angle (policy, economy, sectors, firms, labor, energy, geopolitics). Include 1–3 specific Finnish data points.
   - Else: add a section "Vaikutus Suomeen": channels, exposed sectors, tail risks, timeline, probability.
- local_fi_score: 0..1 (how material for Finland)

Constraints:
- Do not repeat the headline.
- Prefer concrete numbers, not generalities.
- Plain UTF-8 text, no markdown, no lists inside JSON values (bullets as dash-led lines).
- Return only valid minified JSON.

Example Finnish data points to reference when relevant:
- GDP: €270 miljardia (2024)
- Inflaatio: 3.2% (viimeisin)
- Työttömyys: 7.1% 
- Asuntolainat: 80% vaihtuvakorkoisia
- Vientiosuus BKT:sta: 37%
- Sähkönkulutus: 82 TWh/vuosi
- Metsäteollisuus: 20% viennistä
- Nokia/teknologia: 15% viennistä

Return only valid minified JSON."""

ENGLISH_ENRICHMENT_SYSTEM = """You are a senior macro & markets analyst. Your output must be concise in structure, dense in signal, and rich in concrete detail."""

ENGLISH_ENRICHMENT_TEMPLATE = """Context:
- Headline: {title}
- Source: {source_name} ({source_url})
- Published: {published_at}
- Raw summary: {summary_raw}
- Category: {category_guess}
- Country: {origin_country}

Task:
Return minified JSON:
- kicker: 4–8 words
- lede: 240–400 chars (what/why now/so what)
- why_it_matters: 3 bullets, each concrete & with a number (%, $, units)
- analysis: 700–1000 words, argument-first, data-backed; weave mechanism, actors, timeline, magnitudes, and second-order effects. Include 3–5 specific figures (ranges ok). Avoid hedging & clichés.
- cta: 8–12 words, actionable next step
- tags: 4–7 slugs
- local_fi: Optional "Vaikutus Suomeen" section if globally relevant
- local_fi_score: 0..1 if local_fi provided

Constraints:
- No headline repetition.
- Plain text, no markdown.
- Return only valid minified JSON."""

# Quality validation patterns
FORBIDDEN_PHRASES = [
    "only time will tell",
    "game-changer",
    "may impact",
    "could potentially",
    "it remains to be seen",
    "analysts are divided",
    "experts suggest",
    "sources say",
    "according to reports"
]

# Required number patterns for validation
import re
NUMBER_PATTERN = re.compile(r'\d+(?:\.\d+)?(?:%|€|\$|kpl|miljardia|miljoonaa|tuhatta|TWh|BKT)')

def validate_enrichment(enriched_data: dict, origin_country: str = None) -> dict:
    """
    Validate enriched content against quality requirements
    Returns dict with 'valid': bool and 'errors': list
    """
    errors = []
    
    # Check required fields
    required_fields = ['kicker', 'lede', 'why_it_matters', 'analysis', 'cta', 'tags']
    for field in required_fields:
        if field not in enriched_data:
            errors.append(f"Missing required field: {field}")
        elif not enriched_data[field]:
            errors.append(f"Empty required field: {field}")
    
    if errors:
        return {'valid': False, 'errors': errors}
    
    # Length validations
    if len(enriched_data.get('lede', '')) < 240:
        errors.append(f"Lede too short: {len(enriched_data['lede'])} chars (min 240)")
    
    if len(enriched_data.get('analysis', '')) < 600:
        errors.append(f"Analysis too short: {len(enriched_data['analysis'])} chars (min 600)")
    
    # Number requirements
    why_it_matters = enriched_data.get('why_it_matters', '')
    if not NUMBER_PATTERN.search(why_it_matters):
        errors.append("why_it_matters must contain at least one number with unit")
    
    analysis = enriched_data.get('analysis', '')
    numbers_in_analysis = len(NUMBER_PATTERN.findall(analysis))
    if numbers_in_analysis < 2:
        errors.append(f"Analysis must contain at least 2 numbers with units (found {numbers_in_analysis})")
    
    # Forbidden phrases
    full_text = f"{enriched_data.get('lede', '')} {enriched_data.get('analysis', '')}"
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in full_text.lower():
            errors.append(f"Contains forbidden phrase: '{phrase}'")
    
    # Finnish requirements
    if origin_country == "FI":
        if 'local_fi' not in enriched_data:
            errors.append("local_fi required for Finnish content")
        if 'local_fi_score' not in enriched_data:
            errors.append("local_fi_score required for Finnish content")
    
    # Score validation
    if 'local_fi_score' in enriched_data:
        score = enriched_data['local_fi_score']
        if not isinstance(score, (int, float)) or not (0 <= score <= 1):
            errors.append(f"local_fi_score must be 0-1 (got {score})")
    
    # Tags validation
    tags = enriched_data.get('tags', [])
    if not isinstance(tags, list) or len(tags) < 3:
        errors.append(f"Tags must be list with 3+ items (got {len(tags) if isinstance(tags, list) else 'not list'})")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'word_count': len(analysis.split()) if analysis else 0,
        'number_count': numbers_in_analysis
    }

def get_prompt_template(origin_country: str = None) -> tuple:
    """Get appropriate prompt template based on origin country"""
    if origin_country == "FI":
        return FINNISH_ENRICHMENT_SYSTEM, FINNISH_ENRICHMENT_TEMPLATE
    else:
        return ENGLISH_ENRICHMENT_SYSTEM, ENGLISH_ENRICHMENT_TEMPLATE
