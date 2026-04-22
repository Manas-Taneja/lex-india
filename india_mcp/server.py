from pathlib import Path
from mcp.server.fastmcp import FastMCP

CORPUS_ROOT = Path(__file__).parent.parent  # repo root

mcp = FastMCP("lex-india")


def search_corpus(query: str, root: str = None) -> list[dict]:
    """Full-text search over wiki/ and acts/ markdown files."""
    root_path = Path(root) if root else CORPUS_ROOT
    results = []
    query_lower = query.lower()
    query_words = query_lower.split()

    for path in sorted(root_path.rglob("*.md")):
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        text_lower = text.lower()
        score = sum(1 for word in query_words if word in text_lower)
        if score == 0:
            continue

        idx = text_lower.find(query_words[0])
        start = max(0, idx - 50)
        snippet = text[start:start + 200].strip()

        results.append({
            "path": str(path.relative_to(root_path)),
            "score": score,
            "snippet": snippet,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]


def read_page(relative_path: str, root: str = None) -> str:
    """Read a wiki or act page by relative path."""
    root_path = Path(root) if root else CORPUS_ROOT
    resolved = (root_path / relative_path).resolve()
    if not resolved.is_relative_to(root_path.resolve()):
        raise ValueError(f"path traversal rejected: {relative_path}")
    if not resolved.exists():
        raise FileNotFoundError(f"Page not found: {relative_path}")
    return resolved.read_text(encoding="utf-8")


def write_page(relative_path: str, content: str, root: str = None) -> str:
    """Write or update a wiki page. Only wiki/ paths allowed."""
    root_path = Path(root) if root else CORPUS_ROOT
    resolved = (root_path / relative_path).resolve()
    if not resolved.is_relative_to(root_path.resolve()):
        raise ValueError(f"path traversal rejected: {relative_path}")
    if not relative_path.startswith("wiki/"):
        raise ValueError(f"write only allowed in wiki/: {relative_path}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Written: {relative_path}"


@mcp.tool()
def search(query: str) -> list[dict]:
    """Search the lex-india corpus for a topic or keyword.
    Returns ranked list of matching pages with path and snippet."""
    return search_corpus(query)


@mcp.tool()
def read(path: str) -> str:
    """Read a specific page from the lex-india corpus.
    Use paths like 'wiki/topics/theft.md' or 'wiki/INDEX.md'."""
    return read_page(path)


@mcp.tool()
def write(path: str, content: str) -> str:
    """Create or update a wiki page. Only wiki/ paths allowed.
    Always follow schema.md rules. Cite sources in frontmatter."""
    return write_page(path, content)


if __name__ == "__main__":
    mcp.run()
