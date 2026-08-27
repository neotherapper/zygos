---
name: deepseek-harness
title: "DeepSeek Harness (dsh)"
url: https://github.com/deepseek-ai/deepseek-harness
artifact_url: https://github.com/deepseek-ai/deepseek-harness/tree/47f943859bef60e4160492346772ded9b24f765a
commit: 47f943859bef60e4160492346772ded9b24f765a
language: TypeScript
kind: agent-harness
license: MIT
status: developer preview
lifecycle: version-changing
provenance: primary
verified_at: 2026-08-18
axis: [A]
primitives: [event-log, session-header, capability-seam, plugin, profile-bundle, turn-step, goal, scope, tool, command, invariant, token-meter]
embodiment: none
---

# DeepSeek Harness (dsh)

## Philosophy

DeepSeek Harness (dsh) is built on one structural conviction, stated three times across the sources read here (README.md, AGENTS.md, docs/architecture.md): **everything is a plugin**. The README frames the architecture: "It uses an architecture where **everything is a plugin**". docs/architecture.md makes the claim total, including the harness's own spine: "Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself, so every part is replaceable from configuration." It follows that there is nothing privileged to patch: "There is no privileged core to patch: you extend dsh by mounting a plugin beside the others, and registrations are effects that unwind when their plugin unloads."

Two secondary convictions follow from the first. (1) The session log, not the loop, is the source of truth — session.md calls the log "the single source of truth for an agent's whole interaction history" — and its authority is enforced as an invariant: "Model-visible means logged. Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it" (architecture.md). (2) Correctness of structure is pursued before stability of interface. The project declares itself "in _developer preview_" and warns, in all caps: "**THERE WILL BE COMPATIBILITY-BREAKING CHANGES.**" AGENTS.md states the pre-release stance as "foundation over blast radius": "With no external consumers, prefer the correct foundation over compatibility shims: rename or repackage freely and update every reference together." Backends enforce the same refusal at load: an on-disk format this build cannot faithfully read is refused, not migrated.

What it refuses to do: carry compatibility shims that mask a wrong foundation; treat any part of the product — including the agent loop and the model adapter — as unswappable; and let a model-visible input exist without a session-log counterpart. It refuses to trust its own structure to coincidence, wiring structural checks into a runtime invariant registry and a per-file coverage gate.


## Primitives

| Primitive | What it is | Where it lives |
|---|---|---|
| **SessionEvent log** | Append-only log of durable facts (`SessionEvent`); the single source of truth. Message history is *derived* from it, never stored alongside it. | `packages/core/session` |
| **SessionHeader** | Metadata beside the log, deliberately *not* conversation events: format `version`, `id`, `createdAt`, `cwd`, `parentSession` lineage, `seedLength` seed boundary, `origin`, `delegationDepth`, `agentPreset`. | session header |
| **Seam (capability seam)** | A swappable capability with exactly three roles: **Service Definition** (interface), **Service Provider** (implementation), **Consumer** (user, commonly a model-facing tool). One role alone is not a seam. | `docs/capability-seams.md`; e.g. `ctx.fs`, `ctx.shell`, `ctx.subprocess`, `ctx.terminals`, `ctx.lsp`, `ctx.credentials`, `ctx.sandbox` |
| **Plugin** | A Cordis plugin contributing services, typed events, reversible effects to a shared context. Registrations are effects that unwind on unload (disposer returned). | vendored Cordis |
| **Profile / bundle / patch** | Boot-time composition layers. A profile is a named bundle composition in the Harness home; a bundle is a distribution format for config rows + code; patches replace whole config rows by id. `web` and `headless` ship as profile templates. | `packages/boot`, `packages/bundle` |
| **Turn / step** | A **step** is one model request plus the tools it calls. A **turn** is zero or more steps, opened before the first input is claimed and closed once nothing is owed. | `docs/architecture.md` turn flow |
| **Goal** | Durable completion objective attached to the session, managed via `ctx.goals`; every mutation is a durable `goal/change` session event (goal.md) and the session log remains its source of truth. Continues through `agent/*` events. Only goal *activation* is process-local, deliberately not replayed. | `ctx.goals` |
| **Scope** | Per-agent scoped-registration primitive (library, no key): registers a contribution against one agent's context. | `packages/core/scope` |
| **Tool** | Model-facing capability exposed via a Consumer role on a seam; schema joins prompt assembly. `job_*`, `todo_write`, skill catalog/loader are tools. | `ctx.tools`, registry |
| **Command** | Human-input path that dispatches without a model turn (e.g. via `ctx.commands`). | interaction package |
| **Invariant** | A runtime check in the `dsh-invariants` registry asserting an owned relationship over an authoritative event stream. Violation throws. | `dsh-invariants` registry |
| **Model-visible means logged** | Design rule + runtime invariant: anything that reaches a model request must be reconstructable from the log; a new model-visible input requires a new `SessionEventMap` member. | architecture.md |
| **Token-meter projections** | `contextPressure` / `contextBreakdown` — O(1)-checkpoint surface-token accounting that folds compaction replacements (shadow-price protocol). | `packages/llm/token-meter` |


