// frontend/src/pages/UpdateRecord.tsx
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api } from "../services/api";

type ClinicalValue = {
  type: "string" | "number" | "boolean" | "date" | "datetime" | "code" | "object" | "array";
  value: any;
  unit?: string | null;
};

type BatchItem = {
  factor: string;
  value: ClinicalValue;
};

type BatchCreate = {
  patient_id: string;
  section: string;
  events: BatchItem[];
  event_time?: string | null;
  note?: string | null;
  referral_id?: string | null;
};

const SECTION_OPTIONS = [
  "patient_particulars",
  "menstrual_history",
  "contraceptive_history",
  "past_medical_history",
  "family_history",
  "obstetric_history",
  "present_pregnancy",
  "anc_trimester_1",
  "anc_trimester_2",
  "anc_trimester_3",
  "examination_general",
  "vitals",
  "lab_investigations",
  "ultrasound",
  "urine_investigations",
  "maternal_risk_factors",
];

export default function UpdateRecord() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [section, setSection] = useState<string>("vitals");
  const [note, setNote] = useState<string>("");
  const [items, setItems] = useState<BatchItem[]>([
    { factor: "bp_systolic", value: { type: "number", value: 0, unit: "mmHg" } },
  ]);

  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return Boolean(patientId) && section.trim().length > 0 && items.length > 0 && items.every((i) => i.factor.trim().length > 0);
  }, [patientId, section, items]);

  function addRow() {
    setItems((prev) => [...prev, { factor: "", value: { type: "string", value: "" } }]);
  }

  function removeRow(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  async function submit() {
    if (!patientId) return;
    setError(null);
    setOk(null);

    const payload: BatchCreate = {
      patient_id: patientId,
      section,
      events: items.map((it) => ({
        factor: it.factor.trim(),
        value: it.value.type === "number" ? { ...it.value, value: Number(it.value.value) } : it.value,
      })),
      note: note.trim() || null,
    };

    try {
      await api.post("/events/batch", payload);
      setOk("Saved as immutable clinical events.");
      navigate(`/patients/${patientId}`, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to save updates");
    }
  }

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <div>
              <Typography variant="h5">Update Record</Typography>
              <Typography variant="body2" color="text.secondary">
                Section-wise selective update. Each row becomes an immutable event.
              </Typography>
            </div>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={() => navigate(`/patients/${patientId}`)}>
                Back
              </Button>
              <Button variant="contained" onClick={submit} disabled={!canSubmit}>
                Save
              </Button>
            </Stack>
          </Stack>

          <Divider sx={{ my: 2 }} />

          {error && <Alert severity="error">{error}</Alert>}
          {ok && <Alert severity="success">{ok}</Alert>}

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Section"
                value={section}
                onChange={(e) => setSection(e.target.value)}
                fullWidth
              >
                {SECTION_OPTIONS.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Note (optional)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                fullWidth
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 2 }} />

          <Stack spacing={2}>
            {items.map((it, idx) => (
              <Grid container spacing={2} key={idx} alignItems="center">
                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Factor"
                    value={it.factor}
                    onChange={(e) =>
                      setItems((prev) =>
                        prev.map((p, i) => (i === idx ? { ...p, factor: e.target.value } : p))
                      )
                    }
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    select
                    label="Type"
                    value={it.value.type}
                    onChange={(e) =>
                      setItems((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, value: { ...p.value, type: e.target.value as any } } : p
                        )
                      )
                    }
                    fullWidth
                  >
                    {["string", "number", "boolean", "date", "datetime", "code", "object", "array"].map((t) => (
                      <MenuItem key={t} value={t}>
                        {t}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    label="Value"
                    value={String(it.value.value ?? "")}
                    onChange={(e) =>
                      setItems((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, value: { ...p.value, value: e.target.value } } : p
                        )
                      )
                    }
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12} sm={2}>
                  <TextField
                    label="Unit"
                    value={it.value.unit ?? ""}
                    onChange={(e) =>
                      setItems((prev) =>
                        prev.map((p, i) =>
                          i === idx ? { ...p, value: { ...p.value, unit: e.target.value } } : p
                        )
                      )
                    }
                    fullWidth
                  />
                </Grid>

                <Grid item xs={12} sm={1}>
                  <Button color="inherit" onClick={() => removeRow(idx)}>
                    Remove
                  </Button>
                </Grid>
              </Grid>
            ))}

            <Button variant="outlined" onClick={addRow}>
              Add factor
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
