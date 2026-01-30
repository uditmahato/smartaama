# SmartAAMA Facility-Based Permission System - Testing Guide

## Quick Start Testing

### Setup Requirements
1. Backend running on `http://localhost:8000`
2. Frontend running on `http://localhost:5174`
3. Database initialized with `python -m app.db.init_db`
4. Two test users created: one in PHC facility, one in Hospital facility

### Test Scenario 1: PHC User Creates and Refers Patient

**Step 1: Create PHC User (if not exists)**
```bash
# Send to http://localhost:8000/auth/bootstrap-admin
Header: X-Bootstrap-Token: 12345678

{
  "username": "phc_user",
  "password": "password123",
  "full_name": "PHC Doctor",
  "facility_kind": "phc",
  "facility_id": "<phc_facility_id>"
}
```

**Step 2: Login as PHC User**
- Navigate to login page
- Username: `phc_user`
- Password: `password123`
- Verify bootstrap token auto-fills from VITE_BOOTSTRAP_TOKEN

**Step 3: Create Patient**
- Click "Add Patient" or similar
- Fill in patient details
- Note the patient ID

**Step 4: Create Referral**
- Navigate to patient profile
- Click "Refer Patient" button
- Select "Hospital" as receiving facility
- Enter referral reason
- Submit referral
- Verify referral appears in dashboard

**Step 5: Verify Edit Access**
- Patient profile should show "Update Record" button
- No read-only alert should appear
- Should be able to edit patient vitals

### Test Scenario 2: Hospital User Receives Referral

**Step 1: Create Hospital User**
```bash
# Send to http://localhost:8000/auth/bootstrap-admin
Header: X-Bootstrap-Token: 12345678

{
  "username": "hospital_user",
  "password": "password123",
  "full_name": "Hospital Doctor",
  "facility_kind": "hospital",
  "facility_id": "<hospital_facility_id>"
}
```

**Step 2: Login as Hospital User**
- Navigate to login page
- Username: `hospital_user`
- Password: `password123`

**Step 3: Verify Referral Visibility**
- Dashboard should show the referral created by PHC
- Referral card should show status "Referred to Here"
- Should only see referrals involving Hospital facility

**Step 4: Access Patient Profile**
- Click on referral or patient in dashboard
- Patient profile should load
- Verify read-only alert appears: "You are viewing this patient's record as a receiving facility..."
- "Update Record" button should NOT be visible
- "Refer Patient" button should still be visible

**Step 5: Update Referral Status**
- Click on referral history row or "Refer Patient" button
- Navigate to referral details page
- In "Update Status" section:
  - Select new status (e.g., "Referred to Here")
  - Enter note in text area: "Patient has been assessed and admitted"
  - Click status dropdown to update
- Verify status changes and note is appended

**Step 6: Verify Timestamped Notes**
- In referral details, check "Clinician Note" field
- Should contain: `[2026-01-25 10:30 UTC] Status: <status>\nPatient has been assessed and admitted`

### Test Scenario 3: PHC User Sees Updates

**Step 1: Switch Back to PHC User**
- Logout Hospital user
- Login as PHC user again

**Step 2: View Referral**
- Go to patient profile
- Click on referral history row
- Should see:
  - Status changed to "Referred to Here"
  - received_facility_status showing hospital's update
  - Timestamped note from hospital user

**Step 3: Make Counter-Referral**
- From hospital referral details, can create new referral back to PHC
- Click "Refer Patient" button
- Select PHC as receiving facility
- This starts a bidirectional referral chain

### Test Scenario 4: Permission Boundaries

**Test 4a: Receiving Facility Cannot Edit Patient**
```javascript
// Try calling this from Hospital user's console after login:
// Should fail with 403 Forbidden

fetch('http://localhost:5174/api/patients/{patient_id}', {
  method: 'PATCH',
  headers: { 'Authorization': 'Bearer <token>' },
  body: JSON.stringify({ 
    age: 35,
    // ... other patient fields
  })
});
```

**Test 4b: Users Cannot See Foreign Referrals**
- Create referral between Facility A and Facility B
- Login as user from Facility C
- Dashboard should not show this referral
- Verify /referrals endpoint returns empty list

**Test 4c: Cannot Access Patient Without Referral**
- Hospital user tries to access patient not referred to them
- Frontend should not load referral data
- Backend should reject if permission check added

## UI Verification Checklist

