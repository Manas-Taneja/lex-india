"""Add status, department, and enactment_date to all topic page frontmatter."""
import re
from pathlib import Path

TOPICS_DIR = Path(__file__).parent.parent / "wiki" / "topics"

# (status, department, enactment_date)
ENRICHMENT = {
    # Constitutional
    "fundamental-rights":       ("current", "Ministry of Law and Justice", 1950),
    "directive-principles":     ("current", "Ministry of Law and Justice", 1950),
    "constitutional-amendments":("current", "Ministry of Law and Justice", 1950),
    "emergency-provisions":     ("current", "Ministry of Law and Justice", 1950),
    "panchayati-raj":           ("current", "Ministry of Panchayati Raj", 1992),
    # Criminal
    "murder":                   ("current", "Ministry of Home Affairs", 2023),
    "rape":                     ("current", "Ministry of Home Affairs", 2023),
    "theft":                    ("current", "Ministry of Home Affairs", 2023),
    "cheating":                 ("current", "Ministry of Home Affairs", 2023),
    "defamation":               ("current", "Ministry of Home Affairs", 2023),
    "assault":                  ("current", "Ministry of Home Affairs", 2023),
    "kidnapping":               ("current", "Ministry of Home Affairs", 2023),
    "dacoity":                  ("current", "Ministry of Home Affairs", 2023),
    "domestic-violence":        ("current", "Ministry of Women and Child Development", 2005),
    "child-sexual-abuse":       ("current", "Ministry of Women and Child Development", 2012),
    "criminal-conspiracy":      ("current", "Ministry of Home Affairs", 2023),
    "cybercrime":               ("current", "Ministry of Electronics and Information Technology", 2000),
    "corruption":               ("current", "Ministry of Personnel, Public Grievances and Pensions", 2018),
    "drug-offences":            ("current", "Ministry of Finance", 1985),
    "money-laundering":         ("current", "Ministry of Finance", 2002),
    "terror-offences":          ("current", "Ministry of Home Affairs", 2019),
    "atrocities-against-sc-st": ("current", "Ministry of Social Justice and Empowerment", 2015),
    "sexual-harassment-at-work":("current", "Ministry of Women and Child Development", 2013),
    # Procedure
    "bail":                     ("current", "Ministry of Home Affairs", 2023),
    "fir":                      ("current", "Ministry of Home Affairs", 2023),
    "civil-suit-procedure":     ("current", "Ministry of Law and Justice", 1908),
    "trial-procedure":          ("current", "Ministry of Home Affairs", 2023),
    "appeal-and-revision":      ("current", "Ministry of Law and Justice", 1908),
    "evidence-rules":           ("current", "Ministry of Home Affairs", 2023),
    "limitation-period":        ("current", "Ministry of Law and Justice", 1963),
    "arbitration":              ("current", "Ministry of Law and Justice", 1996),
    # Civil
    "specific-performance":     ("current", "Ministry of Law and Justice", 1963),
    "injunction":               ("current", "Ministry of Law and Justice", 1908),
    "tort-negligence":          ("current", "Ministry of Law and Justice", 1908),
    "consumer-rights":          ("current", "Ministry of Consumer Affairs, Food and Public Distribution", 2019),
    "right-to-information":     ("current", "Ministry of Personnel, Public Grievances and Pensions", 2005),
    # Commercial
    "contract":                 ("current", "Ministry of Law and Justice", 1872),
    "company-incorporation":    ("current", "Ministry of Corporate Affairs", 2013),
    "partnership":              ("current", "Ministry of Corporate Affairs", 2008),
    "sale-of-goods":            ("current", "Ministry of Law and Justice", 1930),
    "negotiable-instruments":   ("current", "Ministry of Finance", 1881),
    "insolvency":               ("current", "Ministry of Corporate Affairs", 2016),
    "competition-law":          ("current", "Ministry of Corporate Affairs", 2002),
    "securities-regulation":    ("current", "Ministry of Finance", 1992),
    "foreign-exchange":         ("current", "Ministry of Finance", 1999),
    "insurance":                ("current", "Ministry of Finance", 1938),
    "real-estate-rera":         ("current", "Ministry of Housing and Urban Affairs", 2016),
    # Labour
    "employment-termination":   ("current", "Ministry of Labour and Employment", 1947),
    "minimum-wages":            ("current", "Ministry of Labour and Employment", 1948),
    "provident-fund":           ("current", "Ministry of Labour and Employment", 1952),
    "maternity-benefit":        ("current", "Ministry of Labour and Employment", 1961),
    "factory-safety":           ("current", "Ministry of Labour and Employment", 1948),
    "child-labour":             ("current", "Ministry of Labour and Employment", 1986),
    "contract-labour":          ("current", "Ministry of Labour and Employment", 1970),
    "gratuity":                 ("current", "Ministry of Labour and Employment", 1972),
    # Tax
    "income-tax-return":        ("current", "Ministry of Finance", 1961),
    "gst":                      ("current", "Ministry of Finance", 2017),
    "customs-duty":             ("current", "Ministry of Finance", 1962),
    "tds-tcs":                  ("current", "Ministry of Finance", 1961),
    "capital-gains-tax":        ("current", "Ministry of Finance", 1961),
    # Family
    "divorce":                  ("current", "Ministry of Law and Justice", 1955),
    "marriage-registration":    ("current", "Ministry of Law and Justice", 1955),
    "inheritance-succession":   ("current", "Ministry of Law and Justice", 1956),
    "adoption":                 ("current", "Ministry of Women and Child Development", 2015),
    "maintenance-alimony":      ("current", "Ministry of Law and Justice", 1955),
    "child-custody":            ("current", "Ministry of Law and Justice", 1956),
    "muslim-personal-law":      ("current", "Ministry of Law and Justice", 1937),
    "child-marriage":           ("current", "Ministry of Women and Child Development", 2006),
    # Property
    "property-transfer":        ("current", "Ministry of Law and Justice", 1882),
    "property-registration":    ("current", "Ministry of Law and Justice", 1908),
    "land-acquisition":         ("current", "Ministry of Rural Development", 2013),
    "stamp-duty":               ("current", "Ministry of Finance", 1899),
    # Environmental
    "environmental-clearance":  ("current", "Ministry of Environment, Forest and Climate Change", 1986),
    "forest-rights":            ("current", "Ministry of Tribal Affairs", 2006),
    "wildlife-protection":      ("current", "Ministry of Environment, Forest and Climate Change", 1972),
    "pollution-control":        ("current", "Ministry of Environment, Forest and Climate Change", 1974),
    # IP
    "copyright":                ("current", "Ministry of Commerce and Industry", 1957),
    "patents":                  ("current", "Ministry of Commerce and Industry", 1970),
    "trademarks":               ("current", "Ministry of Commerce and Industry", 1999),
    # Banking
    "banking-regulation":       ("current", "Ministry of Finance", 1949),
    "loan-recovery":            ("current", "Ministry of Finance", 2002),
    # Healthcare
    "abortion-rights":          ("current", "Ministry of Health and Family Welfare", 1971),
    "mental-health-law":        ("current", "Ministry of Health and Family Welfare", 2017),
    "disability-rights":        ("current", "Ministry of Social Justice and Empowerment", 2016),
    # Education
    "right-to-education":       ("current", "Ministry of Education", 2009),
    # Social
    "juvenile-justice":         ("current", "Ministry of Women and Child Development", 2015),
}

