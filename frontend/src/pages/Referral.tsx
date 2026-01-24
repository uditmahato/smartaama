// frontend/src/pages/Referral.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider, Grid, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api, userStore } from "../services/api";

type ReferralOut = {
  id: string;
  patient_id: string;
  from_facility: string;
  to_facility: string;
  status: "draft" | "submitted" | "received" | "closed" | "cancelled";
  received_facility_status?: "draft" | "submitted" | "received" | "closed" | "cancelled" | null;
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

type UserInfo = {
  id: string;
  username: string;
  full_name?: string | null;
  role: string;
  facility_name?: string | null;
};

export default function Referral() {
  const { patientId, referralId } = useParams();
  const navigate = useNavigate();

  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");
  const [reason, setReason] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");

  const [facilityOptions, setFacilityOptions] = useState<FacilityOption[]>([]);
  const [facilityError, setFacilityError] = useState<string | null>(null);
  const [userFacilityName, setUserFacilityName] = useState<string | null>(null);

  const [referral, setReferral] = useState<ReferralOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!!referralId);
  const [statusUpdateNote, setStatusUpdateNote] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [selectedReceivedStatus, setSelectedReceivedStatus] = useState<string>("");

  const isFromHospital = useMemo(() => {
    return facilityOptions.some((f) => f.name === fromFacility && f.kind === "hospital");
  }, [fromFacility, facilityOptions]);

  const canCreate = useMemo(() => {
    return (
      Boolean(patientId) &&
      fromFacility.trim().length > 0 &&
      toFacility.trim().length > 0 &&
      reason.trim().length >= 5
    );
  }, [patientId, fromFacility, toFacility, reason]);

  const isReceivingFacility = useMemo(() => {
    return referral && userFacilityName && referral.to_facility === userFacilityName;
  }, [referral, userFacilityName]);

  const getStatusChip = (status: ReferralOut["status"]) => {
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

  async function loadUserInfo() {
    const cached = userStore.get() as UserInfo | null;
    if (cached) {
        setUserFacilityName(cached.facility_name ?? null);
        return;
    }
    try {
      const resp = await api.get<UserInfo>("/auth/me");
      userStore.set(resp.data);
      setUserFacilityName(resp.data.facility_name ?? null);
    } catch (err) {
      console.error("Failed to load user info", err);
    }
  }

  async function loadFacilities() {
    try {
      const [phcResp, hospitalResp] = await Promise.all([
        api.get<FacilityOption[]>("/facilities", { params: { kind: "phc" } }),
        api.get<FacilityOption[]>("/facilities", { params: { kind: "hospital" } }),
      ]);
      const combined = [...phcResp.data, ...hospitalResp.data];
      setFacilityOptions(combined);
    } catch (err: any) {
      setFacilityError(err?.response?.data?.detail ?? "Failed to load facilities");
    }
  }

  useEffect(() => {
    void loadFacilities();
    void loadUserInfo();
  }, []);

  useEffect(() => {
    if (referralId) {
      void loadReferralById(referralId);
    }
  }, [referralId]);

  async function loadReferralById(id: string) {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.get<ReferralOut>(`/referrals/${id}`);
      setReferral(resp.data);
      // Populate form fields from loaded referral
      setFromFacility(resp.data.from_facility);
      setToFacility(resp.data.to_facility);
      setReason(resp.data.reason);
      setClinicianNote(resp.data.clinician_note || "");
      // Initialize selected received status
      if (isReceivingFacility) {
        setSelectedReceivedStatus(resp.data.received_facility_status || "");
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to load referral");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!fromFacility && facilityOptions.length) {
      const preferred = userFacilityName && facilityOptions.find((f) => f.name === userFacilityName);
      if (preferred) {
        setFromFacility(preferred.name);
      } else {
        setFromFacility(facilityOptions[0].name);
      }
    }
  }, [fromFacility, facilityOptions, userFacilityName]);

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
        status: "submitted",
      });
      setReferral(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to create referral");
    }
  }

  async function setStatus(status: ReferralOut["status"]) {
    if (!referral) return;
    setError(null);
    setIsUpdatingStatus(true);
    try {
      const resp = await api.post<ReferralOut>(`/referrals/${referral.id}/status`, { 
        status,
        // Only include note if user is the receiving facility
        note: isReceivingFacility ? (statusUpdateNote.trim() || undefined) : undefined
      });
      setReferral(resp.data);
      setStatusUpdateNote("");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to update status");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function setReceivedFacilityStatus(status: ReferralOut["received_facility_status"]) {
    if (!referral) return;
    setError(null);
    setIsUpdatingStatus(true);
    try {
      const resp = await api.post<ReferralOut>(`/referrals/${referral.id}/received-status`, { 
        received_facility_status: status,
        note: statusUpdateNote.trim() || undefined
      });
      setReferral(resp.data);
      setStatusUpdateNote("");
      setSelectedReceivedStatus(resp.data.received_facility_status || "");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to update received facility status");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  const handleSaveReceivedStatus = () => {
    if (selectedReceivedStatus) {
      setReceivedFacilityStatus(selectedReceivedStatus as any);
    }
  }

  if (isLoading && referralId) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#F6F7FB" }}>
        <CircularProgress />
      </Box>
    );
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
                      disabled={Boolean(userFacilityName)}
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
                        Status (Referring)
                      </Typography>
                      <Box sx={{ mt: 0.75 }}>
                        <Chip
                          label={getStatusChip(referral.status).label}
                          color={getStatusChip(referral.status).color as any}
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                    <Box flex={1}>
                      <Typography variant="caption" color="text.secondary">
                        Status (Received Place)
                      </Typography>
                      <Box sx={{ mt: 0.75 }}>
                        <Chip
                          label={referral.received_facility_status ? getStatusChip(referral.received_facility_status).label : "Pending"}
                          color={referral.received_facility_status ? getStatusChip(referral.received_facility_status).color as any : "default"}
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
                    {isReceivingFacility ? "Update Your Status (Received Place)" : "Update Status (Referring)"}
                  </Typography>

                  {isReceivingFacility ? (
                    // Receiving facility: Update their own received_facility_status
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          select
                          label="Your facility status"
                          value={selectedReceivedStatus}
                          onChange={(e) => setSelectedReceivedStatus(e.target.value)}
                          fullWidth
                          size="small"
                          disabled={isUpdatingStatus}
                          helperText="Update your facility's acknowledgment of this referral"
                        >
                          <MenuItem value="received">Admitted Here</MenuItem>
                          <MenuItem value="closed">Closed Case</MenuItem>
                          <MenuItem value="cancelled">Referred Elsewhere</MenuItem>
                        </TextField>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="contained"
                          onClick={handleSaveReceivedStatus}
                          fullWidth
                          disabled={isUpdatingStatus || !selectedReceivedStatus || selectedReceivedStatus === (referral.received_facility_status || "")}
                          sx={{
                            textTransform: "none",
                            fontWeight: 700,
                            borderRadius: 2,
                            py: 1,
                            background: "#4F46E5",
                            "&:hover": { background: "#4338CA" },
                          }}
                        >
                          Save Status
                        </Button>
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          label="Add note (optional)"
                          value={statusUpdateNote}
                          onChange={(e) => setStatusUpdateNote(e.target.value)}
                          fullWidth
                          multiline
                          minRows={2}
                          size="small"
                          placeholder="Add clinical notes about this patient's status update"
                          disabled={isUpdatingStatus}
                        />
                      </Grid>
                    </Grid>
                  ) : (
                    // Referring facility: View their status (read-only)
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          select
                          label="Your status"
                          value={referral.status}
                          onChange={(e) => setStatus(e.target.value as any)}
                          fullWidth
                          size="small"
                          disabled={referral.status === "submitted" || isUpdatingStatus}
                          helperText={referral.status === "submitted" ? "Locked until received" : ""}
                        >
                          <MenuItem value="submitted">Referred from Here</MenuItem>
                          <MenuItem value="received">Referred to Here</MenuItem>
                          <MenuItem value="closed">Closed Case</MenuItem>
                          <MenuItem value="cancelled">Cancelled</MenuItem>
                        </TextField>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: "1px solid #e0e0e0",
                            borderRadius: 1,
                            bgcolor: "#f5f5f5"
                          }}
                        >
                          <Typography variant="caption" color="text.secondary">
                            Received Place Status
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
                            {referral.received_facility_status ? getStatusChip(referral.received_facility_status as any).label : "Pending acknowledgment"}
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  )}

                  {isReceivingFacility && referral.clinician_note && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#0F172A", mb: 2 }}>
                        Updates Submitted
                      </Typography>
                      <Box sx={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ backgroundColor: "#f3f4f6", borderBottom: "2px solid #e5e7eb" }}>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Date & Time</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Status</th>
                              <th style={{ padding: "12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Notes</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(() => {
                              const lines = referral.clinician_note.split('\n');
                              const updates = [];
                              
                              for (let i = 0; i < lines.length; i++) {
                                const line = lines[i].trim();
                                // Check if this is a status update header line
                                if (line.includes('[') && line.includes('Received facility status:')) {
                                  const timestampMatch = line.match(/\[(.*?)\]/);
                                  const statusMatch = line.match(/status: (\w+)/i);
                                  const timestamp = timestampMatch ? timestampMatch[1] : '';
                                  let statusValue = statusMatch ? statusMatch[1] : '';
                                  
                                  // Map status values to display labels
                                  let displayStatus = statusValue;
                                  if (statusValue === 'closed') displayStatus = 'Closed Case';
                                  else if (statusValue === 'received') displayStatus = 'Admitted Here';
                                  else if (statusValue === 'referred') displayStatus = 'Referred Elsewhere';
                                  
                                  // Get the note from the next non-empty line
                                  let noteText = "-";
                                  for (let j = i + 1; j < lines.length; j++) {
                                    const nextLine = lines[j].trim();
                                    // Stop if we hit another status line
                                    if (nextLine.includes('[') && nextLine.includes('Received facility status:')) {
                                      break;
                                    }
                                    if (nextLine) {
                                      noteText = nextLine;
                                      i = j; // Skip processed lines
                                      break;
                                    }
                                  }
                                  
                                  updates.push({
                                    timestamp,
                                    status: displayStatus,
                                    note: noteText
                                  });
                                }
                              }
                              
                              return updates.map((update, idx) => (
                                <tr key={idx} style={{ borderBottom: "1px solid #e5e7eb" }}>
                                  <td style={{ padding: "12px", color: "#6b7280" }}>{update.timestamp}</td>
                                  <td style={{ padding: "12px" }}>
                                    <Chip
                                      label={update.status}
                                      size="small"
                                      color="primary"
                                      variant="outlined"
                                    />
                                  </td>
                                  <td style={{ padding: "12px", color: "#374151" }}>{update.note}</td>
                                </tr>
                              ));
                            })()}
                          </tbody>
                        </table>
                      </Box>
                    </>
                  )}

                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
                    {isReceivingFacility ? (
                      <>Note: Only the receiving facility can add notes when updating status.</>
                    ) : (
                      <>Note: All referrals start as "Referred from Here" and are locked until the receiving facility marks them as "Referred to Here". Only the receiving facility can add notes.</>
                    )}
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
