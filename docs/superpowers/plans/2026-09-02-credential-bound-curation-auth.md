# Credential-Bound Curation Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the local TemperPaw that runs zygos-curation to upstream `main` (Temper kernel `43f9379c`, ARN-170 credential-bound auth) without losing the 19 live `HarnessSpec` entities, and make the two zygos write-back clients work against it.

**Architecture:** Upstream `nerdsane/temperpaw` already did the ARN-170 migration (52 commits past the local checkout `75cc6c52`), so the local 147-file mechanical pin bump is discarded and the checkout moves to `origin/main`. On the new kernel every HTTP caller is a credential-resolved `Agent` principal; `principal is Admin` is unreachable over HTTP and self-declared `X-Temper-*` headers are stripped at the edge. zygos therefore issues two agent credentials (`reviewer`, `publisher`) next to the bootstrap operator key, rewrites the `HarnessSpec` Cedar policies on `principal.agent_type` + `agentTypeVerified`, and the clients drop the two headers.

**Tech Stack:** Rust (TemperPaw / Temper, built from source), Cedar, Python 3 stdlib (`urllib`, `hashlib`), bash, `gh`.

**Spec:** `~/Developer/projects/temperpaw/docs/temper-auth-migration-plan.md` (D3) and the findings in this session, recorded in `docs/adrs/0004-credential-bound-curation-auth.md` (Task 5).

## Global Constraints

- Nothing private, ever (CLAUDE.md rule 5). Keys never enter the repo; `.env`-style values live in the shell.
- The five Published entities (`deepseek-harness`, `rlm`, `exo`, `temper`, `pi`) must still be `Published` after cutover. Any loss is a stop condition.
- Data store is the libSQL file `~/.local/share/temperpaw/paw.db` (38 MB, plus `api.key`, `vault.key`, `blobs/`). Back it up before the new binary touches it.
- The operator key: `TEMPER_API_KEY` == contents of `~/.local/share/temperpaw/api.key` == the shell's `ZYGOS_KEY`. The new server must boot with the same `TEMPER_API_KEY` or every existing caller gets 401.
- Kernel facts (Temper `ff0774f`, verified by reading source; `43f9379c` differs only by 5 CI/docs commits):
  - `AgentType` action `Define` params: `name, system_prompt, tool_set, model, max_turns, adapter_config, default_budget_cents` (all strings).
  - `AgentCredential` action `Issue` params: `agent_type_id, agent_instance_id, key_hash, key_prefix, description, created_by, expires_at`; entity id must equal `key_hash` = lowercase hex SHA-256 of the plaintext key; empty `expires_at` = never.
  - Cedar principal attrs for a credential: `principal.agent_type` = the AgentType's `name` field; `principal.agentTypeVerified == true`.
  - Operator key resolves to `Agent::"operator"`, `agent_type == "operator"`, and holds only `manage_policies` on `PolicySet::"default"` out of the box.
  - Policy route: `POST /api/tenants/default/policies/create` body `{"policy_id": "...", "cedar_text": "..."}`, gated on `manage_policies`. `GET /api/tenants/default/policies/list` lists.
  - Identity check: `POST /api/identity/resolve` body `{"bearer_token": "..."}` (unauthenticated) returns `agent_type_name`.
  - OData: `list`/`read` Cedar actions for collection/single GET; a bound action's Cedar action is the bare name after the last dot (`Zygos.Publish` → `Publish`); the resource type is `HarnessSpec`.
  - The kernel installs an app's Cedar from `<app>/policies/*.cedar` (temper-platform `os_apps/mod.rs:287`). `zygos-commons/specs/policies/harness_spec.cedar` is a dead duplicate.
- TemperPaw facts (upstream `383cbc6f`): `make wasm` is REQUIRED before first run (boot shuts down without the `AppRequired` WASM artifacts); the server looks for `<app>/wasm/<module>/target/wasm32-unknown-unknown/release/<module>.wasm`; `/tdata` needs `Authorization: Bearer` + `X-Tenant-Id` only.

