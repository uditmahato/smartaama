// frontend/src/pages/Referral.tsx
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Card, CardContent, Divider, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api } from "../services/api";

type ReferralOut = {
  id: string;
  patient_id: string;
  from_facility: string;
  to_facility: string;
  status: "draft" | "submitted" | "received" | "closed" | "cancelled";
  reason: string;
  clinician_decision?: string | null;
  clinician_note?: string | null;
  created_at: string;
};

export default function Referral() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [fromFacility, setFromFacility] = useState("PHC");
  const [toFacility, setToFacility] = useState("");
  const [reason, setReason] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");

  const [referral, setReferral] = useState<ReferralOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canCreate = useMemo(() => {
    return Boolean(patientId) && toFacility.trim().length > 1 && reason.trim().length >= 5;
  }, [patientId, toFacility, reason]);

  async function create() {
    if (!patientId) return;
    setError(null);
    try {
      const resp = await api.post<ReferralOut>("/referrals", {
        patient_id: patientId,
        from_facility: fromFacility.trim(),
        to_facility: toFacility.trim(),
        reason: reason.trim(),
        clinician_note: clinicianNote.trim() || null,
      });
      setReferral(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to create referral");
    }
  }

  async function setStatus(status: ReferralOut["status"]) {
    if (!referral) return;
    setError(null);
    try {
      const resp = await api.post<ReferralOut>(`/referrals/${referral.id}/status`, { status });
      setReferral(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to update status");
    }
  }

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <div>
              <Typography variant="h5">Referral</Typography>
              <Typography variant="body2" color="text.secondary">
                AI may recommend; clinician submits. Receiving hospital can view full timeline.
              </Typography>
            </div>
            <Button variant="outlined" onClick={() => navigate(`/patients/${patientId}`)}>
              Back
            </Button>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}

          {!referral ? (
            <Stack spacing={2}>
              <TextField label="From facility" value={fromFacility} onChange={(e) => setFromFacility(e.target.value)} />
              <TextField label="To facility" value={toFacility} onChange={(e) => setToFacility(e.target.value)} required />
              <TextField
                label="Referral reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                multiline
                minRows={3}
              />
              <TextField
                label="Clinician note (optional)"
                value={clinicianNote}
                onChange={(e) => setClinicianNote(e.target.value)}
                multiline
                minRows={2}
              />
              <Button variant="contained" onClick={create} disabled={!canCreate}>
                Create referral
              </Button>
            </Stack>
          ) : (
            <Stack spacing={2}>
              <Typography variant="subtitle1">
                Referral ID: {referral.id}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Status: {referral.status}
              </Typography>
              <Typography variant="body2">
                {referral.from_facility} → {referral.to_facility}
              </Typography>
              <Typography variant="body2">Reason: {referral.reason}</Typography>

              <Divider />

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  select
                  label="Change status"
                  value={referral.status}
                  onChange={(e) => setStatus(e.target.value as any)}
                  fullWidth
                >
                  {["draft", "submitted", "received", "closed", "cancelled"].map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>
                <Button variant="contained" onClick={() => navigate(`/patients/${patientId}`)}>
                  View patient timeline
                </Button>
              </Stack>

              <Typography variant="body2" color="text.secondary">
                Note: status transitions are validated server-side (draft → submitted → received → closed).
              </Typography>
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