def enrich(path: Path, status: str, department: str, enactment_date: int) -> bool:
    text = path.read_text(encoding="utf-8")

    # Skip if already enriched
    if "department:" in text and "enactment_date:" in text:
        return False

    # Find end of frontmatter block
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        print(f"  SKIP (no frontmatter): {path.name}")
        return False

    fm = match.group(1)
    rest = text[match.end():]

    # Add fields before closing ---
    additions = []
    if "status:" not in fm:
        additions.append(f"status: {status}")
    if "department:" not in fm:
        additions.append(f"department: \"{department}\"")
    if "enactment_date:" not in fm:
        additions.append(f"enactment_date: {enactment_date}")

    if not additions:
        return False

    new_text = f"---\n{fm}\n" + "\n".join(additions) + f"\n---\n{rest}"
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    updated = 0
    skipped = 0
    for slug, (status, dept, year) in ENRICHMENT.items():
        path = TOPICS_DIR / f"{slug}.md"
        if not path.exists():
            print(f"  MISSING: {slug}.md")
            continue
        if enrich(path, status, dept, year):
            print(f"  ✓ {slug}")
            updated += 1
        else:
            skipped += 1

    print(f"\nDone: {updated} updated, {skipped} already enriched")


if __name__ == "__main__":
    main()
