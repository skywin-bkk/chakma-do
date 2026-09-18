#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
BUNDLE = ROOT / "build/abe/public-release-bundle.json"
ATTEST = ROOT / "build/abe/public-release-readiness.json"

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
att = json.loads(ATTEST.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
if any(queue.get("rules", {}).get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("consequential action gate changed")
if att.get("schema_version") != 1 or att.get("attestation_state") != "READY_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid readiness attestation state")
source = att.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source) or source != bundle.get("source_commit"):
    raise SystemExit("stale or mismatched readiness source commit")
if att.get("publication_policy") != "explicit-public-only" or att.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("readiness public boundary mismatch")
if att.get("bundle_integrity") != bundle.get("bundle_integrity") or att.get("entry_count") != len(bundle.get("entries", [])):
    raise SystemExit("readiness bundle evidence mismatch")
checks = att.get("checks", {})
required = ("public_only", "integrity_verified", "provenance_bound", "external_writes_disabled", "production_deploy_disabled")
if any(checks.get(k) is not True for k in required):
    raise SystemExit("readiness checks incomplete")
if att.get("external_write_performed") is not False or att.get("production_deploy_performed") is not False or att.get("authorizes_deployment") is not False:
    raise SystemExit("readiness attestation cannot authorize consequential action")
if any(x.get("classification") != "PUBLIC" for x in bundle.get("entries", [])):
    raise SystemExit("INTERNAL/RESTRICTED evidence rejected")
print(f"public release readiness validation PASS: source={source[:12]}; deployment_authorized=false")
