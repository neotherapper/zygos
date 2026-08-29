# exo spec — adversarial fidelity review findings

Review of the `exo` `HarnessSpec` entity (`/tmp/exo.entity.json`, `en-01a04778-ea79-7190-8a8e-a2ca0cd8823d`),
re-checked adversarially against independently re-fetched primary sources pinned to commit
`5bc77ce7c7a2921794083d58c926cf721c14bf8a`.

All eight cited files plus the recursive tree were re-fetched fresh from
`raw.githubusercontent.com` / `api.github.com` at the pinned SHA during this review
(200s, byte counts recorded: README 12246, RSI 3544, SELF-CONTROL 22856, spec.md 9408,
EXO-BASICS 4166, exoharness-and-executor 2500, time-travel 1655, canonical-agent 3321;
tree 109333).

## 1. VERDICT

**NEEDS REVISION**

One load-bearing finding (a quote misattributed across two sources, on which an evaluative
claim rests) plus two minor consistency/count errors. The bulk of the spec — Philosophy,
Loop, Boundaries, Verification, Tradeoffs, Economics, Primitives, and the central
"fixed point is a configuration default" finding — verified clean.

## 2. Quote check summary

**N = 22 direct quotes checked. M = 21 verified verbatim (or near-verbatim, not reversed
by truncation). 1 failed.**

Failed quote:

- **WhichAxis** — attributing *"incrementally and (mostly) safely"* to `docs/RSI.md`.
  `docs/RSI.md` line 50 actually reads *"incrementally and **somewhat** safely"* — no
  parenthesis, and the word is "somewhat", not "mostly". The `(mostly)` parenthetical is
  from `README.md` line 31 (*"incrementally and (mostly) safely.*"). The spec compounds the
  error by adding the gloss *"— the parenthesis is the project's own"*, which presents a
  self-aware hedge (a parenthetical qualification) that **RSI.md does not contain**.

Verbatim-confirmed (representative, not exhaustive): the README "systems approach…full
visibility into both its code and runtime logs"; "hand-engineered harness is the next thing
to fall"; "recursion, unlike autocatalysis, requires the system to carry its own state
forward"; "breaks itself, rewinds, and tries again"; "manages the non-semantic substrate";
"ephemeral and swappable"; "If the exoharness _could_ call the LLM for you, then
necessarily, all of this logic must live within it"; "If the thing that stores your history
is the same thing that decides your prompts…"; "no (that is the point)"; "undo button that
it *cannot* break"; "keeps canonical history out of reach"; "the only thing it can't muck
with"; "It is the only part of Exo which cannot be modified by the agent"; "maximum
flexibility to evolve itself, while providing minimal scaffolding to do it safely"; "a
canary path…"; "as practice and primitives rather than as a single tool"; "not hidden
conventions or ad-hoc file edits to host state"; "a mutation path that bypasses the tools
also bypasses the record"; "an audit record of an unrecoverable action is not a substitute
for being able to undo it"; "for a small set of short facts, always injecting the whole
store is simpler and easier to audit"; "the entire state of the agent is defined as the
version of the event log"; "manage a lineage of clones"; "Nothing implements this today";
"still in the early stages of development".

## 3. Fact check summary

Non-quoted factual claims re-checked (state-inventory table, primitives, verification
ladder, economics, the fixed-point finding). Notably clean:

- **State-inventory table** (`SELF-CONTROL.md` §2): the spec's reads are exact — exactly one
  row fails sandbox rewind (sandbox filesystem → "no (that is the point)"), exactly one
  fails service restart (worker connections → "no (reconnect after drain)"), all others
  survive both. ✓
- **The "fixed point is a configuration default, not a structural invariant" finding**:
  correctly holds four surfaces (time-travel.md, exoharness-and-executor.md, README,
  RSI.md body) against RSI.md's `[^2]` footnote ("Whether or not the agent can modify the
  exo-harness is actually a policy consideration…disallowed on the default configuration").
  The framing "three of the four documentation surfaces read as though it described a
  structure" is accurate. ✓
