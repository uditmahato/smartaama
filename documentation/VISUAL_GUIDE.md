# SmartAAMA Permission System - Visual Guide

## 🎯 Permission Matrix

```
┌─────────────────────────────────────────────────────────────┐
│                    PERMISSION MATRIX                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Referral: PHC Hospital → Hospital XYZ                       │
│                                                               │
│  User from PHC Hospital:                                      │
│  ├─ View Patient Profile        ✅ YES                       │
│  ├─ Edit Patient Vitals         ✅ YES                       │
│  ├─ Edit Medical Records        ✅ YES                       │
│  ├─ Update Referral Status      ✅ YES                       │
│  └─ Add Notes to Status         ✅ YES                       │
│                                                               │
│  User from Hospital XYZ:                                      │
│  ├─ View Patient Profile        ✅ YES                       │
│  ├─ Edit Patient Vitals         ❌ NO                        │
│  ├─ Edit Medical Records        ❌ NO                        │
│  ├─ Update Referral Status      ✅ YES                       │
│  └─ Add Notes to Status         ✅ YES                       │
│                                                               │
│  User from Other Facility:                                    │
│  ├─ View Patient Profile        ❌ NO                        │
│  ├─ See Referral at all         ❌ NO                        │
│  └─ Access API Endpoints        ❌ NO                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 📊 User Journey Map

### PHC Clinician's Journey
```
┌──────────────┐
│  Log In      │
└──────┬───────┘
       │ (credentials)
       ▼
┌──────────────────────────────────┐
│ Dashboard - View Referrals       │
│ ├─ Referrals I created (blue)    │
│ └─ Referrals to me (green)       │
└──────┬───────────────────────────┘
       │
       ├─── Click "Create Referral" ──────┐
       │                                    │
       ▼                                    ▼
┌────────────────┐          ┌──────────────────────┐
│ Select Patient │          │ Refer to Hospital    │
└────┬───────────┘          │ - Enter reason       │
     │                       │ - Add notes          │
     └──────────┬────────────┤ - Click Create       │
                │            └──────────┬──────────┘
                ▼                       │
         ┌────────────────┐            │
         │ Patient Profile│◄───────────┘
         │ ├─ Edit button ✅           │
         │ ├─ Update vitals ✅         │ (Referring facility)
         │ └─ Referral history         │
         └────────────────┘            │
                                       ▼
                                 [Referral Created]
                                       │
                                       └──> Hospital sees
                                            in dashboard
```

### Hospital Clinician's Journey
```
┌──────────────┐
│  Log In      │
└──────┬───────┘
       │ (credentials)
       ▼
┌──────────────────────────────────┐
│ Dashboard - View Referrals       │
│ ├─ Referrals I received (green)  │
│ └─ (No creation rights to PHC)   │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Click Referral from PHC          │
└──────┬───────────────────────────┘
       │
       ▼
┌────────────────────────────────────────┐
│ Patient Profile                        │
│ [⚠️ READ-ONLY - Receiving Facility]    │
│ ├─ View All Data ✅                    │
│ ├─ Edit button  ❌ HIDDEN              │
│ └─ Update Referral Status ✅           │
└──────┬─────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Referral Details                 │
│ ├─ Status: Referred to Here      │
│ ├─ Note: "Patient admitted..."   │
│ └─ Submit                        │
└──────┬───────────────────────────┘
       │
       ▼
