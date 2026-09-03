# Runbook: operating the zygos curation pipeline

How to run the server, hold the keys, move one harness spec from Draft to Published, and
practise on a throwaway copy. Written 2026-09-03 against TemperPaw `383cbc6f` (kernel
`43f9379`). Design rationale lives in the ADRs; this file is only the procedure.

Read first if you are lost: [`adrs/0002`](adrs/0002-temper-backed-curation-pipeline.md) (why a
pipeline), [`adrs/0004`](adrs/0004-credential-bound-curation-auth.md) (the three keys), then this.

## 1. What runs where

| Thing | Where |
|---|---|
| Server | `~/Developer/projects/temperpaw`, branch `main`, binary `target/release/temperpaw-server`, port 3467 |
| Data | `~/.local/share/temperpaw` (`paw.db`, `api.key`, `vault.key`, `blobs/`) |
| The zygos app | this repo's `zygos-commons/` symlinked into the TemperPaw checkout's `os-apps/` |
| Spec, model, policy | `zygos-commons/specs/harness_spec.ioa.toml`, `specs/model.csdl.xml`, `policies/harness_spec.cedar` |
| Curation skill | `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md` |
| Research method | `docs/research/SKILL.md` (what to read, what fills each section) |
| Log | `/private/tmp/temperpaw.log` |

Keys are never in this repo. See §3.

## 2. Start, check, stop

```bash
cd ~/Developer/projects/temperpaw
PORT=3467 PAW_TENANT=default TEMPER_API_KEY=$(cat ~/.local/share/temperpaw/api.key) \
  nohup ./target/release/temperpaw-server >> /private/tmp/temperpaw.log 2>&1 &
```

Run `make wasm` first only if `os-apps/` changed. A spec whose hash the server has not seen goes
through the kernel's verification cascade at boot; a failing spec stops the boot, so check the log
tail if `healthz` never answers.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3467/healthz     # 200
K=$(cat ~/.local/share/temperpaw/api.key)
curl -s 'http://127.0.0.1:3467/tdata/HarnessSpecs?$select=Slug,Status' \
  -H "Authorization: Bearer $K" -H "X-Tenant-Id: default"
curl -s http://127.0.0.1:3467/observe/specs -H "Authorization: Bearer $K" -H "X-Tenant-Id: default" \
  | python3 -c 'import sys,json;print([s for s in json.load(sys.stdin)["specs"] if s["entity_type"]=="HarnessSpec"][0]["verification_status"])'
