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

## Production cutover (2026-09-02, 17:29 EEST)

Done by the operator in the temperpaw checkout (`git stash`, `git checkout -B main origin/main`,
`make wasm`, `cargo build -p temperpaw --release`, both exit 0), then the old server (pid 45846,
`75cc6c52`) was stopped, a quiescent backup taken (`~/.local/share/temperpaw-backup-2026-09-02-cutover`),
and the new binary started on port 3467 with the same `TEMPER_API_KEY`.

| Check | Result |
|---|---|
| `GET /healthz` | 200 (new pid 25747) |
| Storage line | `Storage: turso (file:~/.local/share/temperpaw/paw.db)` — same file |
| Specs restored | 83; `Bootstrapped operator credential for TEMPER_API_KEY`; 29 Cedar policies restored |
| `zygos-commons` | `OS app changed; running delta reconcile` — new policy text live (`publisher` ×7, `agentTypeVerified` ×15, `principal is Admin` ×0) |
| Inventory before vs. after | 19 = 19, identical `(Slug, Status)` multiset; Published: `deepseek-harness`, `exo`, `pi`, `rlm`, `temper` |
| Errors in log | only `BatchLogProcessor/BatchSpanProcessor.ExportError` (no OTEL collector on :4317) — present since 2026-08-31 on the old server, not new |

`tools/temper/bootstrap_credentials.py` run by the operator: every step 200/201, both keys resolve
`verified=true` with the right `agent_type_name`. Keys exported in the operator's shell only.

**Separation test on production** (scratch entity `auth-cutover-probe-1788386807`, archived at the end)

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
| GET probe entity | reviewer | 200 | 200 |

Side effect to know about: each 403 row above is an entity-plane Cedar denial, which the kernel records
as a pending decision in tenant `default`. They are evidence, not work; deny them or leave them.
