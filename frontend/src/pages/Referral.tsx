// frontend/src/pages/Referral.tsx
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import {
  api,
  facilityMatches,
  fetchReferralHistory,
  getErrorMessage,
  isForbidden,
  isNotFound,
  type ReferralHistoryOut,
  type ReferralOut,
  type ReferralStatus,
} from "../services/api";
import type { FacilityOption } from "../services/types";
import { useUser } from "../hooks/useUser";

type ChipColor = "default" | "warning" | "success" | "info" | "error";

const HISTORY_KIND_LABELS: Record<ReferralHistoryOut["kind"], string> = {
  created: "Created",
  status: "Referring status",
  received_status: "Receiving status",
  decision: "Clinician decision",
};

const RECEIVED_STATUS_LABELS: Record<string, string> = {
  received: "Admitted Here",
  closed: "Closed Case",
  cancelled: "Referred Elsewhere",
};

const REFERRING_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  submitted: "Referred from Here",
  received: "Referred to Here",
  closed: "Closed Case",
  cancelled: "Cancelled",
};

/** Referring-side state machine (mirrors backend `_ALLOWED_TRANSITIONS`). */
const SENDER_NEXT_STATUSES: Record<ReferralStatus, ReferralStatus[]> = {
  draft: ["submitted", "cancelled"],
  submitted: ["received", "cancelled"],
  received: ["closed"],
  closed: [],
  cancelled: [],
};

function historyStatusLabel(row: ReferralHistoryOut): string {
  const to = row.to_status ?? "";
  if (!to) return HISTORY_KIND_LABELS[row.kind] ?? row.kind;
  if (row.kind === "received_status") return RECEIVED_STATUS_LABELS[to] ?? to;
  if (row.kind === "status" || row.kind === "created")
    return REFERRING_STATUS_LABELS[to] ?? to;
  return to;
}

function historyStatusColor(row: ReferralHistoryOut): ChipColor {
  switch (row.to_status) {
    case "submitted":
      return "warning";
    case "received":
      return "success";
    case "closed":
      return "default";
    case "cancelled":
      return "error";
    default:
      return row.kind === "created" ? "info" : "default";
  }
}

