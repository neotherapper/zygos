---
adr: 0002
title: zygos becomes a Temper-backed curation pipeline, mirroring katagami
status: accepted
date: 2026-08-16
---

# ADR-0002 — zygos becomes a Temper-backed curation pipeline, mirroring katagami

## Status

Accepted. Phase 1 only (below) — later phases are named as direction, not committed scope.

## Context

zygos v1 (`FORMAT.md` §2, ADR-0001) was deliberately scoped as *"a directory of markdown under
version control. There is no application."* A human dispatches an agent per harness; the agent
researches by hand, branches, opens a PR, an independent agent runs fidelity review, a human or the
same agent merges. This has run twice (exo, Temper) and works.

The lab's own stated topology, set at the moment this repo was created, was always meant to change:
*"Temper → Katagami, pavlos → zygos — same relationship."* Katagami is the model this repo was named
against from day one; running zygos as permanently-manual markdown was the honest starting point, not
the destination.

**Katagami's specs are not git-committed files.** This is the load-bearing fact this ADR is built on,
confirmed against katagami's own README before writing anything here (per rule 1). A design language in
katagami is a **Temper entity** — `design_language`, moved through `Draft → UnderReview → Published →
Archived` by a state machine, with a `SubmitForReview` guard that rejects the transition unless all
five spec sections and the embodiment exist. The katagami git repo holds *code*: two Temper apps
(`katagami-commons` for the data layer, `katagami-curation` for the agent work layer) and a Next.js
gallery UI. `DESIGN.md` per language is a **generated projection** of the entity, published at deploy
time — not the source of truth.

zygos today inverts this: the markdown file *is* the source of truth, and there is no entity, no guard,
no runtime underneath it.

**Motivation, in priority order, as stated when this decision was made:** understand Temper hands-on by
building a real application on it (primary); increase research throughput by removing the
human-dispatches-each-target bottleneck (secondary); feed pavlos's build decisions faster once the
pipeline is running (bonus — pavlos already holds requirements, e.g. R8/R9, that name zygos specs as
their evidentiary source).

**Local environment check, done before writing this ADR:** Docker and a Postgres client are present;
no Rust toolchain. Temper is a Rust project — installing `rustup`/`cargo` is a Phase 1 prerequisite,
not yet done.

## Decision

Build a Temper-backed curation pipeline for zygos, structurally mirroring katagami, in **phases** —
Phase 1 is the only phase this ADR commits to; later phases are direction, to be re-scoped against what
Phase 1 actually teaches.

### Phase 1 (committed)

- **Two Temper apps in this repo**, named on katagami's own pattern: `zygos-commons/` (data layer —
  the `HarnessSpec` entity) and `zygos-curation/` (agent work layer — one curation skill). No UI app
  yet.
- **`HarnessSpec` entity**, in `zygos-commons`, carrying the fields the markdown frontmatter already
  has — `name`, `kind`, `axis`, `primitives`, `lifecycle`, `provenance`, `verified_at`, `embodiment`,
  `url`, `artifact_url`, `commit` — plus the ten body sections as document fields. State machine:
  `Draft → UnderReview → Published → Archived`, matching katagami's `design_language` shape exactly
  rather than inventing a new one.
- **`SubmitForReview` guard**: rejects the transition unless every required section (`FORMAT.md` §4.1)
  and every required frontmatter field is present and non-empty. This is the mechanical column of
  zygos's own ADR-0001 table, finally built rather than only specified.
  ​
- **One curation skill: `synthesize-harness`.** Does what the manual process already does — fetch
  order and section-filling guidance straight from `docs/research/SKILL.md`, which does not need to be
  rewritten, only executed by an agent talking to the Temper API (`temper.action(...)` calls) instead of
  editing a file directly.
