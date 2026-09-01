---
name: temper
title: "Temper"
url: https://github.com/nerdsane/temper
artifact_url: https://github.com/nerdsane/temper/tree/ff0774f572197a75987f3329b48553ae9f8b3c29
commit: ff0774f572197a75987f3329b48553ae9f8b3c29
language: Rust
kind: agent-substrate               # its own README: "Not the runtime the agent runs in"
license: MIT / Apache-2.0
status: pre-release                 # project's own words: "Version 0.1.0... API surface is not frozen"
lifecycle: version-changing
provenance: primary
verified_at: 2026-09-02
axis: [A]                           # A — prevention-primary, with a live rollback backstop. See "Which axis"
primitives: [capability, spec, actor, event-journal, transition-table, cedar-policy, pending-decision, o-p-a-d-i-record, trajectory, gepa]
embodiment: partial                 # built and run locally at the pinned commit, one reference app — see "Embodiment"
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
constructor. `docs/PAPER.md` states the mapping directly: *"In Temper, the kernel is the constructor.
It reads specifications and builds running systems from them."* `docs/POSITIONING.md` restates the same
position with the sharper line: *"The kernel does not know whether you are building a project tracker
or a deployment pipeline. It interprets whatever you feed it."* This is the same move exo makes at the
exoharness/executor boundary — a
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
| **Capability** | A verified, deployed description: natural-language description + agent guidance + one or more I/O Automaton specs + a CSDL data model + Cedar policies + integration declarations | The unit an agent operates through. `docs/POSITIONING.md`: *"The natural language description and guidance are what agents and humans read. The specifications are what the kernel verifies and executes"* — two audiences, one artifact |
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
*asynchronously, after* the transition is committed — *"the outbox pattern ensures that side effects
cannot violate state machine invariants because they execute after the transition is persisted, not
during guard evaluation or effect application."* Discovery is self-describing: an agent reads `$metadata` and gets the full typed
surface, including `Agent.Hint` and `Agent.SuccessRate` annotations populated from trajectory data —
no external documentation required, by the CSDL layer's own design intent.

**Per-spec loop (a developer, or a coding agent on a developer's behalf, changing what exists).**
`docs/AGENT_GUIDE.md` states it as a fixed six-step cycle: *CONVERSE → GENERATE → VERIFY → REVIEW →
ITERATE → DEPLOY.* *"The developer never writes specs by hand. They describe their domain through
conversation."* Deploy has two paths: self-host (`temper codegen` → `cargo build` → operator deploys
the binary) or platform-host (`temper serve --specs-dir`, or the `--app NAME=DIR` form that the CLI
help at `ff0774f` says supersedes it). The documents say the serve command runs the full verification
cascade at startup and refuses to serve unverified entities. The run recorded in Embodiment sharpened
that: the server starts serving *before* user-spec verification finishes (`Loaded spec: Order
(verification pending, lint clean)`, then `Verification: running in background`), and the refusal is
per request, not at startup — a dispatch on an entity type whose status is still pending or running is
rejected by the verification gate in `crates/temper-server/src/state/entity_ops.rs` until the cascade
reports every level passed. The kernel's own system-tenant specs are the exception: those are verified
synchronously at boot and a failure there is an assertion, not a gate.

**Evolution loop (production feeds the next spec).** A sentinel actor observes an anomaly →
O-Record → P-Record (formal problem statement) → A-Record (solution options with a spec diff and risk
level) → D-Record (human approval, required for what the project calls "destructive changes" —
*"those that alter state machine invariants, remove entity types, or modify Cedar policies"*) → deploy
through the same verification cascade.
Non-destructive tuning (query plans, cache TTLs, shard placement) runs a separate, faster loop: three
optimizer actors propose changes tiered by risk — `Risk::None` auto-approved, `Risk::Low` auto-approved
only above a stated 10% estimated-improvement threshold, `Risk::Medium` *"never auto-approved"* and
routed through shadow testing first (see Verification).

**The hot-swap step of that loop has a fifth stage this spec initially missed.** `docs/AGENT_GUIDE.md`
§12 states the Tier-2 (interpretable) hot-swap protocol as five steps, not the three (verify → shadow
test → swap) visible from `docs/PAPER.md` alone: *"1. Agent generates new TransitionTable from modified
spec. 2. Verification cascade runs on new table. 3. Shadow test: compare old and new tables on test
cases. 4. If shadow test passes: SwapController.swap(new_table). 5. If production degrades: automatic
rollback."* Step 5 matters more than its one line suggests — see Which axis.

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
the closest analogue is process/actor restart, and the spec is explicit about the boundary:

