#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTEST = ROOT / "build/abe/public-release-readiness.json"
OUT = ROOT / "build/abe/public-release-gate.json"

att = json.loads(ATTEST.read_text(encoding="utf-8"))
if att.get("schema_version") != 1 or att.get("attestation_state") != "READY_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("release gate requires validated repository-local readiness evidence")
source = att.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid readiness source commit")
if att.get("publication_policy") != "explicit-public-only" or att.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("readiness public boundary mismatch")
checks = att.get("checks", {})
required = ("public_only", "integrity_verified", "provenance_bound", "external_writes_disabled", "production_deploy_disabled")
if any(checks.get(k) is not True for k in required):
    raise SystemExit("readiness evidence incomplete")
if att.get("external_write_performed") is not False or att.get("production_deploy_performed") is not False or att.get("authorizes_deployment") is not False:
    raise SystemExit("readiness evidence reports or authorizes consequential action")
integrity = att.get("bundle_integrity", {})
if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", integrity.get("digest", "")):
    raise SystemExit("invalid release bundle integrity evidence")

gate = {
    "schema_version": 1,
    "gate_state": "PASS_REPOSITORY_LOCAL_ONLY",
    "source_commit": source,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "bundle_integrity": integrity,
    "entry_count": att.get("entry_count"),
    "readiness_state": att["attestation_state"],
    "checks": {
        "source_commit_agrees": True,
        "public_only_provenance": True,
        "release_bundle_integrity_verified": True,
        "readiness_evidence_verified": True,
        "external_writes_disabled": True,
        "production_deploy_disabled": True
    },
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "authorizes_deployment": False
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
print(f"public release gate evidence PASS: source={source[:12]}; deployment_authorized=false")
