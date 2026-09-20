# ABE-028 — Anchored public release snapshot continuity foundation

Status: DESIGN CANDIDATE ONLY

## Purpose

Define the next bounded repository-local ABE stage after validated ABE-027 completion: deterministic continuity evidence that binds the current independently validated anchored PUBLIC release snapshot to its exact predecessor snapshot identity when a predecessor exists, while preserving a fail-closed genesis case.

## Safety boundary

ABE-028 is evidence-only. It MUST NOT authorize or perform publication, production deployment, external writes, destructive actions, secret access, or exposure of INTERNAL/RESTRICTED assets.

The authoritative department scope remains exactly DO-DEP-01 through DO-DEP-14 and the verified baseline remains DO-DEP-04.

## Proposed acceptance gate

1. Accept only independently validated ABE-027 anchored PUBLIC release snapshot evidence.
2. Emit deterministic repository-local snapshot-continuity evidence from identical validated inputs.
3. Bind the exact current snapshot identity/digest and, when present, the exact predecessor snapshot identity/digest.
4. Require predecessor linkage to be monotonic and non-self-referential; permit only an explicit deterministic genesis state when no predecessor is present.
5. Reject stale/substituted snapshots, forked predecessor linkage, mutation/deletion, identity or digest mismatch, non-PUBLIC evidence, scope/baseline drift, and any consequential-action authority fail-closed.
6. Preserve `public_exposure=explicit-public-only`, `external_writes=false`, `production_deploy=false`, and `destructive_actions=false`.
7. Preserve DO-DEP-01 through DO-DEP-14 authoritative scope and DO-DEP-04 verified baseline.

## Planned implementation sequence

After this design head receives fresh CI validation:

1. replenish the authoritative queue with ABE-028 as `READY` without changing prior task metadata;
2. implement a deterministic continuity builder;
3. implement an independent fail-closed validator;
4. add dedicated deterministic and negative-case CI;
5. record fresh validation evidence and a separate completion gate before any authoritative completion transition.

No production or external-system change is authorized by this design.
