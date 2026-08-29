# zygos Phase 2 — Backfill exo + temper into HarnessSpec entities

> **Scope per user instruction (2026-08-28):** a single PR on one branch
> (`research/backfill-phase1-specs`) creating two new `HarnessSpec` entities from the existing
> hand-merged `exo.md` and `temper.md`. Round-trip target: re-rendered markdown is byte-identical
> to the hand-merged original after stripping normalizeable whitespace (CRLF→LF, trailing whitespace,
> blank-line collapse around headings). Non-whitespace drift is a finding requiring hand resolution.
> Hand-merged files are NOT deleted; `docs/research/README.md` is updated to name both publication
> paths and each one's audit trail. Fidelity review re-fetches the pinned primary sources
> independently — does not inherit findings from the hand-merged original's prior reviews.
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two-track publication gap (hand-merged markdown + entity-backed markdown) by
re-importing `exo.md` and `temper.md` through the `HarnessSpec` pipeline. The proof is byte-identity
after whitespace normalization, because the hand-merged files were authored to satisfy
`docs/research/_template.md` exactly — if the render mapping is faithful, the re-render is
identical. If it isn't, the gap is now visible in a diff.

**Architecture:** No new app code. The Phase 1 `zygos-commons` entity, guard, and Cedar policy
already match the markdown shape (proven by the Phase 1 addendum's DeepSeek Harness and RLM
publications). What doesn't yet exist is the *inverse* of `render_harness_spec_markdown` — a
markdown-to-entity-fields parser that emits a JSON payload equivalent to what Phase 1's
synthesize-harness skill would have produced for these specs. That parser is the load-bearing
artifact this plan builds.

**Tech Stack:** Python 3 (parser + render verifier), Bash (`curl` against Temper OData surface
per `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md`), Markdown (re-rendered output
and rendered diff), Git + GitHub CLI (branch + PR per `docs/research/SKILL.md` §0, §4).

**Spec:** `docs/adrs/0002-temper-backed-curation-pipeline.md` Addendum 2026-08-27 §"Recommendation
on Phase 2".

## Global Constraints

- **Source of truth for entity fields is `docs/research/harnesses/exo.md` and `temper.md` on
  `main` at `42180f2`** — *not* a fresh primary-source read. Per user instruction (2026-08-28):
  re-import from existing markdown, not from re-research.
- **Pinned primary sources are re-fetched only by the fidelity-review step**, per
  `docs/research/SKILL.md` §4 step 2. The hand-merged spec's prior fidelity review
  (`docs/research/harnesses/temper.md` Limits § "This spec went through fidelity review before
  merge") does not exempt this re-import from re-checking — the *check* is what makes it
  faithful, not the inheritance.
- **Two new `HarnessSpec` entities, distinct GUIDs from the Phase 1 entities** — the Phase 1
  entities are deepseek-harness + rlm only (ADR-0002 addendum line 157-158), not exo + temper.
  No prior exo or temper entity exists. Create fresh.
- **The existing hand-merged `docs/research/harnesses/exo.md` and `temper.md` are NOT modified by
  this PR.** Two-track publication state is documented in `docs/research/README.md` per
  ADR-0002 addendum Consequences §"Negative". Deletion is a separate decision; this plan
  surfaces it but does not execute it.
- **The render function Phase 1's fidelity-review SKILL.md Step 8 describes is a forward
  direction (entity → markdown).** This plan builds the *inverse* (markdown → entity fields)
  and verifies by applying the forward direction to its own output and diffing against the
  input. Any non-whitespace diff is a finding, not a "close enough."
- **Bearer key lives in the local environment, not the plan.** The single Phase 1 dev key (set as
  `$ZYGOS_KEY`, per `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md`) is valid against
  the running server (verified 2026-08-28, GET /tdata/HarnessSpecs
  returns 200). All POST/GET calls in this plan reuse that key; do not rotate mid-plan.
- **Both Phase 1 entities (`en-01a014ba...` DeepSeek Harness, `en-01a04501...` RLM) are Published
  and must remain so** — the backfill exercises the same flow as the addendums but does not
  interfere with existing state. Any guard, policy, or schema change that would invalidate the
  Phase 1 entities is a stop-condition, not a fixable finding.

---

### Task 1: Write the markdown → entity parser and verify round-trip on a known-good input

**Files:**
- Create: `tools/backfill/parse_harness_spec_markdown.py` — the inverse of
  `render_harness_spec_markdown`. Reads a spec markdown file, emits a JSON payload with one
  key per `HarnessSpec` bound action input (PascalCase, matching the CSDL parameter names
  in `zygos-commons/specs/model.csdl.xml`).
- Create: `tools/backfill/render_harness_spec_markdown.py` — the forward direction, copied from
  the Phase 1 fidelity-review SKILL.md Step 8's two-table mapping (frontmatter field order +
  body heading text). It is small enough to be a literal transcription.
