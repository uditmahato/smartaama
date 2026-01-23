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
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, tokenStore } from "../services/api";
import SearchIcon from "@mui/icons-material/Search";
import LogoutIcon from "@mui/icons-material/Logout";

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "submitted":
        return "warning";
      case "received":
        return "success";
      case "closed":
        return "default";
      case "cancelled":
        return "error";
      default:
        return "info";
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", background: "#f8f9fa", py: 4 }}>
      <Container maxWidth="lg">
        <Stack spacing={4}>
          {/* Header */}
          <Box sx={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", borderRadius: 2, p: 4, color: "white" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Stack spacing={1}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  Dashboard
                </Typography>
                <Typography variant="body1" sx={{ opacity: 0.9 }}>
                  Manage referrals and patient care workflows
                </Typography>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ width: { xs: "100%", sm: "auto" } }}>
                <Button
                  variant="contained"
                  sx={{
                    background: "white",
                    color: "#667eea",
                    fontWeight: 600,
                    "&:hover": { background: "#f5f5f5" },
                  }}
                  onClick={() => navigate("/patients?create=true")}
                >
                  👤 Add Patient
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<SearchIcon />}
                  sx={{
                    borderColor: "white",
                    color: "white",
                    fontWeight: 600,
                    "&:hover": { background: "rgba(255, 255, 255, 0.1)" },
                  }}
                  onClick={() => navigate("/patients")}
                >
                  Search
                </Button>
                <Button
                  variant="text"
                  startIcon={<LogoutIcon />}
                  sx={{
                    color: "white",
                    fontWeight: 600,
                    "&:hover": { background: "rgba(255, 255, 255, 0.1)" },
                  }}
                  onClick={() => {
                    tokenStore.clear();
                    navigate("/login", { replace: true });
                  }}
                >
                  Logout
                </Button>
              </Stack>
            </Stack>
          </Box>

          {/* Filters Card */}
          <Card sx={{ boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)" }}>
            <CardContent>
              <Stack spacing={3}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  📋 Referrals Inbox
                </Typography>

                <Grid container spacing={2}>
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
                      label="From Facility"
                      value={fromFacility}
                      onChange={(e) => setFromFacility(e.target.value)}
                      fullWidth
                      size="small"
                      placeholder="Filter by facility"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <TextField
                      label="To Facility"
                      value={toFacility}
                      onChange={(e) => setToFacility(e.target.value)}
                      fullWidth
                      size="small"
                      placeholder="Filter by facility"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={3} sx={{ display: "flex", gap: 1 }}>
                    <Button
                      variant="contained"
                      onClick={loadReferrals}
                      disabled={busy}
                      fullWidth
                      sx={{
                        background: "#667eea",
                        "&:hover": { background: "#5568d3" },
                      }}
                    >
                      {busy ? <CircularProgress size={20} /> : "Refresh"}
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setStatusFilter("submitted");
                        setFromFacility("");
                        setToFacility("");
                      }}
                    >
                      Reset
                    </Button>
                  </Grid>
                </Grid>
              </Stack>
            </CardContent>
          </Card>

          {error && <Alert severity="error">{error}</Alert>}

          {/* Results Section */}
          <Card sx={{ boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)" }}>
            <CardContent>
              <Stack spacing={3}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    Results ({referrals.length})
                  </Typography>
                  {busy && <CircularProgress size={24} />}
                </Box>

                {referrals.length === 0 && !busy ? (
                  <Box
                    sx={{
                      textAlign: "center",
                      py: 6,
                      color: "text.secondary",
                    }}
                  >
                    <Typography variant="body1">No referrals match the current filters.</Typography>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Create a new referral or adjust your filter criteria.
                    </Typography>
                  </Box>
                ) : (
                  <Stack spacing={2}>
                    {referrals.map((referral) => (
                      <Card
                        key={referral.id}
                        variant="outlined"
                        sx={{
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                          border: "1px solid #e0e0e0",
                          "&:hover": {
                            boxShadow: "0 4px 12px rgba(102, 126, 234, 0.15)",
                            borderColor: "#667eea",
                            transform: "translateY(-2px)",
                          },
                        }}
                        onClick={() => navigate(`/patients/${referral.patient_id}`)}
                      >
                        <CardContent>
                          <Stack direction="row" justifyContent="space-between" alignItems="start" spacing={2}>
                            <Stack spacing={1} sx={{ flex: 1 }}>
                              <Stack direction="row" alignItems="center" spacing={2} flexWrap="wrap">
                                <Typography variant="h6" sx={{ fontWeight: 600, flex: 1, minWidth: 300 }}>
                                  {referral.from_facility} → {referral.to_facility}
                                </Typography>
                                <Chip
                                  label={referral.status.toUpperCase()}
                                  size="small"
                                  color={getStatusColor(referral.status) as any}
                                  variant="outlined"
                                />
                              </Stack>
                              <Typography variant="body2" color="text.secondary">
                                <strong>Reason:</strong> {referral.reason}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Created: {new Date(referral.created_at).toLocaleDateString()}
                                {referral.submitted_at && ` • Submitted: ${new Date(referral.submitted_at).toLocaleDateString()}`}
                              </Typography>
                            </Stack>
                          </Stack>
                        </CardContent>
                      </Card>
                    ))}
                  </Stack>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Stack>
      </Container>
    </Box>
  );
}
