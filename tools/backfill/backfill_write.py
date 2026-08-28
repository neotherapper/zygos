#!/usr/bin/env python3
"""
backfill_write.py — drive a parsed HarnessSpec through the write actions.

Reads a parser-produced JSON (PascalCase entity property keys) and POSTs each
bound action for the given entity via the local Temper OData surface. Order and
params per zygos-commons/specs/model.csdl.xml. Exits non-zero on any non-200.
"""

import json
import os
import sys
import urllib.request

BASE = os.environ.get("ZYGOS_BASE", "http://127.0.0.1:3467")
KEY = os.environ.get("ZYGOS_KEY")

# action -> params it consumes from the parsed payload
# (params that are not in the payload are omitted)
ACTION_PARAMS = [
    ("SetIdentity", ["Title", "Url", "ArtifactUrl", "Commit", "Language", "Kind",
                     "License", "ProjectStatus", "Lifecycle", "Provenance", "VerifiedAt"]),
    ("WritePhilosophy", ["Philosophy"]),
    ("WritePrimitivesSection", ["PrimitivesSection", "Primitives"]),
    ("WriteLoop", ["Loop"]),
    ("WriteBoundaries", ["Boundaries"]),
    ("WriteVerification", ["Verification"]),
    ("SetAxis", ["Axis", "WhichAxis"]),
    ("WriteEconomics", ["Economics"]),
    ("WriteTradeoffs", ["Tradeoffs"]),
    ("WriteWhatToSteal", ["WhatToSteal"]),
    ("WriteWhatNotTo", ["WhatNotTo"]),
    ("SetEmbodiment", ["Embodiment", "EmbodimentSection"]),
    ("WriteLimits", ["Limits"]),
    ("WriteSources", ["Sources"]),
]


def post(url, body, principal="agent", agent_type=None):
    headers = {
        "Authorization": f"Bearer {KEY}",
        "X-Temper-Principal-Kind": principal,
        "X-Tenant-Id": "default",
        "Content-Type": "application/json",
    }
    if agent_type:
        headers["X-Temper-Agent-Type"] = agent_type
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode() if e.read else str(e)


def main():
    if len(sys.argv) < 3:
        print("usage: backfill_write.py <parsed.json> <entity_id> [--principal-kind <kind>]", file=sys.stderr)
        sys.exit(2)
    parsed_path, entity_id = sys.argv[1], sys.argv[2]
    principal = "agent"
    if "--principal-kind" in sys.argv:
        principal = sys.argv[sys.argv.index("--principal-kind") + 1]
    if not KEY:
        print("ZYGOS_KEY env not set", file=sys.stderr)
        sys.exit(2)
    with open(parsed_path) as f:
        parsed = json.load(f)

    for action, params in ACTION_PARAMS:
        body = {p: parsed[p] for p in params if p in parsed}
        url = f"{BASE}/tdata/HarnessSpecs('{entity_id}')/Zygos.{action}"
        status, resp = post(url, body, principal=principal)
        flag = "ok" if status in (200, 201) else "FAIL"
        print(f"[{flag}] {action} HTTP {status}")
        if status not in (200, 201):
            print(resp)
            sys.exit(1)
    print("all writes complete")


if __name__ == "__main__":
    main()