// frontend/src/pages/PatientSearch.tsx
import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, CircularProgress, Divider, Stack, TextField, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

type PatientOut = {
  id: string;
  patient_id: string;
  facility_mrn?: string | null;
  national_id?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  age_in_years?: number | null;
  sex?: string | null;
  phone_number?: string | null;
  district?: string | null;
  created_at: string;
};

export default function PatientSearch() {
  const navigate = useNavigate();

  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientOut[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  async function search() {
    setBusy(true);
    setError(null);
    setHasSearched(true);
    try {
      const resp = await api.get<PatientOut[]>("/patients", { params: { q: q.trim(), limit: 50 } });
      setPatients(resp.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Search failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    // intentionally no auto-search on load
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
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Results {hasSearched ? `(${patients.length})` : ""}
          </Typography>

          {busy && patients.length === 0 ? (
            <CircularProgress />
          ) : !hasSearched ? (
            <Box sx={{ color: "text.secondary", fontSize: 14 }}>Search to see patient results.</Box>
          ) : patients.length === 0 ? (
            <Box sx={{ color: "text.secondary", fontSize: 14 }}>No patients found.</Box>
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
                      Patient ID / MRN: {p.facility_mrn ?? p.patient_id ?? "-"} | Age: {p.age_in_years ?? "-"} years
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Phone: {p.phone_number ?? "-"} | District: {p.district ?? "-"}
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
