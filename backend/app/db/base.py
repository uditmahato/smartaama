# backend/app/db/base.py
#
# Importing this module registers every ORM model on Base.metadata (there is no
# app/models/__init__.py, so `import app.models` alone does NOT load the models).
# Use `from app.db.base import Base` wherever you need the full metadata (init_db, Alembic env,
# tests, scripts).

from app.models.base import Base  # noqa: F401

from app.models.facility import Facility  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.clinical_event import ClinicalEvent  # noqa: F401
from app.models.referral import Referral  # noqa: F401
from app.models.referral_status_history import ReferralStatusHistory  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.ai_patient_analysis import AIPatientAnalysis  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.rate_limit import AuthRateLimitHit  # noqa: F401
