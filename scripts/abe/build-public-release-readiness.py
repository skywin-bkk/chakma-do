#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "build/abe/public-release-bundle.json"
OUT = ROOT / "build/abe/public-release-readiness.json"

bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
if bundle.get("schema_version") != 1 or bundle.get("release_state") != "REPOSITORY_LOCAL_ONLY":
    raise SystemExit("release bundle is not validated repository-local evidence")
source_commit = bundle.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
    raise SystemExit("invalid release bundle source commit")
if bundle.get("publication_policy") != "explicit-public-only" or bundle.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("release bundle public boundary mismatch")
if bundle.get("external_write_performed") is not False or bundle.get("production_deploy_performed") is not False:
    raise SystemExit("release bundle reports consequential external action")
entries = bundle.get("entries")
if not isinstance(entries, list) or any(x.get("classification") != "PUBLIC" for x in entries):
    raise SystemExit("readiness attestation accepts PUBLIC entries only")
for item in entries:
    integrity = item.get("integrity", {})
    if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", integrity.get("digest", "")):
        raise SystemExit("invalid entry integrity evidence")

bundle_integrity = bundle.get("bundle_integrity", {})
if bundle_integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", bundle_integrity.get("digest", "")):
    raise SystemExit("invalid bundle integrity evidence")
canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
if hashlib.sha256(canonical).hexdigest() != bundle_integrity["digest"]:
    raise SystemExit("release bundle integrity mismatch")

attestation = {
    "schema_version": 1,
    "attestation_state": "READY_REPOSITORY_LOCAL_ONLY",
    "source_commit": source_commit,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "bundle_integrity": bundle_integrity,
    "entry_count": len(entries),
    "checks": {
        "public_only": True,
        "integrity_verified": True,
        "provenance_bound": True,
        "external_writes_disabled": True,
        "production_deploy_disabled": True
    },
    "external_write_performed": False,
    "production_deploy_performed": False,
    "authorizes_deployment": False
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8")
print(f"public release readiness PASS: {len(entries)} PUBLIC entries; source={source_commit[:12]}")
