# lex-india

[![Topics](https://img.shields.io/badge/topics-87-blue)](wiki/topics/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Daily Update](https://img.shields.io/github/actions/workflow/status/Manas-Taneja/lex-india/scrape.yml?label=daily%20update)](https://github.com/Manas-Taneja/lex-india/actions)
[![MCP](https://img.shields.io/badge/MCP-server%20included-purple)](india_mcp/)

> Indian law as structured data — 87 topic pages across 15 categories, built for LLM agents.

Each page covers one legal topic: plain-English definition, section-by-section breakdown, key provisions tables, and cross-links. Updated daily from official sources.

---

## Browse

**Start here → [`wiki/INDEX.md`](wiki/INDEX.md)**

| Category | Count | Sample topics |
|---|---|---|
| Constitutional | 5 | fundamental rights, emergency provisions, amendments |
| Criminal | 18 | murder, rape, cybercrime, PMLA, UAPA, POCSO |
| Procedure | 8 | bail, FIR, trial, evidence, limitation, arbitration |
| Civil | 5 | tort/negligence, consumer rights, RTI, injunction |
| Commercial | 11 | contract, IBC, SEBI, FEMA, RERA, insurance |
| Labour | 8 | EPF, maternity benefit, factories, gratuity |
| Tax | 5 | GST, TDS/TCS, customs, capital gains |
| Family | 8 | divorce, inheritance, adoption, custody, Muslim personal law |
| Property | 4 | transfer, registration, land acquisition, stamp duty |
| Environmental | 4 | EIA/EC, forest rights, wildlife, pollution |
| Intellectual Property | 3 | copyright, patents, trademarks |
| Banking | 2 | banking regulation, SARFAESI/DRT loan recovery |
| Healthcare | 3 | abortion rights, mental health, disability rights |
| Education | 1 | right to education |
| Social | 1 | juvenile justice |

---

## Page format

Every topic page follows the same schema:

```yaml
---
topic: bail
acts:
  - Bharatiya Nagarik Suraksha Sanhita 2023
status: current
department: Ministry of Home Affairs
enactment_date: 2023
updated: 2026-04-13
---

# Bail

## Definition
...

## Current Law
### BNSS 2023
- § 479 — default bail after ½ max sentence for under-trial...

## Key Provisions
| Type | Section | Condition |
|------|---------|-----------|
...

## Related Topics
- [FIR](fir.md)
```

---

## MCP Server

Plug `india_mcp/server.py` into any MCP-compatible agent for instant access to all 87 topics.

### Claude Code setup

```json
{
  "mcpServers": {
    "lex-india": {
      "command": "python3",
      "args": ["/path/to/lex-india/india_mcp/server.py"]
    }
  }
}
```

### Tools

| Tool | What it does |
|---|---|
| `search("anticipatory bail")` | Full-text search → top 10 ranked results with snippets |
| `read("wiki/topics/bail.md")` | Full topic page |
| `read("wiki/INDEX.md")` | All 87 topics at a glance |
| `write(path, content)` | Add or update a wiki page |

### Typical agent flow

```
1. read("wiki/INDEX.md")               → pick relevant topics
2. search("section 438 anticipatory")  → find specific matches
3. read("wiki/topics/bail.md")         → get full detail with sections
```

---

## Repo structure

```
wiki/
  INDEX.md              ← start here
  topics/               ← 87 topic pages
  transitions/          ← IPC→BNS, CrPC→BNSS, Evidence→BSA mappings
india_mcp/
  server.py             ← MCP server (search / read / write)
scripts/
  wiki_gen.py           ← LLM-based page generator
  scraper.py            ← act text scraper (India Code)
  parse_transitions.py  ← 2023 criminal law reform mapper
schema.md               ← page format spec
```

---

## Self-hosting / CI

Two GitHub Actions run automatically:

| Workflow | Schedule | What it does |
|---|---|---|
| `scrape.yml` | Daily 2am UTC | Scrapes updated act text from India Code |
| `wiki-update.yml` | After scrape | Regenerates changed topic pages via Claude API |

To enable wiki auto-update, add your Anthropic API key as a repo secret:
`Settings → Secrets → ANTHROPIC_API_KEY`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for:
- New topic pages (follow [`schema.md`](schema.md))
- Corrections to section numbers or legal details
- State-level law coverage

---

## Disclaimer

Informational and research purposes only. Not legal advice. Consult a qualified lawyer for specific matters.

## License

MIT — legislative text is in the public domain.

---

*Inspired by [legalize-es](https://github.com/legalize-dev/legalize-es) — Spanish legislation as structured data.*
