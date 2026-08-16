---
adr: 0001
title: A guard checks presence and shape, never truth — design the schema for that ceiling
status: accepted
date: 2026-08-16
---

# ADR-0001 — A guard checks presence and shape, never truth

## Status

Accepted.

## Context

zygos's format is modeled on katagami's, which is built on a runtime (Temper) that enforces structure
at the platform level. Katagami's own README states the mechanism directly: its `SubmitForReview`
transition *"has guards — it checks that all five spec sections and the embodiment exist. If anything's
missing, the transition is rejected. The agent can't skip steps or publish garbage because the rules
are enforced at the platform level."*

That sentence is easy to over-read. The guard checks that five sections **exist** and that an
**embodiment** was generated. It does not, and structurally cannot, check that the Philosophy section's
quote is representative, that the Tokens are the ones the research actually surfaced, or that the
embodiment matches the spec's own Rules — katagami's own pipeline routes that concern to a *separate*
`review-quality` job, run by a different agent, precisely because presence-checking doesn't cover it.

zygos has no runtime under it in v1. There is no guard, no transition, no rejection — a spec is
"published" by being a well-formed markdown file in `docs/research/harnesses/`. The risk this ADR
addresses is not that zygos lacks enforcement today; every research library starts there. The risk is
writing a schema that *implies* more enforcement than a future guard, if built, could ever actually
deliver — which would repeat, one level up, the exact failure `provenance`/`verified_at`/`lifecycle`
exist to catch: precision that reads as verification without being verification.

## Decision

Classify every field and section in the zygos spec format (`DESIGN.md` §4) into one of two categories,
and say so in the design document itself rather than leaving it implicit:

**Mechanically checkable, in principle, by a guard with no judgment:**

- All required sections present and non-empty
- `Limits of this record` present and non-empty
- Frontmatter enum fields valid (`lifecycle`, `provenance`, `axis`, `kind`)
- `artifact_url` matches a 40-hex commit SHA, not a branch ref
- Every direct quote in the body carries a source anchor that resolves against an entry in the
  spec's own Sources table

**Requires judgment — a guard cannot check these no matter how the schema is built:**

- Whether `provenance: primary` reflects a source actually opened, versus asserted
- Whether an axis classification is correct, rather than merely present
- Whether a quote is representative of the project's position, rather than cherry-picked
- Whether a state-inventory table in `Boundaries` is complete, rather than merely formatted like one
- Whether `Economics` says something true about cost, rather than merely occupying the heading

## Consequences

**Positive**

- The schema (`DESIGN.md` §4–§5) states its own ceiling. A reader — or a future implementer building
  an actual guard on top of this format — knows in advance which half of quality control a machine
  check could ever cover.
- It prevents the format from silently promising what katagami's presence-guard already doesn't
  promise. Katagami's own two-job split (`review-quality` runs separately from `SubmitForReview`) is
  independent evidence for the same boundary: even a platform with guards routes the judgment work to
  a distinct check, not the guard.
- It gives a concrete target if zygos ever gets a runtime under it: build the left column first,
  because it is tractable, and do not claim the right column is covered by doing so.

**Negative**

- Every field in v1 is still author-asserted, exactly as in the discipline zygos inherits. Naming what
  *could* be checked later does not check anything *now*. This ADR is a design constraint on the
  schema, not a present capability — stating that plainly is the point, not a hedge.
- The mechanically-checkable column is the smaller one. A reader could take that as pessimism about
  automation; it is instead the accurate answer, and a schema sized to imply otherwise would be the
  worse failure.

**Known gap**

This ADR is about **soundness of the schema against future enforcement**, not about the specs
themselves being correct today. A spec can satisfy every item in the left column — five sections
present, quotes anchored, SHA pinned — and still be wrong throughout, the same way a syntactically
valid program can be wrong. The left column catches malformed specs; only a human reading against the
primary source catches wrong ones. Confusing the two is exactly the error this ADR exists to prevent
one level up.

## Alternatives considered

- **Design the schema without naming this boundary at all**, on the theory that v1 has no guard so the
  distinction is premature. Rejected: the schema is the thing a future guard would be built against: if
  the boundary isn't drawn now, a first implementation attempt would have to guess it, likely by
  building only what's tractable and calling it "enforcement" — the same overclaim, deferred rather
  than avoided.
- **Claim v1 already enforces structure**, since a mandatory-non-empty rule is itself a form of guard
  a human author can apply by hand. Rejected: a human choosing to follow a rule is a convention, and
  pavlos's own ADR-0001 already establishes why a convention doesn't reliably catch what a mechanical
  check would — "cite your sources" is advice a writer under time pressure can satisfy in appearance.
- **Wait until a runtime exists under zygos to write this down.** Rejected: the schema in `DESIGN.md`
  §4 is being fixed now, across the first several specs; retrofitting a presence/judgment split onto an
  existing set of fields is a bigger change than designing the fields with the split in mind from spec
  one.
