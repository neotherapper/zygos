---
name: rlm
title: "RLM"
url: https://github.com/alexzhang13/rlm
artifact_url: https://github.com/alexzhang13/rlm/tree/caf0bffa1acec17c062559433b4cd4ed92eee3d6
commit: caf0bffa1acec17c062559433b4cd4ed92eee3d6
language: Python
kind: inference-paradigm
license: MIT
status: Beta
lifecycle: version-changing
provenance: primary
verified_at: 2026-08-27
axis: [Neither]
primitives: [rlm, repl, lm-handler, llm-query, rlm-query, answer, context, custom-tools, compaction, persistence, logger-metadata]
embodiment: none
---

# RLM

## Philosophy

RLM (Recursive Language Models) is an inference paradigm that replaces the canonical `llm.completion(prompt, model)` call with `rlm.completion(prompt, model)`, acting as a "language model" itself. Its README states the core move directly: *"RLMs replace the canonical `llm.completion(prompt, model)` call with a `rlm.completion(prompt, model)` call, acting as a \"language model\". RLMs offload the context as a variable in a REPL environment that the LM can interact with and launch sub-LM calls inside of."* (README.md)

The positioning is a bet on CodeAct-style harnesses. The same section: *"RLMs are a bet on future \"language model\" design choices. We argue for a [CodeAct](https://arxiv.org/abs/2402.01030)-style harness (i.e. all language models should have access to a code environment) with sub-(R)LM calls as functions in code, and context / prompts as objects in code."* And explicitly against JSON tool-calling: *"We want to move away from the JSON tool-calling standard for both sub-agents and generic tool calls. The naming comes from the fact that such a system is itself a \"language model\" (a probabilistic mapping from text to text) that builds around and relies on recursive sub-LLM calls."*

What it refuses: treating the long-context problem as a context-window scaling problem, and treating decomposition as a fixed controller. The prompt given to the root model (RLM_SYSTEM_PROMPT in rlm/utils/prompts.py) encodes the refusal as instruction to push every long-context operation that would not fit comfortably in its own working window, as the orchestrator prompt begins `Your own context window is small. Push every long-context operation that would not fit comfortably in your own working window` — reading, summarizing, classifying, verifying, answering sub-questions, even recapping your own progress — into `llm_query` / `llm_query_batched` calls instead of pulling that text into your own message stream."* The orchestrator addendum makes the stance explicit: *"As an RLM, you should act as an orchestrator, not a solver."* The model is told to reserve its own tokens for high-level decisions and delegate everything else.


## Primitives

