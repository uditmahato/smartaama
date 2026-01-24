# SmartAAMA Facility-Based Permission System - Quick Reference

## Permission Rules at a Glance

```
User from Facility A viewing Referral between A (from) and B (to):
├─ Can VIEW patient? YES
├─ Can EDIT patient? YES ✅
└─ Can UPDATE referral status? YES ✅

User from Facility B viewing Referral between A (from) and B (to):
├─ Can VIEW patient? YES
├─ Can EDIT patient? NO ❌
└─ Can UPDATE referral status? YES ✅ (with notes)

User from Facility C viewing Referral between A and B:
├─ Cannot see this referral at all ❌
└─ API returns empty list
```

## Code Snippets for Common Tasks

### 1. Check if user can edit patient (Frontend)
```typescript
// In PatientProfile.tsx load() function
const isReceivingFacility = referrals.some(ref => ref.to_facility === userFacilityName);
const isReferringFacility = referrals.some(ref => ref.from_facility === userFacilityName);
const canEdit = !isReceivingFacility || isReferringFacility || referrals.length === 0;

// Use: {canEdit && <EditButton />}
```

### 2. Update referral status with note (Frontend)
```typescript
const payload = {
  status: "received",
  note: "Patient assessed and stable for discharge"
};

const response = await api.post(`/referrals/${referralId}/status`, payload);
```

### 3. Get all referrals for current user (Frontend)
```typescript
// Backend automatically filters - no facility parameter needed!
const referrals = await api.get(`/referrals?patient_id=${patientId}`);
// Only returns referrals where user's facility is involved
```

### 4. Verify user facility (Backend)
```python
# In any endpoint
if current_user.facility_name not in [referral.from_facility, referral.to_facility]:
    raise HTTPException(status_code=403, detail="Not your facility")
```

### 5. Parse timestamped notes (Frontend/Backend)
```typescript
// clinician_note format: [2026-01-25 10:30 UTC] Status: received\nNote text here

const lines = clinician_note.split('\n');
const timestamp = lines[0]; // [2026-01-25 10:30 UTC] Status: received
const note = lines.slice(1).join('\n'); // Note text here
```

## API Endpoint Reference

| Method | Endpoint | Filters | Notes |
|--------|----------|---------|-------|
| GET | /referrals | Auto by facility | No facility param needed |
| GET | /referrals/{id} | None | Anyone can view |
| POST | /referrals/{id}/status | None | Include status and note |
| POST | /referrals/{id}/received-status | None | Receiving facility update |
| GET | /auth/me | None | Returns facility_name |
| GET | /patients/{id} | None | Should validate permission |
| PATCH | /patients/{id} | None | Should validate from_facility |

## Frontend Component Props

### PatientProfile.tsx State
```typescript
const [userFacility, setUserFacility] = useState<string | null>(null);
const [canEdit, setCanEdit] = useState<boolean>(true);
const [referrals, setReferrals] = useState<any[]>([]);
```

### Referral.tsx State  
```typescript
const [statusUpdateNote, setStatusUpdateNote] = useState("");
const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
```

## Database Queries

### Get referrals for user
```sql
SELECT * FROM referrals 
WHERE from_facility = 'User Facility Name' 
   OR to_facility = 'User Facility Name'
ORDER BY created_at DESC;
```

### Get referral with full history
```sql
SELECT id, from_facility, to_facility, status, received_facility_status, clinician_note
FROM referrals
WHERE id = '<referral_id>';
```

### Verify no data leaks
```sql
-- Count referrals visible to each user
SELECT 
  u.facility_name,
  COUNT(r.id) as visible_referrals
FROM users u
CROSS JOIN referrals r
WHERE u.facility_name IN (r.from_facility, r.to_facility)
GROUP BY u.facility_name;
```

## Status Transitions

