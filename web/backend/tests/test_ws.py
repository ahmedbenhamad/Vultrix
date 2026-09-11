"""WebSocket live-feed tests: auth, ownership, snapshot, live events."""

import pytest
from starlette.websockets import WebSocketDisconnect

API = "/api/v1"


def _make_assessment(client, headers) -> int:
    r = client.post(f"{API}/assessments", headers=headers, json={"name": "ws", "target": "e.com", "scan_type": "quick"})
    assert r.status_code == 201
    return r.json()["id"]


def test_ws_sends_snapshot(client, admin_headers, admin_token):
    aid = _make_assessment(client, admin_headers)
    with client.websocket_connect(f"{API}/ws/assessments/{aid}?token={admin_token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "snapshot"
        assert msg["assessment"]["id"] == aid
        assert "logs" in msg


def test_ws_rejects_unauthenticated(client, admin_headers):
    aid = _make_assessment(client, admin_headers)
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"{API}/ws/assessments/{aid}") as ws:
        ws.receive_json()


def test_ws_streams_live_events(client, admin_headers, admin_token):
    """Run a (simulated) scan and confirm live log/state events arrive over the socket."""
    aid = _make_assessment(client, admin_headers)
    with client.websocket_connect(f"{API}/ws/assessments/{aid}?token={admin_token}") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        # kick off the simulation (STRIX_FORCE_SIMULATION=true in tests)
        client.post(f"{API}/assessments/{aid}/run", headers=admin_headers)

        types_seen = set()
        for _ in range(40):  # bounded read
            msg = ws.receive_json()
            types_seen.add(msg["type"])
            if msg.get("type") == "state" and msg.get("status") == "completed":
                break
        assert "log" in types_seen
        assert "state" in types_seen
