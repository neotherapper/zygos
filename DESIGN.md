# zygos — Design Document

**A library of complete AI agent harness specifications, researched and maintained by agents.**

| | |
|---|---|
| **Owner** | George Pilitsoglou |
| **Repository** | `neotherapper/zygos` (public) |
| **Document Version** | 1.0 — August 2026 |
| **Status** | Active |

---

## 1. Overview

zygos holds one complete, structured, sourced specification per AI agent harness — the runtime layer
that assembles a turn, dispatches tools, and decides what state a model call is allowed to touch. Where
a comparison site catalogues breadth across the field, zygos goes deep on individual entries: enough
structure that two harnesses can be read side by side and enough sourcing that every claim can be
checked against what the project actually says.

The name is ζυγός — the yoke that couples draught animals to pull together, and the balance the same
word names in Greek (Ζυγός, Libra). A harness does both: it couples a model to the world, and it trades
capability against constraint. Neither reading is decorative; a spec that only describes what a harness
lets an agent do, without describing what it refuses to let the agent do, has described half of it.

zygos is downstream of research, not upstream of a runtime. It studies harnesses; it does not run one.

## 2. Relationship to sibling work

zygos sits beside two things it is not:

- **pavlos** (`neotherapper/pavlos`) originates the research — provenance rules, the two-axis
  classification, the verification-rigor ladder. zygos inherits that discipline and applies it to a
  format built for a different kind of object.
- **A private harness build**, elsewhere, may draw technique from zygos's specs. Nothing flows back —
  zygos carries no reference to private work, its schema, its thresholds, or its internal names, and no
  spec here should be checkable against anything not publicly readable at its cited URL.

The topology mirrors katagami/Temper: katagami is a library of design-language specs built on the
Temper runtime; zygos is a library of harness specs, with no runtime under it yet. If that changes,
the schema this document defines is the part meant to survive the change — see §5.

## 3. Goals and Non-Goals

### Goals

| # | Goal | Success signal |
|---|---|---|
| G1 | One complete spec per harness, not a shallow entry in a long list | Each spec fills every required section or states plainly why it can't |
| G2 | Comparable structure across harnesses | Two specs answer the same questions in the same order |
| G3 | Provenance as a structural property | Every spec carries `provenance` / `verified_at` / `lifecycle`; every quoted claim anchors to a source |
| G4 | Surface what a harness leaves silent | Axis classification (below) makes "trusts the model" a recorded finding, not an omission |
| G5 | A schema that could be machine-enforced later | Presence, shape and cross-reference are checkable mechanically even in v1's plain markdown — see §5 |

### Non-Goals

- **Breadth.** `best-of-Agent-Harnesses` already covers the field at scale — 161+ projects, an
  autonomy × recovery grid, a queryable MCP server. zygos does not compete with that and should not try;
  depth per entry is the open niche, not coverage of it.
- **Building or running a harness.** This is a study.
- **Ranking.** Specs record tradeoffs a design committed to; they do not declare a winner.
- **Any material from private or client work**, in any form — see §6.

## 4. Spec Format

Every harness spec carries YAML frontmatter. Fields and required-ness are inherited from the research
discipline this project is downstream of, not reinvented:

```yaml
---
name: exo
title: "exo"
url: https://github.com/exoharness/exo          # durable page
artifact_url:                                    # retrieved file or tree, pinned to a commit SHA
commit:                                           # the SHA everything in the spec was read at
language: Rust, TypeScript
kind: agent-harness                               # agent-harness | agent-substrate | inference-paradigm
license: MIT
status: early development                         # the project's own stated maturity
lifecycle: version-changing                        # current | version-changing | retired
provenance: primary                                # primary | secondary | relayed
verified_at: 2026-08-16
axis: [A]                                          # A structural | B factual | both | neither
primitives: [event-log, sandbox, snapshot-rewind]
embodiment: none                                   # none | partial | full — see §4.3
---
```

