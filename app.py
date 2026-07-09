"""Streamlit app — CBA Readability Analyzer (Papikyan design)."""

import base64, os, tempfile, json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from extractor import extract_text
from analyzer import analyze, save_json

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CBA Readability Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Logo ────────────────────────────────────────────────────────────────────────
_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Designs", "CBA Logo Eng Black Transparent.png"
)

def _logo_html():
    try:
        with open(_LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="Central Bank of Armenia" class="cba-logo">'
    except Exception:
        return '<div style="font-size:11px;font-weight:700;letter-spacing:0.1em;color:var(--navy);margin-top:8px;text-align:right;">CENTRAL BANK<br>OF ARMENIA</div>'

LOGO_HTML = _logo_html()

# ── CSS injection via JS (avoids markdown parser mangling <style> content) ───────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');
:root {
  --navy: #00163b;
  --navy-70: rgba(0,22,59,0.7);
  --navy-40: rgba(0,22,59,0.4);
  --navy-10: rgba(0,22,59,0.08);
  --gold: #d39c1f;
  --teal: #24575e;
  --teal-12: rgba(36,87,94,0.10);
  --paper: #f1f2f2;
  --card: #ffffff;
  --line: rgba(0,22,59,0.10);
  --good: #24575e;
  --fair: #d39c1f;
  --hard: #86050c;
}
.stApp { background: var(--paper) !important; }
.main .block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 1100px !important; }
section[data-testid="stSidebar"] > div:first-child { background: var(--card) !important; }
div[data-testid="stMarkdownContainer"] { font-family: 'Inter', sans-serif; }
.stFileUploader > div { background: var(--card) !important; border: 1px solid var(--line) !important; border-radius: 10px !important; }
* { box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; color: var(--navy); }
.cba-logo { height: 44px; width: auto; display: block; margin-top: 4px; flex-shrink: 0; }
.eyebrow { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--teal); font-weight: 600; margin-bottom: 10px; }
.app-title { font-family: 'Source Serif 4', serif; font-weight: 700; font-size: 36px; line-height: 1.1; margin: 0 0 12px; color: var(--navy); }
.app-sub { font-size: 15px; color: var(--navy-70); max-width: 680px; line-height: 1.6; margin: 0 0 24px; }
details.disc { border: 1px solid var(--line); border-radius: 10px; background: var(--card); margin-bottom: 24px; overflow: hidden; }
details.disc summary { list-style: none; cursor: pointer; padding: 14px 18px; display: flex; align-items: center; gap: 10px; font-size: 13.5px; color: var(--navy); font-weight: 500; }
details.disc summary::-webkit-details-marker { display: none; }
.disc-body { padding: 0 18px 18px 18px; font-size: 13px; color: var(--navy-70); line-height: 1.7; }
.disc-body b { color: var(--navy); }
.file-chip { display: inline-flex; align-items: center; gap: 10px; background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px 16px; font-size: 13px; color: var(--navy-70); margin-bottom: 24px; }
.file-chip .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--good); flex-shrink: 0; }
.file-chip b { color: var(--navy); font-weight: 600; }
.scale-key { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 14px 0; display: flex; align-items: center; gap: 22px; flex-wrap: wrap; margin-bottom: 0; }
.scale-key .lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--navy-40); font-weight: 600; }
.scale-key .item { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--navy-70); }
.scale-key .sw { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.sec-head { display: flex; align-items: baseline; justify-content: space-between; border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 20px; margin-top: 48px; }
.sec-head h2 { font-family: 'Source Serif 4', serif; font-size: 22px; font-weight: 600; margin: 0; color: var(--navy); }
.sec-head .note { font-size: 12px; color: var(--navy-40); }
.cbag { display: grid; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; margin-bottom: 0; }
.cbag.c2 { grid-template-columns: repeat(2, 1fr); }
.cbag.c3 { grid-template-columns: repeat(3, 1fr); }
.cbag.c4 { grid-template-columns: repeat(4, 1fr); }
.cbag + .cbag { border-top: none !important; border-radius: 0 0 12px 12px !important; }
.cell { background: var(--card); padding: 20px 22px; }
.cell .k { font-size: 13px; color: var(--navy); font-weight: 600; margin-bottom: 8px; }
.cell .v { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--navy); line-height: 1; }
.cell .v small { font-size: 13px; font-weight: 500; color: var(--navy-40); margin-left: 4px; }
.cell .cap { font-size: 12px; color: var(--navy-40); margin-top: 8px; line-height: 1.4; }
.mc { background: var(--card); padding: 20px 22px; }
.mc .top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; gap: 8px; }
.mc .k { font-size: 13px; color: var(--navy); font-weight: 600; }
.mc .v { font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--navy); white-space: nowrap; line-height: 1; }
.mc .v small { font-size: 13px; font-weight: 500; color: var(--navy-40); margin-left: 3px; }
.mc .gb { font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 4px; margin-left: 7px; vertical-align: 3px; background: var(--navy-10); color: var(--navy); letter-spacing: 0.04em; }
.bar { position: relative; height: 6px; border-radius: 4px; opacity: 0.65; }
.marker { position: absolute; top: -5px; width: 2px; height: 16px; background: var(--navy); border-radius: 1px; transform: translateX(-50%); }
.marker::before { content: ''; position: absolute; top: -3px; left: -3px; width: 8px; height: 8px; border-radius: 50%; background: var(--navy); }
.mc .cap { font-size: 12px; color: var(--navy-40); line-height: 1.5; margin-top: 12px; }
.sent-strip { display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.sc { background: var(--card); padding: 20px 22px; }
.sc .k { font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--navy); font-weight: 700; margin-bottom: 12px; }
.sent-pill { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; }
.sent-pill .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sc .cmpd { font-size: 11px; color: var(--navy-40); margin-top: 8px; font-variant-numeric: tabular-nums; }
.stbl { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.stbl thead th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--navy-40); font-weight: 600; padding: 14px 20px; background: var(--teal-12); border-bottom: 1px solid var(--line); }
.stbl tbody td { padding: 11px 20px; font-size: 13.5px; color: var(--navy); border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
.stbl tbody tr:last-child td { border-bottom: none; }
.stbl tbody tr:hover td { background: var(--navy-10); }
.callout { margin-top: 48px; background: var(--navy); color: #fff; border-radius: 14px; padding: 28px 32px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.callout .txt { font-size: 14px; line-height: 1.6; color: rgba(255,255,255,0.80); max-width: 500px; }
.callout .txt b { color: var(--gold); }
.callout .badge { font-family: 'Source Serif 4', serif; font-size: 14px; color: var(--gold); border: 1px solid rgba(211,156,31,0.4); padding: 8px 16px; border-radius: 8px; white-space: nowrap; flex-shrink: 0; }
"""

components.html(
    "<script>var s=window.parent.document.createElement('style');"
    f"s.textContent={json.dumps(_CSS)};"
    "window.parent.document.head.appendChild(s);</script>",
    height=0,
)



# ── Scale helpers ────────────────────────────────────────────────────────────────

def scale_position(value, low, high, invert=False):
    """Return 0–100 CSS % position of value within [low, high]."""
    if high == low:
        return 0.0
    pct = (value - low) / (high - low) * 100.0
    pct = max(0.0, min(100.0, pct))
    return 100.0 - pct if invert else pct


def make_gradient(good_end, fair_end, low, high, invert=False):
    """CSS linear-gradient with teal/gold/dark-red bands."""
    g = (good_end - low) / (high - low) * 100.0
    f = (fair_end - low) / (high - low) * 100.0
    if invert:
        g, f = 100.0 - g, 100.0 - f
        if g > f:
            g, f = f, g
    g, f = round(g, 1), round(f, 1)
    return (
        f"linear-gradient(to right,"
        f"var(--good) 0%,var(--good) {g}%,"
        f"var(--fair) {g}%,var(--fair) {f}%,"
        f"var(--hard) {f}%,var(--hard) 100%)"
    )


# Pre-built gradients
G_GRADE   = make_gradient(6, 12, 0, 20)                   # grade-level (lower=better)
G_FRE     = make_gradient(70, 50, 0, 100, invert=True)    # Flesch ease (higher=better)
G_REACH   = make_gradient(68, 51, 0, 85, invert=True)     # Reach % (higher=better, cap 85)
G_LONGSNT = make_gradient(10, 20, 0, 40)                  # Long sentences % (lower=better)
G_PASSIVE = make_gradient(15, 25, 0, 40)                  # Passive voice % (lower=better)
G_FWD     = make_gradient(1.5, 0.5, 0, 3, invert=True)   # Forward/hedge ratio (higher=better)
G_JARGON  = make_gradient(3, 6, 0, 10)                    # Jargon/100w (lower=better)
# TTR: non-monotonic — hard below 0.35, good 0.35–0.55, fair above
G_TTR = (
    "linear-gradient(to right,"
    "var(--hard) 0%,var(--hard) 58.3%,"    # 0–0.35 of 0.6 domain = repetitive
    "var(--good) 58.3%,var(--good) 91.7%," # 0.35–0.55 = good
    "var(--fair) 91.7%,var(--fair) 100%)"  # 0.55–0.6 = excess
)


# ── HTML builders ────────────────────────────────────────────────────────────────

def h_cell(label, value_html, caption=None):
    cap = f'<div class="cap">{caption}</div>' if caption else ''
    return f'<div class="cell"><div class="k">{label}</div><div class="v">{value_html}</div>{cap}</div>'


def h_mc(label, value_html, pct, grad, caption, grade=None):
    gb = f'<span class="gb">{grade}</span>' if grade else ''
    return f"""<div class="mc">
  <div class="top"><span class="k">{label}</span><span class="v">{value_html}{gb}</span></div>
  <div class="bar" style="background:{grad}"><div class="marker" style="left:{pct:.1f}%"></div></div>
  <div class="cap">{caption}</div>
</div>"""


def h_sent(period, label, compound):
    colors = {"Positive": "var(--good)", "Neutral": "var(--navy-40)", "Negative": "var(--hard)"}
    c = colors.get(label, "var(--navy-40)")
    sign = "+" if compound >= 0 else ""
    return f"""<div class="sc">
  <div class="k">{period}</div>
  <div class="sent-pill"><span class="dot" style="background:{c}"></span><span style="color:{c}">{label}</span></div>
  <div class="cmpd">compound {sign}{compound:.3f}</div>
</div>"""


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Options**")
    is_mpr = st.checkbox("Apply MPR filtering", value=True,
        help="Skip cover/TOC pages and strip chart artifacts (CBA Monetary Policy Reports).")
    check_grammar = st.checkbox("Check grammar (slower)", value=False,
        help="Uses LanguageTool via Java — adds ~30–60 s. Requires Java.")


# ── Header ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:4px;">
  <div>
    <div class="eyebrow">Communication Quality Diagnostics</div>
    <h1 class="app-title">CBA Readability Analyzer</h1>
  </div>
  {LOGO_HTML}
</div>
<p class="app-sub">Score a document against Readable.com-equivalent metrics plus CBA-specific communication indicators. A horizontal scale runs through every scored metric — the marker shows at a glance where this document sits.</p>

<details class="disc">
  <summary>
    <span style="color:var(--teal);font-size:15px;margin-right:2px;">≡</span>
    Methodology &amp; Reference Key
  </summary>
  <div class="disc-body">
    <b>Letter grades:</b> A (≤6th grade) · B (7–9) · C (10–12) · D (13–16) · F (17+)<br><br>
    <b>Scale bar colors:</b> <span style="color:var(--good)">■</span> Accessible &nbsp;·&nbsp; <span style="color:var(--fair)">■</span> Moderate &nbsp;·&nbsp; <span style="color:var(--hard)">■</span> Difficult<br><br>
    <b>Flesch-Kincaid</b> — U.S. school-grade level required to read the text. ≤6 = accessible · 7–12 = moderate · 13+ = difficult<br>
    <b>Gunning Fog</b> — Years of formal education needed, weighted toward multi-syllable words<br>
    <b>Flesch Reading Ease</b> — 0–100; higher is easier. 70+ = easy · 30–50 = difficult · &lt;30 = very difficult<br>
    <b>Reach</b> — Estimated share of the general public able to read comfortably (formula caps at 85%)<br>
    <b>SMOG</b> — Counts polysyllabic words. Reliable predictor for policy and health documents<br>
    <b>Coleman-Liau</b> — Character-based; unaffected by syllable-counting errors<br>
    <b>ARI</b> — Character-to-word and word-to-sentence ratios; strong cross-check for FK<br><br>
    <b>Passive Voice:</b> &lt;15% = good · 15–25% = moderate · &gt;25% = problematic<br>
    <b>Jargon Density:</b> &lt;3 per 100 words = accessible · 3–6 = specialist · &gt;6 = highly technical<br>
    <b>Forward/Hedge Ratio:</b> &gt;1.5 = clear signaling · 0.5–1.5 = mixed · &lt;0.5 = overly cautious<br>
    <b>Lexical Diversity (TTR):</b> 0.35–0.55 = normal range · &lt;0.25 = repetitive
  </div>
</details>
""", unsafe_allow_html=True)


# ── Upload ───────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload a PDF to analyze", type=["pdf"])

if not uploaded:
    st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────────
with st.spinner("Extracting text from PDF…"):
    raw_bytes = uploaded.read()
    file_size_mb = len(raw_bytes) / 1_048_576
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    try:
        text = extract_text(tmp_path, is_mpr=is_mpr)
    finally:
        os.unlink(tmp_path)

if not text.strip():
    st.error("No prose text could be extracted from this PDF. Check that MPR filtering is appropriate for this document.")
    st.stop()

with st.expander("Extracted text preview (first 80 words)"):
    st.write(" ".join(text.split()[:80]) + "…")

with st.spinner("Computing metrics…"):
    m = analyze(text, check_grammar=check_grammar)

json_path = save_json(m, uploaded.name)

# ── File chip ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="file-chip">
  <span class="dot"></span>
  <b>{uploaded.name}</b>&ensp;·&ensp;{file_size_mb:.1f} MB&ensp;·&ensp;analysis complete
</div>
""", unsafe_allow_html=True)

# ── Scale key ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="scale-key">
  <span class="lbl">Reading scale</span>
  <span class="item"><span class="sw" style="background:var(--good)"></span>Accessible</span>
  <span class="item"><span class="sw" style="background:var(--fair)"></span>Moderate</span>
  <span class="item"><span class="sw" style="background:var(--hard)"></span>Difficult</span>
</div>
""", unsafe_allow_html=True)

