"""API smoke tests."""

from fastapi.testclient import TestClient

from legions_api.api.routes import game as game_routes
from legions_api.core.bootstrap import create_demo_state
from legions_api.core.results import ActionResult, TQCheckOutcome
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
    first_unit = payload["units"][0]
    assert "tq" in first_unit
    assert "cohesion_hits" in first_unit
    assert "is_routed" in first_unit


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
    assert payload["tq_check_outcomes"] == []


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


def test_game_action_response_exposes_tq_roll_metadata(monkeypatch) -> None:
    """Action endpoint should include resolved TQ outcome roll for UI explanation."""

    client = TestClient(app)

    demo_state = create_demo_state()

    def fake_resolve_move(state, action):
        return ActionResult(
            ok=True,
            reason="ok",
            state=demo_state,
            tq_check_outcomes=(
                TQCheckOutcome(
                    unit_id="b1",
                    location=demo_state.units["b1"].position,
                    source="stacking",
                    required=True,
                    formula="tq-2",
                    drm=-1,
                    target=4,
                    roll=7,
                    passed=False,
                    applied_cohesion_hits=1,
                    became_routed=True,
                ),
            ),
        )

    monkeypatch.setattr(game_routes, "resolve_move", fake_resolve_move)

    response = client.post(
        "/game/action",
        json={"unit_id": "r1", "destination": {"q": 1, "r": 0}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["tq_check_outcomes"]) == 1
    outcome = payload["tq_check_outcomes"][0]
    assert outcome["roll"] == 7
    assert outcome["target"] == 4
    assert outcome["passed"] is False
    assert outcome["became_routed"] is True