`kind` classifies what kind of thing is being compared, because "harness" denotes several related
things sharing a word — a runtime that runs the agent loop, a substrate the loop reaches into, or an
inference paradigm that replaces the model call outright. Comparing across `kind` values without
declaring them compares things that aren't comparable.

### 4.1 Body sections

```
Philosophy      What the harness believes about agents, and what it refuses to do.
                Quote the project's own words — paraphrase loses the position.

Primitives      The nouns a user or agent manipulates: event log, sandbox, tool,
                capability, checkpoint. Usually the most transferable part of a spec —
                the vocabulary a design commits to constrains everything built on it.

Loop            The verbs. How a turn is assembled and executed: what may mutate what,
                in what order, and what triggers the next step.

Boundaries      Trusted vs swappable. What is sandboxed. Which state survives which
                kind of reset — a state-inventory table, one row per category of state,
                one column per reset type. Blast radius of an irreversible action.

Verification    Placed on the four-rung ladder — observability-driven feedback, shadow
                evaluation, deterministic simulation, formal specification — and,
                separately, what each mechanism *gates* versus what it merely *reports*.
                A harness that instruments heavily and gates nothing should say so.

Axis            A (can the system enter a broken state?) / B (is the claim about the
                world true?) / both / neither — plus, where axis A applies, whether the
                harness *prevents* entering a broken state or only *recovers* from one.
                Recoverability and soundness are different properties and both get
                called "safety"; conflating them is the most common error this section
                exists to catch.

Economics       Cost as a design property, not an afterthought optimization. Cache
                reuse, compaction shape, what gets re-sent on every turn versus reused.
                Where the material read says nothing about this, say that plainly rather
                than leaving the section absent — an unaddressed cost model is itself
                a finding.

Tradeoffs       What the design buys, stated together with what it pays. Every buy has
                a cost; naming only one side is not a tradeoffs section.

What to steal   Technique stated so it survives without this specific harness.

What not to     Where this design should not be ported, and who should not adopt it.

Embodiment      A canonical task actually run on the installed harness, with a trace.
                Optional in v1 — see §4.3.

Limits of this  Mandatory, non-empty. What was not checked: code vs docs, claims not
spec            verified, files fetched but not read, no hands-on run. A spec that
                cannot name its own gaps is not finished.
```

Ten required sections plus one conditionally-required (Embodiment). No separate machine-readable
export is authored by hand in v1 — see §4.3.

### 4.2 Why this differs from katagami's language spec

Katagami's format — Philosophy / Tokens / Rules / Layout / Guidance / Embodiment, plus a native spec
and a generated `DESIGN.md` — describes a static object: a design language doesn't execute, doesn't
have a trust boundary, and doesn't cost tokens per turn. A harness does all three, so the mapping isn't
one-to-one. `Loop` and `Boundaries` have no katagami analogue and exist because a harness has behavior
over time. `Economics` has no katagami analogue and exists because a harness has a cost curve. `Axis`
has no analogue anywhere in the field found so far — see zygos ADR-0001.

`Guidance` in katagami's table is one section; here it is three (`Tradeoffs` / `What to steal` /
`What not to`), kept separate because they are three different prompts. A single "guidance" heading
invites a vaguer answer than three specific ones do.

### 4.3 Embodiment is optional in v1, and the export is generated, not authored

Katagami renders roughly 15 UI elements per design language — cheap, because rendering a language is a
sandboxed screenshot job. The harness analogue is installing and running the actual project, which is
not cheap, and a spec's other ten sections can be fully sourced without it. Making Embodiment mandatory
from the first spec would make the format expensive before it has been tested at all.

**v1 rule:** `embodiment: none` is an acceptable, honestly-stated value. The section is promoted to
required once either condition holds: (a) four or more specs exist in the library, or (b) any spec
claims a behavioral property — not merely a documented one — that only a run can confirm. Until then,
state `embodiment: none` and do not fabricate a trace to fill the section.

