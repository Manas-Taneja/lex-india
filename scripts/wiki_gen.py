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
    # ── Constitutional ──────────────────────────────────────────────────────
    ("fundamental-rights", ["constitution"], "constitutional"),
    ("directive-principles", ["constitution"], "constitutional"),
    ("constitutional-amendments", ["constitution"], "constitutional"),
    ("emergency-provisions", ["constitution"], "constitutional"),
    ("panchayati-raj", ["constitution", "panchayats-extension-act-1996"], "constitutional"),

    # ── Criminal ────────────────────────────────────────────────────────────
    ("murder", ["bns-2023"], "criminal"),
    ("theft", ["bns-2023"], "criminal"),
    ("rape", ["bns-2023"], "criminal"),
    ("cheating", ["bns-2023"], "criminal"),
    ("defamation", ["bns-2023"], "criminal"),
    ("assault", ["bns-2023"], "criminal"),
    ("kidnapping", ["bns-2023"], "criminal"),
    ("dacoity", ["bns-2023"], "criminal"),
    ("criminal-conspiracy", ["bns-2023"], "criminal"),
    ("drug-offences", ["ndps-act-1985"], "criminal"),
    ("corruption", ["prevention-of-corruption-act-1988"], "criminal"),
    ("money-laundering", ["pmla-2002"], "criminal"),
    ("child-sexual-abuse", ["pocso-act-2012"], "criminal"),
    ("domestic-violence", ["protection-of-women-from-domestic-violence-act-2005"], "criminal"),
    ("cybercrime", ["it-act-2000", "bns-2023"], "criminal"),
    ("atrocities-against-sc-st", ["sc-st-prevention-of-atrocities-act-1989"], "criminal"),
    ("terror-offences", ["uapa-1967"], "criminal"),
    ("sexual-harassment-at-work", ["posh-act-2013"], "criminal"),

    # ── Procedure ───────────────────────────────────────────────────────────
    ("bail", ["bnss-2023"], "procedure"),
    ("fir", ["bnss-2023"], "procedure"),
    ("trial-procedure", ["bnss-2023"], "procedure"),
    ("evidence-rules", ["bsa-2023"], "procedure"),
    ("civil-suit-procedure", ["cpc-1908"], "procedure"),
    ("appeal-and-revision", ["bnss-2023", "cpc-1908"], "procedure"),
    ("limitation-period", ["limitation-act-1963"], "procedure"),
    ("arbitration", ["arbitration-and-conciliation-act-1996"], "procedure"),

    # ── Civil ───────────────────────────────────────────────────────────────
    ("specific-performance", ["specific-relief-act-1963"], "civil"),
    ("injunction", ["specific-relief-act-1963", "cpc-1908"], "civil"),
    ("tort-negligence", ["common-law", "bns-2023"], "civil"),
    ("consumer-rights", ["consumer-protection-act-2019"], "civil"),
    ("right-to-information", ["rti-act-2005"], "civil"),

    # ── Commercial ──────────────────────────────────────────────────────────
    ("contract", ["indian-contract-act-1872"], "commercial"),
    ("company-incorporation", ["companies-act-2013"], "commercial"),
    ("partnership", ["indian-partnership-act-1932", "llp-act-2008"], "commercial"),
    ("sale-of-goods", ["sale-of-goods-act-1930"], "commercial"),
    ("negotiable-instruments", ["negotiable-instruments-act-1881"], "commercial"),
    ("insolvency", ["ibc-2016"], "commercial"),
    ("competition-law", ["competition-act-2002"], "commercial"),
    ("securities-regulation", ["sebi-act-1992"], "commercial"),
    ("foreign-exchange", ["fema-1999"], "commercial"),
    ("insurance", ["insurance-act-1938", "irda-act-1999"], "commercial"),
    ("real-estate-rera", ["rera-2016"], "commercial"),

    # ── Labour ──────────────────────────────────────────────────────────────
    ("employment-termination", ["industrial-disputes-act-1947", "ir-code-2020"], "labour"),
    ("minimum-wages", ["minimum-wages-act-1948", "wages-code-2019"], "labour"),
    ("provident-fund", ["epf-act-1952", "ss-code-2020"], "labour"),
    ("maternity-benefit", ["maternity-benefit-act-1961", "ss-code-2020"], "labour"),
    ("factory-safety", ["factories-act-1948", "osh-code-2020"], "labour"),
    ("child-labour", ["child-labour-prohibition-act-1986"], "labour"),
    ("contract-labour", ["contract-labour-act-1970"], "labour"),
    ("gratuity", ["payment-of-gratuity-act-1972", "ss-code-2020"], "labour"),

    # ── Tax ─────────────────────────────────────────────────────────────────
    ("income-tax-return", ["income-tax-act-1961"], "tax"),
    ("gst", ["cgst-act-2017", "igst-act-2017"], "tax"),
    ("customs-duty", ["customs-act-1962"], "tax"),
    ("tds-tcs", ["income-tax-act-1961"], "tax"),
    ("capital-gains-tax", ["income-tax-act-1961"], "tax"),

    # ── Family ──────────────────────────────────────────────────────────────
    ("divorce", ["hindu-marriage-act-1955"], "family"),
    ("marriage-registration", ["hindu-marriage-act-1955", "special-marriage-act-1954"], "family"),
    ("inheritance-succession", ["hindu-succession-act-1956", "indian-succession-act-1925"], "family"),
    ("adoption", ["hindu-adoption-and-maintenance-act-1956", "juvenile-justice-act-2015"], "family"),
    ("maintenance-alimony", ["hindu-marriage-act-1955", "crpc-section-125", "bnss-2023"], "family"),
    ("child-custody", ["hindu-minority-and-guardianship-act-1956", "guardians-and-wards-act-1890"], "family"),
    ("muslim-personal-law", ["muslim-personal-law-shariat-application-act-1937", "muslim-women-act-2019"], "family"),
    ("child-marriage", ["prohibition-of-child-marriage-act-2006"], "family"),

    # ── Property ────────────────────────────────────────────────────────────
    ("property-transfer", ["transfer-of-property-act-1882"], "property"),
    ("property-registration", ["registration-act-1908"], "property"),
    ("land-acquisition", ["rfctlarr-act-2013"], "property"),
    ("stamp-duty", ["indian-stamp-act-1899"], "property"),

    # ── Environment ─────────────────────────────────────────────────────────
    ("environmental-clearance", ["environment-protection-act-1986"], "environment"),
    ("forest-rights", ["forest-conservation-act-1980", "forest-rights-act-2006"], "environment"),
    ("wildlife-protection", ["wildlife-protection-act-1972"], "environment"),
    ("pollution-control", ["water-act-1974", "air-act-1981"], "environment"),

    # ── Intellectual Property ────────────────────────────────────────────────
    ("copyright", ["copyright-act-1957"], "ip"),
    ("patents", ["patents-act-1970"], "ip"),
    ("trademarks", ["trade-marks-act-1999"], "ip"),

    # ── Banking & Finance ────────────────────────────────────────────────────
    ("banking-regulation", ["banking-regulation-act-1949", "rbi-act-1934"], "banking"),
    ("loan-recovery", ["sarfaesi-act-2002", "rdb-act-1993"], "banking"),

    # ── Healthcare ───────────────────────────────────────────────────────────
    ("abortion-rights", ["mtp-act-1971"], "healthcare"),
    ("mental-health-law", ["mental-healthcare-act-2017"], "healthcare"),
    ("disability-rights", ["rpwd-act-2016"], "healthcare"),

    # ── Education & Social ───────────────────────────────────────────────────
    ("right-to-education", ["rte-act-2009"], "education"),
    ("juvenile-justice", ["juvenile-justice-act-2015"], "social"),
]


