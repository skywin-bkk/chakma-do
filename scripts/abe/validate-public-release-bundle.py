#!/usr/bin/env python3
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = json.loads((ROOT / "config/abe/task-queue.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "build/abe/public-manifest.json").read_text(encoding="utf-8"))
BUNDLE = json.loads((ROOT / "build/abe/public-release-bundle.json").read_text(encoding="utf-8"))

if QUEUE.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or QUEUE.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope or verified baseline changed")
for key in ("external_writes", "production_deploy", "destructive_actions"):
    if QUEUE.get("rules", {}).get(key) is not False:
        raise SystemExit(f"unsafe queue rule enabled: {key}")
if QUEUE.get("rules", {}).get("public_exposure") != "explicit-public-only":
    raise SystemExit("public exposure policy changed")
if BUNDLE.get("schema_version") != 1 or BUNDLE.get("release_state") != "REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid public release bundle schema/state")
if BUNDLE.get("publication_policy") != "explicit-public-only" or BUNDLE.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("invalid public release bundle boundary")
if BUNDLE.get("external_write_performed") is not False or BUNDLE.get("production_deploy_performed") is not False:
    raise SystemExit("release bundle reports consequential external action")

source_commit = BUNDLE.get("source_commit", "")
current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip().lower()
if source_commit != current or MANIFEST.get("provenance", {}).get("source_commit") != current:
    raise SystemExit("release bundle/public provenance is stale for current source commit")
if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
    raise SystemExit("invalid release bundle source commit")

expected = sorted(MANIFEST.get("assets", []), key=lambda x: (x.get("id") or "", x.get("source") or ""))
entries = BUNDLE.get("entries")
if entries != expected:
    raise SystemExit("release bundle entries do not exactly match validated PUBLIC artifacts")
if any(not isinstance(x, dict) or x.get("classification") != "PUBLIC" for x in entries):
    raise SystemExit("non-PUBLIC or invalid entry in release bundle")
for item in entries:
    integrity = item.get("integrity", {})
    if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", integrity.get("digest", "")):
        raise SystemExit("invalid release entry integrity binding")

canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
expected_digest = hashlib.sha256(canonical).hexdigest()
if BUNDLE.get("bundle_integrity") != {"algorithm": "sha256", "digest": expected_digest}:
    raise SystemExit("release bundle integrity digest mismatch")
print(f"public release bundle validation PASS: {len(entries)} PUBLIC entries; source={source_commit[:12]}; bundle={expected_digest[:12]}")
