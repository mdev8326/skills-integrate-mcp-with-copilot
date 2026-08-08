"""High School Management System API with tenant isolation foundations."""

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from typing import Any

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

ROLE_PRECEDENCE = {
    "guardian": 1,
    "teacher": 2,
    "admin": 3,
    "superadmin": 4,
}

INSTITUTIONS = {
    "mergington-high": {
        "id": "mergington-high",
        "name": "Mergington High School",
    },
    "riverside-high": {
        "id": "riverside-high",
        "name": "Riverside High School",
    },
}

audit_logs: list[dict[str, Any]] = []

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
        "institution_id": "mergington-high",
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
        "institution_id": "riverside-high",
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
        "institution_id": "riverside-high",
    }
}


def get_user_context(
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
) -> dict[str, str]:
    institution_id = x_institution_id.strip().lower()
    user_role = x_user_role.strip().lower()
    user_id = x_user_id.strip().lower()

    if institution_id not in INSTITUTIONS:
        raise HTTPException(status_code=400, detail="Unknown institution")
    if user_role not in ROLE_PRECEDENCE:
        raise HTTPException(status_code=400, detail="Unknown role")
    if not user_id:
        raise HTTPException(status_code=400, detail="x-user-id is required")

    return {
        "institution_id": institution_id,
        "user_id": user_id,
        "user_role": user_role,
    }


def require_role(context: dict[str, str], minimum_role: str) -> None:
    if ROLE_PRECEDENCE[context["user_role"]] < ROLE_PRECEDENCE[minimum_role]:
        raise HTTPException(status_code=403, detail="Insufficient role")


def get_institution_activity_or_404(activity_name: str, institution_id: str) -> dict[str, Any]:
    activity = activities.get(activity_name)
    if not activity or activity["institution_id"] != institution_id:
        # Return 404 either when missing or cross-tenant to avoid leaking metadata.
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


def write_audit_log(
    action: str,
    actor_id: str,
    actor_role: str,
    institution_id: str,
    target_type: str,
    target_id: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    audit_logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": {
            "user_id": actor_id,
            "role": actor_role,
            "institution_id": institution_id,
        },
        "target": {
            "type": target_type,
            "id": target_id,
        },
        "before": before,
        "after": after,
    })


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
):
    context = get_user_context(x_institution_id, x_user_id, x_user_role)
    return {
        name: details
        for name, details in activities.items()
        if details["institution_id"] == context["institution_id"]
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
):
    """Sign up a student for an activity"""
    context = get_user_context(x_institution_id, x_user_id, x_user_role)
    activity = get_institution_activity_or_404(activity_name, context["institution_id"])

    before = deepcopy(activity)

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    write_audit_log(
        action="student_signup",
        actor_id=context["user_id"],
        actor_role=context["user_role"],
        institution_id=context["institution_id"],
        target_type="activity",
        target_id=activity_name,
        before=before,
        after=deepcopy(activity),
    )
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
):
    """Unregister a student from an activity"""
    context = get_user_context(x_institution_id, x_user_id, x_user_role)
    activity = get_institution_activity_or_404(activity_name, context["institution_id"])

    before = deepcopy(activity)

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    write_audit_log(
        action="student_unregistered",
        actor_id=context["user_id"],
        actor_role=context["user_role"],
        institution_id=context["institution_id"],
        target_type="activity",
        target_id=activity_name,
        before=before,
        after=deepcopy(activity),
    )
    return {"message": f"Unregistered {email} from {activity_name}"}


@app.patch("/activities/{activity_name}/capacity")
def update_activity_capacity(
    activity_name: str,
    max_participants: int,
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
):
    context = get_user_context(x_institution_id, x_user_id, x_user_role)
    require_role(context, "admin")

    if max_participants < 1:
        raise HTTPException(status_code=400, detail="max_participants must be positive")

    activity = get_institution_activity_or_404(activity_name, context["institution_id"])
    if max_participants < len(activity["participants"]):
        raise HTTPException(
            status_code=400,
            detail="max_participants cannot be less than participant count",
        )

    before = deepcopy(activity)
    activity["max_participants"] = max_participants
    write_audit_log(
        action="activity_capacity_updated",
        actor_id=context["user_id"],
        actor_role=context["user_role"],
        institution_id=context["institution_id"],
        target_type="activity",
        target_id=activity_name,
        before=before,
        after=deepcopy(activity),
    )
    return {"message": f"Updated capacity for {activity_name}"}


@app.get("/audit-logs")
def get_audit_logs(
    x_institution_id: str = Header(default="mergington-high"),
    x_user_id: str = Header(default="anonymous"),
    x_user_role: str = Header(default="guardian"),
):
    context = get_user_context(x_institution_id, x_user_id, x_user_role)
    require_role(context, "admin")

    if context["user_role"] == "superadmin":
        return audit_logs

    return [
        entry
        for entry in audit_logs
        if entry["actor"]["institution_id"] == context["institution_id"]
    ]
