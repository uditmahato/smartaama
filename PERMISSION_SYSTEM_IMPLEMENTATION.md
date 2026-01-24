# Permission System Implementation - Facility-Based Access Control

## Overview
This document describes the complete implementation of a facility-based permission system for the SmartAAMA patient referral management platform. The system ensures that receiving facilities can view all patient data but can only update referral status with notes, while referring facilities have full editing access.

## Architecture

### Permission Model
- **User Association**: Each user belongs to a facility (identified by `facility_name`)
- **Referral Relationships**: Each referral has:
  - `from_facility`: The referring facility
  - `to_facility`: The receiving facility
  - `status`: Referring facility's status
  - `received_facility_status`: Receiving facility's status

### Access Rules
1. **Visibility**: Users can only see referrals where their facility is:
   - The referring facility (from_facility)
   - The receiving facility (to_facility)

2. **Referring Facility** (from_facility):
   - Can CREATE new referrals
   - Can VIEW patient full details
   - Can EDIT patient vitals and medical records
   - Can UPDATE referral status

3. **Receiving Facility** (to_facility):
   - Can VIEW patient full details
   - Cannot EDIT patient vitals or medical records
   - Can UPDATE referral status with notes
   - Can update `received_facility_status` separately

## Backend Implementation

### Database Schema
**Referral Model** (`backend/app/models/referral.py`):
```python
- id: UUID (primary key)
- patient_id: UUID (foreign key)
- from_facility: str
- to_facility: str
- status: ReferralStatus enum
- received_facility_status: ReferralStatus enum (nullable)
- reason: str
- clinician_note: str (includes timestamped status notes)
- clinician_decision: str (nullable)
- created_at: datetime
```

### API Endpoints

#### 1. Referral Listing (GET /referrals)
**Endpoint**: `backend/app/api/v1/endpoints/referrals.py:list_referrals()`

**Behavior**:
- Automatically filters referrals to only show those where user's facility is involved
- When no facility filters provided, queries for:
  - Referrals where `from_facility == user.facility_name`
  - Referrals where `to_facility == user.facility_name`
- Deduplicates and returns combined results sorted by creation date (newest first)

**Code Example**:
```python
if user_facility and not from_facility and not to_facility:
    # Show referrals where user's facility is either sender or receiver
    query1 = ReferralQuery(from_facility=user_facility, ...)
    query2 = ReferralQuery(to_facility=user_facility, ...)
    results1 = ReferralService.list_referrals(db, query1)
    results2 = ReferralService.list_referrals(db, query2)
```

#### 2. Update Referral Status (POST /referrals/{id}/status)
**Endpoint**: `backend/app/api/v1/endpoints/referrals.py:update_referral_status()`

**Request Body**:
```json
{
  "status": "submitted|received|closed|cancelled",
  "note": "Optional status update note"
}
```

**Backend Processing** (`backend/app/services/referral_service.py:transition_status()`):
- Validates status transition rules
- Appends timestamped notes to `clinician_note` field:
  ```
  [2026-01-25 10:30 UTC] Status: received
  Patient improving with treatment
  ```
- Records audit log for all changes

#### 3. Get Current User (GET /auth/me)
**Endpoint**: `backend/app/api/v1/endpoints/auth.py:me()`

**Response**:
```json
{
  "id": "user-uuid",
  "username": "username",
  "full_name": "User Full Name",
  "role": "admin|clinician",
  "is_active": true,
  "facility_type": "phc|hospital",
  "facility_id": "facility-uuid",
  "facility_name": "Facility Name"
}
```

## Frontend Implementation

### Patient Profile Page (`frontend/src/pages/PatientProfile.tsx`)

#### New State Variables
```typescript
const [userFacility, setUserFacility] = useState<string | null>(null);
const [canEdit, setCanEdit] = useState<boolean>(true);
const [referrals, setReferrals] = useState<any[]>([]);
```

