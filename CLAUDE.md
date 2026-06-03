# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`lex-india` — Indian law as structured markdown for LLM agents. 87 topic pages across 15 categories. Daily scraper + Claude-powered wiki generator + MCP server.

## Commands

```bash
pip install -r requirements.txt          # install deps (Python 3.11)

# Tests
pytest                                    # run all
pytest tests/test_mcp_server.py           # single file
pytest tests/test_mcp_server.py::test_x   # single test

# Pipelines (manual; normally run via GitHub Actions)
python scripts/scraper.py                 # scrape India Code → acts/
python scripts/wiki_gen.py                # regenerate wiki/topics/ via Claude API (needs ANTHROPIC_API_KEY)
python scripts/parse_transitions.py       # IPC→BNS / CrPC→BNSS / Evidence→BSA mappings

# MCP server
python india_mcp/server.py                # stdio MCP server (FastMCP)
```

## Architecture

Three-layer pipeline. Each layer has its own output directory; layers run independently and commit.

```
indiacode.nic.in
      │  scripts/scraper.py  (httpx + BeautifulSoup, 2s rate limit, slugify)
      ▼
acts/<slug-year>.md           ← raw scraped act text (read-only by hand; scraper-owned)
      │  scripts/wiki_gen.py  (anthropic SDK, SEED_TOPICS list)
      ▼
wiki/topics/*.md              ← LLM-generated topic pages (schema.md frontmatter)
wiki/INDEX.md                 ← curated index (every topic MUST have entry)
wiki/transitions/             ← 2023 reform mappings
      │  india_mcp/server.py  (FastMCP: search, read, write tools)
      ▼
LLM agents
```

### Key invariants

- **Page schema** is enforced by `schema.md` — frontmatter `topic/acts/status/department/enactment_date/updated`, then sections `Definition → Current Law → Key Provisions → Related Topics`. `wiki_gen.py` and any new generator must produce this exact shape.
- **Path security in MCP** (`india_mcp/server.py`): `read`/`write` resolve against `CORPUS_ROOT` and reject traversal; `write` is restricted to `wiki/` only. Preserve these guards.
- **Search ranking** is naive word-overlap with first-hit snippet (top 10). Don't add fuzzy/semantic search without keeping the simple path — agents depend on deterministic results.
- **`acts/` is generated.** Never hand-edit. Scraper owns it. File issues for scraper bugs (per CONTRIBUTING.md).
- **`SEED_TOPICS`** in `scripts/wiki_gen.py` is the canonical topic list. Adding a topic = append tuple `(slug, [act-slugs], category)` AND ensure `INDEX.md` entry.
- **Slug convention** (`scripts/scraper.py:slugify`): known-abbreviation map first (e.g. `bns-2023`), else fallback. Reuse the map; don't invent new slugs.

### CI

- `.github/workflows/scrape.yml` — daily 2am UTC → commits `acts/`
- `.github/workflows/wiki-update.yml` — triggers on scrape success → runs `wiki_gen.py` → commits `wiki/`

Both push as `lex-india-bot`. Generator needs `ANTHROPIC_API_KEY` repo secret.

## Conventions

- Commit format: `wiki: add topic/<slug>` / `wiki: fix topic/<slug> - <reason>` / `chore: scraper update <date>` (see CONTRIBUTING.md).
- Plans/design docs live in `docs/plans/` (dated). Read latest before changing pipeline shape.
- Disclaimer: informational, not legal advice. Don't add advisory tone to topic pages.
