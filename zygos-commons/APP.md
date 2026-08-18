# zygos-commons

HarnessSpec entity — shared data model for AI agent harness specifications.

## Entity Types

### HarnessSpec
Structured specification of an AI agent harness. Tracks identity, section bodies, axis classification, embodiment level, fidelity-review outcome, and lifecycle state (Draft → UnderReview → Published → Archived). Each section is written via its own action, enabling the synthesize-harness skill to compose specs through discrete Temper API calls.

- **States**: Draft → UnderReview → Published → Archived
- **Completeness guard**: `SubmitForReview` requires all thirteen gated sections present (identity, philosophy, primitives, loop, boundaries, verification, axis, economics, tradeoffs, what-to-steal, what-not-to, limits, sources). Embodiment is optional per FORMAT.md §4.3.
- **Fidelity gate**: `Publish` requires `fidelity_review_passed = true`, set by `RecordFidelityReviewPassed` and cleared by `RecordFidelityReviewFailed` / `Revise`.
- **Key actions**: `SetIdentity`, `WritePhilosophy`, `WritePrimitivesSection`, `WriteLoop`, `WriteBoundaries`, `WriteVerification`, `SetAxis`, `WriteEconomics`, `WriteTradeoffs`, `WriteWhatToSteal`, `WriteWhatNotTo`, `SetEmbodiment`, `WriteLimits`, `WriteSources`, `SubmitForReview`, `RecordFidelityReviewPassed`, `RecordFidelityReviewFailed`, `ReviseDraft`, `Publish`, `Revise`, `Archive`

## Setup

Depends on `paw-fs` for file storage. This is a zygos-specific app — not part of the TemperPaw core.
