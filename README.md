# India Laws Wiki

An open corpus of Indian law topic pages designed for LLM agents — structured, self-contained, and machine-readable.

## What's in here

**86 topic pages** across 15 categories:

| Category | Topics |
|---|---|
| Constitutional | fundamental rights, directive principles, amendments, emergency, panchayati raj |
| Criminal | murder, rape, theft, cheating, corruption, cybercrime, POCSO, UAPA, PMLA, and more |
| Procedure | bail, FIR, trial, evidence, civil suit, appeals, limitation, arbitration |
| Civil | specific performance, injunction, tort/negligence, consumer rights, RTI |
| Commercial | contract, companies, partnership, sale of goods, NI Act, IBC, SEBI, FEMA, RERA, insurance |
| Labour | termination, minimum wages, EPF, maternity, factories, child labour, gratuity |
| Tax | income tax return, GST, customs, TDS/TCS, capital gains |
| Family | divorce, marriage, inheritance, adoption, maintenance, custody, Muslim personal law |
| Property | transfer, registration, land acquisition, stamp duty |
| Environmental | EIA/EC, forest rights, wildlife, pollution control |
| Intellectual Property | copyright, patents, trademarks |
| Banking | banking regulation, loan recovery (SARFAESI/DRT) |
| Healthcare | abortion rights, mental health, disability rights |
| Education | right to education |
| Social | juvenile justice |

Each page has:
- YAML frontmatter (topic slug, relevant acts, date)
- Plain-English definition
- Section-by-section breakdown of current law
- Key provisions tables
- Related topics

## MCP Server

An MCP server is included at `india_mcp/server.py` — plug it into any MCP-compatible agent.

### Tools

| Tool | Description |
|---|---|
| `search(query)` | Full-text search, returns top 10 ranked results with snippets |
| `read(path)` | Read any page, e.g. `wiki/topics/bail.md` or `wiki/INDEX.md` |
| `write(path, content)` | Create or update a wiki page (wiki/ paths only) |

### Usage with Claude Code

Add to `~/.claude/claude.json`:

```json
{
  "mcpServers": {
    "india-laws": {
      "command": "python3",
      "args": ["/path/to/india-laws/india_mcp/server.py"]
    }
  }
}
```

### Usage with any MCP agent

```bash
pip install mcp
python3 india_mcp/server.py
```

Then point your agent at it via stdio transport.

### Typical agent flow

```
1. read("wiki/INDEX.md")           → see all 86 topics
2. search("section 438 bail")      → find relevant pages
3. read("wiki/topics/bail.md")     → get full detail
```

## Repo structure

```
wiki/
  INDEX.md              ← start here
  topics/               ← 86 topic pages
  transitions/          ← IPC→BNS, CrPC→BNSS, Evidence→BSA mappings
india_mcp/
  server.py             ← MCP server (search/read/write tools)
scripts/
  wiki_gen.py           ← LLM-based page generator
  scraper.py            ← act text scraper
  parse_transitions.py  ← 2023 reform transition mapper
schema.md               ← page format spec
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for:
- New topic pages (follow `schema.md`)
- Corrections to section numbers or legal details
- New categories (labour codes, state laws, etc.)

## Disclaimer

This wiki is for informational and research purposes only. It is not legal advice. Always consult a qualified lawyer for specific legal matters.

## License

MIT
