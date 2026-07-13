"""Compute readability metrics matching Readable.com + CBA-specific additions."""

import re
import json
import datetime
import os
import textstat
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from spellchecker import SpellChecker

# Ensure required NLTK data
for resource, kind in [
    ("averaged_perceptron_tagger_eng", "taggers"),
    ("punkt_tab", "taggers"),
    ("vader_lexicon", "sentiment"),
]:
    try:
        nltk.data.find(f"{kind}/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

_spell = SpellChecker()
_sia = SentimentIntensityAnalyzer()
_grammar_tool = None
_roberta_pipelines = None


def _get_grammar_tool():
    global _grammar_tool
    if _grammar_tool is None:
        import language_tool_python
        _grammar_tool = language_tool_python.LanguageTool("en-US")
    return _grammar_tool


def _get_roberta_pipelines():
    """Lazy-load the CentralBankRoBERTa agent + sentiment classifiers.

    Pfeifer & Marohl (2023). Downloads model weights from HuggingFace on
    first use (~500 MB per model)."""
    global _roberta_pipelines
    if _roberta_pipelines is None:
        from transformers import pipeline
        agent = pipeline(
            "text-classification",
            model="Moritz-Pfeifer/CentralBankRoBERTa-agent-classifier",
        )
        sentiment = pipeline(
            "text-classification",
            model="Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier",
        )
        _roberta_pipelines = (agent, sentiment)
    return _roberta_pipelines


# ── helpers ────────────────────────────────────────────────────────────────────

def _sentences(text: str) -> list:
    try:
        return nltk.sent_tokenize(text)
    except Exception:
        return re.split(r'(?<=[.!?])\s+', text)


def _words(text: str) -> list:
    return re.findall(r"[A-Za-z']+", text)


def _alpha_words(text: str) -> list:
    return re.findall(r"[A-Za-z]+", text)


# ── Part 1: Readable.com metrics ───────────────────────────────────────────────

def _letter_grade(grade: float) -> str:
    """Standard grade-level → letter grade used for FK and all new indices."""
    if grade <= 6:
        return "A"
    if grade <= 9:
        return "B"
    if grade <= 12:
        return "C"
    if grade <= 16:
        return "D"
    return "F"


# ── Additional readability indices ─────────────────────────────────────────────

def _smog_score(text: str, sents: list, words: list) -> float:
    """SMOG: 1.0430 × √(polysyllables × 30/sentences) + 3.1291"""
    n_sents = len(sents)
    if n_sents < 3:
        return 0.0
    polysyllables = sum(1 for w in words if textstat.syllable_count(w) >= 3)
    return round(1.0430 * (polysyllables * (30 / n_sents)) ** 0.5 + 3.1291, 1)


def _coleman_liau_score(text: str, words: list, sents: list) -> float:
    """Coleman-Liau: 0.0588×L − 0.296×S − 15.8
    L = avg chars per 100 words, S = avg sentences per 100 words"""
    n_words = len(words)
    n_sents = len(sents)
    if not n_words or not n_sents:
        return 0.0
    chars = sum(len(w) for w in words)
    L = (chars / n_words) * 100
    S = (n_sents / n_words) * 100
    return round(0.0588 * L - 0.296 * S - 15.8, 1)


def _ari_score(text: str, words: list, sents: list) -> float:
    """ARI: 4.71×(chars/words) + 0.5×(words/sentences) − 21.43"""
    n_words = len(words)
    n_sents = len(sents)
    if not n_words or not n_sents:
        return 0.0
    chars = sum(len(w) for w in words)
    return round(4.71 * (chars / n_words) + 0.5 * (n_words / n_sents) - 21.43, 1)


def _reach_score(flesch_ease: float) -> float:
    """Linear interpolation: FRE 100 → 85%, FRE 0 → 0%. Capped at 85%."""
    score = (flesch_ease / 100) * 85
    return round(min(max(score, 0), 85), 1)


def _sentiment_label(compound: float) -> str:
    if compound >= 0.05:
        return "Positive"
    if compound <= -0.05:
        return "Negative"
    return "Neutral"


def _sentiment(text: str) -> dict:
    overall = _sia.polarity_scores(text)
    thirds = len(text) // 3
    parts = {
        "beginning": text[:thirds],
        "middle": text[thirds: 2 * thirds],
        "end": text[2 * thirds:],
    }
    result = {
        "overall_compound": round(overall["compound"], 3),
        "overall_label": _sentiment_label(overall["compound"]),
    }
    for name, chunk in parts.items():
        s = _sia.polarity_scores(chunk)
        result[f"{name}_compound"] = round(s["compound"], 3)
        result[f"{name}_label"] = _sentiment_label(s["compound"])
    return result


ROBERTA_AGENTS = ("households", "firms", "financial_sector", "government")


def _normalize_agent_label(label: str) -> str:
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def _roberta_sentiment(sents: list) -> dict:
    """Agent-conditioned sentiment via CentralBankRoBERTa.

    Each sentence is tagged with the economic agent it concerns (households,
    firms, financial sector, government); sentences with an agent label are
    then scored positive/negative for that agent. Binary output, no neutral."""
    agent_clf, sent_clf = _get_roberta_pipelines()

    # Very short fragments (line artifacts, headings) carry no scoreable content
    candidates = [s for s in sents if len(_words(s)) >= 4]
    if not candidates:
        return {
            "n_sentences": len(sents), "n_classified": 0, "n_other": 0,
            "overall_pos_pct": None, "overall_neg_pct": None,
            "by_agent": {a: {"count": 0, "pos": 0, "neg": 0,
                             "pos_pct": None, "neg_pct": None}
                         for a in ROBERTA_AGENTS},
        }

    # RoBERTa hard limit is 512 tokens; must be passed at call time to take effect
    tok_kwargs = {"batch_size": 16, "truncation": True, "max_length": 512}
    agent_preds = agent_clf(candidates, **tok_kwargs)

    by_agent = {a: {"count": 0, "pos": 0, "neg": 0} for a in ROBERTA_AGENTS}
    labeled = [
        (s, agent)
        for s, pred in zip(candidates, agent_preds)
        if (agent := _normalize_agent_label(pred["label"])) in ROBERTA_AGENTS
    ]

    if labeled:
        sent_preds = sent_clf([s for s, _ in labeled], **tok_kwargs)
        for (s, agent), pred in zip(labeled, sent_preds):
            bucket = by_agent[agent]
            bucket["count"] += 1
            if "pos" in pred["label"].lower():
                bucket["pos"] += 1
            else:
                bucket["neg"] += 1

    total = sum(b["count"] for b in by_agent.values())
    total_pos = sum(b["pos"] for b in by_agent.values())
    for b in by_agent.values():
        b["pos_pct"] = round(b["pos"] / b["count"] * 100, 1) if b["count"] else None
        b["neg_pct"] = round(b["neg"] / b["count"] * 100, 1) if b["count"] else None

    return {
        "n_sentences": len(sents),
        "n_classified": total,
        # Agent model's 5th class is "Central Bank" — sentences about the CBA
        # itself, deliberately outside the four economic-agent buckets
        "n_other": len(candidates) - total,
        "overall_pos_pct": round(total_pos / total * 100, 1) if total else None,
        "overall_neg_pct": round((total - total_pos) / total * 100, 1) if total else None,
        "by_agent": by_agent,
    }


# ── Part 2: CBA-specific metrics ───────────────────────────────────────────────

FORWARD_WORDS = re.compile(
    r'\b(will|shall|expects?|anticipates?|is expected|are expected|projects?|forecasts?)\b',
    re.IGNORECASE,
)

HEDGE_WORDS = re.compile(
    r'\b(may|might|could|possibly|approximately|around|roughly|if|uncertain|unclear)\b',
    re.IGNORECASE,
)

PASSIVE_PATTERN = re.compile(
    r'\b(is|are|was|were|be|been|being)\s+(?:\w+\s+){0,2}\w+(?:ed|en)\b',
    re.IGNORECASE,
)

JARGON_LIST = [
    "basis points", "refinancing rate", "lombard repo", "nairu", "fpas",
    "prmaps", "quantitative easing", "yield curve", "monetary transmission",
    "output gap", "potential gdp", "nominal anchor", "repo rate",
    "inflation expectations", "forward guidance", "neutral rate",
    "real effective exchange rate", "balance of payments", "current account",
]


def _jargon_density(text: str, word_count: int) -> dict:
    text_lower = text.lower()
    count = sum(text_lower.count(term) for term in JARGON_LIST)
    density = round(count / word_count * 100, 2) if word_count else 0
    return {"jargon_count": count, "jargon_per_100_words": density}


def _lexical_diversity(words: list) -> dict:
    if not words:
        return {"unique_words": 0, "ttr": 0.0, "ttr_pct": 0.0}
    unique = len(set(w.lower() for w in words))
    ttr = unique / len(words)
    return {
        "unique_words": unique,
        "ttr": round(ttr, 4),
        "ttr_pct": round(ttr * 100, 1),
    }


# ── Section-level readability ──────────────────────────────────────────────────

KNOWN_SECTIONS = re.compile(
    r'^(Executive Summary|Global Economy|Domestic Economy|Labor Market|'
    r'Financial Markets|Monetary Policy Outlook|Inflation|Economic Activity|'
    r'External Sector|Fiscal|Risks?|Conclusion)',
    re.IGNORECASE,
)


def _detect_sections(text: str) -> list:
    """Return list of (section_name, section_text) tuples."""
    lines = text.splitlines()
    sections = []
    current_name = "Preamble"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        is_heading = (
            (stripped.isupper() and 3 < len(stripped) < 80)
            or KNOWN_SECTIONS.match(stripped)
        )
        if is_heading and current_lines:
            sections.append((current_name, "\n".join(current_lines)))
            current_name = stripped.title()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_name, "\n".join(current_lines)))

    return [(n, t) for n, t in sections if len(t.split()) > 50]


