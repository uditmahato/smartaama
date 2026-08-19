// frontend/src/pages/PatientSearch.tsx
import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { api, getErrorMessage } from "../services/api";
import Navbar, { navLinks } from "../components/Navbar";

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
      const resp = await api.get<PatientOut[]>("/patients", {
        params: { q: q.trim(), limit: 50 },
      });
      setPatients(resp.data);
    } catch (err) {
      setError(getErrorMessage(err, "Search failed"));
    } finally {
      setBusy(false);
    }
  }

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
        title="Search Patients"
        subtitle="Find patient records by name, ID, phone, or national ID."
        links={navLinks}
      />

      {/* Search Box */}
      <CardContent sx={{ p: { xs: 2.5, md: 3.5 }, bgcolor: "white" }}>
        <Stack spacing={2}>
          <Typography
            variant="subtitle1"
            sx={{ fontWeight: 800, color: "#0F172A" }}
          >
            Quick Search
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ xs: "flex-start", sm: "center" }}
          >
            <TextField
              label="Search by name / MRN / phone / national ID"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              fullWidth
              size="small"
              sx={{ flex: 1 }}
            />
            <Button
              variant="contained"
              onClick={search}
              disabled={busy}
              sx={{
                textTransform: "none",
                fontWeight: 700,
                borderRadius: 2,
                background: "#4F46E5",
                "&:hover": { background: "#4338CA" },
                whiteSpace: "nowrap",
                px: 3,
              }}
            >
              {busy ? <CircularProgress size={20} /> : "Search"}
            </Button>
          </Stack>
        </Stack>
      </CardContent>

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
                Results {hasSearched ? `(${patients.length})` : ""}
              </Typography>
              {busy && <CircularProgress size={20} />}
            </Stack>

            {busy && patients.length === 0 ? (
              <Box sx={{ py: 4, textAlign: "center" }}>
                <CircularProgress />
              </Box>
            ) : !hasSearched ? (
              <Box
                sx={{
                  color: "text.secondary",
                  fontSize: 14,
                  py: 3,
                  textAlign: "center",
                }}
              >
                Search to see patient results.
              </Box>
            ) : patients.length === 0 ? (
              <Box
                sx={{
                  color: "text.secondary",
                  fontSize: 14,
                  py: 3,
                  textAlign: "center",
                }}
              >
                No patients found.
              </Box>
            ) : (
              <Stack spacing={1.5}>
                {patients.map((p) => (
                  <Card
                    key={p.id}
                    sx={{
                      cursor: "pointer",
                      border: "1px solid rgba(15, 23, 42, 0.08)",
                      borderRadius: 2,
                      transition: "all 0.2s ease",
                      "&:hover": {
                        boxShadow: "0 4px 16px rgba(15, 23, 42, 0.12)",
                        borderColor: "#667eea",
                      },
                    }}
                    onClick={() => navigate(`/patients/${p.id}`)}
                  >
                    <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
                      <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} sm={6}>
                          <Typography
                            variant="subtitle2"
                            sx={{ fontWeight: 700, color: "#0F172A" }}
                          >
                            {p.first_name} {p.middle_name ?? ""} {p.last_name}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", mt: 0.5 }}
                          >
                            MRN: {p.facility_mrn ?? p.patient_id ?? "-"}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Stack
                            direction="row"
                            spacing={2}
                            justifyContent={{
                              xs: "flex-start",
                              sm: "flex-end",
                            }}
                          >
                            <Box>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                Age
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{ fontWeight: 600 }}
                              >
                                {p.age_in_years ?? "-"} years
                              </Typography>
                            </Box>
                            <Box>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                Phone
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{ fontWeight: 600 }}
                              >
                                {p.phone_number ?? "-"}
                              </Typography>
                            </Box>
                          </Stack>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
