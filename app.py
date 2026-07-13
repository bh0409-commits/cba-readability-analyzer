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

# ── Logo (embedded so it works on Streamlit Cloud without needing the file) ──────
_LOGO_B64 = "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"
LOGO_HTML = f'<img src="data:image/png;base64,{_LOGO_B64}" alt="Central Bank of Armenia" class="cba-logo">'


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
    run_roberta = st.checkbox("CentralBankRoBERTa sentiment (slower)", value=False,
        help="Agent-conditioned sentiment (Pfeifer & Marohl 2023). Downloads ~1 GB of model weights on first run; adds several minutes on CPU.")
    run_members = st.checkbox("Board Member Language Profile (Transparency Reports only)", value=False,
        help="Segments Section B 'Final Vote Submissions' by member and scores each on 5 language axes (1–5, Aikman scorecard format).")


# ── Header ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:4px;">
  <div>
    <div class="eyebrow">Communication Quality Diagnostics</div>
    <h1 class="app-title">CBA Readability Analyzer</h1>
  </div>
  {LOGO_HTML}
</div>
<p class="app-sub">Score a document on standard readability metrics plus CBA-specific communication indicators. A horizontal scale runs through every scored metric — the marker shows at a glance where this document sits.</p>

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
        member_profile = None
        if run_members:
            from members import profile_report
            member_profile = profile_report(tmp_path)
    finally:
        os.unlink(tmp_path)

if not text.strip():
    st.error("No prose text could be extracted from this PDF. Check that MPR filtering is appropriate for this document.")
    st.stop()

with st.expander("Extracted text preview (first 80 words)"):
    st.write(" ".join(text.split()[:80]) + "…")

with st.spinner("Computing metrics… (CentralBankRoBERTa adds several minutes)" if run_roberta else "Computing metrics…"):
    m = analyze(text, check_grammar=check_grammar, run_roberta=run_roberta)

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
  <span class="note">Standard readability metrics</span>
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

# ── CentralBankRoBERTa sentiment (toggle-gated, mirrors grammar-check pattern) ─────
rb = m.get("roberta_sentiment")
if run_roberta and rb:
    st.markdown("""
    <div class="sec-head">
      <h2>CentralBankRoBERTa Sentiment</h2>
      <span class="note">Agent-conditioned, per sentence · Pfeifer &amp; Marohl (2023)</span>
    </div>""", unsafe_allow_html=True)

    if "error" in rb:
        st.warning(f"CentralBankRoBERTa unavailable: {rb['error']}")
    else:
        pos, neg = rb["overall_pos_pct"], rb["overall_neg_pct"]
        overall_label = "Net positive" if (pos or 0) >= 50 else "Net negative"
        oc = "var(--good)" if (pos or 0) >= 50 else "var(--hard)"
        st.markdown(f"""
        <div class="sent-strip" style="grid-template-columns:1.2fr 1fr 1fr;">
          <div class="sc">
            <div class="k">Overall balance</div>
            <div class="sent-pill"><span class="dot" style="background:{oc}"></span><span style="color:{oc}">{overall_label}</span></div>
            <div class="cmpd">{rb["n_classified"]:,} agent-classified sentences</div>
          </div>
          <div class="sc"><div class="k">Positive sentences</div><div class="sent-pill"><span style="color:var(--good)">{pos}%</span></div></div>
          <div class="sc"><div class="k">Negative sentences</div><div class="sent-pill"><span style="color:var(--hard)">{neg}%</span></div></div>
        </div>""", unsafe_allow_html=True)

        agent_names = {
            "households": "Households", "firms": "Firms",
            "financial_sector": "Financial sector", "government": "Government",
        }
        rows = "".join(
            f'<tr><td>{agent_names[a]}</td><td>{b["count"]:,}</td>'
            f'<td>{b["pos_pct"] if b["pos_pct"] is not None else "—"}%</td>'
            f'<td>{b["neg_pct"] if b["neg_pct"] is not None else "—"}%</td></tr>'
            for a, b in rb["by_agent"].items()
        )
        st.markdown(f"""
        <table class="stbl" style="margin-top:16px;">
          <thead><tr><th>Agent</th><th>Sentences</th><th>Positive</th><th>Negative</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="font-size:12px;color:var(--navy-40);margin-top:10px;">
          {rb["n_classified"]:,} of {rb["n_sentences"]:,} sentences classified to an economic agent
          ({rb.get("n_other", 0):,} classified as "Central Bank" — about the CBA itself — and excluded).
          Binary classifier — no neutral class; percentages are within each agent's sentences.
        </p>""", unsafe_allow_html=True)

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