### PatientProfile Component
- [ ] Read-only alert visible for receiving facility
- [ ] Alert contains helpful message about edit restrictions
- [ ] "Update Record" button hidden for receiving facility
- [ ] "Refer Patient" button visible for both facilities
- [ ] Referral history table shows all referrals
- [ ] Clicking referral navigates to detail page

### Referral Component
- [ ] Status dropdown visible and functional
- [ ] Note textarea appears below status dropdown
- [ ] Note field optional (can be empty)
- [ ] Submitting status update includes note in request
- [ ] Clinician Note section displays timestamped notes
- [ ] Referral details show both status fields

### Dashboard Component
- [ ] Status labels show human-readable text
  - "Referred from Here" (blue)
  - "Referred to Here" (green)
  - "Closed Case" (gray)
  - "Admitted Case" (green)
- [ ] Only showing referrals for user's facility
- [ ] Clicking referral navigates to details

## API Testing with curl/Postman

### 1. Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=phc_user&password=password123"

# Response:
# {"access_token": "eyJ...", "token_type": "bearer"}
```

### 2. Get Current User
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"

# Response:
# {
#   "id": "user-id",
#   "username": "phc_user",
#   "facility_name": "PHC Facility Name",
#   "facility_type": "phc",
#   ...
# }
```

### 3. List Referrals (Filtered by Facility)
```bash
curl http://localhost:8000/referrals \
  -H "Authorization: Bearer <token>"

# Should only return referrals where:
# - from_facility = user's facility OR
# - to_facility = user's facility
```

### 4. Update Referral Status with Note
```bash
curl -X POST http://localhost:8000/referrals/<referral_id>/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "received",
    "note": "Patient assessed and admitted"
  }'

# Verify clinician_note contains timestamped update
```

## Common Issues and Solutions

### Issue: "Read-only alert appears for referring facility"
- **Solution**: Check permission calculation in load() function
  - Ensure `isReceivingFacility` correctly identifies receiving facility
  - Verify API returns correct `to_facility` value

### Issue: "Update Record button still visible for receiving facility"
- **Solution**: Check canEdit state logic
  - Should be: `setCanEdit(!isReceivingFacility || isReferringFacility || r.data.length === 0)`
  - Verify state updates before rendering buttons

### Issue: "Cannot see referral from other facility"
- **Solution**: Check list_referrals backend filtering
  - Verify user.facility_name is correctly loaded
  - Check both query1 and query2 are being executed
  - Verify deduplication logic doesn't remove valid results

### Issue: "Note not appearing in referral history"
- **Solution**: Check note appending in backend
  - Verify transition_status() calls append_timestamped_note()
  - Check clinician_note field is being saved to database
  - Verify UI reads clinician_note, not separate note field

### Issue: "Frontend showing JWT_SECRET validation error"
- **Solution**: Verify backend CORS configuration
  - Check CORS_ORIGINS in .env includes 5174
  - Restart backend after .env changes
  - Clear browser cache and cookies

## Performance Notes

1. **Referral Filtering**: Two database queries may impact performance with large datasets
   - Future optimization: Add compound index on (from_facility, to_facility, patient_id)

2. **User Factory Calls**: Each page load calls /auth/me
   - Optimization: Cache user info in localStorage after login
   - Current implementation uses userStore which caches locally

3. **Referral History**: Loading all referrals on patient profile
   - Current: Limited to 100 referrals per query
   - Future: Add pagination or infinite scroll

## Debug Tips

### To inspect frontend state:
```javascript
// In browser console on PatientProfile:
console.log({ userFacility, canEdit, referrals });
```

### To check backend logs:
```bash
# Backend console should show:
# - User login timestamp
# - Referral query filters applied
# - Audit log entries for status changes
```

### To verify database state:
```sql
-- Check referral details:
SELECT id, from_facility, to_facility, status, received_facility_status, clinician_note 
FROM referrals 
WHERE id = '<referral_id>';

-- Check user facility assignments:
SELECT username, facility_name, facility_type 
FROM users 
WHERE username IN ('phc_user', 'hospital_user');
```

## Sign-Off Checklist

- [ ] Frontend compiles without errors
- [ ] Backend starts without errors
- [ ] Login works for multiple users
- [ ] Referrals filtered by facility in dashboard
- [ ] Patient profile shows read-only alert for receiving facility
- [ ] Edit buttons conditionally rendered
- [ ] Referral status updates with notes work
- [ ] Notes appear with timestamps
- [ ] Referral history clickable and navigates correctly
- [ ] No permission leaks (users only see their facility's referrals)