## Loop

Three nested loops run dsh, each feeding the next:

**1. The step loop (one model request + the tools it calls).** The driver claims input from one inbox — next-step input plus one queued message. It assembles prompt sections and tool schemas from what plugins registered, then fires `agent/pre-step`, a waterfall whose listeners may rewrite the claimed messages or reject them outright. A rejected or empty first claim closes a durable turn that spent no step — the attempt is logged. Otherwise it appends the entered messages as `user/message`, **derives model history from the log** (`deriveMessages()`), and runs `agent/request -> llm/stream -> assistant/chunk* -> assistant/message`. Tool calls run the guarded pipeline `tool/call* -> tools/pre-execute -> tools/execute -> tools/post-execute -> tool/result*`. If tools owe another request or new next-step input arrived, it claims again — a new step in the same turn.

**2. The turn loop.** A turn opens with `turn/start` before its first input is claimed and closes with `turn/end` once nothing is owed; `agent/turn-stopping` (serial, no `next()`) is the last chance to stop it. Every step in a turn is durable as session events (`turn/*`, `step/*`, `user/message`, `assistant/*`, `tool/*`); the live `agent/*` events (`pre-step`, `request`, `step`, `status`, `validation`, `continuation`) observe or intercept work in flight and are not persisted.

**3. The goal/round loop.** `ctx.goals` manages a same-session objective; a goal *activation* is a process-local side effect deliberately not replayed from the log — only its declared goal is durable. Work continues through `agent/*` events, which is how a long task is broken into turns.

Ordering rules worth stealing: durable facts are broadcast through `session/event`; agent liveness through `agent/*`; capability policy through seam events (`fs/*`, `tools/*`). Waterfall listeners MUST call `next()` or they short-circuit the chain; `agent/turn-stopping` is serial. Flush (`session/flush`) is the ordering and error-observation checkpoint the loop uses before claiming the next ordinary turn. Persistent background work registers via `ctx.jobs` and is collected by `job_*` tools — the same seam discipline as everything else.


## Boundaries

## Trusted vs swappable

Everything is swappable by construction — the model adapter, tool registry, session log, and agent loop are all plugins. What is *not* swappable is the seam discipline itself: a capability must come as a complete Definition/Provider/Consumer triad, registrations are effects that unwind on unload, and a model-visible input must have a session event. The triad-completeness and effect-unwind rules are conventions; the model-visible rule is enforced by a throwing runtime invariant.

## Sandboxing

Sandbox is itself a seam (`ctx.sandbox`): providers confine spawned processes (argv-wrapped before spawning). Filesystem and subprocess providers share one execution world, so pointing them at a remote sandbox moves Bash, PTY, and LSP with them. Approval/interaction is a capability — the approval seam is `ctx.approval` — not baked into the loop.

## State inventory

