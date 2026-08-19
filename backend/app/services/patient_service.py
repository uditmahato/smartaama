# backend/app/services/patient_service.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.authz import is_admin, patient_access_filter
from app.models.audit_log import AuditLog
from app.models.facility import Facility
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientSearchParams, PatientUpdate
from app.services.facility_service import resolve_facility, resolve_user_facility


class PatientServiceError(ValueError):
    """Business-rule violation surfaced to the API layer as HTTP 400."""


class PatientService:
    # How many times to retry create on a unique-constraint collision (patient_id / facility_mrn
    # are generated from a count/max query, so two concurrent creates can pick the same value).
    _CREATE_RETRIES = 5

    @staticmethod
    def _abbr(value: Optional[str]) -> str:
        """Return uppercased first three alphabetic characters; fallback to UNK."""
        if not value:
            return "UNK"
        letters = "".join(ch for ch in value.upper() if ch.isalpha())
        if not letters:
            return "UNK"
        # Pad with X to always have 3 characters for very short names
        return (letters[:3]).ljust(3, "X")

    @staticmethod
    def _generate_facility_mrn(
        db: Session,
        province: Optional[str],
        district: Optional[str],
        municipality: Optional[str],
        bump: int = 0,
    ) -> str:
        """
        Generate facility MRN with pattern:
        {PROV3}-{DIST3}-{MUNI3}-PHC-{NNN}

        Sequence is scoped per prefix to keep numbers compact per location.
        `bump` is added on retry after a uniqueness collision.
        """

        prov_code = PatientService._abbr(province)
        dist_code = PatientService._abbr(district)
        muni_code = PatientService._abbr(municipality)
        prefix = f"{prov_code}-{dist_code}-{muni_code}-PHC-"

        existing = db.execute(
            select(Patient.facility_mrn).where(Patient.facility_mrn.ilike(f"{prefix}%"))
        ).scalars().all()

        max_seq = 0
        for mrn in existing:
            if not mrn:
                continue
            suffix = mrn.replace(prefix, "", 1)
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

        return f"{prefix}{max_seq + 1 + bump:03d}"

    @staticmethod
    def _generate_patient_id(db: Session, bump: int = 0) -> str:
        """Generate a unique patient ID in format PAT-YYYY-NNNNN"""
        current_year = datetime.now(timezone.utc).year

        # Highest sequence already used this year (more robust than count() after deletions)
        prefix = f"PAT-{current_year}-"
        existing = db.execute(
            select(Patient.patient_id).where(Patient.patient_id.like(f"{prefix}%"))
        ).scalars().all()
        max_seq = 0
        for pid in existing:
            suffix = pid[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

        return f"{prefix}{max_seq + 1 + bump:05d}"

    @staticmethod
    def resolve_registered_facility(
        db: Session, actor: User, payload_name: Optional[str], payload_type: Optional[str] = None
    ) -> Facility:
        """
        Decide which facility a new patient is registered under (a real `facilities` row).
        - Non-admin: always the actor's facility (payload values ignored); 400 if the actor has
          none or it is unknown to the directory.
        - Admin: actor's facility if any, else the payload `registered_facility_name`
          (resolved case-insensitively; 400 "Unknown facility: X" if it does not exist);
          400 if neither is given.
        """
        has_actor_facility = actor.facility_id is not None or bool((actor.facility_name or "").strip())
        if has_actor_facility:
            facility = resolve_user_facility(db, actor)
            if facility is None:
                raise PatientServiceError(
                    f"Your facility '{actor.facility_name}' is not in the facility directory; "
                    "contact an administrator"
                )
            return facility
        if is_admin(actor) and payload_name:
            facility = resolve_facility(db, name=payload_name)
            if facility is None:
                raise PatientServiceError(f"Unknown facility: {payload_name}")
            return facility
        if is_admin(actor):
            raise PatientServiceError(
                "registered_facility_name is required when the admin account has no facility"
            )
        raise PatientServiceError("Your account has no facility assigned; cannot register patients")

    @staticmethod
    def create_patient(
        db: Session,
        *,
        payload: PatientCreate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Patient:
        facility = PatientService.resolve_registered_facility(
            db, actor, payload.registered_facility_name, payload.registered_facility_type
        )
        # Plain values: a retry below rolls the session back and would expire the ORM object.
        facility_id, facility_name, facility_kind = facility.id, facility.name, facility.kind
        actor_id = actor.id

        last_error: Optional[Exception] = None
        for attempt in range(PatientService._CREATE_RETRIES):
            auto_facility_mrn = PatientService._generate_facility_mrn(
                db,
                province=payload.province,
                district=payload.district,
                municipality=payload.municipality,
                bump=attempt,
            )

            patient = Patient(
                patient_id=PatientService._generate_patient_id(db, bump=attempt),
                facility_mrn=payload.facility_mrn or auto_facility_mrn,
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
                # FK is authoritative; name/type are display snapshots of the facility row.
                registered_facility_id=facility_id,
                registered_facility_name=facility_name,
                registered_facility_type=facility_kind,
                created_by_user_id=actor_id,
            )
            db.add(patient)
            try:
                db.flush()  # assign patient.id; raises IntegrityError on patient_id collision
                break
            except IntegrityError as exc:
                db.rollback()
                last_error = exc
                if payload.facility_mrn:
                    # A user-supplied MRN that collides will never succeed on retry.
                    raise PatientServiceError("A patient with this facility MRN already exists") from exc
                continue
        else:
            raise PatientServiceError("Could not allocate a unique patient ID; please retry") from last_error

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
                    "registered_facility_id": str(patient.registered_facility_id),
                    "registered_facility_name": patient.registered_facility_name,
                },
            )
        )

        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_patient(db: Session, patient_id: UUID) -> Optional[Patient]:
        return db.get(Patient, patient_id)

    _AUDITED_FIELDS = (
        "facility_mrn",
        "national_id",
        "first_name",
        "middle_name",
        "last_name",
        "age_in_years",
        "sex",
        "phone_number",
        "address_line",
        "ward",
        "municipality",
        "district",
        "province",
        "registered_facility_id",
        "registered_facility_name",
        "registered_facility_type",
    )

    @staticmethod
    def _snapshot(patient: Patient) -> dict:
        """JSON-safe copy of the audited fields (UUIDs as strings)."""
        out = {}
        for k in PatientService._AUDITED_FIELDS:
            v = getattr(patient, k)
            out[k] = str(v) if isinstance(v, UUID) else v
        return out

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
        Only admins may re-home a patient: `registered_facility_name` is resolved against the
        facility directory (400 "Unknown facility: X" otherwise) and sets the FK + snapshots;
        `registered_facility_type` on its own is ignored (it always mirrors the facility's kind).
        """
        before = PatientService._snapshot(patient)

        # Only set fields provided (exclude None) and prevent MRN / patient_id changes.
        # Facility columns are handled explicitly below (never via setattr).
        exclude = {"facility_mrn", "patient_id", "registered_facility_name", "registered_facility_type"}
        data = payload.model_dump(exclude_unset=True, exclude=exclude)
        for k, v in data.items():
            if v is not None:
                setattr(patient, k, v)

        new_facility_name = payload.registered_facility_name if "registered_facility_name" in payload.model_fields_set else None
        if is_admin(actor) and new_facility_name:
            facility = resolve_facility(db, name=new_facility_name)
            if facility is None:
                raise PatientServiceError(f"Unknown facility: {new_facility_name}")
            patient.registered_facility_id = facility.id
            patient.registered_facility_name = facility.name
            patient.registered_facility_type = facility.kind

        after = PatientService._snapshot(patient)

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
    def search_patients(db: Session, params: PatientSearchParams, *, user: User) -> List[Patient]:
        """
        Supports common PHC lookup: MRN, national id, phone, district, and fuzzy name search.
        Results are always scoped to the patients `user` may access (facility / referral link).
        """
        stmt = select(Patient).where(patient_access_filter(user))

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
