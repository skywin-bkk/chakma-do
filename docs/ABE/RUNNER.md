# ABE Runner

## Runner level now installed
GitHub Actions is the persistent execution layer. It runs validation after pushes and pull requests and can also be dispatched manually.

## Controlled-autonomous mode
The runner may validate repository changes without human intervention. It does **not** currently:
- deploy to production;
- write to Google Drive, Forms, Sheets, Apps Script, Notion, DNS, hosting, or other external systems;
- perform destructive operations;
- expose INTERNAL or RESTRICTED assets.

Those capabilities require a validated integration, least-privilege credentials, rollback controls, and an explicit production gate.

## Human interaction target
Routine repository validation should require no repeated “continue” messages. Human input should be reserved for genuine blockers, permissions, consequential production decisions, or missing authoritative source material.
