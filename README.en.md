# StyleDNA

[中文](README.md) | English

> Identifier: `style-dna-skill` / `StyleDNA`  
> Core Philosophy: Deconstruct writing DNA and turn intuitive voice into reusable assets.

`StyleDNA` is an agent skill and engineering toolchain for distilling an author's writing style, cognitive frameworks, and visual presentation from historical articles. Rather than relying on simple "imitate this voice" prompts, `StyleDNA` decomposes complete articles into an auditable and reusable rule set across six distinct layers (surface language, structure patterns, topic logic, source strategies, cognitive frames, and visual styling). It then guides high-fidelity drafting through dynamic context retrieval and layered constraint assembly.

---

## Core Problem It Solves

Standard AI writing often relies on a few few-shot examples, prompting the LLM to improvise. This tends to capture only superficial tone, resulting in repetitive structures and generic "AI cliches".

`StyleDNA` replaces guesswork with systematic distillation:
- **Surface Language**: Word frequencies, sentence-length distribution, punctuation habits, and cadence.
- **Article Structure**: Hook patterns, body architecture, transition mechanics, and conclusion strategies.
- **Topic Logic**: Editorial timing, analytical angles, and excluded themes.
- **Source Strategy**: Primary vs. secondary evidence, data handling, and screenshot evidentiary roles.
- **Cognitive Frames**: Worldviews, core assumptions, and recurring non-obvious propositions.
- **Visual Presentation**: Image density, image-to-text intervals, heading hierarchies, bolding density, and layout rhythm.

---

## Six Distillation Layers

| Layer | Target | Extraction Method | Primary Output |
| - | - | - | - |
| **L1 Surface Language** | Vocabulary, sentence length, punctuation, rhetoric | Script analysis | `language-dna.md` |
| **L2 Article Structure** | Hook, body architecture, transitions, endings | Structural annotation | `structure-patterns.md` |
| **L3 Topic Logic** | Publication timing, entry angle, topic priorities | Synthesis & categorization | `cognitive-framework.md` |
| **L4 Source Strategy** | Authorities, citations, data, screenshot evidence | Reading synthesis | `cognitive-framework.md` |
| **L5 Cognitive Frames** | Worldview, value judgments, core assumptions | Deep reading synthesis | `cognitive-framework.md` |
| **L6 Visual Style** | Images, paragraph gaps, heading hierarchy, bolding | Multi-modal & layout analysis | `visual-style-guide.md` |

- **L1-L2** define *how it is written*
- **L3-L5** define *how it is reasoned*
- **L6** defines *how it is presented*

---

## Automation Toolchain

The `scripts/` directory provides built-in automation scripts for statistical extraction, retrieval, and evaluation:

1. **Corpus Statistical Analysis (L1)**:
   ```bash
   python3 scripts/analyze_corpus.py <corpus_dir_or_file> -o language-dna.md
   ```
   Computes word frequencies, average sentence length, short/long sentence ratios, punctuation counts, and bold density.

2. **Visual & Layout Analysis (L6)**:
   ```bash
   python3 scripts/analyze_visual.py <corpus_dir> -o visual-style-guide.md
   ```
   Measures image-to-text ratios, image interval paragraphs, and Markdown heading hierarchies.

3. **Context Retriever**:
   ```bash
   python3 scripts/retrieve_context.py <author_dir> -q "Topic & key thesis" -t "Article Type"
   ```
   Applies BM25 and metadata tags to automatically retrieve the Top-5 most relevant source articles.

4. **Style Consistency & AI-Tone Evaluator**:
   ```bash
   python3 scripts/eval_style.py <generated_article.md> -d <language-dna.md>
   ```
   Scores consistency against baseline metrics and identifies repetitive AI cliches.

---

## Complete Workflow

### Stage 1: Corpus Distillation
1. **Collect Articles**: Place at least 20 complete articles (`.md` or `.txt`) into `raw/`.
2. **Tag Metadata**: Create metadata in `_meta/` (title, date, article_type, topic_tags, hook_type).
3. **Extract Features**: Run `analyze_corpus.py` and `analyze_visual.py` to produce statistical foundations.
4. **Synthesize Patterns**: Extract `structure-patterns.md` and `cognitive-framework.md` through deep reading.
5. **Consolidate Writing-DNA**: Merge findings into the unified `Writing-DNA.md`.

> For large corpora (20+ long articles), refer to `references/batch_distillation.md` for batching and incremental updates.

### Stage 2: Drafting with Calibrated Context
1. **Read Distilled Artifacts**: Review all layered files and `Writing-DNA.md`.
2. **Retrieve 5 Reference Articles**: Run `retrieve_context.py` to recall the 5 closest source articles for voice calibration.
3. **Assemble Prompt**: Follow `references/prompt_assembly.md` to combine instructions and constraints.
4. **Priority Rules**:
   - User Instructions > Matching L2 Structure > L1/L6 Style & Layout > L3-L5 Cognitive Frames.
   - Replicate the author's writing mechanics, not their specific factual claims.

### Stage 3: Polish & Evaluation
1. Clean AI tells using the built-in `skills/lieflat-less-ai-tone/` whitelist rules.
2. **Conflict Precedence**: **Where distilled artifacts conflict with generic AI-tone rules, the distilled artifacts win.**
3. Run `scripts/eval_style.py` for automated score verification.

---

## Repository Structure

```text
StyleDNA/
├── SKILL.md                    # Main skill definition & prompt
├── README.md                   # Chinese documentation
├── README.en.md                # English documentation
├── LICENSE                     # MIT License
├── scripts/
│   ├── analyze_corpus.py       # L1 surface language statistical tool
│   ├── analyze_visual.py       # L6 visual & layout analysis tool
│   ├── retrieve_context.py     # Similar context retriever (BM25)
│   ├── eval_style.py           # Style evaluator and AI-tone checker
│   └── requirements.txt        # Dependencies list
├── agents/
│   └── openai.yaml             # Agent configuration
├── references/
│   ├── workflow.en.md          # Detailed English workflow
│   ├── batch_distillation.md   # Batch distillation guide for large corpora
│   └── prompt_assembly.md      # Context assembly guide
├── docs/
│   ├── release-checklist.md    # Pre-release checklist
│   └── usage-boundaries.md     # Usage boundaries
├── templates/
│   └── author-corpus/
│       ├── zh/                 # Chinese templates
│       └── en/                 # English templates
├── skills/
│   └── lieflat-less-ai-tone/   # AI-tone cleanup rules
└── examples/
    └── format-only/            # Demonstration format
```

---

## Usage Boundaries

This project is intended for research, style analysis, and personal writing asset building. Do not use it to impersonate authors, mislead readers, or violate copyright.

---

## Maintainer

Maintained and re-engineered by **OrcGo**.

## License

MIT License
