# Phase 1 — Depth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship full text of 5 foundational Indian acts (BNS, BNSS, BSA, Contract Act 1872, IBC 2016) as section-per-file markdown under `acts/`, addressable via MCP, validated in CI.

**Architecture:** Python typer CLI scrapes indiacode.nic.in (HTML primary, PDF fallback). Each act stored as `acts/{slug}/sections/{N}.md` with YAML frontmatter validated by shared pydantic models. MCP server gains typed `get_section`/`get_index`/`propose_edit` tools. CI validates schema + link integrity on every PR; daily cron opens auto-PR on detected upstream changes.

**Tech Stack:** Python 3.11+, `httpx`, `selectolax`, `pdfplumber`, `pydantic v2`, `ruamel.yaml`, `typer`, `pytest`, `mcp[cli]` (existing). GitHub Actions for CI/cron.

**Companion design doc:** `docs/plans/2026-04-19-direction-design.md` — read first.

**Scope discipline:** Phase 1 only. No embeddings. No case law. No state law. No MCP tools beyond the 3 listed. Cross-linking from topics is light-touch (sample only); deep cross-linking is Phase 2.

---

## Pre-flight

- [ ] Read companion design doc above
- [ ] Confirm working on `main` or a feature branch (`git status`)
- [ ] Confirm `python --version` ≥ 3.11
- [ ] No uncommitted changes (`git status` clean)

---

## Task 1: Pin dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1:** Read current `requirements.txt`.

**Step 2:** Replace contents with:

```
mcp[cli]>=1.0
httpx>=0.27
selectolax>=0.3.21
pdfplumber>=0.11
pydantic>=2.7
ruamel.yaml>=0.18
typer>=0.12
pytest>=8.0
pytest-asyncio>=0.23
```

**Step 3:** Install:

```bash
pip install -r requirements.txt
```
Expected: all install cleanly. Note any conflicts; resolve before continuing.

**Step 4:** Commit.

```bash
git add requirements.txt
git commit -m "chore: pin Phase 1 deps (httpx, selectolax, pdfplumber, pydantic, typer)"
```

---

## Task 2: Pydantic models — single source of truth

**Files:**
- Create: `india_mcp/models.py`
- Test: `tests/test_models.py`

**Step 1: Write failing test** — `tests/test_models.py`:

```python
from datetime import date
import pytest
from pydantic import ValidationError
from india_mcp.models import SectionFrontmatter, ActMeta

def test_section_frontmatter_minimal_valid():
    fm = SectionFrontmatter(
        act="bns",
        section="103",
        chapter=6,
        heading="Punishment for murder",
        status="in_force",
        source_url="https://indiacode.nic.in/x",
        source_hash="sha256:abc",
        synced=date(2026, 4, 19),
    )
    assert fm.section == "103"

def test_section_frontmatter_string_section_id():
    """Sections like 498A, 377A must be allowed as strings."""
    fm = SectionFrontmatter(
        act="ipc", section="498A", chapter=20, heading="Cruelty",
        status="in_force",
        source_url="https://indiacode.nic.in/x",
        source_hash="sha256:abc",
        synced=date(2026, 4, 19),
    )
    assert fm.section == "498A"

def test_section_frontmatter_rejects_bad_status():
    with pytest.raises(ValidationError):
        SectionFrontmatter(
            act="bns", section="1", chapter=1, heading="x",
            status="invalid",
            source_url="https://indiacode.nic.in/x",
            source_hash="sha256:abc",
            synced=date(2026, 4, 19),
        )

def test_act_meta_valid():
    m = ActMeta(
        slug="bns", title="Bharatiya Nyaya Sanhita", year=2023,
        ministry="Ministry of Home Affairs",
        source_url="https://indiacode.nic.in/x",
        last_synced=date(2026, 4, 19),
        section_count=358,
    )
    assert m.slug == "bns"
```

**Step 2:** Run — `pytest tests/test_models.py -v`. Expected: 4 FAILED (module not found).

**Step 3: Write minimal implementation** — `india_mcp/models.py`:

```python
from datetime import date
from typing import Literal
from pydantic import BaseModel, HttpUrl, Field

Status = Literal["in_force", "repealed", "needs_manual_review"]

class SectionFrontmatter(BaseModel):
    act: str
    section: str  # str — handles "498A", "377A"
    chapter: int | None = None
    heading: str
    status: Status
    amended_by: list[str] = Field(default_factory=list)
    source_url: HttpUrl
    source_hash: str
    synced: date
    parse_error: str | None = None

class ActMeta(BaseModel):
    slug: str
    title: str
    year: int
    ministry: str
    source_url: HttpUrl
    last_synced: date
    section_count: int
```

**Step 4:** Run tests — `pytest tests/test_models.py -v`. Expected: 4 PASS.

**Step 5:** Commit.

```bash
git add india_mcp/models.py tests/test_models.py
git commit -m "feat: add pydantic models for act sections + meta"
```

---

## Task 3: YAML frontmatter helpers

**Files:**
- Create: `india_mcp/frontmatter.py`
- Test: `tests/test_frontmatter.py`

**Step 1: Test** — `tests/test_frontmatter.py`:

