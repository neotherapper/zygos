---
name: temper
title: "Temper"
url: https://github.com/nerdsane/temper
artifact_url: https://github.com/nerdsane/temper/tree/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400
commit: 2f43ecefaa00bf2e9d75c6b67c2ddf8857821400
language: Rust
kind: agent-substrate               # its own README: "Not the runtime the agent runs in"
license: MIT / Apache-2.0
status: pre-release                 # project's own words: "Version 0.1.0... API surface is not frozen"
lifecycle: version-changing
provenance: primary
verified_at: 2026-08-16
axis: [A]                           # A, and — unlike exo — prevention, not only recovery. See "Which axis"
primitives: [capability, spec, actor, event-journal, transition-table, cedar-policy, pending-decision, o-p-a-d-i-record, trajectory, gepa]
embodiment: none                    # no hands-on run — see "Embodiment" and "Limits of this record"
---

# Temper

## Philosophy

Temper's stated hypothesis is narrower than "verify everything": *"a large class of the tools agents
build, and a large class of the applications developers build, share this structure"* — the structure
being a state machine. Everything else follows from taking that hypothesis seriously: *"If the state
machine is the essential artifact... verification becomes tractable. You can prove, before anything
runs, that every rule is satisfiable, every constraint holds across all reachable statuses, and no
failure scenario violates the contract. You cannot do this for arbitrary code in general. You can do
it for state machines."*

The design explicitly borrows its shape from Von Neumann's 1949 universal-constructor argument: a
*description* that encodes a blueprint, a *constructor* that builds whatever a description encodes
without knowing in advance what that is, and evolution as changes to descriptions rather than to the
constructor. `docs/PAPER.md` states the mapping directly: *"The kernel is the constructor... The kernel
does not know whether you are building a project tracker or a deployment pipeline. It interprets
whatever you feed it."* This is the same move exo makes at the exoharness/executor boundary — a
generic, minimal, trusted layer that stays ignorant of the semantics running above it — arrived at from
a different argument (proof tractability, not containment) and applied to a different kind of thing
(a state-machine constructor, not an event-log substrate).

**What it refuses to do**, stated in its own words in a table titled *"What Temper is and is not"*:
*"Not the runtime the agent runs in"* (that's a harness CLI's job); *"Not a framework for the agent
loop"* (SDKs and harnesses handle prompts and conversation; Temper holds what the loop calls into);
*"Not a backend-as-a-service"* (a BaaS gives CRUD from an implicit schema; Temper compiles a runtime
from an explicit, verified behavioral contract); *"Not a workflow builder"* (no imperative or visual
flow editor — capabilities are declared state machines). Each refusal narrows the same way: Temper will
not absorb a responsibility that would force it to accept unverifiable input.

**The trust gradient is named as a five-step chain**, and each step is stated to depend on the one
before it: *"unverified → verified → governed → evolving → trust-calibrated... Governance assumes
verification. Evolution assumes governance. Trust calibration assumes evolution data."* This is worth
holding next to exo's philosophy: exo's chain has no such ordering — self-modification is available
immediately, and recoverability is the backstop. Temper's chain gates each capability on the previous
one actually holding.

## Primitives

