#!/usr/bin/env python3
import hashlib
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
if manifest.get("schema_version") != 3:
    raise SystemExit("public manifest provenance/integrity schema must be version 3")

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
if provenance.get("integrity_algorithm") != "sha256":
    raise SystemExit("public artifact integrity algorithm mismatch")
if provenance.get("external_write_performed") is not False:
    raise SystemExit("public artifact provenance reports external write")
if provenance.get("production_deploy_performed") is not False:
    raise SystemExit("public artifact provenance reports production deploy")

assets = manifest.get("assets")
if not isinstance(assets, list) or any(not isinstance(item, dict) for item in assets):
    raise SystemExit("invalid public artifact entries")
if any(item.get("classification") != "PUBLIC" for item in assets):
    raise SystemExit("non-PUBLIC asset found in public artifact provenance")

expected_assets = []
for item in allow.get("assets", []):
    if item.get("classification") != "PUBLIC":
        raise SystemExit("non-PUBLIC asset present in explicit allowlist")
    source = item.get("source")
    source_path = (ROOT / source).resolve()
    try:
        source_path.relative_to(ROOT.resolve())
    except ValueError:
        raise SystemExit(f"PUBLIC asset source escapes repository: {source}")
    if not source_path.is_file():
        raise SystemExit(f"PUBLIC asset source missing: {source}")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    expected_assets.append({
        "id": item.get("id"),
        "source": source,
        "classification": "PUBLIC",
        "integrity": {"algorithm": "sha256", "digest": digest},
    })
if assets != expected_assets:
    raise SystemExit("public artifact provenance/integrity does not match explicit PUBLIC allowlist and source bytes")
for item in assets:
    integrity = item.get("integrity", {})
    if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", integrity.get("digest", "")):
        raise SystemExit("invalid PUBLIC artifact integrity digest")

print(f"public artifact provenance/integrity PASS: {len(assets)} PUBLIC assets; source={source_commit[:12]}; algorithm=sha256")
