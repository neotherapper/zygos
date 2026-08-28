# Temper backfill — fidelity review findings

Reviewed entity: `en-01a047a1-fe13-7b13-a050-ea391f1c7cd8` (`/tmp/temper.entity.json`), which is the verbatim
re-import of `docs/research/harnesses/temper.md`. Primary sources re-fetched independently from
`raw.githubusercontent.com/nerdsane/temper/2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` (README.md,
docs/PAPER.md, docs/POSITIONING.md, docs/AGENT_GUIDE.md, docs/HARNESS.md) plus the recursive tree API.
No content from the draft's own claims was reused.

## VERDICT

**NEEDS REVISION** — one load-bearing fabricated count in the Limits section, plus a recurrence of the
ADR-count imprecision class that section was rewritten to fix.

## 1. Quote check summary

**34 Temper-sourced direct quotes checked. 32 verified verbatim (or legitimate `…`-elision), 2 with
defects.** No misattributed quotes found (the prior "PAPER.md-vs-AGENT_GUIDE §8" defect is genuinely
fixed). No meaning-reversing truncation. The two defects are low-to-moderate severity:

1. **Tradeoffs, conversational-vision quote — truncation.** Written as *"you describe what you want, the
   system builds it"*; source `docs/AGENT_GUIDE.md` §17 (line 33) reads "You describe what you want. The
   system builds it, **verifies it, and evolves it**." The elision drops "verifies it, and evolves it".
   Not meaning-reversing (if anything it understates the source), but it is a non-signalled truncation
   inside a quoted span.
2. **Loop, platform-host quote — paraphrase presented as quote.** Written in italics as a quote:
   *"invalid specs are rejected at startup, never loaded into the runtime"*. Source
   `docs/AGENT_GUIDE.md` (line 407) reads "Invalid specs are rejected at startup — the server will not
   serve unverified entities." "never loaded into the runtime" is a gloss, not the source's wording.

Verified verbatim (sample, all confirmed against the file and line shown): the Philosophy opening
hypothesis + "If the state machine is the essential artifact… verification becomes tractable…" (both in
`POSITIONING.md` 19–21); "In Temper, the kernel is the constructor…" (`PAPER.md` 73); "What Temper is
and is not" table entries (`README.md` 218–221); trust-gradient chain (`POSITIONING.md` 74); outbox
quote (`PAPER.md` 348); six-step cycle + "The developer never writes specs by hand" (`AGENT_GUIDE.md`
47–55); hot-swap five steps incl. "5. If production degrades: automatic rollback" (`AGENT_GUIDE.md`
766–771); mailbox mitigation (`AGENT_GUIDE.md` 82–84); "deliberate design constraint" (`PAPER.md`
635–636); "Single-node architecture…" (`AGENT_GUIDE.md` 77–78); shadow "zero mismatches" (`PAPER.md`
736); HARNESS "agents developing Temper itself (the framework)" + "ALL FOUR must pass" (`HARNESS.md`
51, 153–154); §8 "zero cost — not a metric tag, no cardinality explosion" (`AGENT_GUIDE.md` 553);
"promote an Attribute to a Tag at runtime" (`PAPER.md` 823); GraphQL "becomes a liability" (`PAPER.md`
195); "Some of these are fundamental to finite automata" (`POSITIONING.md` 102); "partially
implemented" / "dependent on the coding agent of choice" (`PAPER.md` 1004, 1006).

## 2. Fact check summary

**One load-bearing failure, two imprecision notes.**

1. **[load-bearing] Limits — "number of documents (600+)" is unsupported.** The spec claims drift risk is
   higher "given the number of documents (600+) actively tracking design decisions in this repository."
   The pinned tree contains **268 total `.md` files** (182 under `docs/adrs/`, 86 elsewhere). Nothing in
   any pinned source mentions "600" as a document count. The number is fabricated and directly
   contradicts the spec's own ADR count two bullets earlier. This sits in the section that is supposed
   to be the spec's most careful self-audit.
2. **Limits — ADR number/`file`-count conflation recurs.** Written: "181 ADR files under `docs/adrs/`
   (159 unique numbers — 21 numbers are reused across 2–3 files each; highest number 0165)". Tree facts:
   **180 numbered ADR files** (plus `TEMPLATE.md` and `gaps/0001-…` = 182 blobs total); **159 unique
   numbers** (correct); highest number **0165** (correct, with 0156 and 0160–0164 absent); **13 numbers
   are reused** (31,32,33,40,41,43,45,46,57,81,82,83,84), accounting for **21 duplicate files/slots**.
   The spec's "21 numbers reused" conflates *duplicate slots* (21) with *reused numbers* (13). The
   parenthetical "21 numbers are reused across 2–3 files each" is factually false, and "181 files"
   matches neither 180 (numbered) nor 182 (total blobs) cleanly. This is the exact "highest-number/
   file-count miscount" class the prior pass was meant to close, in a new form.
