# india-laws: Design Document
**Date:** 2026-04-12  
**Status:** Approved

---

## What We're Building

A public GitHub repository of Indian Central Acts in version-controlled Markdown, plus an LLM-readable wiki layer and an MCP server that connects Claude (or any MCP client) to the corpus.

Two deliverables:
1. **Data repo** (`india-laws`) — public, forkable, like legalize-es for Spain
2. **MCP server** (`india-laws/mcp/`) — agent interface with search, read, write tools

---

## Inspiration

- **legalize-es** — Spanish laws as Git-tracked Markdown. Each act = file. Each amendment = commit. Source: Spain's BOE API.
- **llmwiki** (lucasastorian) — LLM-maintained wiki layer. Three layers: raw sources → wiki pages → MCP tools. LLM reads and writes via MCP, not direct file access.

---

## Scope

**Phase 1:** Central Acts only (~900 acts from indiacode.nic.in). No state laws.

Rationale: single authoritative source, structured HTML, covers 80%+ of high-value legal queries (criminal, corporate, tax, family, constitutional). State laws added later per-jurisdiction as scrapers mature.

---

## Architecture

### Three Layers

```
Layer 1: acts/          — raw scraped acts (immutable)
Layer 2: wiki/          — LLM-generated synthesis (evolving)
Layer 3: mcp/server.py  — agent interface (search, read, write)
```

### Repository Structure

```
india-laws/
  acts/                          # Layer 1: raw acts
    constitution/
    criminal/
    civil/
    commercial/
    labour/
    tax/
    ...

  wiki/                          # Layer 2: synthesis
    INDEX.md                     # LLM entry point — all topics, categorized
    topics/                      # money layer: self-contained topic pages
    acts/                        # per-act summaries (secondary)
    transitions/                 # IPC→BNS, CrPC→BNSS, Evidence→BSA mappings

  data/
    mha-transition-ipc-bns.yaml  # official MHA comparative tables (ground truth)
    mha-transition-crpc-bnss.yaml

  scripts/
    scraper.py                   # scrapes indiacode.nic.in → acts/
    parse-transitions.py         # MHA PDFs → data/*.yaml
    wiki-gen.py                  # LLM generates/updates wiki pages (batch)

  mcp/
    server.py                    # MCP tools: search, read, write
    README.md

  schema.md                      # rules governing wiki page structure
  CONTRIBUTING.md
```

---

## Layer 1: Raw Acts

**Source:** indiacode.nic.in (structured HTML, ~900 Central Acts)  
**Update trigger:** e-gazette.gov.in (new acts + amendments)  
**Automation:** GitHub Actions daily scraper

### Act File Format

```markdown
---
title: "The Bharatiya Nyaya Sanhita, 2023"
short: BNS
year: 2023
ministry: Ministry of Home Affairs
status: in-force
supersedes: ipc-1860
last-amended: 2023-12-25
source: https://indiacode.nic.in/handle/123456789/...
---

# The Bharatiya Nyaya Sanhita, 2023
[full text]
```

### Git Convention

Each amendment = one commit. Commit message format:
```
[BNS] Amendment: Section 12 substituted — Gazette No. GSR 123(E) 2024-03-01
```

---

## Layer 2: Wiki

### Agent Query Flow

```
user query
  → LLM reads wiki/INDEX.md
  → finds relevant topic
  → reads wiki/topics/X.md
  → answers (self-contained, no further lookups needed)
```

### INDEX.md Structure

Flat categorized list. Every topic listed with one-line description. LLM navigates without reading all files.

```markdown
## Criminal Law
- [theft](topics/theft.md) — dishonest taking of property (BNS §303-308)
- [murder](topics/murder.md) — culpable homicide, punishment, exceptions (BNS §101-104)
- [cybercrime](topics/cybercrime.md) — IT Act offences, BNS digital provisions

## Transitions
- [IPC → BNS](transitions/ipc-to-bns.md) — section mapping, 2023 reform
- [CrPC → BNSS](transitions/crpc-to-bnss.md) — procedure reform, 2023
```

### Topic Page Format

```markdown
---
topic: theft
acts: [bns-2023]
supersedes-topic-from: [ipc-1860]
updated: 2026-01-01
---

## Definition
[plain English, 2-3 sentences]

## Current Law (as of 2024)
[BNS provisions — what actually applies today, specific sections]

## Key Provisions
[elements of the offence, punishment, exceptions]

## Transition Note
IPC §378-382 → BNS §303-308. Key change: [what changed].

## Related Topics
- robbery, extortion, cheating
```

**Rule:** topic pages must be self-contained. No "see IPC §420" without explaining what it says.

### Transition Layer

**Why separate:** single-point-of-failure risk mitigated by redundancy — each topic page carries its own inline transition note. The `transitions/` files are convenience aggregates, not load-bearing.

**Source:** official MHA/Law Ministry comparative tables published when BNS/BNSS/BSA passed. Ground truth, not LLM-generated.

```
data/mha-transition-ipc-bns.yaml  →  scripts/parse-transitions.py
  → embeds inline notes into topic pages (via wiki-gen.py)
  → generates transitions/ipc-to-bns.md (aggregate)
```

---

## Layer 3: MCP Server

**Pattern:** llmwiki's MCP approach, adapted for flat files (no Postgres needed at this scale).

### Tools

| Tool | Input | Output |
|------|-------|--------|
| `search` | query string | ranked list of matching topic/act pages |
| `read` | file path | full page content |
| `write` | path + content | creates or updates a wiki page |

The `write` tool is critical — it allows Claude to improve the wiki mid-conversation, not just batch-generate. Community members or a cron job run Claude with write access; wiki self-improves over time.

### Search Implementation

Full-text search over `wiki/` markdown files. ripgrep-style at small scale. PGroonga (as used in llmwiki) is overkill for a flat-file corpus.

---

## What We're NOT Building (yet)

- State laws (28 states + 8 UTs) — future, per-jurisdiction scrapers
- Web frontend — out of scope, public repo is the deliverable
- Auth layer — public corpus, no users
- Case law — Indian Kanoon integration is future scope
- Regulatory/subordinate legislation — rules, notifications, circulars

---

## Key Risks

| Risk | Mitigation |
|------|-----------|
| indiacode.nic.in blocks scraper | Rate limiting + respectful crawl delay; fallback to e-gazette PDFs |
| LLM hallucinations in wiki | Topic pages cite source sections; community review via PRs |
| Transition mappings wrong | Source from official MHA tables, not LLM-generated |
| Wiki goes stale | MCP `write` tool enables ongoing LLM maintenance; GitHub Actions triggers re-gen on new acts |
| PDF-only acts | pdf2md pipeline in scraper; flag for manual review |

---

## Comparison: llmwiki vs Our Design

| Dimension | llmwiki | india-laws |
|---|---|---|
| Storage | Postgres | flat files in Git |
| Search | PGroonga | full-text over .md |
| Agent access | MCP tools | MCP tools |
| Wiki maintenance | LLM write tool (live) | wiki-gen.py (batch) + MCP write |
| Raw sources | immutable | immutable |
| Three layers | raw → wiki → tools | raw → wiki → MCP |
| Schema doc | yes | schema.md |
| Auth | yes (multi-user) | no (public corpus) |

Divergences are intentional: flat files keep the repo forkable and dependency-free. Postgres would make it a hosted service, not a public dataset.
