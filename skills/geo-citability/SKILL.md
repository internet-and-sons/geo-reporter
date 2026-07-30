---
name: geo-citability
description: AI citability scoring and optimization. Analyzes web page content to determine how likely AI systems (ChatGPT, Claude, Perplexity, Gemini) are to cite or quote passages from the page. Provides a citability score (0-100) with specific rewrite suggestions.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Write
---

# AI Citability Scoring Skill

## Core Insight

AI language models cite passages that meet specific structural criteria. Research from Princeton, Georgia Tech, and IIT Delhi (2024) found that GEO-optimized content achieves 30-115% higher visibility in AI-generated responses. The key finding: AI systems preferentially extract and cite passages that are **134-167 words long**, **self-contained** (understandable without surrounding context), **fact-rich** (containing specific statistics, dates, or named entities), and **directly answer a question** in the first 1-2 sentences.

This is fundamentally different from traditional SEO copywriting, which optimizes for keyword density and user engagement metrics. GEO citability optimizes for **extractability** -- the ease with which an AI system can pull a passage from your content and present it as a direct answer.

---

## Citability Scoring Rubric (0-100)

### Category 1: Answer Block Quality (30% of total score)

This measures whether content contains clear, quotable answer passages that AI systems can extract verbatim.

**Scoring Criteria:**

| Score | Criteria |
|---|---|
| **90-100** | Every major section opens with a 1-2 sentence direct answer. Uses "X is..." or "X refers to..." patterns. First 40-60 words of each section can stand alone as a complete answer. |
| **70-89** | Most sections have clear answer openings. Some definition patterns present. Answers are identifiable but may need minor context. |
| **50-69** | Some sections have answer-like openings but many bury the answer in the middle or end of paragraphs. Few explicit definition patterns. |
| **30-49** | Answers are generally buried in long paragraphs. No consistent definition patterns. Content is narrative-driven rather than answer-driven. |
| **0-29** | No identifiable answer blocks. Content is entirely narrative, conversational, or fragmented. AI would struggle to extract any quotable passage. |

**What to look for:**

- **Definition patterns:** "X is [definition]." / "X refers to [explanation]." / "X means [meaning]."
- **Answer-first structure:** The answer appears in the first sentence, followed by supporting detail.
- **Quantified answers:** "The average cost of X is $Y" rather than "Many factors affect the cost of X."
- **Comparison answers:** "X differs from Y in three ways: [list]" rather than "X and Y are often confused."

**High-citability example:**
```
Content delivery networks (CDNs) are distributed server systems that cache and serve
web content from locations geographically close to end users. A CDN reduces latency
by 50-70% on average by serving assets from edge servers rather than a single origin
server. The three largest CDN providers as of 2025 are Cloudflare (serving approximately
20% of all websites), Amazon CloudFront, and Akamai Technologies.
```
Word count: 58. Self-contained: Yes. Facts: 3 specific data points. Definition pattern: Yes.

**Low-citability example:**
```
If you've ever wondered why some websites load faster than others, the answer might
surprise you. There's this amazing technology that has been around for a while now.
It's changed the way we think about web performance. Let me explain how it works and
why you should care about it for your business.
```
Word count: 52. Self-contained: No (no topic identified). Facts: 0. Definition pattern: No.

---

### Category 2: Passage Self-Containment (25% of total score)

This measures whether individual passages can be extracted and understood without needing the surrounding content.

**Scoring Criteria:**

| Score | Criteria |
|---|---|
| **90-100** | 80%+ of content blocks are fully self-contained. Each passage names its subject explicitly. No reliance on pronouns referencing earlier content. Contains specific facts within the passage. |
| **70-89** | 60-79% of content blocks are self-contained. Most passages name their subject. Occasional pronoun references that require context. |
| **50-69** | 40-59% of content blocks are self-contained. Mixed use of explicit subjects and pronouns. Some passages require reading prior sections. |
| **30-49** | 20-39% of content blocks are self-contained. Heavy reliance on pronouns and contextual references. Most passages need surrounding text. |
| **0-29** | Under 20% self-contained. Content reads as a continuous narrative where extracting any paragraph loses meaning. |

**Self-containment checklist for each passage:**

1. Does the passage explicitly name the subject (not "it," "this," "they")?
2. Can someone understand the main point reading ONLY this passage?
3. Does the passage contain at least one specific fact, statistic, or named entity?
4. Is the passage between 50-200 words (the optimal extraction length)?
5. Does the passage avoid starting with conjunctions ("But," "However," "And") that imply prior context?

---

### Category 3: Structural Readability (20% of total score)

This measures the structural formatting that helps AI systems parse and segment content.

**Scoring Criteria:**

| Score | Criteria |
|---|---|
| **90-100** | Clean H1 > H2 > H3 hierarchy. Question-based headings for informational content. Short paragraphs (2-4 sentences). Tables for comparisons. Ordered lists for processes. Unordered lists for features/options. |
| **70-89** | Good heading hierarchy with minor skips. Some question-based headings. Mostly short paragraphs. Some use of tables and lists. |
| **50-69** | Heading hierarchy present but inconsistent. Few question-based headings. Mix of short and long paragraphs. Limited tables/lists. |
| **30-49** | Minimal heading structure. No question-based headings. Long paragraphs dominate. Rare use of tables/lists. |
| **0-29** | No heading structure or severely broken hierarchy. Wall-of-text paragraphs. No tables or lists. |

