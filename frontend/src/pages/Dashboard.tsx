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
import {
  api,
  facilityMatches,
  getErrorMessage,
  type ReferralOut,
} from "../services/api";
import type { FacilityOption } from "../services/types";
import { useUser } from "../hooks/useUser";

import { navLinks } from "../components/Navbar";
import Navbar from "../components/Navbar";

type StatusFilter = "" | "to_here" | "from_here" | "admitted" | "closed";

const STATUS_FILTER_LABELS: Record<Exclude<StatusFilter, "">, string> = {
  to_here: "Referred to Here",
  from_here: "Referred from Here",
  admitted: "Admitted Case",
  closed: "Closed Case",
};

type ChipColor = "default" | "warning" | "success" | "error";

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useUser();
  const userFacilityName = user?.facility_name ?? null;

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");
  const [facilityOptions, setFacilityOptions] = useState<FacilityOption[]>([]);
  const [facilityError, setFacilityError] = useState<string | null>(null);

  const [referrals, setReferrals] = useState<ReferralOut[]>([]);

  const params = useMemo(() => {
    const p: Record<string, string | number> = { limit: 50, offset: 0 };
    // Filter mapping (backend contract): `direction` is relative to the caller's facility.
    switch (statusFilter) {
      case "to_here":
        p.direction = "incoming";
        break;
      case "from_here":
        p.direction = "outgoing";
        break;
      case "admitted":
        p.direction = "incoming";
        p.received_status = "received";
        break;
      case "closed":
        p.status = "closed";
        break;
      default:
        break;
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
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load referrals"));
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
    } catch (err) {
      setFacilityError(getErrorMessage(err, "Failed to load facilities"));
    }
  }

  useEffect(() => {
    loadReferrals();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  useEffect(() => {
    void loadFacilities();
  }, []);

  const getStatusChip = (
    status: ReferralOut["status"],
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
                  onChange={(e) =>
                    setStatusFilter(e.target.value as StatusFilter)
                  }
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
                  ? `Status: ${STATUS_FILTER_LABELS[statusFilter]}`
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
                  const chip = getStatusChip(referral.status, referral);
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
                            label={chip.label}
                            color={chip.color}
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
