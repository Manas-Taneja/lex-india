from io import StringIO
from ruamel.yaml import YAML

yaml = YAML(typ="rt")
yaml.default_flow_style = False
yaml.preserve_quotes = True


def parse(text: str) -> tuple[dict, str]:
    """Split markdown with YAML frontmatter into (dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:].lstrip("\n")
    return dict(yaml.load(fm_text) or {}), body


def dump(fm: dict, body: str) -> str:
    buf = StringIO()
    yaml.dump(fm, buf)
    return f"---\n{buf.getvalue()}---\n\n{body.lstrip()}"
