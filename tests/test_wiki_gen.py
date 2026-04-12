import pytest
from scripts.wiki_gen import (
    build_topic_prompt, parse_wiki_frontmatter,
    topic_page_exists, get_acts_for_topic
)
from pathlib import Path

def test_build_topic_prompt_includes_topic():
    prompt = build_topic_prompt("theft", ["bns-2023"])
    assert "theft" in prompt.lower()
    assert "bns" in prompt.lower()

def test_build_topic_prompt_includes_schema_rules():
    prompt = build_topic_prompt("murder", ["bns-2023"])
    assert "self-contained" in prompt.lower() or "schema" in prompt.lower()

def test_parse_wiki_frontmatter():
    content = "---\ntopic: theft\nacts: [bns-2023]\n---\n\n## Definition\nTest"
    fm = parse_wiki_frontmatter(content)
    assert fm["topic"] == "theft"
    assert "bns-2023" in fm["acts"]

def test_topic_page_exists_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "wiki" / "topics").mkdir(parents=True)
    assert not topic_page_exists("nonexistent-topic")
