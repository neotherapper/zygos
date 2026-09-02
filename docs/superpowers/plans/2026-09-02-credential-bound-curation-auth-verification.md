# Credential-bound curation auth — verification record

Companion to `2026-09-02-credential-bound-curation-auth.md` (Task 6) and `docs/adrs/0004`. No keys
appear here; every call read them from the shell.

## Rehearsal (2026-09-02, before the production cutover)

Run against a **copy** of the production data directory (`~/.local/share/temperpaw`, backed up at
`~/.local/share/temperpaw-backup-2026-09-02-pre-43f9379c`), served on port 3468 by the upstream
TemperPaw binary (`nerdsane/temperpaw` `383cbc6f`, kernel `43f9379c`) built from a scratch worktree
with the zygos apps symlinked into its `os-apps/`, while the old server (`75cc6c52`, kernel
`a747f7d4`) kept running untouched on port 3467.

**Boot on the copied store**

| Check | Result |
|---|---|
| `GET /healthz` | 200 |
| Storage line in log | `Storage: turso (file:<copy>/paw.db)` |
| Specs restored from storage | 83 |
| Operator credential | `Bootstrapped operator credential for TEMPER_API_KEY` (tenant `default`) |
| Cedar policies restored | 29, one tenant |
| `zygos-commons-harness_spec` policy after app reconcile | new text loaded: `publisher` present, `agentTypeVerified` present |
| Errors in log | none (warnings only: `zygos-curation` has no `app.toml`, undeclared bundled WASM artifacts, no sandbox key) |
| `GET /tdata/HarnessSpecs` inventory vs. the old server | 19 = 19, identical `(Slug, Status)` multiset; the five Published rows intact |

Observed difference in the OData surface: the new kernel omits null properties from `$select`
responses where the old one returned them as null (`Slug` on one legacy Draft entity). Not a data change.

**`tools/temper/bootstrap_credentials.py`**

First run: operator policy created (201), both `AgentType`s created + `Define`d (201/200), both
`AgentCredential`s created + `Issue`d (201/200). `POST /api/identity/resolve` returned 401 when sent
without a Bearer: TemperPaw's outer auth layer gates every route except `/healthz`, so the script now
sends the operator key on that call. Second run: every step `[skip]`, both keys resolve with
`verified=true` and the right `agent_type_name`. Exit 0 both times.

**End-to-end separation test** (scratch entity `auth-cutover-probe-1788334573`, archived at the end)

| step | key | expected | got |
|---|---|---|---|
| 14 section writes via backfill_write.py | operator | all writes complete | all writes complete |
| SubmitForReview | operator | 200 | 200 |
| RecordFidelityReviewPassed + self-declared reviewer headers | operator | 403 | 403 |
| RecordFidelityReviewPassed | publisher | 403 | 403 |
| RecordFidelityReviewPassed, no Bearer, header-only reviewer | none | 401 or 403 | 401 |
| RecordFidelityReviewPassed | reviewer | 200 | 200 |
| Publish | reviewer | 403 | 403 |
| Publish | operator | 403 | 403 |
| Publish | publisher | 200 | 200 |
| Archive | reviewer | 403 | 403 |
| Archive | publisher | 200 | 200 |
| GET probe entity | reviewer | 200 | 200, `status: Archived`, `fidelity_review_passed: true` |

Side finding fixed on the branch: the fidelity-review skill documented the review body as
`{"Passed", "Findings"}`; the CSDL parameter is `FidelityFindings` (the verdict is the action name).

## Production cutover

_Pending: Task 1 (checkout switch + build in the human's temperpaw checkout), then Task 6 Steps 3–5
repeated against port 3467 with the same script and the same test. Results to be appended here._