# ── Part 1: Document Overview ─────────────────────────────────────────────────────
st.markdown("""
<div class="sec-head">
  <h2>Part 1 — Document Overview</h2>
  <span class="note">Readable.com-equivalent metrics</span>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="cbag c3">
  {h_cell("Overall Grade", m["overall_grade"])}
  {h_cell("Word Count", f'{m["word_count"]:,}')}
  {h_cell("Sentence Count", f'{m["sentence_count"]:,}')}
</div>
<div class="cbag c3">
  {h_cell("Paragraph Count", f'{m["paragraph_count"]:,}')}
  {h_cell("Sentences &gt; 30 Syllables", f'{m["long_sentences_count"]:,}<small>&nbsp;({m["long_sentences_pct"]}%)</small>')}
  {h_cell("Words &gt; 12 Letters", f'{m["long_words_count"]:,}<small>&nbsp;({m["long_words_pct"]}%)</small>')}
</div>
""", unsafe_allow_html=True)

# ── Core Readability ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="sec-head">
  <h2>Core Readability Metrics</h2>
  <span class="note">Marker shows position on the scale above</span>
</div>""", unsafe_allow_html=True)

fk  = m["flesch_kincaid_grade"]
fog = m["gunning_fog"]
fre = m["flesch_reading_ease"]
rch = m["reach_pct"]

st.markdown(f"""
<div class="cbag c2">
  {h_mc("Flesch-Kincaid Grade Level", fk,
    scale_position(fk, 0, 20), G_GRADE,
    "U.S. school-grade level required to read the text on first pass.",
    grade=m.get("flesch_kincaid_letter"))}
  {h_mc("Gunning Fog Index", fog,
    scale_position(fog, 0, 20), G_GRADE,
    "Years of formal education needed, weighted toward complex multi-syllable words.",
    grade=m.get("gunning_fog_letter"))}
  {h_mc("Flesch Reading Ease", fre,
    scale_position(fre, 0, 100, invert=True), G_FRE,
    "0–100 scale; higher is easier. Typical policy documents sit in the 30–50 band.")}
  {h_mc("Reach Score", f'{rch}<small>%</small>',
    scale_position(rch, 0, 85, invert=True), G_REACH,
    "Estimated share of the general public who can read the document comfortably.")}
