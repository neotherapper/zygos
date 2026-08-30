---
name: pi
title: "Pi (Earendil's Pi Coding Agent)"
url: https://pi.dev
artifact_url: https://github.com/earendil-works/pi/tree/853a80d26c90a14c1886f0ebb8ffaae133ca2185
commit: 853a80d26c90a14c1886f0ebb8ffaae133ca2185
language: TypeScript
kind: agent-harness
license: MIT
status: active development
lifecycle: version-changing
provenance: primary
verified_at: 2026-08-31
axis: [A]
primitives: [agent, tool, extension, skill, prompt-template, session-tree, lane, operation, compaction, pi-package]
embodiment: none
---

# Pi (Earendil's Pi Coding Agent)

## Philosophy

Pi's stated position is that a harness should be minimal and extensible rather than opinionated: *"Pi is aggressively extensible so it doesn't have to dictate your workflow. Features that other tools bake in can be built with extensions, skills, or installed from third-party pi packages. This keeps the core minimal while letting you shape pi to fit how you work."* The same paragraph frames the default as intentional absence: *"Pi ships with powerful defaults but skips features like sub agents and plan mode. Instead, you can ask pi to build what you want or install a third party pi package that matches your workflow."*

What it refuses to bake in is enumerated explicitly, each with the same resolution — build it yourself via the extension surface (Markdown link targets elided in quotes; plain text otherwise verbatim):

- **No MCP.** *"Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support [Why?](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/)."*
- **No sub-agents.** *"There's many ways to do this. Spawn pi instances via tmux, or build your own with [extensions](#extensions), or install a package that does it your way."*
- **No permission popups.** *"Run in a container, or build your own confirmation flow with [extensions](#extensions) inline with your environment and security requirements."*
- **No plan mode.** *"Write plans to files, or build it with [extensions](#extensions), or install a package."*
- **No built-in to-dos.** *"They confuse models. Use a TODO.md file, or build your own with [extensions](#extensions)."*
- **No background bash.** *"Use tmux. Full observability, direct interaction."*

The root README states the trust consequence plainly: *"Pi does not include a built-in permission system for restricting filesystem, process, network, or credential access. By default, it runs with the permissions of the user and process that launched it."* If stronger isolation is needed, the project points to external containerization — a Gondolin micro-VM extension, plain Docker, or OpenShell — not to an in-harness gate.

The durable-runtime specification (`agent/docs/harness.md`) gives the deeper design claim: *"A durable runtime for agent conversations. It persists conversation and operation state so interrupted work can resume without repeating settled effects."* Its first principle is that every durable payload lives in one of three stores — entries, registers, usage ledger — and *"there is no third place."* That is the philosophy at the storage layer corresponding to the minimalism at the product layer: define the smallest durable substrate that can resume correctly, then let everything else be an extension.

## Primitives

| Primitive | What it is | Why it matters |
|---|---|---|
| **Agent** (`@earendil-works/pi-agent-core`) | Stateful agent with tool execution and event streaming. `Agent` owns `AgentState` (system prompt, model, thinking level, tools, messages), exposes `prompt()` / `steer()` / `followUp()` / `continue()`, and emits `agent_start`, `turn_start`, `message_*`, `tool_execution_*`, `turn_end`, `agent_end` | The semantic loop. Swappable; the durable harness and the TUI are built atop it, not inside it |
| **Tool** | Built-ins (`read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find`, `ls`) plus extension-registered or SDK-supplied custom tools. Typed via TypeBox schemas, with `execute(toolCallId, params, signal, onUpdate, ctx)` | Default surface is four tools (`read`, `write`, `edit`, `bash`); everything else is added explicitly. Tool choice is the capability boundary |
| **Extension** | TypeScript module exporting `default (pi: ExtensionAPI) => void \| Promise<void>`. Registers tools, commands, shortcuts, flags, and subscribes to ~30 lifecycle events (`session_start`, `before_agent_start`, `context`, `tool_call`, `tool_result`, `before_provider_request`, `session_before_compact`, etc.) | The only way to add behavior the core refused to bake in. An async factory can fetch remote config before `session_start` but must defer background resources until a session event |
| **Skill** | Agent Skills standard (`SKILL.md` + frontmatter `name`/`description`), progressively disclosed. Only names and descriptions are injected into the system prompt; bodies load on demand via `read`. Invoked as `/skill:name` | Prompt-level extensibility without code. Reuses the same mechanism as exo's skills; colocated with Claude Code / Codex skill directories if configured |
| **Prompt template** | Markdown file expanded via `/name`. Lives in `~/.pi/agent/prompts/`, `.pi/prompts/`, or a pi package | The lightest extension surface — a reusable prompt without logic |
| **Theme** | Terminal theme file (`dark`, `light` built in); hot-reloads on edit | Presentation-only, but part of the package surface and therefore shareable |
| **Pi package** | Distribution unit for extensions + skills + prompts + themes via npm (`npm:@foo/bar`) or git (`git:github.com/user/repo@v1`). Declared via `pi` key in `package.json` or conventional directories; installed to `~/.pi/agent/npm/` or `~/.pi/agent/git/` | Turns any extension composition into a versioned, shareable unit. Install is execution of arbitrary code — *"Extensions execute arbitrary code, and skills can instruct the model to perform any action including running executables"* |
| **Session tree** | JSONL file (`~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`) with `SessionHeader` + `SessionMessageEntry` / `CompactionEntry` / `BranchSummaryEntry` / `CustomEntry` / `CustomMessageEntry` / label / model-change entries. Each entry has `id` / `parentId`, forming a tree that supports in-place branching without new files | The durable conversation. Compaction entries carry `summary` + `retainedTail` and act as checkpoints; `buildContextEntries()` never reads past the newest compaction on the active path |
| **Lane** | Named cursor into the session tree (every session has `main`). Owns `lane.leaf`, `lane.config` (model + thinking level + active tools), `lane.state` (`currentOperationId`, `pendingNextRun`), and at most one `Operation` | Parallel work over shared history without copying it. Two lanes at the same leaf diverge on next append; additional lanes cover Slack threads, sub-agents, and other concurrent work |
| **Operation** | One accepted unit of lane work: `run`, `compaction`, or `navigation`. Immutable `op.meta` plus total `op.state` (the program counter) plus per-step `op.tool_args` and `op.preparation` | Makes interruption recoverable: after every step the harness overwrites `op.state` with complete current state, so recovery reads one register and switches on it |
| **Compaction** | Summarization of older messages as a `compaction` entry with `summary`, `retainedTail`, `tokensBefore`, and optional `details`/`usage`/`fromHook` | Lossy context reduction that the tree preserves as an entry. Triggered manually (`/compact`), on threshold, or on overflow (auto-retry after summarizing). Customizable or cancellable via `session_before_compact` |
| **ModelRuntime** | Unified multi-provider LLM API (`@earendil-works/pi-ai`). Maintains a tool-capable model catalog per provider (Anthropic, OpenAI, Google, Azure, Bedrock, Copilot, etc.), refreshable from provider catalogs or `~/.pi/agent/models.json`. SDK surface is `ModelRuntime.create()` + `getModel()` / `getAvailable()` | Decouples model selection from harness logic. Custom providers and OAuth are extensions; built-in providers cover subscriptions and API keys |