def _section_readability(text: str) -> list:
    sections = _detect_sections(text)
    results = []
    for name, chunk in sections:
        try:
            fk = round(textstat.flesch_kincaid_grade(chunk), 1)
            fre = round(textstat.flesch_reading_ease(chunk), 1)
        except Exception:
            fk, fre = None, None
        results.append({"section": name, "fk_grade": fk, "flesch_ease": fre})
    return results


# ── Main entry point ───────────────────────────────────────────────────────────

def analyze(text: str, check_grammar: bool = False, run_roberta: bool = False) -> dict:
    sents = _sentences(text)
    words = _words(text)
    alpha = _alpha_words(text)
    # Readable.com counts each non-empty line as a paragraph (PDF lines are visual units)
    paragraphs = [ln for ln in text.splitlines() if ln.strip()]

    fk_grade = textstat.flesch_kincaid_grade(text)
    fog = textstat.gunning_fog(text)
    flesch_ease = textstat.flesch_reading_ease(text)
    smog = _smog_score(text, sents, words)
    cli = _coleman_liau_score(text, words, sents)
    ari = _ari_score(text, words, sents)

    long_sents = []
    for s in sents:
        syls = sum(textstat.syllable_count(w) for w in _words(s))
        if syls > 30:
            long_sents.append(s)

    long_words = [w for w in alpha if len(w) > 12]

    tagged = nltk.pos_tag(nltk.word_tokenize(text))
    adverbs = [w for w, tag in tagged if tag in ("RB", "RBR", "RBS")]

    misspelled = _spell.unknown(alpha)
    spelling_issues = [w for w in misspelled if len(w) >= 3]

    grammar_count = 0
    if check_grammar:
        try:
            tool = _get_grammar_tool()
            grammar_count = len(tool.check(text))
        except Exception:
            grammar_count = -1  # signals unavailable

    forward_count = len(FORWARD_WORDS.findall(text))
    hedge_count = len(HEDGE_WORDS.findall(text))
    fwd_hedge_ratio = round(forward_count / hedge_count, 2) if hedge_count else None

    passive_sents = [s for s in sents if PASSIVE_PATTERN.search(s)]

    jargon = _jargon_density(text, len(words))
    diversity = _lexical_diversity(words)
    sentiment = _sentiment(text)
    sections = _section_readability(text)

    roberta = None
    if run_roberta:
        try:
            roberta = _roberta_sentiment(sents)
        except Exception as e:
            roberta = {"error": str(e)}  # signals unavailable

    return {
        # Part 1 — core Readable.com metrics
        "flesch_kincaid_grade": round(fk_grade, 1),
        "flesch_kincaid_letter": _letter_grade(fk_grade),
        "gunning_fog": round(fog, 1),
        "gunning_fog_letter": _letter_grade(fog),
        "flesch_reading_ease": round(flesch_ease, 1),
        "overall_grade": _letter_grade(fk_grade),
        "reach_pct": _reach_score(flesch_ease),
        # Additional indices
        "smog_grade": smog,
        "smog_letter": _letter_grade(smog),
        "coleman_liau_grade": cli,
        "coleman_liau_letter": _letter_grade(cli),
        "ari_grade": ari,
        "ari_letter": _letter_grade(ari),
        "word_count": len(words),
        "sentence_count": len(sents),
        "paragraph_count": len(paragraphs),
        "long_sentences_count": len(long_sents),
        "long_sentences_pct": round(len(long_sents) / len(sents) * 100, 1) if sents else 0,
        "long_words_count": len(long_words),
        "long_words_pct": round(len(long_words) / len(words) * 100, 1) if words else 0,
        "adverb_count": len(adverbs),
        "adverb_pct": round(len(adverbs) / len(words) * 100, 1) if words else 0,
        "spelling_issues": len(spelling_issues),
        "grammar_issues": grammar_count,
        "sentiment": sentiment,
        "roberta_sentiment": roberta,
        # Part 2
        "forward_word_count": forward_count,
        "hedge_word_count": hedge_count,
        "forward_hedge_ratio": fwd_hedge_ratio,
        "passive_sentence_count": len(passive_sents),
        "passive_sentence_pct": round(len(passive_sents) / len(sents) * 100, 1) if sents else 0,
        "jargon_count": jargon["jargon_count"],
        "jargon_per_100_words": jargon["jargon_per_100_words"],
        "unique_words": diversity["unique_words"],
        "ttr": diversity["ttr"],
        "ttr_pct": diversity["ttr_pct"],
        "section_readability": sections,
    }


def save_json(metrics: dict, doc_name: str, output_dir: str = "results") -> str:
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    safe_name = re.sub(r'[^A-Za-z0-9_\-]', '_', os.path.splitext(doc_name)[0])
    path = os.path.join(output_dir, f"{safe_name}_{date_str}.json")
    with open(path, "w") as f:
        json.dump({"document": doc_name, "date": date_str, "metrics": metrics}, f, indent=2)
    return path
