#!/usr/bin/env python3
"""
backfill_write.py — drive a parsed HarnessSpec through the write actions.

Reads a parser-produced JSON (PascalCase entity property keys) and POSTs each
bound action for the given entity via the local Temper OData surface. Order and
params per zygos-commons/specs/model.csdl.xml. Exits non-zero on any non-200.
Auth: Bearer $ZYGOS_KEY + X-Tenant-Id only — identity comes from the credential (Temper ARN-170), never from headers.
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("ZYGOS_BASE", "http://127.0.0.1:3467")
KEY = os.environ.get("ZYGOS_KEY")
TENANT = os.environ.get("ZYGOS_TENANT", "default")

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
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        print(f"cannot reach {BASE}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("usage: backfill_write.py <parsed.json> <entity_id>", file=sys.stderr)
        sys.exit(2)
    parsed_path, entity_id = sys.argv[1], sys.argv[2]
    if not KEY:
        print("ZYGOS_KEY env not set", file=sys.stderr)
        sys.exit(2)
    with open(parsed_path) as f:
        parsed = json.load(f)

    for action, params in ACTION_PARAMS:
        body = {p: parsed[p] for p in params if p in parsed}
        url = f"{BASE}/tdata/HarnessSpecs('{entity_id}')/Zygos.{action}"
        status, resp = post(url, body)
        flag = "ok" if status in (200, 201) else "FAIL"
        print(f"[{flag}] {action} HTTP {status}")
        if status not in (200, 201):
            print(resp)
            sys.exit(1)
    print("all writes complete")


if __name__ == "__main__":
    main()