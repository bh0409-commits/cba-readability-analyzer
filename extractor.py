"""PDF text extraction with CBA-specific filtering."""

import re
import pdfplumber

SIDEBAR_ARTIFACTS = {
    'tropeR', 'yciloP', 'yratenoM', 'soiranecs',
    'evitartsullI', 'esaC', 'citsemoD',
}

HEADER_PATTERN = re.compile(
    r'^Monetary Policy Report\s*\|?\s*\d{4}\s*Q\d', re.IGNORECASE
)

SECTION_DIVIDER = re.compile(r'^\d{2}\s*\|')

# Spaced characters like "1 Q 4 2 0 2" (rotated text artifacts)
SPACED_CHARS = re.compile(r'^(\S\s){3,}\S$')

# Lines that are mostly numbers/symbols (chart data, tables)
NUMERIC_LINE = re.compile(r'^[\d\s,.\-–—%+()/*:]+$')

SOURCE_NOTE = re.compile(r'^(Source|Notes?):?\s', re.IGNORECASE)

# Lines with too many slashes (date/series artifacts like /1/1/2/2/3/3/)
SLASH_HEAVY = re.compile(r'(/\w+){4,}')

# Figure/Table captions that are just labels
FIGURE_LABEL = re.compile(
    r'^(Figure|Table|Chart)\s+[\d\.]+[:\s]', re.IGNORECASE
)

# Lines with lots of scattered single-letter tokens (spaced-out rotated text)
SCATTERED_LETTERS = re.compile(r'^([A-Za-z]\s){5,}')


def _is_junk_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s in SIDEBAR_ARTIFACTS:
        return True
    if HEADER_PATTERN.match(s):
        return True
    if SECTION_DIVIDER.match(s):
        return True
    if SPACED_CHARS.match(s):
        return True
    if NUMERIC_LINE.match(s):
        return True
    if SOURCE_NOTE.match(s):
        return True
    if SLASH_HEAVY.search(s):
        return True
    if SCATTERED_LETTERS.match(s):
        return True
    if FIGURE_LABEL.match(s):
        return True
    # Lines where fewer than 40% of characters are letters (heavy symbol/number content)
    alpha_chars = sum(c.isalpha() for c in s)
    if len(s) > 20 and alpha_chars / len(s) < 0.40:
        return True
    return False


def _prose_ratio(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    alpha = sum(1 for w in words if any(c.isalpha() for c in w))
    return alpha / len(words)


# Inline chart artifacts: repeated numbers like "80 80" or year series
_INLINE_NUMS = re.compile(r'\b(\d{1,4})\s+\1\b')
_YEAR_SERIES = re.compile(r'(\b20\d{2}\s+){3,}')
_TRAILING_NUMS = re.compile(r'[\s\d]+$')


def _clean_inline_artifacts(line: str) -> str:
    """Remove chart axis values that leaked into prose lines."""
    line = _INLINE_NUMS.sub('', line)
    line = _YEAR_SERIES.sub('', line)
    # Strip trailing stray numbers left after removal
    if re.search(r'[a-zA-Z]', line):  # only if line has real words
        line = re.sub(r'\s+\d+(\.\d+)?\s*\.?\s*$', '.', line)
    return line.strip()


def _add_line_terminals(text: str) -> str:
    """Ensure every line ends with sentence-terminal punctuation.

    Lines without a terminal mark are treated by NLTK as continuations of the
    next line, merging fragments into enormous fake sentences and inflating
    Flesch-Kincaid. Adding a period forces the tokenizer to treat each line as
    its own unit.
    """
    result = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped and stripped[-1] not in ".?!:;":
            stripped += "."
        result.append(stripped)
    return "\n".join(result)


def extract_text(pdf_path: str, is_mpr: bool = True) -> str:
    """Extract prose text from a CBA PDF."""
    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1

            # Skip cover and TOC for MPRs
            if is_mpr and page_num <= 2:
                continue

            raw = page.extract_text() or ""

            # Skip chart/appendix pages flagged by Power BI
            if raw.strip().startswith("Power BI Desktop"):
                continue

            # Filter junk lines, then clean inline artifacts
            lines = raw.splitlines()
            clean_lines = [
                _clean_inline_artifacts(ln)
                for ln in lines
                if not _is_junk_line(ln)
            ]
            clean_lines = [ln for ln in clean_lines if ln]
            clean = "\n".join(clean_lines).strip()

            # Skip pages that are mostly non-prose (charts, tables)
            if _prose_ratio(clean) < 0.4:
                continue

            if clean:
                pages_text.append(clean)

    combined = "\n\n".join(pages_text)
    return _add_line_terminals(combined)