- **Verification table**: observability escalation order ("health fields first, then event
  history, then guardian logs, then restarts") matches `SELF-CONTROL.md` §3 verbatim;
  canary path named as a gap; autonomous self-maintenance listed under README "Ongoing
  Work" (= not built). ✓
- **Tool registry** re-registered per round; **adapter** explicit-send rule; **scheduler**
  missed-fire policy (drop / one catch-up / all); **Rust match arm without a TS definition
  is unreachable** — all confirmed against `EXO-BASICS.md` / `SELF-CONTROL.md` /
  `canonical-agent.md`. ✓
- **Economics** memory-store claim ("one JSON artifact…always injecting the whole store")
  confirmed. The "no cost model stated" absence is accurate on the material read. ✓

## 4. Limits check summary

The Limits section's "fetched but not read" file list was checked against the tree at the
pinned SHA:

- `exoharness/docs/sandbox-snapshots.md` → exists ✓
- `exoharness/docs/tools.md` → exists ✓
- `exoharness/docs/http.md` → exists ✓
- `exo/SELF.md` → exists ✓
- `exo/prompts/me.md` → exists ✓
- design notes under `exoharness/docs/design/` → 6 files exist (architecture, cost-tracking,
  local-sandbox, server-plan, skills, tool-support) ✓
- **"the six adapter READMEs" → WRONG COUNT.** There are **7** adapter READMEs:
  `agent-cli`, `discord`, `exochat`, `irc`, `signal`, `slack`, `whatsapp`. `EXO-BASICS.md`
  also lists 7 supported adapters.
- "three named areas of active work" → README "Ongoing Work" has exactly 3 bullet areas. ✓
- RSI link-defect note (`exo/docs/RSI.md` link in README 404s; file is at `docs/RSI.md`)
  → confirmed: tree has `docs/RSI.md` only, README line 50 points at `exo/docs/RSI.md`. ✓

## 5. Identity check summary

- **License — MIT**: README line badge + "License / MIT" section (lines 259–261). ✓
- **Language — Rust, TypeScript**: README has both Rust and TypeScript badges; tree has
  `Cargo.toml` + `crates/*/Cargo.toml` and `package.json`/`tsconfig.json`. ✓
- **Url / Commit / ArtifactUrl**: match the pinned repo and SHA `5bc77ce…`. ✓
- **ProjectStatus — "early development"**: README "Exo is still in the early stages of
  development, with many areas of active work." ✓ (verbatim basis confirmed).

## 6. Full finding list

- `WhichAxis | "incrementally and (mostly) safely" attributed to docs/RSI.md, with "(the parenthesis is the project's own)" | RSI.md says "incrementally and somewhat safely" (no parenthesis); "(mostly)" appears only in README.md line 31 | LOAD-BEARING: the "(mostly)" hedge is cited as evidence of the project's self-awareness about safety limits, but RSI.md hedges with "somewhat", not "mostly", and has no parenthetical — the quote splices two sources and the gloss praises text that doesn't exist where attributed`
- `Limits | "the six adapter READMEs" | actually 7 adapter READMEs (agent-cli, discord, exochat, irc, signal, slack, whatsapp); EXO-BASICS lists 7 supported adapters | count error off-by-one — a Limits-section accuracy claim, the exact class of detail §4.3 says to spot-check`
- `Primitives (list field) vs PrimitivesSection (table) | list field has 11 entries including "scheduler"; table has 10 rows with no scheduler row | scheduler IS a documented primitive (EXO-BASICS §Scheduler, canonical-agent §Scheduler) | internal inconsistency: the machine-readable Primitives list and the human-facing table disagree; scheduler has no row despite being a list member and a sourced concept`

## Summary

One genuinely load-bearing error (the WhichAxis quote splice/misattribution), one count
error in Limits, and one list-vs-table inconsistency. The central analytical finding of the
spec — "the fixed point is a configuration default, not a structural invariant" — survived
adversarial re-verification and is correctly sourced to `docs/RSI.md` footnote `[^2]`.

## RE-VERIFICATION after fixes (2026-08-28)

All three defects were fixed in the source `/docs/research/harnesses/exo.md` and re-imported
into the entity (`en-01a04778-ea79-7190-8a8e-a2ca0cd8823d`, now `UnderReview`). Each fix was
independently re-verified against the pinned sources:

1. **WhichAxis quote splice** — now quotes RSI.md line 50 literally: *"incrementally and
   somewhat safely"* (verified: `docs/RSI.md` line 50 contains "incrementally and somewhat
   safely", no parenthesis; "mostly" and the parenthesis come only from README.md line 31).
   The false gloss "the parenthesis is the project's own" is removed. **FIXED — PASS.**
2. **Limits "six adapter READMEs"** — now "seven adapter READMEs". Verified against the tree
   at `5bc77ce`: 7 adapter READMEs exist at `exo/adapters/{agent-cli,discord,exochat,irc,
   signal,slack,whatsapp}/README.md`. **FIXED — PASS.**
3. **Primitives list-vs-table** — a Scheduler row was added to the `## Primitives` table,
   sourced from `exo/docs/EXO-BASICS.md` §Scheduler (tool names `schedule_sandbox_task` /
   `list_scheduled_tasks` / `cancel_scheduled_task` / `delete_scheduled_task`, `@at <rfc3339>`
   one-shots, missed-fire policy). List now has a matching table row. **FIXED — PASS.**

Overall re-verification verdict: **PASS** — all three findings resolved against primary
sources. A corrected Limits note documenting these fixes was added to the spec per
`docs/research/SKILL.md` §4 step 4.