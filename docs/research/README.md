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

`best-of-Agent-Harnesses` is a discovery source for future targets, not a subject of its own record —
see `DESIGN.md` §3 (Non-Goals: breadth).

## Pinned commits for the next three specs

Read at these SHAs, not `main`, per rule 1:

| Harness | Repo | SHA |
|---|---|---|
| Temper | `nerdsane/temper` | `2f43ecefaa00bf2e9d75c6b67c2ddf8857821400` |
| RLM | (repo TBD at research time) | `caf0bffa1acec17c062559433b4cd4ed92eee3d6` |
| DeepSeek Harness | (repo TBD at research time) | `47f943859bef60e4160492346772ded9b24f765a` |

These SHAs were relayed, not yet independently confirmed to resolve by this repo's own tooling — do so
before citing any of them as `artifact_url` in a spec, the same check already run against katagami's
and best-of-Agent-Harnesses' SHAs before either was quoted from.
