from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

ALL_DEALS = 45


def recommendations(api: TestClient, client_id: str) -> dict[str, Any]:
    response = api.get(f"/clients/{client_id}/recommendations")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_health(api: TestClient) -> None:
    assert api.get("/health").json() == {"status": "ok"}


def test_list_clients_has_every_client_with_a_summary(api: TestClient) -> None:
    clients = api.get("/clients").json()

    assert len(clients) == 15
    priya = next(c for c in clients if c["id"] == "C-01")
    assert priya["feedback_count"] == 7
    assert priya["summary"].startswith("$300,000 (flexible), cash flow focus")


def test_client_detail_has_feedback_newest_first_and_calls(api: TestClient) -> None:
    client = api.get("/clients/C-15").json()

    ids = [f["id"] for f in client["feedback"]]
    assert ids == sorted(ids, reverse=True)
    assert len(client["calls"]) == 2


def test_client_detail_lists_market_terms_with_no_market(api: TestClient) -> None:
    assert api.get("/clients/C-13").json()["unresolved_markets"] == ["Texas Hill Country"]


def test_unknown_client_is_404(api: TestClient) -> None:
    assert api.get("/clients/C-99").status_code == 404
    assert api.get("/clients/C-99/recommendations").status_code == 404


def test_every_deal_is_either_ranked_or_excluded_for_every_client(api: TestClient) -> None:
    for client in api.get("/clients").json():
        body = recommendations(api, client["id"])
        ranked = [r["deal"]["id"] for r in body["ranked"]]
        excluded = [e["deal"]["id"] for e in body["excluded"]]

        assert len(ranked) + len(excluded) == ALL_DEALS
        assert set(ranked).isdisjoint(excluded)
        assert [r["rank"] for r in body["ranked"]] == list(range(1, len(ranked) + 1))


def test_excluded_deals_carry_numbers_and_every_broken_rule(api: TestClient) -> None:
    excluded = {e["deal"]["id"]: e for e in recommendations(api, "C-03")["excluded"]}
    d132 = excluded["D-132"]

    # Shenandoah is avoided by name; resolving it relies on the migration's alias table
    assert {v["code"] for v in d132["violations"]} >= {"AVOIDED_MARKET", "DOES_NOT_PENCIL"}
    assert d132["numbers"]["coc"]["low"] == pytest.approx(0.02993, abs=1e-5)


def test_a_state_name_avoids_every_market_in_it(api: TestClient) -> None:
    excluded = recommendations(api, "C-11")["excluded"]
    florida = [e for e in excluded if e["deal"]["state"] == "FL"]

    assert florida
    assert all("AVOIDED_MARKET" in {v["code"] for v in e["violations"]} for e in florida)


def test_post_feedback_returns_the_created_row(api: TestClient) -> None:
    response = api.post(
        "/feedback",
        json={"client_id": "C-12", "deal_id": "D-108", "reaction": "up", "comment": "  Nice  "},
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["client_id"], body["deal_id"], body["reaction"]) == ("C-12", "D-108", "up")
    assert body["comment"] == "Nice"


def test_post_feedback_rejects_unknown_ids_and_bad_input(api: TestClient) -> None:
    def post(**changes: Any) -> int:
        body = {"client_id": "C-12", "deal_id": "D-108", "reaction": "up"} | changes
        return api.post("/feedback", json=body).status_code

    assert post(client_id="C-99") == 404
    assert post(deal_id="D-999") == 404
    assert post(reaction="maybe") == 422
    assert post(comment="x" * 1001) == 422


def test_feedback_changes_the_next_recommendations(api: TestClient) -> None:
    before = recommendations(api, "C-12")["ranked"]
    passed = before[0]
    neighbour = next(
        r
        for r in before[1:]
        if r["deal"]["market"]["id"] == passed["deal"]["market"]["id"]
        and r["deal"]["address"] != passed["deal"]["address"]
    )

    api.post(
        "/feedback",
        json={"client_id": "C-12", "deal_id": passed["deal"]["id"], "reaction": "down"},
    )
    after = {r["deal"]["id"]: r for r in recommendations(api, "C-12")["ranked"]}

    assert after[passed["deal"]["id"]]["status"] == "already_shared"
    assert after[passed["deal"]["id"]]["reaction"] == "down"
    assert after[neighbour["deal"]["id"]]["score"] < neighbour["score"]


def test_recommendations_make_a_single_database_query(api: TestClient) -> None:
    statements: list[str] = []
    engine = api.app.state.engine  # type: ignore[attr-defined]
    event.listen(engine, "before_cursor_execute", lambda *args: statements.append(args[2]))

    recommendations(api, "C-01")

    assert len(statements) == 1