---

### Task 1: Move the TemperPaw checkout to upstream main and build

**Human-run (the agent is not permitted to stash/switch this checkout).** The agent has already verified `origin/main` compiles (`cargo check -p temperpaw`, 2m06s, exit 0) and is release-building it into the shared `target/` from a scratch worktree so the rebuild here is warm.

**Files:**
- Modify: `~/Developer/projects/temperpaw` working tree (114 obsolete modified files, stashed not deleted)
- Keep untouched: `os-apps/zygos-commons`, `os-apps/zygos-curation` symlinks; `docs/temper-auth-migration-plan.md` (untracked, updated in Task 5)

- [ ] **Step 1: Stash the obsolete mechanical bump and switch**

```bash
cd ~/Developer/projects/temperpaw
git stash push -m "obsolete mechanical pin bump a747f7d4->e9ae1ac0 (superseded upstream, 2026-09-02)"
git checkout -B main origin/main
git log --oneline -1          # expect 383cbc6f
ls -la os-apps | grep zygos   # expect both symlinks still present
```

- [ ] **Step 2: Build the server and the WASM guests**

```bash
cd ~/Developer/projects/temperpaw
rustup target add wasm32-unknown-unknown wasm32-wasip1   # no-op if present
make wasm                                    # slow once; must exit 0
cargo build -p temperpaw --release           # warm from the agent's scratch build
ls -la target/release/temperpaw-server       # new mtime
```

Expected: both exit 0. Do NOT restart the running server yet (pid 45846, port 3467) — Task 6 does that after a backup.

---

### Task 2: Rewrite the HarnessSpec Cedar policies for credential-bound principals

**Files:**
- Modify: `zygos-commons/policies/harness_spec.cedar`
- Delete: `zygos-commons/specs/policies/harness_spec.cedar` (dead duplicate; kernel reads `policies/` only)

**Interfaces:**
- Produces: agent type names `reviewer` and `publisher` that Task 3 must issue and Task 4's clients must use. Cedar action names are the bare IOA action names.

- [ ] **Step 1: Write the new policy file**

Replace the whole file with:

```cedar
// zygos-commons — HarnessSpec Authorization Policies
//
// Credential-bound model (Temper ARN-170 / ADR-0157, zygos ADR-0004): every HTTP
// caller is an Agent principal resolved from an AgentCredential. Authority comes
// from the credential's AgentType name (`principal.agent_type`) — never from a
// header the caller declares. `principal is Admin` is unreachable over HTTP on
// this kernel, so the publish gate is the `publisher` agent type, not Admin.
// `agentTypeVerified` is set only on credential-resolved principals; requiring
// it defeats TemperPaw's header-only loopback branch (unverified principals).
//
// Action names are the exact IOA action names (PascalCase); resource attributes
// use the CSDL property names.

// Any credential-resolved principal can create, read, and list HarnessSpecs
permit(
    principal is Agent,
    action in [Action::"create", Action::"read", Action::"list"],
    resource is HarnessSpec
) when {
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The curator (any verified agent credential, including the operator key) writes
// all sections and submits for review, while in Draft
permit(
    principal is Agent,
    action in [
        Action::"SetIdentity",
        Action::"WritePhilosophy",
        Action::"WritePrimitivesSection",
        Action::"WriteLoop",
        Action::"WriteBoundaries",
        Action::"WriteVerification",
        Action::"SetAxis",
        Action::"WriteEconomics",
        Action::"WriteTradeoffs",
        Action::"WriteWhatToSteal",
        Action::"WriteWhatNotTo",
        Action::"SetEmbodiment",
        Action::"WriteLimits",
        Action::"WriteSources",
        Action::"SubmitForReview"
    ],
    resource is HarnessSpec
) when {
    resource.Status == "Draft" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The reviewer credential records the fidelity review, while in UnderReview
permit(
    principal is Agent,
    action in [Action::"RecordFidelityReviewPassed", Action::"RecordFidelityReviewFailed"],
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "reviewer" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The reviewer credential sends a spec back to Draft, while in UnderReview
permit(
    principal is Agent,
    action == Action::"ReviseDraft",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "reviewer" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// Only the publisher credential publishes. Fidelity enforcement lives in the IOA
// guard (`Publish` requires `is_true fidelity_review_passed`) plus the
// `PublishRequiresFidelityReview` invariant — Cedar sees only entity fields.
permit(
    principal is Agent,
    action == Action::"Publish",
    resource is HarnessSpec
) when {
    resource.Status == "UnderReview" &&
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The publisher credential can send a published spec back to UnderReview
permit(
    principal is Agent,
    action == Action::"Revise",
    resource is HarnessSpec
) when {
    resource.Status == "Published" &&
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};

// The publisher credential can archive any spec
permit(
    principal is Agent,
    action == Action::"Archive",
    resource is HarnessSpec
) when {
    principal has agent_type && principal.agent_type == "publisher" &&
    principal has agentTypeVerified && principal.agentTypeVerified == true
};
```