```python
from india_mcp.frontmatter import parse, dump

SAMPLE = """---
act: bns
section: "103"
heading: Punishment for murder
status: in_force
source_url: https://indiacode.nic.in/x
source_hash: sha256:abc
synced: 2026-04-19
---

# § 103 — Punishment for murder

## Text
Body here.
"""

def test_parse_returns_frontmatter_and_body():
    fm, body = parse(SAMPLE)
    assert fm["section"] == "103"
    assert body.startswith("# § 103")

def test_dump_roundtrip():
    fm, body = parse(SAMPLE)
    out = dump(fm, body)
    fm2, body2 = parse(out)
    assert fm2 == fm
    assert body2.strip() == body.strip()

def test_parse_no_frontmatter_returns_empty_dict():
    fm, body = parse("Just body.\n")
    assert fm == {}
    assert body == "Just body.\n"
```

**Step 2:** Run — `pytest tests/test_frontmatter.py -v`. Expected: FAIL.

**Step 3: Implement** — `india_mcp/frontmatter.py`:

```python
from io import StringIO
from ruamel.yaml import YAML

yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.preserve_quotes = True

def parse(text: str) -> tuple[dict, str]:
    """Split a markdown file with YAML frontmatter into (dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]
    return dict(yaml.load(fm_text) or {}), body

def dump(fm: dict, body: str) -> str:
    buf = StringIO()
    yaml.dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n\n{body.lstrip()}"
```

**Step 4:** Run tests — PASS.

**Step 5:** Commit.

```bash
git add india_mcp/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: add YAML frontmatter parse/dump helpers"
```

---

## Task 4: Scraper CLI scaffolding

**Files:**
- Create: `scripts/scrape_act.py`

**Step 1: Implement** — minimal typer CLI:

```python
"""Scrape an Indian act from indiacode.nic.in into acts/{slug}/."""
from pathlib import Path
import typer

app = typer.Typer(help="Scrape Indian acts.")

REPO_ROOT = Path(__file__).parent.parent

REGISTRY: dict[str, dict] = {
    "bns": {
        "title": "Bharatiya Nyaya Sanhita",
        "year": 2023,
        "ministry": "Ministry of Home Affairs",
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20062",
    },
    "bnss": {
        "title": "Bharatiya Nagarik Suraksha Sanhita",
        "year": 2023,
        "ministry": "Ministry of Home Affairs",
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20098",
    },
    "bsa": {
        "title": "Bharatiya Sakshya Adhiniyam",
        "year": 2023,
        "ministry": "Ministry of Home Affairs",
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20063",
    },
    "contract-act": {
        "title": "Indian Contract Act",
        "year": 1872,
        "ministry": "Ministry of Law and Justice",
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2187",
    },
    "ibc": {
        "title": "Insolvency and Bankruptcy Code",
        "year": 2016,
        "ministry": "Ministry of Corporate Affairs",
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2154",
    },
}

@app.command()
def scrape(slug: str, dry_run: bool = False):
    """Scrape one act by slug. Use 'all' to scrape every registered act."""
    if slug == "all":
        for s in REGISTRY:
            scrape(s, dry_run=dry_run)
        return
    if slug not in REGISTRY:
        typer.secho(f"Unknown slug: {slug}. Known: {list(REGISTRY)}", fg="red")
        raise typer.Exit(1)
    typer.echo(f"Would scrape {slug} from {REGISTRY[slug]['source_url']}")
    # Implementation in subsequent tasks.

if __name__ == "__main__":
    app()
```

**Step 2:** Smoke test — `python scripts/scrape_act.py scrape bns --dry-run`. Expected: prints the URL.

> **Note:** the source URLs above are PLACEHOLDERS pointing to indiacode handle pages. Verify each URL resolves to the act's section listing before running real scrapes (Task 6+). If indiacode's URL scheme has changed, update the registry first.

**Step 3:** Commit.

```bash
git add scripts/scrape_act.py
git commit -m "feat(scraper): add CLI scaffolding + act registry"
```

---

## Task 5: Fetch + cache HTML

**Files:**
- Create: `india_mcp/fetch.py`
- Test: `tests/test_fetch.py`
- Create: `.cache/.gitkeep`

**Step 1: Test** — `tests/test_fetch.py`:

```python
from pathlib import Path
from india_mcp.fetch import fetch_cached

def test_fetch_cached_uses_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr("india_mcp.fetch.CACHE_DIR", cache)
    calls = []

    def fake_get(url):
        calls.append(url)
        return "<html>hi</html>"

    monkeypatch.setattr("india_mcp.fetch._http_get", fake_get)
    a = fetch_cached("https://example.com/x")
    b = fetch_cached("https://example.com/x")
    assert a == b == "<html>hi</html>"
    assert len(calls) == 1  # second call hit cache
```

**Step 2:** Run — FAIL.

**Step 3: Implement** — `india_mcp/fetch.py`:

```python
import hashlib
import httpx
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"

def _http_get(url: str) -> str:
    with httpx.Client(timeout=30.0, follow_redirects=True,
                      headers={"User-Agent": "lex-india/0.1 (+github.com/Manas-Taneja/lex-india)"}) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text

def fetch_cached(url: str) -> str:
    """Fetch URL with on-disk cache keyed by URL hash. Idempotent."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{key}.html"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    text = _http_get(url)
    cache_file.write_text(text, encoding="utf-8")
    return text
```

**Step 4:** Add `.cache/` to `.gitignore` if not present:

```bash
grep -q "^\.cache/" .gitignore || echo ".cache/" >> .gitignore
```

**Step 5:** Run tests — PASS.

**Step 6:** Commit.

```bash
git add india_mcp/fetch.py tests/test_fetch.py .gitignore
git commit -m "feat(scraper): add cached HTTP fetcher"
```

---

## Task 6: Section parser (HTML strategy)

