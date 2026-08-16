---
name: exo
title: "exo"
url: https://github.com/exoharness/exo
artifact_url: https://github.com/exoharness/exo/tree/5bc77ce7c7a2921794083d58c926cf721c14bf8a
commit: 5bc77ce7c7a2921794083d58c926cf721c14bf8a
language: Rust, TypeScript
kind: agent-harness
license: MIT
status: early development      # project's own words: "still in the early stages of development"
lifecycle: version-changing
provenance: primary
verified_at: 2026-08-16
axis: [A]                      # A only, and partially — recoverability, not soundness. See "Which axis"
primitives: [event-log, artifact, sandbox, snapshot-rewind, tool-registry, adapter, skill, binding-secret, guardian, scheduler, memory-store]
embodiment: none               # no hands-on run — see "Embodiment" and "Limits of this spec"
---

# exo

## Philosophy

exo is an agent harness built around the premise that the harness itself should be modifiable by the
agent running inside it. Its README states the position directly: *"Exo is a systems approach to
recursive self improvement. In short, it's a complete AI agent harness (supporting tools, tasks,
integrations, etc. similar to OpenClaw, Pi or Hermes), with the crucial difference that it has full
visibility into both its code and runtime logs."* The design argument is a Bitter Lesson argument,
stated as such in `docs/RSI.md`: *"the hand-engineered harness is the next thing to fall, as models
get smarter, they should have largely unfettered ability to modify their own harnesses rather than
living inside one we froze for them."*

The project draws a distinction it considers load-bearing. Most "self-improving" agents are
*autocatalytic* — they use AI to speed up part of building AI. exo claims *recursion* in the compiler
sense: a complete version of the thing producing another complete version of the thing. `docs/RSI.md`
argues the distinction matters because *"recursion, unlike autocatalysis, requires the system to carry
its own state forward and to do so safely."*

**The problem it names.** An agent whose capabilities are fixed at design time is bounded by whatever
its author anticipated. The usual escape hatches — writable memory, installable skills — let the agent
extend itself at the edges while the loop, the prompt assembly, the tool dispatch and the policy layer
stay frozen. exo's stated failure case is narrower and more interesting than "the agent can't do
enough": it is the failure that appears *once* you let an agent modify itself — an agent that breaks
itself, rolls back, and, having lost the record of the attempt along with the state, tries the
identical broken change again. `docs/RSI.md` names this as the reason the append-only log exists:
*"An agent that breaks itself, rewinds, and tries again can see what it already tried, instead of
repeating the same mistake in a loop."* Rollback without a memory of the rollback is livelock — the
undo mechanism and the record of what was undone have to live at different levels, or undo eats its
own evidence.

## Primitives

| Primitive | What it is | Why it matters |
|---|---|---|
| **Event log** | Append-only record in `.exo/exoharness`: sessions, turns, messages, tool requests and results, errors, artifact writes, sandbox lifecycle. Host components write into the same log as `Custom` events (`host_reboot`, `adapter_runner_started`, `adapter_runner_draining`, `rebuild_and_restart_exo`) | The anti-livelock mechanism. Survives rewind, so a rolled-back agent still knows what it tried. `spec.md`: *"the entire state of the agent is defined as the version of the event log"* |
| **Artifact** | Immutable, versioned opaque bytes, created through the event log; fetch latest or a specific version | Durable agent-owned storage that is not the sandbox filesystem. Skills and the memory store are both artifact-backed, so both survive rewind |
| **Sandbox** | Ubuntu container, agent-scoped by default (shared across conversations), conversation-scoped on opt-in. Repo mounted as part of the sandbox spec | The single designated resettable layer. Making exactly one layer resettable is what makes "what survives?" answerable at all |
| **Snapshot / rewind** | `snapshot_sandbox`, `rewind_sandbox`, `list_sandbox_snapshots`. Snapshot ids are written into the event log | Filesystem state only. Does not roll back events, artifacts, adapter or scheduler records, or secrets |
| **Tool registry** | TypeScript definition is authoritative; the handler runs in TypeScript or delegates to the Rust runtime via `executeTool(...)`. Definitions re-registered every model round | A Rust match arm without a TS definition is unreachable. Registration per round means a tool installed mid-turn is callable in the next round |
| **Adapter** | Host process owning a protocol socket, reconnect behaviour, inbound history, wakeups, outbound sends. Lifecycle *is* the record: create-enabled = start, disable = stop | Inbound messages wake the conversation; model text is never auto-posted outward. `send_adapter_message` is always an explicit decision |
| **Skill** | Standard agent-skills format (`SKILL.md` + frontmatter), artifact-backed. Only names and descriptions injected each turn; bodies load on demand | A third extension surface between prompt text and code-backed tools. Every install is a versioned, auditable artifact write |
| **Binding / secret** | Bindings are non-secret config referring to secrets; secrets hold credential material only. Conversation scope overrides agent scope | Secrets can be mounted into a sandbox so a program uses them *without the model being able to view them*. Capability without disclosure |
| **Guardian** | Host-side supervisor outside the sandbox; builds, restarts, reports status | The self-update path is one fixed operation (`rebuild_and_restart_exo`), deferred so the current turn can finish before the restart lands |
| **Memory store** | `remember(text)` / `forget(id)`, one JSON artifact, whole store injected into every prompt | Explicitly *not* embedding retrieval: *"For a small set of short facts, always injecting the whole store is simpler and easier to audit"* |

