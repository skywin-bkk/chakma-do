#!/usr/bin/env bash
set -euo pipefail

echo "ABE validation starting..."

required=(
  "README.md" ".gitignore" "docs/ABE/README.md" "docs/ABE/BUILD_STATUS.md"
  ".github/pull_request_template.md" "config/abe/build-plan.json" "config/abe/task-queue.json"
  "config/abe/department-manifest.json" "config/abe/public-allowlist.json"
  "scripts/abe/build-public-manifest.py" "scripts/abe/discover-department-evidence.py"
  "scripts/abe/select-next-task.py" "scripts/abe/runner.py" "scripts/abe/plan-execution.py"
  "scripts/abe/write-audit-ledger.py" "scripts/abe/write-execution-receipt.py"
  "scripts/abe/propose-transition.py"
)
for f in "${required[@]}"; do [[ -f "$f" ]] || { echo "::error::Missing required file: $f"; exit 1; }; done

if git grep -nE -- '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}' -- . ':(exclude)scripts/abe/validate.sh' 2>/dev/null; then
  echo "::error::Potential credential/private key detected."; exit 1
fi

python3 - <<'PY'
import json
from pathlib import Path
plan=json.loads(Path('config/abe/build-plan.json').read_text())
assert plan['schema_version']==1 and plan['mode']=='controlled-autonomous'
assert plan['production_deploy'] is False and plan['destructive_actions'] is False
queue=json.loads(Path('config/abe/task-queue.json').read_text())
assert queue['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14']
assert all(queue['rules'][k] is False for k in ('external_writes','production_deploy','destructive_actions'))
manifest=json.loads(Path('config/abe/department-manifest.json').read_text())
expected=[f'DO-DEP-{i:02d}' for i in range(1,15)]
assert manifest['scope']['count']==14 and manifest['scope']['allow_expansion'] is False
assert [d['id'] for d in manifest['departments']]==expected and manifest['verified_baseline']=='DO-DEP-04'
allow=json.loads(Path('config/abe/public-allowlist.json').read_text())
assert allow['policy']=='explicit-public-only' and all(x.get('classification')=='PUBLIC' for x in allow['assets'])
print('ABE policy JSON: PASS')
PY

python3 scripts/abe/build-public-manifest.py
python3 scripts/abe/discover-department-evidence.py
python3 scripts/abe/select-next-task.py
python3 scripts/abe/runner.py
python3 scripts/abe/plan-execution.py
python3 scripts/abe/write-audit-ledger.py
python3 scripts/abe/write-execution-receipt.py
python3 scripts/abe/propose-transition.py

python3 - <<'PY'
import json
from pathlib import Path
selector=json.loads(Path('generated/abe/runner-state.json').read_text())
state=json.loads(Path('build/abe/runner-state.json').read_text())
execution=json.loads(Path('build/abe/execution-plan.json').read_text())
ledger=json.loads(Path('build/abe/audit-ledger.json').read_text())
receipt=json.loads(Path('build/abe/execution-receipt.json').read_text())
proposal=json.loads(Path('build/abe/transition-proposal.json').read_text())
assert selector['blocked'] is False and selector['selected_task'] is not None
assert state['safe_to_proceed'] is True and state['selected_task']==selector['selected_task']
assert execution['safe_to_execute'] is True and execution['task']==state['selected_task']
assert ledger['task_id']==state['selected_task']['id'] and ledger['decision']=='SAFE_TO_EXECUTE_REPOSITORY_LOCAL'
assert all(v is False for v in ledger['controls'].values())
assert receipt['task_id']==state['selected_task']['id'] and receipt['result']=='FOUNDATION_VALIDATED'
assert receipt['transition_authorized'] is False and all(v is False for v in receipt['controls'].values())
assert proposal['task_id']==state['selected_task']['id']
assert proposal['from_status']=='READY' and proposal['to_status']=='COMPLETE_FOUNDATION'
assert proposal['apply_automatically'] is False and proposal['requires_reviewed_repository_commit'] is True
assert proposal['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14']
assert proposal['safety_rules_unchanged'] is True
assert proposal['external_writes'] is False and proposal['production_deploy'] is False and proposal['destructive_actions'] is False
print('ABE runner, evidence chain, and controlled transition proposal: PASS')
PY

echo "ABE validation PASS"
