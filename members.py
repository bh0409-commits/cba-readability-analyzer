"""Board Member Language Taxonomy — Transparency Report "Final Vote Submissions".

Extracts each Board member's individual vote rationale from Section B of a
CBA Transparency Report and scores it on five 1-5 axes (Aikman scorecard
format). Bands are anchored to metric thresholds so scores are reproducible.

Axis conventions (1 → 5):
  hawkish_dovish        1 = strongly dovish        5 = strongly hawkish
  optimistic_pessimistic 1 = pessimistic outlook   5 = optimistic outlook
  technical_narrative   1 = narrative / plain      5 = highly technical
  individual_collective 1 = collective voice       5 = individual voice
  certainty_hedging     1 = heavy hedging          5 = decisive / certain

Hawkish/dovish word lists adapted from published CB dictionaries
(cf. Correa et al. 2021; Gorodnichenko, Pham & Talavera 2021) — flagged in
the feature spec as candidate methodology citations.
"""

import re
import textstat

from extractor import _is_junk_line, _clean_inline_artifacts
from analyzer import (
    _words, _sentences, _jargon_density, _lexical_diversity,
    FORWARD_WORDS, HEDGE_WORDS,
)

# ── Section B extraction ───────────────────────────────────────────────────────

SECTION_B = re.compile(r'^B\.?\s*Final Vote Submissions', re.IGNORECASE | re.MULTILINE)

# Standalone header line: known title + capitalized 2-3 word name
MEMBER_HEADER = re.compile(
    r'^(Governor|Deputy Governor|Board Member)\s+'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*$',
    re.MULTILINE,
)

# Report footer that survives page-level cleanup ("Transparency Report | 2025 Q1")
_FOOTER = re.compile(r'^Transparency Report\s*\|.*$', re.IGNORECASE | re.MULTILINE)


def extract_member_statements(pdf_path: str) -> list:
    """Return [{title, name, text}, ...] from Section B, in document order.

    The full document is concatenated before pattern-matching — member
    statements can span page breaks (spec: October 2024 report, pp. 6-7).
    """
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text() or ""
            lines = [
                _clean_inline_artifacts(ln)
                for ln in raw.splitlines()
                if not _is_junk_line(ln)
            ]
            # Rotated sidebar text shreds into 1-2 char lines; drop them here
            # (extractor's SPACED_CHARS handles the single-line variant)
            pages.append("\n".join(ln for ln in lines if len(ln) > 2))

    full = "\n".join(pages)

    sec_match = SECTION_B.search(full)
    if not sec_match:
        return []
    section = _FOOTER.sub("", full[sec_match.end():])

    headers = list(MEMBER_HEADER.finditer(section))
    members = []
    for i, h in enumerate(headers):
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
        text = section[start:end].strip()
        if len(_words(text)) < 20:  # header matched inside a table, not a statement
            continue
        members.append({"title": h.group(1), "name": h.group(2), "text": text})
    return members


# ── Axis 1: Hawkish ↔ Dovish ───────────────────────────────────────────────────

HAWKISH_TERMS = re.compile(
    r'\b(tighten\w*|restrictive|contractionary|hikes?|'
    r'rais\w+ (?:the )?(?:policy |refinancing )?rate|'
    r'increas\w+ (?:the |in the )?(?:policy |refinancing )?rate|'
    r'inflationary pressures?|upside risks?|overheat\w*|'
    r'above (?:the )?target|exceed\w* (?:the )?target|'
    r'elevated inflation|persistent inflation|demand pressures?)\b',
    re.IGNORECASE,
)

DOVISH_TERMS = re.compile(
    r'\b(eas\w+ (?:of )?(?:the )?(?:monetary )?policy|easing|loosen\w*|'
    r'accommodative|stimulat\w*|expansionary|'
    r'(?:cut|cutting|lower\w*|reduc\w+) (?:the )?(?:policy |refinancing )?rate|'
    r'deflationary|downside risks?|below (?:the )?target|'
    r'weak demand|disinflation\w*|slowdown)\b',
    re.IGNORECASE,
)