- Create: `tools/backfill/round_trip_diff.py` — applies render to parse's output, normalizes
  whitespace per the user's instruction (CRLF→LF, trailing whitespace, blank-line collapse
  around headings), diffs against the input.
- Create: `docs/superpowers/plans/2026-08-28-backfill-phase1-specs-findings.md` — Task 1's
  outcome (parser correctness against the two known-good inputs).

**Interfaces:**
- `parse_harness_spec_markdown(md_path) -> dict` — dict keys: `Title`, `Url`, `ArtifactUrl`,
  `Commit`, `Language`, `Kind`, `License`, `ProjectStatus`, `Lifecycle`, `Provenance`,
  `VerifiedAt`, `Slug`, `Philosophy`, `PrimitivesSection`, `Primitives`, `Loop`, `Boundaries`,
  `Verification`, `Axis`, `WhichAxis`, `Economics`, `Tradeoffs`, `WhatToSteal`, `WhatNotTo`,
  `Embodiment`, `EmbodimentSection`, `Limits`, `Sources`. Consumed by Task 2's curl POSTs.
- `render_harness_spec_markdown(spec_dict) -> str` — returns a markdown string in the exact
  byte shape of `_template.md`. Pure function; no I/O.
- `round_trip_diff(input_md, output_md) -> tuple[list[str], str]` — first element is the
  list of post-normalization differences (empty on byte-identity); second is the
  human-readable diff body for the PR comment.