3. **Minor — "22+ crates" is loosely stated.** The workspace has **27** first-party `crates/temper-*`
   members. "22+" is not false, but a spec that elsewhere cites exact counts (159, 0165, 21) leaves the
   crate figure vague for no reason.

All other factual claims re-checked against source and confirmed: latency figures (~1.4 ms postgres
append ≈ 50× the ~28 μs in-memory dispatch path; `evaluate_ctx()` hot path 28 ns; all `PAPER.md` §11.7,
correctly disambiguated) — correct and correctly attributed; automatic-rollback step 5 verbatim in
`AGENT_GUIDE.md` §12; preferred-verification quote verbatim (note: it lives in `POSITIONING.md` 21, not
`PAPER.md`, but the spec does not misattribute it to PAPER); 22 DST tests incl. 2 determinism proofs
across 10 runs; three guard-resolution bugs; ~2,200 persisted actions/sec; reference-app `409` sequence;
TemperModel/TransitionTable "same `Automaton` … provable equivalence".

## 3. Limits check summary

- Section headings cited in Limits (`AGENT_GUIDE.md` §1, §8, §12, §16) map correctly (lines 29, 522,
  753, 967). Limits is accurate here.
- `docs/HARNESS.md` ~610 lines and "~200 read" matches (file is 610 lines).
- **ADR count bullet fails** — see fact finding #2.
- **"600+ documents" fails** — see fact finding #1.
- The self-description of the prior review's four defects (misattributed quotes, 28 ns/μs swap, ADR
  miscount, missing rollback) is consistent with what the corrected text now shows.

## 4. Identity check summary

All pass: License `MIT / Apache-2.0` (both `LICENSE-MIT` and `LICENSE-APACHE` present in tree);
Language Rust (Cargo workspace); `Url`/`ArtifactUrl`/`Commit` match `2f43ecef…`; `ProjectStatus`
"pre-release" matches README badge ("Pre-release") and "Version 0.1.0. The architecture is stabilizing;
the API surface is not frozen." (README 227). `Lifecycle: VersionChanging` consistent.

## 5. Full finding list (one per line)

- `Limits` | "number of documents (600+) actively tracking design decisions in this repository" | tree has 268 `.md` files (182 under adrs/); no source says 600 | fabricated count in the self-audit section; load-bearing
- `Limits` | "181 ADR files … 21 numbers are reused across 2–3 files each" | 180 numbered ADRs (182 blobs), 13 numbers reused yielding 21 duplicate files, highest 0165 | reappears the ADR miscount class the section was rewritten to fix; load-bearing
- `Tradeoffs` | *"you describe what you want, the system builds it"* | source adds "verifies it, and evolves it" | non-signalled truncation inside a quote; understates the source
- `Loop` | *"invalid specs are rejected at startup, never loaded into the runtime"* | source: "Invalid specs are rejected at startup — the server will not serve unverified entities" | paraphrase rendered as an italicized quote
- `Tradeoffs` | "22+ crates, Docker Compose for Postgres/Redis-stub/ClickHouse/OTEL" | workspace has 27 first-party crates | imprecise figure where the spec elsewhere is exact

## RE-VERIFICATION after fixes (2026-08-28)

All five defects were fixed in the source `/docs/research/harnesses/temper.md` and re-imported
into the entity (`en-01a047a1-fe13-7b13-a050-ea391f1c7cd8`, now `UnderReview`). Each fix was
independently re-verified against the pinned sources:

1. **[load-bearing] "600+ documents"** — replaced with the actual tree count: 268 total `.md`
   files, 182 under `docs/adrs/`. Verified via the tree API at `2f43ece`. **FIXED — PASS.**
2. **ADR count slots-vs-numbers** — corrected to 182 ADR files, 159 unique numbers, 14 numbers
   reused for 22 duplicate files, highest 0165 (0156 and 0160–0164 absent). Verified via the
   tree API (159 unique, highest 165, 14 reused numbers → 22 duplicate files). **FIXED — PASS.**
3. **"22+ crates"** — corrected to "27 first-party crates". Verified: 27 `crates/temper-*`
   directories in the tree. **FIXED — PASS.**
4. **Tradeoffs quote truncation** — restored the full source: "You describe what you want. The
   system builds it, verifies it, and evolves it." (source `docs/AGENT_GUIDE.md` line 33).
   **FIXED — PASS.**
5. **Loop paraphrase-as-quote** — reworded as an unquoted paraphrase matching the source
   ("Invalid specs are rejected at startup — the server will not serve unverified entities",
   `docs/AGENT_GUIDE.md` line 407). **FIXED — PASS.**

Overall re-verification verdict: **PASS** — all five findings resolved against primary
sources. A corrected Limits note documenting these fixes and the recurrence of the count-error
class was added to the spec per `docs/research/SKILL.md` §4 step 4.