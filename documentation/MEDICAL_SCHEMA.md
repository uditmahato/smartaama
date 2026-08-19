# Medical Schema and Structured Clinical Data

SmartAama captures clinical data against a predefined schema: every field has a
type, a unit (where relevant), optional enum values, and a nullable flag. Clinicians
enter values only; the backend validates them and stores each value as a
`ClinicalEvent` row.

Source of truth: `backend/app/models/medical_schema.py`
(`MEDICAL_SCHEMA` dict, `SectionDefinition`, `FieldDefinition`).
To add or change a field or section, edit that file; the API serves it immediately.

## Sections

Sections have a `category` of `static`, `obstetric`, or `event_based`.

| Category | Section key | Label |
|---|---|---|
| static | `patient_particulars` | Patient Particulars (`show_in_updates=False`; captured at registration) |
| static | `menstrual_history` | Menstrual History |
| static | `contraceptive_history` | Contraceptive History |
| static | `past_medical_history` | Past Medical History |
| static | `family_history` | Family History |
| static | `present_pregnancy` | Present Pregnancy |
| obstetric | `obstetric_history` | Obstetric History |
| event_based | `first_trimester_anc` | First Trimester ANC |
| event_based | `second_trimester_anc` | Second Trimester ANC |
| event_based | `third_trimester_anc` | Third Trimester ANC |
| event_based | `general_examination` | General Examination |
| event_based | `vitals` | Vital Signs |
| event_based | `general_signs` | General Signs |
| event_based | `per_abdominal_examination` | Per Abdominal Examination |
| event_based | `cardiovascular_respiratory` | Cardiovascular & Respiratory Examination |
| event_based | `blood_investigations` | Blood Investigations |
| event_based | `renal_function_tests` | Renal Function Tests |
| event_based | `liver_function_tests` | Liver Function Tests |
| event_based | `serology` | Serology |
| event_based | `thyroid_function_tests` | Thyroid Function Tests |
| event_based | `ultrasonography` | Ultrasonography |
| event_based | `urine_examination` | Urine Examination |

Notes on field naming that matter to other code (for example the advisory rule engine):

- Blood pressure lives in `vitals` as `blood_pressure_systolic` / `blood_pressure_diastolic`;
  maternal pulse is `vitals.pulse_rate`.
- Haemoglobin is `blood_investigations.hemoglobin`.
- Urine protein is `urine_examination.dipstick_protein`.
- Fetal heart rate appears in `per_abdominal_examination.fetal_heart_rate` and
  `ultrasonography.fetal_heart_rate`.

## Field definition

```python
class FieldDefinition(BaseModel):
    name: str                       # key used in data_points
    label: str
    field_type: FieldType           # string|integer|float|boolean|date|datetime|enum|object|array
    unit: Optional[str] = None      # e.g. "mmHg", "g/dL", "bpm"
    nullable: bool = False
    enum_values: Optional[List[str]] = None
    default_value: Any = None
    min_value: Optional[float] = None   # informational; not enforced by the API today
    max_value: Optional[float] = None   # informational; not enforced by the API today
    description: Optional[str] = None
```

## API

All paths below are relative to `/api/v1`.

### Schema metadata (`/schema`) - authenticated (any role), read-only

```http
GET /schema/sections                          # all sections
GET /schema/sections?category=static          # static | obstetric | event_based
GET /schema/sections?updates_only=true        # only sections with show_in_updates=True
GET /schema/sections/{section_key}            # full SectionDefinition (fields, types, units, enums)
GET /schema/sections/{section_key}/fields     # simplified {name,label,type,unit,required} list
```

Example `GET /schema/sections/vitals` (abridged):

```json
{
  "section_key": "vitals",
  "section_label": "Vital Signs",
  "category": "event_based",
  "fields": [
    {"name": "pulse_rate", "label": "Pulse Rate", "field_type": "integer", "unit": "bpm", "nullable": false},
    {"name": "blood_pressure_systolic", "label": "Blood Pressure (Systolic)", "field_type": "integer", "unit": "mmHg", "nullable": false}
  ]
}
```

