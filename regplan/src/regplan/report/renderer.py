"""Jinja2 memo renderer — driven entirely by the JSON result file."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from regplan.report.serializer import deserialise

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_memo(result_json_path: Path, out_path: Path) -> None:
    """Render the Markdown memo from *result_json_path* and write to *out_path*."""
    result = deserialise(result_json_path)
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    template = env.get_template("memo.md.j2")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template.render(result=result), encoding="utf-8")