export default function Referral() {
  const { patientId, referralId } = useParams();
  const navigate = useNavigate();
  const { user } = useUser();
  const userFacilityName = user?.facility_name ?? null;
  const isAdmin = user?.role === "admin";

  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");
  const [reason, setReason] = useState("");
  const [clinicianNote, setClinicianNote] = useState("");

  const [facilityOptions, setFacilityOptions] = useState<FacilityOption[]>([]);
  const [facilityError, setFacilityError] = useState<string | null>(null);

  const [referral, setReferral] = useState<ReferralOut | null>(null);
  const [history, setHistory] = useState<ReferralHistoryOut[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accessDenied, setAccessDenied] = useState<"forbidden" | "not_found" | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(!!referralId);
  const [isCreating, setIsCreating] = useState(false);
  const [statusUpdateNote, setStatusUpdateNote] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [selectedReceivedStatus, setSelectedReceivedStatus] =
    useState<string>("");

  const canCreate = useMemo(() => {
    return (
      Boolean(patientId) &&
      fromFacility.trim().length > 0 &&
      toFacility.trim().length > 0 &&
      reason.trim().length >= 5
    );
  }, [patientId, fromFacility, toFacility, reason]);

  const isReceivingFacility = useMemo(
    () =>
      Boolean(referral && facilityMatches(referral.to_facility, userFacilityName)),
    [referral, userFacilityName],
  );

  const getStatusChip = (
    status: ReferralStatus,
    ref?: ReferralOut | null,
  ): { color: ChipColor; label: string } => {
    const isSender = Boolean(
      ref && facilityMatches(ref.from_facility, userFacilityName),
    );

    switch (status) {
      case "submitted":
        return {
          color: "warning",
          label: isSender
            ? "Referred from Here"
            : `Referred from ${ref?.from_facility ?? "Unknown Facility"}`,
        };

      case "received":
        return {
          color: "success",
          label: `Referred to ${ref?.to_facility ?? "Unknown Facility"}`,
        };

      case "closed":
        return { color: "default", label: "Closed Case" };

      case "cancelled":
        return { color: "error", label: "Cancelled" };

      default:
        return { color: "default", label: status };
    }
  };

  /** Chip colour for the receiving facility's own status (received_facility_status). */
  const receivedStatusColor = (status: ReferralStatus): ChipColor => {
    switch (status) {
      case "received":
        return "success";
      case "cancelled":
        return "error";
      default:
        return "default";
    }
  };

  async function loadFacilities() {
    try {
      const [phcResp, hospitalResp] = await Promise.all([
        api.get<FacilityOption[]>("/facilities", { params: { kind: "phc" } }),
        api.get<FacilityOption[]>("/facilities", {
          params: { kind: "hospital" },
        }),
      ]);
      setFacilityOptions([...phcResp.data, ...hospitalResp.data]);
    } catch (err) {
      setFacilityError(getErrorMessage(err, "Failed to load facilities"));
    }
  }

  useEffect(() => {
    void loadFacilities();
  }, []);

  const loadHistory = useCallback(async (id: string) => {
    setHistoryError(null);
    try {
      const rows = await fetchReferralHistory(id);
      setHistory(rows);
    } catch (err) {
      setHistory([]);
      setHistoryError(getErrorMessage(err, "Failed to load referral history"));
    }
  }, []);

  const loadReferralById = useCallback(
    async (id: string) => {
      setIsLoading(true);
      setError(null);
      setAccessDenied(null);
      try {
        const resp = await api.get<ReferralOut>(`/referrals/${id}`);
        const data = resp.data;
        setReferral(data);
        // Populate form fields from loaded referral
        setFromFacility(data.from_facility);
        setToFacility(data.to_facility);
        setReason(data.reason);
        setClinicianNote(data.clinician_note || "");
        // Derived from the response (not from state that hasn't updated yet).
        setSelectedReceivedStatus(data.received_facility_status || "");
        await loadHistory(data.id);
      } catch (err) {
        if (isForbidden(err)) {
          setAccessDenied("forbidden");
        } else if (isNotFound(err)) {
          setAccessDenied("not_found");
        } else {
          setError(getErrorMessage(err, "Failed to load referral"));
        }
      } finally {
        setIsLoading(false);
      }
    },
    [loadHistory],
  );

  useEffect(() => {
    if (referralId) {
      void loadReferralById(referralId);
    }
  }, [referralId, loadReferralById]);

  // Pre-fill "From facility": non-admins are locked to their own facility
  // (backend rejects anything else); admins default to it but may change it.
  useEffect(() => {
    if (referral) return; // display mode: fields come from the referral
    if (userFacilityName) {
      if (!isAdmin || !fromFacility) setFromFacility(userFacilityName);
      return;
    }
    if (!fromFacility && facilityOptions.length && isAdmin) {
      setFromFacility(facilityOptions[0].name);
    }
  }, [referral, userFacilityName, isAdmin, facilityOptions, fromFacility]);

  // Make sure the locked "from" value is always selectable even if the
  // facility list doesn't contain it (e.g. name mismatch).
  const fromFacilityOptions = useMemo(() => {
    if (!fromFacility) return facilityOptions;
    if (facilityOptions.some((f) => f.name === fromFacility)) return facilityOptions;
    const kind: FacilityOption["kind"] =
      user?.facility_type === "hospital" ? "hospital" : "phc";
    return [{ id: "__own__", name: fromFacility, kind }, ...facilityOptions];
  }, [facilityOptions, fromFacility, user?.facility_type]);

  async function create() {
    if (!patientId) return;
    setError(null);
    setIsCreating(true);
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
      setSelectedReceivedStatus(resp.data.received_facility_status || "");
      await loadHistory(resp.data.id);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to create referral"));
    } finally {
      setIsCreating(false);
    }
  }

  async function setStatus(status: ReferralStatus) {
    if (!referral) return;
    setError(null);
    setIsUpdatingStatus(true);
    try {
      const resp = await api.post<ReferralOut>(
        `/referrals/${referral.id}/status`,
        { status },
      );
      setReferral(resp.data);
      setStatusUpdateNote("");
      await loadHistory(resp.data.id);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to update status"));
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function setReceivedFacilityStatus(status: ReferralStatus) {
    if (!referral) return;
    setError(null);
    setIsUpdatingStatus(true);
    try {
      const resp = await api.post<ReferralOut>(
        `/referrals/${referral.id}/received-status`,
        {
          received_facility_status: status,
          note: statusUpdateNote.trim() || undefined,
        },
      );
      setReferral(resp.data);
      setStatusUpdateNote("");
      setSelectedReceivedStatus(resp.data.received_facility_status || "");
      await loadHistory(resp.data.id);
    } catch (err) {
      setError(
        getErrorMessage(err, "Failed to update received facility status"),
      );
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  const handleSaveReceivedStatus = () => {
    if (selectedReceivedStatus) {
      setReceivedFacilityStatus(selectedReceivedStatus as ReferralStatus);
    }
  };

  const receivedStatusIsTerminal =
    referral?.received_facility_status === "closed" ||
    referral?.received_facility_status === "cancelled";

  if (isLoading && referralId) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#F6F7FB",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  const pageSx = {
    minHeight: "100vh",
    bgcolor: "#F6F7FB",
    py: { xs: 2, md: 3 },
    px: { xs: 0.5, sm: 1, md: 1.5 },
    width: "100%",
    boxSizing: "border-box",
  } as const;

  const topBar = (
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
            <Typography
              variant="h5"
              sx={{ fontWeight: 800, letterSpacing: -0.2 }}
            >
              Patient Referral
            </Typography>
            <Typography
              variant="body2"
              sx={{ opacity: 0.9, lineHeight: 1.7 }}
            >
              Create and manage referral requests with clinical details and
              notes.
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
  );

  if (accessDenied) {
    return (
      <Box sx={pageSx}>
        <Stack spacing={3}>
          {topBar}
          <Card
            sx={{
              borderRadius: 3,
              border: "1px solid rgba(15, 23, 42, 0.10)",
              boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
            }}
          >
            <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
              <Alert
                severity={accessDenied === "forbidden" ? "warning" : "info"}
              >
                {accessDenied === "forbidden"
                  ? "You don't have access to this referral. Only the referring or receiving facility (or an administrator) can view it."
                  : "This referral could not be found."}
              </Alert>
              <Button
                variant="outlined"
                onClick={() => navigate(`/patients/${patientId}`)}
                sx={{ mt: 2, textTransform: "none", fontWeight: 700 }}
              >
                Back to patient
              </Button>
            </CardContent>
          </Card>
        </Stack>
      </Box>
    );
  }

  return (
    <Box sx={pageSx}>
      <Stack spacing={3}>
        {/* Top Bar */}
        {topBar}

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
                <Typography
                  variant="subtitle1"
                  sx={{ fontWeight: 800, color: "#0F172A" }}
                >
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
                      helperText={
                        facilityError ??
                        (isAdmin
                          ? "Select referring facility"
                          : userFacilityName
                            ? "Your facility (referrals are sent from here)"
                            : "Your account has no facility assigned — contact an administrator")
                      }
                      error={Boolean(facilityError) || (!isAdmin && !userFacilityName)}
                      disabled={!isAdmin}
                    >
                      {fromFacilityOptions.map((opt) => (
                        <MenuItem key={opt.id} value={opt.name}>
                          {opt.name}{" "}
                          {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
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
                          {opt.name}{" "}
                          {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
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
                        disabled={!canCreate || isCreating}
                        sx={{
                          textTransform: "none",
                          fontWeight: 700,
                          borderRadius: 2,
                          background: "#4F46E5",
                          "&:hover": { background: "#4338CA" },
                          px: 3,
                        }}
                      >
                        {isCreating ? (
                          <CircularProgress size={20} sx={{ color: "white" }} />
                        ) : (
                          "Create Referral"
                        )}
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
                  <Typography
                    variant="subtitle1"
                    sx={{ fontWeight: 800, color: "#0F172A" }}
                  >
                    Referral Created
                  </Typography>

                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={2}
                    alignItems="flex-start"
                  >
                    <Box flex={1}>
                      <Typography variant="caption" color="text.secondary">
                        Referral ID
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontWeight: 700, mt: 0.5 }}
                      >
                        {referral.id}
                      </Typography>
                    </Box>
                    <Box flex={1}>
                      <Typography variant="caption" color="text.secondary">
                        Status (Referring)
                      </Typography>
                      <Box sx={{ mt: 0.75 }}>
                        <Chip
                          label={getStatusChip(referral.status, referral).label}
                          color={getStatusChip(referral.status, referral).color}
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
                          label={
                            referral.received_facility_status
                              ? RECEIVED_STATUS_LABELS[
                                  referral.received_facility_status
                                ] ?? referral.received_facility_status
                              : "Pending"
                          }
                          color={
                            referral.received_facility_status
                              ? receivedStatusColor(
                                  referral.received_facility_status,
                                )
                              : "default"
                          }
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                  </Stack>
                </Stack>

                <Divider sx={{ my: 1 }} />

                <Stack spacing={2}>
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: 700, color: "#0F172A" }}
                  >
                    Referral Details
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">
                        From Facility
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 600, mt: 0.5 }}
                      >
                        {referral.from_facility}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">
                        To Facility
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 600, mt: 0.5 }}
                      >
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
                        <Typography
                          variant="body2"
                          sx={{ mt: 0.5, whiteSpace: "pre-wrap" }}
                        >
                          {referral.clinician_note}
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </Stack>

                <Divider sx={{ my: 1 }} />

                <Stack spacing={2}>
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: 700, color: "#0F172A" }}
                  >
                    {isReceivingFacility
                      ? "Update Your Status (Received Place)"
                      : "Update Status (Referring)"}
                  </Typography>

                  {isReceivingFacility ? (
                    // Receiving facility: Update their own received_facility_status
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          select
                          label="Your facility status"
                          value={selectedReceivedStatus}
                          onChange={(e) =>
                            setSelectedReceivedStatus(e.target.value)
                          }
                          fullWidth
                          size="small"
                          disabled={isUpdatingStatus || receivedStatusIsTerminal}
                          helperText={
                            receivedStatusIsTerminal
                              ? "This referral is closed on your side"
                              : "Update your facility's acknowledgment of this referral"
                          }
                        >
                          <MenuItem value="received">Admitted Here</MenuItem>
                          <MenuItem value="closed">Closed Case</MenuItem>
                          <MenuItem value="cancelled">
                            Referred Elsewhere
                          </MenuItem>
                        </TextField>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Button
                          variant="contained"
                          onClick={handleSaveReceivedStatus}
                          fullWidth
                          disabled={
                            isUpdatingStatus ||
                            receivedStatusIsTerminal ||
                            !selectedReceivedStatus ||
                            selectedReceivedStatus ===
                              (referral.received_facility_status || "")
                          }
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
                          disabled={isUpdatingStatus || receivedStatusIsTerminal}
                        />
                      </Grid>
                    </Grid>
                  ) : (
                    // Referring facility: manage their own status
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <TextField
                          select
                          label="Your status"
                          value={referral.status}
                          onChange={(e) =>
                            setStatus(e.target.value as ReferralStatus)
                          }
                          fullWidth
                          size="small"
                          disabled={
                            isUpdatingStatus ||
                            SENDER_NEXT_STATUSES[referral.status].length === 0
                          }
                          helperText={
                            SENDER_NEXT_STATUSES[referral.status].length === 0
                              ? "Final state — no further changes"
                              : "Updated automatically when the receiving facility admits or closes the case; you can also change it here."
                          }
                        >
                          {[
                            referral.status,
                            ...SENDER_NEXT_STATUSES[referral.status],
                          ].map((s) => (
                            <MenuItem key={s} value={s}>
                              {REFERRING_STATUS_LABELS[s] ?? s}
                            </MenuItem>
                          ))}
                        </TextField>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: "1px solid #e0e0e0",
                            borderRadius: 1,
                            bgcolor: "#f5f5f5",
                          }}
                        >
                          <Typography variant="caption" color="text.secondary">
                            Received Place Status
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{ fontWeight: 600, mt: 0.5 }}
                          >
                            {referral.received_facility_status
                              ? RECEIVED_STATUS_LABELS[
                                  referral.received_facility_status
                                ] ?? referral.received_facility_status
                              : "Pending acknowledgment"}
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  )}

                  <Divider sx={{ my: 2 }} />
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: 700, color: "#0F172A" }}
                  >
                    Status History
                  </Typography>

                  {historyError && (
                    <Alert severity="warning">{historyError}</Alert>
                  )}

                  {history.length === 0 && !historyError ? (
                    <Typography variant="body2" color="text.secondary">
                      No status updates recorded yet.
                    </Typography>
                  ) : history.length > 0 ? (
                    <Box sx={{ overflowX: "auto" }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow sx={{ backgroundColor: "#f3f4f6" }}>
                            <TableCell sx={{ fontWeight: 600 }}>
                              Date &amp; Time
                            </TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Event</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>By</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Notes</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {history.map((row) => (
                            <TableRow key={row.id} hover>
                              <TableCell sx={{ whiteSpace: "nowrap" }}>
                                {new Date(row.created_at).toLocaleString()}
                              </TableCell>
                              <TableCell>
                                {HISTORY_KIND_LABELS[row.kind] ?? row.kind}
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={historyStatusLabel(row)}
                                  color={historyStatusColor(row)}
                                  variant="outlined"
                                  size="small"
                                />
                              </TableCell>
                              <TableCell>{row.actor_name ?? "-"}</TableCell>
                              <TableCell sx={{ whiteSpace: "pre-wrap" }}>
                                {row.note ?? "-"}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Box>
                  ) : null}

                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 2 }}
                  >
                    {isReceivingFacility ? (
                      <>
                        Note: Only the receiving facility can add notes when
                        updating status.
                      </>
                    ) : (
                      <>
                        Note: All referrals start as "Referred from Here" and
                        are locked until the receiving facility marks them as
                        "Referred to Here". Only the receiving facility can add
                        notes.
                      </>
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