## Loop

The central move is a split, defined in `exoharness/docs/spec.md`, between what runs the turn and what
merely stores it:

- The **exoharness** is a trusted, stateful, deliberately minimal substrate. It owns identity (agents,
  conversations, sessions, turns), the append-only event log, artifacts, bindings and secrets, and
  sandbox lifecycle. It brokers privileged resources and *"manages the non-semantic substrate."*
- The **executor** owns semantics: prompt assembly, model calls, tool dispatch, memory and compaction
  policy, approvals. It is described as *"ephemeral and swappable."*
- *"A harness is the combination of an exoharness and an executor."*

The substrate deliberately stops short of calling the model, and the reason given is a containment
argument rather than a layering preference: *"If the exoharness could call the LLM for you, then
necessarily, all of this logic must live within it."* Prompt stitching, model selection and approvals
are semantic choices; admitting any of them into the trusted layer drags the rest in behind them, and
the trusted layer stops being minimal. The concept documentation states what the split buys directly:
*"If the thing that stores your history is the same thing that decides your prompts, you can't safely
let an agent rewrite its prompts — a bad change can corrupt or lose the history too."*

Per-round mechanics that follow from the split: the tool registry is re-registered every model round
(a tool installed mid-turn becomes callable next round, not this one); adapters wake the conversation
on inbound messages but never auto-post model text outward — `send_adapter_message` is always an
explicit tool call, not a loop default; the scheduler drives recurring sandbox work with an explicit
missed-fire policy per task (drop missed slots, fire one catch-up, or fire all).

## Boundaries

Around the exoharness/executor split, the canonical deployment adds a **sandbox** — a vanilla Ubuntu
container, snapshot- and rewind-capable, with exo's own source tree mounted at `/workspace/exo` so the
agent can read and edit the code it is running on — and a **guardian**, a host-side supervisor outside
the sandbox that builds and restarts services. Restarts drain rather than kill: the guardian writes a
marker file, the runner claims it, finishes in-flight work, and exits; a runner that never claims it is
killed after a short wait.

**The state inventory.** The most transferable artifact in the repository is a table in
`docs/SELF-CONTROL.md` §2 answering, for each category of state, *which kinds of reset it survives*:
code and prompts (git), conversation history and event log (`.exo/exoharness`), agent artifacts,
adapter and scheduler records, secrets (Keychain or secret backend), local profile memory, sandbox
filesystem, worker connections.

Exactly one row does not survive sandbox rewind — the sandbox filesystem — and the table annotates it
*"no (that is the point)."* One row does not survive service restart: worker connections, which
reconnect after drain. From that inventory the project derives operating rules rather than asserting
them separately: preserve `.exo` unless deletion is explicitly requested; never store durable memory
only in the sandbox filesystem, because it is the one resettable layer; secrets are the one category
that cannot be casually copied or recreated.

**Blast radius.** Rewind restores a filesystem; it does not retract a message an adapter already
delivered to Slack or WhatsApp. The explicit-send rule for `send_adapter_message` (above) is the
mitigation for that gap, and it is a prompt-level rule, not a structural one.

### The fixed point is a configuration default, not a structural invariant

This is the finding that most affects how the design should be read, and it requires holding two
primary sources against each other.

