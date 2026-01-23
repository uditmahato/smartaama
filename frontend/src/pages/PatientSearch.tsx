// frontend/src/pages/PatientSearch.tsx
import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

type PatientOut = {
  id: string;
  facility_mrn?: string | null;
  national_id?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone_number?: string | null;
  district?: string | null;
  created_at: string;
};

type PatientCreate = {
  facility_mrn?: string | null;
  national_id?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone_number?: string | null;
  district?: string | null;
  municipality?: string | null;
  ward?: string | null;
  province?: string | null;
  address_line?: string | null;
};

export default function PatientSearch() {
  const navigate = useNavigate();

  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientOut[]>([]);

  const [creating, setCreating] = useState(false);
  const [newPatient, setNewPatient] = useState<PatientCreate>({
    first_name: "",
    last_name: "",
  });

  const canCreate = useMemo(() => {
    return newPatient.first_name.trim().length > 0 && newPatient.last_name.trim().length > 0;
  }, [newPatient.first_name, newPatient.last_name]);

  async function search() {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.get<PatientOut[]>("/patients", { params: { q: q.trim(), limit: 50 } });
      setPatients(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function createPatient() {
    setBusy(true);
    setError(null);
    try {
      const payload: PatientCreate = {
        ...newPatient,
        first_name: newPatient.first_name.trim(),
        last_name: newPatient.last_name.trim(),
      };
      const resp = await api.post<PatientOut>("/patients", payload);
      navigate(`/patients/${resp.data.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Create patient failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    // initial list (recent)
    search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="h5" sx={{ flex: 1 }}>
              Patient Search
            </Typography>
            <Button variant="outlined" onClick={() => navigate("/")}>
              Back
            </Button>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
            <TextField
              label="Search by name / MRN / phone / national ID"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              fullWidth
            />
            <Button variant="contained" onClick={search} disabled={busy}>
              {busy ? <CircularProgress size={20} /> : "Search"}
            </Button>
            <Button variant="text" onClick={() => setCreating((v) => !v)}>
              {creating ? "Hide Create" : "Create Patient"}
            </Button>
          </Stack>

          {creating && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle1">Register New Patient</Typography>
              <Grid container spacing={2} sx={{ mt: 0.5 }}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="First name"
                    value={newPatient.first_name}
                    onChange={(e) => setNewPatient((p) => ({ ...p, first_name: e.target.value }))}
                    required
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Last name"
                    value={newPatient.last_name}
                    onChange={(e) => setNewPatient((p) => ({ ...p, last_name: e.target.value }))}
                    required
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Phone"
                    value={newPatient.phone_number ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, phone_number: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Facility MRN"
                    value={newPatient.facility_mrn ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, facility_mrn: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="National ID"
                    value={newPatient.national_id ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, national_id: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="District"
                    value={newPatient.district ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, district: e.target.value }))}
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12}>
                  <Button variant="contained" disabled={busy || !canCreate} onClick={createPatient}>
                    {busy ? <CircularProgress size={20} /> : "Create"}
                  </Button>
                </Grid>
              </Grid>
            </Box>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Results ({patients.length})
          </Typography>

          {busy && patients.length === 0 ? (
            <CircularProgress />
          ) : (
            <Stack spacing={1}>
              {patients.map((p) => (
                <Card
                  key={p.id}
                  variant="outlined"
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/patients/${p.id}`)}
                >
                  <CardContent>
                    <Typography variant="subtitle1">
                      {p.first_name} {p.middle_name ?? ""} {p.last_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      MRN: {p.facility_mrn ?? "-"} | Phone: {p.phone_number ?? "-"} | District:{" "}
                      {p.district ?? "-"}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
