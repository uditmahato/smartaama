// frontend/src/services/types.ts
// Shared API response types (mirrors the backend Pydantic schemas).

export type UserRole = "admin" | "clinician" | "hospital" | "viewer" | string;

/** `UserOut` — returned by /auth/me, /admin/users, /admin/users/pending, /admin/users/rejected, /auth/register. */
export type UserOut = {
  id: string;
  username: string;
  email?: string | null;
  full_name?: string | null;
  phone_number?: string | null;
  nmc_number?: string | null;
  working_hospital?: string | null;
  facility_type?: string | null;
  facility_id?: string | null;
  facility_name?: string | null;
  role: UserRole;
  is_super_admin?: boolean;
  is_active: boolean;
  is_approved: boolean;
  approved_at?: string | null;
  /** Set when an admin rejected the registration (see /admin/users/rejected). */
  rejected_at?: string | null;
  created_at?: string;
  has_id_card?: boolean;
};

/** Minimal user shape cached in localStorage and used across pages. */
export type UserInfo = UserOut;

export type ReferralStatus =
  | "draft"
  | "submitted"
  | "received"
  | "closed"
  | "cancelled";

export type ReferralOut = {
  id: string;
  patient_id: string;
  created_by_user_id?: string | null;
  from_facility: string;
  to_facility: string;
  status: ReferralStatus;
  received_facility_status?: ReferralStatus | null;
  reason: string;
  reason_codes?: string[] | null;
  clinician_decision?: string | null;
  clinician_note?: string | null;
  submitted_at?: string | null;
  received_at?: string | null;
  closed_at?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type ReferralHistoryKind =
  | "created"
  | "status"
  | "received_status"
  | "decision";

/** `ReferralHistoryOut` — rows from GET /referrals/{id}/history. */
export type ReferralHistoryOut = {
  id: string;
  referral_id: string;
  kind: ReferralHistoryKind;
  from_status?: string | null;
  to_status?: string | null;
  note?: string | null;
  actor_user_id?: string | null;
  actor_name?: string | null;
  created_at: string;
};

export type FacilityKind = "phc" | "hospital";

export type FacilityOption = {
  id: string;
  name: string;
  kind: FacilityKind;
};

// ---- Advisory (rule-based) analysis ---------------------------------------

export type AdvisorySummary = {
  summary: string;
  key_findings: string[];
  risk_level?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type DetectedRisk = {
  name: string;
  weight: number;
  value: string;
};

export type RiskFactors = {
  detected_risks?: DetectedRisk[];
  confidence_calculation?: string;
  data_points_analyzed?: number;
  [key: string]: unknown;
};

export type ReferralRecommendation = {
  referral_needed: boolean;
  urgency: string;
  confidence: number;
  reasons: string[];
  recommended_facility?: string | null;
  recommended_specialties?: string[];
  risk_factors: RiskFactors;
  clinical_indicators?: Record<string, unknown>;
  estimated_distance_km?: number | null;
};

/** GET /ai-analysis/patients/{id}/analysis */
export type AdvisoryAnalysis = {
  patient_id: string;
  summary?: AdvisorySummary | null;
  referral_recommendation?: ReferralRecommendation | null;
  last_analyzed_at: string;
  data_version: number;
  model_used?: string | null;
};
