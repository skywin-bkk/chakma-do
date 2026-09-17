#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
ALLOW = ROOT / "config/abe/public-allowlist.json"
MANIFEST = ROOT / "build/abe/public-manifest.json"

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
allow = json.loads(ALLOW.read_text(encoding="utf-8"))
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"]:
    raise SystemExit("authoritative department scope changed")
if queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("verified baseline changed")
if queue.get("rules", {}).get("public_exposure") != "explicit-public-only":
    raise SystemExit("queue public exposure policy changed")
if allow.get("policy") != "explicit-public-only":
    raise SystemExit("allowlist public exposure policy changed")
if manifest.get("schema_version") != 2:
    raise SystemExit("public manifest provenance schema must be version 2")

provenance = manifest.get("provenance")
if not isinstance(provenance, dict):
    raise SystemExit("public manifest provenance missing")
source_commit = provenance.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
    raise SystemExit("invalid provenance source commit")
expected_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip().lower()
if source_commit != expected_commit:
    raise SystemExit("public artifact provenance is stale or not bound to current source commit")
if provenance.get("publication_policy") != "explicit-public-only":
    raise SystemExit("public artifact provenance policy mismatch")
if provenance.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("public artifact provenance classification boundary mismatch")
if provenance.get("external_write_performed") is not False:
    raise SystemExit("public artifact provenance reports external write")
if provenance.get("production_deploy_performed") is not False:
    raise SystemExit("public artifact provenance reports production deploy")

assets = manifest.get("assets")
if not isinstance(assets, list):
    raise SystemExit("public manifest assets must be a list")
if any(item.get("classification") != "PUBLIC" for item in assets if isinstance(item, dict)):
    raise SystemExit("non-PUBLIC asset found in public artifact provenance")
if any(not isinstance(item, dict) for item in assets):
    raise SystemExit("invalid public artifact entry")

expected_assets = [
    {"id": item.get("id"), "source": item.get("source"), "classification": "PUBLIC"}
    for item in allow.get("assets", [])
]
if assets != expected_assets:
    raise SystemExit("public artifact provenance assets do not match explicit PUBLIC allowlist")

print(f"public artifact provenance PASS: {len(assets)} PUBLIC assets; source={source_commit[:12]}")