| Primitive | What it is | Why it matters |
|---|---|---|
| **RLM** | The user-facing class `RLM` in `rlm/core/rlm.py` (`RLM.completion(prompt) -> RLMChatCompletion`). Owns depth, budget, timeout, iteration limits and spawns per-call handler+environment. | The unit a caller replaces an LM call with; the recursion root. |
| **REPL environment** | Code execution surface where `context` lives as a variable (`rlm/environments/local_repl.py`, `base_env.py`). Variants: `local` (in-process `exec()`), `ipython`, `docker`, `modal`, `prime`, `daytona`, `e2b`. | Where programmatic decomposition happens — code, not JSON tools. |
| **LMHandler** | Multi-threaded TCP socket server per `completion()` (`rlm/core/lm_handler.py`, `ThreadingTCPServer`, 4-byte BE length-prefix + JSON). Auto-port `127.0.0.1:0`, daemon thread. | Decouples code execution from LM API calls; same protocol for isolated and non-isolated envs. |
| **`llm_query` / `llm_query_batched`** | Plain single/batch LM completions callable from REPL code (`depth`-independent, always `client.completion`). Per-prompt failure writes `"Error: llm() call failed - <msg>"`. | Fast one-shot extraction over a slice; batched via `asyncio.gather` with `return_exceptions=True`. |
| **`rlm_query` / `rlm_query_batched`** | Recursive child RLM call from REPL (`rlm/environments/local_repl.py` `_rlm_query` -> `RLM._subcall`). Falls back to `llm_query` when `next_depth >= max_depth`. | Gives a subtask its own handler+REPL and iteration loop; the recursive primitive the name names. |
| **`answer` dict** | `_AnswerDict({"content":"", "ready":False})` in REPL locals; `answer["ready"]=True` signals completion, `RLM.completion` loops until `REPLResult.final_answer` is set or `max_iterations` exhausts. | The only termination signal; model must write it from inside a ```repl``` block. |
| **`context` / `context_N` / `history`** | `context` alias for `context_0`; `context_1..` for additional contexts (persistent mode); `history`/`history_N` for prior trajectories when `compaction=True` or `persistent=True`. | The long payload never enters the root prompt directly; it lives in the REPL for code to slice. |
| **Custom tools** | Dict injected into REPL globals (`custom_tools`, `custom_sub_tools`); validated against `RESERVED_TOOL_NAMES` and restored by `_restore_scaffold()` each `exec()`. Isolated envs require serializable values/code strings. | Third extension surface that survives without import; per-depth scoping via `custom_sub_tools`. |
| **RLMLogger / metadata** | Optional `RLMLogger(log_dir?)` capturing `RLMMetadata` + `RLMIteration`s in-memory and optionally as JSONL for the visualizer. Returned on `RLMChatCompletion.metadata`. | Inspectability without re-running; the trajectory is the embodiment record. |
| **Compaction** | Opt-in `compaction=True` summarization when root `message_history` token count crosses `compaction_threshold_pct` of model context limit (`local`/`docker` only). | Keeps the root history within context after many turns without truncating the REPL `context`. |


## Loop

RLM has one primary loop — the per-`completion()` iteration loop — with a secondary factory loop inside each `rlm_query` that can spawn full child RLMs. The architecture doc names the three cooperating pieces and their order:

> 1. **RLM** (`rlm/core/rlm.py`) — the main loop that drives iteration.
> 2. **LMHandler** (`rlm/core/lm_handler.py`) — a per-completion TCP server that routes LM API calls.
> 3. **LocalREPL** (`rlm/environments/local_repl.py`) — the Python execution environment where model-generated code runs.

Per-call setup (`RLM._spawn_completion_context`): create LM client(s) via `get_client`, wrap in `LMHandler` and `start()` on `127.0.0.1:0` (daemon thread, per-connection thread), create `LocalREPL` with `lm_handler_address`, `context_payload`, `depth = self.depth+1`, and `subcall_fn = self._subcall` when `max_depth>1`. When `persistent=True`, reuse `_persistent_env` and call `update_handler_address` + `add_context`; otherwise create fresh and `cleanup()` on exit. `LMHandler.stop()` always runs on context exit.

Per-iteration (`for i in range(max_iterations)`):

1. **Budget/timeout check** (`_check_timeout` before the turn; `_check_iteration_limits` after) — raises `TimeoutExceededError`/`BudgetExceededError`/`TokenLimitExceededError`/`ErrorThresholdExceededError` carrying `partial_answer`.
2. **Compaction gate** (if `compaction`): `_get_compaction_status(message_history)` vs `compaction_threshold_pct`; if over, `_compact_history()` via a handler-routed LM call, then continue with compacted `message_history`.
3. **Prompt assembly**: append `build_user_prompt(i, context_count, history_count)` — the string literal is `"Turn {iter_1}/{max_iter}:"` with the `persistent`/`compaction` notes about `context_N`/`history_N`; iteration 0 prepends the safeguard You have not interacted with the REPL environment or seen your prompt / context yet — look at the context first and do not provide a final answer yet*
4. **Model call**: `_completion_turn(message_history, lm_handler, environment)` — `lm_handler.get_client(...).completion(prompt)` with the full `message_history` (`[system, metadata, user_0, assistant_0, repl_0, user_1, ...]`).
5. **Code extraction**: `find_code_blocks(response)` with regex ```` ```repl\s*\n(.*?)\n``` ```` (DOTALL); each block `execute_code` via `exec(code, combined)` where `combined={**globals, **locals}`; captures `stdout`/`stderr`, `locals` diff, and any `llm_calls`/`rlm_calls` that fired during `exec()`.
6. **REPL output formatting**: `format_iteration` emits exactly two messages per iteration with code — one `assistant` (the raw response) and one combined `user` with `"REPL output (block {i + 1}):" `if multi else "REPL output:"` (rendered as `REPL output (block N):` with `N = i+1`)` headers, each block truncated at `max_character_length=20000`.
7. **Termination**: scan `code_blocks[*].result.final_answer` (`answer["ready"]` flipped truthy via `_AnswerDict.on_ready`); if found, return `RLMChatCompletion` with `usage_summary`, `execution_time`, and `logger.get_trajectory()`. Otherwise append `new_messages` to `message_history` (and `append_compaction_entry` if compacting) and loop.

