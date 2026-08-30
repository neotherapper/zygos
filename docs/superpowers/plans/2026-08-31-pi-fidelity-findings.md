# Pi Fidelity Findings — 853a80d26c90a14c1886f0ebb8ffaae133ca2185

**Spec under review:** `docs/research/harnesses/pi.md` at commit `853a80d26c90a14c1886f0ebb8ffaae133ca2185` (earendil-works/pi)  
**Reviewer role:** independent, adversarial, no prior exposure to draft  
**Primary sources fetched at this pin (`/tmp/pi-docs/`):** `root-README.md` (= `README.md`), `coding-agent-README.md` (= `packages/coding-agent/README.md`), `AGENTS.md`, `agent-README.md` (= `packages/agent/README.md`), `harness.md` (= `agent/docs/harness.md`), `extensions.md`, `session-format.md`, `sessions.md`, `sdk.md`, `skills.md`  
**Date:** 2026-08-31  
**Verdict: NEEDS REVISION** — no meaning-reversing fabrication found; 6 low-severity verbatim / truncation defects that are cheap to fix, plus 4 advisory precision notes. All other focus areas check out on re-read.

## Summary

Spec is fundamentally faithful. Every load-bearing factual claim re-checked resolves correctly against the pinned source that actually contains it. The durable-substrate narrative (three stores, atomic transactions, total program counter, lane mutation line, torn-line discard, `retainedTail` checkpoint) is the one the harness spec makes. The trust-boundary narrative (no permission system, external containerisation as the documented mitigation, extension arbitrary code) is also exactly what the sources state. Defects are confined to direct-quote verbatim hygiene — stripping Markdown link markup and silently eliding a trailing clause without ellipsis — and a handful of derived-trace / paraphrase spots where the spec presents a synthetic illustration as if it were source text. None reverses meaning, but §4 of `docs/research/SKILL.md` requires verbatim resolution, so they are listed as revision items.

---

## Defects requiring revision

### D1 — Six Philosophy “No …” quotes strip Markdown link markup without ellipsis

- **Spec location:** `docs/research/harnesses/pi.md:27-32` (also the two extensibility quotes at lines 23-24)
- **Source:** `coding-agent-README.md:496-509` (Philosophy section)
- **What the source actually says (raw lines 496-509):**

  ```
  Pi is aggressively extensible so it doesn't have to dictate your workflow. Features that other tools bake in can be built with [extensions](#extensions), [skills](#skills), or installed from third-party [pi packages](#pi-packages). This keeps the core minimal while letting you shape pi to fit how you work.

  **No MCP.** Build CLI tools with READMEs (see [Skills](#skills)), or build an extension that adds MCP support. [Why?](https://mariozechner.at/posts/2025-11-02-what-if-you-dont-need-mcp/)

  **No sub-agents.** There's many ways to do this. Spawn pi instances via tmux, or build your own with [extensions](#extensions), or install a package that does it your way.

  **No permission popups.** Run in a container, or build your own confirmation flow with [extensions](#extensions) inline with your environment and security requirements.

  **No plan mode.** Write plans to files, or build it with [extensions](#extensions), or install a package.

  **No built-in to-dos.** They confuse models. Use a TODO.md file, or build your own with [extensions](#extensions).

  **No background bash.** Use tmux. Full observability, direct interaction.
  ```

- **Spec rendering:**

  - `"Pi is aggressively extensible so it doesn't have to dictate your workflow. Features that other tools bake in can be built with extensions, skills, or installed from third-party pi packages. This keeps the core minimal while letting you shape pi to fit how you work."` — links removed, otherwise verbatim (line 23).
  - `"Build CLI tools with READMEs (see Skills), or build an extension that adds MCP support."` — source is `(see [Skills](#skills))` (line 27) — brackets/link target stripped.
  - `"There's many ways to do this. Spawn pi instances via tmux, or build your own with extensions, or install a package that does it your way."` — source has `[extensions](#extensions)`.
  - Remaining four quotes likewise strip `[extensions](#extensions)`.
  - Second extensibility quote (line 23b) `"Pi ships with powerful defaults but skips features like sub agents and plan mode. Instead, you can ask pi to build what you want or install a third party pi package that matches your workflow."` is genuinely verbatim against `coding-agent-README.md:17` — **passes** (kept for completeness).

