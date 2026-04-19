# lex-india — Strategic Direction & Phase 1 Design

**Date:** 2026-04-19
**Status:** Approved (tech sections); legal-scope decisions marked TBD-lawyer
**Author:** Manas Taneja (with Claude Code)

---

## 1. Positioning

**lex-india is the canonical LLM-wiki for Indian law.**

Not RAG. Not another Indian Kanoon scraper. A curated, cross-linked, markdown-native knowledge base shaped for LLM agents to navigate via *index-then-fetch* (Karpathy's [LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)). Authoritative source citations, machine-friendly schema, MCP-packaged.

**Pitch sentence:**
> "Indian law as a navigable wiki for AI agents — bare acts, topic explainers, and cross-references in markdown, served via MCP."

**Core differentiator vs RAG:** knowledge **compounds in the repo**. Every cross-reference is pre-built, every summary is pre-written, every amendment is a diff in git. Agents don't re-discover knowledge per query — they navigate a structure that already encodes synthesis.

### 1.5 Distribution & Contribution Model

Open source, but with an unconventional contributor profile (LLM agents acting on behalf of users).

**Two layers:**

1. **Canonical trunk** (this repo) — single source of truth. PR-driven. MIT license. No server, no API keys, no hosting. Just git + markdown + a Python MCP server.
2. **User clones** — anyone clones, runs `india_mcp/server.py` locally with their own LLM (Claude / Cursor / etc.). Their key, their machine, their privacy. Works offline.

**The contribution loop (the novel bit):**

```
User asks agent "what's § 103 BNS?"
  → agent reads acts/bns/sections/103.md
  → notices summary is thin / missing recent amendment
  → agent edits file locally (improves wiki for itself)
  → user reviews diff
  → user runs `git push` → opens PR
  → maintainer reviews → merges
  → next puller benefits
```

This is the Wikipedia + Linux model with one wrinkle: **the editor is often an LLM agent operating on behalf of the user during normal use**.

**Precedents:** `awesome-*` lists, `tldr-pages`, `nixpkgs`, `DefinitelyTyped` — all PR-driven, no central infra, community-curated.

**Mechanisms to make agent-contribution work:**
- `CONTRIBUTING.md` with explicit "agents may PR" section + diff conventions
- Schema validation in CI (pydantic) — gates ~80% of low-quality PRs automatically
- `.github/PULL_REQUEST_TEMPLATE.md` with citation/source/index checkboxes
- MCP tool `propose_edit(path, diff, rationale)` — agents file structured proposals to `.proposals/{uuid}.md` instead of writing silently; user reviews before commit
- `log.md` (Karpathy convention) — append-only curation history, audit trail for accepted PRs

**Non-goals for this model:**
- No SaaS / hosted MCP — zero server cost, zero auth surface, zero abuse vector
- No closed garden — anyone forks, anyone PRs
- No paid tier — your LLM key, your laptop

**Adoption flywheel:** devs install MCP for free → improvements they/their agents make flow back → trunk gets better → more devs install. Classic OSS flywheel, with AI accelerating contribution rate.

**Risk:** AI-generated PR spam. Mitigations: schema CI, maintainer-only merge initially, `log.md` provenance, eventual trusted-contributor tier.

---

## 2. Roadmap (4 phases)

### Phase 1 — Depth (current scope)
Scrape + clean 5 foundational acts:
- Bharatiya Nyaya Sanhita (BNS) 2023
- Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023
- Bharatiya Sakshya Adhiniyam (BSA) 2023
- Indian Contract Act 1872
- Insolvency and Bankruptcy Code (IBC) 2016

> *TBD-lawyer:* confirm these 5 are the right "foundational set" for adoption demo. Alternates considered: GST Act, Companies Act 2013, IT Act 2000.

Schema: `acts/{slug}/sections/{N}.md` + `acts/{slug}/INDEX.md`.
Topic pages get `## Source Sections` block linking to act files.
Schema validator in CI.

**Ship deliverable:** "full text of 5 foundational acts, navigable via MCP."

### Phase 2 — Cross-linking
- Per-category indexes (`wiki/topics/_criminal.md` etc.)
- IPC↔BNS + CrPC↔BNSS transition tables as first-class pages (extends `wiki/transitions/`)
- Concept pages (mens rea, natural justice, locus standi, jurisdiction)
- `See also` + `Referenced by` blocks auto-generated from links
- `log.md` convention live

### Phase 3 — Agent ergonomics (MCP)
- New tools: `get_index(scope)`, `get_section(act, n)`, `related(path)`, `recent_changes(days)`, `propose_edit(...)`
- Structured (typed) returns instead of raw text
- Search improvements: title/heading boost, section-number aware (`"§103 BNS"` → direct hit)

### Phase 4 — Self-maintenance loop
- Daily scraper detects Gazette amendments → opens draft PR with diff + `log.md` entry
- Dead-link + citation-drift checker
- Trusted-contributor bot tier (auto-merge for high-confidence updates)

**Sequence rationale:** each phase unlocks the next. Depth gives cross-linking something to link. Cross-linking makes ergonomic tools worth building. Ergonomic tools make self-maintenance PRs reviewable.

### Out of scope (explicitly)
- ❌ Embeddings / vector DB — violates LLM-wiki philosophy
- ❌ Hosted service / SaaS
- ❌ Case law scraping (Indian Kanoon) — deferred to optional future phase
- ❌ State-specific law — central only for v1
- ❌ Multi-language — English only for v1

---

## 3. Phase 1 Architecture

### 3.1 File layout

```
acts/
  bns/
    INDEX.md              # all sections, 1-line summary, chapter grouping
    meta.yaml             # act_no, year, ministry, source_url, last_synced, sha
    sections/
      001.md
      002.md
      ...
      358.md
    chapters/
      06.md               # optional chapter intros
    schedules/
      first.md            # for acts with schedules
  bnss/...
  bsa/...
  contract-act/...
  ibc/...
```

### 3.2 Section file schema

`acts/bns/sections/103.md`:

```markdown
---
act: bns
section: "103"           # string — handles "498A", "377A"
chapter: 6
heading: Punishment for murder
status: in_force         # in_force | repealed | needs_manual_review
amended_by: []
source_url: https://indiacode.nic.in/...
source_hash: sha256:abc123
synced: 2026-04-19
---

# § 103 — Punishment for murder

## Text
> (1) Whoever commits murder shall be punished with death...
> (2) When a group of five or more persons...

## Cross-references
- Replaces: [IPC § 302](../../ipc/sections/302.md)
- Procedure: [BNSS § ...](../../bnss/sections/...md)
- Topic: [murder](../../../wiki/topics/murder.md)

## Notes
Brief AI-curated context: when does this apply, common defences, etc.
(Optional, marked clearly as commentary not law.)
```

**Design rationale:**
- Frontmatter = machine-queryable
- Numeric/string section ID as filename = stable, sortable, addressable
- `source_hash` = lets daily scraper detect upstream changes without re-diffing whole text
- Cross-refs as relative links = grep-able, wiki-navigable, agent-friendly
- `## Notes` opt-in = lets contributors add commentary without polluting the law

### 3.3 INDEX.md per act

The agent's entry point. ~one line per section. Agent reads INDEX → fetches only the 2-3 sections it needs. Token-efficient (Karpathy core principle).

### 3.4 Frontmatter format

**YAML** — consistent with existing `wiki/topics/` files; mature Python tooling (`ruamel.yaml` for round-trip with comments).

---

## 4. Sourcing Pipeline

### 4.1 Strategy: hybrid

- **Primary:** indiacode.nic.in (official Govt of India repository, public domain, authoritative)
- **Fallback:** manual paste / human-cleaned text when parser chokes (tables, schedules, weird formatting)

### 4.2 Flow

```
scripts/scrape_act.py <act-slug>
  ├─ fetch indiacode.nic.in page for act
  ├─ download official PDF (canonical) + HTML (parseable)
  ├─ parse:
  │    HTML path → selectolax → split by §
  │    PDF path  → pdfplumber → split by § regex
  ├─ for each section:
  │    write acts/{slug}/sections/{N}.md (frontmatter + ## Text)
  │    compute source_hash
  ├─ generate acts/{slug}/INDEX.md from sections
  ├─ write acts/{slug}/meta.yaml
  └─ exit 0 / report parse failures by §
```

### 4.3 Manual-fallback pattern

When parser fails on a section:
- Writes file with `status: needs_manual_review` + `parse_error: "..."`
- Raw extracted text in `## Text (raw)` block
- CI fails until human/agent fixes
- Once fixed, contributor flips frontmatter to `status: in_force`

### 4.4 Dependency choices

| Need | Pick | Why |
|---|---|---|
| HTTP | `httpx` | modern, async-ready |
| HTML parse | `selectolax` | 10× faster than bs4; pure HTML works for indiacode |
| PDF parse | `pdfplumber` | best for structured legal PDFs (tables, columns) |
| YAML | `ruamel.yaml` | round-trips comments + ordering |
| CLI | `typer` | clean subcommands |
| Schema validation | `pydantic v2` | one model = frontmatter validator + MCP return types |

### 4.5 Idempotency contract

- Re-running `scrape_act.py bns` on unchanged source = zero diff (deterministic ordering, stable hash, no timestamp churn in section files — only `meta.yaml` updates)
- Source change → only affected section files churn → small, reviewable PRs

### 4.6 CI gates

- `validate.yml` — runs on every PR: pydantic schema check on all `acts/**/*.md` + `wiki/**/*.md`, dead-link check, section-number continuity check (no gaps in `sections/`)
- `scrape.yml` — daily cron: re-runs scraper for each act, **opens auto-PR** if diff detected, label `auto-scrape`, assigns to maintainer (Renovate/Dependabot pattern). Extends existing daily wiki scrape workflow.

---

## 5. Cross-linking & MCP Surface

### 5.1 Topic ↔ Acts

Add `## Source Sections` block to existing `wiki/topics/*.md`:

```markdown
## Source Sections
- [BNS § 103 — punishment for murder](../../acts/bns/sections/103.md)
- [BNS § 101 — culpable homicide](../../acts/bns/sections/101.md)
- [BNSS § 187 — police custody](../../acts/bnss/sections/187.md)
```

Reverse: each act section's `## Cross-references` lists topic pages that cite it.
Auto-generated by `scripts/build_backlinks.py` (runs in CI, fails on drift).

### 5.2 log.md (root)

Karpathy convention. Append-only curation log. Both humans + agents write here. Provenance trail.

```markdown
# Curation log

## 2026-04-19
- Phase 1 launched: BNS, BNSS, BSA, Contract Act, IBC scraped from indiacode
- 1,247 sections imported, 23 flagged needs_manual_review
- Topic pages cross-linked to source sections (auto)
```

### 5.3 MCP tools (Phase 1 minimum)

| Tool | Signature | Purpose |
|---|---|---|
| `search` | `(query: str) → list[Hit]` | existing, keep |
| `read` | `(path: str) → str` | existing, keep |
| `get_section` | `(act: str, n: str) → Section` | typed return: text, status, cross-refs, source_url |
| `get_index` | `(scope: str) → str` | scope = `wiki`, `acts/bns`, `topics/criminal` |
| `propose_edit` | `(path, diff, rationale) → str` | writes structured proposal to `.proposals/{uuid}.md` for user review |

`write_page` (current) → deprecated in favour of `propose_edit`. Reduces agent-noise PRs.

### 5.4 Pydantic models — single source of truth

```python
class SectionFrontmatter(BaseModel):
    act: str
    section: str
    chapter: int | None
    heading: str
    status: Literal["in_force", "repealed", "needs_manual_review"]
    amended_by: list[str] = []
    source_url: HttpUrl
    source_hash: str
    synced: date
```

One model = scraper output + MCP return type + CI validator.

### 5.5 Repo shape after Phase 1

```
acts/                    # NEW: full text
  {bns,bnss,bsa,contract-act,ibc}/
docs/
  plans/                 # NEW: design docs (this one + future)
india_mcp/
  server.py              # extended with new tools
  models.py              # NEW: pydantic schemas
scripts/
  scrape_act.py          # NEW
  build_backlinks.py     # NEW
  validate.py            # NEW
  scraper.py             # existing wiki scraper, keep
tests/
  test_schema.py         # NEW
  test_scrape_bns.py     # NEW: regression on parsing
  fixtures/              # NEW: tiny act snippets
wiki/
  topics/*.md            # touched: + ## Source Sections block
  INDEX.md               # touched: + acts/ section
log.md                   # NEW: Karpathy curation log
```

---

## TBD-lawyer (legal-scope items deferred for expert input)

- Confirm 5 foundational acts for Phase 1 (BNS / BNSS / BSA / Contract / IBC) — vs alternates (GST, Companies, IT Act)
- Confirm IPC↔BNS section mapping table is the right Phase-2 priority vs. CrPC↔BNSS
- Concept-page inventory for Phase 2 (which doctrines deserve standalone pages)
- Citation format convention (AIR / SCC / neutral citations) for future case-law layer
- Disclaimer text on every page ("not legal advice") — wording

---

## Approval status

| Section | Status |
|---|---|
| 1. Positioning | ✅ approved |
| 1.5 Distribution & contribution model | ✅ approved |
| 2. Roadmap | ✅ approved |
| 3. Phase 1 architecture | ✅ approved |
| 4. Sourcing pipeline | ✅ approved |
| 5. Cross-linking & MCP surface | ✅ approved |

Next: implementation plan via `superpowers:writing-plans`.
