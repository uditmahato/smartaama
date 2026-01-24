# backend/app/db/base.py

from app.models.base import Base  # noqa: F401

# Import all models so that Base.metadata is populated for Alembic
from app.models.user import User  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.clinical_event import ClinicalEvent  # noqa: F401
from app.models.referral import Referral  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.facility import PHCFacility, HospitalFacility  # noqa: F401
