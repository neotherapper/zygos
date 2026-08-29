#!/usr/bin/env python3
"""
parse_harness_spec_markdown.py — inverse of render_harness_spec_markdown.

Reads a zygos harness-spec markdown file (docs/research/harnesses/<slug>.md shape,
per docs/research/_template.md) and emits a JSON object whose keys are the
PascalCase bound-action input parameter names from zygos-commons/specs/model.csdl.xml,
ready for POST /tdata/HarnessSpecs('<id>')/Zygos.<action>.

The mapping from frontmatter field / body heading to PascalCase entity property is
the *inverse* of the fixed mapping documented in
zygos-curation/agents/curator/skills/fidelity-review/SKILL.md Step 8 (lines 79-106).
See 2026-08-28-backfill-phase1-specs.md Task 1 for the design rationale.
"""

import datetime
import json
import re
import sys
import yaml

# markdown heading text -> entity PascalCase property (inverse of the render table)
BODY_HEADING_TO_PROPERTY = {
    "Philosophy": "Philosophy",
    "Primitives": "PrimitivesSection",
    "Loop": "Loop",
    "Boundaries": "Boundaries",
    "Verification strategy": "Verification",
    "Which axis": "WhichAxis",
    "Economics": "Economics",
    "Tradeoffs": "Tradeoffs",
    "What to steal": "WhatToSteal",
    "What not to": "WhatNotTo",
    "Embodiment": "EmbodimentSection",
    "Limits of this spec": "Limits",
    "Sources": "Sources",
}
PROPERTY_TO_BODY_HEADING = {v: k for k, v in BODY_HEADING_TO_PROPERTY.items()}

# frontmatter field -> entity PascalCase property
FRONTMATTER_TO_PROPERTY = {
    "name": "Slug",
    "title": "Title",
    "url": "Url",
    "artifact_url": "ArtifactUrl",
    "commit": "Commit",
    "language": "Language",
    "kind": "Kind",
    "license": "License",
    "status": "ProjectStatus",
    "lifecycle": "Lifecycle",
    "provenance": "Provenance",
    "verified_at": "VerifiedAt",
    "axis": "Axis",
    "primitives": "Primitives",
    "embodiment": "Embodiment",
}

# enum kebab-case (frontmatter) -> PascalCase (entity), per the render table's
# enum->kebab mapping inverted. These are the exact enum values.
KEBAB_TO_ENUM = {
    # HarnessKind
    "agent-harness": "AgentHarness",
    "agent-substrate": "AgentSubstrate",
    "inference-paradigm": "InferenceParadigm",
    # Lifecycle
    "current": "Current",
    "version-changing": "VersionChanging",
    "retired": "Retired",
    # Provenance
    "primary": "Primary",
    "secondary": "Secondary",
    "relayed": "Relayed",
    # Embodiment
    "none": "None",
    "partial": "Partial",
    "full": "Full",
}


def _strip_inline_comments(text):
    """Remove YAML inline comments while preserving bracket/quote contents.

    A comment starts at a ' #' (space followed by hash) that is not inside a
    running flow collection [ ] { } or a double/single-quoted string. This is the
    minimal handling needed for both exo.md and temper.md, whose frontmatter
    comments are always space-#-prefixed after the value.
    """
    out = []
    depth = 0  # flow-collection nesting for [ ] and { }
    in_dq = in_sq = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_dq:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_dq = False
            i += 1
            continue
        if in_sq:
            out.append(c)
            if c == "'":
                in_sq = False
            i += 1
            continue
        if c == '"':
            in_dq = True
            out.append(c)
            i += 1
            continue
        if c == "'":
            in_sq = True
            out.append(c)
            i += 1
            continue
        if c in "[{":
            depth += 1
            out.append(c)
            i += 1
            continue
        if c in "]}":
            depth = max(0, depth - 1)
            out.append(c)
            i += 1
            continue
        # a comment start: ' #' at depth 0 and not inside quotes
        if c == "#" and i > 0 and text[i - 1] == " " and depth == 0:
            # strip to end of line (we are given a single logical line)
            break
        out.append(c)
        i += 1
    return "".join(out).rstrip()


