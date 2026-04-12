import pytest
from pathlib import Path
from india_mcp.server import search_corpus, read_page, write_page

def test_search_corpus_finds_theft(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki = tmp_path / "wiki" / "topics"
    wiki.mkdir(parents=True)
    (wiki / "theft.md").write_text("# Theft\nSection 303 BNS covers theft.")
    results = search_corpus("theft", str(tmp_path))
    assert len(results) > 0
    assert "theft" in results[0]["path"]

def test_search_corpus_returns_snippets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wiki = tmp_path / "wiki" / "topics"
    wiki.mkdir(parents=True)
    (wiki / "murder.md").write_text("# Murder\nBNS Section 103 covers murder.")
    results = search_corpus("murder", str(tmp_path))
    assert "snippet" in results[0]
    assert len(results[0]["snippet"]) > 0

def test_read_page_returns_content(tmp_path):
    page = tmp_path / "wiki" / "topics" / "theft.md"
    page.parent.mkdir(parents=True)
    page.write_text("# Theft\nTest content")
    content = read_page("wiki/topics/theft.md", str(tmp_path))
    assert content == "# Theft\nTest content"

def test_read_page_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_page("wiki/topics/nonexistent.md", str(tmp_path))

def test_write_page_creates_file(tmp_path):
    write_page("wiki/topics/new-topic.md", "# New Topic\nContent", str(tmp_path))
    assert (tmp_path / "wiki" / "topics" / "new-topic.md").exists()

def test_write_page_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="path traversal"):
        write_page("../evil.md", "content", str(tmp_path))