#### Permission Calculation Logic
In the `load()` function:
1. Fetch user facility via `/auth/me`
2. Load referrals for patient via `/referrals`
3. Determine if user is receiving facility only:
   ```typescript
   const isReceivingFacility = r.data.some((ref: any) => ref.to_facility === userFacilityName);
   const isReferringFacility = r.data.some((ref: any) => ref.from_facility === userFacilityName);
   
   // Can edit only if they are the referring facility
   setCanEdit(!isReceivingFacility || isReferringFacility || r.data.length === 0);
   ```

#### Conditional UI Rendering
```typescript
{!canEdit && patient && (
  <Alert severity="info">
    <strong>Read-Only Access:</strong> You are viewing this patient's record as a receiving facility. 
    You can view all information and update referral status, but cannot edit patient vitals or medical records.
  </Alert>
)}

{canEdit && (
  <Button onClick={() => navigate(`/patients/${patientId}/update`)}>
    Update Record
  </Button>
)}
```

#### Referral History Display
- Displays all referrals for the patient
- Shows timestamps, facilities involved, and status
- Clicking on a referral row navigates to detailed view

### Referral Detail Page (`frontend/src/pages/Referral.tsx`)

#### New State Variables
```typescript
const [statusUpdateNote, setStatusUpdateNote] = useState("");
const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
```

#### Status Update Function
```typescript
async function setStatus(status: ReferralOut["status"]) {
  try {
    const resp = await api.post(`/referrals/${referral.id}/status`, { 
      status,
      note: statusUpdateNote.trim() || undefined
    });
    setReferral(resp.data);
    setStatusUpdateNote("");
  } catch (err: any) {
    setError(err?.response?.data?.detail ?? "Failed to update status");
  }
}
```

#### UI Components
- **Status Dropdown**: Dropdown to select new status
- **Note Field**: Textarea to add optional notes (appears alongside status dropdown)
- **Status Display**: Shows both referring facility status and receiving facility status
- **Referral Details**: Displays reason, clinician notes, facility information

### Dashboard Page (`frontend/src/pages/Dashboard.tsx`)

#### Status Label Mapping
```typescript
const getStatusChip = (status: string) => {
  switch (status) {
    case "submitted":
      return { color: "warning", label: "Referred from Here" };
    case "received":
      return { color: "success", label: "Referred to Here" };
    case "closed":
      return { color: "default", label: "Closed Case" };
    case "cancelled":
      return { color: "success", label: "Admitted Case" };
    default:
      return { color: "default", label: "Closed Case" };
  }
};
```

## Data Flow Diagram

```
User Login
├── Frontend: /login (POST)
└── Backend: Creates JWT token with user info

User Views Dashboard
├── Frontend: GET /referrals (filtered by facility)
├── Backend: Returns only referrals where user.facility_name is from_facility or to_facility
└── Frontend: Displays referral cards with status chips

User Clicks on Patient
├── Frontend: GET /patients/{id}
├── Frontend: GET /auth/me (to determine edit permissions)
├── Frontend: GET /referrals?patient_id={id}
├── Backend: Returns all referrals for patient involving user's facility
└── Frontend: Shows read-only alert if user is receiving facility only

User Updates Referral Status
├── Frontend: POST /referrals/{id}/status with status and note
├── Backend: Appends timestamped note to clinician_note
├── Backend: Records audit log
└── Frontend: Updates display with new status

User Tries to Edit Patient (Receiving Facility)
├── Frontend: Hides "Update Record" button based on canEdit state
├── If user clicks "Update Record" link directly:
│  └── Backend: Should check permissions and reject edit
└── Frontend: Notifies user of read-only access
```

## Testing Checklist

### Scenario 1: Referring Facility (PHC) Refers Patient to Hospital
- [ ] PHC user logs in
- [ ] PHC user creates referral
- [ ] Frontend shows "Update Record" button (canEdit = true)
- [ ] Frontend shows "Refer Patient" button
- [ ] PHC user can view patient vitals and clinical events