**Files:**
- Create: `india_mcp/parser.py`
- Test: `tests/test_parser.py`
- Create: `tests/fixtures/bns_sample.html`

**Step 1: Fixture** — save a small representative snippet of indiacode HTML containing 2–3 sections to `tests/fixtures/bns_sample.html`. (For the first run, fetch the live page once with `python -c "from india_mcp.fetch import fetch_cached; print(fetch_cached('<bns-url>'))" > tmp.html`, then trim to ~3 sections by hand and save as the fixture.)

**Step 2: Test** — `tests/test_parser.py`:

```python
from pathlib import Path
from india_mcp.parser import parse_sections

FIXTURE = (Path(__file__).parent / "fixtures" / "bns_sample.html").read_text()

def test_parse_sections_returns_list():
    sections = parse_sections(FIXTURE)
    assert len(sections) >= 1

def test_section_has_required_fields():
    sections = parse_sections(FIXTURE)
    s = sections[0]
    assert s["number"]
    assert s["heading"]
    assert s["text"]
    assert len(s["text"]) > 10

def test_section_numbers_are_strings():
    sections = parse_sections(FIXTURE)
    for s in sections:
        assert isinstance(s["number"], str)
```

**Step 3:** Run — FAIL.

**Step 4: Implement** — `india_mcp/parser.py`. Indiacode's exact HTML structure must be inspected first; the snippet below is a starting point — adjust selectors after viewing one real page:

```python
import re
from selectolax.parser import HTMLParser

# Section header pattern: matches "1.", "103.", "498A.", "498-A.", etc.
SECTION_RE = re.compile(r"^\s*(\d+[A-Z]?(?:-[A-Z])?)\.\s+(.+?)\s*[—\-:]\s*", re.MULTILINE)

def parse_sections(html: str) -> list[dict]:
    """Split an act's HTML into a list of {number, heading, text} dicts.
    Implementation is deliberately tolerant — adjust selectors per inspection.
    """
    tree = HTMLParser(html)
    # Try common containers; fall back to whole-document text.
    body = tree.css_first("div.act-content, div#content, article, body")
    if body is None:
        return []
    text = body.text(separator="\n", strip=True)

    sections = []
    matches = list(SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        number = m.group(1)
        heading_full = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body_text = text[start:end].strip()
        sections.append({
            "number": number,
            "heading": heading_full,
            "text": body_text,
        })
    return sections
```

**Step 5:** Run tests — PASS (may need to tune the regex or selector once against the real fixture).

**Step 6:** Commit.

```bash
git add india_mcp/parser.py tests/test_parser.py tests/fixtures/bns_sample.html
git commit -m "feat(scraper): add HTML section parser + BNS fixture"
```

---

## Task 7: Section file writer

**Files:**
- Create: `india_mcp/writer.py`
- Test: `tests/test_writer.py`

**Step 1: Test** — `tests/test_writer.py`:

```python
from datetime import date
from pathlib import Path
from india_mcp.models import SectionFrontmatter
from india_mcp.writer import write_section, section_filename

def test_section_filename_pads_numeric():
    assert section_filename("1") == "001.md"
    assert section_filename("103") == "103.md"
    assert section_filename("498A") == "498A.md"

def test_write_section_creates_file(tmp_path):
    fm = SectionFrontmatter(
        act="bns", section="103", chapter=6,
        heading="Punishment for murder", status="in_force",
        source_url="https://indiacode.nic.in/x",
        source_hash="sha256:abc",
        synced=date(2026, 4, 19),
    )
    write_section(tmp_path, fm, body_text="(1) Whoever commits murder...")
    f = tmp_path / "sections" / "103.md"
    assert f.exists()
    content = f.read_text()
    assert "section: '103'" in content or 'section: "103"' in content
    assert "Whoever commits murder" in content
```

**Step 2:** Run — FAIL.

**Step 3: Implement** — `india_mcp/writer.py`:

```python
from pathlib import Path
from india_mcp.models import SectionFrontmatter
from india_mcp.frontmatter import dump

def section_filename(number: str) -> str:
    """Pad numeric portion to 3 digits for stable sort. Keeps suffix letters."""
    import re
    m = re.match(r"^(\d+)([A-Z\-]*)$", number)
    if not m:
        return f"{number}.md"
    num, suffix = m.group(1), m.group(2)
    return f"{int(num):03d}{suffix}.md"

def write_section(act_dir: Path, fm: SectionFrontmatter, body_text: str) -> Path:
    """Write a section file under {act_dir}/sections/{NNN}.md. Returns path."""
    sections_dir = act_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    path = sections_dir / section_filename(fm.section)
    body = (
        f"# § {fm.section} — {fm.heading}\n\n"
        f"## Text\n{body_text}\n\n"
        f"## Cross-references\n_(none yet — populated by build_backlinks.py)_\n"
    )
    fm_dict = fm.model_dump(mode="json")
    path.write_text(dump(fm_dict, body), encoding="utf-8")
    return path
```

**Step 4:** Run tests — PASS.

**Step 5:** Commit.

```bash
git add india_mcp/writer.py tests/test_writer.py
git commit -m "feat(scraper): add section file writer"
```

---

## Task 8: meta.yaml + INDEX.md generators

**Files:**
- Modify: `india_mcp/writer.py` (add `write_meta`, `write_index`)
- Modify: `tests/test_writer.py` (add tests)

**Step 1: Add tests** to `tests/test_writer.py`:

```python
from india_mcp.models import ActMeta
from india_mcp.writer import write_meta, write_index

def test_write_meta_creates_yaml(tmp_path):
    meta = ActMeta(
        slug="bns", title="BNS", year=2023, ministry="MHA",
        source_url="https://indiacode.nic.in/x",
        last_synced=date(2026, 4, 19), section_count=358,
    )
    write_meta(tmp_path, meta)
    assert (tmp_path / "meta.yaml").exists()
    content = (tmp_path / "meta.yaml").read_text()
    assert "slug: bns" in content
    assert "section_count: 358" in content

def test_write_index_lists_sections(tmp_path):
    sections = [
        {"number": "1", "heading": "Short title"},
        {"number": "103", "heading": "Punishment for murder"},
    ]
    write_index(tmp_path, act_title="BNS", sections=sections)
    f = tmp_path / "INDEX.md"
    assert f.exists()
    content = f.read_text()
    assert "§ 1" in content
    assert "Short title" in content
    assert "§ 103" in content
```

**Step 2:** Run — FAIL.

**Step 3: Implement** — append to `india_mcp/writer.py`:

```python
from io import StringIO
from ruamel.yaml import YAML
from india_mcp.models import ActMeta

_yaml = YAML(typ="safe")
_yaml.default_flow_style = False

def write_meta(act_dir: Path, meta: ActMeta) -> Path:
    act_dir.mkdir(parents=True, exist_ok=True)
    buf = StringIO()
    _yaml.dump(meta.model_dump(mode="json"), buf)
    path = act_dir / "meta.yaml"
    path.write_text(buf.getvalue(), encoding="utf-8")
    return path

def write_index(act_dir: Path, act_title: str, sections: list[dict]) -> Path:
    act_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {act_title} — Section Index\n"]
    for s in sections:
        lines.append(f"- [§ {s['number']}](sections/{section_filename(s['number'])}) — {s['heading']}")
    path = act_dir / "INDEX.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
```

**Step 4:** Run tests — PASS.

**Step 5:** Commit.

```bash
git add india_mcp/writer.py tests/test_writer.py
git commit -m "feat(scraper): add meta.yaml + INDEX.md generators"
```

---

## Task 9: Wire scraper end-to-end

**Files:**
- Modify: `scripts/scrape_act.py`

**Step 1: Replace** the `scrape` command body to actually run the pipeline:

```python
import hashlib
from datetime import date
from india_mcp.fetch import fetch_cached
from india_mcp.parser import parse_sections
from india_mcp.writer import write_section, write_meta, write_index
from india_mcp.models import SectionFrontmatter, ActMeta

@app.command()
def scrape(slug: str, dry_run: bool = False):
    if slug == "all":
        for s in REGISTRY:
            scrape(s, dry_run=dry_run)
        return
    if slug not in REGISTRY:
        typer.secho(f"Unknown slug: {slug}. Known: {list(REGISTRY)}", fg="red")
        raise typer.Exit(1)

    info = REGISTRY[slug]
    act_dir = REPO_ROOT / "acts" / slug
    typer.echo(f"Fetching {info['source_url']}")
    html = fetch_cached(info["source_url"])
    sections = parse_sections(html)
    typer.echo(f"Parsed {len(sections)} sections")

    if dry_run:
        for s in sections[:3]:
            typer.echo(f"  § {s['number']}: {s['heading'][:60]}")
        return

    today = date.today()
    for s in sections:
        body_hash = hashlib.sha256(s["text"].encode()).hexdigest()
        fm = SectionFrontmatter(
            act=slug,
            section=s["number"],
            heading=s["heading"],
            status="in_force",
            source_url=info["source_url"],
            source_hash=f"sha256:{body_hash}",
            synced=today,
        )
        write_section(act_dir, fm, body_text=s["text"])

    meta = ActMeta(
        slug=slug, title=info["title"], year=info["year"],
        ministry=info["ministry"], source_url=info["source_url"],
        last_synced=today, section_count=len(sections),
    )
    write_meta(act_dir, meta)
    write_index(act_dir, act_title=info["title"], sections=sections)
    typer.secho(f"✓ {slug}: wrote {len(sections)} sections to {act_dir}", fg="green")
```

**Step 2:** Dry-run BNS — `python scripts/scrape_act.py scrape bns --dry-run`. Expected: prints first 3 section headings.

**Step 3:** Real run BNS — `python scripts/scrape_act.py scrape bns`. Expected: `acts/bns/` populated with INDEX.md, meta.yaml, and sections/.

**Step 4:** Spot-check 3 random sections by opening them. Confirm frontmatter validates:

```bash
python -c "
from pathlib import Path
from india_mcp.frontmatter import parse
from india_mcp.models import SectionFrontmatter
for f in sorted(Path('acts/bns/sections').glob('*.md'))[:5]:
    fm, _ = parse(f.read_text())
    SectionFrontmatter.model_validate(fm)
    print(f.name, '✓')
"
```

**Step 5:** Commit (separately for code + data so reviewers can examine each).

```bash
git add scripts/scrape_act.py
git commit -m "feat(scraper): wire fetch → parse → write end-to-end"

git add acts/bns/
git commit -m "data: import BNS 2023 from indiacode (Phase 1)"
```

---

## Task 10: Schema validator script

**Files:**
- Create: `scripts/validate.py`
- Test: `tests/test_validate.py`

**Step 1: Test** — `tests/test_validate.py`:

```python
from pathlib import Path
import subprocess

REPO = Path(__file__).parent.parent

def test_validate_passes_on_real_corpus():
    """After Task 9, acts/bns/ should validate cleanly."""
    result = subprocess.run(
        ["python", "scripts/validate.py"], cwd=REPO, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

**Step 2:** Run — FAIL (script missing).

**Step 3: Implement** — `scripts/validate.py`:

```python
"""Validate every act/wiki markdown file: schema, links, section continuity."""
import sys
from pathlib import Path
from india_mcp.frontmatter import parse
from india_mcp.models import SectionFrontmatter

REPO = Path(__file__).parent.parent
errors: list[str] = []

def validate_section_files():
    for sec_dir in (REPO / "acts").glob("*/sections"):
        for f in sec_dir.glob("*.md"):
            try:
                fm, _ = parse(f.read_text(encoding="utf-8"))
                SectionFrontmatter.model_validate(fm)
            except Exception as e:
                errors.append(f"{f.relative_to(REPO)}: {e}")

def validate_internal_links():
    import re
    link_re = re.compile(r"\]\((\.\./[^)]+\.md)\)")
    for f in REPO.rglob("*.md"):
        if "/.cache/" in str(f) or "/node_modules/" in str(f):
            continue
        for m in link_re.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            target = (f.parent / m.group(1)).resolve()
            if not target.exists():
                errors.append(f"{f.relative_to(REPO)}: broken link → {m.group(1)}")

def main():
    validate_section_files()
    validate_internal_links()
    if errors:
        for e in errors:
            print(f"✗ {e}")
        print(f"\n{len(errors)} error(s)")
        sys.exit(1)
    print("✓ all valid")

if __name__ == "__main__":
    main()
```

**Step 4:** Run — `python scripts/validate.py`. Expected: `✓ all valid` (after BNS import).

**Step 5:** Run pytest — PASS.

**Step 6:** Commit.

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat(ci): add schema + link validator"
```

---

## Task 11: GitHub Actions — validate on PR

**Files:**
- Create: `.github/workflows/validate.yml`

**Step 1: Implement:**

```yaml
name: validate
on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest -q
      - run: python scripts/validate.py
```

**Step 2:** Commit + push to a throwaway branch, open a draft PR, confirm green.

```bash
git checkout -b ci/validate
git add .github/workflows/validate.yml
git commit -m "ci: validate schema + links on every PR"
git push -u origin ci/validate
# open draft PR via gh pr create, confirm workflow runs green, then merge
```

**Step 3:** Merge + delete branch.

---

## Task 12: Scrape remaining 4 acts

For each of `bnss`, `bsa`, `contract-act`, `ibc`:

**Step 1:** `python scripts/scrape_act.py scrape <slug> --dry-run` — verify section count looks right.

**Step 2:** If parse looks wrong, inspect HTML, tune `SECTION_RE` or selector in `india_mcp/parser.py`, re-run dry. Add a fixture under `tests/fixtures/<slug>_sample.html` if behaviour diverges.

**Step 3:** Real scrape — `python scripts/scrape_act.py scrape <slug>`.

**Step 4:** `python scripts/validate.py`. Fix any `needs_manual_review` flagged sections by hand if blocking.

**Step 5:** Commit one act per commit:

```bash
git add acts/<slug>/
git commit -m "data: import <ACT_NAME> from indiacode (Phase 1)"
```

**Estimate:** ~30 min per act assuming the parser is reasonably robust; schedule and ageing acts (Contract Act 1872) may need manual fixups for sections involving repealed amendments.

---

## Task 13: log.md (Karpathy curation log)

**Files:**
- Create: `log.md`

**Step 1: Implement:**

```markdown
# Curation log

Append-only record of corpus changes. Both humans and AI agents append here.
Newest entries on top.

---

## 2026-04-19 — Phase 1 launch

- Imported full text of 5 foundational acts from indiacode.nic.in:
  BNS 2023, BNSS 2023, BSA 2023, Indian Contract Act 1872, IBC 2016
- New schema: `acts/{slug}/sections/{NNN}.md` + per-act `INDEX.md` + `meta.yaml`
- Pydantic models in `india_mcp/models.py` shared across scraper, MCP, validator
- CI gate: schema + internal-link validation on every PR
```

**Step 2:** Commit.

```bash
git add log.md
git commit -m "docs: add curation log (Karpathy convention)"
```

---

## Task 14: MCP — `get_section` tool

**Files:**
- Modify: `india_mcp/server.py`
- Test: `tests/test_mcp_get_section.py`

**Step 1: Test:**

```python
from india_mcp.server import _get_section_impl

def test_get_section_returns_typed_dict():
    s = _get_section_impl("bns", "103")
    assert s["section"] == "103"
    assert s["act"] == "bns"
    assert "text" in s
    assert s["status"] in {"in_force", "repealed", "needs_manual_review"}

def test_get_section_unknown_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        _get_section_impl("bns", "99999")
```

**Step 2:** Run — FAIL.

**Step 3:** Add to `india_mcp/server.py` (alongside existing tools):

```python
from india_mcp.frontmatter import parse as _parse_fm
from india_mcp.writer import section_filename

def _get_section_impl(act: str, section: str) -> dict:
    path = CORPUS_ROOT / "acts" / act / "sections" / section_filename(section)
    if not path.exists():
        raise FileNotFoundError(f"acts/{act}/sections/{section_filename(section)}")
    fm, body = _parse_fm(path.read_text(encoding="utf-8"))
    # extract just the text block
    text = body
    if "## Text" in body:
        text = body.split("## Text", 1)[1]
        if "##" in text:
            text = text.split("##", 1)[0]
    return {**fm, "text": text.strip()}

@mcp.tool()
def get_section(act: str, section: str) -> dict:
    """Fetch one section of an act with frontmatter + body text.
    Example: get_section("bns", "103")."""
    return _get_section_impl(act, section)
```