The secondary loop is inside `LocalREPL._rlm_query` / `_rlm_query_batched`: if `subcall_fn` exists, call `RLM._subcall(prompt, model)` which computes `remaining_timeout/budget/tokens = max - elapsed/spent`, and if `next_depth >= max_depth` does a plain `client.completion()`; otherwise creates a child `RLM(depth=next_depth, max_timeout=remaining, ...)` and runs `child.completion(prompt)` with its own fresh handler+REPL on a different auto-port. `llm_query_batched` fans out via `LMHandler._handle_batched` (`asyncio.gather(..., return_exceptions=True)`, semaphore `batch_max_concurrent`); `rlm_query_batched` iterates `subcall_fn` per prompt, collecting `"Error: llm() call failed - <msg>"` per slot.

If the loop exhausts, `_default_answer(message_history, lm_handler)` makes one final plain LM call for a best-effort answer. `KeyboardInterrupt` raises `CancellationError` with `partial_answer`.


## Boundaries

## Trusted vs swappable

The harness boundary is the REPL namespace boundary, not a deployment seam. The trusted piece is `LocalREPL._SAFE_BUILTINS` — `eval`, `exec`, `compile`, `input` are removed from `__builtins__`, but the REPL still runs `exec(code, combined)` in the same Python interpreter (docs/architecture.md: *"There is no subprocess, no fork, and no IPC for code execution"*). The doc calls this *"Limited sandbox: Dangerous builtins (`eval`, `exec`, `compile`, `input`) are removed from the namespace. This is a soft sandbox — it prevents accidental misuse but is not a security boundary."* No capability seam, no plugin revocation — the only isolation is what was stripped from `__builtins__` and what `_restore_scaffold()` repairs.

Swappable pieces are the **environment** (`local` / `ipython` / `docker` / `modal` / `prime` / `daytona` / `e2b`) and the **LM backend** (`openai` / `anthropic` / `gemini` / `azure_openai` / `portkey` / `openrouter` / `vllm`) via `rlm/clients/` and `rlm/environments/` registries. Isolated envs swap the transport: sandboxed code cannot TCP to `LMHandler`, so the sandbox runs a Flask broker with `/enqueue` (blocks), `/pending` (host polls), `/respond`, `/health` — host `ModalREPL` polls `tunnel_url/pending` every 100ms, forwards to `LMHandler` over socket, POSTs to `/respond` to unblock.

## Sandboxing

| Environment | Isolation | Transport for `llm_query`/`rlm_query` | State persistence |
|---|---|---|---|
| `local` | In-process `exec()`, soft builtins filter | Direct TCP socket to handler (`socket_send` length-prefix JSON) | `self.locals` dict accumulates; `_restore_scaffold` repairs reserved names |
| `ipython` | In-process or `ipykernel` subprocess with `cell_timeout` | Same socket | Same, with optional kernel isolation |
| `docker` | Container (`python:3.11-slim` default) | Host-side proxy bridges to handler | Container namespace |
| `modal`/`prime`/`daytona`/`e2b` | Cloud sandbox, encrypted tunnel | HTTP broker + host poller (see above) | `dill` to `/tmp/rlm_state.dill` |

