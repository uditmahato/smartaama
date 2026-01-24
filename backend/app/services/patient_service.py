# backend/app/services/patient_service.py

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientSearchParams, PatientUpdate


class PatientService:
    @staticmethod
    def _generate_patient_id(db: Session) -> str:
        """Generate a unique patient ID in format PAT-YYYY-NNNNN"""
        current_year = datetime.now().year
        
        # Count existing patients created this year
        count = db.execute(
            select(func.count(Patient.id)).where(
                func.extract('year', Patient.created_at) == current_year
            )
        ).scalar() or 0
        
        seq_num = count + 1
        return f"PAT-{current_year}-{seq_num:05d}"

    @staticmethod
    def create_patient(db: Session, *, payload: PatientCreate, actor: User, ip: Optional[str] = None, user_agent: Optional[str] = None) -> Patient:
        patient = Patient(
            patient_id=PatientService._generate_patient_id(db),
            facility_mrn=payload.facility_mrn,
            national_id=payload.national_id,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            age_in_years=payload.age_in_years,
            sex=payload.sex,
            phone_number=payload.phone_number,
            address_line=payload.address_line,
            ward=payload.ward,
            municipality=payload.municipality,
            district=payload.district,
            province=payload.province,
        )
        db.add(patient)
        db.flush()  # assign patient.id

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="PATIENT_CREATED",
                entity_type="patient",
                entity_id=patient.id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "patient_id": patient.patient_id,
                    "facility_mrn": patient.facility_mrn,
                    "national_id": patient.national_id,
                },
            )
        )

        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_patient(db: Session, patient_id: UUID) -> Optional[Patient]:
        return db.get(Patient, patient_id)

    @staticmethod
    def update_patient(
        db: Session,
        *,
        patient: Patient,
        payload: PatientUpdate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Patient:
        """
        Controlled updates for demographic corrections only.
        Clinical history must be updated via ClinicalEvent.
        """
        before = {
            "facility_mrn": patient.facility_mrn,
            "national_id": patient.national_id,
            "first_name": patient.first_name,
            "middle_name": patient.middle_name,
            "last_name": patient.last_name,
            "age_in_years": patient.age_in_years,
            "sex": patient.sex,
            "phone_number": patient.phone_number,
            "address_line": patient.address_line,
            "ward": patient.ward,
            "municipality": patient.municipality,
            "district": patient.district,
            "province": patient.province,
        }

        # Only set fields provided (exclude None)
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            if v is not None:
                setattr(patient, k, v)

        after = {
            "facility_mrn": patient.facility_mrn,
            "national_id": patient.national_id,
            "first_name": patient.first_name,
            "middle_name": patient.middle_name,
            "last_name": patient.last_name,
            "age_in_years": patient.age_in_years,
            "sex": patient.sex,
            "phone_number": patient.phone_number,
            "address_line": patient.address_line,
            "ward": patient.ward,
            "municipality": patient.municipality,
            "district": patient.district,
            "province": patient.province,
        }

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="PATIENT_UPDATED",
                entity_type="patient",
                entity_id=patient.id,
                ip_address=ip,
                user_agent=user_agent,
                details={"before": before, "after": after},
            )
        )

        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def search_patients(db: Session, params: PatientSearchParams) -> List[Patient]:
        """
        Supports common PHC lookup: MRN, national id, phone, district, and fuzzy name search.
        """
        stmt = select(Patient)

        filters = []

        if params.facility_mrn:
            filters.append(Patient.facility_mrn.ilike(f"%{params.facility_mrn}%"))
        if params.national_id:
            filters.append(Patient.national_id.ilike(f"%{params.national_id}%"))
        if params.phone_number:
            filters.append(Patient.phone_number.ilike(f"%{params.phone_number}%"))
        if params.district:
            filters.append(Patient.district.ilike(f"%{params.district}%"))

        if params.q:
            q = params.q.strip()
            # Search across name parts and identifiers
            filters.append(
                or_(
                    Patient.first_name.ilike(f"%{q}%"),
                    Patient.middle_name.ilike(f"%{q}%"),
                    Patient.last_name.ilike(f"%{q}%"),
                    Patient.facility_mrn.ilike(f"%{q}%"),
                    Patient.national_id.ilike(f"%{q}%"),
                    Patient.phone_number.ilike(f"%{q}%"),
                    Patient.patient_id.ilike(f"%{q}%"),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Patient.created_at.desc()).limit(params.limit).offset(params.offset)

        return list(db.execute(stmt).scalars().all())