## Loop

Three nested loops at different timescales, plus the durable state machine that makes the innermost one resumable.

**1. Agent loop (one `prompt()` call, from `pi-agent-core`).** The `Agent` class owns semantics — prompt assembly, model calls, tool dispatch:

```
prompt("Hello")
├─ agent_start
├─ turn_start
├─ message_start/end  { user }
├─ message_start → message_update* → message_end  { assistant + optional toolCalls }
├─ tool_execution_start → (tool_call hook) → execute → tool_result hook → tool_execution_end   (per call; parallel by default)
├─ message_start/end  { toolResult }   (in assistant source order regardless of completion order)
├─ turn_end
│   ├─ steering queued? → inject, next turn
│   ├─ no tool calls and no steering? → check followUp queue
│   └─ shouldStopAfterTurn true? → exit before polling queues
└─ agent_end   (awaited subscribers count toward settlement)
```

Tool execution is `parallel` by default: calls are preflighted sequentially, executed concurrently, but `tool_execution_end` fires in completion order while `toolResult` messages and `turn_end.toolResults` still emit in assistant source order. Setting any tool's `executionMode: "sequential"` forces the whole batch sequential. `beforeToolCall` can `block` a call; `afterToolCall` can patch `content`/`details`/`isError`. Every tool result may set `terminate: true`, but the loop only skips the follow-up LLM call when *every* finalized result in the batch terminates. `transformContext` / `convertToLlm` run before each LLM call; `shouldStopAfterTurn` can halt before queued messages are polled.

**2. Coding-agent harness loop (one lane, from `pi-coding-agent`).** The interactive mode wraps the agent loop with session, queue, and structural concerns. The extension lifecycle makes the order explicit:

```
user sends prompt
├─ extension commands checked first (bypass if found)
├─ input event (can transform or handle; skill/template expansion follows if not handled)
├─ before_agent_start (can inject message, modify system prompt)
├─ agent_start → [turn loop as above, with per-turn context / before_provider_* / after_provider_response hooks]
├─ agent_end → agent_settled (no retry/compaction/follow-up left)
└─ next prompt
```

Two additional harness loops interleave with the run:

