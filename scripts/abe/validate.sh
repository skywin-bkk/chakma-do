#!/usr/bin/env bash
set -euo pipefail

echo "ABE validation starting..."
required=("README.md" ".gitignore" "docs/ABE/README.md" "docs/ABE/BUILD_STATUS.md" ".github/pull_request_template.md" "config/abe/build-plan.json" "config/abe/task-queue.json" "config/abe/department-manifest.json" "config/abe/public-allowlist.json" "scripts/abe/build-public-manifest.py" "scripts/abe/build-public-release-bundle.py" "scripts/abe/build-public-release-readiness.py" "scripts/abe/discover-department-evidence.py" "scripts/abe/select-next-task.py" "scripts/abe/runner.py" "scripts/abe/plan-execution.py" "scripts/abe/write-audit-ledger.py" "scripts/abe/write-execution-receipt.py" "scripts/abe/propose-transition.py" "scripts/abe/bounded-work-loop.py" "scripts/abe/multi-step-advance.py" "scripts/abe/validate-public-registry.py" "scripts/abe/validate-queue-replenishment.py" "scripts/abe/validate-public-provenance.py" "scripts/abe/validate-public-release-bundle.py" "scripts/abe/validate-public-release-readiness.py")
for f in "${required[@]}"; do [[ -f "$f" ]] || { echo "::error::Missing required file: $f"; exit 1; }; done
if git grep -nE -- '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}' -- . ':(exclude)scripts/abe/validate.sh' 2>/dev/null; then echo "::error::Potential credential/private key detected."; exit 1; fi
python3 - <<'PY'
import json
from pathlib import Path
plan=json.loads(Path('config/abe/build-plan.json').read_text()); assert plan['schema_version']==1 and plan['mode']=='controlled-autonomous'; assert plan['production_deploy'] is False and plan['destructive_actions'] is False
queue=json.loads(Path('config/abe/task-queue.json').read_text()); assert queue['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14']; assert queue['verified_baseline']=='DO-DEP-04'; assert all(queue['rules'][k] is False for k in ('external_writes','production_deploy','destructive_actions'))
manifest=json.loads(Path('config/abe/department-manifest.json').read_text()); expected=[f'DO-DEP-{i:02d}' for i in range(1,15)]; assert manifest['scope']['count']==14 and manifest['scope']['allow_expansion'] is False; assert [d['id'] for d in manifest['departments']]==expected and manifest['verified_baseline']=='DO-DEP-04'
allow=json.loads(Path('config/abe/public-allowlist.json').read_text()); assert allow['policy']=='explicit-public-only' and all(x.get('classification')=='PUBLIC' for x in allow['assets']); print('ABE policy JSON: PASS')
PY
python3 scripts/abe/validate-public-registry.py
python3 scripts/abe/validate-queue-replenishment.py
python3 scripts/abe/build-public-manifest.py
python3 scripts/abe/validate-public-provenance.py
python3 scripts/abe/build-public-release-bundle.py
python3 scripts/abe/validate-public-release-bundle.py
python3 scripts/abe/build-public-release-readiness.py
python3 scripts/abe/validate-public-release-readiness.py
python3 scripts/abe/discover-department-evidence.py
python3 scripts/abe/select-next-task.py
python3 scripts/abe/runner.py
# An exhausted authoritative queue is a valid fail-closed SAFE_IDLE state, not a
# validation failure. All policy, PUBLIC-only, provenance, bundle, readiness,
# department-scope and baseline gates above have already passed. Do not invoke
# task-execution stages when there is deliberately no READY task.
if python3 - <<'PY'
import json
from pathlib import Path
selector=json.loads(Path('generated/abe/runner-state.json').read_text())
runner=json.loads(Path('build/abe/runner-state.json').read_text())
replenishment=json.loads(Path('build/abe/queue-replenishment-state.json').read_text())
assert selector['blocked'] is False and selector['selected_task'] is None
assert runner['safe_to_proceed'] is False and runner['selected_task'] is None and runner['blocked_reason'] is None
assert replenishment['status']=='SAFE_IDLE' and replenishment['ready_task_ids']==[] and replenishment['idle'] is True
assert replenishment['replenishment_policy']=='REVIEWED_REPOSITORY_CHANGE_ONLY'
assert replenishment['authoritative_mutation_performed'] is False and replenishment['scope_expansion_allowed'] is False
assert replenishment['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14'] and replenishment['verified_baseline']=='DO-DEP-04'
assert replenishment['external_writes'] is False and replenishment['production_deploy'] is False and replenishment['destructive_actions'] is False
print('ABE SAFE_IDLE gate: PASS (no READY task; reviewed repository replenishment required)')
PY
then
  echo "ABE validation PASS — SAFE_IDLE"
  exit 0
