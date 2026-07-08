"""Streamlit app — CBA Readability Analyzer."""

import tempfile
import os
import streamlit as st
import pandas as pd

from extractor import extract_text
from analyzer import analyze, save_json

st.set_page_config(page_title="CBA Readability Analyzer", layout="wide")

st.title("CBA Readability Analyzer")
st.markdown("Upload a PDF to score it on readability metrics matching Readable.com, plus CBA-specific indicators.")

# ── Reference Key ──────────────────────────────────────────────────────────────
with st.expander("📖 Readability Reference Key", expanded=False):
    st.code("""READABILITY REFERENCE KEY
─────────────────────────────────────────────────────────────────────
OVERALL GRADE          A (best) → F (hardest to read)
Flesch-Kincaid Grade   ≤6 = accessible | 7–9 = standard | 10–12 = moderate | 17+ = very difficult
Gunning Fog            <10 = accessible | 10–13 = standard | 14+ = difficult
Flesch Reading Ease    70–100 = easy | 50–70 = standard | 30–50 = difficult | <30 = very difficult
Reach                  80%+ = excellent | 60–80% = good | <60% = limited audience
Sentences >30 syl.     <10% = good | 10–20% = acceptable | >20% = too complex
Adverb Rate            <5% = good | >10% = overused
Passive Voice          <15% = good | >25% = problematic
Forward/Hedge Ratio    >1.5 = clear signaling | 0.5–1.5 = mixed | <0.5 = overly cautious
Jargon Density         <3 per 100 words = accessible | >6 = specialist only
Lexical Diversity      0.35–0.55 = normal | <0.25 = repetitive
Sentiment              Report only — no threshold for central bank docs
─────────────────────────────────────────────────────────────────────""")

# ── Sidebar options ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Options")
    is_mpr = st.checkbox(
        "Apply MPR filtering",
        value=True,
        help="Skip cover/TOC pages and strip chart artifacts (use for CBA Monetary Policy Reports).",
    )
    check_grammar = st.checkbox(
        "Check grammar (slower)",
        value=False,
        help="Uses LanguageTool via Java — adds ~30–60 seconds. May not work on all machines.",
    )

