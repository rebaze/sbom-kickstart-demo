#!/usr/bin/env python3
"""The policy gate: upload the build's SBOM to Dependency-Track, wait for the evaluation, stop on FAIL.

    DT_URL=https://dependencytrack.example DT_API_KEY=... \\
      python3 scripts/gate.py partner-portal/target/bom.json "Partner Portal backend" 2016.4 \\
        --parent "Vulnerable showcase" --tags owner:team-storefront,cra-scope:in

Every violation is printed with the rule and the reason the rule exists (policies/sources.json).
FAIL stops the build (exit 1); WARN and INFO are reported. Standard library only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = {"FAIL": 0, "WARN": 1, "INFO": 2}


def call(method, path, data=None, headers=None):
    req = urllib.request.Request(os.environ["DT_URL"].rstrip("/") + path, data=data, method=method, headers={
        "X-Api-Key": os.environ["DT_API_KEY"], "Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path}: {e.code} {e.read().decode()[:300]}")
    return json.loads(text) if text else None


def upload(bom, fields):
    boundary = uuid.uuid4().hex
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items())
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="bom"; filename="bom.json"\r\n'
             f"Content-Type: application/json\r\n\r\n").encode() + bom + f"\r\n--{boundary}--\r\n".encode()
    return call("POST", "/api/v1/bom", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def violations(project):
    out, page = [], 1
    while True:
        batch = call("GET", f"/api/v1/violation/project/{project}?pageSize=100&pageNumber={page}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bom"), ap.add_argument("name"), ap.add_argument("version")
    ap.add_argument("--parent"), ap.add_argument("--tags", default="")
    a = ap.parse_args()
    sources = json.load(open(os.path.join(HERE, "..", "policies", "sources.json")))

    fields = {"projectName": a.name, "projectVersion": a.version, "autoCreate": "true", "projectTags": a.tags}
    if a.parent:
        fields["parentName"] = a.parent
    started = time.time()
    token = upload(open(a.bom, "rb").read(), fields)["token"]
    while call("GET", f"/api/v1/event/token/{token}").get("processing"):
        time.sleep(2)
    project = call("GET", "/api/v1/project/lookup?" + urllib.parse.urlencode({"name": a.name, "version": a.version}))

    # Analysis and policy evaluation follow the upload: wait until two polls agree.
    found, same = None, 0
    while same < 2 and time.time() - started < 180:
        time.sleep(5)
        now = violations(project["uuid"])
        same = same + 1 if found is not None and len(now) == len(found) else 0
        found = now

    rows = sorted({(v["policyCondition"]["policy"]["violationState"], v["policyCondition"]["policy"]["name"],
                    f"{v['component']['name']} {v['component'].get('version', '')}".strip()) for v in found},
                  key=lambda r: (ORDER.get(r[0], 9), r[1], r[2]))
    fails = [r for r in rows if r[0] == "FAIL"]
    url = f"{os.environ['DT_URL'].rstrip('/')}/projects/{project['uuid']}/policyViolations"

    print(f"{a.name} {a.version}: {len(rows)} policy violations, {len(fails)} stop the build "
          f"({time.time() - started:.0f} s)\n")
    for state, rule, component in rows:
        print(f"  {state:<4}  {component}\n        rule    {rule}\n        source  {sources.get(rule, 'not documented')}")
    print(f"\n{url}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Policy gate: {a.name} {a.version}\n\n")
            f.write(("**Build stopped.** " if fails else "**Passed.** ") +
                    f"{len(rows)} violations, {len(fails)} with state FAIL.\n\n")
            if rows:
                f.write("| State | Component | Rule | Source |\n|---|---|---|---|\n")
                f.writelines(f"| {s} | {c} | {r} | {sources.get(r, 'not documented')} |\n" for s, r, c in rows)
            f.write(f"\n[Open in Dependency-Track]({url})\n")
    for state, rule, component in fails:
        print(f"::error title=Policy gate::{component} violates \"{rule}\" ({sources.get(rule, 'not documented')})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
