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
  Container,
  Grid,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, tokenStore, userStore } from "../services/api";
import SearchIcon from "@mui/icons-material/Search";
import LogoutIcon from "@mui/icons-material/Logout";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";

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

export default function Dashboard() {
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>("User");
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const [statusFilter, setStatusFilter] = useState<ReferralOut["status"] | "">("submitted");
  const [fromFacility, setFromFacility] = useState("");
  const [toFacility, setToFacility] = useState("");

  const [referrals, setReferrals] = useState<ReferralOut[]>([]);

  const params = useMemo(() => {
    const p: Record<string, any> = { limit: 50, offset: 0 };
    if (statusFilter) p.status = statusFilter;
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

  useEffect(() => {
    loadReferrals();
    loadUserInfo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  async function loadUserInfo() {
    const cached = userStore.get();
    if (cached) {
      setUserName(cached.full_name || cached.username);
      return;
    }
    try {
      const resp = await api.get("/auth/me");
      userStore.set(resp.data);
      setUserName(resp.data.full_name || resp.data.username);
    } catch (err) {
      console.error("Failed to load user info", err);
    }
  }

  const getStatusChip = (status: ReferralOut["status"]) => {
    // Keep colors conservative and semantically consistent
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

  const resetFilters = () => {
    setStatusFilter("submitted");
    setFromFacility("");
    setToFacility("");
  };

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F7FB", py: { xs: 2, md: 3 }, px: { xs: 0.5, sm: 1, md: 1.5 } }}>
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
                    Dashboard
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9, lineHeight: 1.7 }}>
                    Referrals overview and patient workflow access.
                  </Typography>
                </Stack>

                <Stack
                  direction="row"
                  spacing={1.25}
                  sx={{ width: { xs: "100%", md: "auto" } }}
                  justifyContent={{ xs: "space-between", md: "flex-end" }}
                  alignItems="center"
                >
                  <Button
                    variant="contained"
                    onClick={() => navigate("/patients?create=true")}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      background: "rgba(255,255,255,0.95)",
                      color: "#4C51BF",
                      "&:hover": { background: "white" },
                      flex: { xs: 1, md: "unset" },
                      px: 2.25,
                    }}
                  >
                    Add patient
                  </Button>

                  <Button
                    variant="outlined"
                    startIcon={<SearchIcon />}
                    onClick={() => navigate("/patients")}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      borderColor: "rgba(255,255,255,0.65)",
                      color: "white",
                      "&:hover": { borderColor: "rgba(255,255,255,0.95)", background: "rgba(255,255,255,0.10)" },
                      flex: { xs: 1, md: "unset" },
                      px: 2.25,
                    }}
                  >
                    Patients
                  </Button>

                  <Box
                    sx={{
                      ml: { xs: 0, md: 2 },
                      pl: { xs: 0, md: 2 },
                      borderLeft: { xs: "none", md: "1px solid rgba(255,255,255,0.2)" },
                      display: { xs: "none", sm: "block" },
                    }}
                  >
                    <Button
                      onClick={(e) => setAnchorEl(e.currentTarget)}
                      endIcon={<ArrowDropDownIcon />}
                      sx={{
                        textTransform: "none",
                        color: "white",
                        borderRadius: 2,
                        px: 1.5,
                        py: 0.75,
                        "&:hover": { background: "rgba(255,255,255,0.10)" },
                      }}
                    >
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <AccountCircleIcon sx={{ fontSize: 24 }} />
                        <Stack spacing={0} alignItems="flex-start">
                          <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2, fontSize: 13 }}>
                            {userName}
                          </Typography>
                          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.75)", lineHeight: 1, fontSize: 10 }}>
                            Healthcare Provider
                          </Typography>
                        </Stack>
                      </Stack>
                    </Button>

                    <Menu
                      anchorEl={anchorEl}
                      open={menuOpen}
                      onClose={() => setAnchorEl(null)}
                      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                      transformOrigin={{ vertical: "top", horizontal: "right" }}
                      slotProps={{
                        paper: {
                          sx: {
                            mt: 1,
                            minWidth: 180,
                            borderRadius: 2,
                            boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
                          },
                        },
                      }}
                    >
                      <MenuItem
                        onClick={() => {
                          setAnchorEl(null);
                          tokenStore.clear();
                          navigate("/login", { replace: true });
                        }}
                        sx={{ py: 1.5, px: 2 }}
                      >
                        <LogoutIcon sx={{ mr: 1.5, fontSize: 20, color: "text.secondary" }} />
                        <Typography variant="body2">Logout</Typography>
                      </MenuItem>
                    </Menu>
                  </Box>

                  <IconButton
                    onClick={() => {
                      tokenStore.clear();
                      navigate("/login", { replace: true });
                    }}
                    sx={{
                      display: { xs: "flex", sm: "none" },
                      color: "white",
                    }}
                  >
                    <LogoutIcon />
                  </IconButton>
                </Stack>
              </Stack>
            </Box>

            {/* Filters */}
            <CardContent sx={{ p: { xs: 2.5, md: 3.5 }, bgcolor: "white" }}>
              <Stack spacing={2}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                    Referrals
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {busy && <CircularProgress size={18} />}
                    <Typography variant="caption" color="text.secondary">
                      Showing {referrals.length}
                    </Typography>
                  </Stack>
                </Stack>

                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={6} md={3}>
                    <TextField
                      select
                      label="Status"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value as any)}
                      fullWidth
                      size="small"
                    >
                      <MenuItem value="">All</MenuItem>
                      <MenuItem value="draft">Draft</MenuItem>
                      <MenuItem value="submitted">Submitted</MenuItem>
                      <MenuItem value="received">Received</MenuItem>
                      <MenuItem value="closed">Closed</MenuItem>
                      <MenuItem value="cancelled">Cancelled</MenuItem>
                    </TextField>
                  </Grid>

                  <Grid item xs={12} sm={6} md={3}>
                    <TextField
                      label="From facility"
                      value={fromFacility}
                      onChange={(e) => setFromFacility(e.target.value)}
                      fullWidth
                      size="small"
                    />
                  </Grid>

                  <Grid item xs={12} sm={6} md={3}>
                    <TextField
                      label="To facility"
                      value={toFacility}
                      onChange={(e) => setToFacility(e.target.value)}
                      fullWidth
                      size="small"
                    />
                  </Grid>

                  <Grid item xs={12} sm={6} md={3}>
                    <Stack direction="row" spacing={1}>
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
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                    Inbox
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {statusFilter ? `Status: ${statusFilter}` : "All statuses"}
                  </Typography>
                </Stack>

                {referrals.length === 0 && !busy ? (
                  <Box sx={{ py: 6, textAlign: "center" }}>
                    <Typography variant="body1" sx={{ fontWeight: 700, color: "#0F172A" }}>
                      No referrals found
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
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
                          onClick={() => navigate(`/patients/${referral.patient_id}`)}
                          sx={{
                            borderRadius: 2.5,
                            borderColor: "rgba(15, 23, 42, 0.12)",
                            cursor: "pointer",
                            transition: "box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease",
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

                                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                                  {referral.reason}
                                </Typography>

                                <Typography variant="caption" color="text.secondary">
                                  Created {new Date(referral.created_at).toLocaleDateString()}
                                  {referral.submitted_at
                                    ? ` • Submitted ${new Date(referral.submitted_at).toLocaleDateString()}`
                                    : ""}
                                </Typography>
                              </Stack>

                              <Chip
                                label={chip.label}
                                size="small"
                                color={chip.color as any}
                                variant="outlined"
                                sx={{ fontWeight: 700 }}
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
        </Stack>
    </Box>
  );
}
