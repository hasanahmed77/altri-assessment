"""Every client x deal eligibility decision, checked against a reviewed snapshot.

Regenerate after an intended rule change with UPDATE_GOLDEN=1, then review the diff.
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "eligibility.json"


def eligibility(api: TestClient) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for client in api.get("/clients").json():
        body = api.get(f"/clients/{client['id']}/recommendations").json()
        snapshot[client["id"]] = {
            "eligible": sorted(r["deal"]["id"] for r in body["ranked"]),
            "excluded": {
                e["deal"]["id"]: sorted(v["code"] for v in e["violations"])
                for e in body["excluded"]
            },
        }
    return snapshot


def test_eligibility_matches_the_reviewed_snapshot(api: TestClient) -> None:
    current = eligibility(api)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    assert current == json.loads(GOLDEN.read_text())