- **Message queue loop.** While streaming, `Enter` queues a *steering* message (delivered after the current assistant turn's tool calls), `Alt+Enter` queues a *follow-up* (delivered only after the agent finishes all work). `steeringMode` / `followUpMode` (`"one-at-a-time"` vs `"all"`) control draining; `tool_call` handlers see session state synchronized through the current assistant message but are not guaranteed to see sibling results from the same batch in parallel mode. `ctx.isIdle()` is false until retries, auto-compaction retries, and queued continuations settle.

- **Compaction / navigation loop.** `/compact` or automatic threshold/overflow triggers `session_before_compact` (cancellable, or returns custom `{ summary, firstKeptEntryId, tokensBefore }`), then `session_compact` on success or `session_compact_failed` on abort. `/tree` navigation follows the same pattern (`session_before_tree` → `session_tree`). Extensions can supply custom compaction summaries, including cost-bearing LLM-generated ones.

**3. Durable operation state machine (from `agent/docs/harness.md`).** Every lane operation is a total state machine whose current state lives in one register (`op.state/{operationId}`) overwritten after each transition. Terminal completion deletes `op.meta`, `op.state`, `op.tool_args`, and `op.preparation` and writes `lane.lastResult`. Illustrative trace for a Slack thread (abbreviated ids, each `TX[...]` one atomic commit; synthesized from §0.4 and §3.7) shows the shape:

```
TX[ insert n1 (user), upsert op.meta/O, upsert op.state/O = checkpoint, upsert lane.leaf=n1 ]
TX[ upsert op.state/O = assistant ready ]
TX[ upsert op.state/O = effect_pending (reserves response n2, usage u1) ]
… provider streams …                          ← uncertain window
TX[ insert n2, insert usage u1, upsert lane.leaf=n2, upsert op.state/O = tools (result id n3) ]
TX[ upsert op.tool_args/O:s1:0, upsert op.state/O = call 0 effect_pending (replay: never) ]
… tool runs …
TX[ insert n3, upsert lane.leaf=n3, upsert op.state/O = checkpoint ]
TX[ delete op.meta/O, op.state/O, op.tool_args/O:*, upsert lane.lastResult, lane.state={currentOperationId:null} ]
```

Provider requests and tool calls are wrapped in an *effect sandwich*: intent commit (reserving result ids) → effect (non-durable) → settlement commit (output + usage + next state). Crash between any two transactions leaves exactly one durable sentence as the last committed state; recovery reads five register point-lookups per lane and continues. The one genuinely uncertain window — intent durable but settlement absent — has a stated policy: assistant retries under the captured retry policy or synthesizes an error, tools re-execute only if both stored and current declarations say `safe`.

Per-round mechanics that follow: the footer reports `↑ input, ↓ output, R cache read, W cache write, CH cache hit rate, cost, context usage` inclusive of summary generation; intermittent `before_provider_request` payload rewrites are not reflected in `ctx.getSystemPrompt()`; and `SessionManager.buildContextEntries()` walks the tree but never reads past the newest compaction because `retainedTail` makes it a self-contained checkpoint.

## Boundaries

**Trusted vs swappable.** The durable harness (three stores + operation state machine + lane mutation line) is the trusted substrate. The `Agent` (prompt assembly, model selection, `transformContext` / `convertToLlm`, tool choice) is explicitly swappable — *"The session layer manages durable data and exposes typed tree views. The harness drives lanes"* — and tools, extensions, skills, prompt templates, themes, and even the TUI are above the line. The `pi-ai` provider registry is similarly swappable: a missing or swapped registry entry *"fails the request in-band, like an unknown tool."*

**Sandboxing: none by default.** The project states this as a design choice, not an omission: the coding agent runs with the invoking user's filesystem, process, network, and credential permissions. External containerization is the boundary when one is needed:

- **Gondolin extension** — keep `pi` and provider auth on the host while routing built-in tools and `!` commands into a local Linux micro-VM.
- **Plain Docker** — run the whole `pi` process in a local container.
- **OpenShell** — run the whole `pi` process in a policy-controlled sandbox.

Extensions themselves are unsandboxed TypeScript executed via `jiti` with full system access; the docs warn: *"Extensions run with your full system permissions and can execute arbitrary code."*

**Project trust gate.** Before loading project-local settings, resources, or project `.agents/skills`, pi asks whether to trust the project folder (or a parent) against `~/.pi/agent/trust.json`. Only global/user extensions and CLI `-e` extensions participate in the `project_trust` event; project-local extensions, project packages, and `.pi/settings.json` load only after trust. Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) do not prompt — `defaultProjectTrust` (`ask` / `always` / `never`) controls the fallback, overridable per-run with `--approve` / `--no-approve`.

**State inventory.**

