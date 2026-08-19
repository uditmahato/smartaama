# backend/app/api/v1/endpoints/facilities.py
"""
Public facility directory (unified `facilities` table).

    GET /facilities?kind=phc|hospital&q=<substring>

Used by the signup / bootstrap forms and by referral forms to pick a facility. Items are
`{id, name, kind}`; `id` is what registration sends back as `facility_id`, `name` is what
referral / patient payloads send (names are resolved server-side to the same ids).
"""

from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.facility import Facility

router = APIRouter(prefix="/facilities", tags=["Facilities"])


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: Literal["phc", "hospital"]


@router.get("", response_model=List[FacilityOut])
def list_facilities(
    kind: Optional[Literal["phc", "hospital"]] = Query(None, description="Facility type to list (omit for all)"),
    q: Optional[str] = Query(None, max_length=255, description="Optional case-insensitive name filter"),
    db: Session = Depends(get_db),
) -> List[Facility]:
    stmt = select(Facility)
    if kind:
        stmt = stmt.where(Facility.kind == kind)
    if q and q.strip():
        stmt = stmt.where(Facility.name.ilike(f"%{q.strip()}%"))
    stmt = stmt.order_by(Facility.kind.asc(), Facility.name.asc())
    return list(db.execute(stmt).scalars().all())
