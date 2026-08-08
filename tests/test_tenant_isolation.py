from fastapi.testclient import TestClient

from src import app as app_module


client = TestClient(app_module.app)


def _headers(institution_id: str, role: str = "guardian", user_id: str = "user-1"):
    return {
        "x-institution-id": institution_id,
        "x-user-role": role,
        "x-user-id": user_id,
    }


def test_get_activities_returns_only_request_tenant_data():
    response_mergington = client.get("/activities", headers=_headers("mergington-high"))
    response_riverside = client.get("/activities", headers=_headers("riverside-high"))

    assert response_mergington.status_code == 200
    assert response_riverside.status_code == 200

    mergington_activities = response_mergington.json()
    riverside_activities = response_riverside.json()

    assert "Chess Club" in mergington_activities
    assert "Math Club" not in mergington_activities

    assert "Math Club" in riverside_activities
    assert "Chess Club" not in riverside_activities


def test_cross_tenant_mutation_attempt_returns_not_found_and_does_not_change_state():
    before = client.get("/activities", headers=_headers("riverside-high")).json()

    response = client.post(
        "/activities/Chess%20Club/signup?email=alex@riverside.edu",
        headers=_headers("riverside-high", user_id="guardian-riverside"),
    )

    after = client.get("/activities", headers=_headers("riverside-high")).json()

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"
    assert before == after


def test_audit_log_records_actor_and_before_after_for_critical_mutation():
    admin_headers = _headers("mergington-high", role="admin", user_id="admin-mergington")

    mutation_response = client.patch(
        "/activities/Chess%20Club/capacity?max_participants=18",
        headers=admin_headers,
    )
    assert mutation_response.status_code == 200

    logs_response = client.get("/audit-logs", headers=admin_headers)
    assert logs_response.status_code == 200

    logs = logs_response.json()
    assert logs

    latest = logs[-1]
    assert latest["action"] == "activity_capacity_updated"
    assert latest["actor"]["user_id"] == "admin-mergington"
    assert latest["actor"]["role"] == "admin"
    assert latest["actor"]["institution_id"] == "mergington-high"
    assert latest["target"]["type"] == "activity"
    assert latest["target"]["id"] == "Chess Club"
    assert latest["before"]["max_participants"] == 12
    assert latest["after"]["max_participants"] == 18
    assert latest["timestamp"]
