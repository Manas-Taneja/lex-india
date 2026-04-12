import pytest
import yaml
from pathlib import Path
from scripts.parse_transitions import load_mappings, find_new_section, generate_transition_md

def test_load_mappings_from_yaml():
    data = load_mappings(Path("data/ipc-to-bns-sample.yaml"))
    assert len(data["mappings"]) > 0
    assert data["meta"]["old_act"] == "Indian Penal Code, 1860"

def test_find_new_section():
    data = load_mappings(Path("data/ipc-to-bns-sample.yaml"))
    result = find_new_section(data, "302")
    assert result["new_section"] == "103"
    assert "murder" in result["new_description"].lower()

def test_find_new_section_missing():
    data = load_mappings(Path("data/ipc-to-bns-sample.yaml"))
    result = find_new_section(data, "999")
    assert result is None

def test_generate_transition_md_contains_table():
    data = load_mappings(Path("data/ipc-to-bns-sample.yaml"))
    md = generate_transition_md(data)
    assert "| IPC Section |" in md
    assert "| 302 |" in md
    assert "103" in md
