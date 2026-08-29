# Backfill Phase 1 spec findings — Task 1 round-trip tooling

**Date:** 2026-08-28
**Branch:** `research/backfill-phase1-specs`
**Plan:** `docs/superpowers/plans/2026-08-28-backfill-phase1-specs.md`

## What Task 1 produced

Three tools under `tools/backfill/`:

- `parse_harness_spec_markdown.py` — inverse of the Phase 1 `render_harness_spec_markdown`
  mapping (`zygos-curation/agents/curator/skills/fidelity-review/SKILL.md` Step 8). Reads a
  spec markdown file, emits a JSON object with PascalCase `HarnessSpec` bound-action param
  names from `zygos-commons/specs/model.csdl.xml`.
- `render_harness_spec_markdown.py` — forward direction (entity fields → markdown), a literal
  transcription of the Phase 1 Step 8 two-table mapping.
- `round_trip_diff.py` — applies the user-specified whitespace normalization (CRLF→LF,
  trailing-space strip, blank-line collapse) and diffs source vs re-render.

## Round-trip results (measured, not assumed)

| Input | Parse | Render | Round-trip diff | Verdict |
|---|---|---|---|---|
| `docs/research/harnesses/rlm.md` (Phase 1 entity-generated, clean frontmatter) | ok | ok | `NORMALIZED-IDENTICAL` (0 diff lines) | ✅ byte-identical after whitespace normalization |
| `docs/research/harnesses/exo.md` (hand-merged, v1) | ok | ok | DIFF-CONTENT, 19 diff lines across 337 source + 337 rendered lines | ⚠️ comment-only |
| `docs/research/harnesses/temper.md` (hand-merged, v1) | ok | ok | DIFF-CONTENT, 22 diff lines across 466 source + 466 rendered lines | ⚠️ comment-only |

**Key result:** line counts are identical (337/337, 466/466) for both hand-merged files. The
*entire* divergence is the inline `# comment` on frontmatter values:

- `exo.md`: `status`, `axis`, `embodiment` lines carry trailing comments (project's own words,
  axis justification, embodiment justification).
- `temper.md`: `kind`, `status`, `axis`, `embodiment` lines carry trailing comments.

There is **no content divergence** — no body section, no frontmatter value, no heading order
drifts.

## Decision (2026-08-28, user-approved)

**Accept the frontmatter-comment drop; document the diff.**

- The entity schema has no per-field comment storage, and the Phase 1 convention
  (`deepseek-harness.md`, `rlm.md`) is comment-free. The re-render therefore cannot be
  byte-identical to the *hand-merged* v1 files, which annotate values inline.
- The substantive justification behind `axis`/`embodiment`/`status` lives in the **body
  sections** (`## Which axis`, `## Embodiment`), which the entity carries and which round-trip
  verbatim. The comment is a redundant pointer, not the substance.
- Round-trip proof for the backfill = **byte-identical after whitespace normalization**
  (on `rlm.md`, evidence the parser/renderer is faithful) **plus a documented one-comment-per-line
  diff** against the v1 hand-merged files (the only non-normalizable difference).

This is recorded in the backfill PR body (Task 5) so a reader knows the re-render is not
byte-identical to `docs/research/harnesses/exo.md`/`temper.md` on `main` *only* because of the
stripped frontmatter comments, and that the axis/enbodiment/status justification is preserved
in the body sections.

## Developer notes

- PyYAML parses unquoted frontmatter dates (`verified_at: 2026-08-27`) to `datetime.date`;
  the parser serializes to ISO string before JSON.
- Inline frontmatter comments are stripped by a small state machine (tracks flow-collection
  depth `[ ] { }` and quote state) so a `#` inside a quoted/bracketed value is not mistaken
  for a comment. No `#` in any existing spec's frontmatter is inside such a region, but the
  guard is cheap and prevents future breakage.
- Body sections are split only on the **canonical known heading set**, not on any `## `.
  Both `exo.md` and `temper.md` live in `docs/research/harnesses/` with body content that
  includes embedded subsection headings (rlm's `## Trusted vs swappable` inside Boundaries,
  exo's `###`-level subsections). Splitting on the known headings keeps those inside their
  enclosing canonical section instead of creating a bogus top-level section.
- The heading-capture regex must be single-line (`[^\n]+`) — a greedy `(.+)` with `re.DOTALL`
  swallows the whole first section body. Caught and fixed during Task 1.