| Primitive | What it is | Why it matters |
|---|---|---|
| **Capability** | A verified, deployed description: natural-language description + agent guidance + one or more I/O Automaton specs + a CSDL data model + Cedar policies + integration declarations | The unit an agent operates through. `docs/PAPER.md` §3: *"The natural language description and guidance are what agents and humans read. The specifications are what the kernel verifies and executes"* — two audiences, one artifact |
| **Spec (IOA + CSDL + Cedar)** | Three declarative, non-imperative artifacts: I/O Automaton TOML (states/transitions/guards/invariants), CSDL XML (entity types, actions, relationships), Cedar (authorization policy) | *"Nothing in this layer is imperative code."* The spec is simultaneously the verification target and the runtime execution artifact — not two things kept in sync, one thing read two ways |
| **Actor** | One lightweight, per-entity-instance process; messages handled strictly sequentially, no concurrent state access | *"if the transition table is correct and the initial state is valid, then every reachable state is valid"* — the sequential-consistency guarantee is what makes the proof apply to the running system, not just the model |
| **Event journal + snapshot** | Every transition persisted as an event to Postgres; periodic snapshots bound replay time; compaction truncates events once the count since last snapshot exceeds a threshold | The durable record actor state rebuilds from on restart. Bounded by construction (TigerStyle), not by an operator remembering to prune |
| **TransitionTable (three-tier)** | Tier 1 compiled Rust (codegen, needs rebuild); Tier 2 interpretable (data structure, built from the same `Automaton`); Tier 3 overlay — hot-swappable via `SwapController`, atomic, versioned, no restart | The tier that actually serves traffic (Tier 2/3) derives from the *same* struct the verification cascade checks — "provable equivalence" by shared derivation, not by discipline |
| **Cedar policy / pending decision** | Default-deny authorization; an unpermitted action becomes a pending decision surfaced to a human; approval is scoped narrow / medium / broad and hot-loaded as a generated policy | Capability without pre-anticipated policy — the policy set is built reactively from what an agent actually tries, with a human retaining every scope expansion |
| **O-P-A-D-I record chain** | Observation → Problem → Analysis → Decision → Impact, immutable, linked, dual-written to Git and Postgres | Every spec change traces back to the telemetry that motivated it. `validate_chain` walks a leaf back to its root and checks the type ordering and that no link is broken |
| **Trajectory** | The full sequence of API calls an agent makes in one turn, with a `TrajectoryOutcome` (completed/failed/pivoted/abandoned), feedback score, token count, API call count | Product signal, not a cost-control mechanism — see Economics. Feeds two optimization loops (agent guidance, API shape), not caching or spend |
| **GEPA (evolution engine)** | Replays captured trajectories against current specs, clusters failure patterns, proposes a spec diff | The mechanism that closes Von Neumann's "changes to the description, not the constructor" loop from production use back into the next description |

## Loop

Two nested loops, at different timescales.

**Per-action loop (an agent operating through a deployed capability).** An agent reaches Temper over
HTTP/OData directly, an SDK, or the `temper mcp` stdio bridge — *"a sandboxed Python REPL with a
`temper.* ` API for submitting specs, creating entities, and invoking actions."* A representative
sequence from the reference app: `POST /tdata/Orders` spawns an actor in `Draft`; `POST .../AddItem`
mutates state and appends an event; `POST .../SubmitOrder` a second time from `Submitted` returns `409`
— the guard rejected it, not application code. Each call: Cedar authorizes (default-deny) → the
`TransitionTable` checks the `from_states` guard and the semantic guard → effects apply → the event
persists to Postgres → the `IntegrationEngine` dispatches any declared external side effects
*asynchronously, after* the transition is committed — *"the outbox pattern ensures side effects cannot
violate state machine invariants because they execute after the transition is persisted, not during
guard evaluation."* Discovery is self-describing: an agent reads `$metadata` and gets the full typed
surface, including `Agent.Hint` and `Agent.SuccessRate` annotations populated from trajectory data —
no external documentation required, by the CSDL layer's own design intent.

