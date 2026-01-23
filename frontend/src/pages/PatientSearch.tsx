// frontend/src/pages/PatientSearch.tsx
import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useNavigate, useSearchParams } from "react-router-dom";
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

type PatientCreate = {
  facility_mrn?: string | null;
  national_id?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  age_in_years?: number | null;
  sex?: string | null;
  phone_number?: string | null;
  district?: string | null;
  municipality?: string | null;
  ward?: string | null;
  province?: string | null;
  address_line?: string | null;
  // Patient particulars fields
  occupation?: string | null;
  education_level?: string | null;
  marital_status?: string | null;
  duration_of_marriage?: number | null;
  smoking_use?: boolean;
  alcohol_use?: boolean;
  intoxicant_use?: boolean;
};

export default function PatientSearch() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientOut[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [creating, setCreating] = useState(searchParams.get("create") === "true");
  const [newPatient, setNewPatient] = useState<PatientCreate>({
    first_name: "",
    last_name: "",
    smoking_use: false,
    alcohol_use: false,
    intoxicant_use: false,
  });

  const canCreate = useMemo(() => {
    return newPatient.first_name.trim().length > 0 && newPatient.last_name.trim().length > 0;
  }, [newPatient.first_name, newPatient.last_name]);

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
    // Don't auto-search on page load
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
              <Typography variant="subtitle1" gutterBottom>Register New Patient</Typography>
              <Typography variant="caption" color="text.secondary">Basic Demographics</Typography>
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
                    label="Middle name"
                    value={newPatient.middle_name ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, middle_name: e.target.value }))}
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
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Age (years)"
                    type="number"
                    value={newPatient.age_in_years ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, age_in_years: e.target.value ? parseInt(e.target.value) : undefined }))}
                    fullWidth
                    inputProps={{ min: 0, max: 150 }}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    select
                    label="Sex"
                    value={newPatient.sex ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, sex: e.target.value }))}
                    fullWidth
                  >
                    <MenuItem value="">-</MenuItem>
                    <MenuItem value="Female">Female</MenuItem>
                    <MenuItem value="Male">Male</MenuItem>
                    <MenuItem value="Other">Other</MenuItem>
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Phone"
                    value={newPatient.phone_number ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, phone_number: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Facility MRN"
                    value={newPatient.facility_mrn ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, facility_mrn: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">Patient Particulars</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Occupation"
                    value={newPatient.occupation ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, occupation: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    select
                    label="Education Level"
                    value={newPatient.education_level ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, education_level: e.target.value }))}
                    fullWidth
                  >
                    <MenuItem value="">-</MenuItem>
                    <MenuItem value="None">None</MenuItem>
                    <MenuItem value="Primary">Primary</MenuItem>
                    <MenuItem value="Secondary">Secondary</MenuItem>
                    <MenuItem value="Higher Secondary">Higher Secondary</MenuItem>
                    <MenuItem value="Bachelor">Bachelor</MenuItem>
                    <MenuItem value="Master">Master</MenuItem>
                    <MenuItem value="Other">Other</MenuItem>
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    select
                    label="Marital Status"
                    value={newPatient.marital_status ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, marital_status: e.target.value }))}
                    fullWidth
                  >
                    <MenuItem value="">-</MenuItem>
                    <MenuItem value="Single">Single</MenuItem>
                    <MenuItem value="Married">Married</MenuItem>
                    <MenuItem value="Divorced">Divorced</MenuItem>
                    <MenuItem value="Widowed">Widowed</MenuItem>
                  </TextField>
                </Grid>
                {newPatient.marital_status === "Married" && (
                  <Grid item xs={12} sm={4}>
                    <TextField
                      label="Duration of Marriage (years)"
                      type="number"
                      value={newPatient.duration_of_marriage ?? ""}
                      onChange={(e) => setNewPatient((p) => ({ ...p, duration_of_marriage: parseInt(e.target.value) || null }))}
                      fullWidth
                    />
                  </Grid>
                )}
                
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">Lifestyle</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <label>
                    <input
                      type="checkbox"
                      checked={newPatient.smoking_use ?? false}
                      onChange={(e) => setNewPatient((p) => ({ ...p, smoking_use: e.target.checked }))}
                    />
                    {" "}Smoking Use
                  </label>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <label>
                    <input
                      type="checkbox"
                      checked={newPatient.alcohol_use ?? false}
                      onChange={(e) => setNewPatient((p) => ({ ...p, alcohol_use: e.target.checked }))}
                    />
                    {" "}Alcohol Use
                  </label>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <label>
                    <input
                      type="checkbox"
                      checked={newPatient.intoxicant_use ?? false}
                      onChange={(e) => setNewPatient((p) => ({ ...p, intoxicant_use: e.target.checked }))}
                    />
                    {" "}Intoxicant Use
                  </label>
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary">Address</Typography>
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Address Line"
                    value={newPatient.address_line ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, address_line: e.target.value }))}
                    fullWidth
                    multiline
                    rows={2}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Ward"
                    value={newPatient.ward ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, ward: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Municipality"
                    value={newPatient.municipality ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, municipality: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="District"
                    value={newPatient.district ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, district: e.target.value }))}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Province"
                    value={newPatient.province ?? ""}
                    onChange={(e) => setNewPatient((p) => ({ ...p, province: e.target.value }))}
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12}>
                  <Button variant="contained" disabled={busy || !canCreate} onClick={createPatient}>
                    {busy ? <CircularProgress size={20} /> : "Create Patient"}
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
                      Patient ID: {p.patient_id} | Age: {p.age_in_years ?? "-"} years
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