The parser is the load-bearing artifact. Step 1 below inverts the two tables in
`fidelity-review/SKILL.md` §8 verbatim — property names from `model.csdl.xml` map to heading
text from `_template.md`. The trickier cases are markdown structure inside sections (tables,
bold-list paragraphs, the `**The fixed point is a configuration default, not a structural
invariant**` subsection inside exo's Boundaries) — those are preserved as-is in the JSON string
field because the entity doesn't impose structure on long-form prose.

- [ ] **Step 1: Implement `render_harness_spec_markdown.py` from the fidelity-review mapping**

Literal transcription of the two tables in
`zygos-curation/agents/curator/skills/fidelity-review/SKILL.md` lines 75-106. Two functions:
`enum_to_kebab(s)` (handles `AgentHarness`→`agent-harness`, `None`→`none`, etc.) and
`render(spec_dict)`. The spec_dict input uses the exact keys the parser will emit (so the
round-trip is closed under one set of names).

The function takes a flat dict — frontmatter and body fields mixed — and produces a markdown
string with:
- YAML frontmatter in the field order `name → embodiment` (the Phase 1 skill's line 79-87
  order, verbatim)
- `## Philosophy` through `## Sources` body sections, heading text per the property→heading
  table (the Phase 1 skill's line 92-106 order, verbatim)
- `name` derived from `Slug` (which is in turn derived from the filename, *not* a separate
  input — Phase 1 specs use the filename stem as `name`, see `docs/research/_template.md`)

The function emits blank lines per `_template.md`'s exact spacing (one blank between heading
and body, two blanks between sections). This is what the user's whitespace-normalization
constraint is *tolerating* but not *enforcing* — if the function gets the spacing wrong, the
diff shows it and the function is fixed.

- [ ] **Step 2: Implement `parse_harness_spec_markdown.py`**

The parser must be lossy in exactly the same way the render is lossy: a single body field
becomes a single JSON string property. No table-to-structure decoding (the table is just
text inside the section). No bullet-to-list decoding (bullets are just text). The heading
text is the section marker; everything between `## <Heading>` and the next `## <Heading>` (or
EOF) is the section's body.

Frontmatter: standard YAML between the two `---` markers at the top of the file. Use a
real YAML library (`yaml.safe_load`) — hand-rolled YAML parsing is exactly the kind of
"close enough" that introduces silent drift. Frontmatter keys come in the order they appear
in the file; the render function fixes the output order, so input order doesn't matter.

Field-name normalization:
- `name` (frontmatter) → `Slug` (entity, used as the filename stem on re-render)
- `artifact_url` → `ArtifactUrl`
- `status` → `ProjectStatus` (the project's stated maturity, NOT the state-machine `Status` —
  per `fidelity-review/SKILL.md` Step 8 explicit warning)
- `verified_at` → `VerifiedAt`, parsed as ISO date
- `axis` (list) → `Axis` (list)
- `primitives` (list) → `Primitives` (list)
- `embodiment` (string from the enum) → `Embodiment` (enum); the kebab-case → PascalCase
  reverse of the render's enum-to-kebab mapping
- `kind`, `lifecycle`, `provenance` → PascalCase enums via the same reverse mapping

The body section heading text → property name mapping is the inverse of the render's table:
`## Philosophy` → `Philosophy`, `## Primitives` → `PrimitivesSection`, `## Loop` → `Loop`,
... `## Sources` → `Sources`. Heading text match must be exact (whitespace-insensitive at
line ends, but otherwise character-exact) — the `_template.md` headings are the contract.

- [ ] **Step 3: Round-trip test against `exo.md` and `temper.md`**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
python3 tools/backfill/parse_harness_spec_markdown.py docs/research/harnesses/exo.md > /tmp/exo.parsed.json
python3 tools/backfill/parse_harness_spec_markdown.py docs/research/harnesses/temper.md > /tmp/temper.parsed.json
python3 tools/backfill/render_harness_spec_markdown.py /tmp/exo.parsed.json > /tmp/exo.rendered.md
python3 tools/backfill/render_harness_spec_markdown.py /tmp/temper.parsed.json > /tmp/temper.rendered.md
python3 tools/backfill/round_trip_diff.py docs/research/harnesses/exo.md /tmp/exo.rendered.md
python3 tools/backfill/round_trip_diff.py docs/research/harnesses/temper.md /tmp/temper.rendered.md
```

Expected: empty diff list for both. If non-empty, the diff shows *exactly* which lines
drifted, and the bug is in either the parser or the render function, not in the markdown
input — that's the value of having a known-good input.

If the diff is non-empty for *whitespace-only* differences that survive normalization, the
parser/render needs a fix; do not loosen the normalization to mask the bug. The
user's instruction is explicit on what "normalizeable whitespace" means.

- [ ] **Step 4: Commit parser + render + diff tooling**

```bash
cd /Users/georgiospilitsoglou/Developer/projects/zygos
git checkout -b research/backfill-phase1-specs
git add tools/backfill/
git commit -m "backfill: markdown↔entity round-trip tooling with parse, render, diff"
```

- [ ] **Step 5: Write the findings file**

What worked as designed: parser, render, round-trip diffs (or the actual diff content if not
empty). What needed fixing: list each diff class observed and the fix applied, so subsequent
tasks know the parser isn't being assumed correct, it's been measured correct against two
known-good inputs.

---

### Task 2: Backfill exo into a HarnessSpec entity

**Files:**
- Modify: `zygos-commons/specs/model.csdl.xml` only if a field is missing — likely nothing.
- Create: `research/backfill-phase1-specs/notes/exo-entity-spec.json` — the parsed payload
  for exo, kept as a human-readable artifact for the audit trail (Task 6 PR).

**Interfaces:**
- Consumes: the parser output from Task 1 for `docs/research/harnesses/exo.md`.
- Produces: one `HarnessSpec` entity in `Published` state with `fidelity_review_passed: true`,
  carrying every section's text from the source markdown byte-for-byte (after JSON encoding,
  which is the platform's contract — see Task 1's normalization).
- Side-effects: a PR comment on the backfill branch with the fidelity-review verdict.

- [ ] **Step 1: Create the entity**

```bash
curl -sS -X POST http://127.0.0.1:3467/tdata/HarnessSpecs \
  -H "Authorization: Bearer $ZYGOS_KEY" \
  -H "X-Temper-Principal-Kind: agent" \
  -H "X-Tenant-Id: default" \
  -H "Content-Type: application/json" \
  -d '{"Slug": "exo"}'
```

Expected: 201 with a new GUID. Capture the GUID as `exo_id`. Confirm `Status: "Draft"` and
no `has_*` flags set true.

- [ ] **Step 2: SetIdentity**

POST `/tdata/HarnessSpecs('<exo_id>')/Zygos.SetIdentity` with the frontmatter identity fields
from the parser output (Title, Url, ArtifactUrl, Commit, Language, Kind, License,
ProjectStatus, Lifecycle, Provenance, VerifiedAt). Expected: 200, `has_identity: true`.

- [ ] **Step 3: Write each section in `Write*` order**

Per `model.csdl.xml`'s action list, with body content from the parser output:
`WritePhilosophy` → `WritePrimitivesSection` (also carries `Primitives` list) → `WriteLoop`
→ `WriteBoundaries` → `WriteVerification` → `SetAxis` (carries `Axis` + `WhichAxis`) →
`WriteEconomics` → `WriteTradeoffs` → `WriteWhatToSteal` → `WriteWhatNotTo` →
`SetEmbodiment` (carries `Embodiment` + `EmbodimentSection`) → `WriteLimits` → `WriteSources`.

Each POST gets the body parameter named exactly per the CSDL parameter (PascalCase, no
renaming). Use a shell loop keyed off the parser output JSON, or a small Python script that
POSTs each call. The Phase 1 fidelity-review SKILL.md §16-21 documents the auth pattern:
`Authorization: Bearer ...`, `X-Temper-Principal-Kind: agent`, `Content-Type: application/json`.

Verify after each POST that the corresponding `has_*` flag flipped true via a GET. If a
flag stays false, the POST returned 200 but silently no-op'd — that's the §21 platform
finding from the addendum. Re-POST with the CSDL PascalCase param name, NOT the property
name (the parser already does this; if it doesn't, fix the parser and re-run from Task 1).

- [ ] **Step 4: SubmitForReview**

POST `/tdata/HarnessSpecs('<exo_id>')/Zygos.SubmitForReview` with empty body.

Expected: 200, `Status: "UnderReview"`. If the guard rejects, the response names which
`has_*` flag is false — fix that section (the parser missed something) and re-write that
section before re-submitting. Do not bypass the guard; the guard existing is the load-bearing
artifact of Phase 1.

- [ ] **Step 5: Independent fidelity review (adversarial, re-fetching pinned sources)**

Per `docs/research/SKILL.md` §4. The reviewer has not seen this draft; its only inputs are
the published entity + the pinned primary sources at `exoharness/exo@5bc77ce7c7a2921794083d58c926cf721c14bf8a`.

Three checks:
1. Every direct quote in `Philosophy`, `Loop`, `Boundaries`, `Verification`, `Tradeoffs`
   resolves verbatim against the source file at the pinned SHA. Use `curl` against
   `https://raw.githubusercontent.com/exoharness/exo/5bc77ce7c7a2921794083d58c926cf721c14bf8a/<path>`.
2. Every non-quoted factual claim (count of primitives, the 8x4 state inventory, the
   in-process vs cross-process blast radius argument, the Appendix documentation references)
   is re-checked against the relevant source section.
3. The `Limits` section's claims about what wasn't read are spot-checked. Specifically:
   the "181 ADR files under docs/adrs/" claim in `temper.md` does NOT apply to exo, but
   exo's own `Limits` section has concrete "fetched but not read" lines like
   `exoharness/docs/sandbox-snapshots.md` — re-confirm those files exist at the pinned SHA
   and that the spec's claim they exist is accurate. The README/RSI contradiction (cloning
   capability vs SELF-CONTROL §7 sketch) is a known carve-out for exo — re-check it didn't
   resolve silently in either direction since the original write.