def _band_net(net: float, evidence: int = 99) -> int:
    """Map a -1..+1 net balance onto 1-5.

    Extreme scores (1 or 5) require at least 3 matched terms — a lone
    dictionary hit shouldn't produce a 'strongly' rating."""
    if net <= -0.6:
        score = 1
    elif net <= -0.2:
        score = 2
    elif net < 0.2:
        score = 3
    elif net < 0.6:
        score = 4
    else:
        score = 5
    if evidence < 3:
        score = min(max(score, 2), 4)
    return score


def _score_hawkish_dovish(text: str) -> dict:
    hawk = [m.group(0).lower() for m in HAWKISH_TERMS.finditer(text)]
    dove = [m.group(0).lower() for m in DOVISH_TERMS.finditer(text)]
    total = len(hawk) + len(dove)
    if not total:
        return {"score": 3, "hawkish_terms": 0, "dovish_terms": 0,
                "rationale": "No directional policy vocabulary detected — neutral by default."}
    net = (len(hawk) - len(dove)) / total
    score = _band_net(net, evidence=total)
    lean = {1: "strongly dovish", 2: "leans dovish", 3: "balanced",
            4: "leans hawkish", 5: "strongly hawkish"}[score]
    examples = ", ".join(f"'{t}'" for t in sorted(set(hawk if net >= 0 else dove))[:3])
    sparse = " Sparse evidence — treat with caution." if total < 3 else ""
    return {
        "score": score, "hawkish_terms": len(hawk), "dovish_terms": len(dove),
        "rationale": (f"{len(hawk)} hawkish vs {len(dove)} dovish terms "
                      f"(net {net:+.2f}) — {lean}."
                      + (f" E.g. {examples}." if examples else "") + sparse),
    }


# ── Axis 2: Optimistic ↔ Pessimistic ───────────────────────────────────────────

OPTIMISTIC_TERMS = re.compile(
    r'\b(improv\w+|robust|strong\w*|favorable|resilien\w+|recover\w+|'
    r'stabiliz\w+|anchored|balanced|positive|growth|confiden\w+|'
    r'approach\w* (?:the |its )?(?:target|stable))\b',
    re.IGNORECASE,
)

PESSIMISTIC_TERMS = re.compile(
    r'\b(deteriorat\w+|weak\w*|concern\w*|volatil\w+|shocks?|declin\w+|'
    r'worsen\w*|adverse|instability|stress|vulnerab\w+|threat\w*|'
    r'recession\w*|crisis)\b',
    re.IGNORECASE,
)


def _score_outlook(text: str) -> dict:
    opt = len(OPTIMISTIC_TERMS.findall(text))
    pes = len(PESSIMISTIC_TERMS.findall(text))
    total = opt + pes
    if not total:
        return {"score": 3, "optimistic_terms": 0, "pessimistic_terms": 0,
                "rationale": "No outlook vocabulary detected — neutral by default."}
    net = (opt - pes) / total
    score = _band_net(net, evidence=total)
    tone = {1: "pessimistic", 2: "leans pessimistic", 3: "mixed",
            4: "leans optimistic", 5: "optimistic"}[score]
    sparse = " Sparse evidence — treat with caution." if total < 3 else ""
    return {
        "score": score, "optimistic_terms": opt, "pessimistic_terms": pes,
        "rationale": f"{opt} positive-outlook vs {pes} negative-outlook terms (net {net:+.2f}) — {tone}.{sparse}",
    }


# ── Axis 3: Technical ↔ Narrative ──────────────────────────────────────────────

