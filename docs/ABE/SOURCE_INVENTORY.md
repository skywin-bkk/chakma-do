# ABE Source Inventory

Status: repository-controlled inventory baseline

## Authoritative scope
- Department IDs: DO-DEP-01 through DO-DEP-14 only.
- Current verified departmental baseline: DO-DEP-04.
- No DO-DEP-15 is to be inferred or created.

## Repository-controlled surfaces
| Surface | Classification | Current role |
|---|---|---|
| `.github/` | INTERNAL BUILD CONTROL | CI, templates and repository automation |
| `config/abe/` | INTERNAL BUILD CONTROL | machine-readable ABE policy and task queue |
| `docs/ABE/` | INTERNAL DOCUMENTATION | architecture, status, runner and evidence notes |
| `scripts/abe/` | INTERNAL BUILD CONTROL | validation scripts |
| `README.md` | PUBLIC-CANDIDATE REPOSITORY DOC | repository overview; not a website publication authorization |

## External/source-system boundary
Google Forms, Google Sheets, Apps Script deployments, Notion records, hosting/DNS and production website assets are not represented in this repository inventory unless their source is explicitly committed later. Their absence must not be treated as permission to recreate, overwrite, expose or delete them.

## Exposure rule
Only an asset carrying explicit PUBLIC authorization may enter a website/publication pipeline. INTERNAL and RESTRICTED assets must remain excluded by default. Unknown classification is treated as non-public.

## Next safe build step
Create a non-production website integration pipeline scaffold that consumes an explicit public allowlist and fails closed when classification is absent or invalid.
