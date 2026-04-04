"""API smoke tests."""

from fastapi.testclient import TestClient

from legions_api.main import app


def test_health_returns_ok() -> None:
    """Health endpoint returns stable OK payload."""

    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_game_state_endpoint_returns_tiles_and_units() -> None:
    """Current game state endpoint returns map and unit payloads."""

    client = TestClient(app)

    response = client.get("/game/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_side"] in {"red", "blue"}
    assert len(payload["tiles"]) > 0
    assert len(payload["units"]) > 0


def test_game_action_rejects_illegal_move() -> None:
    """Invalid movement command returns stable error response shape."""

    client = TestClient(app)

    response = client.post(
        "/game/action",
        json={"unit_id": "r1", "destination": {"q": 99, "r": 99}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["reason"] in {"destination_out_of_map", "no_valid_path"}
    assert payload["effects"] == []
    assert payload["pending_tq_checks"] == []


def test_rulesets_endpoint_returns_original_and_simple() -> None:
    """Ruleset catalog endpoint exposes both supported variants."""

    client = TestClient(app)

    response = client.get("/game/rulesets")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload["rulesets"]) == {"original", "simple"}


def test_new_game_accepts_ruleset_selection() -> None:
    """New game endpoint applies selected ruleset to state payload."""

    client = TestClient(app)

    response = client.post("/game/new", json={"ruleset": "simple"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ruleset"] == "simple"