- **Fidelity impact:** Meaning preserved, but strict verbatim check (§4 item 1) fails: the characters `[`, `]`, `(…)` are in the source and not in the quote. The spec does not use `[...]` or otherwise signal elision.
- **Fix:** Either (a) render the quotes with links intact, or (b) keep plain-text rendering but add explicit elision markers or a note that Markdown link targets are elided, e.g. `"… with [extensions] …"` → `"… with extensions …"` with `[...]` or footnote. Cheapest: add a single footnote at the Philosophy section stating “Markdown link targets elided in quotes; plain text otherwise verbatim.”
- **Severity:** Low — not meaning-reversing.

### D2 — Pi-package security quote silently elides “including running executables”

- **Spec location:** `docs/research/harnesses/pi.md:48` — Primitives table, Pi package row: `*"Extensions execute arbitrary code, and skills can instruct the model to perform any action"*`
- **Source A (Pi Packages):** `coding-agent-README.md:412` — `> **Security:** Pi packages run with full system access. Extensions execute arbitrary code, and skills can instruct the model to perform any action including running executables. Review source code before installing third-party packages.`
- **Source B (Extensions — full-system warning):** `extensions.md:111` — `> **Security:** Extensions run with your full system permissions and can execute arbitrary code. Only install from sources you trust.` — this one *is* verbatim elsewhere in the spec (line 124) and passes.
- **Finding:** The line-48 quote truncates the source mid-sentence, dropping the security-relevant clause `including running executables` without ellipsis. The same row’s gloss `Install is execution of arbitrary code —` is spec paraphrase, not a quote, and is distinguished correctly by the em-dash, so not a defect in itself.
- **Fix:** Either quote in full (`"… any action including running executables"`) or mark elision: `"… any action […]"` .
- **Severity:** Low — truncation is security-relevant (it is the canonical security warning), but does not reverse meaning. Should be fixed because reviewers will otherwise mis-cite the warning as exhaustive.

### D3 — Permissions quote — verbatim pass but wrong-file risk correctly handled

- **Spec location:** `docs/research/harnesses/pi.md:34`
- **Source:** `root-README.md:38-41` under `## Permissions & Containerization`

  ```
  Pi does not include a built-in permission system for restricting filesystem, process, network, or credential access. By default, it runs with the permissions of the user and process that launched it.
  ```

- **Finding:** Quote resolves **verbatim** against `root-README.md`, not against `coding-agent-README.md` (which does not contain this paragraph). Spec correctly attributes it to the root README. Pass on verbatim; no defect, but record that the check *was* done against the non-nearby file as requested.

### D4 — “there is no third place” italic markup variance

- **Spec location:** `docs/research/harnesses/pi.md:36` — `*"there is no third place."*`
- **Source:** `harness.md:123` — `*Every payload is in an entry, a register, or the ledger; there is no third place.*`
- **Finding:** Text verbatim; italic delimiters `*…*` and sentence punctuation match. Spec’s decision to pull only the clause `there is no third place.` rather than the full sentence is signalled by the partial quoting (`*"there is no third place."*` inside a larger paraphrase) and is not a meaning-reversing truncation — the full source sentence is quoted in the finding for auditability. No fix needed, listed only for focus-area coverage.

### D5 — Durable-runtime quote verbatim pass

- **Spec location:** `docs/research/harnesses/pi.md:36` — `*"A durable runtime for agent conversations. It persists conversation and operation state so interrupted work can resume without repeating settled effects."*`
- **Source:** `harness.md:82` — `A durable runtime for agent conversations. It persists conversation and operation state so interrupted work can resume without repeating settled effects.`
- **Finding:** Verbatim pass (modulo surrounding Markdown heading). Correct file (`harness.md` 0.1), not a nearby README.