```

Stop with `kill <pid>` of the listener on 3467 (`lsof -nP -iTCP:3467 -sTCP:LISTEN`). Never kill by
name; a sandbox may be running too.

## 3. The three keys and who holds them

| Env var | Agent type | May fire | Held by |
|---|---|---|---|
| `ZYGOS_KEY` | operator | create, read, list, every Draft write, SubmitForReview | the drafting agent's shell |
| `ZYGOS_REVIEWER_KEY` | reviewer | RecordFidelityReviewPassed / Failed, ReviseDraft | the reviewing agent's shell |
| `ZYGOS_PUBLISHER_KEY` | publisher | Publish, Revise, Archive | **you, in your own shell** |

`ZYGOS_KEY` is the server's `api.key`. The other two exist only as plaintext in shells and as
SHA-256 hashes on the server; issue or rotate them with `tools/temper/bootstrap_credentials.py`
(see `tools/temper/README.md`). Every request sends only `Authorization: Bearer <key>` and
`X-Tenant-Id: default`. A 403 is a Cedar denial and also creates a pending decision under
`/api/tenants/default/decisions`; a 409 is an automaton guard and the message names the guard.

The publisher key in your shell only is what makes the human gate real. An agent that holds it
can walk a spec to Published unaided, which is what happened for every spec before 2026-09-03.

## 4. One harness, Draft to Published

1. **Branch and pick the target.** `git checkout -b research/<slug>`; the target list is
   `docs/research/README.md`.
2. **Draft through the entity (operator key).** An agent session following
   `docs/research/SKILL.md` creates the entity (`POST /tdata/HarnessSpecs {"Slug": ...}`), calls
   `SetIdentity`, then one `Write*`/`Set*` action per section, then `SubmitForReview`. The entity's
   `@odata.actions` list shows which actions are legal from its current state. Never write files
   in `docs/research/harnesses/` by hand for a pipeline spec; that directory is an export.
3. **Fidelity review (reviewer key).** A separate agent session runs the `fidelity-review` skill:
   it re-opens the sources at the pinned commit and records `RecordFidelityReviewPassed` or
   `RecordFidelityReviewFailed` with its findings in `FidelityFindings`. On failure it calls
   `ReviseDraft`, and step 2 repeats.
4. **Read the findings yourself.** `GET /tdata/HarnessSpecs('<id>')?$select=Slug,Status,fidelity_review_passed,FidelityFindings`.
5. **Publish (publisher key).** `POST /tdata/HarnessSpecs('<id>')/Zygos.Publish` with an empty
   JSON body. This is the decision the library stands behind. Do it from your shell.
6. **Export and merge.** Render the entity to `docs/research/harnesses/<slug>.md` with the backfill
   tooling in `tools/backfill/`, update the target list, open a PR, and merge it yourself in the
   GitHub UI. The PR merge is the second human gate; do not delegate it.

Post-publication corrections go through `Revise` (Published to UnderReview, which clears the
fidelity bit) and a fresh review, never through editing the exported markdown.

## 5. Practise on a throwaway server

A second TemperPaw with an empty store, on another port, from the same binary:

```bash
SB=/tmp/zygos-sandbox && mkdir -p $SB/.local/share/temperpaw
cd ~/Developer/projects/temperpaw
HOME=$SB PORT=3468 PAW_TENANT=default PUBLIC_BASE_URL=http://localhost:3468 \
  nohup ./target/release/temperpaw-server >> $SB/sandbox.log 2>&1 &
# wait for healthz 200, then:
ZYGOS_BASE=http://127.0.0.1:3468 ZYGOS_KEY=$(cat $SB/.local/share/temperpaw/api.key) \
  python3 tools/temper/bootstrap_credentials.py      # prints two new keys, once
```

The server generates its own `api.key` in that `HOME`. Delete the directory to start over. Walk a
spec through by hand with three keys and watch which gate answers each request: 409 with a
guard name is the automaton, 403 with a decision id is Cedar. This is the fastest way to
understand the machine, and it cannot touch production data or the repo.

## 6. Verify the spec before changing it

```bash
# once: build the kernel CLI at the commit TemperPaw runs
cd ~/.cargo/git/checkouts/temper-*/43f9379 && cargo build --release -p temper-cli
# then, from the zygos checkout
<that checkout>/target/release/temper verify --specs-dir zygos-commons/specs
```

Four levels must pass. Run it on any branch that touches `harness_spec.ioa.toml` before
opening the PR; the server will refuse to boot on a failing spec anyway, but the CLI tells you
why. A change to the automaton with entities already in the store is a migration: new boolean
state variables start false on existing entities, so decide whether published specs are
grandfathered or must pass the new guard on their next `Revise`, and say so in the ADR.

## 7. Where the automation stands, and the order to grow it

What exists is an agent with keys following two documents, not a self-running pipeline. That
is enough for a spec every few days. Katagami, the model this repo's shape follows, grew the
same seed into WASM integrations that spawn agent sessions per job and finalize them, a job
queue, and a named human publishing seat. The order that respects what ADR-0002 already learned:

1. Close the two-track publication (entities are the source of truth, markdown is an export).
2. Commit the drafting skill as a file under `zygos-curation/agents/curator/skills/`; today the
   drafting procedure lives only in `docs/research/SKILL.md` and in session transcripts.
3. Make review a job that starts on `UnderReview` rather than a session someone dispatches. This
   needs the TemperPaw session primitive, which is why ADR-0002 could only promise it.
4. Target discovery as an entity (katagami's `CurationDirection`): one research prompt fans out
   into N candidate harnesses, each becoming a Draft.
5. Only then a browsing surface, if anyone needs one beyond GitHub.

Each step is an ADR before it is code. None of them changes the human gate in §3.