**Step 4:** Tests PASS.

**Step 5:** Commit.

```bash
git add india_mcp/server.py tests/test_mcp_get_section.py
git commit -m "feat(mcp): add get_section tool"
```

---

## Task 15: MCP — `get_index` tool

**Files:**
- Modify: `india_mcp/server.py`
- Test: `tests/test_mcp_get_index.py`

**Step 1: Test:**

```python
from india_mcp.server import _get_index_impl

def test_get_index_returns_act_index():
    out = _get_index_impl("acts/bns")
    assert "Section Index" in out or "INDEX" in out

def test_get_index_returns_wiki_index():
    out = _get_index_impl("wiki")
    assert len(out) > 100

def test_get_index_rejects_traversal():
    import pytest
    with pytest.raises(ValueError):
        _get_index_impl("../etc")
```

**Step 2:** Run — FAIL.

**Step 3:** Add to `india_mcp/server.py`:

```python
def _get_index_impl(scope: str) -> str:
    """Return INDEX.md content for a scope. Scope = relative dir under repo root."""
    target = (CORPUS_ROOT / scope).resolve()
    root_resolved = CORPUS_ROOT.resolve()
    if not str(target).startswith(str(root_resolved)):
        raise ValueError(f"path traversal rejected: {scope}")
    index_file = target / "INDEX.md"
    if not index_file.exists():
        raise FileNotFoundError(f"{scope}/INDEX.md")
    return index_file.read_text(encoding="utf-8")

@mcp.tool()
def get_index(scope: str) -> str:
    """Read the INDEX.md for a scope (e.g. 'wiki', 'acts/bns', 'wiki/topics')."""
    return _get_index_impl(scope)
```

**Step 4:** Tests PASS.

**Step 5:** Commit.

```bash
git add india_mcp/server.py tests/test_mcp_get_index.py
git commit -m "feat(mcp): add get_index tool"
```

---

## Task 16: MCP — `propose_edit` tool + `.proposals/` convention

**Files:**
- Modify: `india_mcp/server.py`
- Modify: `.gitignore` (ignore `.proposals/`)
- Test: `tests/test_mcp_propose_edit.py`

**Step 1: Test:**

```python
from india_mcp.server import _propose_edit_impl

def test_propose_edit_writes_proposal_file(tmp_path, monkeypatch):
    monkeypatch.setattr("india_mcp.server.CORPUS_ROOT", tmp_path)
    out = _propose_edit_impl(
        path="wiki/topics/test.md",
        diff="--- a\n+++ b\n@@ ... @@\n-old\n+new",
        rationale="Fix typo in heading",
    )
    proposals_dir = tmp_path / ".proposals"
    files = list(proposals_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "Fix typo" in content
    assert "wiki/topics/test.md" in content
    assert "saved to" in out
```

**Step 2:** Run — FAIL.

**Step 3:** Add to `india_mcp/server.py`:

```python
import uuid
from datetime import datetime

def _propose_edit_impl(path: str, diff: str, rationale: str) -> str:
    """Write an edit proposal for human review. No file is modified directly."""
    proposals = CORPUS_ROOT / ".proposals"
    proposals.mkdir(exist_ok=True)
    pid = uuid.uuid4().hex[:8]
    ts = datetime.utcnow().isoformat(timespec="seconds")
    proposal = proposals / f"{ts.replace(':', '-')}_{pid}.md"
    proposal.write_text(
        f"# Proposed edit\n\n"
        f"- **Path:** `{path}`\n"
        f"- **Created:** {ts}Z\n"
        f"- **Rationale:** {rationale}\n\n"
        f"## Diff\n\n```diff\n{diff}\n```\n",
        encoding="utf-8",
    )
    return f"saved to .proposals/{proposal.name}"

@mcp.tool()
def propose_edit(path: str, diff: str, rationale: str) -> str:
    """File a structured edit proposal under .proposals/ for the user to review.
    Replaces silent writes. The user converts approved proposals into PRs."""
    return _propose_edit_impl(path, diff, rationale)
```

**Step 4:** Update `.gitignore`:

```bash
grep -q "^\.proposals/" .gitignore || echo ".proposals/" >> .gitignore
```

**Step 5:** Optionally remove the existing `write_page` tool (or mark deprecated in its docstring). Leave it for one cycle to avoid breaking anyone testing.

**Step 6:** Tests PASS.

**Step 7:** Commit.

```bash
git add india_mcp/server.py tests/test_mcp_propose_edit.py .gitignore
git commit -m "feat(mcp): add propose_edit tool (replaces silent writes)"
```

---

## Task 17: Backlinks generator

**Files:**
- Create: `scripts/build_backlinks.py`
- Test: `tests/test_backlinks.py`

**Step 1: Test** (using a tmp corpus):

```python
from pathlib import Path
import subprocess

def test_backlinks_populates_cross_references(tmp_path, monkeypatch):
    # Set up minimal corpus
    (tmp_path / "wiki/topics").mkdir(parents=True)
    (tmp_path / "wiki/topics/murder.md").write_text(
        "# Murder\n\n## Source Sections\n- [BNS § 103](../../acts/bns/sections/103.md)\n"
    )
    (tmp_path / "acts/bns/sections").mkdir(parents=True)
    (tmp_path / "acts/bns/sections/103.md").write_text(
        "---\nact: bns\nsection: '103'\nheading: x\nstatus: in_force\n"
        "source_url: https://x\nsource_hash: y\nsynced: 2026-04-19\n---\n\n"
        "# § 103\n\n## Text\nfoo\n\n## Cross-references\n_(none yet)_\n"
    )
    import sys
    monkeypatch.setenv("LEX_INDIA_ROOT", str(tmp_path))
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "scripts/build_backlinks.py")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    section = (tmp_path / "acts/bns/sections/103.md").read_text()
    assert "wiki/topics/murder.md" in section
```