| State category | Where it lives | Survives process crash? | Survives `/new` / `resume` / `fork`? | Survives compaction / `/tree` navigation? | Notes |
|---|---|---|---|---|---|
| Conversation entries (messages, tool results, `compaction`, `branch_summary`, `custom`) | JSONL entries (write-once, `id`/`parentId` tree); SQLite branch index rebuildable from entries | **Yes** — append-only; a torn final line is discarded whole, never a partial transaction. Entries and usage rows are never deleted (precise rewrite §2.9 is the sole exception) | `/new` starts a new file; `/resume` reopens; `/fork`/`/clone` copy the active path into a new file. The tree itself is never mutated by these operations | Compaction appends a `compaction` entry; context building stops at the newest compaction but the tree retains all entries. Navigation appends a `branch_summary` and moves `lane.leaf` | The only state the provider context rebuilds from; `retainedTail` makes newer compactions self-contained checkpoints |
| Lane registers (`lane.leaf`, `lane.config`, `lane.state`, `lane.lastResult`) | Registers (`lane.*` namespace), keyed by lane name | **Yes** — point-lookup on restore; `lane.lastResult` is the one bounded register per lane, overwritten by each terminal transaction, never read by recovery | New session gets fresh lane registers; fork copies `leaf` + `config` but not in-flight `currentOperationId` | Compaction/navigation move `lane.leaf` and clear `currentOperationId` via terminal transaction; `lane.lastResult` overwritten | `lane.state.currentOperationId` is the liveness bit; `op.*` registers exist iff it is non-null |
| Operation registers (`op.meta`, `op.state`, `op.tool_args`, `op.preparation`) | Registers (`op.*` namespace), keyed by operation id | **Yes**, iff operation was open — `op.state` is the program counter read on restore. Five point-lookups (3 lane + `op.meta` + `op.state`) suffice | Not carried across sessions — terminal transaction deletes them atomically with clearing `currentOperationId` | In-run compaction leaves `op.preparation` after `resumeAfter` but deletes on terminal; standalone compaction deletes all `op.*` on terminal | A 30-turn run overwrites `op.state` ~30 times then deletes it; zero dead state remains (JSONL defers physical reclamation to snapshot compaction) |
| Pending queued content (`steer`, `followUp`, `nextRun`, deferred writes) | `pending.entry/{id}` registers, enqueued by id in `op.state.inbox` / `lane.state.pendingNextRun` | **Yes** — owned by operation if enqueued mid-run (deleted by terminal cleanup), or by lane if queued while idle (`pendingNextRun` outlives operations) | Idle-queued `pendingNextRun` survives session switches until consumed or cancelled; operation-owned pending dies with the operation | Consumed by queue drain: placement transaction writes the entry and deletes the register atomically | Double-write is the one deliberate redundancy: register at enqueue, entry at placement; cancellation deletes the register with no entry ever appearing |
| Usage ledger (provider token/cost rows, tool-reported usage) | Append-only `usage` rows; `getStats()` is a maintained projection (message count + ledger sum) | **Yes** — never deleted by terminal cleanup; survives everything orchestration state does not. `scanUsage({fromSeq})` catches up after downtime | New session starts at zero; forked session's ledger starts at zero (entry-local display usage on copied entries remains) | Compaction/navigation may contribute a usage row for the summary generation; still append-only | Billing survives orchestration resets by construction; synthetic settlements write zero usage under reserved ids |
| Facts (`fact.name`, `fact.label`, `fact.custom`) | Registers (`fact.*`), latest-wins | **Yes** — durable registers; JSON `null` is a legal custom value distinct from deletion | Survive across sessions only if explicitly copied; labels are per-entry branch bookmarks | Unaffected — fact writes commit immediately and never move `lane.leaf` | Deleting an unset fact is a no-op; no tombstones |
| Credentials & provider catalog (`~/.pi/agent/auth.json`, `models.json`, `models-store.json`) | Files outside the session; resolved at dispatch time by durable identities in `op.state` | **Yes** — on disk, but a missing or swapped registry entry at dispatch fails in-band as a synthetic error | Survive — global to the agent dir; per-cwd overrides via `PI_CODING_AGENT_DIR` | Unaffected | Rotation is safe: captured `model` identity is resolved through `Models` at request time |
| Extensions / skills / prompts / themes (code & markdown on disk) | Files in `~/.pi/agent/extensions/`, `.pi/extensions/`, `~/.pi/agent/skills/`, etc., plus installed pi packages in `~/.pi/agent/npm/` or `~/.pi/agent/git/` | **Yes** — on disk; reloaded on `session_start` / `/reload`. Async factories are awaited before `session_start` | Project-local resources require trust; global ones load unconditionally | `session_before_compact` / `session_before_tree` hooks can supply custom summaries; `/reload` rebinds extensions | No sandboxing; a malicious extension has the same permissions as the user |
| External effects (files written, commands run, messages sent via adapters) | Outside the session entirely | **N/A** — already happened | **N/A** | **N/A** | Blast radius is unbounded. Rewind is tree navigation, not filesystem undo. `send_adapter_message`-style explicit send is a prompt-level convention, not a structural gate |

**Blast radius.** Rewinding via `/tree` or branching via `/fork` moves the active leaf in the tree; it does not retract a file edit, a `bash` deletion, or a Slack message already sent. The mitigation is the `tool_call` hook (block or mutate `event.input` before execution) — a prompt/extension-level rule, not a harness gate — plus external containerization for stronger isolation. The durable runtime's guarantee is narrower and precise: no effect repeats without an explicit replay policy, and no conversation state is lost.

## Verification strategy

