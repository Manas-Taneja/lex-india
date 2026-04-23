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
