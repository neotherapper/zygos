# How to research a harness

Procedure, not policy — `DESIGN.md` §4 defines what a spec must contain; this file is how to actually
go get it. Written after the Temper pass, from the friction that pass hit, not designed in advance.
Follow `CLAUDE.md`'s five rules throughout; this file assumes them.

## 0. Before you start

Confirm the target has a `status: not-started` row in `docs/research/README.md` with a pinned commit
SHA that resolves. If the SHA doesn't resolve — `curl -sI` against
`raw.githubusercontent.com/<org>/<repo>/<sha>/README.md` should return `200` — stop and fix the
coordinate before reading anything. A relayed SHA with no org/repo, or one that 404s, has happened
twice already in this library's short history; it is the single most common way a pass starts on the
wrong foot.

Branch first: `git checkout -b research/<slug>`. Never commit a spec directly to `main` — see §4.

## 1. Fetch order

1. **The repository tree, recursive, via the GitHub API** (`/repos/<org>/<repo>/git/trees/<sha>?recursive=1`),
   not a directory listing by hand. This is how you find the deep docs a README only points at, and how
   you catch a repo that's much larger than it looks from the README alone — Temper's tree surfaced 165+
   ADRs and a 78KB architecture paper that the README only linked to once, in passing.
2. **The README, in full.** It is almost never sufficient on its own for Verification or Boundaries, but
   it tells you what else exists and how the project describes itself in the fewest words — the
   Philosophy section usually starts here.
3. **Whatever the README calls its architecture/positioning/design document**, in full, if one exists.
   Look for it by name in the tree (`PAPER.md`, `ARCHITECTURE.md`, `DESIGN.md`, `POSITIONING.md`) before
   assuming the README is all there is. This is where Verification, Loop, and Boundaries actually get
   filled — Temper's cascade, gate points, and hot-swap protocol were only fully specified here, not in
   the README's compressed version.
4. **Anything the project calls its own "harness," "agent guide," or "developer guide."** Read the whole
   filename before trusting it describes what you think it describes — see §2.
5. **Everything else, by grep, not by full read.** A large repo's ADR/changelog archive is implementation
   history, not the spec-level primary source this library cites. Grep it for the specific terms your
   still-open sections need (see §3) and read only the hits in context. Disclose in Sources what was
   scanned by heading/filename versus actually read — this distinction matters and reviewers will check it.

Stop reading and start writing once Philosophy, Primitives, Loop, Boundaries, and Verification each have
at least one primary-sourced claim. Circle back for Economics, Tradeoffs, and the two What-to/What-not
sections once the shape of the project is clear — they're easier to write well after the mechanism
sections, not before.

## 2. The name-vs-thing trap, specifically for this library's subject

This library studies "harnesses." A meaningful fraction of harness repositories will contain a file or
directory *also* called "harness" — their own development tooling, a CI gate, a submodule named after
the pattern. Temper's `docs/HARNESS.md` was its own dev-time contributor gate, not the product's
agent-facing surface, and a first pass nearly cited it as the latter. Before citing any file whose name
matches this library's own subject, read enough of it to answer: *is this describing what an agent gets
when using the product, or is this describing how the maintainers build the product itself?* State the
answer in Sources even when it resolves in the file's favor — a reader shouldn't have to re-derive it.

## 3. Filling each section

- **Philosophy.** Quote, don't paraphrase, the project's own stated position and its own stated refusals
  ("what Temper is and is not"-style tables are a gift when they exist — check for one). A paraphrase
  loses the specific words a project chose, and those words are often the finding.
- **Primitives.** One row per noun a user or agent actually manipulates, not per implementation detail.
  If a "why it matters" cell just restates the "what it is" cell, the primitive probably isn't pulling
  weight in the record — cut it or dig for a sharper source line.
- **Loop.** Identify how many distinct loops exist (a harness usually has more than one: a per-action
  loop, a per-change/deploy loop, sometimes an evolution/feedback loop) before writing prose. Naming them
  separately up front prevents them from blurring together in the write-up.
