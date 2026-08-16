---
name:
title: ""
url:
artifact_url:
commit:
language:
kind:                  # agent-harness | agent-substrate | inference-paradigm
license:
status:                # the project's own stated maturity
lifecycle:             # current | version-changing | retired
provenance:            # primary | secondary | relayed
verified_at:
axis: []               # A | B | both | neither — plus prevention vs recovery if A
primitives: []
embodiment: none       # none | partial | full — see FORMAT.md §4.3
---

# <name>

## Philosophy

What this harness believes about agents, and what it refuses to do. Quote the project's own words.

## Primitives

The nouns a user or agent manipulates.

## Loop

The verbs. How a turn is assembled and executed: what may mutate what, in what order, what triggers
the next step.

## Boundaries

Trusted vs swappable. What is sandboxed. State-inventory table: one row per category of state, one
column per kind of reset, stating which resets it survives. Blast radius of an irreversible action.

## Verification strategy

| Method | Present? | Notes |
|---|---|---|
| Observability-driven feedback | | |
| Shadow evaluation | | |
| Deterministic simulation testing | | |
| Formal specification | | |

State what each mechanism gates versus what it merely reports.

## Which axis

A / B / both / neither, and — if A — prevention vs recovery.

## Economics

Cost as a design property: cache reuse, compaction shape, what's re-sent every turn vs reused. If the
material read says nothing about this, state that plainly.

## Tradeoffs

What the design buys, together with what it pays.

## What to steal

Technique stated so it survives without this specific harness.

## What not to

Where this design should not be ported, and who should not adopt it.

## Embodiment

A canonical task run on the installed harness, with a trace. `embodiment: none` in frontmatter is
acceptable in v1 — do not fabricate a trace to fill this section; state the omission instead.

## Limits of this spec

Mandatory, non-empty. What was not checked.

## Sources

All fetched as raw markdown pinned to a commit SHA, not a branch ref.

| Source | Type | Retrieved |
|---|---|---|
