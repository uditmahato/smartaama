// frontend/src/pages/PatientProfile.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
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

type ClinicalEventOut = {
  id: string;
  patient_id: string;
  created_by_user_id?: string | null;
  event_time: string;
  section: string;
  factor: string;
  value: Record<string, any>;
  note?: string | null;
  referral_id?: string | null;
  created_at: string;
};

function formatValue(v: any): string {
  if (!v) return "-";
  const t = v.type;
  const val = v.value;

  let rendered =
    typeof val === "object" ? JSON.stringify(val) : val === null || val === undefined ? "-" : String(val);

  if (t === "boolean") rendered = String(Boolean(val));
  if (v.display && t === "code") rendered = `${v.display}${v.code ? ` (${v.code})` : ""}`;

  return `${t ? `${t}: ` : ""}${rendered}${v.unit ? ` ${v.unit}` : ""}`;
}

export default function PatientProfile() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [patient, setPatient] = useState<PatientOut | null>(null);
  const [events, setEvents] = useState<ClinicalEventOut[]>([]);

  // UI controls
  const [sectionFilter, setSectionFilter] = useState<string>("");
  const [factorFilter, setFactorFilter] = useState<string>("");

  async function load() {
    if (!patientId) return;
    setBusy(true);
    setError(null);
    try {
      const p = await api.get<PatientOut>(`/patients/${patientId}`);
      setPatient(p.data);

      const e = await api.get<ClinicalEventOut[]>(`/events`, {
        params: { patient_id: patientId, limit: 1000, offset: 0 },
      });
      setEvents(e.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to load patient");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  const sections = useMemo(() => {
    const s = new Set<string>();
    for (const e of events) s.add(e.section);
    return Array.from(s).sort((a, b) => a.localeCompare(b));
  }, [events]);

  // Latest-per-factor snapshot grouped by section
  const summaryBySection = useMemo(() => {
    // events from API already sorted asc in backend; but do not rely on it.
    const sorted = [...events].sort((a, b) => {
      const ta = new Date(a.event_time).getTime();
      const tb = new Date(b.event_time).getTime();
      if (ta !== tb) return ta - tb;
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    });

    // section -> factor -> latest event
    const map = new Map<string, Map<string, ClinicalEventOut>>();
    for (const ev of sorted) {
      if (!map.has(ev.section)) map.set(ev.section, new Map());
      map.get(ev.section)!.set(ev.factor, ev);
    }

    // convert to arrays for rendering
    const out: Array<{ section: string; items: Array<{ factor: string; ev: ClinicalEventOut }> }> = [];
    for (const [section, factorMap] of map.entries()) {
      const items = Array.from(factorMap.entries())
        .map(([factor, ev]) => ({ factor, ev }))
        .sort((a, b) => a.factor.localeCompare(b.factor));
      out.push({ section, items });
    }

    out.sort((a, b) => a.section.localeCompare(b.section));
    return out;
  }, [events]);

  const filteredTimeline = useMemo(() => {
    return events.filter((ev) => {
      if (sectionFilter && ev.section !== sectionFilter) return false;
      if (factorFilter.trim() && !ev.factor.toLowerCase().includes(factorFilter.trim().toLowerCase())) return false;
      return true;
    });
  }, [events, sectionFilter, factorFilter]);

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="center">
            <div>
              <Typography variant="h5">Patient Profile</Typography>
              <Typography variant="body2" color="text.secondary">
                Snapshot (latest per factor) plus full immutable timeline.
              </Typography>
            </div>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={() => navigate("/patients")}>
                Back
              </Button>
              <Button variant="contained" onClick={() => navigate(`/patients/${patientId}/update`)}>
                Update Record
              </Button>
              <Button variant="outlined" onClick={() => navigate(`/patients/${patientId}/referral`)}>
                Referral
              </Button>
            </Stack>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}
          {busy && <CircularProgress />}

          {patient && (
            <Stack spacing={0.5}>
              <Typography variant="subtitle1">
                {patient.first_name} {patient.middle_name ?? ""} {patient.last_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                MRN: {patient.facility_mrn ?? "-"} | Phone: {patient.phone_number ?? "-"} | District:{" "}
                {patient.district ?? "-"}
              </Typography>
            </Stack>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1">Current Snapshot (Latest Values)</Typography>
            <Typography variant="body2" color="text.secondary">
              Derived from immutable events
            </Typography>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {summaryBySection.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No clinical events recorded yet.
            </Typography>
          ) : (
            <Stack spacing={2}>
              {summaryBySection.map((sec) => (
                <Card key={sec.section} variant="outlined">
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                      <Typography variant="subtitle2">{sec.section}</Typography>
                      <Chip
                        label={`${sec.items.length} factors`}
                        size="small"
                        onClick={() => setSectionFilter(sec.section)}
                        sx={{ cursor: "pointer" }}
                      />
                    </Stack>

                    <Grid container spacing={1}>
                      {sec.items.slice(0, 12).map(({ factor, ev }) => (
                        <Grid item xs={12} sm={6} md={4} key={`${sec.section}:${factor}`}>
                          <Typography variant="body2">
                            <strong>{factor}</strong>
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {formatValue(ev.value)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(ev.event_time).toLocaleString()}
                          </Typography>
                        </Grid>
                      ))}
                    </Grid>

                    {sec.items.length > 12 && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                        Showing first 12 factors. Use timeline filters to drill down.
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1" sx={{ flex: 1 }}>
              Timeline ({filteredTimeline.length})
            </Typography>

            <TextField
              select
              label="Section"
              value={sectionFilter}
              onChange={(e) => setSectionFilter(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              <option value=""></option>
              {sections.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </TextField>

            <TextField
              label="Factor contains"
              value={factorFilter}
              onChange={(e) => setFactorFilter(e.target.value)}
              sx={{ minWidth: 220 }}
            />

            <Button
              variant="outlined"
              onClick={() => {
                setSectionFilter("");
                setFactorFilter("");
              }}
            >
              Clear
            </Button>
          </Stack>

          <Divider sx={{ my: 2 }} />

          <Stack spacing={1}>
            {filteredTimeline.map((ev) => (
              <Card key={ev.id} variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2">
                    {ev.section} → {ev.factor}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Event time: {new Date(ev.event_time).toLocaleString()}
                  </Typography>
                  <Typography variant="body2">{formatValue(ev.value)}</Typography>
                  {ev.note && (
                    <Typography variant="body2" color="text.secondary">
                      Note: {ev.note}
                    </Typography>
                  )}
                  {ev.referral_id && (
                    <Typography variant="caption" color="text.secondary">
                      Referral link: {ev.referral_id}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