</div>
""", unsafe_allow_html=True)

# ── Additional Indices ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="sec-head">
  <h2>Additional Readability Indices</h2>
  <span class="note">Independent formulas cross-checking FK &amp; Fog</span>
</div>""", unsafe_allow_html=True)

smog_v = m.get("smog_grade", 0)
cli_v  = m.get("coleman_liau_grade", 0)
ari_v  = m.get("ari_grade", 0)

st.markdown(f"""
<div class="cbag c3">
  {h_mc("SMOG Grade", smog_v,
    scale_position(smog_v, 0, 20), G_GRADE,
    "Simple Measure of Gobbledygook — counts polysyllabic words. Strong predictor for policy documents.",
    grade=m.get("smog_letter"))}
  {h_mc("Coleman-Liau Index", cli_v,
    scale_position(cli_v, 0, 20), G_GRADE,
    "Character-based formula; unaffected by syllable-counting errors. Useful with heavy technical terminology.",
    grade=m.get("coleman_liau_letter"))}
  {h_mc("Automated Readability Index", ari_v,
    scale_position(ari_v, 0, 20), G_GRADE,
    "Character-to-word and word-to-sentence ratios. Strong correlation with FK; useful cross-check.",
    grade=m.get("ari_letter"))}
</div>""", unsafe_allow_html=True)