| Category of state | Crash / restart | Cold load of a persisted log | Fork / resume | HMR (live plugin unload) |
|---|---|---|---|---|
| **Session event log** (durable facts) | Survives; an interrupted turn is closed with a synthetic `turn/end {reason:{kind:'interrupted'}}` — never truncated | Survives; repaired in memory | Survives as inherited prefix, bounded by `seedLength` in the header | Survives (live prefix adopted without closing its active turn) |
| **SessionHeader** (version, lineage, `seedLength`, `delegationDepth`, `agentPreset`, `origin`) | Survives | Survives; wrong `version` → load refused (`SessionFormatUnsupportedError`) | Written on fork; `parentSession` set | Survives |
| **Derived surface** — titles, projections (`contextPressure`/`contextBreakdown`) with persisted O(1) checkpoints | Re-derived from the log; checkpoints persist as rows in the separate `session_projcache` cache (throttled write-behind, mandatory at `turn/end` and session disposal) | Replayed | Replayed from the seed prefix | Survives (projection state is durable, `stateVersion`-bounded) |
| **Live registrations** (effects on `ctx`) | Gone; rebuilt at boot | n/a | n/a | Unwound by disposer when the contributing plugin unloads |
| **Goal activation** (process-local side effect) | Lost — deliberately not replayed; only the declared goal is durable | Lost | Lost | n/a |
| **Compaction lock / ownership** | Detected as orphan on restart — a `compaction/start` with no matching `compaction/end` — not silently stale | Classified on load: stale if before newer `session/end-seed` (ignored), otherwise `busy` | Not wedged — a newer constructor-written `session/end-seed` proves the older unmatched start stale | n/a — no documented unload behavior |
| **Settings / credentials** | Persisted via `settings` / `credentials` capabilities (file provider, `.env`) | n/a | n/a | Survives |
| **Token-meter surface checkpoint** | Survives as a persisted checkpoint in that projection-cache store; unpriced replacement folds neutrally so replay never dies | Replayed | Replayed | Survives |

## Blast radius of an irreversible action

The irreversible action is a **history replacement** (compaction). It rewrites the model-visible surface in place (`surfaceOp {op:'replace', start, end}`). Downstream cost: the provider prefix cache is invalidated from the first replaced token, so subsequent turns re-pay prompt processing for everything after the head. The repair, not the replacement, is durable; the replaced text is gone except for the summary that replaced it. A lost/corrupt log makes a session permanently unopenable — which is exactly what format-refusal and the interrupted-turn repair exist to prevent. Rejection is loud: an event type outside the build's generated vocabulary refuses the whole log unless the envelope carries `ignorable: true`.


## Verification strategy

Placed on the four-rung ladder, with the gates named separately from what merely reports:

| Rung | Mechanism | What it gates vs what it only reports |
|---|---|---|
| **Deterministic simulation / testing** | Vitest unit suites stay with the code they exercise; every registry gets an HMR-safety test. CI **coverage gate** is per-file 100% on `packages/*/*/src` — `test:coverage`, not `test`, is the gate. | **Gates:** every merge. An uncovered line is often dead code the gate is correctly flagging for deletion, not a missing test. |
| **Deterministic simulation (replay)** | Keyless **snapshot** tests boot the real ACP automation-server example, replay a recorded session, and diff normalized JSON-RPC plus the re-persisted log; headless scenarios replay through a JSONL driver. **Required for every non-trivial model-, protocol-, or human-visible change in the same PR.** | **Gates:** model/product-visible behavior changes merge only with a keyless assembled transcript. |
| **Deterministic simulation (web)** | `test:web` — Chromium compares replayed browser output; CI forces read-only `DSH_SNAPSHOT=replay`. | **Gates:** PR merge (required Linux gate). |
| **Observability-driven (real-API e2e)** | With-key tests against live DeepSeek/EXA/Perplexity APIs; each suite self-skips without its key so keyless CI stays green. | **Reports,** does not gate keyless CI. testing.md's with-key policy is titled "inference is cheap here" and its body reads "We are DeepSeek — do not ration real-API tests." |
| **Formal/invariant** | `dsh-invariants` runtime registry asserts owned relationships over authoritative event streams ("Runtime invariants assert owned relationships. Check authoritative event streams or mutable data, not service or method presence, plugin metadata or effects, or fixed pure examples"). The flagship invariant: **model-visible ⟺ logged**. | **Gates execution at runtime:** a violation throws. Plus structural gates: format-refusal on load (a log this build cannot read is refused, with upgrade direction), event-type refusal for unknown required events, loud rejection of a mismatched adjacent shadow-price claim. |

**What it does not gate:** the model's factual claims about the world. All five rungs verify that the *harness* — its log, structure, seams, replay, transport — behaves as designed. Nothing verifies that what the model says is true; the harness trusts the model on Axis B, and the design does not claim otherwise. testing.md's "Verify the world, not the self-report" rule is about e2e *tests* re-running a command externally rather than probing the agent's own output — it verifies harness behavior, not world-truth.