def build_topic_prompt(topic: str, act_slugs: list[str]) -> str:
    schema = SCHEMA_PATH.read_text() if SCHEMA_PATH.exists() else ""
    return f"""You are building the lex-india wiki. Write a topic page for: "{topic}"

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


FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
STRIP_BOLD_ITALIC_RE = re.compile(r'\*+')
STRIP_CODE_RE = re.compile(r'`[^`]*`')
SENTENCE_RE = re.compile(r'([^.!?]+[.!?])')


def parse_wiki_frontmatter(content: str) -> dict:
    match = FRONTMATTER_RE.match(content)
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

    prompt = f"""Write a brief act summary page for the lex-india wiki.

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


CATEGORY_HEADERS = {
    "constitutional": "## Constitutional Law",
    "criminal":       "## Criminal Law",
    "procedure":      "## Procedure",
    "civil":          "## Civil Law",
    "commercial":     "## Commercial Law",
    "labour":         "## Labour Law",
    "tax":            "## Tax Law",
    "family":         "## Family Law",
    "property":       "## Property Law",
    "environment":    "## Environmental Law",
    "ip":             "## Intellectual Property",
    "banking":        "## Banking & Finance",
    "healthcare":     "## Healthcare Law",
    "education":      "## Education Law",
    "social":         "## Social Law",
}