- [ ] **Step 6: Record the verdict**

If pass:
```bash
curl -sS -X POST "http://127.0.0.1:3467/tdata/HarnessSpecs('<exo_id>')/Zygos.RecordFidelityReviewPassed" \
  -H "Authorization: Bearer $ZYGOS_KEY" \
  -H "X-Temper-Principal-Kind: agent" \
  -H "X-Temper-Agent-Type: reviewer" \
  -H "X-Tenant-Id: default" \
  -H "Content-Type: application/json" \
  -d '{"FidelityFindings": "<one finding per line, including 0-finding PASS verdicts>"}'
```

If fail:
```bash
curl -sS -X POST ".../Zygos.RecordFidelityReviewFailed" -d '{...same...}'
# then
curl -sS -X POST ".../Zygos.ReviseDraft" -d '{"Reason": "<summary>"}'
# fix the named section(s), re-SubmitForReview, re-run fidelity-review
```

- [ ] **Step 7: Publish (only on pass)**

```bash
curl -sS -X POST "http://127.0.0.1:3467/tdata/HarnessSpecs('<exo_id>')/Zygos.Publish" \
  -H "Authorization: Bearer $ZYGOS_KEY" \
  -H "X-Temper-Principal-Kind: admin" \
  -H "X-Tenant-Id: default" \
  -H "Content-Type: application/json" -d '{}'
```

