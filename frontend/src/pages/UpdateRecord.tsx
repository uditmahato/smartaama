// frontend/src/pages/UpdateRecord.tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, getErrorMessage } from "../services/api";

interface FieldDefinition {
  name: string;
  label: string;
  field_type: string;
  unit?: string;
  nullable: boolean;
  enum_values?: string[];
  min_value?: number;
  max_value?: number;
  description?: string;
}

interface SectionSchema {
  section_key: string;
  section_label: string;
  category: string;
  fields: FieldDefinition[];
  description?: string;
}

interface SectionOption {
  key: string;
  label: string;
}

type FormValue = string | number | boolean | null | undefined;

export default function UpdateRecord() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // `?section=<key>` (from the profile's per-section edit button) preselects a section.
  const requestedSection = searchParams.get("section")?.trim() || "";

  const [sections, setSections] = useState<SectionOption[]>([]);
  const [selectedSection, setSelectedSection] = useState<string>("");
  const [schema, setSchema] = useState<SectionSchema | null>(null);
  const [formData, setFormData] = useState<Record<string, FormValue>>({});
  const [note, setNote] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Load available sections on mount
  useEffect(() => {
    loadSections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load schema when section changes
  useEffect(() => {
    if (selectedSection) {
      loadSchema(selectedSection);
    }
  }, [selectedSection]);

  async function loadSections() {
    try {
      // Fetch only sections that should appear in clinical updates
      const response = await api.get<SectionSchema[]>(
        "/schema/sections?updates_only=true",
      );
      const sectionList: SectionOption[] = response.data.map((s) => ({
        key: s.section_key,
        label: s.section_label,
      }));
      setSections(sectionList);

      // Pre-select the requested section (fall back to the first one).
      if (sectionList.length > 0) {
        const match = requestedSection
          ? sectionList.find((s) => s.key === requestedSection)
          : undefined;
        setSelectedSection((match ?? sectionList[0]).key);
      }
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load sections"));
    }
  }

  async function loadSchema(sectionKey: string) {
    setSchemaLoading(true);
    setError(null);
    try {
      const response = await api.get<SectionSchema>(
        `/schema/sections/${sectionKey}`,
      );
      setSchema(response.data);

      // Initialize form data with default values
      const initialData: Record<string, FormValue> = {};
      response.data.fields.forEach((field) => {
        if (field.field_type === "boolean") {
          initialData[field.name] = false;
        } else {
          initialData[field.name] = "";
        }
      });
      setFormData(initialData);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load schema"));
      setSchema(null);
    } finally {
      setSchemaLoading(false);
    }
  }

  const canSubmit = useMemo(() => {
    if (!patientId || !selectedSection || !schema) return false;

    // Check if at least one field has a value
    const hasData = schema.fields.some((field) => {
      const value = formData[field.name];
      if (field.field_type === "boolean") return true; // Booleans always have a value
      return value !== "" && value !== null && value !== undefined;
    });

    return hasData;
  }, [patientId, selectedSection, schema, formData]);

  async function submit() {
    if (!patientId || !selectedSection || !schema) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Filter out empty values for nullable fields
      const dataPoints: Record<string, FormValue> = {};
      schema.fields.forEach((field) => {
        const value = formData[field.name];

        if (field.field_type === "boolean") {
          dataPoints[field.name] = Boolean(value);
        } else if (value !== "" && value !== null && value !== undefined) {
          // Convert to proper type
          if (field.field_type === "integer") {
            dataPoints[field.name] = parseInt(String(value), 10);
          } else if (field.field_type === "float") {
            dataPoints[field.name] = parseFloat(String(value));
          } else {
            dataPoints[field.name] = value;
          }
        } else if (!field.nullable) {
          // Required field is empty
          throw new Error(`${field.label} is required`);
        }
      });

      // Submit to new medical data endpoint
      await api.post(`/medical-data/patients/${patientId}/sections/${selectedSection}`, {
        section_key: selectedSection,
        data_points: dataPoints,
        event_time: new Date().toISOString(),
        note: note.trim() || null,
      });

      setSuccess(`${schema.section_label} data saved successfully!`);

      // Navigate back after a brief delay
      setTimeout(() => {
        navigate(`/patients/${patientId}`, { replace: true });
      }, 1500);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to save data"));
    } finally {
      setLoading(false);
    }
  }

  const textValue = (name: string): string | number => {
    const v = formData[name];
    if (v === null || v === undefined || typeof v === "boolean") return "";
    return v;
  };

  const renderField = (field: FieldDefinition) => {
    const fieldLabel = field.unit ? `${field.label} (${field.unit})` : field.label;

    switch (field.field_type) {
      case "boolean":
        return (
          <Grid item xs={12} sm={6} key={field.name}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!formData[field.name]}
                  onChange={(e) =>
                    setFormData({ ...formData, [field.name]: e.target.checked })
                  }
                />
              }
              label={fieldLabel}
            />
          </Grid>
        );

      case "enum":
        return (
          <Grid item xs={12} sm={6} key={field.name}>
            <TextField
              select
              label={fieldLabel}
              value={textValue(field.name)}
              onChange={(e) =>
                setFormData({ ...formData, [field.name]: e.target.value })
              }
              fullWidth
              required={!field.nullable}
            >
              <MenuItem value="">
                <em>Select...</em>
              </MenuItem>
              {field.enum_values?.map((option) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        );

      case "integer":
      case "float":
        return (
          <Grid item xs={12} sm={6} key={field.name}>
            <TextField
              label={fieldLabel}
              type="number"
              value={textValue(field.name)}
              onChange={(e) =>
                setFormData({ ...formData, [field.name]: e.target.value })
              }
              fullWidth
              required={!field.nullable}
              inputProps={{
                min: field.min_value,
                max: field.max_value,
                step: field.field_type === "integer" ? 1 : 0.1,
              }}
            />
          </Grid>
        );

      case "date":
        return (
          <Grid item xs={12} sm={6} key={field.name}>
            <TextField
              label={fieldLabel}
              type="date"
              value={textValue(field.name)}
              onChange={(e) =>
                setFormData({ ...formData, [field.name]: e.target.value })
              }
              fullWidth
              required={!field.nullable}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
        );

      case "string":
      default:
        return (
          <Grid item xs={12} sm={6} key={field.name}>
            <TextField
              label={fieldLabel}
              value={textValue(field.name)}
              onChange={(e) =>
                setFormData({ ...formData, [field.name]: e.target.value })
              }
              fullWidth
              required={!field.nullable}
            />
          </Grid>
        );
    }
  };

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <div>
              <Typography variant="h5">Update Record</Typography>
              <Typography variant="body2" color="text.secondary">
                Select a section and fill in the clinical data. All fields have predefined types and units.
              </Typography>
            </div>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={() => navigate(`/patients/${patientId}`)}>
                BACK
              </Button>
              <Button
                variant="contained"
                onClick={submit}
                disabled={!canSubmit || loading}
              >
                {loading ? <CircularProgress size={24} /> : "SAVE"}
              </Button>
            </Stack>
          </Stack>

          <Divider sx={{ mb: 2 }} />

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Section"
                value={selectedSection}
                onChange={(e) => setSelectedSection(e.target.value)}
                fullWidth
                disabled={loading}
              >
                {sections.map((s) => (
                  <MenuItem key={s.key} value={s.key}>
                    {s.label}
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
                placeholder="Add any relevant notes..."
              />
            </Grid>
          </Grid>

          {schemaLoading && (
            <Stack alignItems="center" sx={{ py: 4 }}>
              <CircularProgress />
              <Typography sx={{ mt: 2 }}>Loading fields...</Typography>
            </Stack>
          )}

          {schema && !schemaLoading && (
            <>
              <Typography variant="h6" sx={{ mb: 2 }}>
                {schema.section_label}
                {schema.description && (
                  <Typography variant="body2" color="text.secondary">
                    {schema.description}
                  </Typography>
                )}
              </Typography>

              <Grid container spacing={2}>
                {schema.fields.map(renderField)}
              </Grid>
            </>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