gi = m["grammar_issues"]
if not check_grammar:
    gi_html = '<span style="color:var(--navy-40);font-size:18px;">Not checked</span>'
elif gi == -1:
    gi_html = '<span style="color:var(--navy-40);font-size:18px;">Unavailable</span>'
else:
    gi_html = f'{gi:,}'

adv_cap = f'Adverbs as a share of total words — &lt;5% = good · 5–10% = moderate · &gt;10% = overused'

st.markdown(f"""
<div class="cbag c3">
  {h_cell("Adverb Count", f'{m["adverb_count"]:,}<small>&nbsp;({m["adverb_pct"]}%)</small>', adv_cap)}
  {h_cell("Spelling Issues", f'{m["spelling_issues"]:,}')}
  <div class="cell"><div class="k">Grammar Issues</div><div class="v">{gi_html}</div></div>
</div>""", unsafe_allow_html=True)

# ── Sentiment ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sec-head">
  <h2>Sentiment Analysis</h2>
  <span class="note">VADER compound score, split by document third</span>
</div>""", unsafe_allow_html=True)

sent = m["sentiment"]
st.markdown(f"""
<div class="sent-strip">
  {h_sent("Overall tone", sent["overall_label"], sent["overall_compound"])}
  {h_sent("Beginning (1st third)", sent["beginning_label"], sent["beginning_compound"])}
  {h_sent("Middle (2nd third)", sent["middle_label"], sent["middle_compound"])}
  {h_sent("End (3rd third)", sent["end_label"], sent["end_compound"])}