# ── File upload ─────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded:
    with st.spinner("Extracting text from PDF…"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        try:
            text = extract_text(tmp_path, is_mpr=is_mpr)
        finally:
            os.unlink(tmp_path)

    if not text.strip():
        st.error("No prose text could be extracted from this PDF.")
        st.stop()

    with st.expander("Extracted text preview (first 80 words)"):
        st.write(" ".join(text.split()[:80]) + "…")

    with st.spinner("Computing metrics…"):
        metrics = analyze(text, check_grammar=check_grammar)

    # Save JSON
    json_path = save_json(metrics, uploaded.name)
    st.success(f"Analysis complete! Results saved to `{json_path}`")

    # ── Part 1: Readable.com Metrics ────────────────────────────────────────────
    st.subheader("Part 1 — Readable.com Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Readability Scores**")
        grade_color = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "🔴"}
        g = metrics["overall_grade"]
        st.metric("Overall Grade", f"{grade_color.get(g, '')} {g}")
        st.metric("Flesch-Kincaid Grade Level", metrics["flesch_kincaid_grade"])
        st.metric("Gunning Fog Index", metrics["gunning_fog"])
        st.metric("Flesch Reading Ease", metrics["flesch_reading_ease"])
        st.metric("Reach Score", f"{metrics['reach_pct']}%")

    with col2:
        st.markdown("**Document Counts**")
        st.metric("Word Count", f"{metrics['word_count']:,}")
        st.metric("Sentence Count", f"{metrics['sentence_count']:,}")
        st.metric("Paragraph Count", f"{metrics['paragraph_count']:,}")

    with col3:
        st.markdown("**Complexity Flags**")
        st.metric(
            "Sentences > 30 syllables",
            f"{metrics['long_sentences_count']:,} ({metrics['long_sentences_pct']}%)",
        )
        st.metric(
            "Words > 12 letters",
            f"{metrics['long_words_count']:,} ({metrics['long_words_pct']}%)",
        )
        st.metric(
            "Adverb Count",
            f"{metrics['adverb_count']:,} ({metrics['adverb_pct']}%)",
        )

    col4, col5 = st.columns(2)
    with col4:
        st.metric("Spelling Issues", metrics["spelling_issues"])
    with col5:
        gi = metrics["grammar_issues"]
        if gi == -1:
            st.metric("Grammar Issues", "unavailable")
            st.caption("LanguageTool failed — Java may not be compatible.")
        elif not check_grammar:
            st.metric("Grammar Issues", "not checked")
        else:
            st.metric("Grammar Issues", f"{gi:,}")

    # ── Sentiment ───────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Sentiment Analysis (VADER)")
    sent = metrics["sentiment"]

    def sentiment_color(label):
        return {"Positive": "🟢", "Neutral": "⚪", "Negative": "🔴"}.get(label, "")

    scol1, scol2, scol3, scol4 = st.columns(4)
    for col, key, label in [
        (scol1, "overall", "Overall"),
        (scol2, "beginning", "Beginning (1st third)"),
        (scol3, "middle", "Middle (2nd third)"),
        (scol4, "end", "End (3rd third)"),
    ]:
        lbl = sent[f"{key}_label"]
        compound = sent[f"{key}_compound"]
        with col:
            st.metric(label, f"{sentiment_color(lbl)} {lbl}")
            st.caption(f"Compound: {compound:+.3f}")

    # ── Part 2: CBA-Specific Metrics ────────────────────────────────────────────
    st.divider()
    st.subheader("Part 2 — CBA-Specific Metrics")

    p2col1, p2col2, p2col3 = st.columns(3)

    with p2col1:
        st.markdown("**Forward Guidance vs. Hedge**")
        st.metric("Forward-Looking Words", metrics["forward_word_count"])
        st.metric("Hedge Words", metrics["hedge_word_count"])
        ratio = metrics["forward_hedge_ratio"]
        st.metric("Forward/Hedge Ratio", f"{ratio:.2f}" if ratio is not None else "N/A")

    with p2col2:
        st.markdown("**Passive Voice**")
        st.metric(
            "Passive Sentences",
            f"{metrics['passive_sentence_count']:,} ({metrics['passive_sentence_pct']}%)",
        )
        st.markdown("**Jargon Density**")
        st.metric("Jargon Terms Found", metrics["jargon_count"])
        st.metric("Jargon per 100 Words", metrics["jargon_per_100_words"])

    with p2col3:
        st.markdown("**Lexical Diversity (TTR)**")
        st.metric("Unique Words", f"{metrics['unique_words']:,}")
        st.metric("Type-Token Ratio", f"{metrics['ttr']:.4f} ({metrics['ttr_pct']}%)")

    # ── Section-Level Readability ────────────────────────────────────────────────
    sections = metrics.get("section_readability", [])
    if sections:
        st.divider()
        st.subheader("Section-Level Readability")
        df_sections = pd.DataFrame(sections)
        df_sections.columns = ["Section", "FK Grade", "Flesch Ease"]
        st.dataframe(df_sections, use_container_width=True, hide_index=True)

    # ── Export ──────────────────────────────────────────────────────────────────
    st.divider()
    flat = {k: v for k, v in metrics.items() if k not in ("sentiment", "section_readability")}
    flat.update({f"sentiment_{k}": v for k, v in metrics["sentiment"].items()})
    df_export = pd.DataFrame([flat])
    df_export.insert(0, "document", uploaded.name)
    csv = df_export.to_csv(index=False)
    st.download_button(
        "Download results as CSV",
        data=csv,
        file_name=f"{os.path.splitext(uploaded.name)[0]}_readability.csv",
        mime="text/csv",
    )