TRANSITIONS_SECTION = """## Transitions (2023 Reform)
- [IPC → BNS](transitions/ipc-to-bns.md) — section mapping for Bharatiya Nyaya Sanhita 2023
- [CrPC → BNSS](transitions/crpc-to-bnss.md) — section mapping for Bharatiya Nagarik Suraksha Sanhita 2023
- [Evidence Act → BSA](transitions/evidence-to-bsa.md) — section mapping for Bharatiya Sakshya Adhiniyam 2023
"""


def _one_liner_from_page(content: str) -> str:
    """Extract first non-empty sentence after frontmatter and headings."""
    lines = content.splitlines()
    # Skip frontmatter (--- ... ---)
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    for line in lines[start:]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("|") or line.startswith(">"):
            continue
        if line.startswith("-") or line.startswith("*") and len(line) < 4:
            continue
        # Strip markdown bold/italic
        clean = STRIP_BOLD_ITALIC_RE.sub('', line)
        clean = STRIP_CODE_RE.sub('', clean)
        clean = clean.strip()
        if not clean:
            continue
        m = SENTENCE_RE.match(clean)
        if m:
            return m.group(1).strip()
        return clean[:120]
    return ""


def _acts_from_frontmatter(content: str) -> list[str]:
    fm = parse_wiki_frontmatter(content)
    return fm.get("acts", [])


def update_index():
    """Rebuild wiki/INDEX.md from all existing topic pages."""
    index_path = Path("wiki/INDEX.md")

    # Build category → list of (topic, one_liner, acts) from SEED_TOPICS order
    cat_map: dict[str, list[tuple[str, str, list[str]]]] = {c: [] for c in CATEGORY_HEADERS}

    for topic, acts, category in SEED_TOPICS:
        page_path = WIKI_TOPICS_DIR / f"{topic}.md"
        if not page_path.exists():
            continue
        content = page_path.read_text(encoding="utf-8")
        one_liner = _one_liner_from_page(content)
        acts_in_file = _acts_from_frontmatter(content) or acts
        cat_map.setdefault(category, []).append((topic, one_liner, acts_in_file))

    lines = [
        "# lex-india — Topic Index\n",
        "> Entry point for LLM agents. Read this file first, then fetch the relevant topic page.",
        "> All topic pages are self-contained — no cross-file lookups needed to answer a query.\n",
    ]

    for cat, header in CATEGORY_HEADERS.items():
        entries = cat_map.get(cat, [])
        lines.append(header)
        if not entries:
            lines.append("<!-- topics go here -->")
        else:
            for topic, one_liner, acts in entries:
                primary = acts[0] if acts else ""
                desc = one_liner or topic.replace("-", " ").title()
                lines.append(f"- [{topic}](topics/{topic}.md) — {desc}")
        lines.append("")

    lines.append(TRANSITIONS_SECTION)

    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  INDEX updated: {index_path} ({sum(len(v) for v in cat_map.values())} topics)")


def run_wiki_gen(force: bool = False, category: str | None = None):
    topics = SEED_TOPICS
    if category:
        topics = [(t, a, c) for t, a, c in SEED_TOPICS if c == category]
        print(f"Generating topic pages (category={category}, {len(topics)} topics)...")
    else:
        print(f"Generating topic pages ({len(topics)} total)...")

    for topic, acts, _ in topics:
        generate_topic_page(topic, acts, force=force)

    if not category:
        print("\nGenerating act summaries...")
        for act_path in sorted(Path("acts").rglob("*.md")):
            slug = act_path.stem
            generate_act_summary(slug, act_path.read_text(), force=force)

    print("\nUpdating INDEX.md...")
    update_index()


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    force = "--force" in args
    cat = next((a.split("=", 1)[1] for a in args if a.startswith("--category=")), None)
    run_wiki_gen(force=force, category=cat)