- **Boundaries.** Build the state-inventory table before writing the surrounding prose — see exo.md and
  temper.md for the shape: one row per category of state, one column for what it survives, one cell per
  row stating the mitigation in the same breath as any lossy row. If you can't find enough material to
  build at least three rows, that's a real finding (state boundary the project's docs don't discuss) —
  say so rather than leaving the table thin without comment.
- **Verification.** Place every mechanism found on the four-rung ladder (`CLAUDE.md`), then write one
  sentence per mechanism on whether it *gates* or only *reports*. Don't infer gating from a mechanism's
  name — confirm it against the source describing what actually happens on failure (blocked? rejected?
  logged and continued?).
- **Which axis.** State the axis, then check specifically whether the project's own recovery/prevention
  framing has a footnote, caveat, or a second document that qualifies it — this is the single highest-yield
  place a project's own docs contradict each other, per this library's experience so far (twice: exo's
  default-vs-structural footnote, Temper's PAPER.md-vs-AGENT_GUIDE.md rollback gap).
- **Economics.** Grep the material for `cost|cache|token|prefix|compaction` before concluding the
  section is empty — but don't stop at "found nothing," because a real cost model can exist at a
  different layer than the one you were looking for (Temper had one for its own backend, not for LLM
  tokens). State precisely which layer has a cost model and which doesn't, rather than a single
  present/absent verdict.
- **Embodiment.** `embodiment: none` is a fine answer in v1 — see `DESIGN.md` §4.3 for the promotion
  criterion. If the project discloses its own benchmarks with a stated method (sample count, tool name),
  that's real evidentiary standing worth recording even without a hands-on run — say so, and say clearly
  that it's still not this record's own evidence.

## 4. Fidelity review, before merge, not after

A presence check (every section filled, frontmatter valid) proves nothing about whether the content is
true — see `docs/adrs/0001-guards-check-presence-not-truth.md`. Before merging a spec:

1. Open a PR from the research branch. Never merge a research branch without one — the PR body and its
   comments are the audit trail.
2. Dispatch an independent agent — one that has not seen the draft being written, only the finished file
   and the same pinned sources — to check three things, adversarially, with intent to refute rather than
   confirm:
   - **Every direct quote** resolves against the actual source file, not a nearby file, and isn't
     truncated in a way that reverses its meaning.
   - **Every non-quoted factual claim** is re-checked against the relevant source section, not accepted
     because it sounds plausible or because a name implies it (pavlos ADR-0001 failure mode 2).
   - **The Limits section's own claims about what wasn't read** are spot-checked — counts, section
     numbers, and scope statements are exactly the kind of detail that's easy to get approximately right
     and exactly wrong (an ADR count off by one highest-number-mistaken-for-file-count, a "read sections
     1 and 16" disclosure that turns out to need 8 and 12 too once a claim depends on them).
3. Post the findings as a PR comment, whatever the verdict. A clean pass is worth recording as evidence
   the process works; a NEEDS REVISION verdict is worth recording as evidence it caught something.
4. Fix findings in the file itself, including a note in the spec's own Limits section about what changed
   and why — the correction is part of the record, not a private cleanup. Merge only after the fixes are
   in and pushed.

This step found real, load-bearing defects the one time it's been run so far (`temper.md`, PR #1) —
three misattributed quotes, a unit error, a wrong count, and one error in a central analytical claim
that a presence check would never have caught. Do not skip it to save time; it is currently the single
highest-value check in this whole procedure.

## 5. What this file doesn't cover yet

- How to handle a target whose primary "harness" concept turns out to span multiple repositories (not
  yet encountered).
- What changes about this procedure once `docs/concepts/` has its first real entry — concept-document
  research likely needs its own version of §4's fidelity check, scoped to "does every cited occurrence
  still say what the concept document claims," and that hasn't been written yet either.