</div>""", unsafe_allow_html=True)

# ── Part 2 ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sec-head">
  <h2>Part 2 — CBA-Specific Metrics</h2>
  <span class="note">Forward guidance · voice · jargon · lexical diversity</span>
</div>""", unsafe_allow_html=True)

ratio = m.get("forward_hedge_ratio")
ratio_v   = ratio if ratio is not None else 0.0
ratio_str = f"{ratio_v:.2f}" if ratio is not None else "N/A"
passive_pct = m["passive_sentence_pct"]
jargon_d    = m["jargon_per_100_words"]
ttr         = m["ttr"]
ttr_pos     = scale_position(ttr, 0, 0.6)   # non-monotonic — position in 0–0.6 domain

fwd_cap = (
    f'Forward-looking: {m["forward_word_count"]} words &nbsp;·&nbsp; '
    f'Hedge: {m["hedge_word_count"]} words. '
    f'&gt;1.5 = clear signaling · 0.5–1.5 = mixed · &lt;0.5 = overly cautious'
)

st.markdown(f"""
<div class="cbag c3">
  {h_mc("Forward / Hedge Ratio", ratio_str,
    scale_position(ratio_v, 0, 3, invert=True), G_FWD, fwd_cap)}
  {h_mc("Passive Voice Rate",
    f'{m["passive_sentence_count"]:,}<small>&nbsp;({passive_pct}%)</small>',
    scale_position(passive_pct, 0, 40), G_PASSIVE,
    "Passive sentences as a share of total. &lt;15% = good · 15–25% = moderate · &gt;25% = high.")}
  {h_mc("Jargon Density",
    f'{m["jargon_count"]}<small>&nbsp;terms</small>',
    scale_position(jargon_d, 0, 10), G_JARGON,
    f'{jargon_d} jargon terms per 100 words. &lt;3 = accessible · 3–6 = specialist · &gt;6 = highly technical.')}
</div>
<div class="cbag c2">
  {h_cell("Unique Words", f'{m["unique_words"]:,}', "Distinct word forms in the document")}
  {h_mc("Lexical Diversity (Type-Token Ratio)",
    f'{ttr:.4f}<small>&nbsp;({m["ttr_pct"]}%)</small>',
    ttr_pos, G_TTR,
    "Unique words ÷ total words. 0.35–0.55 = normal range · &lt;0.25 = repetitive (expected in long policy documents).")}
</div>""", unsafe_allow_html=True)

