# Concepts

Cross-cutting technique, lifted out of individual specs once it recurs across three or more harnesses.
Each concept document must cite the specs it generalises from and re-verify each occurrence against its
own primary source — do not inherit someone else's synthesis on their word alone, even when the
synthesis itself cites primary sources correctly.

Concepts are the durable output of this library. Individual harness specs age; the technique they share
usually does not.

## Planned

| Concept | Candidate evidence | Status |
|---|---|---|
| The log is the program | exo (event-log-as-state), a plugin-composable harness with a per-request invariant check, a proved-before-running runtime — three candidates named at project start, none yet independently verified here | not started — verify each occurrence against its own primary source before writing |
| Recoverability vs soundness | exo (recovery, no prevention) against a proved-before-running design (prevention, no recovery emphasis) | seeded by exo's "Which axis" section; needs a second spec |
| Verification: what gates vs what merely reports | exo's instrumentation-without-gating finding | seeded; needs a second spec that gates something, for contrast |

Nothing written yet. A concept document needs at least three cited occurrences before it moves out of
this table — see `CLAUDE.md`.
