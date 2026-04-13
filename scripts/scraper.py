import re
import time
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import date

INDIACODE_BASE = "https://indiacode.nic.in"
ACTS_DIR = Path("acts")
RATE_LIMIT_SECONDS = 2  # respectful crawl

CATEGORY_MAP = {
    "criminal": ["penal", "nyaya sanhita", "crpc", "nagarik suraksha"],
    "civil": ["civil procedure", "specific relief", "limitation"],
    "constitutional": ["constitution", "citizenship", "representation"],
    "commercial": ["companies", "partnership", "insolvency", "contract"],
    "labour": ["labour", "industrial", "workmen", "factories"],
    "tax": ["income tax", "gst", "customs", "excise"],
    "family": ["hindu", "marriage", "adoption", "guardianship"],
    "property": ["transfer of property", "registration", "land acquisition"],
}


def slugify(title: str) -> str:
    """Convert act title to filesystem slug. 'The Indian Penal Code, 1860' -> 'ipc-1860'"""
    # Extract year
    year_match = re.search(r'\b(\d{4})\b', title)
    year = year_match.group(1) if year_match else ""

    # Known abbreviations
    abbrevs = {
        "Indian Penal Code": "ipc",
        "Bharatiya Nyaya Sanhita": "bns",
        "Code of Criminal Procedure": "crpc",
        "Bharatiya Nagarik Suraksha Sanhita": "bnss",
        "Indian Evidence Act": "iea",
        "Bharatiya Sakshya Adhiniyam": "bsa",
        "Companies Act": "companies-act",
        "Income Tax Act": "income-tax-act",
        "Constitution of India": "constitution",
    }
    for key, abbrev in abbrevs.items():
        if key.lower() in title.lower():
            return f"{abbrev}-{year}" if year else abbrev

    # Generic: lowercase words, drop "the", join with hyphens
    words = re.sub(r'[^\w\s]', '', title.lower()).split()
    words = [w for w in words if w not in ("the", "a", "an", "of", "and")]
    slug = "-".join(words[:4])
    return f"{slug}-{year}" if year else slug


def build_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for key in ["title", "short", "year", "ministry", "status", "supersedes",
                "last_amended", "source_url"]:
        if key in meta and meta[key]:
            val = meta[key]
            if isinstance(val, str) and any(c in val for c in ':,#&'):
                val = f'"{val}"'
            lines.append(f"{key}: {val}")
    lines.append("---\n")
    return "\n".join(lines)


def infer_category(title: str) -> str:
    title_lower = title.lower()
    for category, keywords in CATEGORY_MAP.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "misc"


def parse_act_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    # Try multiple title selectors (indiacode.nic.in uses h1.act-title or h1)
    title_el = (soup.find("h1", class_="act-title") or
                soup.find("h1") or
                soup.find("title"))
    title = title_el.get_text(strip=True) if title_el else "Unknown"

    # Extract body content
    body_el = (soup.find("div", class_="act-content") or
               soup.find("div", id="content") or
               soup.find("body"))
    body = body_el.get_text(separator="\n", strip=True) if body_el else ""

    return {"title": title, "body": body}


def scrape_act(url: str, client: httpx.Client) -> dict | None:
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        return parse_act_html(resp.text)
    except Exception as e:
        print(f"  ERROR: {url}: {e}")
        return None


def save_act(slug: str, category: str, meta: dict, body: str):
    category_dir = ACTS_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)
    path = category_dir / f"{slug}.md"
    frontmatter = build_frontmatter(meta)
    path.write_text(frontmatter + "\n" + body, encoding="utf-8")
    return path


def fetch_act_list(client: httpx.Client) -> list[dict]:
    """Fetch the full list of Central Acts from indiacode.nic.in"""
    acts = []
    page = 0
    while True:
        url = f"{INDIACODE_BASE}/simple-search?query=&filter_field_1=type&filter_type_1=equals&filter_value_1=Acts&rpp=100&sort_by=dc.date.issued_dt&order=ASC&start={page * 100}"
        resp = client.get(url, timeout=30)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("td.artifact-title a")
        if not items:
            break
        for item in items:
            acts.append({
                "title": item.get_text(strip=True),
                "url": INDIACODE_BASE + item["href"],
            })
        page += 1
        time.sleep(RATE_LIMIT_SECONDS)
    return acts


def run_scraper(limit: int = None):
    """Main entry point. limit=N for testing with first N acts."""
    with httpx.Client(headers={"User-Agent": "lex-india-bot/1.0 (github.com/Manas-Taneja/lex-india)"}) as client:
        print("Fetching act list...")
        acts = fetch_act_list(client)
        if limit:
            acts = acts[:limit]
        print(f"Found {len(acts)} acts. Scraping...")

        for i, act in enumerate(acts):
            parsed = scrape_act(act["url"], client)
            if not parsed:
                continue
            meta = {
                "title": parsed["title"],
                "year": re.search(r'\b(\d{4})\b', parsed["title"]) and
                        re.search(r'\b(\d{4})\b', parsed["title"]).group(1),
                "status": "in-force",
                "source_url": act["url"],
                "last_amended": str(date.today()),
            }
            slug = slugify(parsed["title"])
            category = infer_category(parsed["title"])
            path = save_act(slug, category, meta, parsed["body"])
            print(f"  [{i+1}/{len(acts)}] {path}")
            time.sleep(RATE_LIMIT_SECONDS)


if __name__ == "__main__":
    run_scraper()
