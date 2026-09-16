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
)

for f in "${required[@]}"; do
  [[ -f "$f" ]] || { echo "::error::Missing required file: $f"; exit 1; }
done

# Fail on common committed secret/private-key signatures.
if git grep -nE -- '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}' -- .   ':(exclude)scripts/abe/validate.sh' 2>/dev/null; then
  echo "::error::Potential credential/private key detected."
  exit 1
fi

# Validate JSON using Python from the hosted runner.
python3 - <<'PY'
import json
from pathlib import Path
p=Path("config/abe/build-plan.json")
data=json.loads(p.read_text())
assert data["schema_version"] == 1
assert data["mode"] == "controlled-autonomous"
assert data["production_deploy"] is False
assert data["destructive_actions"] is False
print("build-plan.json: PASS")
PY

echo "ABE validation PASS"