### Structured data entry (`/medical-data`) - authenticated

Authorization: callers must have access to the patient (facility-based, see
`ACCESS_CONTROL.md`); writes require the `clinician`, `hospital` or `admin` role, and
`viewer` is read-only. Every write also invalidates the stored advisory analysis for
that patient (`mark_ai_analysis_for_update`).

#### Add data for one section

```http
POST /medical-data/patients/{patient_id}/sections/{section_key}
```

```json
{
  "section_key": "vitals",
  "data_points": {
    "pulse_rate": 78,
    "blood_pressure_systolic": 110,
    "blood_pressure_diastolic": 70,
    "temperature": 36.8,
    "weight": 62
  },
  "event_time": "2026-01-24T10:30:00Z",
  "note": "Routine ANC checkup"
}
```

Behaviour:

1. `section_key` in the body must equal the one in the URL (400 otherwise).
2. `data_points` is validated against the schema (`app/schemas/medical_data.py`):
   unknown field, wrong type, non-nullable `null`, or value outside `enum_values`
   all return 422.
3. One `ClinicalEvent` row is created per field, with `section=<section_key>`,
   `factor=<field name>`, and `value = {"value": ..., "unit": ..., "type": ...}`.
   `event_time` defaults to now.
4. An `AuditLog` row (`MEDICAL_DATA_ADDED`) is written.

Static sections use the same append-only mechanism; "latest" simply means the newest
value per field.

#### Bulk entry (several sections in one visit)

```http
POST /medical-data/patients/{patient_id}/bulk-entry
```

```json
{
  "patient_id": "uuid",
  "sections": [
    {"section_key": "vitals", "data_points": {"pulse_rate": 78, "blood_pressure_systolic": 110, "blood_pressure_diastolic": 70}},
    {"section_key": "blood_investigations", "data_points": {"hemoglobin": 11.2, "blood_group": "O+"}}
  ],
  "visit_note": "Second trimester ANC visit"
}
```

#### Latest values for a section

```http
GET /medical-data/patients/{patient_id}/sections/{section_key}/latest
```

Returns `{section_key, section_label, category, data_points, event_time, recorded_at}`
with the most recent value of each field, or `data_points: {}` and a `message` when
nothing has been recorded.

#### History (time series)

```http
GET /medical-data/patients/{patient_id}/sections/{section_key}/history?limit=10
```

Entries are grouped by `event_time` (newest first):

```json
{
  "section_key": "vitals",
  "section_label": "Vital Signs",
  "entries": [
    {
      "event_id": "uuid",
      "event_time": "2026-01-24T10:30:00Z",
      "data_points": {"pulse_rate": 78, "blood_pressure_systolic": 110, "blood_pressure_diastolic": 70, "weight": 62},
      "note": "Routine checkup",
      "recorded_by": null
    }
  ],
  "total_entries": 2
}
```

There is no API to delete or edit a clinical event; corrections are made by
recording a new entry.

## Frontend usage

The frontend axios instance (`frontend/src/services/api.ts`) already has
`VITE_API_BASE_URL` (for example `http://localhost:8000/api/v1`) as its base URL, so
calls omit the prefix. `UpdateRecord.tsx` and `PatientProfile.tsx` are the current
consumers.

```typescript
// Sections to show in the clinical-update form
const sections = (await api.get("/schema/sections?updates_only=true")).data;

// Field definitions for one section -> render inputs by field_type, show unit, use enum_values for selects
const schema = (await api.get(`/schema/sections/${sectionKey}`)).data;

// Submit
await api.post(`/medical-data/patients/${patientId}/sections/${sectionKey}`, {
  section_key: sectionKey,
  data_points: values,
  event_time: new Date().toISOString(),
});

// History
const history = (await api.get(`/medical-data/patients/${patientId}/sections/vitals/history`)).data;
```