[Update sent back to PHC]
```

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LOGIN                            │
│                                                               │
│  Frontend POST /auth/login                                   │
│         ↓ (username, password)                              │
│  Backend validates credentials                              │
│         ↓                                                    │
│  Backend creates JWT with:                                  │
│    - user_id                                                 │
│    - facility_name ◄──────── KEY!                            │
│    - role                                                    │
│         ↓                                                    │
│  Frontend stores token (localStorage)                       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    VIEW PATIENT PROFILE                      │
│                                                               │
│  Frontend GET /auth/me                                      │
│         ↓ (token)                                            │
│  Backend returns user with facility_name                    │
│         ↓ (cache in userStore)                              │
│  Frontend GET /referrals?patient_id=X                       │
│         ↓ (token with facility_name)                        │
│  Backend automatically filters:                             │
│    WHERE from_facility = 'User Facility'                    │
│       OR to_facility = 'User Facility'                      │
│         ↓                                                    │
│  Frontend receives list of filtered referrals               │
│         ↓                                                    │
│  Frontend calculates permissions:                           │
│    isReceiving = any referral.to_facility == userFacility   │
│    isReferring = any referral.from_facility == userFacility │
│    canEdit = !isReceiving OR isReferring                    │
│         ↓                                                    │
│  Frontend renders UI based on canEdit:                      │
│    if (canEdit) show <Edit Button>                          │
│    if (!canEdit) show <Read-Only Alert>                     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              UPDATE REFERRAL STATUS WITH NOTE               │
│                                                               │
│  Frontend POST /referrals/{id}/status                       │
│    {                                                         │
│      status: "received",                                    │
│      note: "Patient stabilized"                             │
│    }                                                         │
│         ↓ (token with user_id, facility_name)              │
│  Backend service.transition_status():                       │
│    - Validates status transition rules                      │
│    - Appends note with timestamp:                           │
│      "[2026-01-25 10:30 UTC] Status: received"             │
│      "Patient stabilized"                                   │
│    - Saves to clinician_note field                          │
│    - Creates audit log entry                                │
│         ↓                                                    │
│  Backend returns updated referral                           │
│         ↓                                                    │
│  Frontend displays new status                               │
│  Frontend clears note field                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 UI State Transitions

```
PATIENT PROFILE - Edit Button State

┌─────────────────────────────────────────┐
│ Load Patient & Referrals                │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
    No Referrals    Has Referrals
        │                 │
        │          ┌──────┴──────┐
        │          ▼             ▼
        │      I'm Referring  I'm Receiving
        │      (from_facility) (to_facility)
        │          │             │
        │          ▼             ▼
        │        canEdit=✅    canEdit=❌
        │          │             │
        └──────────┼─────────────┘
                   ▼
        ┌──────────────────────┐
        │ Render JSX:          │
        │ {canEdit && (        │
        │   <Edit Button />    │
        │ )}                   │
        │ {!canEdit && (       │
        │   <Alert />          │
        │ )}                   │
        └──────────────────────┘
```

## 📋 API Request/Response Examples

### GET /referrals - Automatic Filtering

**Frontend Request:**
```http
GET /referrals?patient_id=abc123
Authorization: Bearer eyJ...
```

**Backend Processing:**
```python
user.facility_name = "PHC Hospital"
queries = [
  SELECT * FROM referrals WHERE from_facility='PHC Hospital' AND patient_id='abc123',
  SELECT * FROM referrals WHERE to_facility='PHC Hospital' AND patient_id='abc123'
]
# Combine and deduplicate
```

**Frontend Response:**
```json
[
  {
    "id": "ref1",
    "from_facility": "PHC Hospital",
    "to_facility": "Hospital XYZ",
    "status": "submitted",
    "received_facility_status": null
  }
]
```

### POST /referrals/{id}/status - Status Update with Note

**Frontend Request:**
```http
POST /referrals/ref1/status
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "status": "received",
  "note": "Patient has been assessed"
}
```

**Backend Processing:**
```python
timestamp = "2026-01-25 10:30 UTC"
old_note = referral.clinician_note or ""
new_note = f"[{timestamp}] Status: received\nPatient has been assessed"
combined = f"{old_note}\n{new_note}".strip()
referral.clinician_note = combined
db.commit()
```

**Frontend Response:**
```json
{
  "id": "ref1",
  "status": "submitted",
  "received_facility_status": "received",
  "clinician_note": "[2026-01-25 10:30 UTC] Status: received\nPatient has been assessed"
}
```

## 🔐 Security Layers

```
┌────────────────────────────────────────────────────────────┐
│            SECURITY - DEFENSE IN DEPTH                      │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: Frontend Permission Check                         │
│  ├─ Load user facility via /auth/me                        │
│  ├─ Calculate canEdit based on referral relationships      │
│  └─ Conditionally render UI (UX purpose)                   │
│      ⚠️ NOT for security - can be bypassed                 │
│                                                              │
│  Layer 2: API Authentication                                │
│  ├─ Validate JWT token signature                           │
│  ├─ Extract user_id, facility_name from token             │
│  └─ Reject if token missing or invalid                     │
│                                                              │
│  Layer 3: API Authorization                                 │
│  ├─ Check user.facility_name in resource                   │
│  ├─ For referral: verify in [from_facility, to_facility]  │
│  ├─ For patient: verify has referral with user facility    │
│  └─ Reject if permission denied (403)                      │
│                                                              │
│  Layer 4: Audit Logging                                     │
│  ├─ Log all permission checks                              │
│  ├─ Log all denied access attempts                         │
│  ├─ Store user_id, timestamp, IP address                   │
│  └─ Enable forensic analysis                               │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

