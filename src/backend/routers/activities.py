"""
Endpoints for the High School Management System API
"""


from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..database import activities_collection, teachers_collection, announcements_collection


router = APIRouter(
    prefix="/activities",
    tags=["activities"]
)


# --- Activities listing endpoint ---
@router.get("", response_model=Dict[str, Any])
def list_activities(
    day: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Return all activities as a mapping of name -> details.

    Supports optional filtering by day and by a start/end time range.
    The time comparison expects HH:MM strings (24-hour) which matches the
    seeded `schedule_details.start_time`/`end_time` format.
    """
    results: Dict[str, Any] = {}

    for a in activities_collection.find({}):
        name = a.get("_id") or a.get("name")
        details = {k: v for k, v in a.items() if k != "_id"}

        # Filter by day if requested
        if day:
            sd = a.get("schedule_details") or {}
            days = sd.get("days", [])
            if day not in days:
                continue

        # Filter by start/end time if requested
        if start_time and end_time:
            sd = a.get("schedule_details")
            if not sd:
                continue
            s = sd.get("start_time")
            e = sd.get("end_time")
            if not s or not e:
                continue
            # Simple lexicographic compare works for HH:MM format
            if s < start_time or e > end_time:
                continue

        results[name] = details

    return results

# --- Announcement Endpoints ---
def is_authenticated(username: str) -> bool:
    teacher = teachers_collection.find_one({"_id": username})
    return teacher is not None

@router.get("/announcements", response_model=List[Dict[str, Any]])
def get_announcements() -> List[Dict[str, Any]]:
    """Get all announcements (active and expired)"""
    return [
        {**a, "_id": str(a.get("_id", ""))}
        for a in announcements_collection.find({})
    ]

@router.post("/announcements", response_model=Dict[str, Any])
def create_announcement(
    username: str = Body(...),
    message: str = Body(...),
    expiration_date: str = Body(...),
    start_date: str = Body(None)
) -> Dict[str, Any]:
    """Create a new announcement (signed-in users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    if not message or not expiration_date:
        raise HTTPException(status_code=400, detail="Message and expiration date required")
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
    doc = {"message": message, "expiration_date": expiration_date}
    if start_date:
        doc["start_date"] = start_date
    result = announcements_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@router.put("/announcements/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    username: str = Body(...),
    message: str = Body(...),
    expiration_date: str = Body(...),
    start_date: str = Body(None)
) -> Dict[str, Any]:
    """Update an announcement (signed-in users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        exp = datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
    update_doc = {"message": message, "expiration_date": expiration_date}
    if start_date:
        update_doc["start_date"] = start_date
    result = announcements_collection.update_one({"_id": announcement_id}, {"$set": update_doc})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    doc = announcements_collection.find_one({"_id": announcement_id})
    doc["_id"] = str(doc["_id"])
    return doc

@router.delete("/announcements/{announcement_id}", response_model=Dict[str, Any])
def delete_announcement(
    announcement_id: str,
    username: str = Body(...)
) -> Dict[str, Any]:
    """Delete an announcement (signed-in users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"_id": announcement_id, "deleted": True}


@router.get("/days", response_model=List[str])
def get_available_days() -> List[str]:
    """Get a list of all days that have activities scheduled"""
    # Aggregate to get unique days across all activities
    pipeline = [
        {"$unwind": "$schedule_details.days"},
        {"$group": {"_id": "$schedule_details.days"}},
        {"$sort": {"_id": 1}}  # Sort days alphabetically
    ]

    days = []
    for day_doc in activities_collection.aggregate(pipeline):
        days.append(day_doc["_id"])

    return days


@router.post("/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, teacher_username: Optional[str] = Query(None)):
    """Sign up a student for an activity - requires teacher authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Get the activity
    activity = activities_collection.find_one({"_id": activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400, detail="Already signed up for this activity")

    # Add student to participants
    result = activities_collection.update_one(
        {"_id": activity_name},
        {"$push": {"participants": email}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update activity")

    return {"message": f"Signed up {email} for {activity_name}"}


@router.post("/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, teacher_username: Optional[str] = Query(None)):
    """Remove a student from an activity - requires teacher authentication"""
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Get the activity
    activity = activities_collection.find_one({"_id": activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400, detail="Not registered for this activity")

    # Remove student from participants
    result = activities_collection.update_one(
        {"_id": activity_name},
        {"$pull": {"participants": email}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update activity")

    return {"message": f"Unregistered {email} from {activity_name}"}