| State category | Survives actor crash / process restart? |
|---|---|
| Event journal (Postgres, or the default embedded libSQL file) | Yes — the durable record; actors rebuild state by replay. **Observed** (Embodiment rows 12–14): three events for one order, sequence 1–3, identical before and after a process restart, and the rebuilt actor enforces the same from-state rule. **Caveat at the original pin:** OData PATCH/PUT field updates skipped the journal until commit `cda632b` (upstream ADR-0157 "Journaled PATCH/PUT Field Updates", 2026-08-18), so at `2f43ece` a field update was lost on the next actor eviction or restart — ADR-0157's own words: *"every PATCH/PUT was silently lost the moment any of those ran."* Fixed fail-closed at `ff0774f`: an update that does not append is not acknowledged |
| Actor state (in-memory) | Rebuilt from journal + latest snapshot, not itself persisted |
| In-flight mailbox messages (`tokio::mpsc`) | **No** — lost on crash. `docs/AGENT_GUIDE.md` states the mitigation directly: *"the HTTP caller gets a connection error... the caller retries — the actor is back at the last committed state"* |
| Cedar policies | Yes — **observed**: five permits appended through the policy API were all present after restart |
| Pending decisions | Yes — **observed**: the decision minted by a denied create was listed as pending after restart, same id, still un-approvable by its own subject |
| Registered specs (transition tables) | **Depends on the path in, and this is not documented.** Specs the disk loader (`--app` / `--specs-dir`) persisted were restored at boot (`Restored 23 specs from Turso`). Specs pushed at runtime through `POST /api/specs/load-dir` were **not** there after restart on the default store: `crates/temper-server/src/observe/specs/load_dir.rs` persists *"when Postgres is configured"* and otherwise only registers in memory. Separately, specs loaded from disk into the `default` tenant were replaced at boot by the built-in agent specs (`crates/temper-cli/src/serve/bootstrap.rs` registers them into `default` with merge disabled), so `default` cannot hold user specs across a restart by either path. In both cases the entity journals survived; the table needed to fold them did not, until the spec was pushed again |
| Evolution records (O-P-A-D-I) | Yes — dual-written to Git and Postgres |
| Trajectory / telemetry data | Yes — separate OTEL/ClickHouse store |

