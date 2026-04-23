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