def _score_technical(text: str) -> dict:
    words = _words(text)
    fk = textstat.flesch_kincaid_grade(text) if words else 0.0
    jargon = _jargon_density(text, len(words))["jargon_per_100_words"]

    fk_band = 1 if fk <= 8 else 2 if fk <= 10 else 3 if fk <= 12 else 4 if fk <= 14 else 5
    jg_band = 1 if jargon == 0 else 2 if jargon < 1 else 3 if jargon < 2 else 4 if jargon < 4 else 5
    score = round((fk_band + jg_band) / 2)

    ttr = _lexical_diversity(words)["ttr"]
    style = {1: "plain narrative", 2: "mostly narrative", 3: "moderately technical",
             4: "technical", 5: "highly technical"}[score]
    return {
        "score": score, "fk_grade": round(fk, 1),
        "jargon_per_100_words": jargon, "ttr": ttr,
        "rationale": (f"FK grade {fk:.1f}, {jargon} jargon terms/100 words, "
                      f"TTR {ttr:.2f} — {style}."),
    }


# ── Axis 4: Individual ↔ Collective ────────────────────────────────────────────

FIRST_PERSON_SINGULAR = re.compile(r'\b(I|my|me|mine)\b')
COLLECTIVE_VOICE = re.compile(
    r'\b(we|our|us|ours)\b|\bthe (?:Central Bank )?Board\b|\bthe Central Bank\b',
    re.IGNORECASE,
)


def _score_voice(text: str) -> dict:
    # First-person-singular "I" is case-sensitive by nature; my/me/mine are not
    fps = len(FIRST_PERSON_SINGULAR.findall(text))
    coll = len(COLLECTIVE_VOICE.findall(text))
    total = fps + coll
    if not total:
        return {"score": 3, "first_person_count": 0, "collective_count": 0,
                "rationale": "No voice markers detected — indeterminate."}
    share = fps / total
    score = 5 if share >= 0.8 else 4 if share >= 0.6 else 3 if share >= 0.4 else 2 if share >= 0.2 else 1
    voice = {1: "strongly collective", 2: "mostly collective", 3: "mixed voice",
             4: "mostly individual", 5: "strongly individual"}[score]
    return {
        "score": score, "first_person_count": fps, "collective_count": coll,
        "rationale": (f'{fps} first-person-singular vs {coll} collective/institutional '
                      f'markers ({share:.0%} individual) — {voice}.'),
    }


# ── Axis 5: Certainty ↔ Hedging ────────────────────────────────────────────────

def _score_certainty(text: str) -> dict:
    fwd = len(FORWARD_WORDS.findall(text))
    hedge = len(HEDGE_WORDS.findall(text))
    if hedge == 0:
        ratio = None
        score = 5 if fwd else 3
    else:
        ratio = fwd / hedge
        score = 5 if ratio >= 2 else 4 if ratio >= 1.5 else 3 if ratio >= 1.0 else 2 if ratio >= 0.5 else 1
    stance = {1: "heavily hedged", 2: "cautious", 3: "mixed",
              4: "mostly decisive", 5: "decisive"}[score]
    ratio_str = f"{ratio:.2f}" if ratio is not None else "∞ (no hedges)"
    return {
        "score": score, "forward_words": fwd, "hedge_words": hedge,
        "forward_hedge_ratio": round(ratio, 2) if ratio is not None else None,
        "rationale": f"{fwd} forward-looking vs {hedge} hedge words (ratio {ratio_str}) — {stance}.",
    }


# ── Entry point ────────────────────────────────────────────────────────────────

AXES = ("hawkish_dovish", "optimistic_pessimistic", "technical_narrative",
        "individual_collective", "certainty_hedging")


def score_statement(text: str) -> dict:
    return {
        "word_count": len(_words(text)),
        "sentence_count": len(_sentences(text)),
        "hawkish_dovish": _score_hawkish_dovish(text),
        "optimistic_pessimistic": _score_outlook(text),
        "technical_narrative": _score_technical(text),
        "individual_collective": _score_voice(text),
        "certainty_hedging": _score_certainty(text),
    }


def profile_report(pdf_path: str) -> list:
    """Full pipeline: extract Section B member statements and score each."""
    return [
        {**m, "scores": score_statement(m["text"])}
        for m in extract_member_statements(pdf_path)
    ]
