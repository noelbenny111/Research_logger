"""
Local summarization engine using TF-IDF sentence ranking.
No external AI APIs required — runs entirely offline.
"""
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from utils.richtext import content_to_plain_text


# ─── Stop words ───────────────────────────────────────────────────────────────

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "i", "we", "you", "he", "she", "it", "they",
    "this", "that", "these", "those", "my", "our", "your", "his", "her",
    "its", "their", "what", "which", "who", "how", "when", "where", "why",
    "not", "no", "so", "if", "then", "also", "as", "up", "about", "into",
    "through", "during", "including", "until", "while", "although", "after",
    "before", "since", "without", "under", "between", "each", "more",
    "very", "just", "than", "both", "only", "over", "such", "same",
}


# ─── Text utilities ────────────────────────────────────────────────────────────

def _clean_markdown(text: str) -> str:
    """Strip markdown formatting."""
    text = content_to_plain_text(text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)           # bold/italic
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL) # code
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)       # HTML comments
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)         # links
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)     # list items
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)     # ordered lists
    text = re.sub(r"-{3,}", "", text)                             # horizontal rules
    return text.strip()


def _tokenize(text: str) -> List[str]:
    """Simple word tokenizer."""
    return [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text)
            if w.lower() not in STOP_WORDS]


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    text = _clean_markdown(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


# ─── TF-IDF implementation ─────────────────────────────────────────────────────

def _compute_tfidf(sentences: List[str]) -> Dict[str, float]:
    """Compute TF-IDF scores for words across sentences."""
    n = len(sentences)
    if n == 0:
        return {}

    # Term frequency per sentence
    tf_per_sentence = []
    for sent in sentences:
        tokens = _tokenize(sent)
        total = len(tokens) or 1
        tf = Counter(tokens)
        tf_per_sentence.append({w: c / total for w, c in tf.items()})

    # Document frequency
    df = Counter()
    for tf in tf_per_sentence:
        for word in tf:
            df[word] += 1

    # TF-IDF score per word (averaged across sentences)
    tfidf_scores: Dict[str, float] = {}
    for tf in tf_per_sentence:
        for word, freq in tf.items():
            idf = math.log((n + 1) / (df[word] + 1)) + 1
            tfidf_scores[word] = tfidf_scores.get(word, 0) + freq * idf

    return tfidf_scores


def _score_sentences(sentences: List[str], word_scores: Dict[str, float]) -> List[float]:
    """Score each sentence by average word TF-IDF."""
    scores = []
    for sent in sentences:
        tokens = _tokenize(sent)
        if not tokens:
            scores.append(0.0)
            continue
        score = sum(word_scores.get(w, 0) for w in tokens) / len(tokens)
        # Slight bonus for sentences with numbers (often results)
        if re.search(r"\d+", sent):
            score *= 1.15
        scores.append(score)
    return scores


def summarize_text(text: str, num_sentences: int = 5) -> str:
    """Extract the most informative sentences from text."""
    sentences = _split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= num_sentences:
        return " ".join(sentences)

    word_scores = _compute_tfidf(sentences)
    sent_scores = _score_sentences(sentences, word_scores)

    # Rank by score but preserve original order
    indexed = sorted(enumerate(sent_scores), key=lambda x: x[1], reverse=True)
    top_indices = sorted([i for i, _ in indexed[:num_sentences]])
    return " ".join(sentences[i] for i in top_indices)


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extract top keywords from text."""
    clean = _clean_markdown(text)
    tokens = _tokenize(clean)
    if not tokens:
        return []
    freq = Counter(tokens)
    return [word for word, _ in freq.most_common(top_n)]


def extract_section(content: str, section_header: str) -> str:
    """Extract a named section from a markdown entry."""
    pattern = rf"##\s+{re.escape(section_header)}\s*\n(.*?)(?=##|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


# ─── High-level summary builders ──────────────────────────────────────────────

def build_weekly_summary(entries: List[Dict[str, Any]]) -> str:
    """Generate a weekly summary from a list of entry dicts."""
    if not entries:
        return "No entries found for this week."

    lines = []
    lines.append(f"**Entries covered:** {len(entries)} days\n")

    # Collect plan-for-tomorrow from last entry
    last_entry = entries[-1]
    tomorrow_plan = extract_section(last_entry.get("content", ""), "Plan for Tomorrow")
    if tomorrow_plan:
        lines.append("### 📌 Carry-over from Last Entry")
        lines.append(tomorrow_plan)
        lines.append("")

    # Per-day bullets
    lines.append("### 📅 Daily Highlights")
    for entry in entries:
        content = entry.get("content", "")
        date_str = entry.get("entry_date", "")
        worked_on = extract_section(content, "What I Worked On Today")
        summary = summarize_text(worked_on, num_sentences=2) if worked_on else summarize_text(content, num_sentences=2)
        if summary:
            lines.append(f"**{date_str}:** {summary}")
    lines.append("")

    # Keywords across the week
    all_text = " ".join(e.get("content", "") for e in entries)
    keywords = extract_keywords(all_text, top_n=15)
    if keywords:
        lines.append("### 🔑 Key Topics This Week")
        lines.append(", ".join(keywords))
        lines.append("")

    # Problems
    problems = []
    for entry in entries:
        p = extract_section(entry.get("content", ""), "Problems Encountered")
        if p and p not in ("<!-- Note any blockers, bugs, or unexpected issues -->", ""):
            problems.append(f"- {p[:200]}")
    if problems:
        lines.append("### ⚠️ Problems Encountered")
        lines.extend(problems[:5])
        lines.append("")

    # Ideas
    ideas = []
    for entry in entries:
        idea = extract_section(entry.get("content", ""), "Ideas / Observations")
        if idea and "Capture any new ideas" not in idea and idea:
            ideas.append(f"- {idea[:200]}")
    if ideas:
        lines.append("### 💡 Ideas & Observations")
        lines.extend(ideas[:5])
        lines.append("")

    return "\n".join(lines)


def build_monthly_summary(entries: List[Dict[str, Any]], year: int, month: int) -> str:
    """Generate a monthly summary."""
    import calendar
    if not entries:
        return "No entries found for this month."

    month_name = calendar.month_name[month]
    lines = [f"## {month_name} {year} — Research Summary\n"]
    lines.append(f"**Total logged days:** {len(entries)} / {calendar.monthrange(year, month)[1]}\n")

    # Full text for global analysis
    all_text = " ".join(e.get("content", "") for e in entries)

    # Top keywords
    keywords = extract_keywords(all_text, top_n=20)
    if keywords:
        lines.append("### 🔑 Top Research Topics")
        lines.append(", ".join(keywords))
        lines.append("")

    # Overall summary
    summary = summarize_text(all_text, num_sentences=6)
    if summary:
        lines.append("### 📋 Month in Brief")
        lines.append(summary)
        lines.append("")

    # Weekly breakdown
    lines.append("### 📆 Weekly Breakdown")
    weeks: Dict[int, List] = {}
    for entry in entries:
        try:
            d = date.fromisoformat(entry["entry_date"])
            week = d.isocalendar()[1]
            weeks.setdefault(week, []).append(entry)
        except Exception:
            pass

    for week_num in sorted(weeks):
        week_entries = weeks[week_num]
        dates = [e["entry_date"] for e in week_entries]
        week_text = " ".join(e.get("content", "") for e in week_entries)
        week_summary = summarize_text(week_text, num_sentences=2)
        lines.append(f"**Week {week_num}** ({dates[0]} → {dates[-1]}): {week_summary}")
    lines.append("")

    return "\n".join(lines)
