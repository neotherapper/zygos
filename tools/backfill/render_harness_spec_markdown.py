#!/usr/bin/env python3
"""
render_harness_spec_markdown.py — the forward direction.

Copied as a literal transcription of the fixed mapping in
zygos-curation/agents/curator/skills/fidelity-review/SKILL.md Step 8 (lines 75-106):
frontmatter field order `name → embodiment`, body section order and exact heading
text per the property→heading table.

Input is a JSON object with the exact keys produced by
parse_harness_spec_markdown.py (PascalCase entity property names). Output is a
markdown string in the byte shape of docs/research/_template.md.
"""

import json
import sys

# frontmatter field order (render's Step 8 line 79-87), and how each is derived
FRONTMATTER_ORDER = [
    ("name", "Slug"),
    ("title", "Title"),
    ("url", "Url"),
    ("artifact_url", "ArtifactUrl"),
    ("commit", "Commit"),
    ("language", "Language"),
    ("kind", "Kind"),
    ("license", "License"),
    ("status", "ProjectStatus"),
    ("lifecycle", "Lifecycle"),
    ("provenance", "Provenance"),
    ("verified_at", "VerifiedAt"),
    ("axis", "Axis"),
    ("primitives", "Primitives"),
    ("embodiment", "Embodiment"),
]

# body heading order + exact heading text (render's Step 8 line 92-106)
PROPERTY_TO_BODY_HEADING = {
    "Philosophy": "Philosophy",
    "PrimitivesSection": "Primitives",
    "Loop": "Loop",
    "Boundaries": "Boundaries",
    "Verification": "Verification strategy",
    "WhichAxis": "Which axis",
    "Economics": "Economics",
    "Tradeoffs": "Tradeoffs",
    "WhatToSteal": "What to steal",
    "WhatNotTo": "What not to",
    "EmbodimentSection": "Embodiment",
    "Limits": "Limits of this spec",
    "Sources": "Sources",
}
BODY_ORDER = list(PROPERTY_TO_BODY_HEADING.keys())

# enum PascalCase (entity) -> kebab (frontmatter), the render table's rule
ENUM_TO_KEBAB = {
    "AgentHarness": "agent-harness",
    "AgentSubstrate": "agent-substrate",
    "InferenceParadigm": "inference-paradigm",
    "Current": "current",
    "VersionChanging": "version-changing",
    "Retired": "retired",
    "Primary": "primary",
    "Secondary": "secondary",
    "Relayed": "relayed",
    "None": "none",
    "Partial": "partial",
    "Full": "full",
}


def enum_to_kebab(s):
    return ENUM_TO_KEBAB.get(s, s)


def _fmt_list(v):
    if not isinstance(v, list):
        return str(v)
    return "[" + ", ".join(str(x) for x in v) + "]"


def render(spec):
    """spec: dict with PascalCase entity property keys. Returns markdown string."""
    lines = ["---"]
    for fm_key, prop in FRONTMATTER_ORDER:
        v = spec.get(prop)
        if v is None:
            lines.append(f"{fm_key}:")
            continue
        if prop in ("Axis", "Primitives"):
            lines.append(f"{fm_key}: {_fmt_list(v)}")
        elif prop in ("Kind", "Lifecycle", "Provenance", "Embodiment"):
            lines.append(f"{fm_key}: {enum_to_kebab(str(v))}")
        elif fm_key == "title" and not str(v).startswith('"'):
            lines.append(f"{fm_key}: \"{v}\"")
        else:
            lines.append(f"{fm_key}: {v}")
    lines.append("---")
    lines.append("")
    slug = spec.get("Slug") or "name"
    lines.append(f"# {spec.get('Title') or ''}")
    lines.append("")
    for prop in BODY_ORDER:
        heading = PROPERTY_TO_BODY_HEADING[prop]
        body = spec.get(prop) or ""
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(body)
        lines.append("")
    # remove the trailing blank added after the last section
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2:
        print("usage: render_harness_spec_markdown.py <spec.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        spec = json.load(f)
    sys.stdout.write(render(spec))


if __name__ == "__main__":
    main()