## Which axis

**Axis A (structural soundness) — primary, and the design is deeply aware of it.** The harness can enter broken states, and it both *prevents* and *recovers*, with the two named distinctly:

- **Prevention:** a build refuses a log it cannot faithfully read (format refusal with upgrade direction); refuses an unknown required event unless `ignorable: true`; throws on a live, contradictory adjacent shadow-price claim rather than letting the token total drift; the runtime invariant registry throws when a relationship over an authoritative stream breaks; `assertNever` on closed unions.
- **Recovery:** a crash mid-turn leaves an open `turn/start` with no `turn/end` — the harness does *not* truncate, it closes the orphan with a synthetic `turn/end {reason:{kind:'interrupted'}}`, keeping the interrupted execution balanced. Compaction orphan locks are detected on restart rather than treated as silently stale. An unpriced historical replacement folds neutrally so a pre-protocol session still replays.

**Axis B (factual truth) — absent, and unclaimed.** Nothing in the harness verifies that a model's output matches the world. The e2e discipline "Verify the world, not the self-report" governs the project's *own tests*, not the product's runtime behavior. The design appears aware of the gap: its verification vocabulary is about replay, transport, structure, and invariants — there is no claim to world-truth checking. *Trusts the model* is the honest finding on Axis B.


## Economics

Cost is a first-class design property here, concentrated in the compaction seam and the token-meter service — and this is the section that either confirms or kills pavlos's R8 (medium-confidence: "compaction must preserve provider prefix reuse"). **Reading the primary sources: R8 is confirmed as best-effort, not invariant.**

**Compaction as a prefix-cache optimization.** The compaction seam's whole point is that replacing the model-visible surface with a summary *preserves* provider KV-cache reuse rather than destroying it. The bug-fix note `2026-07-21-compaction-summary-prefix-cache-reuse.md` documents the failure it fixed: the old summarizer built a bespoke system prompt plus a flattened transcript, so its first token differed from any real request and the provider's entire cached prefix was invalidated — the model re-processed the full prompt. The fix: the summarization call **replays the last routed request's prefix verbatim** and appends the directive as a trailing user message, so the auxiliary call is a genuine *prefix-extension* of the warm request and the provider KV cache is reused. Auto-compaction is always head-anchored (the shadowed region is the head of the routed request), so the replayed prefix matches exactly — a guaranteed hit. The best-effort caveat is explicit in the material: a manual mid-range `compactRegion` replays the true prefix (correct, but forgoes reuse), and a summarization route that differs from the conversation's own provider/model also forgoes reuse — a deliberate deployment trade-off, not an invariant.