Host-side is explicitly non-isolated: README warns *"The default RLM client uses a REPL environment that runs on the host process through Python `exec` calls."* README also notes for the `LocalREPL` that *"Using this REPL is generally safe, but should not be used for production settings."**

## State inventory

| Category of state | Crash / restart | Fresh `completion()` (non-persistent) | `persistent=True` across `completion()`s | `isolation` change |
|---|---|---|---:|---|
| **REPL `context` / `context_N`** | Lost — `LocalREPL.locals` is in-process dict, no journal | Reset: new `LocalREPL` with new `context_payload` | Survives: `add_context` appends `context_N`, `get_context_count()` tracks; `history_N` similarly | Lost: new environment |
| **`locals` user variables** | Lost | Reset | Survives within the persistent env's namespace | Lost |
| **Reserved names (`llm_query`, `rlm_query`, `answer`, `context`, `history`, `SHOW_VARS`)** | N/A | Restored each `exec()` via `_restore_scaffold()` — a write like `llm_query="oops"` is repaired before next block | Same | Same |
| **Message history / compaction** | Lost (in-memory `message_history` list) | New `build_rlm_system_prompt` each call | Survives: `add_history(message_history)` persists the trajectory; `history` variable exposed when `compaction` | Lost unless persisted |
| **LMHandler (TCP server, port, clients)** | Torn down: `lm_handler.stop()` in `finally` of `_spawn_completion_context` | Fresh handler per `completion()`, OS auto-port | Fresh handler per call; persistent env only updates `lm_handler_address` | New handler |
| **Child RLM handler+REPL** | Child torn down when leaf `_subcall` returns; parent continues | New per `rlm_query` | New per `rlm_query` within that `completion()` | New |
| **Logger trajectory** | `get_trajectory()` returns `run_metadata+iterations` for that `completion()` only; `clear_iterations()` on next call | New per `completion()` | New per `completion()` but parent can aggregate `rlm_calls` nested in `REPLResult` | New |
| **Budget / timeout / token counters** | `_cumulative_cost`, `_completion_start_time` not persisted across process | Reset | Reset per `completion()` (child gets `remaining_*`, not total) | Reset |

## Blast radius of an irreversible action

The irreversible action is **executing model-generated code via `exec()` in the host process** (`local` default). A malicious or buggy block can `open()`, `import os; os.system()`, or overwrite process state — `open` and `__import__` remain in `_SAFE_BUILTINS`. There is no undo log, no snapshot/rewind, no capability lease to revoke. The blast radius is the process. Mitigation is choosing an isolated environment (`docker`/`modal`/`e2b`/`prime`/`daytona`) where the brokered sandbox is the one that executes. The loop itself has no invariant that gates this; it trusts the environment choice.


## Verification strategy

Placed on the four-rung ladder:

| Rung | Mechanism | What it gates vs what it only reports |
|---|---|---|
| **Deterministic simulation (unit / integration)** | `pytest` suites under `tests/` — `uv run pytest` is the `test.yml` gate. Fixtures include `mock_lm.py`, `test_lm_handler.py`, `test_rlm_query.py`, `test_subcall.py`, `test_multi_turn_integration.py`, `test_depth_metadata.py`, `test_e2e_depth.py`. Isolated-env tests mock external services (`AGENTS.md`: *"For isolated environments, mock external services"*). | **Gates** merge via `make check` (`ruff check --fix`, `ruff format`, `pre-commit`) and `test.yml`. What is tested is harness plumbing (parsing ````repl```` blocks, handler routing, depth propagation, `answer["ready"]` capture), not world-truth. |
| **Deterministic simulation (compaction / persistence)** | `LocalREPL` compaction threshold and `persistent=True` `context_N`/`history_N` paths have dedicated tests; `_restore_scaffold()` repair and `RESERVED_TOOL_NAMES` validation are exercised. | **Gates** — prevents namespace-corruption and compaction-threshold regressions. |
| **Observability-driven feedback** | `RLMLogger` (JSONL optional `log_dir`) + `VerbosePrinter` (`verbose=True`, `rich`). Trajectory is available on `RLMChatCompletion.metadata` and browsable via `visualizer/` (`npm run dev` on `localhost:3001`). No automatic policy consumes it. | **Reports only.** Logged iterations and the visualizer are inspected by humans after a run; nothing in the harness blocks on log content. |
| **Formal specification** | None disclosed. | — |

