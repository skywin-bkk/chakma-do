#!/usr/bin/env python3
"""Fail-closed checks for the browser-side approved PUBLIC registry.

The public-data collection is the publication boundary. Canonical pages expose
its declared state; the shared renderer may render only those repository-local
collections. Empty collections are valid and preferred to invented records.
"""
from pathlib import Path
import re

DATA = Path("website/assets/public-data.js")
text = DATA.read_text(encoding="utf-8")
APP = Path("website/assets/app.js").read_text(encoding="utf-8")

required_policy = "policy:'EXPLICIT_PUBLIC_ONLY'"
if required_policy not in text:
    raise SystemExit("PUBLIC registry policy is not EXPLICIT_PUBLIC_ONLY")

expected = {
    "opportunities": "VERIFIED_PUBLIC_ONLY",
    "services": "EXPLICIT_PUBLIC_ONLY",
    "resources": "APPROVED_PUBLIC_ONLY",
    "updates": "VERIFIED_PUBLIC_ONLY",
    "people": "OPT_IN_OR_APPROVED_PUBLIC_ONLY",
}
for key, state in expected.items():
    pattern = rf"\b{re.escape(key)}:'{re.escape(state)}'"
    if not re.search(pattern, text):
        raise SystemExit(f"publication contract mismatch: {key} must be {state}")

for key in ("opportunities", "services", "resources", "updates"):
    if not re.search(rf"\b{key}:\[", text):
        raise SystemExit(f"missing public registry collection: {key}")

# Opportunities have a stricter per-record verification gate in their canonical
# page. Other registries are collection-gated: entering public-data.js is itself
# the explicit/approved/verified publication action described by their state.
opportunity = Path("website/opportunities.html").read_text(encoding="utf-8")
for marker in ("VERIFIED_PUBLIC_ONLY", "public===true", "verified===true"):
    if marker not in opportunity:
        raise SystemExit(f"website/opportunities.html missing fail-closed marker: {marker}")

page_states = {
    "website/services.html": ("services", "EXPLICIT_PUBLIC_ONLY"),
    "website/resources.html": ("resources", "APPROVED_PUBLIC_ONLY"),
    "website/updates.html": ("updates", "VERIFIED_PUBLIC_ONLY"),
}
for filename, (key, state) in page_states.items():
    page = Path(filename).read_text(encoding="utf-8")
    if f"publication?.{key}" not in page:
        raise SystemExit(f"{filename} does not expose its publication state")
    if state not in text:
        raise SystemExit(f"{filename} publication state missing from public-data contract")
    renderer_marker = f"'{key}','"
    if renderer_marker not in APP:
        raise SystemExit(f"shared renderer is not wired to {key} registry")

center = Path("website/opportunity-center.html").read_text(encoding="utf-8")
if 'href="opportunities.html' not in center:
    raise SystemExit("opportunity center is not connected to canonical opportunity registry")

publication_match = re.search(r"publication:\{([^}]*)\}", text)
if not publication_match:
    raise SystemExit("missing publication contract")
if re.search(r"\b(?:INTERNAL|RESTRICTED)\b", publication_match.group(1)):
    raise SystemExit("non-public classification found in publication contract")

print("Public registry publication contract: PASS")
print("Canonical opportunity per-record gate: PASS")
print("Shared approved-data registry wiring: PASS")