**No hand-authored `HARNESS.md`.** Katagami's own README states the reason to skip this for v1 more
precisely than YAGNI does: the native Katagami spec is the source of truth, and a portable `DESIGN.md`
projection is *generated* from it at publish time, not independently authored. zygos's frontmatter is
already structured — enum-valued fields, a pinned SHA, a primitives list — so a generated export is a
mechanical transform whenever it's needed. Authoring two synced formats by hand before the first has
survived contact with more than one spec invites drift between them for no present benefit.

## 5. What a Guard Could Actually Check

Katagami's `SubmitForReview` transition has guards: it rejects publication unless all five spec
sections and the embodiment exist. That is real enforcement, and it is enforcement of **presence and
shape**, not of **truth**. A guard can confirm a `Philosophy` section is non-empty; it cannot confirm
the quote inside it is accurate, or that `provenance: primary` reflects a source actually opened.

zygos v1 has no runtime and enforces nothing beyond markdown convention and the author's own honesty —
the same position pavlos starts from. The schema in §4 is written so that a future guard, if one is ever
built, has a defined set of checks available to it without redesigning the format:

| Mechanically checkable now | Requires a human (or a model) to judge |
|---|---|
| All required sections present and non-empty | Whether the Philosophy quote is representative, not cherry-picked |
| `Limits of this spec` present and non-empty | Whether `provenance: primary` reflects a source actually opened |
| Frontmatter enums valid (`lifecycle`, `provenance`, `axis`, `kind`) | Whether the Axis classification is correct |
| `artifact_url` matches a 40-hex commit SHA, not a branch ref | Whether `Boundaries`' state-inventory table is complete |
| Every direct quote carries a source anchor resolving in the Sources table | Whether `Economics` says something true, versus merely says something |

The right column is the larger one, on purpose. Naming the boundary is the point: a schema that implies
more enforcement than a guard could deliver would oversell exactly the thing ADR-0001 in this repo
exists to name honestly. See `docs/adrs/0001-guards-check-presence-not-truth.md`.

## 6. Boundaries

This repository is public.

| Permitted | Excluded |
|---|---|
| Public open-source harnesses | Client or employer-internal work, in any form |
| Published documentation, source, write-ups | Private repository contents |
| Generalized technique | Internal paths, schema internals, thresholds, corpus figures |
| The author's own conclusions | Verbatim text from private sources |

**Entity-level redaction is insufficient.** Stripping names and paths while keeping distinctive
phrasing still reproduces confidential text. Where a finding is informed by private work, restate it in
fresh words rather than editing the original down — the same rule pavlos runs under, applied here too
because the risk is identical regardless of which public repo it would surface in.

## 7. Initial Scope

| Harness | Why | Status |
|---|---|---|
| **exo** | Fully recursive self-editing agent + harness; migrated from pavlos | done (v1 body, `embodiment: none`) |
| **Temper** | Formal verification of agent-authored capabilities — nothing else on the list gates on proof | not started |
| **RLM** | Recursive context decomposition as an alternative to tool-calling entirely | not started |
| **DeepSeek Harness** | Plugin-composable architecture; candidate "log is the program" third instance | not started |
| **pi** | Named by the owner; needs disambiguation before research — see `docs/research/README.md` | blocked on disambiguation |

Temper, RLM and DeepSeek Harness are chosen to bracket the design space — proved-before-running,
recursive-self-editing, everything-is-a-plugin — rather than sample it.

## 8. Summary

zygos is a markdown library, agent-maintained, of complete AI agent harness specifications. It commits
to depth per entry over breadth of coverage, to a ten-section format shaped by what a harness actually
is — a thing with a loop, a trust boundary, and a cost curve — rather than borrowed unchanged from a
sibling library of a different kind of object, and to naming exactly what a future guard could and
could not verify, rather than letting "researched and maintained by agents" imply enforcement this
version does not have.