| Method | Present? | Notes |
|---|---|---|
| Observability-driven feedback | **Partial — reports, does not gate** | Rich event surface (`agent_start`/`agent_end`/`agent_settled`, `turn_start`/`turn_end`, `message_*`, `tool_execution_*`, `context`, `before_provider_request`, `after_provider_response`, `session_before_compact`/`session_compact`, etc.) plus `TelemetryContext`/`Telemetry` typed schemas and a `usage` event per commit. The agent or an extension closes the loop by reading these; nothing in the default harness acts automatically. The `GEPA`-class autonomous evolution loop Temper has is absent — pi's evolution is the user installing a different extension or package |
| Shadow evaluation | **No** | Not present. No canary path that runs a changed harness or model against a cloned session and compares behavior before adopting. The closest is manual `/fork` + re-run, which is a user convention, not a harness mechanism |
| Deterministic simulation testing | **No** (as a harness-level gate) | The harness specification (`agent/docs/harness.md` Part 9) defines invariants, a race catalog, and test tiers, and the repo runs CI plus `test.sh`/`pi-test.sh` with faux-provider harnesses — but these are ordinary software tests of pi, not a harness-level simulation that gates agent-authored changes before they take effect. There is no seeded-PRNG fault injection over the lane mutation line the way Temper's Level 2 does |
| Formal specification | **No** (as a gate) | `agent/docs/harness.md` is a formal implementation specification — three stores, atomic transaction rule, durable program counter, invariants (§9.1) — but it is a design document, not a verification gate. No Z3/Stateright-style cascade proves invariants before a change ships. The spec's invariants are tested (see above), not proved |

**What gates vs what reports.** The only hard gates in the default installation are: the `lane` mutation line serializes all operation acceptance, queue enqueue/cancel, aborts, and configuration changes (concurrent mutations have exactly two durable histories, both tested — §4.3); `before_provider_request` type validation and the atomic transaction rule (no partial commit is visible); and the single-writer-per-session claim enforced by `writer_lease` on SQLite (with process ownership and a torn-line-discard rule on JSONL). Everything else — tool effects, model output, compaction quality, navigation summaries — reports through events and the session tree but does not block. An extension can add a gate (e.g., `tool_call` returning `{ block: true, reason }`), but that is extension policy, not a harness invariant.

## Which axis

**Axis A, and the answer is recoverability, not prevention — with a narrow durability-prevention layer underneath.**

At the file/process/network boundary, pi provides no prevention. The shipped default has no permission system; a model-authored `rm -rf` is not blocked, not sandboxed, and not conditional on a proof. The harness readily enters a broken external state, and the design is explicit that this is the user's to mitigate (containerize, or write an extension that blocks).

At the conversation-durability boundary, pi provides genuine prevention of a different, smaller class of broken state: the atomic transaction rule, the single-writer-per-session lease, the total `op.state` program counter, and the five-lookup restore. These prevent the session itself from entering a corrupt or ambiguous state — no partial transaction, no torn write, no inferred position from absence, no concurrent writer interleaving. This is prevention, but scoped to the session store, not to what the agent does through it.

Recoverability is the primary Axis A property and the one the harness is organized around:

| | Prevents entering a broken state | Restores from a broken state |
|---|---|---|
| External effects (files, processes, network, credentials) | **no** — trusts the model; extensions or containers must be added | **no** — navigation/branching does not undo external effects |
| Session durability (conversation + operation state + ledger) | **yes, narrowly** — atomic transactions, single-writer lease, total program counter | **yes** — crash at any point between transactions resumes from the last committed sentence; the one uncertain window (intent durable, settlement absent) has an explicit retry-or-synthesize policy |

**Axis B is absent and undiscussed.** Nothing in pi evaluates whether a claim the agent makes about the world is true. Provider output, tool results, compaction summaries, and branch summaries are persisted as-is. A false premise synthesized by the model flows through the same durable path as a true one, and no mechanism corroborates, attributes sources, or detects contradiction.

## Economics

Pi has a concrete per-turn cost model at the token/context layer, plus a deferred-physical-deletion cost noted in the harness spec. It does not have a backend-infrastructure cost optimizer of the kind Temper documents.

- **Context cost is first-class and visible.** The TUI footer reports `↑ input, ↓ output, R cache read, W cache write, CH latest cache hit rate, cost, context usage` inclusive of summary generation, and the `Usage` type carries `{ input, output, cacheRead, cacheWrite, totalTokens, cost: { input, output, cacheRead, cacheWrite, total } }`. The agent tracks `tokensBefore` on each compaction and `buildContextEntries()` enforces the *"context never reads past a compaction"* invariant, so compaction is the explicit cost control. Configuration is `CompactionSettings { enabled, reserveTokens, keepRecentTokens }` — both token counts finite non-negative safe integers — with manual `/compact [prompt]`, threshold-triggered, and overflow-triggered (auto-retry after summarizing) paths. Extensions can cancel or supply a custom `{ summary, tokensBefore }` via `session_before_compact`.

- **Cache invalidation is priced explicitly.** The harness spec states the invariant: *"Across the requests of one lane, provider context must only grow at the tail. An insertion before the previous request's tail invalidates the provider's KV cache and multiplies cost. This is why mid-run writes defer to checkpoints, where they append at the tail. Compaction is the one deliberate cache invalidation, and it trades that for a smaller context."* Deferred writes and `skipInboxOnce` exist to preserve prefix reuse; `PI_CACHE_RETENTION=long` opts into extended prompt cache (Anthropic 1h, OpenAI 24h).

