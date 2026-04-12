import pytest
from scripts.scraper import parse_act_html, build_frontmatter, slugify

def test_slugify_basic():
    assert slugify("The Indian Penal Code, 1860") == "ipc-1860"

def test_slugify_special_chars():
    assert slugify("The Bharatiya Nyaya Sanhita, 2023") == "bns-2023"

def test_build_frontmatter_required_fields():
    meta = {
        "title": "The Indian Penal Code, 1860",
        "year": "1860",
        "ministry": "Ministry of Law and Justice",
        "status": "superseded",
        "source_url": "https://indiacode.nic.in/handle/123456789/2263",
    }
    fm = build_frontmatter(meta)
    assert fm.startswith("---\n")
    assert "title:" in fm
    assert "year:" in fm
    assert fm.endswith("---\n")

def test_parse_act_html_extracts_title():
    html = """
    <html><body>
      <h1 class="act-title">The Indian Penal Code, 1860</h1>
      <div class="act-content"><p>Section 1. Title.</p></div>
    </body></html>
    """
    result = parse_act_html(html)
    assert result["title"] == "The Indian Penal Code, 1860"
    assert "Section 1" in result["body"]