**Step 2:** Run — FAIL.

**Step 3: Implement** — `scripts/build_backlinks.py`:

```python
"""Scan all topic pages for links to acts/, write backlinks into each section's
## Cross-references block. Idempotent."""
import os
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(os.environ.get("LEX_INDIA_ROOT", Path(__file__).parent.parent))
LINK_RE = re.compile(r"\]\(([^)]*acts/([^/]+)/sections/([^)]+\.md))\)")

def main():
    backlinks: dict[Path, list[Path]] = defaultdict(list)
    for topic in (REPO / "wiki" / "topics").rglob("*.md"):
        for m in LINK_RE.finditer(topic.read_text(encoding="utf-8")):
            target = (topic.parent / m.group(1)).resolve()
            if target.exists():
                backlinks[target].append(topic)

    for section_path, sources in backlinks.items():
        text = section_path.read_text(encoding="utf-8")
        block_lines = ["## Cross-references"]
        for src in sorted(set(sources)):
            rel = os.path.relpath(src, section_path.parent)
            block_lines.append(f"- Topic: [{src.stem}]({rel})")
        block = "\n".join(block_lines) + "\n"
        # Replace existing ## Cross-references block
        new = re.sub(
            r"## Cross-references.*?(?=^## |\Z)",
            block + "\n",
            text,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )
        section_path.write_text(new, encoding="utf-8")
    print(f"✓ updated cross-references for {len(backlinks)} sections")

if __name__ == "__main__":
    main()
```

**Step 4:** Test PASS.

**Step 5:** Commit.

```bash
git add scripts/build_backlinks.py tests/test_backlinks.py
git commit -m "feat: add backlinks generator (topics → act sections)"
```

---

## Task 18: Sample cross-link from 1 topic page (proof)

**Files:**
- Modify: `wiki/topics/murder.md` (or another topic with clear act mapping)

**Step 1:** Pick one well-defined topic with sections you know exist post-scrape (e.g. `murder.md` → BNS §§ 101–105).

**Step 2:** Add a `## Source Sections` block before `## Definition` or near the top:

```markdown
## Source Sections
- [BNS § 101 — culpable homicide](../../acts/bns/sections/101.md)
- [BNS § 103 — punishment for murder](../../acts/bns/sections/103.md)
- [BNS § 105 — culpable homicide not amounting to murder](../../acts/bns/sections/105.md)
```

**Step 3:** Run `python scripts/build_backlinks.py` to populate the reverse links.

**Step 4:** Run `python scripts/validate.py` — expect ✓.

**Step 5:** Commit.

```bash
git add wiki/topics/murder.md acts/bns/sections/
git commit -m "docs: cross-link murder topic to BNS sections (sample)"
```

---

## Task 19: Update `validate.yml` to also run backlinks check

**Files:**
- Modify: `.github/workflows/validate.yml`

**Step 1:** Add a step that runs backlinks then verifies no diff (CI fails if a contributor forgot to regenerate):

```yaml
      - run: python scripts/build_backlinks.py
      - run: |
          if ! git diff --quiet; then
            echo "::error::Backlinks out of date. Run scripts/build_backlinks.py and commit."
            git diff
            exit 1
          fi
```

**Step 2:** Commit + push, verify CI green on a draft PR.

```bash
git add .github/workflows/validate.yml
git commit -m "ci: enforce backlinks freshness in validate workflow"
```

---

## Task 20: Daily auto-PR scrape workflow

**Files:**
- Create: `.github/workflows/scrape-acts.yml`

**Step 1: Implement:**

```yaml
name: scrape-acts
on:
  schedule:
    - cron: "17 3 * * *"   # daily 03:17 UTC
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python scripts/scrape_act.py scrape all
      - run: python scripts/build_backlinks.py
      - uses: peter-evans/create-pull-request@v6
        with:
          branch: auto-scrape/${{ github.run_id }}
          commit-message: "data: auto-scrape detected upstream changes"
          title: "Auto-scrape: upstream act changes detected"
          body: |
            Automated scrape detected differences from canonical sources.

            Review the diff carefully — legal text changes have real consequences.
            Append a corresponding entry to `log.md` before merging.
          labels: auto-scrape
```

**Step 2:** Commit. (Test by running `workflow_dispatch` manually from GitHub UI after pushing.)

```bash
git add .github/workflows/scrape-acts.yml
git commit -m "ci: daily auto-PR scrape for upstream act changes"
```

---

## Task 21: Update CONTRIBUTING.md with agent-PR protocol

**Files:**
- Modify: `CONTRIBUTING.md`

**Step 1:** Read existing `CONTRIBUTING.md`.

**Step 2:** Append (or insert near the top) a section:

