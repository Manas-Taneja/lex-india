# lex-india MCP Server

Gives Claude (or any MCP client) search, read, and write access to the lex-india corpus.

## Setup

```bash
pip install -r requirements.txt
```

## Add to Claude Code

In your Claude config (`claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "lex-india": {
      "command": "python",
      "args": ["/path/to/lex-india/india_mcp/server.py"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `search(query)` | Full-text search, returns top 10 matches with snippets |
| `read(path)` | Read a page, e.g. `wiki/topics/theft.md` |
| `write(path, content)` | Create/update a wiki page (wiki/ only) |

## Example Usage (Claude)

> "What is the punishment for theft in India?"
> Claude calls `search("theft")` → finds `wiki/topics/theft.md` → calls `read("wiki/topics/theft.md")` → answers.
