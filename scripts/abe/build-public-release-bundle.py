#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_MANIFEST = ROOT / "build/abe/public-manifest.json"
OUT = ROOT / "build/abe/public-release-bundle.json"

manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
if manifest.get("schema_version") != 3:
    raise SystemExit("validated public manifest schema must be version 3")
provenance = manifest.get("provenance")
if not isinstance(provenance, dict):
    raise SystemExit("missing public artifact provenance")
source_commit = provenance.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
    raise SystemExit("invalid public artifact source commit")
if provenance.get("publication_policy") != "explicit-public-only":
    raise SystemExit("public release bundle policy mismatch")
if provenance.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("public release bundle classification boundary mismatch")
if provenance.get("integrity_algorithm") != "sha256":
    raise SystemExit("public release bundle integrity algorithm mismatch")
if provenance.get("external_write_performed") is not False or provenance.get("production_deploy_performed") is not False:
    raise SystemExit("public release bundle source reports consequential external action")

entries = []
for item in manifest.get("assets", []):
    if not isinstance(item, dict) or item.get("classification") != "PUBLIC":
        raise SystemExit("non-PUBLIC or invalid asset cannot enter release bundle")
    integrity = item.get("integrity", {})
    digest = integrity.get("digest", "")
    if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SystemExit("invalid PUBLIC asset integrity binding")
    entries.append({
        "id": item.get("id"),
        "source": item.get("source"),
        "classification": "PUBLIC",
        "integrity": {"algorithm": "sha256", "digest": digest},
    })

entries = sorted(entries, key=lambda x: (x["id"] or "", x["source"] or ""))
canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
bundle_digest = hashlib.sha256(canonical).hexdigest()
bundle = {
    "schema_version": 1,
    "release_state": "REPOSITORY_LOCAL_ONLY",
    "source_commit": source_commit,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "bundle_integrity": {"algorithm": "sha256", "digest": bundle_digest},
    "external_write_performed": False,
    "production_deploy_performed": False,
    "entries": entries,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
print(f"public release bundle PASS: {len(entries)} PUBLIC entries; source={source_commit[:12]}; bundle={bundle_digest[:12]}")
