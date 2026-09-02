# tools/temper

Operator-side scripts for the local TemperPaw that runs zygos-curation. Keys never live in this
repo; every script reads them from the shell.

| Script | Run as | Purpose |
|---|---|---|
| `bootstrap_credentials.py` | operator (`ZYGOS_KEY`) | One-time per server database: issue the `reviewer` and `publisher` agent credentials and the operator's identity-admin Cedar permit. Idempotent. Prints generated keys once. |

Environment (see `docs/adrs/0004-credential-bound-curation-auth.md` for why there are three keys):

| Variable | Holder | Grants (per `zygos-commons/policies/harness_spec.cedar`) |
|---|---|---|
| `ZYGOS_KEY` | operator (== server `TEMPER_API_KEY`) | create/read/list, all Draft section writes, `SubmitForReview`, policy management |
| `ZYGOS_REVIEWER_KEY` | fidelity-review skill | `RecordFidelityReviewPassed/Failed`, `ReviseDraft` (UnderReview only) |
| `ZYGOS_PUBLISHER_KEY` | whoever publishes | `Publish` (UnderReview), `Revise` (Published), `Archive` |

Rotation: issue a new key with the script (set the env var to the new value), then `Revoke` the old
`AgentCredential` by its SHA-256 id via `POST /tdata/AgentCredentials('<sha256>')/Temper.Agent.Revoke`.
