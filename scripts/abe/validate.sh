#!/usr/bin/env bash
set -euo pipefail

echo "ABE validation starting..."

required=(
  "README.md"
  ".gitignore"
  "docs/ABE/README.md"
  "docs/ABE/BUILD_STATUS.md"
  ".github/pull_request_template.md"
  "config/abe/build-plan.json"
  "config/abe/task-queue.json"
  "config/abe/department-manifest.json"
  "config/abe/public-allowlist.json"
  "scripts/abe/build-public-manifest.py"
  "scripts/abe/discover-department-evidence.py"
)

for f in "${required[@]}"; do
  [[ -f "$f" ]] || { echo "::error::Missing required file: $f"; exit 1; }
done

if git grep -nE -- '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}' -- . \
  ':(exclude)scripts/abe/validate.sh' 2>/dev/null; then
  echo "::error::Potential credential/private key detected."
  exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path
plan=json.loads(Path("config/abe/build-plan.json").read_text())
assert plan["schema_version"] == 1
assert plan["mode"] == "controlled-autonomous"
assert plan["production_deploy"] is False
assert plan["destructive_actions"] is False
queue=json.loads(Path("config/abe/task-queue.json").read_text())
assert queue["authoritative_department_scope"] == ["DO-DEP-01", "DO-DEP-14"]
manifest=json.loads(Path("config/abe/department-manifest.json").read_text())
expected=[f"DO-DEP-{i:02d}" for i in range(1,15)]
assert manifest["scope"]["count"] == 14
assert manifest["scope"]["allow_expansion"] is False
assert [d["id"] for d in manifest["departments"]] == expected
assert manifest["verified_baseline"] == "DO-DEP-04"
allow=json.loads(Path("config/abe/public-allowlist.json").read_text())
assert allow["policy"] == "explicit-public-only"
assert all(x.get("classification") == "PUBLIC" for x in allow["assets"])
print("ABE policy JSON: PASS")
PY

python3 scripts/abe/build-public-manifest.py
python3 scripts/abe/discover-department-evidence.py

echo "ABE validation PASS"
