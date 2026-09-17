#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOW = ROOT / "config/abe/public-allowlist.json"
OUT = ROOT / "build/abe/public-manifest.json"
POLICY = "explicit-public-only"

raw = json.loads(ALLOW.read_text(encoding="utf-8"))
if raw.get("schema_version") != 1 or raw.get("policy") != POLICY:
    raise SystemExit("invalid public allowlist policy")

assets = raw.get("assets")
if not isinstance(assets, list):
    raise SystemExit("assets must be a list")

public = []
for item in assets:
    if not isinstance(item, dict):
        raise SystemExit("allowlist entry must be an object")
    classification = item.get("classification")
    if classification != "PUBLIC":
        raise SystemExit("non-PUBLIC asset present in public allowlist")
    asset_id = item.get("id")
    source = item.get("source")
    if not asset_id or not source:
        raise SystemExit("PUBLIC asset requires id and source")
    public.append({"id": asset_id, "source": source, "classification": "PUBLIC"})

source_commit = os.environ.get("GITHUB_SHA", "").strip()
if not source_commit:
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
if len(source_commit) != 40 or any(c not in "0123456789abcdefABCDEF" for c in source_commit):
    raise SystemExit("invalid source commit for public artifact provenance")

manifest = {
    "schema_version": 2,
    "provenance": {
        "source_commit": source_commit.lower(),
        "publication_policy": POLICY,
        "classification_boundary": "PUBLIC_ONLY",
        "external_write_performed": False,
        "production_deploy_performed": False,
    },
    "assets": public,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"public manifest PASS: {len(public)} explicitly PUBLIC assets; provenance={source_commit[:12]}")
