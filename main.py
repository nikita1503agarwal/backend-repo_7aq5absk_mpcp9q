import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Service, Availability, Booking

app = FastAPI(title="Appointments API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Appointments API running"}


@app.get("/schema")
def get_schema_index():
    return {
        "service": Service.model_json_schema(),
        "availability": Availability.model_json_schema(),
        "booking": Booking.model_json_schema(),
    }


# Utilities

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def parse_time(hhmm: str) -> datetime:
    return datetime.strptime(hhmm, "%H:%M")


# Seed minimal data if empty
@app.on_event("startup")
def seed_data():
    if db is None:
        return
    if db["service"].count_documents({}) == 0:
        create_document("service", {
            "name": "Consultation Call",
            "description": "30-min strategy session",
            "duration_minutes": 30,
            "price": 0,
            "color": "#22c55e",
            "slug": "consultation-call",
        })
    if db["availability"].count_documents({}) == 0:
        # Weekday availability Mon-Fri 09:00-17:00 UTC
        service = db["service"].find_one({})
        for weekday in range(0,5):
            create_document("availability", {
                "service_id": str(service["_id"]),
                "weekday": weekday,
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "UTC",
            })


# Services
@app.get("/api/services")
def list_services():
    services = get_documents("service")
    for s in services:
        s["_id"] = str(s["_id"])
    return services


# Availability
class FreeSlot(BaseModel):
    date: str
    start_time: str
    end_time: str


@app.get("/api/services/{service_id}/slots", response_model=List[FreeSlot])
def get_free_slots(service_id: str, days: int = 14):
    if db is None:
        raise HTTPException(500, "Database not configured")

    service = db["service"].find_one({"_id": to_object_id(service_id)})
    if not service:
        raise HTTPException(404, "Service not found")

    # Collect rule-based availability
    rules = list(db["availability"].find({"service_id": service_id}))

    # Collect existing bookings
    bookings = list(db["booking"].find({"service_id": service_id}))

    # Build a set of booked date+time ranges
    booked = {}
    for b in bookings:
        key = b["date"]
        booked.setdefault(key, []).append((b["start_time"], b["end_time"]))

    out: List[FreeSlot] = []
    today = datetime.utcnow().date()
    for i in range(days):
        day = today + timedelta(days=i)
        day_str = day.isoformat()
        weekday = day.weekday()
        # get matching rules (weekday or specific date)
        day_rules = [r for r in rules if (r.get("weekday") == weekday) or (r.get("date") == day_str)]
        for r in day_rules:
            start = parse_time(r["start_time"]).time()
            end = parse_time(r["end_time"]).time()
            # service duration
            dur = timedelta(minutes=int(service.get("duration_minutes", 30)))
            cursor = datetime.combine(day, start)
            end_dt = datetime.combine(day, end)

            while cursor + dur <= end_dt:
                slot_start = cursor.strftime("%H:%M")
                slot_end = (cursor + dur).strftime("%H:%M")
                # skip if overlaps a booking
                overlaps = any(not (slot_end <= b_start or slot_start >= b_end) for (b_start, b_end) in booked.get(day_str, []))
                if not overlaps:
                    out.append(FreeSlot(date=day_str, start_time=slot_start, end_time=slot_end))
                cursor += dur

    return out[:200]


# Bookings
@app.post("/api/bookings")
def create_booking(payload: Booking):
    if db is None:
        raise HTTPException(500, "Database not configured")

    # validate service exists
    service = db["service"].find_one({"_id": to_object_id(payload.service_id)})
    if not service:
        raise HTTPException(404, "Service not found")

    # prevent double-booking
    conflict = db["booking"].find_one({
        "service_id": payload.service_id,
        "date": payload.date,
        "$or": [
            {"start_time": {"$lt": payload.end_time}, "end_time": {"$gt": payload.start_time}}
        ]
    })
    if conflict:
        raise HTTPException(409, "Time slot already booked")

    data = payload.model_dump()
    data["service_name"] = service.get("name")
    inserted_id = create_document("booking", data)
    return {"id": inserted_id, "status": "ok"}


@app.get("/api/bookings")
def list_bookings(service_id: Optional[str] = None):
    if db is None:
        raise HTTPException(500, "Database not configured")
    q = {"service_id": service_id} if service_id else {}
    docs = list(db["booking"].find(q).sort("created_at", -1))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected & Working",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "collections": []
    }
    try:
        if db is not None:
            response["collections"] = db.list_collection_names()[:10]
    except Exception as e:
        response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