**What it does not gate:** the model's factual claims about the world, and whether a decomposition strategy is sound. The harness will run any sequence of `llm_query`/`rlm_query` slices the model writes, collect whatever strings return, and return the `answer["content"]` the model sets `ready` on. `ErrorThresholdExceededError` / `TimeoutExceededError` / `BudgetExceededError` abort the loop and surface `partial_answer`, but they gate on resource signals, not on answer correctness. A harness that instruments every turn and gates only on plumbing is accurately described as reports heavily but gates only the machine


## Which axis

**Neither — and the design appears aware of it.**

- **Axis A (structural soundness: can the system enter a broken state? does the harness prevent or only recover?)** — Neither prevention nor recovery is a first-class property. RLM can enter broken states that are not caught: the default `local` REPL runs arbitrary `exec()` in the host interpreter (soft builtins filter only), `open` and `__import__` remain, and there is no invariant, journal, or snapshot/rewind to recover a corrupted process. `LMHandler` is fail-open on socket errors (`BrokenPipeError`/`ConnectionResetError` silently ignored; handler's `except Exception` returns an error payload but does not crash the loop). Depth/budget/timeout limits are *resource* limits, not structural invariants — and child budgets are `remaining = max - elapsed`, so a child cannot overdraw the parent but can still run arbitrary code up to that remainder. The harness trusts the environment choice to bound structure.

- **Axis B (factual truth: is the claim about the world correct?)** — Also neither. Nothing in the loop verifies that a sub-LM's summary, classification, or answer is true; the parent aggregates strings (`answers = llm_query_batched(prompts)` → `summary = llm_query(...)`) without a truth gate. The `answer` dict is whatever the model sets before flipping `ready`. The training harness (`training/`, `verifiers`/`prime-rl` `Environment`) exposes `rlm.RLM` as a `verifiers` env and plugs into a rollout scorer, but that scorer evaluates task reward after the fact — it is not a pre-execution proof that the claim is true.

The honest finding is trusts the model on both axes, with deliberately chosen escapes: use an isolated environment for Axis A, and use training-time reward or an external verifier for Axis B. The harness itself provides the loop and the decomposition API, not the gates.


## Economics

RLM's cost model is per-call, per-model token+time, with no disclosed pricing of its own. Cost is incurred on two surfaces:

**What gets re-sent each turn:** the full `message_history` `[system, metadata, user_0, assistant_0, repl_0, ...]` is serialized into the root `client.completion()` each iteration, so context grows linearly with turns and with REPL output that was not compacted. REPL stdout over ~20K chars is truncated per `format_iteration` (`max_character_length=20000`), but the model's own `assistant` content is not — long assistant replies accumulate.

**Cache / reuse:** no provider KV-cache protocol is disclosed. The harness's own "reuse" is `subcall` remaining-budget propagation (`remaining_timeout = max_timeout - elapsed`, `remaining_budget = max_budget - spent`) and `llm_query_batched` concurrency (`asyncio.gather` + `batch_max_concurrent` semaphore, `RLM.max_concurrent_subcalls` for `rlm_query_batched` thread pool). The orchestrator guidance codifies the budgeting explicitly: `(1) Per-prompt capacity: a single sub-call answers well only when its input stays modestly sized — a useful rough ceiling is ~100K characters per prompt` and `(2) Per-batch fan-out: `llm_query_batched` concurrency is bounded too — a useful rough ceiling is ~20 prompts per batch.` Tiny-prompt mega-batches (hundreds or thousands of single-item prompts) are the anti-pattern; fat-prompt small batches are correct."*

**Explicit price controls:** `max_budget` (USD, requires cost-tracking backend like OpenRouter), `max_tokens`, `max_timeout`, `max_iterations=30`, `max_errors`, `max_concurrent_subcalls=4`, and per-batch concurrency on the handler. `BudgetExceededError`/`TokenLimitExceededError`/`TimeoutExceededError`/`ErrorThresholdExceededError` each carry `partial_answer` (last non-empty `iteration.response`) so a capped run still returns something.

**What has no cost model in the material read:** compaction's summarization call is a plain LM completion (priced like any other), and isolated envs add cloud sandbox time on top; neither is priced separately in the docs. No caching, prefix-reuse, or shadow-price layer is documented — RLM treats inference as priced externally.


## Tradeoffs

**Buys:**

- *Near-infinite context as a program.* The long payload never enters the root prompt as raw text; model code slices `context` and fans out via `llm_query_batched`/`rlm_query_batched`. One `rlm.completion` can cover a context far beyond a single window without a fixed chunk graph.
- *Decomposition without a fixed controller.* The model chooses the chunking strategy, branching, and aggregation in code, so a new strategy is a new program, not a new harness version.
- *Recursive depth as a primitive.* `rlm_query` gives a subtask its own REPL+iteration loop, so depth buys iterative sub-reasoning, not just one-shot extraction.
- *Provider and environment pluggability.* New backends inherit `BaseLM` (`completion`/`acompletion`/`get_usage_summary`); new envs inherit `NonIsolatedEnv`/`IsolatedEnv` (`setup`/`load_context`/`execute_code`).

**Pays:**

- *Host-process execution by default.* `local` is `exec()` in-process with open `__import__`/`open`; isolation is opt-in and requires Docker/cloud setup plus a tunneled broker.
- *No gates on the model.* Correctness of decomposition, slice boundaries, and the final `answer["content"]` are whatever the model sets `ready` on; the loop gates only on resource signals.
- *Message-history growth.* Each turn appends assistant+REPL-output to `message_history`; without `compaction=True` a long run can itself pressure the root context.
- *Per-prompt and per-batch ceilings.* ~100K chars per sub-call and ~20 prompts per batch are documented ceilings; a workload exceeding `20 × 100K` chars must be staged — coarse filter pass then targeted extract — or it is brute-force work with two independent budgets.
- *Depth×iteration cost.* `max_iterations` applies per RLM; a depth-2 tree can pay `parent_iterations × child_iterations` LM calls even with remaining-budget caps.


## What to steal

1. **Context as a REPL variable, not a prompt argument.** Put the long payload in `context` inside the execution environment so the model writes a program that slices it, rather than pasting it into its own window.
2. **Two sub-call primitives with different contracts.** `llm_query` (one-shot, cheap, no REPL) vs `rlm_query` (own REPL+loop, fallback to `llm_query` at `max_depth`). Let the model choose iterative vs one-shot per subtask.
3. **Scaffold restoration per `exec()`.** After each code block, repair `RESERVED_TOOL_NAMES` (`llm_query`, `rlm_query`, `context`, `answer`, etc.) so a stray `llm_query = "oops"` cannot corrupt the next turn — simple, high-leverage invariant.
4. **Per-prompt failure isolation in batches.** `return_exceptions=True` + per-slot `"Error: llm() call failed - <msg>"` keeps one failed sub-call from aborting the batch and preserves index alignment.
5. **Remaining-budget propagation to children.** Pass `remaining_timeout/budget/tokens` to each child RLM, not the parent's totals, so depth cannot overdraw the root budget.
6. **The `answer` dict as termination.** A plain dict with `ready` flag that `exec()` can flip and the loop detects via `REPLResult.final_answer` — no special tool, no parser, just a variable and a flag.
7. **Orchestrator prompting that budgets the model.** Naming explicit per-prompt (~100K chars) and per-batch (~20 prompts) ceilings in the system prompt makes an otherwise invisible cost model legible to the policy that spends it.


## What not to

- **The default `local` REPL for anything adversarial or production.** It is `exec()` in the host interpreter with `open` and `__import__` available and only four names stripped from `__builtins__`. Use `docker`/`modal`/`e2b`/`prime`/`daytona` or an IPython subprocess when the prompt or the data is untrusted.
- **Treating `llm_query_batched` as free fan-out.** It parallelizes but does not relax either axis of budget — per-prompt capacity and per-batch concurrency are independent ceilings. A mega-batch of tiny prompts is documented as the anti-pattern; it also multiplies cost with little work per call.
- **Porting compaction as a correctness fix.** `compaction=True` keeps the *root* history within context, not the REPL `context` itself; it is available only on `local`/`docker` and priced as an extra LM call. Treat it as a long-run guard, not as a context substitute.
- **Trusting the model's decomposition.** The harness will run any `rlm_query` graph the model writes, including one that slices `context` incorrectly or sets `answer["ready"]=True` on a weakly supported claim. Add an external verifier or training reward (`verifiers`/`prime-rl`) if Axis B matters.
- **Assuming isolation is free.** Brokered envs add a Flask broker + tunnel + host poller (100ms), plus sandbox billed time. Budget for both the token cost and the wall-clock cost when comparing to a single large-window call.


## Embodiment

No hands-on run against the pinned commit. `visualizer/` exists as a trajectory viewer for JSONL from `RLMLogger(log_dir=...)`, and `training/` exposes `rlm.RLM` as a `verifiers` Environment for `prime-rl`, but no canonical task was executed and no provider key was used for this spec. Per FORMAT.md §4.3, `embodiment: none` is stated honestly with this text as the section body.


## Limits of this spec

What this spec does not claim to have checked:

- **No hands-on run.** Everything was read from raw files pinned at `caf0bffa1acec17c062559433b4cd4ed92eee3d6`. No `RLM.completion()` was executed, no LM key was used, no sandbox was launched, no visualizer JSONL was produced. Loop timings, batch concurrency, and remaining-budget propagation are as documented in `rlm/core/rlm.py` and `rlm/core/lm_handler.py`, not as observed.
- **Read vs scanned.** Fully read: `README.md`, `docs/architecture.md`, `AGENTS.md`, `pyproject.toml`, `LICENSE`, `rlm/core/rlm.py` (all 914 lines), `rlm/core/types.py`, `rlm/core/lm_handler.py` (and `comms_utils.py` framing), `rlm/environments/base_env.py` + `local_repl.py` (sandbox and scaffold sections), `rlm/utils/prompts.py` (`RLM_SYSTEM_PROMPT` + `ORCHESTRATOR_ADDENDUM` in full), `rlm/utils/parsing.py`, `rlm/logger/rlm_logger.py`, `docs/api/rlm.md` (Rlm class reference). The remaining ~210-tree was scanned by name/path only: `rlm/clients/` (`anthropic.py`, `openai.py`, `gemini.py`, `portkey.py` — only role-shifted reading of handler routing), `rlm/environments/` (`daytona_repl.py`, `e2b_repl.py`, `modal_repl.py`, `prime_repl.py`, `docker_repl.py`, `ipython_repl.py` — architecture doc's HTTP broker description vs full provider files), `examples/` (14 files), `visualizer/` + `docs/src/` (Next.js assets), `training/` (`verifiers`/`prime-rl` integration), and `tests/` (only filenames/mocks skimmed). Claims about those areas are limited to what the fully-read files assert about them.
- **Paper not primary for the harness claim.** `https://arxiv.org/abs/2512.24601` and the blogpost are linked from the README but were not treated as primary sources for harness mechanics — harness claims anchor to code and repo docs at the pin, not to the paper's results.
- **Economics design vs measurement.** The ~100K-chars / ~20-prompts ceilings, `max_concurrent_subcalls`, and budget/timeout limits are as written in the system prompt and handler; no provider was billed to confirm the ceilings are sufficient in practice.
- **Security boundary is as-advertised, not verified.** The soft-sandbox characterization follows directly from `_SAFE_BUILTINS` and the `exec()` path in the same file; no adversarial prompt was tried.


## Sources

| Source | Pinned at | Used for |
|---|---|---|
| `README.md` | caf0bff | Philosophy (rlm.completion replacement quote, CodeAct bet, against JSON tool-calling), overview, REPL env taxonomy, training `verifiers`/`prime-rl` pointer, version/beta |
| `docs/architecture.md` | caf0bff | Loop (three cooperating pieces, lifecycle `1→4`, wire protocol framing, why a TCP server, LocalREPL namespace layout, `llm_query` vs `rlm_query` flow, depth recursion diagram, per-completion handler, resource-limits propagation) |
| `AGENTS.md` | caf0bff | Verification (fail-fast philosophy, ruff/pytest/ty discipline, `mock external services` for isolated envs, provider/client patterns), sandbox guidance |
| `pyproject.toml` | caf0bff | Language (Python >=3.11), license (MIT), version 0.1.3 `Development Status :: 4 - Beta`, dependencies |
| `LICENSE` | caf0bff | License (MIT, Copyright 2025 Alex Zhang) |
| `rlm/core/rlm.py` (914 lines) | caf0bff | Loop (iteration `for i in range(max_iterations)`, `_spawn_completion_context`, `_completion_turn`, `find_code_blocks`, `format_iteration`, `answer["ready"]` gate, `max_*` limits with `partial_answer`, `_subcall` depth+remaining budget, compaction gate), `other_backends` validation, sampling args |
| `rlm/core/types.py` | caf0bff | Primitives (`RLMChatCompletion`, `REPLResult`, `RLMIteration`, `RLMMetadata`, `QueryMetadata`, `UsageSummary`/`ModelUsageSummary`, `ClientBackend`/`EnvironmentType`) |
| `rlm/core/lm_handler.py` | caf0bff | LMHandler (`ThreadingTCPServer`, daemon, `get_client(model,depth)` routing, `other_backend_client`, `register_client`, `_handle_single`/`_handle_batched` with `asyncio.gather(return_exceptions=True)`), socket error tolerance |
| `rlm/core/comms_utils.py` (via handler/architecture) | caf0bff | Wire protocol (4-byte BE length-prefix + JSON, `socket_send`/`socket_recv`, `LMRequest`/`LMResponse`) |
| `rlm/environments/base_env.py` | caf0bff | `RESERVED_TOOL_NAMES` (8 names), `ToolInfo`/`parse_custom_tools`/`format_tools_for_prompt`, custom-tools contract |
| `rlm/environments/local_repl.py` | caf0bff | Boundaries (in-process `exec()`, `_SAFE_BUILTINS` soft sandbox, `_AnswerDict` `ready` callback, `_restore_scaffold`, `persistent`/`compaction` only on `local`/`docker`, `SHOW_VARS`, per-prompt `Error:` framing) |
| `rlm/utils/prompts.py` | caf0bff | Philosophy & Loop (`RLM_SYSTEM_PROMPT` orchestrator addendum verbatim, `build_rlm_system_prompt`, `build_user_prompt` literal `"Turn {iter_1}/{max_iter}:"`, safeguard text, per-prompt ~100K / per-batch ~20 guidance, `context`/`history` presentation) |
| `rlm/utils/parsing.py` | caf0bff | `find_code_blocks` regex ```` ```repl```` and `format_iteration` 20K truncation / two-message shape |
| `rlm/logger/rlm_logger.py` | caf0bff | Logger (`RLMLogger` in-memory + optional JSONL, `get_trajectory`, `visualizer` JSONL shape) |
| `docs/api/rlm.md` | caf0bff | Public constructor signature (environment/backend literals) — confirms taxonomy, not dynamics |
| `https://api.github.com/repos/alexzhang13/rlm/git/trees/caf0bffa1acec17c062559433b4cd4ed92eee3d6?recursive=1` | caf0bff | Tree enumeration (222 entries); used to find deep docs and verify repo size beyond README |

All sources fetched raw at the pinned commit (`https://raw.githubusercontent.com/alexzhang13/rlm/<sha>/<path>`) except the tree API. The remaining ~210 tree entries were scanned by name only — see Limits. The `rlm` directory was not mistaken for a harness-vs-thing name trap beyond noting the expected match; no file named for the library's subject was mis-cited.