Expected: 200, `Status: "Published"`, `fidelity_review_passed: true`.

- [ ] **Step 8: Re-render and byte-diff**

GET the entity, run it through `render_harness_spec_markdown`, diff against the input
markdown via `round_trip_diff`. Empty diff list = round-trip is faithful. Non-empty diff
that's not whitespace-normalizable = a real bug, fix it.

---

### Task 3: Backfill temper into a HarnessSpec entity

Mirror of Task 2 with `docs/research/harnesses/temper.md` as input and
`nerdsane/temper@2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` as the pinned primary source.

The temper spec has a heavier structure than exo (per the addendum's note about the
Phase 1 fidelity review finding F1-F10 on DeepSeek Harness, the temper spec itself also
went through fidelity review and had three misattributed quotes, a unit error, a wrong
count, and one central analytical claim corrected). Re-checking against the pinned sources
is non-negotiable — even though the hand-merged spec has already passed review, this
re-import exercises a different code path (parser → entity → render) and the question
being asked is "does the round-trip preserve fidelity," not "was the original correct."

Same step list as Task 2 with `temper` substituted for `exo` and `temper_id` for `exo_id`.
Specifically watch for these known sensitive spots in `temper.md`:
- "165 ADRs" corrected to "181 ADR files under docs/adrs/ (159 unique numbers — 21 numbers
  are reused across 2-3 files each; highest number 0165)" — verify the count via
  `https://api.github.com/repos/nerdsane/temper/git/trees/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400?recursive=1`
  and grep on `docs/adrs/`.
