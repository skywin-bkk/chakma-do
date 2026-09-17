#!/usr/bin/env python3
"""Fail-closed checks for the browser-side approved PUBLIC registry.

This validator deliberately inspects only repository-local source. It does not
publish, deploy, or contact external systems.
"""
from pathlib import Path
import re

DATA = Path("website/assets/public-data.js")
text = DATA.read_text(encoding="utf-8")

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

# Empty public registries are valid and safer than invented records.
for key in ("opportunities", "services", "resources", "updates"):
    if not re.search(rf"\b{key}:\[", text):
        raise SystemExit(f"missing public registry collection: {key}")

# Security contracts belong to the canonical pages that actually render each
# registry. Landing/discovery hubs may link to these pages but must not be
# mistaken for the renderer itself.
page_contracts = {
    "website/opportunities.html": (
        "VERIFIED_PUBLIC_ONLY",
        "public===true",
        "verified===true",
    ),
    "website/services.html": ("EXPLICIT_PUBLIC_ONLY",),
    "website/resources.html": ("APPROVED_PUBLIC_ONLY",),
    "website/updates.html": ("VERIFIED_PUBLIC_ONLY",),
}
for filename, markers in page_contracts.items():
    page = Path(filename).read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in page]
    if missing:
        raise SystemExit(f"{filename} missing fail-closed marker(s): {', '.join(missing)}")

# Discovery hub must route opportunity browsing to the canonical gated registry.
center = Path("website/opportunity-center.html").read_text(encoding="utf-8")
if 'href="opportunities.html' not in center:
    raise SystemExit("opportunity center is not connected to canonical opportunity registry")

# INTERNAL/RESTRICTED labels must never appear as publication states in the
# approved browser registry.
publication_match = re.search(r"publication:\{([^}]*)\}", text)
if not publication_match:
    raise SystemExit("missing publication contract")
if re.search(r"\b(?:INTERNAL|RESTRICTED)\b", publication_match.group(1)):
    raise SystemExit("non-public classification found in publication contract")

print("Public registry publication contract: PASS")
print("Canonical registry fail-closed gates: PASS")