**Per-spec loop (a developer, or a coding agent on a developer's behalf, changing what exists).**
`docs/AGENT_GUIDE.md` states it as a fixed six-step cycle: *CONVERSE → GENERATE → VERIFY → REVIEW →
ITERATE → DEPLOY.* *"The developer never writes specs by hand. They describe their domain through
conversation."* Deploy has two paths: self-host (`temper codegen` → `cargo build` → operator deploys
the binary) or platform-host (`temper serve --specs-dir` — the serve command itself runs the full
verification cascade at startup and *"invalid specs are rejected at startup, never loaded into the
runtime"*).

**Evolution loop (production feeds the next spec).** A sentinel actor observes an anomaly →
O-Record → P-Record (formal problem statement) → A-Record (solution options with a spec diff and risk
level) → D-Record (human approval, required for anything that *"alters state machine invariants,
removes entity types, or modifies Cedar policies"*) → deploy through the same verification cascade.
Non-destructive tuning (query plans, cache TTLs, shard placement) runs a separate, faster loop: three
optimizer actors propose changes tiered by risk — `Risk::None` auto-approved, `Risk::Low` auto-approved
only above a stated 10% estimated-improvement threshold, `Risk::Medium` *"never auto-approved"* and
routed through shadow testing first (see Verification).

## Boundaries

**Trusted vs swappable**, in the same shape as exo's exoharness/executor split but drawn on different
grounds: the kernel (spec parser, verification cascade, actor runtime, authorization engine, event
sourcing) is the constructor and does not change per-app; specs, data models, policies, and application
WASM modules are what an agent or developer supplies and what hot-reloads. *"The kernel does not know
whether you are building a project tracker or a deployment pipeline."*

**Sandboxing.** Application logic (the fourth spec part, "what runs inside the state machine") runs as
sandboxed WASM modules with per-call resource budgets, triggered inline by transitions but with external
side effects deferred to the outbox pattern described in Loop — network calls are structurally kept out
of guard evaluation and effect application.

**What survives what.** Temper has no single named "reset" primitive the way exo has sandbox rewind;
the closest analogue is process/actor restart, and the record is explicit about the boundary:

| State category | Survives actor crash / process restart? |
|---|---|
| Event journal (Postgres) | Yes — the durable record; actors rebuild state by replay |
| Actor state (in-memory) | Rebuilt from journal + latest snapshot, not itself persisted |
| In-flight mailbox messages (`tokio::mpsc`) | **No** — lost on crash. `docs/AGENT_GUIDE.md` states the mitigation directly: *"the HTTP caller gets a connection error... the caller retries — the actor is back at the last committed state"* |
| Cedar policies | Yes — hot-loaded and, by the same durability argument applied to specs generally, not re-derived per restart |
| Evolution records (O-P-A-D-I) | Yes — dual-written to Git and Postgres |
| Trajectory / telemetry data | Yes — separate OTEL/ClickHouse store |

Exactly one row is explicitly named as lossy, and the project states the mitigation in the same breath
rather than leaving it implicit — the same shape as exo's "no (that is the point)" annotation on its
one non-surviving row, arrived at for a different reason (an at-least-once-retry contract, not a
designed reset).

**Blast radius / autonomy gradient.** Authorization is default-deny; every unpermitted action becomes a
pending decision, not a silent failure. Human approval is required for any spec change that alters
invariants, removes entity types, or changes Cedar policy — stated as *"a deliberate design
constraint: the system may autonomously observe, formalize problems, analyze root causes, and propose
solutions, but it may not unilaterally implement changes that affect correctness."* Below that line,
autonomy is explicit and tiered by risk rather than binary (see Loop).

**Scale boundary, stated plainly.** *"Single-node architecture. The current runtime is single-process.
Actor mailboxes use local `tokio::sync::mpsc` channels, not Redis."* The `temper-store-redis` crate
defines the traits for a distributed future with in-memory stubs; `REDIS_URL` *"is not read by the
server today."* This is named directly rather than left to be discovered by an operator who sets the
variable and finds nothing happens.

## Verification strategy

| Method | Present? | Notes |
|---|---|---|
| Observability-driven feedback | **Yes, gated** | GEPA replays trajectories, proposes spec diffs via the O-P-A-D-I chain — but a destructive diff requires a human D-Record before it deploys. Non-destructive optimizer output is gated by risk tier and a `SafetyChecker`, not applied unconditionally |
| Shadow evaluation | **Yes, gates a hot-swap** | `shadow_test` runs a suite of test cases against *both* the old and new `TransitionTable` before a Tier-3 overlay swap; any mismatch is a `Mismatch`, and the swap proceeds *"only if the `ShadowResult` reports zero mismatches (or the mismatches are explicitly expected)."` This is the exact "canary path — run the changed build against a clone and compare before adopting on the live instance" that exo's own record names as a gap it doesn't have |
| Deterministic simulation testing | **Yes, gates** | Level 2 of the cascade: seeded xorshift64 PRNG, a tick-based `SimScheduler`, three fault profiles (`none`/`light`/`heavy` — up to 30% delay, 5% drop, 2% crash). Reproducible by seed. Runs pre-deploy as part of the cascade, and separately as the project's own *development* methodology (DST-first, per the dev-harness docs) |
| Formal specification | **Yes, gates** | Level 0 (Z3 SMT: guard satisfiability, invariant induction, unreachable-state detection) and Level 1 (Stateright: exhaustive BFS over the bounded state space, safety + liveness properties, counterexample traces) |

**What gates vs what reports, stated precisely.** All four cascade levels (L0–L3) must pass before a
spec deploys — enforced twice: as a blocking pre-commit-style hook during development (`ALL FOUR must
pass → Edit allowed / ANY failure → Edit BLOCKED`) and again at the platform boundary (`temper serve`
rejects invalid specs at startup, never loads them). Shadow testing gates the separate hot-swap path
for non-cascade tuning changes. The human D-Record gate covers the fourth path (evolution-proposed
destructive changes). The only reporting-only mechanism is trajectory telemetry itself — it feeds
`Agent.Hint`/`Agent.SuccessRate` annotations and the GEPA's proposals, but a proposal is not an applied
change; something downstream always gates it. Measured against exo's profile — instrumentation genuinely
good, but *"the agent closes the loop... nothing acts on a signal automatically"* — Temper's default is
inverted: the mechanism, not the agent's judgment, is what applies or blocks a change.

## Which axis

**Axis A, and it is prevention, not recovery** — the polar opposite of exo's profile.

| | Prevents entering a broken state | Restores from a broken state |
|---|---|---|
| exo | no | yes, by construction |
| Temper | **yes, for specs — proof before deploy** | yes, but only for infrastructure crashes (event replay), not for a bad spec |

The proof is the load-bearing claim: *"You can prove, before anything runs, that every rule is
satisfiable, every constraint holds across all reachable statuses, and no failure scenario violates the
contract."* A spec that fails any cascade level is never loaded into the runtime — there is no "broken
spec state" to recover from, because it never reaches a state where it could enter one. Where Temper
*does* offer recovery is a different, narrower layer entirely: actor state after a process crash,
rebuilt from the event journal. That recovery mechanism says nothing about whether the spec being
recovered is *correct* — it only guarantees the actor comes back to its last committed, already-verified
state.

This is direct evidence toward the open question pavlos's own research raised across records: are
prevention and recovery opposed, or complementary at different layers? Temper's own architecture answers
it by example rather than argument — prevention operates on the spec/behavior layer, recovery operates
on the process/infrastructure layer, and the two never substitute for each other because they answer
different questions ("is this contract sound?" vs. "did this process survive?").

**Axis B is absent and undiscussed, same as exo.** Nothing in the material read evaluates whether a
capability's data — an order total, a payment status, a claim an agent's application logic asserts about
the external world through an integration — is *true*. Cedar governs who may call an action; the
verification cascade proves the state machine's own rules hold; neither touches whether the content
flowing through it is factually correct. An agent could authorize, verify, and execute a transition
built entirely on a false premise, and nothing in the read material would notice.

## Economics

More present than exo's record, but not where the format's default question points, and that
distinction is the finding. **Nothing in the material read discusses LLM prompt or token economics** —
no prompt caching, no compaction strategy, no discussion of what fraction of a conversational turn is
repeated prefix. Pavlos-init's prediction (Economics comes back empty a second time) is only half
right, and the half that's wrong is informative:

- **System-level cost optimization exists and is real, at the infrastructure layer.** A `CacheOptimizer`
  actor analyzes hit/miss rates and adjusts TTLs; a `QueryOptimizer` detects N+1 patterns; both are
  gated by risk tier (see Loop). This is genuine cost-as-a-design-property machinery — it is simply
  aimed at Temper's own backend (Postgres queries, cache TTLs), not at the token cost of the agent
  conversation reaching it.
- **Telemetry cardinality has an explicit, named cost-decoupling design.** §9.4 of `docs/PAPER.md`:
  treating `entity_id` as an Attribute rather than a Tag by default is *"zero cost — not a metric tag,
  no cardinality explosion"* — promotable to a Tag at runtime *"if [an operator] decides the cost is
  worth it."* Cost is a first-class, deferred decision here, just not an LLM-token one.
  ​
- **Trajectory records carry `token count` as a field** — but as a *telemetry signal* feeding agent-hint
  and API-shape optimization (§7.2), not as an input to any caching, compaction, or spend-reduction
  mechanism. The number is observed, not acted on for cost.
- **One indirect economics argument for the API shape itself:** CSDL/OData was chosen over GraphQL
  partly because GraphQL's query flexibility *"becomes a liability for agents, which must reason about
  query structure, cost, and output validity on every call"* — a reasoning-cost argument for the agent,
  made once, at the level of API design rather than runtime behavior.

Read plainly: Temper has a cost model, but it is a *backend infrastructure* cost model inherited from
building a database-backed API server, not an *agent-conversation* cost model. A harness whose primary
interface to an agent is HTTP/OData or an MCP stdio bridge apparently has not needed one yet at 0.1.0 —
or the material read does not surface it. Two specs is enough to say the section isn't universally
empty (system economics is real here); it is not yet enough to say whether LLM-token economics is a
gap specific to these two projects or absent from the field's early designs generally.

## Tradeoffs

**Buys**

- Proof before deploy, not test-after-deploy. Whole classes of state-machine bugs — dead guards,
  non-inductive invariants, unreachable states — are eliminated before a spec is ever loaded, not
  caught in production.
- Shadow-tested hot-swap. Unlike a design that validates a change on the only running copy, Temper runs
  the new artifact against recorded cases beside the old one and blocks on any mismatch.
- Bounded execution everywhere, by construction (TigerStyle): mailbox capacity, `MAX_ITEMS`, snapshot
  compaction thresholds, sim queue bounds. An entire failure class — unbounded queues, unbounded caches,
  unbounded replay logs — is a build-time decision, not a monitoring target.
- Self-describing API. An agent reads `$metadata` and gets the complete typed surface plus
  usage-derived hints, without external documentation.
- Institutional memory with evidentiary chain. Every spec change traces to the O-Record that motivated
  it; `validate_chain` makes a broken or fabricated provenance link mechanically detectable, not just
  conventionally discouraged.
- Same artifact, two roles. The struct the cascade verifies is the struct the runtime executes — not
  two implementations kept in sync by discipline.

**Pays**

- Constrained expressiveness, named by the project itself: no floating-point state (prices live in
  payload, not state), no conditional effects without decomposing into guarded actions, no temporal
  guards without scheduled actions, single-node only. *"Some of these are fundamental to finite
  automata. Others are engineering work"* — the record does not know which is which for any given
  future need.
- An extra layer of indirection between intent and artifact. Specs are generated by a coding agent from
  conversation, not hand-authored — the opposite of exo's position, where the agent edits its own
  harness directly. Faster iteration requires trusting the generation step, which sits outside anything
  the cascade verifies (the cascade checks the spec, not the conversation that produced it).
- Real latency cost from durability. Postgres event append dominates end-to-end latency at ~1.4ms per
  action, roughly 50× the in-memory actor dispatch path (~28ns) — the tradeoff of durability-first
  design made visible in the project's own benchmarks, not hidden.
- The pitched conversational experience — *"you describe what you want, the system builds it"* — is
  explicitly *"partially implemented"* and *"dependent on the coding agent of choice."* Today's actual
  path is closer to a coding agent authoring specs on a developer's behalf than to a from-scratch
  natural-language interface.
- All the operational weight of a Postgres-backed multi-crate Rust service (22+ crates, Docker Compose
  for Postgres/Redis-stub/ClickHouse/OTEL) for what a single verified capability needs to run.

## What to steal

1. **Derive the verification target and the runtime artifact from the same struct.** Temper's
   `TemperModel` (checked by Stateright) and its `TransitionTable` (executed at runtime) both parse from
   one `Automaton`. "Provable equivalence" here means the two can't drift apart the way two independent
   implementations can — there's only one implementation, read two ways. This generalizes past state
   machines: wherever a system needs "the thing I verified is the thing that ran," make it the same
   artifact rather than a second one kept in sync by policy.

2. **Shadow-test before a hot-swap, with an explicit pass condition.** Run the new artifact against a
   fixed suite of cases beside the old one; block unless the result set matches (or a mismatch is
   explicitly declared expected). This is exo's named gap, implemented: validate on a comparison, not on
   the only running copy.

3. **Tier autonomy by risk, with a stated numeric threshold, not a binary human/no-human split.**
   `Risk::None` auto-applies, `Risk::Low` auto-applies only above a named 10% improvement estimate,
   `Risk::Medium` is never auto-approved. Making the threshold a number rather than a policy-in-prose
   makes the autonomy boundary itself inspectable and arguable.

4. **Gate the human approval on a category of change, not on "any change."** Destructive changes
   (alters invariants, removes entity types, changes authorization) require a human D-Record; everything
   else can move faster. Naming the category precisely is what lets the system move quickly on the 90%
   of changes that aren't the dangerous 10%, instead of either gating everything or gating nothing.

5. **When a state category is lossy, say so in the same sentence as the mitigation.** The in-flight
   mailbox message row states *"lost on crash"* and *"the caller retries"* together, not as separate
   findings a reader has to reconcile. Same discipline exo's state-inventory table applies to its one
   non-surviving row — worth treating as a convention, not a coincidence, now that two independent
   projects do it.

## What not to

- **Do not adopt this for a domain that doesn't reduce to a state machine.** The project names its own
  boundary — no floats in state, no conditional effects without decomposition, no temporal guards yet.
  E-commerce order/payment/shipment fits the shape; not everything does, and the constraint is real, not
  an early-stage placeholder that will disappear with more engineering.
- **Do not port "the developer just converses and the system builds it" as the current experience.**
  It is the stated vision, explicitly flagged *"partially implemented"* and dependent on which coding
  agent is in the loop. Porting the pitch without the qualifier is the same failure shape as porting
  exo's "the log is the only thing it can't muck with" without its footnote.
- **Do not assume multi-node readiness.** Single-process today; Redis-backed distribution is designed
  (traits exist) but explicitly not wired (`REDIS_URL` unread). A deployment that needs horizontal scale
  today needs a different substrate or a wait.
- **Do not treat the specific formalism choices (I/O Automata, CSDL, Cedar) as portable independent of
  the problem shape.** The project states a specific reason for each — precondition/effect mapping to
  the runtime model, a rigid contract chosen *because* it reduces agent reasoning burden, a
  `(principal, action, resource, context)` tuple matching the OData request shape. Those reasons are
  about this problem's shape; a different domain may not share them.
- **Do not read the Economics section as "harnesses don't think about cost."** This spec's own finding
  is narrower: this harness has a real cost model, aimed at its own backend rather than at the LLM
  conversation reaching it. Generalizing to "the field ignores economics" from two records is exactly
  the kind of unsupported leap `DESIGN.md` warns against — see Limits.

## Embodiment

`embodiment: none`. Temper was not installed or run; nothing here is this record's own behavioral
evidence. Unlike exo, though, the project's own material includes a real, methodologically-disclosed
evaluation: Criterion benchmarks (100 samples) for the transition-table hot path (28ns–16μs range) and
full-stack agent-checkout latency (461μs in-memory; 17.7ms with Postgres persistence, ~2,200 persisted
actions/sec at 100 concurrent checkouts), 22 named DST tests including two determinism-reproducibility
proofs across ten runs, and three specific guard-resolution bugs the project's own DST-first process
caught before they would have shipped. That is stronger evidentiary standing than exo's record had —
but it is still the project's own reported results, not independently reproduced here, and is recorded
as such rather than as this spec's own finding. Per `DESIGN.md` §4.3, Embodiment stays optional until
four or more specs exist in the library or a claim here depends on a run to confirm; neither condition
is met.

## Limits of this record

- **Source read, code not read.** Every claim comes from `README.md`, `docs/PAPER.md` (read in full),
  `docs/POSITIONING.md` (read in full), and the sections of `docs/AGENT_GUIDE.md` covering core
  concepts, verification, and anti-patterns. The Rust implementation itself was not read. Whether the
  code matches the documentation — the same question that produced exo's central finding — is unchecked
  here.

- **165 ADRs under `docs/adrs/` were not read individually.** Only filenames were scanned from the
  repository tree to confirm nothing load-bearing was missed at the top level (e.g., confirming
  verification-cascade and DST-related ADR numbers exist). Any single ADR could sharpen, qualify, or
  contradict a claim synthesized here from `PAPER.md` — the same category of risk exo's record flagged
  for its own unread design-note files, at much larger scale.

- **`docs/HARNESS.md` describes Temper's own development harness — the dev-time hooks and gates for
  people building Temper itself — not what an agent gets when building *on* Temper.** ~200 of 610 lines
  were read, used only for the blocking/advisory/agent-review taxonomy referenced in passing in
  Verification, not as a description of the product's agent-facing primitives. The filename overlap with
  this library's own subject ("harness") is exactly the name-vs-thing trap this lab's own writing
  checklist warns about; flagged explicitly so a future reader doesn't inherit the conflation from a
  careless skim.

- **Two precise, self-sourced claims in the README have no artifact behind them in the material read.**
  *"Runs on every build, in well under a second on a small spec"* and *"Deployed on Railway; Katagami
  runs on it in production."* Neither appears in `docs/PAPER.md`'s Evaluation section, which has real
  benchmarks but no cascade-total-time measurement and no deployment-uptime data. Quoted and attributed
  above as the project's own self-description; not treated as independently verified.

- **No hands-on run.** `embodiment: none` reflects this exactly — see Embodiment above for what
  evidentiary standing the project's own disclosed benchmarks do and don't provide in place of one.

- **`lifecycle: version-changing`** on the project's own statement that *"the API surface is not
  frozen"* at 0.1.0, with an explicit "cannot do this yet" list the project expects to shrink. A record
  written against `2f43ece` should be assumed to drift, plausibly faster than exo's given the number of
  documents (600+) actively tracking design decisions in this repository.

- **Compared to exo, once, by me — not adjudicated by a third source.** The prevention-vs-recovery
  contrast and the "same artifact serves two roles" parallel to "the log is the program" are this
  record's own synthesis, built from having read both records, not from any source that compares the
  two projects itself. Pavlos's own Q3 (are prevention and recovery opposed or complementary at
  different layers?) is addressed above with a specific answer — complementary, at the spec layer vs.
  the infrastructure layer — but that answer rests on two data points and should be treated as a strong
  lead for the eventual concept document, not as settled by this record alone.

- **Economics finding rests on absence, checked by keyword search plus targeted reads, not exhaustive
  reading.** "No LLM-token economics discussion" was confirmed by grep across `PAPER.md`,
  `AGENT_GUIDE.md`, and `HARNESS.md` for cost/cache/token/prefix/compaction terms, then read in context
  wherever a hit appeared. A discussion using none of those terms would not have been found this way.

## Sources

All fetched as raw markdown pinned to commit `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400`, not to `main`
— a branch ref changes content silently and still resolves, so a link check cannot catch drift.

| Source | Type | Retrieved |
|---|---|---|
| [`README.md`](https://github.com/nerdsane/temper/blob/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400/README.md) | primary — project self-description, full read | 2026-08-16 |
| [`docs/PAPER.md`](https://github.com/nerdsane/temper/blob/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400/docs/PAPER.md) | primary — full architecture paper, full read (all 12 sections) | 2026-08-16 |
| [`docs/POSITIONING.md`](https://github.com/nerdsane/temper/blob/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400/docs/POSITIONING.md) | primary — positioning statement, full read | 2026-08-16 |
| [`docs/AGENT_GUIDE.md`](https://github.com/nerdsane/temper/blob/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400/docs/AGENT_GUIDE.md) | primary — sections 1 (Core Concepts) and 16 (Anti-Patterns) read; remainder scanned by heading only | 2026-08-16 |
| [`docs/HARNESS.md`](https://github.com/nerdsane/temper/blob/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400/docs/HARNESS.md) | primary — first ~200 of 610 lines read; this is Temper's own dev-time harness, not the product's agent-facing surface — see Limits | 2026-08-16 |
| Repository tree at `2f43ece` (GitHub API, recursive) | primary — used to enumerate docs and confirm the 165-ADR count; ADR bodies not read | 2026-08-16 |

**Cross-reference:** `docs/research/harnesses/exo.md` in this repository, read in full before this
record was written, for every comparison drawn above.