The concept documentation presents the trust boundary in structural language. `time-travel.md`: an
agent experimenting on itself *"needs an undo button that it cannot break. Because the event log lives
in the trusted exoharness, below everything the agent can touch, a failed experiment is always
recoverable."* `exoharness-and-executor.md` says the substrate *"keeps canonical history out of
reach."* The README says the log is *"the only thing it can't muck with."*

`docs/RSI.md` says the same thing in the body — *"It is the only part of Exo which cannot be modified
by the agent"* — and then footnotes it:

> *"Whether or not the agent can modify the exo-harness is actually a policy consideration. The
> system technically allows it, but to provide safer standard usage, it's disallowed on the default
> configuration."*

So the boundary that makes recursive self-modification safe is enforced by a default setting, not by
architecture. Under the shipped default the guarantee holds; the sentence "below everything the agent
can touch" describes a policy, and three of the four documentation surfaces read as though it described
a structure. exo is aware of this — the footnote is the project telling on itself, and that is a mark
in its favour — but a reader who takes the concept pages at face value will over-estimate the strength
of the guarantee, and anyone porting the design needs to know which of the two readings they are
porting.

## Verification strategy

| Method | Present? | Notes |
|---|---|---|
| Observability-driven feedback | **Partial** | The instrumentation is genuinely good — health fields plus `last_error` per adapter, `list_adapter_events` with type and time filters, `list_conversation_events` with kind filters and cursors, scheduler run results with exit codes, a documented escalation order (health fields → event history → guardian logs → restart). But *the agent* closes the loop by reading these, not the harness. Nothing acts on a signal automatically. Autonomous self-maintenance is listed in the README as an area of active work, i.e. not built |
| Shadow evaluation | **No** | Named as a gap by the project: *"a canary path — run the changed build against a cloned sandbox or forked conversation and compare behavior before adopting it on the live instance, instead of validating on the only copy of itself"* |
| Deterministic simulation testing | **No** | Not present. The repo runs CI and integration test suites, which is ordinary software testing of exo, not verification of agent-authored changes |
| Formal specification | **No** | Nothing of the kind |

`docs/SELF-CONTROL.md` §8 is unusually candid: self-verification and rollback exist *"as practice and
primitives rather than as a single tool."* The loop is snapshot → edit → run `cargo`/`pnpm` checks →
`rebuild_and_restart_exo` → observe the reboot wakeup and event log → commit or revert. Everything in
that chain is a convention the agent is prompted to follow, not a gate the harness enforces — none of
it stops a bad change from landing; it only makes a bad change legible after the fact.

**The verification of a self-change is that it built and the process came back up.** Behavioural
regression is caught, if at all, by a human noticing.

## Which axis

**Axis A, partially. Axis B not at all.**

The useful precision is that exo's Axis A coverage is **recoverability, not soundness**. It does not
prevent the system from entering a broken state — the whole design is organised around the assumption
that it *will*. What it provides is a guaranteed path back out: a resettable layer, a durable log below
it that records the failure, and git as a second immutable log for code. Those are different
properties, and conflating them is easy because both get called "safety":

| | Prevents entering a broken state | Restores from a broken state |
|---|---|---|
| exo | no | yes, by construction |

The design is explicit about choosing this. `docs/RSI.md` describes the goal as *"maximum flexibility
to evolve itself, while providing minimal scaffolding to do it safely"* and elsewhere concedes the
recursion is done *"incrementally and (mostly) safely"* — the parenthesis is the project's own.

**Axis B is absent and undiscussed.** Nothing in exo evaluates whether a claim the agent makes about
the world is true. This is not a criticism — it is out of scope for a runtime layer — but it should be
recorded rather than assumed: the material read contains no mechanism for source attribution,
corroboration, entailment or contradiction detection, and the question is not raised. An exo agent that
concludes something false about its own state will act on it, and the event log will faithfully record
it doing so.

## Economics

Not addressed as a design concern in the material read. The one primitive that is a cost decision by
implication is the memory store: the whole JSON store is injected into every prompt rather than
retrieved by embedding search, on the stated argument that *"for a small set of short facts, always
injecting the whole store is simpler and easier to audit"* — a legibility-over-cost tradeoff, explicitly
scoped to a small store. Nothing in the read material discusses cache reuse, compaction shape, or what
fraction of a turn's tokens are repeated prefix versus new content. This absence is itself a finding:
a harness whose entire value proposition is runtime self-modification has, on the material read, no
stated position on what that modification costs per turn.