```
DRAFT (optional initial state)
  └─> SUBMITTED (PHC creates referral)
        └─> RECEIVED (Hospital receives)
              ├─> CLOSED (resolved)
              └─> CANCELLED (rejected/admitted elsewhere)

RECEIVED_FACILITY_STATUS (Hospital's acknowledgment)
  └─> RECEIVED (acknowledged)
        ├─> CLOSED (patient discharged)
        └─> CANCELLED (referred elsewhere)
```

## Common Development Tasks

### Add permission check to new endpoint
```python
@router.get("/my-endpoint")
def my_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    # Get the resource
    resource = db.execute(...).scalar_one_or_none()
    
    # Check permission
    if current_user.facility_name != resource.facility_name:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return resource
```

### Conditionally render component based on edit permission
```typescript
{canEdit ? (
  <Button onClick={() => navigate(`/patients/${id}/update`)}>
    Edit Patient
  </Button>
) : (
  <Alert severity="info">
    You can only view this patient. To edit, refer from your facility.
  </Alert>
)}
```

### Log permission check for debugging
```python
import logging
logger = logging.getLogger(__name__)

def check_permission(user_facility, referral):
    allowed = user_facility in [referral.from_facility, referral.to_facility]
    logger.info(
        f"Permission check: user={user_facility}, "
        f"from={referral.from_facility}, to={referral.to_facility}, "
        f"allowed={allowed}"
    )
    return allowed
```

## Debugging Checklist

- [ ] User facility loaded correctly: Check browser DevTools → localStorage
- [ ] Referrals filtered by facility: Check Network tab → /referrals response
- [ ] Permission calculated correctly: Add console.log(userFacility, canEdit)
- [ ] Note sent with status: Check Network tab → /referrals/{id}/status payload
- [ ] Note saved correctly: Check /referrals/{id} response → clinician_note
- [ ] Read-only alert showing: Check JSX conditional rendering
- [ ] Edit button hidden: Check {canEdit && <Button>}
- [ ] Database migration run: Check referrals table schema includes received_facility_status

## Environment Configuration

### Backend (.env)
```
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175
DATABASE_URL=postgresql://user:password@localhost/smartaama
JWT_SECRET_KEY=your-secret-key-here
BOOTSTRAP_TOKEN=12345678
ENV=dev
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_BOOTSTRAP_TOKEN=12345678
```

## Performance Tips

1. **Cache user info**: Use userStore to avoid repeated /auth/me calls
2. **Batch queries**: Load patient + referrals in parallel
3. **Index database**: Add index on (from_facility, to_facility, patient_id)
4. **Lazy load**: Load referral history only when drawer opened
5. **Memoize**: Use useMemo for permission calculations

## Security Reminders

⚠️ **IMPORTANT**: Frontend permission checks are for UX only!
✅ **ALWAYS** validate permissions on backend
✅ **ALWAYS** check user.facility_name matches resource
✅ **NEVER** trust frontend to enforce security
✅ **LOG** all permission denials for audit trail
✅ **VALIDATE** all user input on backend

## Support Scenarios

**Q: User says they can't edit patient**
A: Check if they're the receiving facility. If yes, that's correct behavior.

**Q: Dashboard shows referral not involving this facility**
A: Bug in list_referrals filtering. Check both from_facility AND to_facility queries.

**Q: Note not appearing after status update**
A: Check that service method appends note to clinician_note field.

**Q: Can see referral but not patient data**
A: Permission check working. Would need separate permission to edit patient.

**Q: Receiving facility can still edit patient**
A: Frontend check working but backend not enforcing. Add backend permission check to /patients PATCH endpoint.

## Version Information

- **SmartAAMA Version**: 1.0.0
- **Permission System Version**: 1.0.0
- **Last Updated**: January 25, 2025
- **Backend**: Python 3.10+, FastAPI
- **Frontend**: React 18, TypeScript
- **Database**: PostgreSQL 12+

---

For full documentation, see:
- `PERMISSION_SYSTEM_IMPLEMENTATION.md` - Technical deep dive
- `TESTING_GUIDE.md` - Testing procedures
- `SESSION_COMPLETION_SUMMARY.md` - Session overview
