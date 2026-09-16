#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOW = ROOT / "config/abe/public-allowlist.json"
OUT = ROOT / "build/abe/public-manifest.json"

raw = json.loads(ALLOW.read_text(encoding="utf-8"))
if raw.get("schema_version") != 1 or raw.get("policy") != "explicit-public-only":
    raise SystemExit("invalid public allowlist policy")

assets = raw.get("assets")
if not isinstance(assets, list):
    raise SystemExit("assets must be a list")

public = []
for item in assets:
    if not isinstance(item, dict):
        raise SystemExit("allowlist entry must be an object")
    if item.get("classification") != "PUBLIC":
        raise SystemExit("non-PUBLIC asset present in public allowlist")
    asset_id = item.get("id")
    source = item.get("source")
    if not asset_id or not source:
        raise SystemExit("PUBLIC asset requires id and source")
    public.append({"id": asset_id, "source": source, "classification": "PUBLIC"})

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schema_version": 1, "assets": public}, indent=2) + "\n", encoding="utf-8")
print(f"public manifest PASS: {len(public)} explicitly PUBLIC assets")
