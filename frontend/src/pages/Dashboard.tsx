// frontend/src/pages/Dashboard.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, userStore } from "../services/api";

import { navLinks } from "../components/Navbar";
import Navbar from "../components/Navbar";

type ReferralOut = {
  id: string;
  patient_id: string;
  from_facility: string;
  to_facility: string;
  status: "draft" | "submitted" | "received" | "closed" | "cancelled";
  reason: string;
  clinician_decision?: string | null;
  clinician_note?: string | null;
  submitted_at?: string | null;
  received_at?: string | null;
  closed_at?: string | null;
  created_at: string;
};

type UserInfo = {
  id: string;
  username: string;
  full_name?: string | null;
  role: string;
  facility_type?: string | null;
  facility_id?: string | null;
  facility_name?: string | null;
};

type FacilityOption = {
  id: string;
  name: string;
  kind: "phc" | "hospital";
};

export default function Dashboard() {
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>("User");
  const [facilityLabel, setFacilityLabel] = useState<string>(
    "Healthcare Provider",
  );
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const [statusFilter, setStatusFilter] = useState<
    ReferralOut["status"] | "admitted" | "to_here" | "from_here" | ""
  >("");
  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");
  const [facilityOptions, setFacilityOptions] = useState<FacilityOption[]>([]);
  const [facilityError, setFacilityError] = useState<string | null>(null);
  const [userFacilityName, setUserFacilityName] = useState<string | null>(null);

  const [referrals, setReferrals] = useState<ReferralOut[]>([]);

  const params = useMemo(() => {
    const p: Record<string, any> = { limit: 50, offset: 0 };
    if (statusFilter) {
      if (statusFilter === "admitted") {
        // Map "Admitted Case" to received for now (backend has no separate admitted status)
        p.status = "received";
      } else if (statusFilter === "closed") {
        p.status = "closed";
      } else if (statusFilter === "from_here") {
        // Outgoing referrals: submitted from this facility
        p.status = "submitted";
      } else if (statusFilter === "to_here") {
        // Incoming referrals: received at this facility
        p.status = "received";
      }
    }
    if (fromFacility.trim()) p.from_facility = fromFacility.trim();
    if (toFacility.trim()) p.to_facility = toFacility.trim();
    return p;
  }, [statusFilter, fromFacility, toFacility]);

  async function loadReferrals() {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<ReferralOut[]>("/referrals", { params });
      setReferrals(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to load referrals");
    } finally {
      setBusy(false);
    }
  }

  async function loadFacilities() {
    try {
      const [phcResp, hospitalResp] = await Promise.all([
        api.get<FacilityOption[]>("/facilities", { params: { kind: "phc" } }),
        api.get<FacilityOption[]>("/facilities", {
          params: { kind: "hospital" },
        }),
      ]);
      setFacilityOptions([...phcResp.data, ...hospitalResp.data]);
    } catch (err: any) {
      setFacilityError(
        err?.response?.data?.detail ?? "Failed to load facilities",
      );
    }
  }

  useEffect(() => {
    loadReferrals();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  useEffect(() => {
    loadUserInfo();
    void loadFacilities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formatFacility = (u: UserInfo) => {
    if (u.facility_name) {
      const suffix = u.facility_type === "hospital" ? "Hos" : "PHC";
      return `${u.facility_name} (${suffix})`;
    }
    return "Healthcare Provider";
  };

  async function loadUserInfo() {
    const cached = userStore.get() as UserInfo | null;
    if (cached) {
      setUserName(cached.full_name || cached.username);
      setFacilityLabel(formatFacility(cached));
      setUserFacilityName(cached.facility_name ?? null);

      return;
    }
    try {
      const resp = await api.get<UserInfo>("/auth/me");
      userStore.set(resp.data);
      setUserName(resp.data.full_name || resp.data.username);
      setFacilityLabel(formatFacility(resp.data));
      setUserFacilityName(resp.data.facility_name ?? null);
    } catch (err) {
      console.error("Failed to load user info", err);
    }
  }

  const getStatusChip = (
    status: ReferralOut["status"],
    ref?: ReferralOut | null,
  ) => {
    const userFacility = userFacilityName;

    const isSender = ref && userFacility && ref.from_facility === userFacility;

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
        return { color: "success", label: "Admitted Case" };

      default:
        return { color: "default", label: status };
    }
  };
  const resetFilters = () => {
    setStatusFilter("");
    setFromFacility("");
    setToFacility("");
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#F6F7FB",
        py: { xs: 2, md: 3 },
        px: { xs: 0.5, sm: 1, md: 1.5 },
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <Navbar
        title="Dashboard"
        subtitle="Referrals overview and patient workflow access."
        links={navLinks}
      />
      <Card>
        {/* Filters */}
        <CardContent sx={{ p: { xs: 2.5, md: 3.5 }, bgcolor: "white" }}>
          <Stack spacing={2}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 800, color: "#0F172A" }}
              >
                Referrals
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                {busy && <CircularProgress size={18} />}
                <Typography variant="caption" color="text.secondary">
                  Showing {referrals.length}
                </Typography>
              </Stack>
            </Stack>

            <Grid container spacing={2} alignItems="flex-start">
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  select
                  label="Status"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as any)}
                  fullWidth
                  size="small"
                  helperText="Filter by status"
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="to_here">Referred to Here</MenuItem>
                  <MenuItem value="from_here">Referred from Here</MenuItem>
                  <MenuItem value="admitted">Admitted Case</MenuItem>
                  <MenuItem value="closed">Closed Case</MenuItem>
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  select
                  label="From facility"
                  value={fromFacility}
                  onChange={(e) => setFromFacility(e.target.value)}
                  fullWidth
                  size="small"
                  helperText={facilityError ?? "Filter by originating facility"}
                  error={Boolean(facilityError)}
                >
                  <MenuItem value="">All facilities</MenuItem>
                  {facilityOptions.map((opt) => (
                    <MenuItem key={opt.id} value={opt.name}>
                      {opt.name} {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  select
                  label="To facility"
                  value={toFacility}
                  onChange={(e) => setToFacility(e.target.value)}
                  fullWidth
                  size="small"
                  helperText={facilityError ?? "Filter by receiving facility"}
                  error={Boolean(facilityError)}
                >
                  <MenuItem value="">All facilities</MenuItem>
                  {facilityOptions.map((opt) => (
                    <MenuItem key={opt.id} value={opt.name}>
                      {opt.name} {opt.kind === "hospital" ? "(Hos)" : "(PHC)"}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid
                item
                xs={12}
                sm={6}
                md={3}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  height: "100%",
                }}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ width: "100%", alignItems: "stretch" }}
                >
                  <Button
                    variant="contained"
                    onClick={loadReferrals}
                    disabled={busy}
                    fullWidth
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      background: "#4F46E5",
                      "&:hover": { background: "#4338CA" },
                    }}
                  >
                    {busy ? <CircularProgress size={20} /> : "Refresh"}
                  </Button>

                  <Button
                    variant="outlined"
                    onClick={resetFilters}
                    disabled={busy}
                    fullWidth
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      whiteSpace: "nowrap",
                    }}
                  >
                    Reset
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </Stack>
        </CardContent>
      </Card>

      {error && <Alert severity="error">{error}</Alert>}

      {/* Results */}
      <Card
        sx={{
          borderRadius: 3,
          border: "1px solid rgba(15, 23, 42, 0.10)",
          boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
        }}
      >
        <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
          <Stack spacing={2}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 800, color: "#0F172A" }}
              >
                Inbox
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {statusFilter
                  ? `Status: ${statusFilter === "to_here" ? "Referred to Here" : statusFilter === "from_here" ? "Referred from Here" : statusFilter === "admitted" ? "Admitted Case" : "Closed Case"}`
                  : "All statuses"}
              </Typography>
            </Stack>

            {referrals.length === 0 && !busy ? (
              <Box sx={{ py: 6, textAlign: "center" }}>
                <Typography
                  variant="body1"
                  sx={{ fontWeight: 700, color: "#0F172A" }}
                >
                  No referrals found
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  Adjust filters or refresh to load the latest referrals.
                </Typography>
              </Box>
            ) : (
              <Stack spacing={1.25}>
                {referrals.map((referral) => {
                  const chip = getStatusChip(referral.status);
                  return (
                    <Card
                      key={referral.id}
                      variant="outlined"
                      onClick={() =>
                        navigate(`/patients/${referral.patient_id}`)
                      }
                      sx={{
                        borderRadius: 2.5,
                        borderColor: "rgba(15, 23, 42, 0.12)",
                        cursor: "pointer",
                        transition:
                          "box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease",
                        "&:hover": {
                          borderColor: "rgba(79, 70, 229, 0.45)",
                          boxShadow: "0 10px 22px rgba(15, 23, 42, 0.08)",
                          transform: "translateY(-1px)",
                        },
                      }}
                    >
                      <CardContent sx={{ p: 2.25 }}>
                        <Stack
                          direction={{ xs: "column", sm: "row" }}
                          spacing={1.25}
                          justifyContent="space-between"
                          alignItems={{ xs: "flex-start", sm: "center" }}
                        >
                          <Stack spacing={0.6} sx={{ minWidth: 0 }}>
                            <Typography
                              variant="subtitle1"
                              sx={{
                                fontWeight: 800,
                                color: "#0F172A",
                                lineHeight: 1.35,
                              }}
                            >
                              {referral.from_facility} → {referral.to_facility}
                            </Typography>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ lineHeight: 1.7 }}
                            >
                              {referral.reason}
                            </Typography>

                            <Typography
                              variant="caption"
                              color="text.secondary"
                            >
                              Created{" "}
                              {new Date(
                                referral.created_at,
                              ).toLocaleDateString()}
                              {referral.submitted_at
                                ? ` • Submitted ${new Date(referral.submitted_at).toLocaleDateString()}`
                                : ""}
                            </Typography>
                          </Stack>

                          <Chip
                            label={
                              getStatusChip(referral.status, referral).label
                            }
                            color={
                              getStatusChip(referral.status, referral)
                                .color as any
                            }
                            variant="outlined"
                          />
                        </Stack>
                      </CardContent>
                    </Card>
                  );
                })}
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
