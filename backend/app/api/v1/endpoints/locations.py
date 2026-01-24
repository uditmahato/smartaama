from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.utils.nepal_locations import (
    get_provinces,
    get_districts,
    get_municipalities,
    get_wards,
)

router = APIRouter(prefix="/locations", tags=["locations"])


class MunicipalityOut(BaseModel):
    local_level_name: str
    local_level_type: str
    wards: int


@router.get("/provinces", response_model=List[str])
def get_all_provinces():
    """Get all provinces in Nepal"""
    return get_provinces()


@router.get("/districts", response_model=List[str])
def get_all_districts(province: str = Query(..., description="Province name")):
    """Get all districts for a given province"""
    return get_districts(province)


@router.get("/municipalities", response_model=List[MunicipalityOut])
def get_all_municipalities(
    province: str = Query(..., description="Province name"),
    district: str = Query(..., description="District name"),
):
    """Get all municipalities (local levels) for a given province and district"""
    return get_municipalities(province, district)


@router.get("/wards", response_model=int)
def get_all_wards(
    province: str = Query(..., description="Province name"),
    district: str = Query(..., description="District name"),
    municipality: str = Query(..., description="Municipality name"),
):
    """Get number of wards for a given municipality"""
    return get_wards(province, district, municipality)
