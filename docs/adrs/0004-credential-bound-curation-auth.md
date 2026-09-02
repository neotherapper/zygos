---
adr: 0004
title: Credential-bound curation auth — three keys, and the publisher agent type replaces Admin
status: accepted
date: 2026-09-02
---

# ADR-0004 — Credential-bound curation auth: three keys, and the publisher agent type replaces Admin

## Status

Accepted. Supersedes, by reference, the authorization paragraph of ADR-0002's Phase 1 result
("curator writes in Draft, reviewer records fidelity in UnderReview, admin publishes"); ADR-0002 is
otherwise untouched. The live cutover and its separation test are a separate step (see Known gap).

## Context

The local TemperPaw that runs zygos-curation had been sitting on a checkout (`75cc6c52`) whose Temper
kernel authenticated HTTP callers by a Bearer key and then let the caller *declare* who it was through
two headers, `X-Temper-Principal-Kind` and `X-Temper-Agent-Type`. The `HarnessSpec` Cedar policies in
`zygos-commons/policies/harness_spec.cedar` were written against that model: any authenticated
principal could read, an `Agent` could write Draft sections, an `Agent` with `agent_type == "reviewer"`
could record the fidelity review, and only `principal is Admin` could `Publish`, `Revise`, or
`Archive`. Both write-back clients (`tools/backfill/backfill_write.py` and the `fidelity-review`
skill) sent those headers.

Upstream `nerdsane/temperpaw` has since done the ARN-170 migration itself — 52 commits past the local
checkout, landing on `main` at `383cbc6f` with the Temper kernel pinned at `43f9379c`. The local
147-file mechanical pin bump that tried to do the same thing is therefore discarded, and the checkout
moves to `origin/main`. On that kernel the auth model is different in kind, and the old policies and
clients fail in three concrete, observed ways:

1. **The headers are stripped at the edge, so every reviewer and publish write is denied.** The
   ARN-170 kernel removes every self-declared `X-Temper-*` header before authorization. The operator
   key (`TEMPER_API_KEY`, the shell's `ZYGOS_KEY`) resolves to `Agent::"operator"` with
   `agent_type == "operator"`, whatever the caller claims. Every `RecordFidelityReview*`,
   `ReviseDraft`, and `Publish` call is Cedar-denied, and the denial is recorded as a pending decision
   that the same key cannot approve, because the kernel forbids self-approval (Temper ADR-0172).
   Confirmed live against kernel `ff0774f` on 2026-09-02.

2. **`principal is Admin` is unreachable over HTTP, so the old publish gate locks itself out.** The
   `Admin` principal is constructed only in-process (`temper-server/src/admin/mod.rs`, `api/repl.rs`)
   and never from a Bearer token or a JWT. Rewriting the clients would not help: the `Admin`-gated
   `Publish`, `Revise`, and `Archive` rules would deny every HTTP caller, permanently.

3. **The old model never gave separation of duties anyway.** One key self-declared every role by
   changing a header; nothing prevented the drafting key from passing its own review and publishing.

The kernel facts that shape the fix, verified by reading source at `ff0774f` (`43f9379c` differs only
by five CI/docs commits): a Cedar principal resolved from an `AgentCredential` carries
`principal.agent_type` equal to its `AgentType`'s `name` field and `principal.agentTypeVerified == true`;
a credential's entity id must equal the lowercase hex SHA-256 of the plaintext key; the operator key
holds only `manage_policies` on `PolicySet::"default"` out of the box; and the kernel installs an app's
Cedar from `<app>/policies/*.cedar` only, which makes `zygos-commons/specs/policies/harness_spec.cedar`
a dead duplicate.

## Decision

**Authority is resolved from the credential by the kernel, never declared by the caller.** The curation
pipeline holds three keys, each an `AgentCredential` whose agent type decides what Cedar permits:

| Key | Holder | Grants (per `zygos-commons/policies/harness_spec.cedar`) |
|---|---|---|
| `ZYGOS_KEY` | operator (== server `TEMPER_API_KEY`) | create/read/list, all Draft section writes, `SubmitForReview`, policy management |
| `ZYGOS_REVIEWER_KEY` | fidelity-review skill | `RecordFidelityReviewPassed/Failed`, `ReviseDraft` (UnderReview only) |
| `ZYGOS_PUBLISHER_KEY` | whoever publishes | `Publish` (UnderReview), `Revise` (Published), `Archive` |

Concretely:

- **Two agent types, two credentials.** `tools/temper/bootstrap_credentials.py`, run once per server
  database as the operator, defines `AgentType`s `zygos-reviewer-type` (name `reviewer`) and
  `zygos-publisher-type` (name `publisher`) and issues one `AgentCredential` for each, keyed by the
  SHA-256 of a plaintext the caller supplies or the script generates and prints once. Because the
  operator key holds only `manage_policies` out of the box, the script first installs a Cedar permit
  (`zygos-operator-identity-admin`) granting `Agent::"operator"` create/read/list/`Define` on
  `AgentType` and create/read/list/`Issue`/`Revoke` on `AgentCredential`. It verifies each new key
  through `POST /api/identity/resolve` and is idempotent.
- **Every `HarnessSpec` permit requires `agentTypeVerified`.** The rewritten policy file binds each
  rule to `principal is Agent` plus `principal.agentTypeVerified == true`; the review rules add
  `principal.agent_type == "reviewer"` and the publish/revise/archive rules add
  `principal.agent_type == "publisher"`.
- **The publish gate is the `publisher` agent type, not `Admin`.** Fidelity enforcement stays where it
  was: the IOA guard (`Publish` requires `is_true fidelity_review_passed`) and the
  `PublishRequiresFidelityReview` invariant. Cedar sees only entity fields.
- **Clients send `Authorization: Bearer <key>` and `X-Tenant-Id` and nothing else.**
  `backfill_write.py` loses its `--principal-kind` flag and runs section writes as the operator; the
  `fidelity-review` skill names which key each step needs and treats a 403 as a Cedar denial to report,
  not a transient error.
- **The dead duplicate policy file is deleted.** Only `zygos-commons/policies/` is read by the kernel.
- **Keys never enter the repo.** All three are read from the shell (`tools/temper/README.md`); the
  server holds only their SHA-256.

## Consequences

**Positive**

- `Publish`, `Revise`, and `Archive` are reachable again over HTTP, which they were not under the
  `Admin` rules on this kernel.
- Separation of duties exists for the first time: the key that drafts cannot record its own review,
  and the key that reviews cannot publish. The roles are enforced by the kernel's credential resolution,
  not by a header the caller chooses.
- The 19 live `HarnessSpec` entities, including the five Published ones (`deepseek-harness`, `rlm`,
  `exo`, `temper`, `pi`), stay on the same libSQL store; the change is to policies and clients, not to
  data. Losing any Published entity at cutover is a stop condition, not an accepted cost.
- Rotation is defined: issue a new key with the script, then `Revoke` the old credential by its SHA-256 id.

**Negative**

- **The separation is only as real as where the keys sit.** Today all three are exported in one shell.
  A single operator with all three keys can still draft, review, and publish a spec alone; the kernel
  now distinguishes the roles, but nothing yet forces them onto different people or processes.
- **Plaintext keys are secrets in the strong sense.** The kernel hashes them with unsalted SHA-256, so a
  leaked hash plus a guessable plaintext is a leaked credential. Treat the plaintexts as such, and treat
  the generated keys as printed exactly once.
- **A human-in-the-loop publish is still not enforced by the kernel.** It never was; the old `Admin`
  gate implied it without delivering it. The `publisher` key is a credential like any other, and whoever
  holds it can publish from a script.
- **The operator's identity-admin permit stays in the tenant after bootstrap.** The operator key can
  define agent types and issue or revoke credentials indefinitely, not only during the one-time setup.
- **The `agentTypeVerified` clause is load-bearing, not decorative.** Upstream TemperPaw still carries a
  header-only loopback branch that produces unverified principals. Every rule requires the flag so that
  branch cannot satisfy any `HarnessSpec` permit; dropping the clause from a single rule would reopen
  the self-declared path for that rule.

**Known gap**

This ADR decides the auth model and the policy text. It does not claim the cutover succeeded: the
restart on the new binary, the bootstrap run, the policy-reload check, and the end-to-end status table
(operator denied on review, reviewer denied on publish, header-only caller never `200`) have their own record.

## Alternatives considered

- **TemperPaw cookie login, resolving to `Admin`.** Would keep the `Admin`-gated rules as written.
  Rejected: script-hostile for the two write-back clients, and whether the kernel accepts a tokenless
  injected context that way was not verified, so the publish path would rest on an unconfirmed assumption.
- **Trusted-issuer JWT (option D1 in the TemperPaw migration plan).** Mint a token per role from a
  trusted issuer. Rejected for now: the environment variable names are undocumented and there is no
  minting route to call, so it could not be exercised end to end.
- **Collapse to the operator key alone**, granting it every `HarnessSpec` action. Rejected: zero
  separation of duties, and it would put `manage_policies` in the hand of whoever runs the reviewer,
  letting the reviewer rewrite the very rules that constrain it.