- **Storage cost has a deferred-reclamation shape.** A 30-turn run overwrites one `op.state` register ~30 times then deletes it — logically zero dead state remains. On SQLite this is an in-place upsert. On JSONL every `set` appends, so the same run leaves ~10 dead `op.state` lines until snapshot compaction (`header + current entries + current registers + usage rows` via temp file + atomic rename). Between compactions, *"deleted pending payloads and superseded state revisions linger as bytes until compaction — logical deletion is immediate, physical deletion is deferred."* A deployment needing prompt physical removal of sensitive cancelled content compacts eagerly at terminal boundaries.

- **Catalog refresh is throttled.** Remote model catalog refreshes are throttled to once per provider per four hours unless forced via `modelRuntime.refresh({ allowNetwork: true, force: true })`; `PI_OFFLINE=1` disables all startup network operations. This is a network-cost control, not a token-cost one.

- **No backend optimizer.** Unlike Temper's `CacheOptimizer`/`QueryOptimizer` actors that tune TTLs and detect N+1 patterns, pi has no autonomous cost-reduction loop that observes usage and rewrites its own queries or cache policy. Trajectory/token counts are reported, not acted on automatically.

## Tradeoffs

**Buys**

- Smallest possible trusted core. Three stores, atomic transactions, a total program counter, and a single lane mutation line are the whole durability argument. Everything else — permissions, sub-agents, plan mode, todos, background execution, MCP, compaction strategy, even the model catalog — is an extension, so the core has little to break and the policy surface has no reason to drift into it.
- Full user control over workflow. Because no opinionated loop is baked in, a team can make pi look like Claude Code, add Git checkpointing and auto-commit, route tools through SSH, or run Doom in the TUI, without forking pi internals. Pi packages make that composition shareable.
- Resumability without repeating settled effects. The effect sandwich (intent → effect → settlement) plus the one-uncertain-window policy means a crash mid-provider-stream or mid-tool does not double-bill or double-execute (unless the tool is explicitly `safe` to replay). In-flight work resumes from the last committed sentence by reading five registers.
- Tree-structured conversation as a durable primitive. In-place branching, forking, cloning, and compaction summaries are not bolt-on features but consequences of the `id`/`parentId` entry tree plus `lane.leaf`. An agent that explores a dead end can return to an ancestor without losing the abandoned branch's history.
- Provider agnosticism as a distribution property. `ModelRuntime` abstracts OpenAI, Anthropic, Google, Bedrock, Copilot, and custom providers behind one `Model` identity; `pi-ai`'s `StringEnum` and `api: "openai-completions" | "anthropic"` adapters let a local `llama.cpp` router appear as just another provider, and extensions can add OAuth or custom APIs without touching core dispatch.

**Pays**

- No safety by default where it matters most. The external blast radius is unbounded and unmitigated in the shipped configuration. A harness that couples a powerful model to `bash` with the user's full permissions and no gate is relying entirely on the model's judgement plus whatever extension the user remembered to install. Containerization is documented but opt-in.
- Extension power is extension risk. The same surface that lets an extension replace any tool or intercept any event lets a malicious or buggy extension exfiltrate credentials, suppress tool results, or rewrite context (`context` event handlers may modify messages arbitrarily). Review is the mitigation, not sandboxing.
- Minimalism pushes integration burden to the user. Teams that want sub-agents, plan mode, permission gates, or MCP must find, evaluate, and maintain extensions or packages for each. The core's refusal to choose is a real choice with a real maintenance cost — the opposite of Temper's and DeepSeek Harness's "batteries included" trade.
- Compaction is lossy and user-visible. Automatic threshold compaction fires at most once per trigger boundary and can be cancelled, but when it does fire it summarizes older messages irreversibly for context (the full history remains in the JSONL file, reachable via `/tree`). A poor summary silently degrades downstream reasoning.
- Durability is single-writer, single-node, and single-file-per-session. One process owns one session file; the SQLite `writer_lease` enforces this, but Memory and JSONL rely on process ownership and a JSONL session opened twice is undetected corruption. There is no replication, no cross-session transaction, and no multi-writer lane — lanes are the intended concurrency primitive, not concurrent writers.
- The formal harness specification (`agent/docs/harness.md`, ~229 KB) describes a more complete durable runtime than the shipped coding-agent session format alone implements. Reading the spec as the current system overstates what `packages/coding-agent/src/core/session-manager.ts` does today.

## What to steal

1. **The three-store durable substrate with a total program counter.** Entries (write-once tree) + registers (namespaced current values) + usage ledger (append-only), atomic transactions as the only write primitive, and one register (`op.state`) overwritten with the *complete* next state after each step. Recovery becomes five point-lookups and a switch, not a journal replay. Applicable to any system that must resume without repeating settled effects.

2. **The effect sandwich with reserved ids.** Intent commit (reserving result ids) → non-durable effect → settlement commit (output + usage + next state). The one genuinely uncertain window is explicit and has a named policy per effect kind (assistant retry-or-synthesize, tool replay-only-if-`safe`, deferred wait-for-`resume()`). Worth copying wherever external calls can be billed or have side effects.

