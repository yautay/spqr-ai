"""API smoke tests."""

from fastapi.testclient import TestClient

from legions_api.api.routes import game as game_routes
from legions_api.core.bootstrap import create_demo_state
from legions_api.core.results import (
    ActionResult,
    MissileDRMModifier,
    MissileEvent,
    MissileOutcome,
    ShockModifier,
    ShockOutcome,
    TQCheckOutcome,
)
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
    assert payload["turn_phase"] in {"orders", "rout_and_reload"}
    assert payload["active_side"] in {"red", "blue"}
    assert len(payload["tiles"]) > 0
    assert len(payload["units"]) > 0
    first_unit = payload["units"][0]
    assert "tq" in first_unit
    assert "cohesion_hits" in first_unit
    assert "is_routed" in first_unit
    assert "shock_type" in first_unit
    assert "pursuit_capable" in first_unit


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
    assert payload["events"] == []


def test_rulesets_endpoint_returns_original_and_simple() -> None:
    """Ruleset catalog endpoint exposes both supported variants."""

    client = TestClient(app)

    response = client.get("/game/rulesets")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload["rulesets"]) == {"original", "simple"}


def test_legal_moves_endpoint_returns_preview_options() -> None:
    """Legal moves endpoint should return destination and path metadata for active unit."""

    client = TestClient(app)

    response = client.get("/game/legal-moves/r1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["unit_id"] == "r1"
    assert len(payload["options"]) > 0
    first_option = payload["options"][0]
    assert "destination" in first_option
    assert "total_cost" in first_option
    assert "path" in first_option
    assert len(first_option["path"]) > 1


def test_missile_preview_endpoint_returns_read_only_metadata() -> None:
    """Missile preview endpoint should return hit threshold metadata without mutating state."""

    client = TestClient(app)
    before_state = client.get("/game/state").json()

    response = client.post(
        "/game/preview/missile",
        json={
            "firing_unit_id": "r1",
            "target_unit_id": "b1",
            "modifier_ids": [],
            "fire_mode": "active",
            "reaction_trigger": None,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["reason"] == "ok"
    assert payload["preview"]["range_to_target"] == 2
    assert "hit_threshold" in payload["preview"]

    after_state = client.get("/game/state").json()
    assert after_state == before_state


def test_shock_preview_endpoint_returns_read_only_metadata() -> None:
    """Shock preview endpoint should return column preview without mutating state."""

    client = TestClient(app)
    _ = client.post("/game/new", json={"ruleset": "original"})
    _ = client.post(
        "/game/action",
        json={"unit_id": "r1", "destination": {"q": 1, "r": 0}},
    )
    before_state = client.get("/game/state").json()

    response = client.post(
        "/game/preview/shock",
        json={
            "attacker_unit_id": "r1",
            "defender_unit_id": "b1",
            "angle": "front",
            "modifier_ids": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["reason"] == "ok"
    assert payload["preview"]["base_column"] >= 1
    assert payload["preview"]["final_column"] >= 1

    after_state = client.get("/game/state").json()
    assert after_state == before_state


def test_new_game_accepts_ruleset_selection() -> None:
    """New game endpoint applies selected ruleset to state payload."""

    client = TestClient(app)

    response = client.post("/game/new", json={"ruleset": "simple"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ruleset"] == "simple"


def test_phase_endpoint_updates_turn_phase() -> None:
    """Phase endpoint should update serialized turn phase marker."""

    client = TestClient(app)

    response = client.post("/game/phase", json={"phase": "rout_and_reload"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["turn_phase"] == "rout_and_reload"


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


def test_missile_action_endpoint_returns_drm_breakdown(monkeypatch) -> None:
    """Missile endpoint should expose modified roll and DRM breakdown payload."""

    client = TestClient(app)

    demo_state = create_demo_state()

    def fake_resolve_missile(state, action):
        return ActionResult(
            ok=True,
            reason="ok",
            state=demo_state,
            missile_outcome=MissileOutcome(
                firing_unit_id="r1",
                target_unit_id="b1",
                fire_mode="active",
                reaction_trigger=None,
                missile_class_id="A",
                range_to_target=2,
                table_strength=7,
                base_roll=6,
                total_drm=1,
                modified_roll=7,
                hit=True,
                applied_cohesion_hits=1,
                drm_breakdown=(
                    MissileDRMModifier(id="target_woods", drm=2),
                    MissileDRMModifier(id="target_sk", drm=-1),
                ),
            ),
            events=(
                MissileEvent(
                    event_type="missile_fired",
                    unit_id="r1",
                    target_unit_id="b1",
                    roll=6,
                    success=True,
                ),
                MissileEvent(
                    event_type="supply_changed",
                    unit_id="r1",
                    supply_before="normal",
                    supply_after="low",
                ),
            ),
        )

    monkeypatch.setattr(game_routes, "resolve_missile", fake_resolve_missile)

    response = client.post(
        "/game/action/missile",
        json={
            "firing_unit_id": "r1",
            "target_unit_id": "b1",
            "modifier_ids": ["target_woods", "target_sk"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    outcome = payload["missile_outcome"]
    assert outcome["modified_roll"] == 7
    assert outcome["total_drm"] == 1
    assert outcome["drm_breakdown"] == [
        {"id": "target_woods", "drm": 2},
        {"id": "target_sk", "drm": -1},
    ]
    assert payload["events"][0]["event_type"] == "missile_fired"
    assert payload["events"][1]["event_type"] == "supply_changed"


def test_missile_reload_endpoint_returns_reload_events(monkeypatch) -> None:
    """Missile reload endpoint should expose reload_attempt and supply_changed events."""

    client = TestClient(app)

    demo_state = create_demo_state()

    def fake_resolve_reload(state, action):
        return ActionResult(
            ok=True,
            reason="ok",
            state=demo_state,
            events=(
                MissileEvent(
                    event_type="reload_attempt",
                    unit_id="r1",
                    roll=2,
                    target=6,
                    success=True,
                    supply_before="no",
                    supply_after="no",
                ),
                MissileEvent(
                    event_type="supply_changed",
                    unit_id="r1",
                    supply_before="no",
                    supply_after="low",
                    success=True,
                ),
            ),
        )

    monkeypatch.setattr(game_routes, "resolve_reload", fake_resolve_reload)

    response = client.post(
        "/game/action/missile/reload",
        json={"unit_id": "r1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["events"] == [
        {
            "event_type": "reload_attempt",
            "unit_id": "r1",
            "target_unit_id": None,
            "reaction_trigger": None,
            "roll": 2,
            "target": 6,
            "success": True,
            "supply_before": "no",
            "supply_after": "no",
        },
        {
            "event_type": "supply_changed",
            "unit_id": "r1",
            "target_unit_id": None,
            "reaction_trigger": None,
            "roll": None,
            "target": None,
            "success": True,
            "supply_before": "no",
            "supply_after": "low",
        },
    ]


def test_shock_endpoint_returns_shock_outcome(monkeypatch) -> None:
    """Shock endpoint should expose resolved shock metadata payload."""

    client = TestClient(app)
    demo_state = create_demo_state()

    def fake_resolve_shock(state, action):
        return ActionResult(
            ok=True,
            reason="ok",
            state=demo_state,
            shock_outcome=ShockOutcome(
                attacker_unit_id="r1",
                defender_unit_id="b1",
                angle="front",
                attacker_type="HI",
                defender_type="HI",
                base_column=5,
                total_shift=1,
                final_column=6,
                roll=6,
                attacker_hits=1,
                defender_hits=2,
                modifier_breakdown=(ShockModifier(id="attacker_charging", shift=1),),
            ),
        )

    monkeypatch.setattr(game_routes, "resolve_shock", fake_resolve_shock)

    response = client.post(
        "/game/action/shock",
        json={
            "attacker_unit_id": "r1",
            "defender_unit_id": "b1",
            "angle": "front",
            "modifier_ids": ["attacker_charging"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["shock_outcome"]["final_column"] == 6
    assert payload["shock_outcome"]["modifier_breakdown"] == [{"id": "attacker_charging", "shift": 1}]


def test_game_events_websocket_stream_emits_live_action_events() -> None:
    """Websocket endpoint should stream action lifecycle events in realtime."""

    client = TestClient(app)

    with client.websocket_connect("/game/ws/events") as websocket:
        reset_response = client.post("/game/new", json={"ruleset": "original"})
        assert reset_response.status_code == 200

        reset_event = websocket.receive_json()
        assert reset_event["event_type"] == "game_reset"
        assert reset_event["ok"] is True

        action_response = client.post(
            "/game/action",
            json={"unit_id": "r1", "destination": {"q": 1, "r": 0}},
        )
        assert action_response.status_code == 200

        action_event = websocket.receive_json()
        assert action_event["event_type"] == "move_resolved"
        assert action_event["reason"] == "ok"
        assert action_event["details"]["unit_id"] == "r1"
