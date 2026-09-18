# ABE-021 — Public release gate chain-of-custody foundation

Status: DESIGN_CANDIDATE_ONLY

This repository-local design is the bounded next candidate after ABE-020 receives its authoritative validated transition. It does not change the authoritative task queue by itself and does not authorize publication, deployment, external writes, or destructive actions.

## Objective

Bind validated public release-gate evidence into a deterministic, append-only repository-local chain-of-custody record so that later validation can prove which source commit, public bundle, readiness attestation, and gate evidence were used without weakening any existing fail-closed boundary.

## Required invariants

1. Preserve the authoritative department scope exactly as DO-DEP-01 through DO-DEP-14 and preserve DO-DEP-04 as the verified baseline.
2. Accept only evidence already classified for explicit PUBLIC exposure. INTERNAL and RESTRICTED material must fail closed and must never be copied into chain records.
3. Require agreement between source commit, public artifact provenance, integrity digest, release bundle, readiness attestation, and release-gate evidence.
4. Use deterministic canonical serialization and SHA-256 identifiers for repository-local evidence binding.
5. Each custody record must bind to the immediately preceding validated record digest when a predecessor exists. Missing, reordered, duplicated, stale, or mismatched predecessors must fail closed.
6. The genesis record must be explicit and may be created only from validated ABE-020 gate evidence.
7. Chain generation and validation are repository-local only. `external_writes=false`, `production_deploy=false`, and `destructive_actions=false` remain mandatory.
8. A custody PASS is evidence integrity only. It must never be interpreted as deployment authorization.
9. No secrets, credentials, personal data, INTERNAL payloads, or RESTRICTED payloads may be emitted into custody records, logs, fixtures, or CI artifacts.
10. Any unknown classification, unsupported schema version, missing digest, or evidence disagreement must stop validation with a non-zero result.

## Planned repository artifacts

- `scripts/abe/build-public-release-custody.py` — deterministic repository-local custody record builder.
- `scripts/abe/validate-public-release-custody.py` — independent fail-closed validator.
- `build/abe/public-release-custody.json` — generated non-sensitive evidence record only after all upstream gates validate.
- Main ABE CI integration after local validation proves deterministic output and negative fixtures fail closed.

## Minimum acceptance tests

- Deterministic rebuild produces byte-identical custody evidence for identical validated inputs.
- PUBLIC validated input passes.
- INTERNAL classification fails.
- RESTRICTED classification fails.
- Source commit mismatch fails.
- Bundle digest mismatch fails.
- Readiness attestation mismatch fails.
- Release-gate digest mismatch fails.
- Missing predecessor fails for non-genesis records.
- Predecessor digest mismatch fails.
- Duplicate or reordered custody sequence fails.
- Any flag suggesting deployment, publication, external write, or destructive action fails.

## Transition discipline

ABE-021 must not become authoritative READY work until ABE-020 is changed from `READY` to `COMPLETE_FOUNDATION` by a traceable repository commit and that transition commit receives fresh CI validation. This design file may exist before that transition solely to make the next bounded implementation auditable and reviewable.