The project names exactly one row as lossy (the mailbox) and states the mitigation in the same breath
rather than leaving it implicit — the same shape as exo's "no (that is the point)" annotation on its
one non-surviving row, arrived at for a different reason (an at-least-once-retry contract, not a
designed reset). The run added a second lossy row the documents do not name — runtime-pushed specs on
the default store — and it is the more surprising one, because the journal underneath it is intact and
the entity simply becomes unreadable until its spec is registered again. Nothing in the read material
warns an operator of this.

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
| Shadow evaluation | **Yes, gates a hot-swap** | `shadow_test` runs a suite of test cases against *both* the old and new `TransitionTable` before a Tier-3 overlay swap; any mismatch is a `Mismatch`, and the swap proceeds *"only if the `ShadowResult` reports zero mismatches (or the mismatches are explicitly expected)."` This is the exact "canary path — run the changed build against a clone and compare before adopting on the live instance" that exo's own spec names as a gap it doesn't have |
| Deterministic simulation testing | **Yes, gates** | Level 2 of the cascade: seeded xorshift64 PRNG, a tick-based `SimScheduler`, three fault profiles (`none`/`light`/`heavy` — up to 30% delay, 5% drop, 2% crash). Reproducible by seed. Runs pre-deploy as part of the cascade, and separately as the project's own *development* methodology (DST-first, per the dev-harness docs). Scope note from `.agents/skills/verify-temper/features/spec-cascade.md` at `ff0774f`: an actor-level simulation level (L2b, driving the real `TransitionTable::evaluate()`) is *"defined but not wired into the CLI/platform cascade today"*; actor-level DST coverage lives in thirteen standalone `dst_*` test suites instead. So the cascade a user's spec passes at load is L0–L3 at the model level, not the production dispatch path |
| Formal specification | **Yes, gates** | Level 0 (Z3 SMT: guard satisfiability, invariant induction, unreachable-state detection) and Level 1 (Stateright: exhaustive BFS over the bounded state space, safety + liveness properties, counterexample traces) |

**What gates vs what reports, stated precisely.** All four cascade levels (L0–L3) must pass before a
spec deploys — enforced at the platform boundary for every user. The precise shape, from the run: `temper
serve` loads the spec, runs the cascade in the background, and gates every dispatch on the result (see
Loop); the project's own verify-temper notes add that a *failing* spec is not rejected at load either
— it registers, fails, and *"blocks all dispatches on that type with 'Fix the spec and re-push' until a
passing one lands."* The gate is real; "never loading them" was this spec's overstatement. A second, stricter enforcement point — a
blocking pre-commit-style hook, `ALL FOUR must pass → Edit allowed / ANY failure → Edit BLOCKED` — exists
too, but `docs/HARNESS.md` scopes it explicitly to *"agents developing Temper itself (the framework)"*;
an agent building an app *on* Temper gets the `temper serve`/`temper verify` gate by default and this
stricter hook only if `temper init` scaffolds it in. Stating "enforced twice" without that scope
distinction overstates what a typical Temper user actually has — corrected here after the spec's own
Limits section flagged the risk in the abstract without carrying it into this section's body, which is
exactly the gap a fidelity pass exists to catch. Shadow testing gates the hot-swap path for non-cascade
tuning changes, and — per the fifth hot-swap step surfaced in Loop — a live rollback gates *after* the
swap too, if production degrades post-swap despite passing both the cascade and shadow test. The human
D-Record gate covers the remaining path (evolution-proposed destructive changes). The only reporting-only
mechanism is trajectory telemetry itself — it feeds `Agent.Hint`/`Agent.SuccessRate` annotations and the
GEPA's proposals, but a proposal is not an applied change; something downstream always gates it. Measured
against exo's profile — instrumentation genuinely good, but *"the agent closes the loop... nothing acts
on a signal automatically"* — Temper's default is inverted: the mechanism, not the agent's judgment, is
what applies or blocks a change, and now — per the correction above — automatic rollback is one more
instance of the same pattern operating *after* a change has already shipped.

## Which axis

**Axis A — prevention-primary, with recovery layered under it at two different levels, not one.** An
earlier draft of this spec claimed Temper offers "no recovery for a bad spec, only for infrastructure
crashes" — that claim did not survive fidelity review. `docs/AGENT_GUIDE.md` §12 documents an
automatic-rollback step in the hot-swap protocol itself (see Loop): if a `TransitionTable` that already
passed the verification cascade *and* shadow testing still degrades production after being swapped in,
the rollback is automatic, not human-gated. That is genuine recovery at the spec/behavior layer, not
only at the infrastructure layer — the finding is more interesting than the clean "opposite of exo"
story this spec started with.

| | Prevents entering a broken state | Restores from a broken state |
|---|---|---|
| exo | no | yes, by construction — the only mechanism it has |
| Temper | yes, primary mechanism — proof + shadow test before a swap ships | yes, but as a **backstop for what proof and shadow-testing miss**, not the primary safety mechanism |

The proof is still the load-bearing primary claim: *"You can prove, before anything runs, that every
rule is satisfiable, every constraint holds across all reachable statuses, and no failure scenario
violates the contract."* Most of what would be a broken state never ships, because the cascade and the
shadow test catch it first. But "most" is doing real work in that sentence — shadow testing runs a
*fixed suite of test cases*, not the full space of production traffic, so a `TransitionTable` can pass
every gate and still misbehave against inputs the suite didn't anticipate. Step 5 of the hot-swap
protocol exists for exactly that residual gap. Separately, and at a different layer again, actor state
after a *process* crash (as opposed to a bad spec) recovers by event-journal replay — see Boundaries.
So Temper actually has recovery at two distinct points: a live rollback for a spec that degrades
production despite passing every pre-ship gate, and event replay for infrastructure crashes unrelated
to spec correctness. Neither substitutes for the cascade; both catch what the cascade structurally
cannot (real production behavior in the first case, process failure in the second).

**A third recovery point landed between the two pins.** Upstream ADR-0173 (accepted 2026-08-27, in the
tree at `ff0774f`): the one shared Genesis app-install path now verifies that the installed root app is
runtime-ready and every required WASM module compiles, and *"if it is not, and a previous good Genesis
install exists, the install restores that previous version and returns an error; if there is no safe
prior, it fails cleanly."* The routing is a pure decision function — `Commit | RollBackToPrevious |
FailNoRollback` — with a DST invariant (P18) behind it. That is the same composition as the hot-swap
rollback, one layer up: at install rather than at swap. So the count is three at the current pin —
install-time rollback, post-swap rollback, and journal replay — each scoped to what the gate before it
cannot see.

**The human gate hardened too.** Upstream ADR-0172 (accepted 2026-08-20) seeds the bootstrap operator
exactly one permit, `manage_policies` on its tenant's `PolicySet`, and bans self-approval: *"the
approve/deny handlers refuse to let the subject of the denial walk through it for that decision."*
Observed (Embodiment row 15): the operator's own denied create became a pending decision, and the
operator's approve and deny calls on it both returned `403` with `The denied principal cannot approve
or deny this decision`. The decision stayed pending. That closes a hole this spec's Boundaries
paragraph ("every unpermitted action becomes a pending decision") had not asked about: whether the
principal that triggered the decision could also settle it.

This still bears on the open question pavlos's own research raised across specs — are prevention and
recovery opposed, or complementary? — but the answer this spec now supports is narrower and more
interesting than "opposed, at different layers": Temper demonstrates prevention and recovery
**composed within a single change path**, with recovery scoped tightly to the residual risk that
prevention's own instruments (a necessarily finite test suite) cannot close. That composition, not a
clean prevention/recovery split, is the more transferable finding — see What to steal.

**Axis B is absent and undiscussed, same as exo.** Nothing in the material read evaluates whether a
capability's data — an order total, a payment status, a claim an agent's application logic asserts about
the external world through an integration — is *true*. Cedar governs who may call an action; the
verification cascade proves the state machine's own rules hold; neither touches whether the content
flowing through it is factually correct. An agent could authorize, verify, and execute a transition
built entirely on a false premise, and nothing in the read material would notice.

## Economics

More present than exo's spec, but not where the format's default question points, and that
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
  treating `entity_id` as an Attribute rather than a Tag by default means an operator *"can promote an
  Attribute to a Tag at runtime if they decide the cost is worth it for a specific investigation."*
  `docs/AGENT_GUIDE.md` §8 states the same design more tersely: *"zero cost — not a metric tag, no
  cardinality explosion."* Cost is a first-class, deferred decision here, just not an LLM-token one.
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
- A live rollback backstop scoped to exactly the residual risk proof and shadow-testing can't close.
  Automatic, not human-gated, and only for the narrow case where a change already passed every pre-ship
  gate — see Which axis.

**Pays**

- Constrained expressiveness, named by the project itself: no floating-point state (prices live in
  payload, not state), no conditional effects without decomposing into guarded actions, no temporal
  guards without scheduled actions, single-node only. *"Some of these are fundamental to finite
  automata. Others are engineering work"* — the spec does not know which is which for any given
  future need.
- An extra layer of indirection between intent and artifact. Specs are generated by a coding agent from
  conversation, not hand-authored — the opposite of exo's position, where the agent edits its own
  harness directly. Faster iteration requires trusting the generation step, which sits outside anything
  the cascade verifies (the cascade checks the spec, not the conversation that produced it).
- Real latency cost from durability. Postgres event append dominates end-to-end latency at ~1.4ms per
  action, roughly 50× the in-memory actor dispatch path (~28μs) — the tradeoff of durability-first
  design made visible in the project's own benchmarks, not hidden. (A separate, much faster figure in
  the same benchmark suite — the `evaluate_ctx()` hot path at ~28ns — is the cost of a single guard
  check in isolation, not the dispatch path this ratio is measured against; the two numbers are easy to
  conflate because they're both "28" and both from the same table.)
- The pitched conversational experience — *"You describe what you want. The system builds it, verifies
  it, and evolves it."* — is
  explicitly *"partially implemented"* and *"dependent on the coding agent of choice."* Today's actual
  path is closer to a coding agent authoring specs on a developer's behalf than to a from-scratch
  natural-language interface.
- All the operational weight of a Postgres-backed multi-crate Rust service (27 first-party crates,
  Docker Compose
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

6. **Scope a recovery mechanism to the specific gap your prevention mechanism can't close, instead of
   treating prevention and recovery as a binary choice.** Temper's automatic rollback doesn't compensate
   for a weak cascade — it exists because a shadow test's suite is necessarily finite while production
   traffic isn't, and that specific, named gap is what triggers it. A recovery mechanism with no stated
   scope tends toward becoming the *real* safety mechanism by default, quietly displacing the prevention
   work it was meant to backstop; naming the gap precisely is what keeps that from happening.

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
  conversation reaching it. Generalizing to "the field ignores economics" from two specs is exactly
  the kind of unsupported leap `FORMAT.md` warns against — see Limits.

## Embodiment

`embodiment: partial`. Temper was built from source and run locally at the pinned commit `ff0774f`
with one reference app, one tenant, and the default embedded libSQL store. The run exercised the auth
edge, runtime spec verification, the state machine's guard and from-state rejections, the journal
across a process restart, the policy plane, and the pending-decision flow. It did not exercise hot swap
of a live table, WASM application logic, the evolution loop, the Postgres or Redis backends, or any
DST suite — see the last paragraph and Limits.

**Setup.** `cargo build -p temper-cli` on the pinned toolchain (`nightly-2026-02-08`); 2m19s on a
laptop. Kernel started as `temper serve --port 3100 --no-observe --storage turso` with
`TEMPER_API_KEY` set and `TURSO_URL` pointing at a scratch file, following the project's own
`.agents/skills/verify-temper/SKILL.md` isolation recipe. No Postgres, Docker, or Redis was running.
Every request below carries `Authorization: Bearer <key>` and `X-Tenant-Id: default` unless the row
says otherwise. The reference app is `reference-apps/ecommerce/specs` (Order, Payment, Shipment).

| # | Request | Observed | What it shows |
|---|---|---|---|
| 1 | `GET /healthz`; `GET /tdata/$metadata`, no key | 200; 200 with CSDL XML | Liveness and schema are the declared public routes |
| 2 | `GET /tdata/Plans` with no key; again with the operator key | 401; 403 | Fail-closed edge (upstream ARN-170): no credential is denied as anonymous, a credential with no permit is denied by Cedar |
| 3 | `POST /api/specs/load-dir` for the reference specs, merge mode | 403 `no matching permit policy`, **no pending decision minted** | Management-plane denials for a sessionless principal stay plain 403s — `crates/temper-server/src/authz/helpers.rs`: *"Non-agent or sessionless denials stay ordinary `403 Forbidden` responses so passive/admin surfaces do not generate noisy approval work"* |
| 4 | `POST /api/tenants/default/policies/rules`, appending a permit for `load_specs_from_directory` on `SpecDirectory` to the verified-operator principal | 200 `rule_added` | The bootstrap operator's one seeded permit is `manage_policies` (ADR-0172); the policy plane is the sanctioned way to widen it |
| 5 | Row 3 again | 200, NDJSON stream: `specs_loaded` → `verification_started` / `verification_result` per entity → `summary all_passed: true`. Order: L0 11 guards satisfiable, 5 invariants inductive; L1 24 states; L2 5 seeds, 43 transitions; L3 100 cases | The cascade runs at load, streams, and is per entity. `$metadata` listed `Orders` only after this |
| 6 | `POST /tdata/Orders` with `{"id":"ord-1","CustomerId":"cust-1"}` | 403, message ends `(decision: PD-…)` | Entity-plane denial **does** mint a pending decision, unlike row 3, for the same sessionless operator |
| 7 | Append permits for the operator on `Order`, `Payment`, `Shipment`, `Customer`; retry row 6 | 409 `ConstraintViolation`: `relation target 'Customer' with id 'cust-1' not found` | Cross-entity relation integrity is checked on create |
| 7b | `POST /tdata/Customers` with `{"id":"cust-1"}` | 500 `No transition table for tenant 'default', entity type 'Customer'` | The reference app's CSDL declares `Customers` and `Products` with no IOA spec (the loader warns `csdl_missing_ioa_spec`), so an Order with a valid `CustomerId` cannot be created through the create path at all at this pin |
| 8 | `POST /tdata/Orders('ord-1')/Temper.AddItem` with `{"ProductId":"sku-1","Quantity":2}` | 200; entity in `Draft`, `items: 1`, two events (`Created`, `AddItem`) | A dispatch on an id that was never created **spawned it at the initial state** (`get_or_spawn_tenant_actor` in `entity_ops.rs`); the spawned entity has no `CustomerId`, so row 7's check never ran |
| 9 | `…/Temper.SubmitOrder` with `{"ShippingAddressId":"addr-1","PaymentMethod":"card"}` | 200; `Submitted`, three events | The transition the spec permits |
| 10 | Row 9 again | 409 `Action 'SubmitOrder' not valid from state 'Submitted'` | From-state rejection by the transition table, not by application code |
| 11 | `…/Orders('ord-2')/Temper.SubmitOrder` on an order with no items | 409 `Action 'SubmitOrder' blocked from state 'Draft': guard min_count on 'items' requires >= 1, found 0` | Guard rejection; the TOML guard `items > 0` compiled to a `min_count` check |
| 12 | `GET /observe/entities/Order/ord-1/history` | 200; `Created`, `AddItem`, `SubmitOrder`, sequence 1–3, with params | The journal is the record |
| 13 | Kill the process; restart on the same store; `GET /tdata/$metadata` | log `Restored 23 specs from Turso`; `Orders` **absent**; `GET …/Orders('ord-1')` → 404 `EntitySetNotFound`; row 12 still returns the three events, with `current_state: null` | Runtime-pushed specs do not survive restart on the default store — see Boundaries. The journal did |
| 14 | Row 3 again (the permit from row 4 persisted); `GET …/Orders('ord-1')` | 200; `Submitted`, `total_event_count: 3`, `items: 1`, shipping fields intact; row 10 repeated → 409 | **Replay proof.** State rebuilt from the journal alone, and the from-state rule holds on the rebuilt actor |
| 15 | `POST …/decisions/PD-…/approve` with scope `this_agent / this_action / this_resource / always`; then `…/deny` | 403 both: `The denied principal cannot approve or deny this decision`; decision still `pending` | ADR-0172's self-approval ban, live |
| 16 | `temper decide --port 3100 --tenant default`, 12 s, one decision pending | `Waiting for pending decisions...` and nothing else | The CLI polls `?status=Pending` while the store holds `pending`. The project tracks this as ARN-442 in `features/cedar-authz.md`. Reproduced here, not discovered |

**What the run did not do.** No WASM module was triggered (the reference Order spec declares none). No
hot swap of a live table — row 14 re-registered a spec into an empty slot, which is registration, not
a swap under live actors. No evolution loop, no GEPA, no trajectory analysis beyond noticing that every
denied request wrote a `trajectory.store.write` log line. Only the `turso` store and the in-process
`legacy` actor runtime; the project's own notes say the declared key index is *not* maintained on
turso, so nothing here speaks to the keyed-absence guarantee. No DST suite was run; every number under
"deterministic simulation testing" remains the project's own. One tenant, one principal; the
non-default-tenant credential path and the trusted-issuer JWT path were not touched.

**Three things the run found that the documents do not say.** (1) A dispatch on an unknown entity id
creates the entity, without the create path's field validation (rows 7–8). (2) Specs pushed at runtime
are lost on restart on the default store while their journals persist (row 13). (3) The bundled
ecommerce reference app cannot create an Order through the create path at all (row 7b). All three are
recorded as observations at `ff0774f`, not as design intent, and none was raised with the maintainers.

## Limits of this spec

- **Documents read in full, code read in part, for the run only.** Every claim in Philosophy, Primitives,
  Loop, and the analytical sections comes from `README.md`, `docs/PAPER.md` (read in full),
  `docs/POSITIONING.md` (read in full), and the sections of `docs/AGENT_GUIDE.md` covering core
  concepts, observability, JIT optimization, and anti-patterns (§1, §8, §12, §16). For the re-pin and
  the run, these implementation files were read in part, only far enough to explain an observation:
  `temper-platform/src/bearer_auth.rs`, `temper-cli/src/serve/bootstrap.rs`,
  `temper-server/src/state/entity_ops.rs` (the verification gate and the spawn-on-dispatch path),
  `temper-server/src/authz/helpers.rs`, `temper-server/src/observe/specs/load_dir.rs`,
  `temper-platform/src/tenant_api.rs`, `temper-server/src/api/policies.rs`,
  `temper-platform/src/operator_manage_policies.rs`, `temper-authz/src/policy_gen.rs`. The
  implementation as a whole was not read. Whether the code matches the documentation was checked only
  at the points the run touched — and at two of them it did not (Embodiment, last paragraph).

- **188 entries under `docs/adrs/` at `ff0774f` — 186 numbered files plus `TEMPLATE.md` and a `gaps/`
  directory; 164 unique numbers; 14 numbers carry more than one file; highest 0173 — were not read
  individually.** Counted with `git ls-tree` on a clone, the same method applied to the old pin (182
  entries, 180 numbered, 159 unique, highest 0165), so the two figures are comparable; the earlier
  "14 numbers reused for 22 duplicate files" phrasing came from a different count and should not be
  read against these. Six files were added between the pins: `0157-journaled-field-updates.md` (a
  second file under an already-used number), `0160`, `0164`, `0166`, `0172`, `0173`. Of these, 0157,
  0172, and 0173 were read in their Context and Decision sections for this re-pin, because each bore
  on a claim in the body; 0160, 0164, and 0166 by title and opening lines only. An earlier draft of
  this spec stated "165 ADRs," mistaking the highest number for a file count — caught by fidelity
  review. Any single unread ADR could sharpen, qualify, or contradict a claim synthesized here from
  `PAPER.md` — the same category of risk exo's spec flagged for its own unread design-note files, at
  much larger scale, and the PATCH/PUT finding below is one instance of exactly that risk landing.

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

- **The hands-on run is partial, and single-configuration.** `embodiment: partial` reflects one
  reference app, one tenant, one principal, the default store, and the in-process actor runtime, at one
  commit, on one laptop. Embodiment lists what was and was not exercised. The project's own disclosed
  benchmarks (Criterion hot-path figures, the 22 named DST tests, the two determinism proofs) were
  not reproduced and remain the project's reported results.

- **Auth model not covered.** Upstream ARN-170 (merged 2026-08-14, before the original pin) replaced
  header-asserted identity with a credential-bound request context, and ARN-255 (after the original
  pin) added trusted-issuer JWT verification. This spec describes neither beyond what the run touched:
  a bootstrap operator credential in the `default` tenant, a tenant header, and fail-closed 401/403.
  How an agent obtains a credential in a non-default tenant, the JWT path, and the internal-invocation
  capability were not read. The WASM guest-isolation fixes between the pins (ARN-208/226/243, ADRs
  0164 and 0166) were not evaluated; the Sandboxing paragraph in Boundaries still rests on the
  documents alone.

- **`lifecycle: version-changing`** on the project's own statement that *"the API surface is not
  frozen"* at 0.1.0, with an explicit "cannot do this yet" list the project expects to shrink. A spec
  first written against `2f43ece` and re-pinned to `ff0774f` on 2026-09-02 should be assumed to keep
  drifting, plausibly faster than exo's given the number of documents (275 `.md` files in the tree at
  `ff0774f`, up from 268; 188 entries under `docs/adrs/`, up from 182) actively tracking design
  decisions in this repository. Between the two pins the five documents this body quotes did not
  change by a byte (`git diff 2f43ece ff0774f -- README.md docs/PAPER.md docs/POSITIONING.md
  docs/AGENT_GUIDE.md docs/HARNESS.md` on a clone returned nothing), so the quotes were carried
  forward rather than re-verified one by one. That byte-identity check is the claim the fidelity review
  must independently repeat (zygos ADR-0003).

- **Compared to exo, once, by me — not adjudicated by a third source.** The prevention-vs-recovery
  contrast and the "same artifact serves two roles" parallel to "the log is the program" are this
  spec's own synthesis, built from having read both specs, not from any source that compares the
  two projects itself. Pavlos's own Q3 (are prevention and recovery opposed or complementary at
  different layers?) is addressed above with a specific answer, revised once already during this
  spec's own fidelity review: not cleanly "at different layers" but *composed within one change
  path*, with recovery scoped to the named residual gap prevention's own instruments can't close. That
  answer rests on two data points (exo, Temper) and should be treated as a strong lead for the eventual
  concept document, not as settled by this spec alone — and the fact that it changed once already,
  mid-spec, is itself a reason for caution rather than confidence.

- **Economics finding rests on absence, checked by keyword search plus targeted reads, not exhaustive
  reading.** "No LLM-token economics discussion" was confirmed by grep across `PAPER.md`,
  `AGENT_GUIDE.md`, and `HARNESS.md` for cost/cache/token/prefix/compaction terms, then read in context
  wherever a hit appeared. A discussion using none of those terms would not have been found this way.

- **This spec went through fidelity review before merge, and it changed a central claim.** A first
  draft misattributed three quotes to the wrong source file (two spliced `PAPER.md`+`POSITIONING.md`
  phrasing under a single citation, one cited `PAPER.md` for a sentence actually in `AGENT_GUIDE.md` §8,
  a section outside that draft's disclosed reading scope), swapped a 28ns figure for an unrelated 28μs
  figure in a latency ratio, miscounted the ADR total, and — the load-bearing one — claimed no recovery
  mechanism exists for a spec that already passed the cascade and shadow test, when `AGENT_GUIDE.md` §12
  documents exactly that mechanism (the automatic-rollback step). All of the above are corrected in this
  version. This is recorded here deliberately: a presence-checking guard (zygos ADR-0001) would have
  passed the first draft outright — every section was filled, every field populated, nothing missing.
  Only re-reading the same primary sources with intent to refute caught the actual defects. That is the
  argument for the fidelity pass being load-bearing, made concrete rather than asserted.

- **Corrected again after the Phase 2 backfill fidelity review (2026-08-28).** A re-import of this
  spec through an independent adversarial review that re-fetched the pinned sources found new defects,
  all fixed here: (1) the drift claim cited *"the number of documents (600+)"* — the pinned tree has
  268 `.md` files (182 under `docs/adrs/`); no source says "600"; (2) the ADR count still conflated
  reuse *slots* with reused *numbers* — it is 182 ADR files, 159 unique numbers, 14 numbers reused for
  22 duplicate files, highest 0165; (3) the "22+ crates" figure is actually 27 first-party crates;
  (4) a Tradeoffs quote truncated the source's full "builds it, verifies it, and evolves it"; (5) a
  Loop passage presented a paraphrase as a verbatim quote. The recurrence of a count error in the very
  section rewritten to fix the prior count error is itself evidence that count-claims need independent
  re-verification each time, not just once.

- **Re-pinned 2026-09-02, `2f43ece` → `ff0774f`, 18 upstream commits, and the pin moved more than the
  prose.** No quote drifted (see the lifecycle bullet). Five claims changed on the strength of what was
  new upstream or what the run showed: (1) the Boundaries journal row now carries the PATCH/PUT caveat
  from upstream ADR-0157 — at the original pin this spec asserted a durability property for all writes
  that the documents only ever stated for transitions, and the table's "yes" was an inference, not a
  source; (2) Which axis counts three recovery points, not two, after ADR-0173; (3) the same section
  records the self-approval ban from ADR-0172; (4) Loop and Verification strategy no longer say the
  serve command rejects unverified specs at startup — the gate is per dispatch, and a failing spec
  loads and then blocks; (5) the Boundaries table gained two rows (pending decisions, registered specs)
  and observed evidence on two others. Embodiment moved from `none` to `partial`. The method lesson is
  the first item: a state-inventory row needs its own source or observation, and this spec's original
  table had one row that had neither. Carried into `docs/research/SKILL.md` §6.

## Sources

Originally fetched as raw markdown pinned to commit `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400`
(2026-08-16), never to `main` — a branch ref changes content silently and still resolves, so a link
check cannot catch drift. Re-pinned to `ff0774f572197a75987f3329b48553ae9f8b3c29` on 2026-09-02 after
`git diff 2f43ece ff0774f -- README.md docs/PAPER.md docs/POSITIONING.md docs/AGENT_GUIDE.md
docs/HARNESS.md` on a clone returned empty; the five links below now point at the new pin and resolve
to the same bytes the original pass read. The rows after them are new to the re-pin.

| Source | Type | Retrieved |
|---|---|---|
| [`README.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/README.md) | primary — project self-description, full read | 2026-08-16 |
| [`docs/PAPER.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/PAPER.md) | primary — full architecture paper, full read (all 12 sections) | 2026-08-16 |
| [`docs/POSITIONING.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/POSITIONING.md) | primary — positioning statement, full read | 2026-08-16 |
| [`docs/AGENT_GUIDE.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/AGENT_GUIDE.md) | primary — §1 Core Concepts, §8 Observability, §12 JIT Optimization, §16 Anti-Patterns read (§8 and §12 added after fidelity review; remainder scanned by heading only) | 2026-08-16 |
| [`docs/HARNESS.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/HARNESS.md) | primary — first ~200 of 610 lines read; this is Temper's own dev-time harness, not the product's agent-facing surface — see Limits | 2026-08-16 |
| Repository tree at `2f43ece` (GitHub API, recursive) | primary — used to enumerate docs and confirm the ADR file count at the original pin; ADR bodies not read | 2026-08-16 |
| Repository tree at `ff0774f` (`git ls-tree` on a clone) | primary — recount of `docs/adrs/` and `.md` totals with a stated method, applied to both pins; commit log `2f43ece..ff0774f` (18 commits) read by subject line | 2026-09-02 |
| [`docs/adrs/0157-journaled-field-updates.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/adrs/0157-journaled-field-updates.md), [`0172-operator-bootstrap-manage-policies.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/adrs/0172-operator-bootstrap-manage-policies.md), [`0173-genesis-install-verified-or-reverted.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/docs/adrs/0173-genesis-install-verified-or-reverted.md) | primary — Context and Decision sections read; each is quoted above | 2026-09-02 |
| `docs/adrs/0160`, `0164`, `0166` (RUSTSEC cleanup; WASM guest read bounds; per-tenant LLM-content redaction) | primary — title and opening lines only; cited as existing, not as read | 2026-09-02 |
| [`.agents/skills/verify-temper/SKILL.md`](https://github.com/nerdsane/temper/blob/ff0774f572197a75987f3329b48553ae9f8b3c29/.agents/skills/verify-temper/SKILL.md) and `features/` — `serve-and-odata.md`, `entity-lifecycle.md`, `cedar-authz.md`, `spec-cascade.md`, `spec-hot-swap.md`, `event-sourcing-readback.md` (full), `dst-proof.md` (first 25 lines) | primary — the project's own end-to-end verification recipes at this pin; used to drive the run and quoted in Verification strategy and Embodiment. The project's own findings against itself (ARN-442, the unwired L2b level) are attributed to it, not claimed as this spec's | 2026-09-02 |
| Implementation files listed in the first Limits bullet | primary — read in part, only to explain an observation from the run | 2026-09-02 |
| Local build and run at `ff0774f` (`cargo build -p temper-cli`; `temper serve --storage turso`, one reference app, one tenant) | primary — this spec's own observations; commands and responses in Embodiment | 2026-09-02 |

**Cross-reference:** `docs/research/harnesses/exo.md` in this repository, read in full before this
spec was written, for every comparison drawn above.