## Tradeoffs

**Buys**

- Maximum evolvable surface. Prompts, tools, adapters, scheduler and harness code are all reachable,
  and the substrate is minimised specifically to enlarge what can live above it.
- Auditability as a design principle rather than a feature. The stated rule is that durable mutations
  go through named tools with schemas, *"not hidden conventions or ad-hoc file edits to host state,"*
  with the reason given: *"a mutation path that bypasses the tools also bypasses the record."*
- Reversible by default — disable and checkpoint are preferred to delete and rewrite, on the argument
  that *"an audit record of an unrecoverable action is not a substitute for being able to undo it."*
- Executor swappability. Because durable state sits below the loop, the loop can in principle be
  replaced without rebuilding the agent.

**Pays**

- No pre-adoption verification. A self-change is validated on the only running copy of the agent.
- The safety envelope is the model's judgement plus reversibility. Between "the model decides
  correctly" and "we can undo it," there is no third mechanism.
- Reversibility is scoped to what the system controls — see Boundaries' blast-radius note.
- The trusted core's immutability is a default, not a structure (see Boundaries above).
- Operational weight. Docker, mise-pinned Node/pnpm/Rust toolchains, host supervisors, adapter worker
  processes — a substantial amount of machinery to keep alive for one agent.

## What to steal

Five things, stated so they survive without exo.

1. **Write the state inventory before designing the reset.** For every category of state: where it
   lives, and which resets it survives. The table is a few rows and it makes an otherwise implicit
   question answerable. The operating rules fall out of it rather than needing separate invention.

2. **Have exactly one resettable layer, and say which.** exo's power comes from the sandbox filesystem
   being the *only* thing rewind touches. Multiple partially-resettable layers make "what survives?"
   unanswerable, and unanswerable-at-design-time becomes wrong-at-3am.

3. **Rollback needs a log that rollback cannot reach.** An undo that erases the evidence of what was
   undone produces an agent that repeats the failure. The record of the attempt and the state being
   reverted must live at different levels. This generalises well past self-modifying agents — it
   applies to any retry loop over a mutable resource.

4. **Route durable mutations through named, schema'd tools, and treat that as the audit design.** Not
   because tools are tidier than file writes, but because a bypass path is a hole in the record.
   Auditability requires a chokepoint; it is not obtainable by logging harder.

5. **Split the trusted substrate from the semantic loop, and put the boundary at the model call.**
   exo's containment argument is the reusable part: the trusted layer must stop before any decision
   that requires semantics, because admitting one such decision drags the rest in and the trusted layer
   stops being small enough to trust.

## What not to

- **Do not adopt the self-modification loop for a domain where being wrong is expensive.** Validating a
  change on the only copy of the system is exactly the pattern the project itself flags as a gap.
  Take the split, the log and the inventory; do not take "rebuild and see."
- **Do not treat "the agent can't modify the log" as an architectural guarantee** when it is a
  configuration default, and do not port the sentence without porting the footnote.
- **Do not use it where actions leave the blast radius of the undo button.** Rewind covers a
  filesystem. Money moved, messages sent, records written to a third-party system are outside it.
- **Do not copy the always-inject-everything memory model past a small set of short facts** — the
  project itself scopes it that way and describes the read path as the thing that would need to change.
- **Do not read the README's capability list as the built set** (see Limits below).

## Embodiment

`embodiment: none`. exo was not installed or run. No canonical task, no trace. Nothing in this spec
is behavioural evidence — every claim above comes from documentation, not from watching the harness
operate. Per `FORMAT.md` §4.3, this section is optional in v1 and becomes required once four or more
specs exist in the library or once any claim here depends on a run to confirm; both conditions are
unmet for this spec today.

## Limits of this spec

- **Source read, code not read.** Every claim here comes from documentation in the repository, not
  from the Rust or TypeScript implementation. Whether the code matches the docs is unchecked. For a
  spec whose central finding is a mismatch *between two docs*, that limit is worth weighing.