- [ ] **Step 2: Delete the dead duplicate and parse-check**

```bash
cd ~/Developer/projects/zygos
git rm -q zygos-commons/specs/policies/harness_spec.cedar
# Parse check with the kernel's own CLI is not available for a bare .cedar file;
# balance check only — the live check is Task 6 Step 5 (policy list shows the 7 statements).
grep -c '^permit(' zygos-commons/policies/harness_spec.cedar   # expect 7
```

- [ ] **Step 3: Commit**

```bash
git add zygos-commons/policies/harness_spec.cedar
git commit -m "zygos-commons: credential-bound HarnessSpec policies (reviewer/publisher agent types replace Admin + headers)"
```

---

### Task 3: Credential bootstrap script

**Files:**
- Create: `tools/temper/bootstrap_credentials.py`
- Create: `tools/temper/README.md`

**Interfaces:**
- Consumes: env `ZYGOS_BASE` (default `http://127.0.0.1:3467`), `ZYGOS_KEY` (operator), `ZYGOS_REVIEWER_KEY`, `ZYGOS_PUBLISHER_KEY` (plaintext keys the caller chooses; generated and printed if unset).
- Produces: AgentTypes `zygos-reviewer-type` (name `reviewer`), `zygos-publisher-type` (name `publisher`); AgentCredentials ids = sha256 of each key; policy `zygos-operator-identity-admin`. Idempotent: re-running against an already-bootstrapped tenant exits 0.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
bootstrap_credentials.py — issue the zygos-curation agent credentials on a TemperPaw
running the credential-bound auth edge (Temper ARN-170).

