// frontend/src/pages/Referral.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, MenuItem, Stack, TextField, Typography } from "@mui/material";
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

type FacilityOption = {
  id: string;
  name: string;
  kind: "phc" | "hospital";
};

export default function Referral() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");
  const [reason, setReason] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");

  const [facilityOptions, setFacilityOptions] = useState<FacilityOption[]>([]);
  const [facilityError, setFacilityError] = useState<string | null>(null);

  const [referral, setReferral] = useState<ReferralOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canCreate = useMemo(() => {
    return (
      Boolean(patientId) &&
      fromFacility.trim().length > 0 &&
      toFacility.trim().length > 0 &&
      reason.trim().length >= 5
    );
  }, [patientId, fromFacility, toFacility, reason]);

  const getStatusChip = (status: ReferralOut["status"]) => {
    switch (status) {
      case "submitted":
        return { color: "warning", label: "Submitted" };
      case "received":
        return { color: "success", label: "Received" };
      case "closed":
        return { color: "default", label: "Closed" };
      case "cancelled":
        return { color: "error", label: "Cancelled" };
      default:
        return { color: "info", label: "Draft" };
    }
  };

  async function loadFacilities() {
    try {
      const [phcResp, hospitalResp] = await Promise.all([
        api.get<FacilityOption[]>("/facilities", { params: { kind: "phc" } }),
        api.get<FacilityOption[]>("/facilities", { params: { kind: "hospital" } }),
      ]);
      const combined = [...phcResp.data, ...hospitalResp.data];
      setFacilityOptions(combined);
      if (!fromFacility && combined.length) {
        setFromFacility(combined[0].name);
      }
    } catch (err: any) {
      setFacilityError(err?.response?.data?.detail ?? "Failed to load facilities");
    }
  }

  useEffect(() => {
    void loadFacilities();
  }, []);

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
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F7FB", py: { xs: 2, md: 3 }, px: { xs: 0.5, sm: 1, md: 1.5 }, width: "100%", boxSizing: "border-box" }}>
      <Stack spacing={3}>
        {/* Top Bar */}
        <Card
          sx={{
            borderRadius: 3,
            border: "1px solid rgba(15, 23, 42, 0.10)",
            boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              px: { xs: 2.5, md: 3.5 },
              py: { xs: 2.5, md: 3 },
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
            }}
          >
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={{ xs: 2, md: 3 }}
              justifyContent="space-between"
              alignItems={{ xs: "flex-start", md: "center" }}
            >
              <Stack spacing={0.5}>
                <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -0.2 }}>
                  Patient Referral
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9, lineHeight: 1.7 }}>
                  Create and manage referral requests with clinical details and notes.
                </Typography>
              </Stack>

              <Stack direction="row" spacing={1.25} alignItems="center">
                <Button
                  variant="contained"
                  onClick={() => navigate(`/patients/${patientId}`)}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    borderRadius: 2,
                    background: "rgba(255,255,255,0.95)",
                    color: "#4C51BF",
                    "&:hover": { background: "white" },
                    px: 2.25,
                  }}
                >
                  Back
                </Button>
              </Stack>
            </Stack>
          </Box>

          {error && (
            <CardContent sx={{ p: { xs: 2.5, md: 3.5 }, bgcolor: "white" }}>
              <Alert severity="error">{error}</Alert>
            </CardContent>
          )}
        </Card>

        {/* Form or Display */}
        <Card
          sx={{
            borderRadius: 3,
            border: "1px solid rgba(15, 23, 42, 0.10)",
            boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
          }}
        >
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            {!referral ? (
              <Stack spacing={3}>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                  Create New Referral
                </Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      select
                      label="From facility"
                      value={fromFacility}
                      onChange={(e) => setFromFacility(e.target.value)}
                      fullWidth
                      size="small"
                      required
                      helperText={facilityError ?? "Select referring facility"}
                      error={Boolean(facilityError)}
                    >
                      {facilityOptions.map((opt) => (
                        <MenuItem key={opt.id} value={opt.name}>
                          {opt.name} {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      select
                      label="To facility"
                      value={toFacility}
                      onChange={(e) => setToFacility(e.target.value)}
                      required
                      fullWidth
                      size="small"
                      helperText={facilityError ?? "Select receiving facility"}
                      error={Boolean(facilityError)}
                    >
                      {facilityOptions.map((opt) => (
                        <MenuItem key={opt.id} value={opt.name}>
                          {opt.name} {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      label="Referral reason"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      required
                      fullWidth
                      multiline
                      minRows={3}
                      size="small"
                      helperText="Describe the reason for referral (minimum 5 characters)"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <TextField
                      label="Clinician note (optional)"
                      value={clinicianNote}
                      onChange={(e) => setClinicianNote(e.target.value)}
                      fullWidth
                      multiline
                      minRows={2}
                      size="small"
                      helperText="Add any additional clinical notes"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Stack direction="row" spacing={2}>
                      <Button
                        variant="contained"
                        onClick={create}
                        disabled={!canCreate}
                        sx={{
                          textTransform: "none",
                          fontWeight: 700,
                          borderRadius: 2,
                          background: "#4F46E5",
                          "&:hover": { background: "#4338CA" },
                          px: 3,
                        }}
                      >
                        Create Referral
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => navigate(`/patients/${patientId}`)}
                        sx={{
                          textTransform: "none",
                          fontWeight: 700,
                          borderRadius: 2,
                        }}
                      >
                        Cancel
                      </Button>
                    </Stack>
                  </Grid>
                </Grid>
              </Stack>
            ) : (
              <Stack spacing={3}>
                <Stack spacing={2}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                    Referral Created
                  </Typography>

                  <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="flex-start">
                    <Box flex={1}>
                      <Typography variant="caption" color="text.secondary">
                        Referral ID
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700, mt: 0.5 }}>
                        {referral.id}
                      </Typography>
                    </Box>
                    <Box flex={1}>
                      <Typography variant="caption" color="text.secondary">
                        Status
                      </Typography>
                      <Box sx={{ mt: 0.75 }}>
                        <Chip
                          label={getStatusChip(referral.status).label}
                          color={getStatusChip(referral.status).color as any}
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                  </Stack>
                </Stack>

                <Divider sx={{ my: 1 }} />

                <Stack spacing={2}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#0F172A" }}>
                    Referral Details
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">
                        From Facility
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
                        {referral.from_facility}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">
                        To Facility
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
                        {referral.to_facility}
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">
                        Reason
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        {referral.reason}
                      </Typography>
                    </Grid>
                    {referral.clinician_note && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">
                          Clinician Note
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>
                          {referral.clinician_note}
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </Stack>

                <Divider sx={{ my: 1 }} />

                <Stack spacing={2}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#0F172A" }}>
                    Update Status
                  </Typography>

                  <Grid container spacing={2} alignItems="flex-end">
                    <Grid item xs={12} sm={6}>
                      <TextField
                        select
                        label="Change status"
                        value={referral.status}
                        onChange={(e) => setStatus(e.target.value as any)}
                        fullWidth
                        size="small"
                      >
                        {["draft", "submitted", "received", "closed", "cancelled"].map((s) => (
                          <MenuItem key={s} value={s}>
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Button
                        variant="outlined"
                        onClick={() => navigate(`/patients/${patientId}`)}
                        fullWidth
                        sx={{
                          textTransform: "none",
                          fontWeight: 700,
                          borderRadius: 2,
                        }}
                      >
                        View Patient Timeline
                      </Button>
                    </Grid>
                  </Grid>

                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                    Note: Status transitions are validated server-side (draft → submitted → received → closed).
                  </Typography>
                </Stack>
              </Stack>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}
