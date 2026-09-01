---
adr: 0003
title: A re-pin gets a scoped fidelity review, gated on the reviewer repeating the source diff
status: accepted
date: 2026-09-02
---

# ADR-0003 — A re-pin gets a scoped fidelity review, gated on the reviewer repeating the source diff

## Status

Accepted.

## Context

- `docs/research/harnesses/temper.md` was pinned to `2f43ece` (2026-08-15). By 2026-09-02 upstream
  `main` was 18 commits ahead. No procedure existed for moving a spec's pin forward, and
  `docs/research/SKILL.md` §5 did not list the gap.
- Between the two pins, the five documents the spec quotes were byte-identical (`git diff` on a clone
  returned nothing for them). Six ADRs, a distilled `AGENTS.md`, and a fifteen-file self-verification
  skill were new. A full §4 fidelity review would re-verify roughly forty quotes that could not have
  drifted, spending reviewer attention that should go to the new material.
- The "nothing drifted" claim is exactly the kind a presence check would wave through (ADR-0001). If
  the author ran the diff against the wrong ref, every quote could be wrong while the review skipped
  them all.
- Concrete failure the re-pin caught: the Boundaries state-inventory row "event journal survives
  restart" was true for transitions and false for PATCH/PUT field updates at the original pin
  (upstream ADR-0157, fixed at commit `cda632b`). The row had been inferred from the table's general
  claim, not sourced. A quote re-check would not have caught it. A row-by-row source check does.
- A second failure the run caught, not the read: specs pushed into the `default` tenant at runtime were
  gone after a restart while their journals persisted. No document said either way. Only a restart
  under observation finds a row like that.

## Decision

1. **A re-pin's fidelity review is scoped.** The reviewer independently repeats the source diff
   between the two pins on their own clone, with both SHAs stated in the PR. Only if their result
   matches the author's stated result do unchanged files keep their existing quotes unreviewed. Any
   mismatch escalates to a full §4 review.
2. **New and changed claims get the full §4 treatment.** The Boundaries state-inventory table gets a
   row-by-row source-or-observation check regardless of what the diff says.
3. **A re-pin does not bump the body version in the target list.** It records both pin dates in the
   pinned-SHA table. A version bump means the body was rewritten, not that the pin moved.
4. **A re-pin lands in one PR with any Embodiment work done at the same SHA.** Splitting them lets the
   run and the pin disagree about which commit was observed.

## Consequences

- Re-pins become cheap enough to do on a cadence. Attention goes to what changed.
- The scope decision rests on one mechanical check. A reviewer who skips it produces something worse
  than no review, because the result reads as reviewed. The PR must show the diff command and its
  output verbatim.
- Known gap: no cadence is set. A `version-changing` spec has no trigger for a re-pin other than
  someone noticing. That is a separate decision.
- Known gap: nothing here covers concept documents, which cite several specs at once
  (`docs/research/SKILL.md` §5).

## Alternatives considered

- **Full §4 review on every re-pin.** Safe, but spends most of an hour on quotes proven unchanged.
  Under time pressure it gets skipped outright, which is worse than a scoped review done properly.
- **Author-only re-pin, no review.** Rejected. The PATCH/PUT row shows the author's own re-read misses
  rows that were inferred rather than sourced.
- **Keep the old spec and add a versioned copy.** Rejected. Git already holds the history, two files
  invite drift between them, and every concept document would have to cite both.
