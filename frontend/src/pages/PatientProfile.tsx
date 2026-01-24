// frontend/src/pages/PatientProfile.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { Edit as EditIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from "@mui/icons-material";
import Drawer from "@mui/material/Drawer";
import { api } from "../services/api";

type PatientOut = {
  id: string;
  facility_mrn?: string | null;
  patient_id?: string | null;
  national_id?: string | null;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  age_in_years?: number | null;
  date_of_birth?: string | null;
  sex?: string | null;
  phone_number?: string | null;
  district?: string | null;
  province?: string | null;
  municipality?: string | null;
  ward?: string | null;
  address_line?: string | null;
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

type FieldDefinition = {
  name: string;
  label: string;
  field_type: string;
  unit?: string;
  nullable: boolean;
};

type SectionSchema = {
  section_key: string;
  section_label: string;
  fields: FieldDefinition[];
};

function formatValue(v: any): string {
  if (!v) return "-";
  const t = v.type;
  const val = v.value;

  const unit = v.unit ? ` ${v.unit}` : "";

  if (t === "boolean") return Boolean(val) ? "Yes" : "No";
  if (t === "enum") return v.display ?? humanizeLabel(String(val));
  if (t === "code") return v.display ? `${v.display}${v.code ? ` (${v.code})` : ""}` : String(val ?? "-");
  if (t === "integer" || t === "number") return `${val ?? "-"}${unit}`;

  if (typeof val === "object") return JSON.stringify(val);
  return `${val ?? "-"}${unit}`;
}

function humanizeLabel(input: string): string {
  if (!input) return "";
  return input
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");
}

function PatientProfile() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [patient, setPatient] = useState<PatientOut | null>(null);
  const [events, setEvents] = useState<ClinicalEventOut[]>([]);
  const [schemas, setSchemas] = useState<Record<string, SectionSchema>>({});
  const [notesDrawer, setNotesDrawer] = useState<boolean>(false);
  const [referralsDrawer, setReferralsDrawer] = useState<boolean>(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  // UI controls
  const [sectionFilter, setSectionFilter] = useState<string>("");
  const [factorFilter, setFactorFilter] = useState<string>("");

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const toggleAllSections = (expand: boolean) => {
    const newState: Record<string, boolean> = {};
    summaryBySection.forEach(sec => {
      newState[sec.section] = expand;
    });
    setExpandedSections(newState);
  };

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

      // Load schemas for sections
      const sectionsResponse = await api.get("/schema/sections?updates_only=true");
      const schemasMap: Record<string, SectionSchema> = {};
      for (const section of sectionsResponse.data) {
        schemasMap[section.section_key] = section;
      }
      setSchemas(schemasMap);
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

  const factors = useMemo(() => {
    const f = new Set<string>();
    for (const e of events) {
      if (!sectionFilter || e.section === sectionFilter) f.add(e.factor);
    }
    return Array.from(f).sort((a, b) => a.localeCompare(b));
  }, [events, sectionFilter]);

  useEffect(() => {
    if (factorFilter && !factors.includes(factorFilter)) {
      setFactorFilter("");
    }
  }, [factors, factorFilter]);

  // Stable, latest-first ordering for timeline view
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      const ta = new Date(a.event_time).getTime();
      const tb = new Date(b.event_time).getTime();
      if (tb !== ta) return tb - ta; // newest first
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
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
    const eventMap = new Map<string, Map<string, ClinicalEventOut>>();
    for (const ev of sorted) {
      if (!eventMap.has(ev.section)) eventMap.set(ev.section, new Map());
      eventMap.get(ev.section)!.set(ev.factor, ev);
    }

    // convert to arrays for rendering, include all schema fields
    const out: Array<{ section: string; items: Array<{ factor: string; ev: ClinicalEventOut | null; fieldLabel: string }> }> = [];
    
    // Get unique sections from both schemas and events
    const allSections = new Set<string>();
    Object.keys(schemas).forEach(s => allSections.add(s));
    eventMap.forEach((_, section) => allSections.add(section));

    for (const section of Array.from(allSections).sort()) {
      const schema = schemas[section];
      const factorMap = eventMap.get(section) || new Map();
      const items: Array<{ factor: string; ev: ClinicalEventOut | null; fieldLabel: string }> = [];

      // If schema exists, include all fields
      if (schema) {
        for (const field of schema.fields) {
          items.push({
            factor: field.name,
            ev: factorMap.get(field.name) || null,
            fieldLabel: field.label
          });
        }
      } else {
        // No schema, just show recorded factors
        for (const [factor, ev] of factorMap.entries()) {
          items.push({ factor, ev, fieldLabel: humanizeLabel(factor) });
        }
      }

      if (items.length > 0) {
        out.push({ section, items: items.sort((a, b) => a.fieldLabel.localeCompare(b.fieldLabel)) });
      }
    }

    return out;
  }, [events, schemas]);

  const filteredTimeline = useMemo(() => {
    return sortedEvents.filter((ev) => {
      if (sectionFilter && ev.section !== sectionFilter) return false;
      if (factorFilter && ev.factor !== factorFilter) return false;
      return true;
    });
  }, [sortedEvents, sectionFilter, factorFilter]);

  const notesList = useMemo(() => {
    return sortedEvents.filter((ev) => ev.note);
  }, [sortedEvents]);

  const referralList = useMemo(() => {
    return sortedEvents.filter((ev) => ev.referral_id);
  }, [sortedEvents]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F7FB", py: { xs: 2, md: 3 }, px: { xs: 0.5, sm: 1, md: 1.5 }, width: "100%", boxSizing: "border-box" }}>
      <Stack spacing={3}>
        {/* Top Bar */}
        {patient && (
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
                    {patient.first_name} {patient.middle_name ?? ""} {patient.last_name}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9, lineHeight: 1.7 }}>
                    MRN: {patient.facility_mrn || patient.patient_id || "Not assigned"}
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1.25} alignItems="center">
                  <Button
                    variant="contained"
                    onClick={() => navigate(`/patients/${patientId}/update`)}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      background: "rgba(255,255,255,0.95)",
                      color: "#4C51BF",
                      "&:hover": { background: "white" },
                      px: 2.25,
                    }}
                  >
                    Update Record
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => navigate(`/patients/${patientId}/referral`)}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      background: "rgba(255,255,255,0.95)",
                      color: "#4C51BF",
                      "&:hover": { background: "white" },
                      px: 2.25,
                    }}
                  >
                    Refer Patient
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => navigate("/patients")}
                    sx={{
                      textTransform: "none",
                      fontWeight: 700,
                      borderRadius: 2,
                      background: "rgba(255,255,255,0.25)",
                      color: "white",
                      "&:hover": { background: "rgba(255,255,255,0.35)" },
                      px: 2.25,
                    }}
                  >
                    Back
                  </Button>
                </Stack>
              </Stack>
            </Box>

            {error && (
              <CardContent sx={{ p: { xs: 2.5, md: 3.5 }, bgcolor: "white" }}>
                <Alert severity="error">{error}</Alert>
              </CardContent>
            )}
          </Card>
        )}

        {error && !patient && <Alert severity="error">{error}</Alert>}
        {busy && !patient && <CircularProgress />}

        {patient && (
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
                    Personal Information
                  </Typography>
                  <Tooltip title="Edit patient information" arrow>
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => navigate(`/patients/${patientId}/edit`)}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">Full Name</Typography>
                    <Typography variant="body1">
                      {patient.first_name} {patient.middle_name ?? ""} {patient.last_name}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">Patient ID / Facility MRN</Typography>
                    <Typography variant="body1">{patient.facility_mrn || patient.patient_id || "Not assigned"}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">Age</Typography>
                    <Typography variant="body1">{patient.age_in_years ? `${patient.age_in_years} years` : "Not recorded"}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">Sex</Typography>
                    <Typography variant="body1">{patient.sex || "Not recorded"}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">Phone Number</Typography>
                    <Typography variant="body1">{patient.phone_number || "Not provided"}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2" color="text.secondary">District</Typography>
                    <Typography variant="body1">{patient.district || "Not recorded"}</Typography>
                  </Grid>
                  {patient.municipality && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">Metropolitan City / Sub Metropolitan City / Municipality</Typography>
                      <Typography variant="body1">{patient.municipality}</Typography>
                    </Grid>
                  )}
                  {patient.ward && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">Ward</Typography>
                      <Typography variant="body1">{patient.ward}</Typography>
                    </Grid>
                  )}
                  {patient.address_line && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">Tole Name</Typography>
                      <Typography variant="body1">{patient.address_line}</Typography>
                    </Grid>
                  )}
                  {patient.national_id && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">National ID</Typography>
                      <Typography variant="body1">{patient.national_id}</Typography>
                    </Grid>
                  )}
                </Grid>
              </Stack>
            </CardContent>
          </Card>
        )}

        <Card
          sx={{
            borderRadius: 3,
            border: "1px solid rgba(15, 23, 42, 0.10)",
            boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
          }}
        >
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            <Stack spacing={2}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                Notes & Referrals
              </Typography>
              <Stack direction="row" spacing={2}>
                <Button variant="outlined" onClick={() => setNotesDrawer(true)}>
                  View Notes ({events.filter((e) => e.note).length})
                </Button>
                <Button variant="outlined" onClick={() => setReferralsDrawer(true)}>
                  View Referral History ({events.filter((e) => e.referral_id).length})
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>

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
                  Clinical Summary
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button 
                    variant="outlined" 
                    size="small"
                    onClick={() => toggleAllSections(true)}
                  >
                    Show All
                  </Button>
                  <Button 
                    variant="outlined" 
                    size="small"
                    onClick={() => toggleAllSections(false)}
                  >
                    Collapse All
                  </Button>
                </Stack>
              </Stack>

              {summaryBySection.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No clinical events recorded yet.
                </Typography>
              ) : (
                <Stack spacing={2}>
                  {summaryBySection.map((sec) => {
                    const isExpanded = expandedSections[sec.section] === true; // default collapsed
                    return (
                      <Card 
                        key={sec.section} 
                        sx={{
                          border: "1px solid rgba(15, 23, 42, 0.08)",
                          borderRadius: 2,
                        }}
                      >
                        <CardContent>
                          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: isExpanded ? 2 : 0 }}>
                            <Typography variant="body1" sx={{ fontWeight: 700 }}>{humanizeLabel(sec.section)}</Typography>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip
                                label={`${sec.items.length} factors`}
                                size="small"
                                onClick={() => setSectionFilter(sec.section)}
                                sx={{ cursor: "pointer" }}
                              />
                              <Tooltip title="Edit section" arrow>
                                <IconButton
                                  size="small"
                                  color="primary"
                                  onClick={() => navigate(`/patients/${patientId}/update?section=${sec.section}`)}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title={isExpanded ? "Collapse" : "Expand"} arrow>
                                <IconButton
                                  size="small"
                                  onClick={() => toggleSection(sec.section)}
                                >
                                  {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                </IconButton>
                              </Tooltip>
                            </Stack>
                          </Stack>

                          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                            <Grid container spacing={1}>
                              {sec.items.slice(0, 12).map(({ factor, ev, fieldLabel }) => (
                                <Grid item xs={12} sm={6} md={4} key={`${sec.section}:${factor}`}>
                                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                                    {fieldLabel}
                                  </Typography>
                                  <Typography variant="body2" sx={{ mb: 0.5, color: ev ? "text.primary" : "text.disabled" }}>
                                    {ev ? formatValue(ev.value) : "Not recorded"}
                                  </Typography>
                                  {ev && (
                                    <Typography variant="caption" color="text.secondary">
                                      {new Date(ev.event_time).toLocaleString()}
                                    </Typography>
                                  )}
                                </Grid>
                              ))}
                            </Grid>

                            {sec.items.length > 12 && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                                Showing first 12 factors. Use timeline filters to drill down.
                              </Typography>
                            )}
                          </Collapse>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Stack>
              )}
            </Stack>
          </CardContent>
        </Card>

        <Card
          sx={{
            borderRadius: 3,
            border: "1px solid rgba(15, 23, 42, 0.10)",
            boxShadow: "0 10px 28px rgba(15, 23, 42, 0.06)",
          }}
        >
          <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
            <Stack spacing={2}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#0F172A" }}>
                Timeline ({filteredTimeline.length})
              </Typography>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "flex-start", sm: "center" }}>
                <TextField
                  select
                  label="Section"
                  value={sectionFilter}
                  onChange={(e) => setSectionFilter(e.target.value)}
                  size="small"
                  sx={{ minWidth: 200 }}
                >
                  <MenuItem value="">All sections</MenuItem>
                  {sections.map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  select
                  label="Factor"
                  value={factorFilter}
                  onChange={(e) => setFactorFilter(e.target.value)}
                  size="small"
                  sx={{ minWidth: 200 }}
                >
                  <MenuItem value="">All factors</MenuItem>
                  {factors.map((f) => (
                    <MenuItem key={f} value={f}>
                      {f}
                    </MenuItem>
                  ))}
                </TextField>

                <Button
                  variant="outlined"
                  onClick={() => {
                    setSectionFilter("");
                    setFactorFilter("");
                  }}
                  sx={{ whiteSpace: "nowrap" }}
                >
                  Clear
                </Button>
              </Stack>

              <Divider sx={{ my: 2 }} />

              {filteredTimeline.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No events match the current filters.
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Section</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Factor</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Event time</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredTimeline.map((ev) => (
                      <TableRow key={ev.id} hover>
                        <TableCell>{humanizeLabel(ev.section)}</TableCell>
                        <TableCell>{humanizeLabel(ev.factor)}</TableCell>
                        <TableCell>{new Date(ev.event_time).toLocaleString()}</TableCell>
                        <TableCell>{formatValue(ev.value)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Stack>
          </CardContent>
        </Card>

        <Drawer anchor="right" open={notesDrawer} onClose={() => setNotesDrawer(false)} sx={{ minWidth: 360 }}>
          <Stack spacing={2} sx={{ p: 2, width: { xs: 320, sm: 420 } }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Notes</Typography>
              <Button size="small" onClick={() => setNotesDrawer(false)}>
                Close
              </Button>
            </Stack>
            {notesList.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No notes recorded.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Event time</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Section</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Factor</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Note</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {notesList.map((ev) => (
                  <TableRow key={ev.id} hover>
                    <TableCell>{new Date(ev.event_time).toLocaleString()}</TableCell>
                    <TableCell>{humanizeLabel(ev.section)}</TableCell>
                    <TableCell>{humanizeLabel(ev.factor)}</TableCell>
                    <TableCell>{ev.note}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Stack>
      </Drawer>

      <Drawer anchor="right" open={referralsDrawer} onClose={() => setReferralsDrawer(false)} sx={{ minWidth: 360 }}>
        <Stack spacing={2} sx={{ p: 2, width: { xs: 320, sm: 420 } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Referral History</Typography>
            <Button size="small" onClick={() => setReferralsDrawer(false)}>
              Close
            </Button>
          </Stack>
          {referralList.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No referrals recorded.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Event time</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Section</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Factor</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Referral ID</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {referralList.map((ev) => (
                  <TableRow key={ev.id} hover>
                    <TableCell>{new Date(ev.event_time).toLocaleString()}</TableCell>
                    <TableCell>{humanizeLabel(ev.section)}</TableCell>
                    <TableCell>{humanizeLabel(ev.factor)}</TableCell>
                    <TableCell>{ev.referral_id}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Stack>
      </Drawer>
      </Stack>
    </Box>
  );
}

export default PatientProfile;
