# Target list

| Harness | `kind` | Why it's on the list | Status | Spec |
|---|---|---|---|---|
| **exo** | agent-harness | Fully recursive self-editing agent + harness | done (v1 body, `embodiment: none`) | [`harnesses/exo.md`](harnesses/exo.md) |
| **Temper** | agent-substrate | Formal verification of agent-authored capabilities — the only proved-before-running design on the list | not-started | — |
| **RLM** | inference-paradigm | Recursive context decomposition as an alternative to tool-calling entirely | not-started | — |
| **DeepSeek Harness** | agent-harness | Plugin-composable architecture from a frontier lab; candidate third instance of "the log is the program" | not-started | — |
| **pi** | — | Named by the owner; exo's README places "Pi" alongside OpenClaw and Hermes as a personal-runtime-class harness, but does not identify a repo | blocked — needs disambiguation before research starts | — |

Temper, RLM and DeepSeek Harness are chosen to bracket the design space — proved-before-running,
recursive-self-editing (already covered by exo), everything-is-a-plugin — rather than sample it.

**Economics is load-bearing for the DeepSeek Harness spec, more than the format's default.** pavlos
carries a candidate requirement (R8, medium-confidence: compaction must preserve provider prefix
reuse) drawn from two dsh design notes read directly, not yet backed by a spec. This spec's Economics
section is that backing — it either confirms R8 or kills it. Read the compaction/caching material with
that question open, not as a general pass.

`best-of-Agent-Harnesses` is a discovery source for future targets, not a subject of its own record —
see `DESIGN.md` §3 (Non-Goals: breadth).

## Pinned commits for the next three specs

Read at these SHAs, not `main`, per rule 1. All three now confirmed to resolve
(`curl -sI` against raw.githubusercontent.com, 2026-08-16) — repo coordinates for RLM and DeepSeek
Harness came from pavlos's own target list, not the relayed message, which gave SHAs with no org/repo
for either:

| Harness | Repo | SHA | Resolved? |
|---|---|---|---|
| Temper | `nerdsane/temper` | `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` | ✅ 2026-08-16 |
| RLM | `alexzhang13/rlm` | `caf0bffa1acec17c062559433b4cd4ed92eee3d6` | ✅ 2026-08-16 |
| DeepSeek Harness | `deepseek-ai/deepseek-harness` | `47f943859bef60e4160492346772ded9b24f765a` | ✅ 2026-08-16 |

Confirming a SHA resolves confirms the *coordinate*, not the *content* — still read the file at that
pin before citing anything from it, per rule 1.

## Prep notes for Temper (leads, not findings — verify before use)

- Don't stop at the README. `docs/PAPER.md` (~78KB) and `docs/POSITIONING.md` (~14KB) exist at the
  pinned SHA and are unread as of this note. The verification cascade is likely specified there, not
  in the README's collapsed summary — for the one project on the list whose entire pitch is
  verification, a README-only Verification section would be thin.
- The README carries an explicit "What Temper is and is not" table — four rows, each naming something
  it is not and why. Good raw material for `Boundaries`; check it's still current at the pinned SHA.
- Two watch-for claims in the README, precise and self-sourced, no artifact behind either as read:
  *"Runs on every build, in well under a second on a small spec"* and *"Deployed on Railway; Katagami
  runs on it in production."* Quote and attribute as the project's own claim, or omit — do not let the
  precision read as verified.
- **Prediction to test, not assume:** the README says nothing about token/cost behavior. If Economics
  comes back empty for Temper too (exo already did), that's either a real finding about the field or
  evidence the section doesn't belong in the format — two specs is enough to start telling which,
  one wasn't.