# ── Board Member Language Profile (toggle-gated, Transparency Reports only) ────────
AXIS_COLS = [
    ("hawkish_dovish", "Hawkish ↔ Dovish"),
    ("optimistic_pessimistic", "Optimistic ↔ Pessimistic"),
    ("technical_narrative", "Technical ↔ Narrative"),
    ("individual_collective", "Individual ↔ Collective"),
    ("certainty_hedging", "Certainty ↔ Hedging"),
]

if run_members:
    st.markdown("""
    <div class="sec-head">
      <h2>Board Member Language Profile</h2>
      <span class="note">Section B "Final Vote Submissions" · 1–5 scale, Aikman scorecard format</span>
    </div>""", unsafe_allow_html=True)

    if not member_profile:
        st.warning('No "Final Vote Submissions" section found — this profile only '
                   'applies to CBA Transparency Reports.')
    else:
        head = "".join(f"<th>{label}</th>" for _, label in AXIS_COLS)
        rows = ""
        for p in member_profile:
            s = p["scores"]
            cells = "".join(
                f'<td><b>{s[axis]["score"]}</b>/5<br>'
                f'<span style="font-size:11.5px;color:var(--navy-70);">{s[axis]["rationale"]}</span></td>'
                for axis, _ in AXIS_COLS
            )
            rows += (f'<tr><td><b>{p["name"]}</b><br>'
                     f'<span style="font-size:11.5px;color:var(--navy-40);">{p["title"]} · '
                     f'{s["word_count"]} words</span></td>{cells}</tr>')
        st.markdown(f"""
        <table class="stbl">
          <thead><tr><th>Member</th>{head}</tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="font-size:12px;color:var(--navy-40);margin-top:10px;">
          Scores are anchored to metric thresholds (dictionary counts, FK grade, jargon density,
          pronoun ratios, forward/hedge ratio) — see members.py for the bands. Axis direction:
          1 = dovish / pessimistic / narrative / collective / hedged · 5 = hawkish / optimistic /
          technical / individual / certain.
        </p>""", unsafe_allow_html=True)

        mrows = []
        for p in member_profile:
            s = p["scores"]
            row = {"document": uploaded.name, "title": p["title"], "name": p["name"],
                   "word_count": s["word_count"], "sentence_count": s["sentence_count"]}
            for axis, _ in AXIS_COLS:
                row[f"{axis}_score"] = s[axis]["score"]
                row[f"{axis}_rationale"] = s[axis]["rationale"]
            mrows.append(row)
        st.download_button(
            "⬇ Download member scores as CSV",
            data=pd.DataFrame(mrows).to_csv(index=False),
            file_name=f"{os.path.splitext(uploaded.name)[0]}_member_profile.csv",
            mime="text/csv",
        )

# ── Export ─────────────────────────────────────────────────────────────────────────
flat = {k: v for k, v in m.items() if k not in ("sentiment", "section_readability", "roberta_sentiment")}
flat.update({f"sentiment_{k}": v for k, v in m["sentiment"].items()})
rb_flat = m.get("roberta_sentiment")
if rb_flat and "error" not in rb_flat:
    flat["roberta_overall_pos_pct"] = rb_flat["overall_pos_pct"]
    flat["roberta_overall_neg_pct"] = rb_flat["overall_neg_pct"]
    flat["roberta_n_classified"] = rb_flat["n_classified"]
    for agent, b in rb_flat["by_agent"].items():
        flat[f"roberta_{agent}_count"] = b["count"]
        flat[f"roberta_{agent}_pos_pct"] = b["pos_pct"]
        flat[f"roberta_{agent}_neg_pct"] = b["neg_pct"]
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