3. **Extension-driven minimalism as a product strategy.** Define a stable `ExtensionAPI` (tools, commands, shortcuts, flags, ~30 typed events, `ctx.ui` / `ctx.sessionManager` / `ctx.modelRegistry`), keep the core at four default tools, and let every opinionated workflow be a package. The docs' own framing — *"Features that other tools bake in can be built with extensions"* — is portable well beyond coding agents.

4. **Progressive skill disclosure.** Inject only skill names and descriptions into the system prompt; load full `SKILL.md` bodies on demand via `read` (or forced via `/skill:name`). This keeps a large skill library affordable in context while keeping bodies versioned alongside code. The same pattern applies to prompt templates.

5. **Tree plus compaction as a checkpoint.** Newer `compaction` entries embed `retainedTail` so `buildContextEntries()` never reads past the newest compaction — the compaction is a self-contained checkpoint rather than a pointer. Branch summaries (`branch_summary` with `fromId`) preserve context from abandoned paths without replaying them. Any long-running conversational system needs both.

6. **Lane as the concurrency primitive.** Rather than multi-writer sessions or complex locking, give each concurrent thread a named lane (cursor) over shared history. *"Two lanes at the same leaf simply diverge on their next append."* The lane mutation line serializes only per-lane acceptance and queue operations, leaving provider/tool work fully concurrent.

## What not to

- **Do not adopt the "no permission system by default" posture for a domain where external effects are irreversible or regulated.** Pi's threat model is explicit — *"runs with the permissions of the user and process that launched it"* — and it is suitable for a local developer tool where the user is the principal. It is not suitable as a hosted agent touching production data, payment systems, or multi-tenant stores without adding the containerization or extension gates pi deliberately left out.

- **Do not treat pi packages as safe to install without review.** An extension *"can execute arbitrary code"* and a skill *"can instruct the model to perform any action including running executables."* The install surface (`pi install npm:@foo/bar`, `pi install git:github.com/user/repo@v1`) is a full-code-execution grant. Do not add it to automated setup without pinning and auditing.

- **Do not port the single-file-per-session JSONL store to a replicated or multi-writer deployment.** The design's single-writer claim is enforced by a `writer_lease` on SQLite only; JSONL relies on convention. Opening the same JSONL file twice is silent corruption. If you need multi-writer or replication, implement the partitioned Postgres backend sketched in Part 6 of the harness spec, or choose a different store.

- **Do not read `agent/docs/harness.md` as the shipped system.** It is an implementation specification for a durable runtime, not a description of the current `packages/coding-agent` storage. Conflating the two overstates the guarantees of the JSONL session manager and understates the work to reach the spec's full recovery and invariant coverage.

- **Do not copy the four-tool default without considering the task.** `read`, `write`, `edit`, `bash` are sufficient for coding; a non-coding domain (research, data analysis, comms) will need different built-ins or will force the model to synthesize capabilities via `bash` that deserve first-class tools.

- **Do not rely on compaction quality without evaluating it.** The default compaction is lossy summarization; the `retainedTail` checkpoint mitigates token cost but not semantic loss. An extension that supplies custom `session_before_compact` logic should be tested on the target workload — the harness will accept any summary it is given.

## Embodiment

`embodiment: none`. Pi was not installed or run; nothing here is this spec's own behavioral evidence. Every claim above comes from documentation at the pinned commit, not from watching the harness operate. Per `FORMAT.md` §4.3, this section is optional in v1 and becomes required once four or more specs exist in the library or once any claim here depends on a run to confirm; both conditions are unmet for this spec today.

## Limits of this spec

- **Source read, code not read.** Every claim comes from `README.md` (root), `packages/coding-agent/README.md`, `AGENTS.md`, `packages/agent/README.md`, `packages/coding-agent/docs/session-format.md`, `packages/coding-agent/docs/sessions.md`, `packages/coding-agent/docs/compaction.md` (head only), `packages/coding-agent/docs/extensions.md`, `packages/coding-agent/docs/skills.md`, `packages/coding-agent/docs/sdk.md`, and `agent/docs/harness.md` (Parts 0–1, 2.1–2.3, 3.2–3.7, 3.9, 3.11–3.13, 4.1–4.9, 5.1 scanned; remainder by heading/TOC grep). The TypeScript implementation (`packages/agent/src/agent-loop.ts`, `packages/coding-agent/src/core/session-manager.ts`, etc.) was not read. Whether the code matches the harness specification — the same question that produced exo's central finding — is unchecked here. The harness specification is notably larger than what the current coding-agent storage implements; the gap is flagged above but not measured against code.

- **Fetched but not read in full:** `agent/docs/harness.md` Parts 2.4–2.8, 3.1, 3.8, 3.10, 5.2–5.8, 6–9, Appendices A–C (only headings/TOC plus targeted grep for Economics/Verification terms); `packages/coding-agent/docs/providers.md`, `docs/models.md`, `docs/custom-provider.md`, `docs/rpc.md`, `docs/json.md`, `docs/compaction.md` (body), `docs/containerization.md`, and the repository tree beyond the ten fetched files. Any of these could sharpen, qualify, or contradict a claim here — particularly `containerization.md` for the Boundaries sandboxing boundary and `compaction.md` for the Economics compaction details.