- **One review job, automated: the fidelity-review check.** `docs/research/SKILL.md` §4's three-part
  adversarial check (quotes resolve, non-quoted claims aren't backwards, Limits section is honest) runs
  as a Temper job on `UnderReview`, not as a manually-dispatched agent. This is katagami's
  `review-quality` job, for a different kind of quality.
- **`Publish`**: generates `docs/research/harnesses/<slug>.md` — same file, same shape readers see
  today — as an export. The published markdown remains the public-readable artifact; it stops being
  hand-merged.

### Explicitly deferred, not forgotten

- **Target discovery** (katagami's `research-direction` skill / `CurationDirection` fan-out). The
  target list in `docs/research/README.md` stays a manually-maintained table for now.
- **`organize-taxonomy` equivalent.** `kind` and `axis` stay author-asserted per spec; no automated
  classification job yet.
- **A gallery UI.** Named and deferred deliberately, not by omission: katagami's UI earns its place
  because a design language is visual and benefits from a rendered embodiment page. A harness spec is
  prose and tables. Whether a browsable UI is worth building for that content is unproven, not assumed
  — revisit after Phase 1, informed by whether anyone (including George) actually wants to browse
  zygos specs anywhere other than GitHub.
- **Migrating `exo.md` and `temper.md` into entities.** They stay git-only, hand-merged artifacts for
  now. Backfilling them into `zygos-commons` once Phase 1 works is the natural Phase 2 opener, but is
  not required for Phase 1 to be considered done — Phase 1's success criterion is a **third** spec
  (DeepSeek Harness or RLM) going through the entity-backed pipeline end to end, not a migration of the
  first two.
- **Hosted / multi-tenant deployment.** Local only, on the same pattern as katagami's own "Running
  locally" instructions — a Temper checkout, this repo's apps symlinked into `os-apps/`, `cargo run`.

## Consequences

**Positive**

- Builds the real Temper primitives — entities, guards, hot-reload, the verification cascade — hands
  on, which is the stated primary motivation, not a side effect.
- The presence/judgment split in zygos's own ADR-0001 stops being a design argument and becomes an
  actual guard. A future reader can point at working code, not just a table.
- The fidelity-review pattern, already proven once by hand (`temper.md`, PR #1) with real findings,
  gets automated rather than re-improvised per spec.
- Directly informs pavlos: building a Temper app to research Temper, whose specs then feed pavlos's own
  runtime-versus-fork-versus-build decision, is a tight loop with a short feedback path.

**Negative**

- Real infrastructure to install and keep running: Rust toolchain, Postgres, a Temper server — none of
  which zygos needed before this. The "just markdown, no application" property this repo started with
  is gone by design, and that is a real cost, not only a milestone.
- Two publication paths exist during the transition: `exo.md` and `temper.md` remain hand-merged git
  artifacts (per the deferral above) while anything researched from here forward goes through the
  entity pipeline. Readers see no difference in the output file; maintainers need to know which model
  a given spec is actually under until the backfill (if it happens) closes the gap.
- Harness specs carry far more prose per entity than katagami's design tokens — ten sections of
  argument and quoted evidence, versus a bounded token schema (colors, typography, spacing). Whether
  Temper's CSDL/IOA model, built for structured data-plus-state-machine domains, holds up well for an
  entity that is mostly long-form prose is genuinely untested. Phase 1's actual job is finding out.
- The fidelity-review job, as an automated Temper job rather than a dispatched general-purpose agent,
  needs its own tool access (fetch primary sources, read the draft) defined and budgeted — not yet
  designed at the level `docs/research/SKILL.md` §4 assumes for a manually-dispatched review.

**Known gap**

This ADR commits to Phase 1 only. It does not commit to the gallery UI, target-discovery automation, or
taxonomy automation ever being built — each is a separate decision, to be made with what Phase 1
teaches in hand, not assumed now because katagami has all of them.

## Alternatives considered

- **Approach B — Temper orchestrates, git stays authoritative.** Temper runs a job queue; a bot opens
  PRs against markdown as the real artifact, same as today, just triggered automatically. Rejected:
  lower-risk, but a shallow replication — katagami's specs are not git-committed files a bot maintains,
  so this would not actually be "the same approach," only automation layered on the existing one. Ruled
  out specifically because the stated primary goal is learning Temper's real primitives, which this
  approach only touches at the orchestration layer.
- **No Temper — better tooling around the manual process instead** (a workflow queue, scheduled
  dispatch, nothing Temper-specific). Rejected outright: does not serve the stated primary motivation at
  all, and the throughput gain without the entity/guard model is smaller than Approach A's.
- **Design and build the full stack at once** (both Temper apps, all four curation skills, and the
  gallery UI, in one pass). Rejected in favor of phasing: katagami itself represents a mature, multi-
  hundred-ADR build; committing to its full shape before Temper has been touched once risks a Phase 1
  shape that doesn't fit what Temper actually teaches once it's running.