**Structural best practices for AI citability:**

- **Heading hierarchy:** H1 (page title) > H2 (major sections) > H3 (subsections). Never skip levels.
- **Question-based headings:** "What is [topic]?" and "How does [topic] work?" are directly matchable to AI queries.
- **Paragraph length:** 2-4 sentences per paragraph. AI systems parse short paragraphs more reliably.
- **Tables:** Use for any comparison of 3+ items. AI systems extract table data with high accuracy.
- **Lists:** Use ordered lists for sequential processes, unordered lists for non-sequential items.
- **Bold key terms:** Bold the first use of important terms. This aids AI entity recognition.

---

### Category 4: Statistical Density (15% of total score)

This measures the presence of specific, verifiable data points that AI systems prioritize when selecting citation sources.

**Scoring Criteria:**

| Score | Criteria |
|---|---|
| **90-100** | 5+ specific statistics per 500 words. All claims backed by named sources or dates. Uses exact numbers (not "many" or "several"). Includes percentages, dollar amounts, timeframes, and named studies. |
| **70-89** | 3-4 statistics per 500 words. Most claims have sources. Mostly specific numbers with occasional vague quantifiers. |
| **50-69** | 1-2 statistics per 500 words. Some claims sourced. Mix of specific and vague numbers. |
| **30-49** | Less than 1 statistic per 500 words. Few sourced claims. Predominantly vague quantifiers. |
| **0-29** | No statistics. No sourced claims. All quantifiers are vague ("many," "most," "a lot"). |

**What counts as a statistic:**
- Specific percentages: "73% of marketers report..."
- Dollar amounts: "The average cost is $4,500 per month"
- Timeframes: "Implementation takes 6-8 weeks on average"
- Named studies: "According to the 2025 HubSpot State of Marketing Report..."
- Specific counts: "The platform integrates with 340+ tools"
- Comparison data: "40% faster than the industry average"

**What does NOT count:**
- "Many companies use..." (vague)
- "A significant percentage..." (vague)
- "Studies show that..." (no named source)
- "Experts agree..." (no named experts)

---

### Category 5: Uniqueness & Original Data (10% of total score)

This measures whether the content provides information that AI systems cannot find elsewhere, making it a necessary citation source.

**Scoring Criteria:**

| Score | Criteria |
|---|---|
| **90-100** | Contains first-party research, proprietary data, original surveys, or unique datasets. Presents analysis or insights not found on any other page. Clear methodological descriptions. |
| **70-89** | Contains some original insights or unique analysis of existing data. Offers a distinct perspective with original examples. |
| **50-69** | Mostly synthesizes existing information but adds some unique commentary or examples. |
| **30-49** | Largely derivative content that restates common knowledge with minimal original contribution. |
| **0-29** | Entirely derivative. All information is available (often verbatim) on higher-authority sources. |

**Signals of unique content:**
- "Our analysis of [X] data found..."
- "We surveyed [N] [professionals] and found..."
- "Based on our experience with [N] clients..."
- Custom charts, graphs, or data visualizations
- Case studies with specific named outcomes
- Original frameworks, methodologies, or taxonomies

---

## Analysis Procedure

The rubric above is the *reference* — the packaged scorer implements it deterministically. Use the scorer; the manual rubric only exists for understanding what the numbers mean and for writing rewrite recommendations.