## 📱 Responsive UI Layout

```
DESKTOP VIEW (> 768px)
┌─────────────────────────────────────────┐
│  Patient Profile                        │
├─────────────────────────────────────────┤
│  [Edit] [Refer] [Back]                  │
│                                          │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ Patient Info │  │ Referral        │ │
│  │              │  │ History (Table) │ │
│  │              │  │                 │ │
│  └──────────────┘  └─────────────────┘ │
│                                          │
│  [Clinical Events Timeline]             │
└─────────────────────────────────────────┘

MOBILE VIEW (< 768px)
┌──────────────────────────────┐
│  Patient Profile             │
├──────────────────────────────┤
│  [Edit]                      │
│  [Refer]                     │
│  [Back]                      │
│                              │
│  Patient Info                │
│                              │
│  [View Referral History]     │
│  (Drawer when clicked)       │
│                              │
│  Clinical Events Timeline    │
└──────────────────────────────┘
```

## ⏱️ State Timeline

```
REFERRAL LIFECYCLE

┌─────────┐      ┌──────────┐      ┌───────────────┐
│ DRAFT   │─────▶│SUBMITTED │─────▶│ RECEIVED      │
└─────────┘      └──────────┘      └───────┬───────┘
                                            │
                          ┌─────────────────┼──────────────┐
                          ▼                 ▼              ▼
                     ┌─────────┐     ┌──────────┐    ┌──────────┐
                     │ CLOSED  │     │CANCELLED │    │ Refer    │
                     └─────────┘     │(Admitted)│    │Back to   │
                                     └──────────┘    │Original  │
                                                     └──────────┘

Status meanings:
- DRAFT: Initial unsaved state
- SUBMITTED: PHC has referred to Hospital
- RECEIVED: Hospital has acknowledged receipt
- CLOSED: Patient discharged/case resolved
- CANCELLED: Admission elsewhere/declined
```

## 🎯 Testing Matrix

```
┌────────────────────────────────────────────────────────┐
│           TEST SCENARIOS MATRIX                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│ Scenario │ PHC Actor │ Hospital Actor │ Expected      │
│          │ Can Do    │ Can Do         │ Outcome       │
│──────────┼───────────┼────────────────┼───────────────│
│ 1. PHC   │ Create ✅ │ See ✅        │ Both see      │
│   Refers │ Edit ✅   │ Edit ❌        │ in dashboard  │
│──────────┼───────────┼────────────────┼───────────────│
│ 2. Hosp  │ See ✅    │ Update ✅     │ PHC sees      │
│   Update │ Edit ❌   │ Note ✅        │ hospital's    │
│ Status   │           │                │ update        │
│──────────┼───────────┼────────────────┼───────────────│
│ 3. Hosp  │ Refer ✅  │ Refer ✅      │ Bidirectional│
│   Refers │ Edit ✅   │ Edit ✅        │ communication│
│   Back   │           │                │              │
│──────────┼───────────┼────────────────┼───────────────│
│ 4. 3rd   │ See ❌    │ See ❌        │ Data isolation│
│   Facility           │                │ verified     │
│──────────┴───────────┴────────────────┴───────────────│
│
└────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Flow

```
┌──────────────────────────────────────────────┐
│           DEPLOYMENT CHECKLIST                │
├──────────────────────────────────────────────┤
│                                               │
│  1. Database Migration                       │
│     $ python -m app.db.init_db               │
│     ↓ Adds received_facility_status column   │
│                                               │
│  2. Backend Restart                          │
│     $ python -m app.main                     │
│     ↓ Loads new env variables                │
│                                               │
│  3. Frontend Build                           │
│     $ npm run build                          │
│     ↓ Compiles TypeScript & React            │
│                                               │
│  4. Frontend Deploy                          │
│     Copy dist/ to web server                 │
│     ↓ Serves new version                     │
│                                               │
│  5. Verification Tests                       │
│     ✓ Login works                            │
│     ✓ Referrals filtered                     │
│     ✓ Permissions enforced                   │
│     ✓ Timestamps working                     │
│                                               │
└──────────────────────────────────────────────┘
```

---

**This visual guide complements the detailed documentation files. For specific implementation details, refer to:**
- PERMISSION_SYSTEM_IMPLEMENTATION.md (technical)
- QUICK_REFERENCE.md (code examples)
- TESTING_GUIDE.md (testing procedures)
