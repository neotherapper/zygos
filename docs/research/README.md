# Target list

| Harness | `kind` | Why it's on the list | Status | Spec |
|---|---|---|---|---|
| **exo** | agent-harness | Fully recursive self-editing agent + harness | done (v1 body, `embodiment: none`) | [`harnesses/exo.md`](harnesses/exo.md) — **two-track** ① |
| **Temper** | agent-substrate | Formal verification of agent-authored capabilities — the only proved-before-running design on the list | done (v1 body, `embodiment: partial`; re-pinned 2026-09-02) | [`harnesses/temper.md`](harnesses/temper.md) — **two-track** ① |
| **RLM** | inference-paradigm | Recursive context decomposition as an alternative to tool-calling entirely | done (v1 body, `embodiment: none`) | [`harnesses/rlm.md`](harnesses/rlm.md) |
| **DeepSeek Harness** | agent-harness | Plugin-composable architecture from a frontier lab; candidate third instance of "the log is the program" | done (v1 body, `embodiment: none`) | [`harnesses/deepseek-harness.md`](harnesses/deepseek-harness.md) |
| **pi** | agent-harness | Named by the owner; exo's README places "Pi" alongside OpenClaw and Hermes as a personal-runtime-class harness. **Now resolved (2026-08-29):** Pi is **Earendil Inc's "Pi Coding Agent"** — a terminal-based coding agent at pi.dev, source at `github.com/earendil-works/pi` (harness in `packages/coding-agent`, npm `@earendil-works/pi-coding-agent`, MIT). Pinned below | done (v1 body, `embodiment: none`) | [`harnesses/pi.md`](harnesses/pi.md) |

> ① **Two-track publication (2026-08-28, Phase 2 backfill).** Two publication paths coexist for exo
> and temper: the hand-merged `harnesses/exo.md` / `harnesses/temper.md` (git-committed content authored
> 2026-08-16) and the entity-backed versions published through the Phase 2 backfill (`HarnessSpec`
> entities re-imported from the markdown and re-rendered). The re-rendered entity output is
> byte-identical to the hand-merged file after whitespace normalization, except the inline `# comment`
> lines in the hand-merged frontmatter, which the entity schema has no field to carry (the substantive
> `axis`/`embodiment`/`status` justification lives in the body sections, which round-trip verbatim). See
> `docs/adrs/0002-temper-backed-curation-pipeline.md` Addendum 2026-08-27 §"Recommendation on Phase 2"
> and `docs/superpowers/plans/2026-08-28-backfill-phase1-specs-findings.md`. The hand-merged files
> remain canonical until the backfill is verified and a deletion decision is made; deletion is a
> separate decision per ADR-0002.

Temper, RLM and DeepSeek Harness are chosen to bracket the design space — proved-before-running,
recursive-self-editing (already covered by exo), everything-is-a-plugin — rather than sample it.

**Economics is load-bearing for the DeepSeek Harness spec, more than the format's default.** pavlos
carries a candidate requirement (R8, medium-confidence: compaction must preserve provider prefix
reuse) drawn from two dsh design notes read directly, not yet backed by a spec. This spec's Economics
section is that backing — it either confirms R8 or kills it. Read the compaction/caching material with
that question open, not as a general pass.

`best-of-Agent-Harnesses` is a discovery source for future targets, not a subject of its own spec —
see `FORMAT.md` §3 (Non-Goals: breadth).

## Pinned commits

Read at these SHAs, not `main`, per rule 1. RLM and DeepSeek Harness are now done; pi is the next
target. All confirmed to resolve (`curl -sI` against raw.githubusercontent.com):

| Harness | Repo | SHA | Resolved? |
|---|---|---|---|
| Temper | `nerdsane/temper` | `ff0774f572197a75987f3329b48553ae9f8b3c29` | ✅ 2026-09-02 (re-pin; first pin `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` ✅ 2026-08-16) |
| RLM | `alexzhang13/rlm` | `caf0bffa1acec17c062559433b4cd4ed92eee3d6` | ✅ 2026-08-16 |
| DeepSeek Harness | `deepseek-ai/deepseek-harness` | `47f943859bef60e4160492346772ded9b24f765a` | ✅ 2026-08-16 |
| pi | `earendil-works/pi` | `853a80d26c90a14c1886f0ebb8ffaae133ca2185` | ✅ 2026-08-29 |

Confirming a SHA resolves confirms the *coordinate*, not the *content* — still read the file at that
pin before citing anything from it, per rule 1.

## Temper pass — outcome against the prep notes

Prep notes (below, superseded by [`harnesses/temper.md`](harnesses/temper.md)) predicted three things;
here's how each landed:

- **Read past the README.** Did — `docs/PAPER.md` and `docs/POSITIONING.md` read in full. The
  verification cascade is specified there in real depth (four levels, gate points named precisely) —
  the README's version is a fair but compressed summary.
- **The two unsourced precise claims.** Confirmed unsourced — neither appears in `PAPER.md`'s
  Evaluation section, which has real Criterion-benchmarked numbers but not these two. Quoted and
  attributed as the project's own self-description in the spec's Limits section, not treated as
  verified.
- **Economics-empty-twice prediction: half right.** Not empty — but not what the format's default
  question expects either. Temper has a real cost model for its own backend (query/cache optimizers,
  telemetry cardinality decoupling) and none at all for LLM token/prompt economics. See the spec's
  Economics section for the distinction; it's the more interesting finding than either "empty" or
  "present" alone would have been.

One thing the prep notes missed entirely: `docs/HARNESS.md` is Temper's own *development* harness (gates
on people building Temper itself), not the product's agent-facing surface — a name-vs-thing trap, caught
during the pass and flagged explicitly in the spec's Limits section rather than silently avoided.
