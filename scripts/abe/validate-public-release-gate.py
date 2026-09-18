#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
BUNDLE = ROOT / "build/abe/public-release-bundle.json"
ATTEST = ROOT / "build/abe/public-release-readiness.json"
GATE = ROOT / "build/abe/public-release-gate.json"

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
att = json.loads(ATTEST.read_text(encoding="utf-8"))
gate = json.loads(GATE.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
if queue.get("rules", {}).get("public_exposure") != "explicit-public-only" or any(queue.get("rules", {}).get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("authoritative safety gate changed")
if gate.get("schema_version") != 1 or gate.get("gate_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid release gate evidence state")
source = gate.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source) or source != att.get("source_commit") or source != bundle.get("source_commit"):
    raise SystemExit("stale or mismatched release gate source commit")
if gate.get("publication_policy") != "explicit-public-only" or gate.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("release gate public boundary mismatch")
if gate.get("bundle_integrity") != att.get("bundle_integrity") or gate.get("bundle_integrity") != bundle.get("bundle_integrity"):
    raise SystemExit("release gate integrity evidence mismatch")
if gate.get("entry_count") != att.get("entry_count") or gate.get("entry_count") != len(bundle.get("entries", [])):
    raise SystemExit("release gate entry evidence mismatch")
if gate.get("readiness_state") != "READY_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("release gate readiness state mismatch")
checks = gate.get("checks", {})
required = ("source_commit_agrees", "public_only_provenance", "release_bundle_integrity_verified", "readiness_evidence_verified", "external_writes_disabled", "production_deploy_disabled")
if any(checks.get(k) is not True for k in required):
    raise SystemExit("release gate checks incomplete")
if any(x.get("classification") != "PUBLIC" for x in bundle.get("entries", [])):
    raise SystemExit("INTERNAL/RESTRICTED evidence rejected")
if gate.get("external_write_performed") is not False or gate.get("production_deploy_performed") is not False or gate.get("publication_performed") is not False or gate.get("authorizes_deployment") is not False:
    raise SystemExit("release gate cannot perform or authorize consequential action")
print(f"public release gate validation PASS: source={source[:12]}; deployment_authorized=false")