Run once per server database, as the operator (ZYGOS_KEY == TEMPER_API_KEY). Idempotent.

  ZYGOS_BASE            server base URL           (default http://127.0.0.1:3467)
  ZYGOS_KEY             operator key              (required)
  ZYGOS_REVIEWER_KEY    plaintext reviewer key    (generated + printed if unset)
  ZYGOS_PUBLISHER_KEY   plaintext publisher key   (generated + printed if unset)

Sequence (Temper ff0774f, crates/temper-platform/tests/identity_e2e.rs:614-720):
  0. operator grants itself create/Define/Issue/Revoke on AgentType/AgentCredential
     (out of the box it holds only manage_policies — ADR-0172)
  1. POST /tdata/AgentTypes {id}; POST .../Temper.Agent.Define {name,...}
  2. POST /tdata/AgentCredentials {id: sha256(key)}; POST .../Temper.Agent.Issue {...}
  3. POST /api/identity/resolve {bearer_token} -> agent_type_name must match
"""

import hashlib
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("ZYGOS_BASE", "http://127.0.0.1:3467").rstrip("/")
TENANT = os.environ.get("ZYGOS_TENANT", "default")
OPERATOR = os.environ.get("ZYGOS_KEY")

AGENT_TYPES = [
    # (entity id, AgentType.name -> principal.agent_type, env var, instance id)
    ("zygos-reviewer-type", "reviewer", "ZYGOS_REVIEWER_KEY", "zygos-reviewer"),
    ("zygos-publisher-type", "publisher", "ZYGOS_PUBLISHER_KEY", "zygos-publisher"),
]

OPERATOR_IDENTITY_POLICY_ID = "zygos-operator-identity-admin"
OPERATOR_IDENTITY_POLICY = "\n".join(
    f'permit(principal == Agent::"operator", action == Action::"{action}", resource is {rtype});'
    for rtype, actions in (
        ("AgentType", ["create", "read", "list", "Define"]),
        ("AgentCredential", ["create", "read", "list", "Issue", "Revoke"]),
    )
    for action in actions
)


def request(method, path, body=None, key=None):
    headers = {"X-Tenant-Id": TENANT, "Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def must(status, ok, what, payload):
    if status not in ok:
        print(f"[FAIL] {what}: HTTP {status} {payload}", file=sys.stderr)
        sys.exit(1)
    print(f"[ok]   {what}: HTTP {status}")


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_operator_policy():
    status, listing = request("GET", f"/api/tenants/{TENANT}/policies/list", key=OPERATOR)
    must(status, (200,), "list policies as operator", listing)
    existing = json.dumps(listing)
    if OPERATOR_IDENTITY_POLICY_ID in existing:
        print(f"[skip] policy {OPERATOR_IDENTITY_POLICY_ID} already present")
        return
    status, payload = request(
        "POST", f"/api/tenants/{TENANT}/policies/create",
        {"policy_id": OPERATOR_IDENTITY_POLICY_ID, "cedar_text": OPERATOR_IDENTITY_POLICY},
        key=OPERATOR,
    )
    must(status, (200, 201), f"create policy {OPERATOR_IDENTITY_POLICY_ID}", payload)


def ensure_agent_type(type_id, name):
    status, payload = request("GET", f"/tdata/AgentTypes('{type_id}')", key=OPERATOR)
    if status == 200 and payload.get("status") == "Active":
        print(f"[skip] AgentType {type_id} already Active")
        return
    if status == 404:
        status, payload = request("POST", "/tdata/AgentTypes", {"id": type_id}, key=OPERATOR)
        must(status, (200, 201), f"create AgentType {type_id}", payload)
    status, payload = request(
        "POST", f"/tdata/AgentTypes('{type_id}')/Temper.Agent.Define",
        {
            "name": name,
            "system_prompt": f"zygos-curation {name} credential (no model; HTTP client identity only)",
            "tool_set": "local",
            "model": "none",
            "max_turns": "0",
            "adapter_config": "{}",
            "default_budget_cents": "0",
        },
        key=OPERATOR,
    )
    must(status, (200,), f"Define AgentType {type_id} name={name}", payload)


def ensure_credential(type_id, instance_id, plaintext, env_var):
    key_hash = sha256_hex(plaintext)
    status, payload = request("GET", f"/tdata/AgentCredentials('{key_hash}')", key=OPERATOR)
    if status == 200 and payload.get("status") == "Active":
        print(f"[skip] AgentCredential for {env_var} already Active")
        return
    if status == 404:
        status, payload = request("POST", "/tdata/AgentCredentials", {"id": key_hash}, key=OPERATOR)
        must(status, (200, 201), f"create AgentCredential for {env_var}", payload)
    status, payload = request(
        "POST", f"/tdata/AgentCredentials('{key_hash}')/Temper.Agent.Issue",
        {
            "agent_type_id": type_id,
            "agent_instance_id": instance_id,
            "key_hash": key_hash,
            "key_prefix": plaintext[:8],
            "description": f"zygos-curation {instance_id}",
            "created_by": "zygos bootstrap_credentials.py",
            "expires_at": "",
        },
        key=OPERATOR,
    )
    must(status, (200,), f"Issue AgentCredential for {env_var}", payload)


def verify(plaintext, expected_name, env_var):
    status, payload = request("POST", "/api/identity/resolve", {"bearer_token": plaintext})
    must(status, (200,), f"resolve {env_var}", payload)
    got = payload.get("agent_type_name")
    if got != expected_name or payload.get("verified") is not True:
        print(f"[FAIL] {env_var} resolved to {payload}, expected agent_type_name={expected_name} verified=true",
              file=sys.stderr)
        sys.exit(1)
    print(f"[ok]   {env_var} resolves to agent_type={got} verified=true")


def main():
    if not OPERATOR:
        print("ZYGOS_KEY env not set (operator key == TEMPER_API_KEY of the server)", file=sys.stderr)
        sys.exit(2)
    generated = []
    keys = {}
    for _, _, env_var, _ in AGENT_TYPES:
        value = os.environ.get(env_var)
        if not value:
            value = "tmpr_" + secrets.token_hex(24)
            generated.append((env_var, value))
        keys[env_var] = value

    ensure_operator_policy()
    for type_id, name, env_var, instance_id in AGENT_TYPES:
        ensure_agent_type(type_id, name)
        ensure_credential(type_id, instance_id, keys[env_var], env_var)
    for type_id, name, env_var, instance_id in AGENT_TYPES:
        verify(keys[env_var], name, env_var)

    if generated:
        print("\nGenerated keys — export these in the shell that runs the curation skills;"
              " they are not stored anywhere else (the server holds only their SHA-256):")
        for env_var, value in generated:
            print(f"  export {env_var}={value}")
    print("\nbootstrap complete")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the README**

```markdown
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
```

- [ ] **Step 3: Syntax-check and commit**

```bash
cd ~/Developer/projects/zygos
python3 -m py_compile tools/temper/bootstrap_credentials.py && chmod +x tools/temper/bootstrap_credentials.py
git add tools/temper/
git commit -m "tools/temper: bootstrap reviewer + publisher agent credentials (ARN-170 auth edge)"
```

The live run is Task 6 Step 4; the script cannot be exercised before the new server is up.

---

### Task 4: Drop the stripped headers from the two zygos clients

**Files:**
- Modify: `tools/backfill/backfill_write.py` (`post()`, `main()` `--principal-kind`, docstring)
- Modify: `zygos-curation/agents/curator/skills/fidelity-review/SKILL.md:20-22` and the step 6/7 code comments

**Interfaces:**
- Consumes: env vars named in Task 3's README.

- [ ] **Step 1: backfill_write.py**

Replace `post()` and the `--principal-kind` handling so the file reads:

```python
def post(url, body):
    headers = {
        "Authorization": f"Bearer {KEY}",
        "X-Tenant-Id": TENANT,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
```

with `TENANT = os.environ.get("ZYGOS_TENANT", "default")` next to `KEY`, the usage line reduced to `backfill_write.py <parsed.json> <entity_id>`, the `--principal-kind` branch removed, the call site `post(url, body)`, and the docstring gaining one line: `Auth: Bearer $ZYGOS_KEY + X-Tenant-Id only — identity comes from the credential (Temper ARN-170), never from headers.`

Section writes run as the operator key, which the Task 2 policy permits (`principal is Agent` + `agentTypeVerified`).

- [ ] **Step 2: SKILL.md**

Replace lines 20-22 with:

```markdown
- **Bound actions need a credential-resolved principal, and which key you hold decides what you may do.**
  Send `Authorization: Bearer <key>` plus `X-Tenant-Id: default` and nothing else — the kernel strips every
  `X-Temper-*` header at its edge (Temper ARN-170), so a self-declared principal kind or agent type is
  silently ignored and the call 403s. Three keys, all read from the shell, none in the repo
  (`tools/temper/README.md`): `$ZYGOS_KEY` (operator) for `GET`s; `$ZYGOS_REVIEWER_KEY` for
  `RecordFidelityReviewPassed` / `RecordFidelityReviewFailed` / `ReviseDraft`; `$ZYGOS_PUBLISHER_KEY` for
  `Publish` and `Archive`. In an agent shell, run `echo ${ZYGOS_REVIEWER_KEY:-missing}` — if `missing`, ask
  the human to export it (issued by `tools/temper/bootstrap_credentials.py`); do not invent a key or commit
  one. A 403 on a write is a Cedar denial recorded as a pending decision, not a transient error — report it.
```

and annotate the code comments: step 4's two `POST` lines get the suffix `(key: $ZYGOS_REVIEWER_KEY)`, step 6's `ReviseDraft` line gets `(key: $ZYGOS_REVIEWER_KEY)`, step 7's `Publish` line gets `(key: $ZYGOS_PUBLISHER_KEY)`.

- [ ] **Step 3: Check and commit**

```bash
cd ~/Developer/projects/zygos
python3 -m py_compile tools/backfill/backfill_write.py
grep -rn 'X-Temper-Principal-Kind\|X-Temper-Agent-Type' tools zygos-curation zygos-commons   # expect no hits
git add tools/backfill/backfill_write.py zygos-curation/agents/curator/skills/fidelity-review/SKILL.md
git commit -m "curation clients: Bearer + tenant only; reviewer/publisher keys replace X-Temper-* headers"
```

---

### Task 5: Record the decision (ADR-0004, glossary, superseded plan, memory)

**Files:**
- Create: `docs/adrs/0004-credential-bound-curation-auth.md`
- Modify: `CONTEXT.md` (add one glossary entry after **re-pin**)
- Modify: `~/Developer/projects/temperpaw/docs/temper-auth-migration-plan.md` (untracked, local): prepend a status line
- Modify: `docs/adrs/0002-temper-backed-curation-pipeline.md`: no edit (ADR-0004 supersedes its auth paragraph by reference)

- [ ] **Step 1: ADR-0004**

Frontmatter and headings match ADR-0003 (`adr`, `title`, `status: accepted`, `date: 2026-09-02`; sections Status / Context / Decision / Consequences / Alternatives considered). Content must state, in fresh words:

Context — concrete observed failures: (1) the ARN-170 kernel strips `X-Temper-Principal-Kind` / `X-Temper-Agent-Type`, so the operator key resolves as `agent_type == "operator"` and every reviewer/publish write is Cedar-denied and becomes a pending decision the same key cannot approve (ADR-0172 self-approval ban, confirmed live against `ff0774f` on 2026-09-02); (2) `principal is Admin` is constructed only in-process (`temper-server/src/admin/mod.rs`, `api/repl.rs`), never from a Bearer or JWT, so the old `Admin`-gated `Publish`/`Revise`/`Archive` rules would lock those actions out entirely; (3) the old header model gave no separation of duties anyway — one key self-declared every role.

Decision: three keys with distinct Cedar reach (table from Task 3 README); agent types `reviewer`/`publisher` issued as `AgentCredential`s by `tools/temper/bootstrap_credentials.py`; every `HarnessSpec` permit requires `agentTypeVerified`; the publish gate is the `publisher` type, not Admin; clients send Bearer + tenant only.

Consequences — negative and gaps: the separation is only as real as where the keys sit (today all three in one shell); the kernel hashes keys with unsalted SHA-256, so treat plaintexts as secrets; a human-in-the-loop publish is still not enforced by the kernel (it never was); the operator's identity-admin permit stays in the tenant after bootstrap; the TemperPaw header-only loopback branch still exists upstream (unverified principals), which is why `agentTypeVerified` is mandatory in every rule.

Alternatives: TemperPaw cookie login → `Admin` (script-hostile, kernel acceptance of a tokenless injected context unverified); trusted-issuer JWT (D1 in the TemperPaw plan; env var names undocumented, no minting route); collapse to the operator key alone (zero separation, and it would put `manage_policies` in the reviewer's hand).

- [ ] **Step 2: CONTEXT.md entry** (after **re-pin**, before **target list**):

```markdown
**operator key** / **reviewer key** / **publisher key**:
The three credentials the curation pipeline holds against the local TemperPaw, each an
`AgentCredential` whose agent type decides what Cedar permits it: the operator key drafts and
manages policies, the reviewer key records fidelity reviews, the publisher key publishes and
archives. Authority is resolved from the credential by the kernel, never declared by the caller.
Rationale and the full grant table: `docs/adrs/0004`, `tools/temper/README.md`.
_Avoid_: "admin key" or "the API key" — there is no admin principal over HTTP, and "the" key hides which of the three is meant.
```

- [ ] **Step 3: Mark the TemperPaw plan superseded** — insert after line 3 of `~/Developer/projects/temperpaw/docs/temper-auth-migration-plan.md`:

```markdown
> **Superseded 2026-09-02.** Upstream `nerdsane/temperpaw` merged this migration itself (ARN-170 auth
> edge in `crates/temperpaw/src/auth.rs`, ARN-255 issuer bootstrap, pin `43f9379c` on `main` at
> `383cbc6f`; bot PR #496 bumps to `ff0774f`). The local mechanical bump is stashed, the checkout is
> `origin/main`. Only D3 survives, decided as zygos ADR-0004: `reviewer` + `publisher` agent
> credentials, issued by `zygos/tools/temper/bootstrap_credentials.py`.
```

- [ ] **Step 4: Commit (zygos only)**

```bash
cd ~/Developer/projects/zygos
git add docs/adrs/0004-credential-bound-curation-auth.md CONTEXT.md
git commit -m "ADR-0004: credential-bound curation auth (three keys, publisher agent type replaces Admin)"
```

---

### Task 6: Cutover — back up, restart on the new binary, bootstrap, verify

**Agent-run, after Task 1 is done by the human.** All commands read secrets from the environment of the running process or `api.key`, never from the repo.

- [ ] **Step 1: Back up the store while the old server still runs**

```bash
B=~/.local/share/temperpaw-backup-2026-09-02-pre-43f9379c
cp -R ~/.local/share/temperpaw "$B" && ls -la "$B" | head
cp ~/Developer/projects/temperpaw/target/release/temperpaw-server "$B/temperpaw-server.75cc6c52"   # only if Task 1 has not overwritten it yet
```

- [ ] **Step 2: Record the pre-cutover inventory**

```bash
K=$(cat ~/.local/share/temperpaw/api.key)
curl -sS 'http://127.0.0.1:3467/tdata/HarnessSpecs?$select=Slug,Status' -H "Authorization: Bearer $K" -H "X-Tenant-Id: default" > /tmp/zygos-pre.json
python3 -c 'import json;v=json.load(open("/tmp/zygos-pre.json"))["value"];print(len(v),sorted((x["Slug"],x["Status"]) for x in v if x["Status"]=="Published"))'
```
Expected: `19` and the five Published slugs.

- [ ] **Step 3: Stop pid 45846 and start the new binary with the same environment**

```bash
kill 45846; sleep 3; pgrep -fl temperpaw-server || echo stopped
cd ~/Developer/projects/temperpaw
K=$(cat ~/.local/share/temperpaw/api.key)
PORT=3467 PAW_TENANT=default TEMPER_API_KEY="$K" ZYGOS_KEY="$K" nohup ./target/release/temperpaw-server >> /private/tmp/temperpaw.log 2>&1 &
sleep 20; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3467/healthz     # 200
tail -n 200 /private/tmp/temperpaw.log | grep -E 'Storage:|Restored|deleted .* uncommitted|Registered trusted|operator credential|ERROR' | cut -c1-200
```
Stop condition: any `ERROR` about migrations, or the restart inventory (Step 5) is short. Recovery: kill the new pid, `rm -rf ~/.local/share/temperpaw && cp -R "$B" ~/.local/share/temperpaw`, restart the saved old binary the same way.

- [ ] **Step 4: Bootstrap credentials**

```bash
cd ~/Developer/projects/zygos
ZYGOS_KEY="$(cat ~/.local/share/temperpaw/api.key)" python3 tools/temper/bootstrap_credentials.py
```
Expected: every line `[ok]` or `[skip]`, two `export` lines printed. Capture the two keys into the agent's shell for Step 6 only; hand them to the human in the final report as "exported in your shell by you", never written to a file in the repo.

- [ ] **Step 5: Verify policies and inventory**

```bash
K=$(cat ~/.local/share/temperpaw/api.key)
curl -sS http://127.0.0.1:3467/api/tenants/default/policies/list -H "Authorization: Bearer $K" -H "X-Tenant-Id: default" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(json.dumps(d)[:200]);print("publisher" in json.dumps(d), "agentTypeVerified" in json.dumps(d))'
curl -sS 'http://127.0.0.1:3467/tdata/HarnessSpecs?$select=Slug,Status' -H "Authorization: Bearer $K" -H "X-Tenant-Id: default" > /tmp/zygos-post.json
python3 -c 'import json;a=json.load(open("/tmp/zygos-pre.json"))["value"];b=json.load(open("/tmp/zygos-post.json"))["value"];print(len(a),len(b),sorted((x["Slug"],x["Status"]) for x in a)==sorted((x["Slug"],x["Status"]) for x in b))'
```
Expected: `True True`, then `19 19 True`. If the app policy did not reload (no `publisher`), the reconcile did not pick up the changed `.cedar` — restart once more; if still absent, install it via `POST /api/tenants/default/policies/create` with `policy_id: zygos-harness-spec` and the file's text, and record that in the PR.

- [ ] **Step 6: End-to-end separation test on a scratch spec**

```bash
K=$(cat ~/.local/share/temperpaw/api.key); R=$ZYGOS_REVIEWER_KEY; P=$ZYGOS_PUBLISHER_KEY; H='X-Tenant-Id: default'; C='Content-Type: application/json'; U=http://127.0.0.1:3467/tdata/HarnessSpecs
ID=$(curl -sS -X POST $U -H "Authorization: Bearer $K" -H "$H" -H "$C" -d '{"Slug":"auth-cutover-probe-2026-09-02"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
# 1. curator writes as operator: expect 200 on each; use tools/backfill/backfill_write.py with a minimal parsed.json
# 2. SubmitForReview as operator: 200
# 3. RecordFidelityReviewPassed with $K (operator): expect 403  — headers do not help:
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$U('$ID')/Zygos.RecordFidelityReviewPassed" -H "Authorization: Bearer $K" -H 'X-Temper-Agent-Type: reviewer' -H 'X-Temper-Principal-Kind: agent' -H "$H" -H "$C" -d '{"Passed":true,"Findings":"probe"}'
# 4. same with $R: 200
# 5. Publish with $R: 403 ; Publish with $P: 200 ; Archive with $P: 200
# 6. no Bearer, header-only self-declared reviewer: expect 401/403, never 200
```
Record every status code in `docs/superpowers/plans/2026-09-02-credential-bound-curation-auth-verification.md` (in the repo, no keys) and paste the table in the PR body. A `200` on line 3, line 5's first call, or line 6 is a stop condition.

---

### Task 7: Review and PR

- [ ] **Step 1: Independent review** — dispatch a fresh reviewer subagent over the branch diff with `docs/adrs/0004` as the spec: does the Cedar file grant exactly the table in the README; does any client still send a stripped header; does the script's `Define`/`Issue` body match the kernel params listed in Global Constraints; does ADR-0004 make any precise-but-unsourced claim.
- [ ] **Step 2: Open the PR** against `main`, title `curation: credential-bound auth for the ARN-170 TemperPaw (ADR-0004)`, body = summary, verification table, and the exact human steps (Task 1 stash/checkout, exporting the two keys).
- [ ] **Step 3: Update memory** — `temper-versions-and-curation-auth-break.md` becomes "resolved 2026-09-02: local TemperPaw on upstream main `383cbc6f` (kernel `43f9379c`); three keys; bot PR #496 pending upstream for `ff0774f`".