fi
python3 scripts/abe/plan-execution.py
python3 scripts/abe/write-audit-ledger.py
python3 scripts/abe/write-execution-receipt.py
python3 scripts/abe/propose-transition.py
python3 scripts/abe/bounded-work-loop.py
python3 scripts/abe/multi-step-advance.py
python3 - <<'PY'
import json
from pathlib import Path
selector=json.loads(Path('generated/abe/runner-state.json').read_text()); state=json.loads(Path('build/abe/runner-state.json').read_text()); execution=json.loads(Path('build/abe/execution-plan.json').read_text()); ledger=json.loads(Path('build/abe/audit-ledger.json').read_text()); receipt=json.loads(Path('build/abe/execution-receipt.json').read_text()); proposal=json.loads(Path('build/abe/transition-proposal.json').read_text()); loop=json.loads(Path('build/abe/work-loop-state.json').read_text()); advancement=json.loads(Path('build/abe/advancement-history.json').read_text()); replenishment=json.loads(Path('build/abe/queue-replenishment-state.json').read_text()); bundle=json.loads(Path('build/abe/public-release-bundle.json').read_text()); readiness=json.loads(Path('build/abe/public-release-readiness.json').read_text())
assert selector['blocked'] is False and selector['selected_task'] is not None; assert state['safe_to_proceed'] is True and state['selected_task']==selector['selected_task']; assert execution['safe_to_execute'] is True and execution['task']==state['selected_task']; assert ledger['task_id']==state['selected_task']['id'] and ledger['decision']=='SAFE_TO_EXECUTE_REPOSITORY_LOCAL'; assert all(v is False for v in ledger['controls'].values()); assert receipt['task_id']==state['selected_task']['id'] and receipt['result']=='FOUNDATION_VALIDATED'; assert receipt['transition_authorized'] is False and all(v is False for v in receipt['controls'].values()); assert proposal['task_id']==state['selected_task']['id']; assert proposal['from_status']=='READY' and proposal['to_status']=='COMPLETE_FOUNDATION'; assert proposal['apply_automatically'] is False and proposal['requires_reviewed_repository_commit'] is True; assert proposal['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14']; assert proposal['safety_rules_unchanged'] is True; assert proposal['external_writes'] is False and proposal['production_deploy'] is False and proposal['destructive_actions'] is False
assert loop['status']=='RUNNING' and loop['bounded_max_steps']==5; assert loop['next_task']==state['selected_task']; assert loop['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14'] and loop['verified_baseline']=='DO-DEP-04'; assert loop['production_deploy'] is False and loop['destructive_actions'] is False and loop['external_writes'] is False; assert not Path('build/abe/work-loop.lock').exists()
assert advancement['status']=='WAITING_VALIDATION'; assert advancement['bounded_max_steps']==5; assert advancement['history'][0]['task_id']==state['selected_task']['id']; assert advancement['history'][0]['decision']=='WAITING_FRESH_VALIDATION'; assert advancement['authoritative_mutation_performed'] is False and advancement['requires_reviewed_repository_commit'] is True; assert advancement['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14'] and advancement['verified_baseline']=='DO-DEP-04'; assert advancement['external_writes'] is False and advancement['production_deploy'] is False and advancement['destructive_actions'] is False
assert replenishment['status']=='READY_TASK_AVAILABLE'; assert replenishment['ready_task_ids']==[state['selected_task']['id']]; assert replenishment['replenishment_policy']=='REVIEWED_REPOSITORY_CHANGE_ONLY'; assert replenishment['authoritative_mutation_performed'] is False and replenishment['scope_expansion_allowed'] is False; assert replenishment['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14'] and replenishment['verified_baseline']=='DO-DEP-04'; assert replenishment['external_writes'] is False and replenishment['production_deploy'] is False and replenishment['destructive_actions'] is False
assert bundle['release_state']=='REPOSITORY_LOCAL_ONLY'; assert bundle['classification_boundary']=='PUBLIC_ONLY'; assert bundle['external_write_performed'] is False and bundle['production_deploy_performed'] is False; assert all(x['classification']=='PUBLIC' for x in bundle['entries'])
assert readiness['attestation_state']=='READY_REPOSITORY_LOCAL_ONLY'; assert readiness['classification_boundary']=='PUBLIC_ONLY'; assert readiness['bundle_integrity']==bundle['bundle_integrity']; assert readiness['entry_count']==len(bundle['entries']); assert readiness['authorizes_deployment'] is False; assert readiness['external_write_performed'] is False and readiness['production_deploy_performed'] is False
print('ABE runner, evidence chain, bounded work-loop, validated multi-step gate, queue replenishment gate, public provenance/integrity gate, PUBLIC release bundle gate, release readiness attestation gate, and controlled transition proposal: PASS')
PY
echo "ABE validation PASS"