### Scenario 2: Hospital (Receiving Facility) Receives Referral
- [ ] Hospital user logs in
- [ ] Hospital sees referral in dashboard
- [ ] Hospital clicks patient profile
- [ ] Frontend shows read-only alert
- [ ] Frontend hides "Update Record" button (canEdit = false)
- [ ] Hospital can click on referral to update status with notes
- [ ] Hospital can add timestamped notes when updating status

### Scenario 3: PHC Sees Hospital's Status Update
- [ ] PHC views referral details
- [ ] PHC sees received_facility_status updated
- [ ] PHC sees hospital's notes in clinician_note field

### Scenario 4: Facility Permissions Boundary
- [ ] User from Facility A cannot see referrals not involving Facility A
- [ ] User from Facility B cannot edit patient if not the referring facility
- [ ] User cannot access API endpoints with fake patient IDs (backend auth)

## Configuration Files Modified

### Backend
1. **`backend/app/models/referral.py`**
   - Added `received_facility_status` field

2. **`backend/app/schemas/referral.py`**
   - Added `note` field to `ReferralStatusUpdate`
   - Added `note` field to `ReceivedFacilityStatusUpdate`

3. **`backend/app/services/referral_service.py`**
   - Updated `transition_status()` to accept and append notes
   - Updated `update_received_facility_status()` to accept and append notes
   - Added note formatting with timestamp

4. **`backend/app/api/v1/endpoints/referrals.py`**
   - Updated `list_referrals()` with facility filtering logic
   - Updated `update_referral_status()` to pass note parameter

5. **`backend/app/db/init_db.py`**
   - Added `_ensure_referral_received_status_column()` migration

### Frontend
1. **`frontend/src/pages/PatientProfile.tsx`**
   - Added `userFacility` state
   - Added `canEdit` state
   - Updated `load()` function to fetch user facility and calculate permissions
   - Added conditional "Update Record" button rendering
   - Added read-only access alert
   - Added referral history loading and display

2. **`frontend/src/pages/Referral.tsx`**
   - Added `statusUpdateNote` state
   - Added `isUpdatingStatus` state
   - Updated `setStatus()` to include note parameter
   - Added note textarea in status update section

3. **`frontend/src/pages/Dashboard.tsx`**
   - Updated status label mapping

## Environment Variables

### Backend (.env)
- `CORS_ORIGINS`: Include all frontend ports (5173, 5174, 5175)
- `DATABASE_URL`: PostgreSQL connection
- `JWT_SECRET_KEY`: JWT signing key
- `BOOTSTRAP_TOKEN`: For initial admin creation

### Frontend (.env)
- `VITE_API_BASE_URL`: Backend API URL
- `VITE_BOOTSTRAP_TOKEN`: Token for bootstrap endpoint

## Deployment Notes

1. **Database Migration**: Run `python -m app.db.init_db` to ensure schema updates
2. **Environment Setup**: Ensure all .env files are properly configured
3. **Backend Restart**: Restart backend after environment variable changes
4. **CORS Configuration**: Verify CORS_ORIGINS includes all frontend addresses
5. **JWT Validation**: Ensure JWT tokens include `facility_name` field

## Security Considerations

1. **Backend Validation**: All permission checks happen on backend; frontend checks are for UX only
2. **Audit Logging**: All referral status changes are logged with user ID, timestamp, and IP address
3. **Facility Isolation**: Users cannot see referrals not involving their facility
4. **Patient Access**: Backend should validate that patient being accessed is actually in a referral involving user's facility
5. **Note Size Limits**: Notes are limited to 4000 characters per update to prevent abuse

## Future Enhancements

1. **Granular Permissions**: Support different roles (e.g., admin can override, read-only clinician)
2. **Facility Approval**: Require facility head approval for certain referral statuses
3. **Automated Notifications**: Email/SMS when receiving facility updates referral status
4. **Bulk Operations**: Allow marking multiple referrals as received
5. **Export Reports**: Generate referral reports for quality assurance
6. **Analytics Dashboard**: Track referral patterns and outcomes by facility