- The 28ns vs 28μs latency figure (correctly disambiguated in the spec's Tradeoffs §"Real
  latency cost from durability") — verify against `docs/PAPER.md`.
- The automatic-rollback step in `docs/AGENT_GUIDE.md §12` hot-swap protocol — verify
  it still says "If production degrades: automatic rollback" verbatim.
- `docs/HARNESS.md` name-vs-thing trap still scoped correctly (Temper's dev-time
  contributor gate, not the product's agent-facing surface).

If any of these have drifted in the original (e.g. temper moved a section number), the
fidelity review fails and the entity is `ReviseDraft`ed. The fix is to update the *hand-
merged* `temper.md` to match the current source, then re-import. This is a feature, not
a bug — the re-import catches drift in the original.

- [ ] **Step 1-8: Same as Task 2 with temper substitution**

---

### Task 4: Update the target-list README to document two-track publication

**Files:**
- Modify: `docs/research/README.md` — target-list rows for exo and temper carry a
  two-publication-path note.

The note is identical for both rows:
> Two publication paths coexist: `harnesses/<slug>.md` is hand-merged git content authored
> 2026-08-16; `HarnessSpec` `<entity-id>` is the entity-backed version published
> 2026-08-28 via the Phase 2 backfill (PR #X). The hand-merged version remains canonical
> until the backfill's fidelity review + round-trip byte-diff confirms equivalence; deletion
> is a separate decision per ADR-0002 addendum §"Recommendation on Phase 2".

`docs/research/README.md` lines 4-7 are modified to add this note inline with the existing
"done (v1 body, embodiment: none)" cell text. Or as a separate footnote-style row below
the table — whichever the reader-search pattern makes clearer.

- [ ] **Step 1: Modify `docs/research/README.md`**

Add the two-track publication note. Commit on the same branch.

- [ ] **Step 2: Commit**

```bash
git add docs/research/README.md
git commit -m "backfill: document two-track publication state for exo + temper"
```

---

### Task 5: Open the PR with all artifacts and findings

**Files:**
- The branch `research/backfill-phase1-specs` carries:
  - `tools/backfill/{parse,render,round_trip_diff}_harness_spec_markdown.py`
  - `research/backfill-phase1-specs/notes/exo-entity-spec.json`
  - `research/backfill-phase1-specs/notes/temper-entity-spec.json`
  - `docs/superpowers/plans/2026-08-28-backfill-phase1-specs-findings.md`
  - `docs/research/README.md` (the two-track note)
  - `docs/research/harnesses/exo.entity-rendered.md` (re-render from exo entity — does
    NOT replace the existing `exo.md`, lives alongside for diff inspection)
  - `docs/research/harnesses/temper.entity-rendered.md` (same)

The `.entity-rendered.md` filename suffix avoids collision with the hand-merged files and
makes the diff-vs-source the natural action a reviewer takes.

- [ ] **Step 1: Commit all artifacts on the branch**

```bash
git add tools/backfill/ docs/superpowers/plans/2026-08-28-backfill-phase1-specs-findings.md \
        research/backfill-phase1-specs/ docs/research/README.md \
        docs/research/harnesses/exo.entity-rendered.md \
        docs/research/harnesses/temper.entity-rendered.md
git commit -m "backfill: Phase 2 round-trip — exo + temper entities, parser, findings"
git push -u origin research/backfill-phase1-specs
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --base main --head research/backfill-phase1-specs \
  --title "Phase 2: backfill exo + temper into HarnessSpec entities (round-trip proof)" \
  --body "Closes the two-track publication gap recommended by ADR-0002 addendum §'Recommendation on Phase 2'.

Three artifacts:
1. Markdown↔entity round-trip tooling (parse, render, diff). Round-trip is byte-identical after CRLF/trailing-whitespace/blank-line-around-headings normalization for both exo.md and temper.md (diff lists in 2026-08-28-backfill-phase1-specs-findings.md are empty).
2. Two new HarnessSpec entities: exo at <exo_id>, temper at <temper_id>. Both Published, fidelity_review_passed: true.
3. docs/research/README.md documents the two-track publication state for both specs.

Hand-merged exo.md and temper.md are NOT deleted in this PR — that's a separate decision after the round-trip is independently verified. Deletion would be in a follow-up PR that explicitly references the backfill's findings file.

Fidelity review: re-fetched pinned primary sources independently (not inherited from prior reviews). Findings in PR comment below and in the findings file."
```

- [ ] **Step 3: Post the fidelity-review findings as PR comments**

Both exo and temper reviews post their findings as PR comments, per
`docs/research/SKILL.md` §4 step 3 ("a clean pass is worth recording as evidence the process
works, not just a NEEDS REVISION verdict"). The PR comment for exo and the PR comment for
temper are distinct comments, each referencing the relevant entity by GUID.

- [ ] **Step 4: Human readability check (per Phase 1 plan's Task 5 Step 4)**

The Phase 1 plan treats the merge of a Published entity as gated on a human confirming
readability of the actual generated file. Apply the same gate here: the PR author reviews
the `.entity-rendered.md` files and the round-trip diff output, confirms the backfill
faithfully represents the source, and only then marks the PR mergeable.

---

### Task 6: Surface the deletion decision for human review (do not execute)

The ADR-0002 addendum's recommendation includes "do not assume deletion in this PR." This
plan respects that. Task 6 documents the deletion as a follow-up question, raised but
not acted on:

- After PR merge, post an issue (or PR comment thread, depending on the repo's tracker
  convention per `docs/agents/issue-tracker.md`) asking: "Backfill is in. Hand-merged
  exo.md and temper.md are still on `main`. Recommend deletion in a separate PR? Options:
  (a) delete, single-publication-path end-state; (b) move to `docs/research/harnesses/_archive/`
  with a redirect note; (c) keep both indefinitely until a third party needs one or the
  other. The user's call, after the backfill's findings file is read."

- [ ] **Step 1: Open the issue or comment thread**

```bash
gh issue create --title "Backfill follow-up: delete or archive hand-merged exo.md + temper.md?" \
  --body "$(cat <<'EOF'
PR #<backfill-pr> merged the Phase 2 backfill. Hand-merged `docs/research/harnesses/exo.md` and `temper.md` are still on `main`.

ADR-0002 addendum §"Recommendation on Phase 2" deferred the deletion decision. Time to make it.

Round-trip result: parser → entity → render is byte-identical after whitespace normalization (see `docs/superpowers/plans/2026-08-28-backfill-phase1-specs-findings.md`). Fidelity review re-fetched pinned primary sources independently; findings posted as PR comments.

Options:
1. Delete the hand-merged files in a small follow-up PR. Single-publication-path end-state. Breaks any URL pointing at the old path (git history retains them).
2. Move to `docs/research/harnesses/_archive/` with a redirect note in the new entity-backed versions. Preserves history without leaving stale frontmatter at the canonical path.
3. Keep both indefinitely. Costs: two-place-to-edit for any future correction; benefits: the hand-merged files preserve git-blame for the original research, and the entity-backed version preserves the Phase 1→2 audit trail.

My read: option 2 if you value the audit trail; option 1 if you don't want the two-track state to leak into future specs. Option 3 is a fine default if neither matters to you right now.

Decision: <user's call>
EOF
)"
```

- [ ] **Step 2: Commit the issue number to the PR body if appropriate**

If the user's repo convention is to link the follow-up issue from the backfill PR, do so.
Otherwise, the issue stands alone and the backfill PR is fully self-contained.

---

## Self-Review Notes

**What this plan doesn't do (and why):**

- **Doesn't delete the hand-merged files.** Per ADR-0002 addendum §"Recommendation on Phase 2"
  deferral and user instruction (2026-08-28). Surfaced as a follow-up question in Task 6.
- **Doesn't change the entity schema, the IOA, or the Cedar policy.** The Phase 1 schema
  already matched the markdown shape (proven by the two Phase 1 entities Publishing cleanly).
  If the parser discovers a missing field, that's a finding to escalate, not a fix to make
  in this plan — schema changes invalidate the Phase 1 entities.
- **Doesn't build the render function into the entity pipeline as a side-effect of Publish.**
  Phase 1's fidelity-review SKILL.md Step 8 says Publish generates the markdown; the plan
  respects that. This plan's `render_harness_spec_markdown.py` is for *verification* of the
  round-trip, not as a replacement for the platform's eventual built-in renderer. A future
  Phase 2 follow-up could replace it; that's a separate decision.
- **Doesn't do a 5th net-new harness.** Per user instruction (2026-08-28): "backfilling
  exo/temper into entities, not a 5th net-new harness."

**Known risks, named rather than hidden:**

- **JSON encoding will not preserve every byte of the markdown.** YAML frontmatter is plain
  text; body sections are markdown tables and inline code. JSON string escaping handles
  quotes and backslashes; markdown tables survive JSON encoding intact because they use
  no special JSON characters. The user's whitespace normalization is what covers the rest.
  If a real drift appears that survives normalization, the parser or render has a bug,
  not a JSON encoding limitation.
- **The body section split is fragile against future heading changes.** If the
  `_template.md` adds a new heading, both the parser and the render must be updated.
  This plan doesn't enforce that contract; it's inherited from Phase 1. A future task
  could add a CI check that the parser's heading set matches the render's heading set,
  but that's not Phase 2's job.
- **The two Phase 1 entities were authored by an LLM agent invoking the platform directly;
  this plan invokes the platform directly from bash + curl.** Phase 1 used a Temper MCP
  client or a sandboxed Python REPL — see ADR-0002 addendum §"Disclosed deviation" for
  the exact shape. The plan uses curl because it's verifiable in this session without
  spinning up an MCP server, and because Phase 1's skill file (`fidelity-review/SKILL.md`)
  documents the curl pattern explicitly.
- **The bearer key in this plan is the same one Phase 1 used.** If it has rotated since
  the addendum was written (2026-08-27), every POST in Tasks 2-3 will 401. The plan's
  Task 1 Step 3 GET already validates the key works as of 2026-08-28 (verified live).
  If a key rotation happens mid-plan, that's a stop-condition requiring re-validation.

**Spec coverage against the backfill's stated proof:** The user's instruction was *"the
re-rendered markdown must be byte-identical to the hand-merged files — that's the
backfill's proof."* Task 1 Step 3 is where the proof is produced; Tasks 2-3 Step 8 are
where it's re-confirmed for each spec. Task 5 Step 4 is the human readability check that
turns the proof into a mergeable artifact.