```markdown
## Contribution by AI agents

lex-india is designed to be edited by both humans and AI agents.

If you are an AI agent (or are using one to draft a PR):

1. Use the `propose_edit` MCP tool, **not** silent writes. Proposals land
   in `.proposals/` for your operator to review before commit.
2. Cite the source URL for any factual change to an act or topic.
3. Keep diffs focused — one concern per PR.
4. Append an entry to `log.md` describing what you changed and why.
5. CI runs `scripts/validate.py` and `scripts/build_backlinks.py` on every PR.
   Make sure both pass locally before pushing.

If you are the human operator: review proposals as you would a junior
contributor's patch. The agent does the typing; you carry the legal
responsibility for what gets merged.
```

**Step 3:** Commit.

```bash
git add CONTRIBUTING.md
git commit -m "docs: document AI-agent contribution protocol"
```

---

## Task 22: PR template

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

**Step 1: Implement:**

```markdown
### Summary
<!-- 1-2 sentences. What changed and why. -->

### Type
- [ ] Bug fix
- [ ] New topic / section
- [ ] Schema or tooling change
- [ ] Auto-scrape (from CI cron)
- [ ] Other

### Checklist
- [ ] Cited official source for any legal text change
- [ ] Linked from a relevant `INDEX.md` (where applicable)
- [ ] Frontmatter validates (`python scripts/validate.py`)
- [ ] Backlinks regenerated (`python scripts/build_backlinks.py`)
- [ ] Appended an entry to `log.md`
- [ ] Drafted by an AI agent? Note which model + version.
```

**Step 2:** Commit.

```bash
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "ci: add PR template with citation + log.md checklist"
```

---

## Task 23: README refresh

**Files:**
- Modify: `README.md`

**Step 1:** Update positioning sentence near the top to reflect LLM-wiki framing:

> "Indian law as a navigable wiki for AI agents — bare acts, topic explainers, and cross-references in markdown, served via MCP."

**Step 2:** Add an `acts/` row to the structure section:

```markdown
| `acts/`  | Full text of foundational Indian acts, section per file (Phase 1: BNS, BNSS, BSA, Contract Act, IBC) |
| `wiki/`  | Topic explainers, transitions, indices                                                                |
```

**Step 3:** Add a "Quick start for agents" snippet showing the new MCP tools:

````markdown
## Quick start (MCP)

```jsonc
// Claude / Cursor MCP config
"lex-india": {
  "command": "python",
  "args": ["/path/to/lex-india/india_mcp/server.py"]
}
```

Tools your agent gets:
- `search(query)` — full-text across the corpus
- `read(path)` — fetch a specific markdown file
- `get_section(act, section)` — typed section fetch (e.g. `("bns", "103")`)
- `get_index(scope)` — fetch an INDEX.md (`"wiki"`, `"acts/bns"`, …)
- `propose_edit(path, diff, rationale)` — file a PR-ready proposal
````

**Step 4:** Commit.

```bash
git add README.md
git commit -m "docs: refresh README for LLM-wiki framing + acts/ + new MCP tools"
```

---

## Task 24: Final verification

**Step 1:** From a clean checkout, run the whole gauntlet:

```bash
pip install -r requirements.txt
pytest -q
python scripts/validate.py
python scripts/build_backlinks.py
git diff --quiet || { echo "Backlinks out of date"; exit 1; }
```

Expected: all green.

**Step 2:** Spot-check the MCP server boots:

```bash
python india_mcp/server.py --help 2>&1 | head -5
```

(or whichever invocation `mcp[cli]` exposes)

**Step 3:** Update `log.md` with a final Phase 1 closeout entry:

```markdown
## 2026-04-19 — Phase 1 complete

- All 5 acts ingested and validated
- MCP exposes `get_section`, `get_index`, `propose_edit`
- Daily auto-PR cron live
- Backlinks generator integrated into CI
```

**Step 4:** Commit + tag.

```bash
git add log.md
git commit -m "docs: close out Phase 1"
git tag -a v0.1.0-phase1 -m "Phase 1 — depth: 5 foundational acts ingested"
```

---

## Done criteria for Phase 1

- ✅ `acts/{bns,bnss,bsa,contract-act,ibc}/sections/*.md` all present and validate
- ✅ Each act has `INDEX.md` and `meta.yaml`
- ✅ Pytest green
- ✅ `scripts/validate.py` green on a fresh clone
- ✅ MCP exposes `get_section`, `get_index`, `propose_edit`
- ✅ Daily auto-scrape workflow live (manually triggerable via `workflow_dispatch`)
- ✅ Backlinks check enforced in CI
- ✅ At least 1 topic page (`murder.md`) cross-links to act sections, with reverse links populated
- ✅ `log.md`, updated `CONTRIBUTING.md`, PR template, refreshed `README.md` all committed
- ✅ Tag `v0.1.0-phase1`

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| indiacode HTML structure varies per act | Per-act fixtures + selector overrides; manual fallback flag |
| Old acts (Contract Act 1872) have repealed sections / odd numbering | `status: needs_manual_review` + human cleanup; CI flags but doesn't block all |
| Auto-PR floods on noisy upstream | `peter-evans/create-pull-request` deduplicates by branch name; review before merge |
| Schema drift across phases | Pydantic models are single source of truth; bump version in `models.py` if breaking |
| Section number collisions across acts | Filename = section ID only; act is part of path. No global namespace. |

---

## Deferred to later phases (do NOT do now)

- Concept pages (mens rea, jurisdiction, etc.) — Phase 2
- IPC↔BNS / CrPC↔BNSS full transition tables — Phase 2
- `related(path)` / `recent_changes()` MCP tools — Phase 3
- Trusted-contributor bot tier — Phase 4
- Case law layer (Indian Kanoon) — out of scope
- Embeddings / vector search — explicitly rejected