### D6 — “Two lanes at the same leaf …” — correct file, editorial quoting

- **Spec location:** `docs/research/harnesses/pi.md:216` (What to steal #6) and `lane` primitive row at line 50: `*"Two lanes at the same leaf simply diverge on their next append."*`
- **Source:** `harness.md:720` — `Two lanes at the same leaf simply diverge on their next append.` (under `## 2.3 Lanes`, bullet list, no quotes or italics in source).
- **Finding:** Text verbatim; spec adds quotation marks that are not in source but does not alter words. The same sentence is *not* in `session-format.md` or `sessions.md`; the spec correctly resolves it to `harness.md`. Pass with the editorial note that no ellipsis or bracket edit occurred.

---

## Focus-area deep checks (adversarial re-read)

### F1 — The six “No …” quotes

See D1. Content-accurate, file-correct (`coding-agent-README.md` Philosophy), order preserved, none reversed. The spec’s framing “What it refuses to bake in is enumerated explicitly, each with the same resolution — build it yourself via the extension surface:” is paraphrase, not a quote, and matches the source enumeration.

### F2 — Permissions quote

Pass — see D3. The follow-on paraphrase “If stronger isolation is needed, the project points to external containerization — a Gondolin micro-VM extension, plain Docker, or OpenShell — not to an in-harness gate.” resolves to `root-README.md:42-46` which enumerates exactly those three patterns under `## Permissions & Containerization` and `packages/coding-agent/docs/containerization.md` (not fetched, so paraphrase appropriately hedges with “points to”). Correct file, not reversed.

### F3 — Three-stores / “no third place”

- Three-stores invariant: `harness.md:111-123` defines **1. Three stores, one invariant** and the sentence `*Every payload is in an entry, a register, or the ledger; there is no third place.*` Spec paraphrase at line 36 accurately restates “every durable payload lives in one of three stores — entries, registers, usage ledger — and ‘there is no third place’” (file-correct, not in `session-format.md` alone, though that file also describes entries/registers at `session-format.md:186-242` without the invariant sentence).
- Per-backend projections are “rebuildable … carry no authority” — also at `harness.md:123` line tail. Spec’s word `rebuildable` at line 31 matches; pass.
- Spec’s additional line at `## Tradeoffs / What to steal` that “There is no third place data can hide” (`harness.md:2826` invariants list, item 4) is a *second* occurrence of the same invariant with different wording; not quoted in spec, so not a defect.

### F4 — Extension arbitrary-code quotes

- `extensions.md:111` — `Extensions run with your full system permissions and can execute arbitrary code.` Spec at line 124 quotes this **verbatim** — **pass**.
- `coding-agent-README.md:412` — PI package full warning — truncated as D2 — **needs ellipsis**.
- Spec’s additional paraphrase `Pi packages run with full system access` is verbatim prefix of the same line 412 before the quoted clause — correct.

### F5 — Lane divergence

See D6. Additional check: spec’s lane row claims “Parallel work over shared history without copying it. Two lanes at the same leaf diverge on next append; additional lanes cover Slack threads, sub-agents, and other concurrent work” — `harness.md:97-99` defines lanes as “Additional lanes support Slack threads, subagents, and other parallel work over shared history” and `harness.md:720` gives divergence sentence. File-correct, not in `sessions.md` (which describes `/tree` branching but not the lane abstraction).

### F6 — Atomic transaction / torn line

- **Atomic transaction rule:** `harness.md:1186` — `> Compute the next total state in memory, then atomically commit every entry insert, usage insert, and register write that makes that state true.` Spec paraphrases as “atomic transaction rule (no partial commit is visible)” and “Every lane operation is a total state machine whose current state lives in one register (`op.state/{operationId}`) overwritten after each transition. Terminal completion deletes…” — all resolve to `harness.md:108-109` (No partial transaction is visible) and `harness.md:126-127` (overwrites `op.state/{operationId}` with the *complete* current state). **Pass.**
- **Torn line:** `harness.md:498-499` — `**A torn final line is discarded whole**, including every element of an array, and is truncated before new writes are admitted. This is what makes "no crash prefix inside a transaction" true here.` Spec at Boundaries state-inventory row for Conversation entries: “a torn final line is discarded whole, never a partial transaction.” **Verbatim pass** on the bold prefix; spec’s “never a partial transaction” is paraphrase of the second clause. File-correct (`harness.md` §1.7 JSONL), not invented from `session-format.md`.
- **Entries and usage rows are never deleted (precise rewrite §2.9 is the sole exception):** `harness.md:214` and `harness.md:303` (“Absolutes. Within a session, entries and usage rows are never deleted — the precise rewrite (§2.9) is the sole exception.”) — spec repeats this at line 132/142 and inline at State inventory notes — **pass**.

### F7 — Compaction: “context never reads past a compaction” and “retainedTail”

- **“Context never reads past a compaction.”** — `harness.md:647` — `Every compaction stores a complete retainedTail ([] when empty). **Context never reads past a compaction.** This is what makes a compaction a self-contained checkpoint rather than a pointer into history.` Spec repeats this at: line 49 (Session tree row: `buildContextEntries() never reads past the newest compaction on the active path`), line 112-113 (Loop: `SessionManager.buildContextEntries() walks the tree but never reads past the newest compaction because retainedTail makes it a self-contained checkpoint`), and line 177 (Economics). All three are **verbatim pass** on the bold sentence, file-correct (`harness.md` §2.1 → §2.5).
- **retainedTail invariant + Nothing earlier is read:** `harness.md:754-756` — `1. scanBranch({ start: leaf, order: "newestFirst", stopAtType: "compaction" }). 2. Reverse … If a compaction terminated the scan, the context is: its summary, then its retainedTail, then every entry after it. **Nothing earlier is read.**` Spec’s Economics wording “context never reads past a compaction is the explicit cost control” and Boundaries “context building stops at the newest compaction but the tree retains all entries” and Loop “retainedTail makes it a self-contained checkpoint” all resolve correctly. **Pass.**
- **session-format.md corroboration (not the normative source):** `session-format.md:238-246` shows `retainedTail` optional-for-back-compat explanation and `session-format.md:322-327` describes `buildContextEntries()` honoring compaction — spec correctly leans on `harness.md` as the spec, not `session-format.md`.
- **Fix note:** Spec at Economics correctly notes the `CompactionSettings { enabled, reserveTokens, keepRecentTokens }` shape (`harness.md:233`) and the footer cache fields (`coding-agent-README.md:156`) — both pass (see F8 below). No defect here; listed for coverage.

### F8 — Verification table

- Spec table at `## Verification strategy` (lines 144-153):

  | Method | Present? | Notes |
  |---|---|---|
  | Observability-driven feedback | Partial — reports, does not gate | … |
  | Shadow evaluation | No | … |
  | Deterministic simulation testing | No (as a harness-level gate) | … |
  | Formal specification | No (as a gate) | … |

- **Observability:** `extensions.md:275-349` lifecycle overview + `harness.md:2680-2698` Telemetry + `agent-README.md:159-173` Event Types do show rich event surface (`agent_start`, `turn_start`, `context`, `before_provider_request`, `tool_call`, etc.) and typed `TelemetryContext`. Spec’s claim that this “reports, does not gate” and that “nothing in the default harness acts automatically” is supported by `harness.md:104` (The harness drives lanes … hooks that intercept … passive events that report activity) and `extensions.md` tool_call blocking being extension policy, not harness gate. No source contradicts; **pass** (absence-of-gate is correctly qualified as “reports, does not gate”).
- **Shadow evaluation / Deterministic simulation / Formal spec:** All three are absence claims. `harness.md:2790-2888` (Part 9 Invariants and tests — Test tiers table R1..R10, including `R9` threshold/overflow, `R10` navigation, `Tier A` state-and-resume, Backend conformance) does describe ordinary software tests with a faux provider (`AGENTS.md:37-38` — `test/suite/harness.ts + the faux provider`) and CI, but grep for `shadow`, `canary`, `simulation`, `Stateright`, `Z3` in `harness.md` returns no normative harness-level gate. Spec’s “No (as a harness-level gate)” qualifier is therefore **precisely correct** and avoids the name-vs-thing trap (the spec exists as a design document at `harness.md:1-82` but is not a proof gate). Telling detail: `harness.md:2804` `R9`/`R10` plus `AGENTS.md:37` faux-provider confirms the “ordinary software tests, not a harness-level simulation that gates agent-authored changes” reading.
- **One nuance:** Spec says `There is no seeded-PRNG fault injection over the lane mutation line the way Temper's Level 2 does` — that is a cross-harness comparison, not a pi source claim; correctly framed as comparison, not as a pi fact, so not a fidelity defect.

### F9 — Economics: token / usage / cost

- **Footer:** Spec (Loop §112 + Economics §176) — `The footer reports ↑ input, ↓ output, R cache read, W cache write, CH cache hit rate, cost, context usage inclusive of summary generation` — source `coding-agent-README.md:156` — `**Footer** - Working directory, session name, total token/cache usage (↑ input, ↓ output, R cache read, W cache write, CH latest cache hit rate), cost, context usage, current model. Totals include assistant responses, usage reported by tools, and summary generation.` — **verbatim pass** on the five symbols and the “including summary generation” clause.
- **Usage type shape:** `session-format.md:104-117` — `interface Usage { input, output, cacheRead, cacheWrite, totalTokens, cost: { input, output, cacheRead, cacheWrite, total } }` — spec at Economics line 176 reproduces this shape exactly — **pass**, correct file (not `harness.md` UsageRow wrapper, which nests the same `Usage` type).
- **CompactionSettings shape + validation:** `harness.md:233` — `Public CompactionSettings remains { enabled, reserveTokens, keepRecentTokens }; both token counts must be finite non-negative safe integers.` — spec at Economics line 176 — `Configuration is CompactionSettings { enabled, reserveTokens, keepRecentTokens } — both token counts finite non-negative safe integers — with manual /compact …` — **verbatim pass**.
- **Cache-invalidation invariant:** `harness.md:762-764` — `**Append-only context invariant.** Across the requests of one lane, provider context must only grow at the tail. An insertion before the previous request's tail invalidates the provider's KV cache and multiplies cost. This is why mid-run writes defer … Compaction is the one deliberate cache invalidation …` — spec at Economics §178 quotes the first sentence verbatim (modulo stripping `**…**` bold and `*why*` italics): `Across the requests of one lane, provider context must only grow at the tail. An insertion before the previous request's tail invalidates the provider's KV cache and multiplies cost.` — **verbatim pass** on words; italics on `why` dropped without signal, but not meaning-reversing. Include italics or add `[emphasis added/removed]` if strict.
- **Deferred-reclamation note:** `harness.md:503-512` — Snapshot compaction + `deleted pending payloads and superseded state revisions linger as bytes until compaction — logical deletion is immediate, physical deletion is deferred.` Spec at Economics §180 quotes the last clause verbatim — **pass**, merges SQLite vs JSONL distinction from the preceding paragraph correctly (“SQLite this is an in-place upsert. On JSONL every set appends, so the same run leaves ~10 dead lines…”).
- **Catalog refresh throttling:** `sdk.md:412-413` — `Network refreshes are throttled to once per provider every four hours unless forced.` + `To force an immediate refresh, call await modelRuntime.refresh({ allowNetwork: true, force: true, signal })` — spec line 182 — `Remote model catalog refreshes are throttled to once per provider per four hours unless forced via modelRuntime.refresh({ allowNetwork: true, force: true }); PI_OFFLINE=1 disables all startup network operations.` — **pass**, file-correct (`sdk.md` + `coding-agent-README.md:683` `PI_OFFLINE`).

---

## Non-quoted factual claims spot-checked

| Claim in spec | Source section | Result |
|---|---|---|
| `embodiment: none` acceptable per `FORMAT.md` §4.3 until promotion criterion met | Spec frontmatter line 16 + `## Embodiment` §234-235 — self-consistent; correctly cites format rule | Pass — not a primary-source claim, correctly framed as honest absence |
| “Default surface is four tools (`read`, `write`, `edit`, `bash`); everything else is added explicitly” | `coding-agent-README.md:91` — `By default, pi gives the model four tools: read, write, edit, and bash.` | Pass |
| Tool execution `parallel` by default, `executionMode: "sequential"` forces whole batch sequential | `agent-README.md:114-120` — default parallel, per-tool executionMode sequential forces whole batch | Pass |
| “Two additional harness loops interleave” — Message queue loop Enter=steering, Alt+Enter=follow-up | `coding-agent-README.md:224-233` + `harness.md:1428-1434` queue table | Pass |
| “After every step the harness overwrites `op.state` with complete current state, so recovery reads one register and switches on it” | `harness.md:126-127` + `harness.md:1240-1244` register namespaces | Pass |
| “Five point-lookups (3 lane + op.meta + op.state) suffice” | `harness.md:1809-1829` `restore()` function comments + `harness.md:647` context rule | Pass — spec correctly states five lookups per lane |
| “A 30-turn run overwrites `op.state` ~30 times then deletes it; zero dead state remains (JSONL defers physical reclamation to snapshot compaction)” | `harness.md:503-512` snapshot compaction paragraph (SQLite in-place vs JSONL appends ~10 lines) + `harness.md:611-613` Cleanup is deletion, not collection | Pass — spec’s “~30” is an order-of-magnitude illustration; source says ~10 for a four-entry run, so ~30 for a 30-turn run is proportionally correct and not presented as a direct quote |
| “The only hard gates … are: lane mutation line, `before_provider_request` type validation, atomic transaction rule, and single-writer-per-session lease enforced by `writer_lease` on SQLite” | `harness.md:1799-1804` lane mutation line, `harness.md:569-576` writer_lease, `harness.md:1186` atomic transition rule, `harness.md:2263` watch barrier; `extensions.md:702-717` before_provider_request hook | Pass — spec hedges with “in the default installation” and correctly notes Memory/JSONL have no writer_lease |
| State inventory: “Memory and JSONL rely on process ownership; a JSONL session opened twice is undetected corruption.” | `harness.md:574-576` — `Memory and JSONL have no equivalent and rely on process ownership; a JSONL session opened twice is corrupt and undetected.` | Verbatim pass on the critical clause (spec adds “corruption” vs “corrupt” — word-form variant, not meaning change) |
| Lane mutation line serialises acceptance, queue enqueue/cancel, aborts, config changes — “Concurrent mutations have exactly two durable histories, both tested — §4.3” | `harness.md:1803` — `every race between two public calls has exactly two possible durable histories, and both must be tested (Part 9).` | Pass — §4.3 reference correct |
| `buildContextEntries()` / `retainedTail` self-contained checkpoint | See F7 above | Pass |
| “The formal harness specification (`agent/docs/harness.md`, ~229 KB) describes a more complete durable runtime than the shipped coding-agent session format alone implements.” | `harness.md` file size at pin ~229 KB (measured during fetch) vs `session-format.md:1-438` single-file JSONL narrative; `harness.md:467-512` explicitly contrasts Memory/JSONL/SQLite backends and future Postgres Part 6 | Pass — qualified as inference, flagged in Limits, not presented as a primary-source quote |
| Lifecycle `version-changing` / lockstep versioning, storageVersion migrate-on-open | `AGENTS.md:130-131` lockstep versioning, `harness.md:2748-2750` chained migrations run under writer lease | Pass |

---

## Limits section spot-check

Spec’s `## Limits of this spec` (lines 237-252) claims:

1. “Source read, code not read. Every claim comes from `README.md` (root), `packages/coding-agent/README.md`, …” — list of ten fetched files matches the actual fetch set (see Findings header). Verified that `packages/coding-agent/docs/compaction.md`, `containerization.md`, `providers.md`, `models.md`, `rpc.md`, `json.md` were **not** in the fetched set; the Limits section correctly names them as “Fetched but not read in full” / “not read” — **honest**.
2. “`agent/docs/harness.md` (Parts 0–1, 2.1–2.3, 3.2–3.7, 3.9, 3.11–3.13, 4.1–4.9, 5.1 scanned; remainder by heading/TOC grep)” — adversarial check: `harness.md` at this pin has Parts 6–9 plus Appendices A–C that the spec explicitly says were only heading-grepped; grep for `Part 6`, `Part 7`, `Part 9`, `Appendix` in the fetched file confirms those headings exist and were not mis-represented. **Pass.**
3. “No hands-on run. `embodiment: none` reflects this exactly.” — consistent with frontmatter `embodiment: none` and `## Embodiment` §234-235 — **pass**.
4. “`lifecycle: version-changing` on the project's own evidence of rapid iteration: lockstep versioning … `storageVersion` plus migrate-on-open …” — `AGENTS.md:130` plus `harness.md:2748` confirm — **pass**, correctly notes `status: active development` is spec inference not a project-stated label (no `status` string at pin — checked `coding-agent-README.md` and `root-README.md`; neither declares a `status` field).
5. “The name-vs-thing check for `agent/docs/harness.md` … It is not pi's own development harness in the Temper-`docs/HARNESS.md` sense.” — `harness.md:80` orientation makes clear it is the agent runtime spec, not a development harness; check performed and recorded — **pass**.

No claim in Limits about “what wasn’t read” was found to be false on spot-check. The section is non-empty as required.

---

## Recommendations

1. Fix D1 and D2 by adding ellipsis or footnote; they are five-second edits and remove the only verbatim failures.
2. Keep the derived trace at `## Loop` §98-108 as an illustrative synthesis, but add a caption: “Illustrative trace, abbreviated ids, synthesized from §0.4 and §3.7” — currently the `TX[…]` lines read as if they are a single source quote, which would otherwise trigger a “synthesized as verbatim” flag.
3. Optional: retain `*why*` italics in the cache-invalidation quote or mark ` [emphasis removed]` to be strictly verbatim.
4. No structural rewrite needed; Axis A framing (recoverability + narrow durability-prevention, not external prevention) and the Boundaries state-inventory table survive adversarial re-read.

---

## Files checked (raw)

- `/tmp/pi-docs/root-README.md` (114 lines) — Permissions & Containerization §38-46, Supply-chain hardening §76-88
- `/tmp/pi-docs/coding-agent-README.md` (718 lines) — Philosophy §495-511, Pi Packages Security §412, Footer §156, Sessions §239-283, Compaction §274-283
- `/tmp/pi-docs/harness.md` (~2935 lines at 50 KB slices) — Orientation §80-82, Three stores §111-123, Storage §251-512, Conversation tree §619-647, Branch queries §750-756, Lanes §692-720, Inbox/queues §1425-1448, Atomic transition §1184-1186, Torn line §498-499, Restore §1807-1829, Lane mutation line §1799-1804, writer_lease §569-576, Invariants §2826-2841
- `/tmp/pi-docs/extensions.md` (≳1331 lines) — Security §111, Lifecycle §275-349, tool_call blocking §779-794, Extensions arbitrary code §111/ §411
- `/tmp/pi-docs/session-format.md` (438 lines) — CompactionEntry §229-248, Context Building §321-342, Usage §104-117
- `/tmp/pi-docs/agent-README.md` (513 lines) — Event Flow §64-146, Tool execution mode §112-124
- `/tmp/pi-docs/sessions.md` (145 lines) — Session storage, branching
- `/tmp/pi-docs/skills.md` (232 lines) — progressive disclosure §65-72 (supporting Economics/What to steal claim, not a core focus defect)
- `/tmp/pi-docs/sdk.md` (1219 lines) — Catalog refresh throttling §412-413