**The main conversation's cache is a different ledger.** While the summarization call rides the warm request's prefix, the main conversation itself is invalidated from the first shadowed token by the replacement (the KV-cache effect is documented in the compaction provider's README). Only the unchanged head — system prompt and tools — survives. So compaction preserves reuse *for the summarizer*, at the cost of invalidating the conversation it compacts.

**Token-meter: O(1) accounting that must survive replay.** `contextPressure`/`contextBreakdown` keep O(1) persisted checkpoints plus at most one pending shadow-price claim. A replacement immediately preceded by a `compaction/summary` or `compaction/prune` metering event prices the exact replaced range via `shadowedTokenCount`; an *unpriced* replacement (pre-protocol history) folds neutrally (`deltaTokens: 0`, overcount retained until the next usage sample re-anchors) so replay never dies; a claim naming a *different* range throws — a live producer bug, must fail loud. This is why a session survives years of replay: accounting is a derived, replayable projection, not a parallel truth.

**What gets re-sent vs reused each turn.** The model-visible surface is re-derived from the log each turn (`deriveMessages()`) and re-serialized; the reuse mechanism is the provider's prefix cache, which dsh manipulates by ordering and anchoring replacements. There is no disclosed pricing or budget layer — the repo's own tree has no cost/price/budget surface beyond the token meter — and the project, being DeepSeek, treats model inference as cheap enough that its own e2e policy is "do not ration real-API tests."


## Tradeoffs

**Buys:**
- *Replaceable everything.* The agent loop, model adapter, tool registry, and session log are all plugins — no privileged core to patch. Adding a capability means designing a complete seam triad; one provider swap moves Bash, PTY, LSP, and FS together.
- *Replayable truth.* An append-only event log as the single source of truth; message history, titles, telemetry, token accounting, fork/resume all derive from it.
- *Crash honesty.* An interrupted turn is repaired with a synthetic `interrupted` end, never truncated; format refusal is loud with an upgrade direction.
- *Verification as gates.* Per-file 100% coverage gate on every merge; keyless snapshot transcripts required for every non-trivial model-/product-visible change; web snapshot gate on PRs; runtime invariant registry throws on structural violation.

**Pays:**
- *Compatibility instability.* Developer preview, explicitly "THERE WILL BE COMPATIBILITY-BREAKING CHANGES", `SESSION_FORMAT_VERSION` stays at 0 with "no migration — see the constant", no compatibility promise, backends refuse old formats. Anyone who adopts now re-writes their session store or is stranded on a pinned build.
- *Seam complexity.* Every capability must be a three-role seam; one role alone is explicitly not a seam. That is real design overhead and a real review burden (the repo's own AGENTS.md makes the triad a rule).
- *Single-provider default.* The model adapter seam is generic but the shipped provider and the e2e policy are DeepSeek-shaped (testing.md's with-key policy: "We are DeepSeek — do not ration real-API tests."); a deployment on a metered third-party provider inherits an economics posture designed for near-free inference.
- *Compaction best-effort.* Prefix reuse is preserved for the summarizer but at the cost of invalidating the compacted conversation's own cache; manual mid-range compaction and route-mismatched summarization forgo reuse. The optimization is real but conditional.
- *Derived-surface drift risk.* O(1) token checkpoints intentionally overcount after an unpriced replace until the next usage sample re-anchors — a deliberate, documented approximation in the safe direction.


## What to steal

1. **The append-only event log as the single source of truth, with all model-visible history *derived* from it.** No parallel "message history" store that can drift. Anything the model sees must be reconstructable from the log — enforced as a runtime invariant ("Model-visible means logged"). This is the most transferable idea in the spec: a new model-visible input requires a new log event, which makes the log a *change-enforced* truth rather than a best-effort mirror.
2. **Capability seams as complete triads.** Define a swappable capability as Service Definition + Service Provider + Consumer together; one role is not a seam. Adding a capability means designing all three up front, which forces the interface boundary into existence before implementation.
3. **Registrations are effects with disposers.** Every contribution goes through `ctx.effect()`/`ctx.on()`; `register()` returns a disposer, and unloading a plugin unwinds its registrations. Unload safety is tested (every registry gets an HMR-safety test).
4. **Crash repair that preserves work.** An interrupted turn is closed with a synthetic `turn/end {reason:{kind:'interrupted'}}` rather than truncated — a single turn can be huge in a long-horizon task, and truncating throws away durable work. The repair, not the truncation, is the default.
5. **Format refusal with an upgrade direction.** A log a build cannot faithfully read is refused with a message that distinguishes a newer log ("written by a newer harness — upgrade the harness to open it") from an older one, where the build ships no upgrade path; unknown events refuse the log unless the envelope carries `ignorable: true`. Silent skipping of an unrecognized required event could change how the rest of the log must be read.
6. **The compaction prefix-replay trick.** To summarize a conversation *without* paying a second full prompt-processing cost, replay the last routed request's prefix verbatim and append the directive as a trailing user message — the auxiliary call becomes a genuine prefix-extension of the warm request, so the provider KV cache is reused. Anchor compaction at the head so the replayed prefix matches exactly.
7. **Keyless snapshot replay as a merge gate.** Non-trivial model-/product-visible changes must land with a keyless assembled transcript (boot the real example, replay a recorded session, diff normalized output) — so green unit tests with a broken product can't merge. Same idea, one rung stronger: per-file 100% coverage as the CI gate.
8. **Runtime invariants over authoritative streams.** "Runtime invariants assert owned relationships. Check authoritative event streams or mutable data, not service or method presence, plugin metadata or effects, or fixed pure examples." Wire mechanically checkable invariants into an executed gate and prove each changed acceptance path rejects an invalid case.


## What not to

- **The "no compatibility promise" stance.** "prefer the correct foundation over compatibility shims" is internally coherent only because the project has zero external consumers and says so outright ("Remove this section at the first tagged release"). `SESSION_FORMAT_VERSION` sits at 0 with "no migration", and backends refuse older formats. Porting that stance to a project that already ships to users strands them on pinned builds and burns trust; the refusal discipline is worth keeping, the *no-migration* version is not.
- **The DeepSeek economics posture.** testing.md's with-key policy — "We are DeepSeek — do not ration real-API tests." — is calibrated to near-free inference on an owned provider. The with-key e2e *self-skip* is explicitly not a cost signal: testing.md says "Self-skip keeps secretless CI and keyless contributors unblocked; it is not a cost signal." A harness that pays per token for a third-party model should not inherit the do-not-ration posture: it makes the with-key lane unbounded-cost by design.
- **Single-vendor coupling as a default.** The adapter seam is generic, but the shipped provider, the e2e gate, and the tuning are DeepSeek-shaped. Adopting the design without owning the provider means importing someone else's economics and latency profile as if they were neutral.
- **Best-effort cache reuse treated as an invariant.** The compaction prefix-reuse property holds only for head-anchored auto-compaction with a matching summarization route. A design that needs cost *bounds* cannot rest on a best-effort cache optimization; it needs the token-meter to be load-bearing (it is here) and the compaction shape to be policy, not accident.
- **O(1) approximation in the safe direction as a universal rule.** Unpriced replacements deliberately overcount occupancy until the next usage sample re-anchors. In this codebase the error direction is safe (earlier compaction). For a system where over-provisioning is the dangerous direction, the same approximation flips from safe to harmful.


## Embodiment

No documented trace of a canonical task actually run on the installed harness exists in the repository. AGENTS.md’s repository-layout block names a `self-modification/` package ("the agent inspects/mounts its own plugins"), but no such directory exists in the tree at the pinned commit — the list is stale (it also lists `support/` where the tree has `packages/test-support`). The repo does contain a `demo:cordis` that "the agent modifies its own runtime", and docs/architecture.md recommends using an agent to explore the codebase — but these are capabilities and invitations, not a recorded embodiment trace. `BENCHMARK.md` is a 3-line how-to (run the `jsonrpc-agent` minimal variant via the Python SDK), not a disclosed benchmark result. Per FORMAT.md §4.3, embodiment stays `none` until a canonical task with a trace satisfies the promotion criterion; no such trace is fabricated here.


## Limits of this spec

What this spec does not claim to have checked:

- **No hands-on run.** Everything here was read from raw sources pinned at commit `47f943859bef60e4160492346772ded9b24f765a`. No `dsh` binary was run, no LLM key was used, no session was executed or compacted. R8's confirmation rests on reading the design notes and compaction subsystem docs, not on observing provider cache behavior.
- **Read vs scanned.** Fully read: README.md, AGENTS.md, docs/architecture.md, docs/capability-seams.md, docs/agent-lifecycle.md, docs/subsystems/session.md, docs/subsystems/goal.md, docs/subsystems/invariants.md, docs/subsystems/persistence.md, docs/subsystems/compaction.md, docs/subsystems/token-meter.md, docs/subsystems/session-projection.md, docs/glossary.md, docs/testing.md, BENCHMARK.md, packages/interaction/README.md, packages/compaction/compaction-basic/README.md, the 2026-06-18 compaction-capability-seam feature note, the 2026-07-21 compaction-summary-prefix-cache-reuse bug-fix note, and the 2026-08-06 token-surface unpriced-replace bug-fix note. The remaining ~8.6k-tree was scanned by name/path only: the subsystem docs for tools, skills, workflow, subagent, approval, attachment, client-modules, code-runtime, commands, core, credentials, extensions, feedback, filesystem, jobs, llm-streaming, lsp, permission-presets, plan, sandbox, schedule, scope, session-query, session-reference, session-telemetry, session-title, settings, shell, spill, storage, subprocess, system-prompt, terminal, typert, user-questions, web, web-server, workspace; the top-level docs/defensive-patterns.md, docs/development.md, docs/cordis-primer.md, docs/cookbook/; the top-level `*-catalog.md` files (tool-catalog, persistence-catalog, config-catalog); and every `zh` translation were *not* read. Claims about them are limited to what a filename or the read docs assert.
- **Bilingual asymmetry.** All quotes are from the English sides; the Chinese mirrors were not compared. A contradiction in a `zh` mirror would not have been caught.
- **The cache-reuse claim is about design intent, not measurement.** The KV-cache effect is asserted by the project's own notes and READMEs; this spec did not instrument a provider to confirm the reuse actually happens in production.
- **Developer-preview drift.** The project is explicitly compatibility-breaking and iterating; the pinned SHA is already a moving target, and `SESSION_FORMAT_VERSION` = 0 means the sources themselves may refuse to read their own future. Treat any specific claim here as verified only at the pinned commit.


## Sources

| Source | Pinned at | Used for |
|---|---|---|
| `README.md` | 47f9438 | Philosophy (everything-is-a-plugin, developer preview, compatibility warning), license (MIT), run model |
| `AGENTS.md` | 47f9438 | Pre-release stance (foundation over blast radius), conventions (registrations are effects, runtime invariants, model-visible ⟺ logged), testing commands, repo layout block (tree-verified in Embodiment) |
| `docs/architecture.md` | 47f9438 | Philosophy quotes (no privileged core), turn/step flow, session log as source of truth, capability seams, where-new-behavior-goes table |
| `docs/capability-seams.md` | 47f9438 | Seam triad completeness (Definition/Provider/Consumer) and seam registry (`ctx.lsp`, `ctx.credentials`, etc.) |
| `docs/agent-lifecycle.md` | 47f9438 | Turn/step lifecycle, session/event durable vs agent/* live, sourceEventSeqs listing |
| `docs/subsystems/session.md` | 47f9438 | SessionEvent vocabulary, "the single source of truth" phrasing, derived message history, goal/scope, turn-end reason map |
| `docs/subsystems/goal.md` | 47f9438 | Goal primitive: durable `goal/change` session events, revisioned phase, process-local activation |
| `docs/subsystems/persistence.md` | 47f9438 | Flush checkpoint, crash recovery (synthetic interrupted end), SessionHeader, format refusal, seed/fork/resume, SessionLocation, raw artifacts |
| `docs/subsystems/invariants.md` | 47f9438 | dsh-invariants registry, package-owned checks, INVARIANT error discipline |
| `docs/subsystems/compaction.md` | 47f9438 | Compaction seam, surfaceOp replace, metering events, lock ordering (release last) |
| `docs/subsystems/token-meter.md` | 47f9438 | Token-meter service and usage anchoring |
| `docs/glossary.md` | 47f9438 | Primitives vocabulary (seam, scope, goal, turn/step/round, Ralph, command) |
| `docs/testing.md` | 47f9438 | Testing tiers, coverage gate, snapshot policy, with-key e2e policy, verify-the-world rule |
| `BENCHMARK.md` | 47f9438 | Embodiment (how-to only, no disclosed results) |
| `.agents/notes/implemented/feature/2026-06-18-compaction-capability-seam.md` | 47f9438 | Compaction seam origin, head-anchored auto-compaction, manual compactRegion |
| `.agents/notes/implemented/bug-fix/2026-07-21-compaction-summary-prefix-cache-reuse.md` | 47f9438 | R8 core: prefix-replay summarization fix, KV-cache effect, route-mismatch trade-off |
| `.agents/notes/implemented/bug-fix/2026-08-06-token-surface-unpriced-replace-compatibility.md` | 47f9438 | contextPressure/contextBreakdown O(1) checkpoints, shadow-price protocol, unpriced-replace neutral fold, mismatched-claim throw, projection O(1) rationale |
| `docs/subsystems/session-projection.md` | 47f9438 | Projection-cache mechanism: `session_projcache` domain, throttled write-behind checkpoints, mandatory at `turn/end` and session disposal, cold-read ladder |
| `packages/interaction/README.md` | 47f9438 | Interaction-group ctx keys (`ctx.approval`, `ctx.commands`, `ctx.permissionPresets`, `ctx.userQuestions`) |
| `packages/compaction/compaction-basic/README.md` | 47f9438 | Compaction provider KV-cache effect: replacement invalidates reuse from the first replaced history token |

All sources fetched raw at the pinned commit; links above resolve. The remaining tree (~8.6k entries) was scanned by name only — see Limits.