- **The README overstates what is built, and I verified the contradiction but not its resolution.**
  The README says exo *"can clone itself, and even manage a lineage of clones"* and lists lineage
  management as a current capability. `docs/SELF-CONTROL.md` §7 says of cloning and migration:
  *"Nothing implements this today; this section sketches the intended shape."* I did not determine
  which is current — the docs could be stale in either direction. Treat the README's capability list
  as aspirational until checked against code.

- **Unverified project claims, recorded as claims.** *"We've had agents learn to play games,
  cost-optimize themselves, build complex systems"* — no artefact, run or measurement is offered, and
  I did not look for one. Likewise the concept documentation's assertion that the same agent can run
  *"via Codex, Claude Code, the Cursor SDK, or your own executor"*; I found no executor implementations
  other than exo's own in the material read.

- **Fetched but not read:** `exoharness/docs/sandbox-snapshots.md`, `exoharness/docs/tools.md`,
  `exoharness/docs/http.md`, `exo/SELF.md`, `exo/prompts/me.md`, the six adapter READMEs, and the
  design notes under `exoharness/docs/design/`. `exo/prompts/me.md` in particular would sharpen the
  verification section — several safety properties described above are prompt-level rules, and I have
  characterised them from a document *about* the prompts rather than from the prompts.

- **No hands-on run.** exo was not installed or executed. `embodiment: none` reflects this exactly.
  Snapshot/rewind is documented as backend-dependent (Docker warm sandboxes support it, other backends
  "report clear errors"); which backends actually work is untested.

- **`lifecycle: version-changing`** on the project's own statement that it is *"still in the early
  stages of development"* with three named areas of active work. A spec written against commit
  `5bc77ce` should be assumed to drift quickly.

- **Not compared.** Placing exo against Temper and RLM is the point of building this library and none
  of it is done here. The recoverability-versus-soundness distinction in "Which axis" is the hinge I
  expect to use, and it is currently asserted from one side only.

- **Migrated, not re-researched.** This spec was originally written against pavlos's ten-section
  research-record format and reshaped into zygos's format (`FORMAT.md` §4) without returning to the
  primary sources a second time. The reshaping moved prose between sections — Architecture split into
  Loop and Boundaries — and added an `Economics` section that the original format did not ask for;
  that section's content is new synthesis from material already read, not from a fresh fetch. No claim
  was added that the sources above do not support.

## Sources

All fetched as raw markdown pinned to commit `5bc77ce7c7a2921794083d58c926cf721c14bf8a`, not to
`main` — a branch ref changes content silently and still resolves, so a link check cannot catch drift.

| Source | Type | Retrieved |
|---|---|---|
| [`README.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/README.md) | primary — project self-description | 2026-08-16 |
| [`docs/RSI.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/docs/RSI.md) | primary — design rationale | 2026-08-16 |
| [`docs/SELF-CONTROL.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/docs/SELF-CONTROL.md) | primary — capability areas, state inventory, self-declared gaps | 2026-08-16 |
| [`exoharness/docs/spec.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/exoharness/docs/spec.md) | primary — substrate spec and data model | 2026-08-16 |
| [`exo/docs/EXO-BASICS.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/exo/docs/EXO-BASICS.md) | primary — concepts and tool surface | 2026-08-16 |
| [`website/docs-src/concepts/exoharness-and-executor.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/website/docs-src/concepts/exoharness-and-executor.md) | primary — published concept doc | 2026-08-16 |
| [`website/docs-src/concepts/time-travel.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/website/docs-src/concepts/time-travel.md) | primary — published concept doc | 2026-08-16 |
| [`website/docs-src/concepts/canonical-agent.md`](https://github.com/exoharness/exo/blob/5bc77ce7c7a2921794083d58c926cf721c14bf8a/website/docs-src/concepts/canonical-agent.md) | primary — published concept doc | 2026-08-16 |
| Repository tree at `5bc77ce` | primary — used to locate docs and confirm what exists | 2026-08-16 |

**Source defect noted:** the README links the RSI document as `exo/docs/RSI.md`; the file is at
`docs/RSI.md`. The link 404s. Recorded because it is evidence about the documentation's state, and
because the RSI document is the one carrying the footnote that qualifies the central safety claim.

**Provenance note on this migration:** the original research pass (pavlos, 2026-08-16) is the
`verified_at` date retained here. No source was re-fetched for the migration; frontmatter and body were
reshaped from that pass's own text. If a future edit adds new claims to this spec, re-verify against
the sources above rather than extending on memory of the original pass.