- **No hands-on run.** `embodiment: none` reflects this exactly. Session branching, compaction, lane concurrency, extension `tool_call` blocking, and the `writer_lease` single-writer enforcement are documented behaviors, not observed ones. The harness spec's crash-recovery policy (retry-or-synthesize, replay-only-if-`safe`) is a specified policy, not a witnessed recovery.

- **`lifecycle: version-changing`** on the project's own evidence of rapid iteration: lockstep versioning across all packages, `npm-shrinkwrap.json` pinning transitive deps, `storageVersion` plus migrate-on-open for sessions, and a ~229 KB implementation specification that is itself versioned. A spec written against `853a80d` should be assumed to drift quickly. `status: active development` is this spec's inference (the project does not state a `status` string at the pinned commit); if the project later publishes an explicit maturity label, prefer it.

- **Not compared.** Placing pi against exo, Temper, RLM, and DeepSeek Harness is the point of building this library and none of it is done here — except for noting that exo's README places "Pi" alongside OpenClaw and Hermes as a personal-runtime-class harness, and that pi's extension-driven minimalism is the opposite design choice from Temper's proved-before-running substrate. The recoverability-vs-prevention distinction in "Which axis" is the hinge this spec expects to use, and it is currently asserted from one side only.

- **The name-vs-thing check for `agent/docs/harness.md`.** This file is pi's durable-runtime implementation specification — what an agent *gets* when using the harness (three stores, lanes, operations, effect sandwich). It is not pi's own development harness in the Temper-`docs/HARNESS.md` sense. The check was performed and resolved in favor of the file, and the distinction is recorded here so a future reader does not inherit the opposite conflation from the filename alone.

- **Counts and scope.** The `agent/docs/harness.md` size (~229 KB) and the ten-file fetch list above are measured at the pinned commit; file counts for the repository tree as a whole were not enumerated and should not be inferred from this spec.

- **Corrected after independent fidelity review (2026-08-31).** An adversarial re-read of the pinned sources found no meaning-reversing defects but two verbatim-hygiene defects, both fixed here: (1) the six Philosophy "No …" quotes stripped Markdown link targets (`[extensions](#extensions)` etc.) without ellipsis — fixed by restoring link markup inline and noting the elision convention; (2) the Pi-package security quote in Primitives truncated mid-sentence, dropping `including running executables` — fixed by restoring the clause. The illustrative `TX[…]` trace in Loop was also captioned as synthesized from §0.4 and §3.7 rather than source text. These are the kind of defects only adversarial re-verification against the pinned sources catches; a presence check would have passed the prior draft.

## Sources

All fetched as raw markdown pinned to commit `853a80d26c90a14c1886f0ebb8ffaae133ca2185`, not to `main` — a branch ref changes content silently and still resolves, so a link check cannot catch drift.

| Source | Type | Retrieved |
|---|---|---|
| [`README.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/README.md) | primary — project self-description, supply-chain hardening, permissions statement | 2026-08-31 |
| [`packages/coding-agent/README.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/README.md) | primary — coding agent self-description, Philosophy "No MCP / No sub-agents / ..." table, modes, commands, settings, customization | 2026-08-31 |
| [`AGENTS.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/AGENTS.md) | primary — project development rules, git discipline, release process | 2026-08-31 |
| [`packages/agent/README.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/agent/README.md) | primary — `@earendil-works/pi-agent-core` Agent loop, event flow, tool execution modes | 2026-08-31 |
| [`agent/docs/harness.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/agent/docs/harness.md) | primary — AgentHarness implementation specification: three stores, conversation tree, operation state machine, execution/recovery/abort/close, public surface | 2026-08-31 |
| [`packages/coding-agent/docs/extensions.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/docs/extensions.md) | primary — extension system, events, ExtensionAPI, lifecycle | 2026-08-31 |
| [`packages/coding-agent/docs/session-format.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/docs/session-format.md) | primary — JSONL session file format, entry types, tree structure, SessionManager API | 2026-08-31 |
| [`packages/coding-agent/docs/sessions.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/docs/sessions.md) | primary — session storage, branching with `/tree`, fork/clone | 2026-08-31 |
| [`packages/coding-agent/docs/sdk.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/docs/sdk.md) | primary — SDK (`createAgentSession`, `AgentSessionRuntime`, `ModelRuntime`) | 2026-08-31 |
| [`packages/coding-agent/docs/skills.md`](https://github.com/earendil-works/pi/blob/853a80d26c90a14c1886f0ebb8ffaae133ca2185/packages/coding-agent/docs/skills.md) | primary — skills (Agent Skills standard), progressive disclosure | 2026-08-31 |
| Repository tree at `853a80d` (GitHub API, recursive — via prior fetch) | primary — used to locate docs and confirm what exists | 2026-08-29 |

**Provenance note:** `verified_at: 2026-08-31` is the date the sources above were read at the pinned commit. `provenance: primary` reflects that every quoted claim was checked against a file at that pin, not against a secondary summary.