def parse_markdown(md_text):
    """Return the JSON-serializable dict for one HarnessSpec."""
    # --- split frontmatter ---
    if not md_text.startswith("---\n"):
        raise ValueError("markdown must start with frontmatter '---\\n'")
    after_fm = md_text.split("\n---\n", 1)
    if len(after_fm) != 2:
        raise ValueError("could not split frontmatter (expected a '\\n---\\n' terminator)")
    fm_text, body_text = after_fm
    fm_lines = fm_text.split("\n")
    # drop the leading '---'
    fm_lines = fm_lines[1:] if fm_lines and fm_lines[0] == "---" else fm_lines

    # strip inline comments line-by-line (a YAML flow scalar may span lines, but
    # in both target files each frontmatter field is on one line — safe here)
    cleaned_fm = []
    for ln in fm_lines:
        if ln.strip() == "" or ln.strip().startswith("#"):
            continue
        cleaned_fm.append(_strip_inline_comments(ln))
    fm_yaml = "\n".join(cleaned_fm)

    fm = yaml.safe_load(fm_yaml) or {}
    if not isinstance(fm, dict):
        raise ValueError("frontmatter did not parse to a mapping")

    result = {}
    for fk, prop in FRONTMATTER_TO_PROPERTY.items():
        if fk in fm:
            val = fm[fk]
            # list fields pass through
            if isinstance(val, list):
                result[prop] = val
                continue
            # enum kebab -> PascalCase
            if prop in ("Kind", "Lifecycle", "Provenance", "Embodiment"):
                result[prop] = KEBAB_TO_ENUM.get(str(val), str(val))
                continue
            # serialize dates (PyYAML parses unquoted dates to date objects)
            if isinstance(val, (datetime.date, datetime.datetime)):
                result[prop] = val.isoformat()
                continue
            result[prop] = val

    # --- body sections ---
    # The body is: after frontmatter there is a leading blank line, then `# <name>`
    # (H1), then H2 sections. Some specs embed H3/H4 headings inside sections — the
    # separator is only `^## ` at column 0.
    body = body_text
    # strip one leading blank line after the frontmatter terminator
    body = body.lstrip("\n")
    # skip the H1 title line (level-1 heading); keep everything after it.
    # Match only the single heading line — `re.DOTALL` on a greedy `.*` would
    # swallow the whole body; anchor `.*` to a single line with `[^\n]*`.
    title_match = re.match(r"#[ \t]*[^\n]*(?:\n|$)", body)
    if title_match:
        body = body[title_match.end():]
    body = body.lstrip("\n")

    # split on canonical top-level H2 headings only — NOT any `## `. A spec may
    # embed `## <subsection>` headings inside a section (rlm.md Boundaries has
    # `## Trusted vs swappable`, `## State inventory`); those are content of the
    # enclosing canonical section and must not trigger a split. Build the split
    # regex from the known heading set so unknown headings stay inside a section.
    known_headings = sorted(BODY_HEADING_TO_PROPERTY.keys(), key=len, reverse=True)
    split_re = re.compile(r"\n(?=## (?:%s)\n)" % "|".join(re.escape(h) for h in known_headings))
    parts = split_re.split(body)
    for part in parts:
        part = part.strip("\n")
        if not part.strip():
            continue
        m = re.match(r"## ([^\n]+)[ \t]*(?:\n(.*))?$", part, re.DOTALL)
        if not m:
            raise ValueError(f"unparseable body block: {part[:80]!r}")
        heading = m.group(1).strip()
        content = (m.group(2) or "").strip("\n")
        if heading not in BODY_HEADING_TO_PROPERTY:
            raise ValueError(f"unknown heading: ## {heading}")
        result[BODY_HEADING_TO_PROPERTY[heading]] = content

    return result


def main():
    if len(sys.argv) != 2:
        print("usage: parse_harness_spec_markdown.py <spec.md>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        md_text = f.read()
    result = parse_markdown(md_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()