### Step 1: Run the packaged scorer

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/citability_scorer.py" <url>
```

This produces a single JSON object that already does Steps 1–4 of the previous procedure: fetches the page, strips nav/footer/sidebar/scripts/forms, segments into blocks at H1–H4 boundaries (with a 20-word minimum per block), and scores every block on the five dimensions.

Fields:

| Field | Meaning |
|---|---|
| `total_blocks_analyzed` | Block count (≥20 words each) |
| `average_citability_score` | Page Citability Score (0–100) |
| `optimal_length_passages` | Blocks in the 134–167 word AI sweet spot |
| `grade_distribution` | `{A, B, C, D, F}` counts |
| `top_5_citable[]` | Strongest blocks — each has `heading`, `content`, `word_count`, `total_score`, `breakdown` (per-dimension), `grade` |
| `bottom_5_citable[]` | Weakest blocks — same shape, these are your rewrite targets |
| `all_blocks[]` | Every scored block |
| `fetch_method` | `"default"` (ordinary browser UA) or `"bot_ua_fallback"` (retried as an AI crawler after a WAF challenge) |
| `challenge_detected` | `true` when the first request hit a WAF/JS challenge |

**Disclose the fetch method.** The scorer returns `fetch_method` and `challenge_detected`. When `fetch_method == "bot_ua_fallback"`, the site's WAF challenged an ordinary browser request and scores were computed from the content an **AI crawler** receives. State this in the report methodology — for a GEO audit that is arguably the more relevant view, but the reader must know which view was measured.

Read `top_5_citable` into the "Strongest Content Blocks" output section and `bottom_5_citable` into "Weakest Content Blocks (Rewrite Priority)". `average_citability_score` becomes the Page Citability Score in the summary.

### Step 2: Generate rewrite suggestions for weakest blocks

For each entry in `bottom_5_citable` (or any block with `total_score < 60`), look at its `breakdown` to identify the primary weakness:

| Weakest dimension | Rewrite recommendation pattern |
|---|---|
| `answer_block_quality` (low) | Propose rewriting the opening sentence as a definition or direct answer ("X is …", "X refers to …", "X means …"). |
| `self_containment` (low) | Suggest defining acronyms / pronouns / forward references on first use; recommend a 1-sentence summary at the top of the block. |
| `structural_readability` (low) | Recommend converting prose to a list, table, or numbered steps; suggest bolding key terms. |
| `statistical_density` (low) | Suggest adding specific numbers, percentages, dates, dollar amounts, or named entities. |
| `uniqueness` (low) | Suggest adding original data (survey results, internal metrics, case-study numbers) or a perspective not found in obvious competing sources. |

Each rewrite suggestion should reference the block's heading and quote the first ~30 words so the reader knows exactly which passage you're talking about.

---

## Output Format

Generate a file called `GEO-CITABILITY-SCORE.md`:

```markdown
# AI Citability Analysis: [Page Title]

**URL:** [URL]
**Analysis Date:** [Date]
**Overall Citability Score: [X]/100**
**Citability Coverage:** [X]% of content blocks score above 70
**Measured on:** [Standard browser request | Content served to an AI crawler — the site's WAF challenged our normal request (`fetch_method: bot_ua_fallback`)]

---

## Score Summary

| Category | Score | Weight | Weighted |
|---|---|---|---|
| Answer Block Quality | [X]/100 | 30% | [X] |
| Passage Self-Containment | [X]/100 | 25% | [X] |
| Structural Readability | [X]/100 | 20% | [X] |
| Statistical Density | [X]/100 | 15% | [X] |
| Uniqueness & Original Data | [X]/100 | 10% | [X] |
| **Overall** | | | **[X]/100** |

---

## Strongest Content Blocks

### 1. "[Heading]" -- Score: [X]/100
> [First 2 sentences of the block]

**Why it works:** [Explanation]

### 2. "[Heading]" -- Score: [X]/100
> [First 2 sentences of the block]

**Why it works:** [Explanation]

---

## Weakest Content Blocks (Rewrite Priority)

### 1. "[Heading]" -- Score: [X]/100

**Current opening:**
> [First 2 sentences as they exist]

**Problem:** [Specific issue -- buried answer, no facts, etc.]

**Suggested rewrite:**
> [Rewritten opening 2-3 sentences with answer-first pattern and facts]

**Additional improvements:**
- [Add table comparing X, Y, Z]
- [Include statistic about ...]
- [Split long paragraph into 2-3 shorter ones]

---

## Quick Win Reformatting Recommendations

1. **[Specific recommendation]** -- Expected citability lift: +[X] points
2. **[Specific recommendation]** -- Expected citability lift: +[X] points
3. **[Specific recommendation]** -- Expected citability lift: +[X] points
4. **[Specific recommendation]** -- Expected citability lift: +[X] points
5. **[Specific recommendation]** -- Expected citability lift: +[X] points

---

## Per-Section Scores

| Section Heading | Words | Answer Quality | Self-Contained | Structure | Stats | Unique | Overall |
|---|---|---|---|---|---|---|---|
| [H2 heading] | [N] | [X] | [X] | [X] | [X] | [X] | [X] |
```

---

## Reference Data

### Optimal Passage Characteristics (from GEO Research)

- **Optimal length for AI citation:** 134-167 words (Bortolato 2025 analysis of AI Overview passages)
- **Definition patterns increase citation rate by:** 2.1x (Georgia Tech 2024)
- **Adding statistics to passages increases citation by:** 40% (Princeton GEO study 2024)
- **Adding quotations from authorities increases citation by:** 115% in certain categories (IIT Delhi 2024)
- **Fluency optimization increases visibility by:** 30% on average across all query types
- **Content with source citations is cited:** 20-25% more often by Perplexity and ChatGPT search

### AI System Citation Preferences

| AI System | Citation Preference |
|---|---|
| **ChatGPT (Search)** | Prefers passages with explicit definitions, named sources, and recent dates. Tends to cite 2-4 sources per response. |
| **Perplexity** | Heavily favors fact-dense passages with statistics. Cites 4-8 sources per response. Values recency highly. |
| **Claude** | Prefers well-structured, comprehensive passages. Values nuance and accuracy over brevity. |
| **Gemini (AI Overviews)** | Prefers concise answer blocks (40-60 words). Values content already ranking in top 10 organic results. |
| **Copilot (Bing)** | Similar to Gemini. Prefers passages from high-authority domains with clear factual claims. |
