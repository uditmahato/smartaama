from typing import List, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.facility import HospitalFacility, PHCFacility

router = APIRouter(prefix="/facilities", tags=["Facilities"])


class FacilityOut(BaseModel):
    id: str
    name: str
    kind: Literal["phc", "hospital"]


@router.get("", response_model=List[FacilityOut])
def list_facilities(
    kind: Literal["phc", "hospital"] = Query(..., description="Facility type to list"),
    q: str | None = Query(None, description="Optional case-insensitive name filter"),
    db: Session = Depends(get_db),
):
    model = PHCFacility if kind == "phc" else HospitalFacility

    stmt = select(model)
    if q:
        stmt = stmt.where(model.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(model.name.asc())

    facilities = db.execute(stmt).scalars().all()
    return [{"id": str(f.id), "name": f.name, "kind": kind} for f in facilities]
