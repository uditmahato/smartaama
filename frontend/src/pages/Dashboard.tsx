// frontend/src/pages/Dashboard.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, tokenStore } from "../services/api";

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
  }, []);

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <div>
              <Typography variant="h5">Dashboard</Typography>
              <Typography variant="body2" color="text.secondary">
                Referral inbox and quick access to patient workflows.
              </Typography>
            </div>

            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={() => navigate("/patients")}>
                Patient Search
              </Button>
              <Button
                variant="text"
                color="inherit"
                onClick={() => {
                  tokenStore.clear();
                  navigate("/login", { replace: true });
                }}
              >
                Logout
              </Button>
            </Stack>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}

          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                fullWidth
              >
                <MenuItem value="">All</MenuItem>
                {["draft", "submitted", "received", "closed", "cancelled"].map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                label="From facility (contains)"
                value={fromFacility}
                onChange={(e) => setFromFacility(e.target.value)}
                fullWidth
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                label="To facility (contains)"
                value={toFacility}
                onChange={(e) => setToFacility(e.target.value)}
                fullWidth
              />
            </Grid>

            <Grid item xs={12}>
              <Stack direction="row" spacing={1}>
                <Button variant="contained" onClick={loadReferrals} disabled={busy}>
                  {busy ? <CircularProgress size={20} /> : "Refresh"}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    setStatusFilter("");
                    setFromFacility("");
                    setToFacility("");
                  }}
                >
                  Clear filters
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1">Referrals ({referrals.length})</Typography>
            <Typography variant="body2" color="text.secondary">
              Click a referral’s patient to open timeline.
            </Typography>
          </Stack>

          {busy && referrals.length === 0 ? (
            <CircularProgress />
          ) : (
            <Stack spacing={1}>
              {referrals.map((r) => (
                <Card key={r.id} variant="outlined" sx={{ cursor: "pointer" }} onClick={() => navigate(`/patients/${r.patient_id}`)}>
                  <CardContent>
                    <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
                      <div>
                        <Typography variant="subtitle2">
                          {r.from_facility} → {r.to_facility} | {r.status}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Created: {new Date(r.created_at).toLocaleString()}
                          {r.submitted_at ? ` | Submitted: ${new Date(r.submitted_at).toLocaleString()}` : ""}
                          {r.received_at ? ` | Received: ${new Date(r.received_at).toLocaleString()}` : ""}
                        </Typography>
                      </div>
                      <Typography variant="body2" color="text.secondary">
                        Referral ID: {r.id}
                      </Typography>
                    </Stack>

                    <Divider sx={{ my: 1 }} />

                    <Typography variant="body2">
                      <strong>Reason:</strong> {r.reason}
                    </Typography>
                    {r.clinician_note && (
                      <Typography variant="body2" color="text.secondary">
                        <strong>Clinician note:</strong> {r.clinician_note}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))}

              {referrals.length === 0 && !busy && (
                <Typography variant="body2" color="text.secondary">
                  No referrals match the current filters.
                </Typography>
              )}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
