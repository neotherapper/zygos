# CLAUDE.md — operating rules for zygos

Read [`FORMAT.md`](FORMAT.md) first. It is the specification; this file is the working procedure.
[`CONTEXT.md`](CONTEXT.md) is the glossary — check it before introducing a new term, and before using
"spec," "record," "harness," "primitive," or "embodiment" in a way that might not match how this repo
already uses them.

## What this repo is

A library of **complete AI agent harness specifications** — one deep, structured, sourced spec per
harness, not a wide shallow catalogue. Output is markdown, not code.

## The five rules

1. **Read the primary source.** Never cite something you did not open. Fetch raw files pinned to a
   commit SHA, not a branch ref — a `main` ref changes content silently and still resolves, so no link
   check catches the drift.
2. **Every spec carries `provenance`, `verified_at`, `lifecycle`.** Required frontmatter, none
   substitutable for another. See [`docs/adrs/0001-guards-check-presence-not-truth.md`](docs/adrs/0001-guards-check-presence-not-truth.md).
3. **"Limits of this spec" is mandatory and non-empty.** A spec that cannot name its own gaps is not
   finished.
4. **Omit weak figures rather than sourcing them weakly.** Star counts and adoption figures are
   excluded by default. If a number is load-bearing, open the primary source behind it — not the
   nearest secondary summary that quotes it.
5. **Nothing private, ever.** This repo is public. No client or employer material — not paths, not
   schema internals, not thresholds, not verbatim text. Stripping names is not enough; distinctive
   phrasing survives it. Restate findings in fresh words rather than editing originals down.

## Writing a harness spec

**Read [`docs/research/SKILL.md`](docs/research/SKILL.md) first.** It's the how-to — fetch order, the
name-vs-thing trap this library's own subject invites, what fills each section well, and the fidelity-
review step that must run before any merge. This file states what's required; that one states how to
actually get it.

```bash
git checkout -b research/<slug>
cp docs/research/_template.md docs/research/harnesses/<slug>.md
```

Fill every required section (`FORMAT.md` §4.1). `embodiment: none` is an acceptable, honestly-stated
frontmatter value until the promotion criterion in `FORMAT.md` §4.3 is met — do not fabricate a trace
to fill the section. Update the target-list status in [`docs/research/README.md`](docs/research/README.md).

**Never merge a research branch without a PR and an independent fidelity review** — `docs/research/SKILL.md`
§4. A presence check (every section filled) proves nothing about whether the content is true.

**Before marking a spec done, ask the three questions that catch real defects:**

- Is any claim here *precise but unsourced*? Precision reads as verification whether or not it is.
- Is any claim here true of the *name* rather than the *thing*? Re-read the source asking "is this
  backwards?"
- Would this still be true if the project changed last month? If unsure, that is `lifecycle`.

A fourth, specific to this format: **does `Boundaries`' state-inventory table actually name, for every
category of state, which reset it survives?** A table with a row missing is worse than no table,
because it reads as complete.

## Concept documents

When a technique recurs across three or more harnesses, lift it into `docs/concepts/` and cite each
occurrence. Concepts are the durable output; individual specs age. Before publishing a concept, verify
each occurrence yourself against its primary source — do not inherit a synthesis someone else offers,
even a trusted one, on their word alone.

## ADRs

Decisions about **the library itself** — format, scope, process. Not about harnesses. Context with
concrete observed failures, Decision, Consequences including the negative ones and the known gaps,
Alternatives considered.

## Two axes — classify every harness

- **Axis A — structural soundness.** Can the system enter a broken state? If yes, does the harness
  *prevent* that or only *recover* from it — these are different properties and both get called
  "safety."
- **Axis B — factual truth.** Is the claim about the world correct?

Most harnesses address one and are silent on the other. Which, and does the design appear aware of the
gap? "Trusts the model" is a legitimate finding, and a common one.

## Verification rigor levels

| Method | Gives | Cost |
|---|---|---|
| Observability-driven feedback | Production contradicts the harness → harness updates | Lowest |
| Shadow evaluation | Run the new rule against existing labelled data, compare | Low |
| Deterministic simulation testing | Replayable runs with injected faults | Medium |
| Formal specification | Proof no reachable state violates an invariant | Highest |

Record what a mechanism **gates** separately from what it merely **reports**. Heavy instrumentation
that nothing acts on automatically is not verification — say so plainly when that's what the material
shows.

## Working style

**Answer first, one decision at a time, short blocks.** Put durable detail in files and give the path,
not the content. Don't stack open questions — ask the one that blocks the next step.

## Boundary with sibling repos

`pavlos` originates the research discipline this repo inherits; treat it as upstream and read-only —
do not edit it from here. Nothing from any private repository flows into this one, in any form,
regardless of how it is phrased or how thoroughly names are stripped.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues, driven by the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map to same-named labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adrs/` at the repo root. See `docs/agents/domain.md`.
