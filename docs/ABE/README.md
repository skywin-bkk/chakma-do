# Autonomous Build Environment (ABE)

## Purpose
ABE is the controlled build environment for the D.O. Upgrade Version v2.0 ecosystem.

## Operating principles
1. GitHub is the authoritative code/change-history layer.
2. Production-affecting changes must be traceable.
3. No credentials, tokens, personal data, or restricted institutional records are committed.
4. PUBLIC assets may be website-exposed only when explicitly classified PUBLIC.
5. INTERNAL and RESTRICTED assets remain non-public.
6. Existing verified deployments are preserved unless a change is explicitly required.
7. Changes should be validated before production deployment.

## Current baseline
- Department Registry scope: DO-DEP-01 through DO-DEP-14.
- DO-DEP-04 physical Forms deployment has verified evidence.
- DEP-02 and DEP-03 are not to be modified by the DEP-04 deployment baseline.
- DEP-05 is not created by the DEP-04 deployment baseline.

## Build flow
Inventory → Plan → Build → Validate → Review → Deploy → Verify → Record evidence.
