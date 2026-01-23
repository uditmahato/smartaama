# backend/app/api/v1/endpoints/medical_schema.py
"""
Endpoints for medical schema metadata.
Provides frontend with structured field definitions, data types, units, and validation rules.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.medical_schema import (
    MEDICAL_SCHEMA,
    SectionDefinition,
    get_all_sections,
    get_section_definition,
    get_sections_by_category,
)

router = APIRouter()


@router.get("/sections", response_model=List[SectionDefinition])
def list_all_sections(
    category: Optional[str] = None,
    updates_only: bool = False
):
    """
    Get all medical data sections.
    
    Optional filter by category:
    - static: Patient master profile data (demographics, history)
    - obstetric: Obstetric history
    - event_based: Time-series clinical data (exams, investigations)
    
    Set updates_only=true to only get sections for clinical updates (excludes patient registration fields).
    """
    sections = get_all_sections()
    
    if category:
        if category not in ["static", "obstetric", "event_based"]:
            raise HTTPException(status_code=400, detail="Invalid category")
        sections = get_sections_by_category(category)
    
    if updates_only:
        sections = [s for s in sections if s.show_in_updates]
    
    return sections


@router.get("/sections/{section_key}", response_model=SectionDefinition)
def get_section_schema(section_key: str):
    """
    Get detailed schema for a specific section.
    Returns field definitions with data types, units, enum values, and validation rules.
    """
    section = get_section_definition(section_key)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section '{section_key}' not found")
    
    return section


@router.get("/sections/{section_key}/fields")
def get_section_fields(section_key: str):
    """
    Get simplified field list for a section (useful for quick reference).
    """
    section = get_section_definition(section_key)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section '{section_key}' not found")
    
    return {
        "section_key": section.section_key,
        "section_label": section.section_label,
        "category": section.category,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "type": f.field_type,
                "unit": f.unit,
                "required": not f.nullable,
            }
            for f in section.fields
        ],
    }
