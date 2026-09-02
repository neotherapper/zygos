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
