# ABE-023 — Public Release Custody History Checkpoint Foundation

## Purpose

Define the next bounded repository-local foundation after ABE-022: deterministic checkpoints over validated append-only PUBLIC release custody history. A checkpoint is evidence about history integrity only; it is never publication, deployment, or external-write authorization.

## Preconditions

Implementation MUST NOT begin until ABE-022 is authoritatively transitioned from `READY` to `COMPLETE_FOUNDATION` after fresh CI validation of its validation-evidence commit.

## Safety invariants

- Preserve the authoritative department scope exactly as DO-DEP-01 through DO-DEP-14.
- Preserve DO-DEP-04 as the verified baseline; do not fabricate verification for any other department.
- Preserve `explicit-public-only` exposure policy.
- Keep external writes, production deployment, destructive actions, and secret access disabled.
- Reject INTERNAL or RESTRICTED evidence fail-closed.
- A checkpoint MUST NOT authorize publication, deployment, external writes, or destructive actions.

## Deterministic checkpoint contract

A checkpoint builder should consume only a custody history that independently passes ABE-022 validation and emit canonical repository-local evidence containing at minimum:

1. checkpoint schema/version and stage identifier;
2. exact source/history identity;
3. first and last custody sequence numbers covered;
4. exact terminal custody record digest;
5. deterministic digest of the canonical validated history covered by the checkpoint;
6. record count and continuity assertion;
7. PUBLIC-only classification assertion;
8. explicit consequential-action flags set to false.

The canonical checkpoint digest must be stable for identical validated inputs.

## Fail-closed validator contract

An independent validator must reject at minimum:

- missing or malformed checkpoint fields;
- history that fails ABE-022 validation;
- sequence gaps, reorder, duplication, deletion, or mutation;
- first/last sequence or record-count mismatch;
- terminal custody digest mismatch;
- checkpoint/history digest mismatch;
- stale or mismatched source identity;
- any INTERNAL or RESTRICTED classification;
- any publication, deployment, external-write, destructive-action, or secret-access intent.

## CI contract

A dedicated repository-local CI gate should rebuild the checkpoint from authoritative inputs, independently validate it, compare deterministic output, and fail closed on disagreement. Existing ABE safety and custody-history validation must remain intact.

## Acceptance criteria

ABE-023 may later be marked `COMPLETE_FOUNDATION` only after all of the following are true:

- deterministic checkpoint builder exists;
- independent fail-closed validator exists;
- dedicated CI enforcement exists;
- validation evidence is recorded in the repository;
- that evidence commit itself receives fresh successful CI validation;
- no production deployment, publication, external write, destructive action, scope expansion, or secret access occurred.

## Transition discipline

This design does not change the authoritative task queue. ABE-022 remains authoritative until a separately validated queue transition. Only after that transition may ABE-023 become `READY` and implementation begin.