# ── Section-Level Readability ──────────────────────────────────────────────────────
sections = m.get("section_readability", [])
if sections:
    st.markdown("""
    <div class="sec-head">
      <h2>Section-Level Readability</h2>
      <span class="note">Detected sections within the document</span>
    </div>""", unsafe_allow_html=True)

    rows = "".join(
        f'<tr><td>{s["section"]}</td><td>{s["fk_grade"]}</td><td>{s["flesch_ease"]}</td></tr>'
        for s in sections
    )
    st.markdown(f"""
    <table class="stbl">
      <thead><tr><th>Section</th><th>FK Grade</th><th>Flesch Ease</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ── Export ─────────────────────────────────────────────────────────────────────────
flat = {k: v for k, v in m.items() if k not in ("sentiment", "section_readability")}
flat.update({f"sentiment_{k}": v for k, v in m["sentiment"].items()})
df_export = pd.DataFrame([flat])
df_export.insert(0, "document", uploaded.name)
csv = df_export.to_csv(index=False)

st.markdown("<br>", unsafe_allow_html=True)
st.download_button(
    "⬇ Download results as CSV",
    data=csv,
    file_name=f"{os.path.splitext(uploaded.name)[0]}_readability.csv",
    mime="text/csv",
)

# ── Footer callout ─────────────────────────────────────────────────────────────────
json_filename = os.path.basename(json_path)
st.markdown(f"""
<div class="callout">
  <div class="txt">Results saved to <b>{json_filename}</b>. Upload additional documents to build the longitudinal dataset. All scored metrics use the shared reading scale above.</div>
  <div class="badge">CBA · Monetary Policy Department</div>
</div>""", unsafe_allow_html=True)
