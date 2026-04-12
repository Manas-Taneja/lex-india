import yaml
from pathlib import Path


def load_mappings(yaml_path: Path) -> dict:
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_new_section(data: dict, old_section: str) -> dict | None:
    for mapping in data["mappings"]:
        if mapping["old_section"] == old_section:
            return mapping
    return None


def generate_transition_md(data: dict) -> str:
    meta = data["meta"]
    lines = [
        f"# {meta['old_act']} → {meta['new_act']}",
        f"\n**Source:** {meta['source']}  ",
        f"**Effective:** {meta['effective']}\n",
        "## Section Mapping\n",
        "| IPC Section | IPC Description | BNS Section | BNS Description | Change Note |",
        "|---|---|---|---|---|",
    ]
    for m in data["mappings"]:
        lines.append(
            f"| {m['old_section']} | {m['old_description']} "
            f"| {m['new_section']} | {m['new_description']} "
            f"| {m.get('change_note', '')} |"
        )
    return "\n".join(lines)


def generate_all_transition_files():
    for yaml_path in Path("data").glob("*-to-*.yaml"):
        data = load_mappings(yaml_path)
        md = generate_transition_md(data)
        stem = yaml_path.stem  # e.g. ipc-to-bns-sample -> ipc-to-bns
        out_name = stem.replace("-sample", "")
        out_path = Path("wiki/transitions") / f"{out_name}.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"Written: {out_path}")


if __name__ == "__main__":
    generate_all_transition_files()
