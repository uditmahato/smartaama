// frontend/src/pages/PatientCreate.tsx
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
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

type PatientCreate = {
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
  occupation?: string | null;
  education_level?: string | null;
  marital_status?: string | null;
  duration_of_marriage?: number | null;
  smoking_use?: boolean;
  alcohol_use?: boolean;
  intoxicant_use?: boolean;
};

type Municipality = {
  local_level_name: string;
  local_level_type: string;
  wards: number;
};

type PatientOut = {
  id: string;
};

export default function PatientCreate() {
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [provinces, setProvinces] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [wards, setWards] = useState<number>(0);

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

  useEffect(() => {
    loadProvinces();
  }, []);

  const loadProvinces = async () => {
    try {
      const resp = await api.get<string[]>("/locations/provinces");
      setProvinces(resp.data);
    } catch (err) {
      console.error("Failed to load provinces", err);
    }
  };

  const loadDistricts = async (province: string) => {
    try {
      const resp = await api.get<string[]>("/locations/districts", { params: { province } });
      setDistricts(resp.data);
    } catch (err) {
      console.error("Failed to load districts", err);
      setDistricts([]);
    }
  };

  const loadMunicipalities = async (province: string, district: string) => {
    try {
      const resp = await api.get<Municipality[]>("/locations/municipalities", { params: { province, district } });
      setMunicipalities(resp.data);
    } catch (err) {
      console.error("Failed to load municipalities", err);
      setMunicipalities([]);
    }
  };

  const loadWards = async (province: string, district: string, municipality: string) => {
    try {
      const resp = await api.get<number>("/locations/wards", { params: { province, district, municipality } });
      setWards(resp.data);
    } catch (err) {
      console.error("Failed to load wards", err);
      setWards(0);
    }
  };

  async function createPatient() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: PatientCreate = {
        ...newPatient,
        first_name: newPatient.first_name.trim(),
        last_name: newPatient.last_name.trim(),
      };
      const resp = await api.post<PatientOut>("/patients", payload);
      setSuccess("Patient created successfully");
      navigate(`/patients/${resp.data.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Create patient failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="h5" sx={{ flex: 1 }}>
              Create Patient
            </Typography>
            <Button variant="outlined" onClick={() => navigate("/patients")}>Back to Search</Button>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}

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
            <Grid item xs={12} sm={4}>
              <TextField
                label="Duration of Marriage (years)"
                type="number"
                value={newPatient.duration_of_marriage ?? ""}
                onChange={(e) => setNewPatient((p) => ({ ...p, duration_of_marriage: e.target.value ? parseInt(e.target.value) : undefined }))}
                fullWidth
              />
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
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Province"
                value={newPatient.province ?? ""}
                onChange={async (e) => {
                  const value = e.target.value;
                  setNewPatient((p) => ({ ...p, province: value, district: "", municipality: "", ward: "" }));
                  setDistricts([]);
                  setMunicipalities([]);
                  setWards(0);
                  if (value) await loadDistricts(value);
                }}
                fullWidth
              >
                <MenuItem value="">Select Province</MenuItem>
                {provinces.map((prov) => (
                  <MenuItem key={prov} value={prov}>
                    {prov}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="District"
                value={newPatient.district ?? ""}
                onChange={async (e) => {
                  const value = e.target.value;
                  setNewPatient((p) => ({ ...p, district: value, municipality: "", ward: "" }));
                  setMunicipalities([]);
                  setWards(0);
                  if (newPatient.province && value) await loadMunicipalities(newPatient.province, value);
                }}
                fullWidth
                disabled={!newPatient.province}
              >
                <MenuItem value="">Select District</MenuItem>
                {districts.map((dist) => (
                  <MenuItem key={dist} value={dist}>
                    {dist}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Metropolitan City / Sub Metropolitan City / Municipality"
                value={newPatient.municipality ?? ""}
                onChange={async (e) => {
                  const value = e.target.value;
                  setNewPatient((p) => ({ ...p, municipality: value, ward: "" }));
                  setWards(0);
                  if (newPatient.province && newPatient.district && value) await loadWards(newPatient.province, newPatient.district, value);
                }}
                fullWidth
                disabled={!newPatient.district}
              >
                <MenuItem value="">Select Municipality</MenuItem>
                {municipalities.map((muni) => (
                  <MenuItem key={muni.local_level_name} value={muni.local_level_name}>
                    {muni.local_level_name} ({muni.local_level_type})
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Ward"
                value={newPatient.ward ?? ""}
                onChange={(e) => setNewPatient((p) => ({ ...p, ward: e.target.value }))}
                fullWidth
                disabled={!newPatient.municipality || wards === 0}
              >
                <MenuItem value="">Select Ward</MenuItem>
                {Array.from({ length: wards }, (_, i) => (
                  <MenuItem key={i + 1} value={(i + 1).toString()}>
                    Ward {i + 1}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Tole Name"
                value={newPatient.address_line ?? ""}
                onChange={(e) => setNewPatient((p) => ({ ...p, address_line: e.target.value }))}
                fullWidth
                multiline
                rows={2}
              />
            </Grid>

            <Grid item xs={12}>
              <Stack direction="row" spacing={2}>
                <Button variant="contained" onClick={createPatient} disabled={!canCreate || busy}>
                  {busy ? <CircularProgress size={20} /> : "Create Patient"}
                </Button>
                <Button variant="text" onClick={() => navigate("/patients")} disabled={busy}>
                  Cancel
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Stack>
  );
}
