import re
import yaml
import anthropic
from pathlib import Path
from datetime import date

WIKI_TOPICS_DIR = Path("wiki/topics")
WIKI_ACTS_DIR = Path("wiki/acts")
SCHEMA_PATH = Path("schema.md")

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

SEED_TOPICS = [
    ("murder", ["bns-2023"], "criminal"),
    ("theft", ["bns-2023"], "criminal"),
    ("rape", ["bns-2023"], "criminal"),
    ("cheating", ["bns-2023"], "criminal"),
    ("defamation", ["bns-2023"], "criminal"),
    ("bail", ["bnss-2023"], "procedure"),
    ("fir", ["bnss-2023"], "procedure"),
    ("contract", ["indian-contract-act-1872"], "commercial"),
    ("company-incorporation", ["companies-act-2013"], "commercial"),
    ("divorce", ["hindu-marriage-act-1955"], "family"),
    ("income-tax-return", ["income-tax-act-1961"], "tax"),
    ("fundamental-rights", ["constitution"], "constitutional"),
]


def build_topic_prompt(topic: str, act_slugs: list[str]) -> str:
    schema = SCHEMA_PATH.read_text() if SCHEMA_PATH.exists() else ""
    return f"""You are building an India Laws wiki. Write a topic page for: "{topic}"

Relevant acts: {', '.join(act_slugs)}

SCHEMA RULES (follow exactly):
{schema}

CRITICAL: The page must be self-contained. Do not write "see IPC §420" without explaining what it says inline.
Write current law first (BNS/BNSS/BSA if criminal/procedural). Old act references go only in Transition Note.
Use the frontmatter format:
---
topic: {topic}
acts: {act_slugs}
updated: {date.today()}
---

Write the complete topic page now. Plain English first, then legal specifics."""


def parse_wiki_frontmatter(content: str) -> dict:
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def topic_page_exists(topic: str) -> bool:
    return (WIKI_TOPICS_DIR / f"{topic}.md").exists()


def get_acts_for_topic(topic: str) -> list[str]:
    """Look up which acts are relevant for a topic based on SEED_TOPICS."""
    for t, acts, _ in SEED_TOPICS:
        if t == topic:
            return acts
    return []


def generate_topic_page(topic: str, act_slugs: list[str], force: bool = False) -> Path | None:
    path = WIKI_TOPICS_DIR / f"{topic}.md"
    if path.exists() and not force:
        print(f"  SKIP (exists): {path}")
        return None

    prompt = build_topic_prompt(topic, act_slugs)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    content = message.content[0].text
    WIKI_TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  WRITTEN: {path}")
    return path


def generate_act_summary(act_slug: str, act_text: str, force: bool = False) -> Path | None:
    path = WIKI_ACTS_DIR / f"{act_slug}.md"
    if path.exists() and not force:
        return None

    prompt = f"""Write a brief act summary page for an India Laws wiki.

Act: {act_slug}
Full text (first 3000 chars):
{act_text[:3000]}

Output format:
---
act: {act_slug}
updated: {date.today()}
---

## Summary
[1 paragraph plain English description]

## Key Sections
| Section | Description |
|---|---|
[list top 10 sections]

## Status
[in-force / superseded / partially-superseded — and why]"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # cheaper for summaries
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    content = message.content[0].text
    WIKI_ACTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  WRITTEN: {path}")
    return path


def run_wiki_gen(force: bool = False):
    print("Generating topic pages...")
    for topic, acts, _ in SEED_TOPICS:
        generate_topic_page(topic, acts, force=force)

    print("\nGenerating act summaries...")
    for act_path in sorted(Path("acts").rglob("*.md")):
        slug = act_path.stem
        generate_act_summary(slug, act_path.read_text(), force=force)


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_wiki_gen(force=force)
