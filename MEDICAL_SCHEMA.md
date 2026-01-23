# Medical Schema System - Smart Aama

## Overview

The medical schema system provides a structured, type-safe way to capture clinical data with predefined fields, data types, and units. This ensures data consistency and eliminates the need for doctors to manually select data types.

## Key Features

### 1. **Predefined Data Types & Units**
- All clinical fields have predefined types (integer, float, boolean, string, enum, date)
- Units are automatically included (e.g., "mmHg" for blood pressure, "g/dL" for hemoglobin)
- Doctors only enter values; the system handles type validation and unit display

### 2. **Hierarchical Sections**
Data is organized into logical sections:

**Static Profile Sections** (one-time or rarely updated):
- Patient Particulars
- Menstrual History
- Contraceptive History
- Past Medical History
- Family History
- Present Pregnancy
- Obstetric History

**Event-Based Sections** (time-series data with multiple dated entries):
- First/Second/Third Trimester ANC
- General Examination
- Vital Signs
- General Signs
- Per Abdominal Examination
- Cardiovascular & Respiratory Examination
- Blood Investigations
- Renal Function Tests
- Liver Function Tests
- Serology
- Thyroid Function Tests
- Ultrasonography
- Urine Examination

### 3. **Time-Series Support**
- Event-based sections automatically record the date/time of each entry
- Multiple entries can exist for the same section (e.g., multiple blood test results)
- Historical data is preserved and queryable by date

## API Endpoints

### Get Schema Information

#### List All Sections
```http
GET /api/v1/schema/sections
GET /api/v1/schema/sections?category=static
GET /api/v1/schema/sections?category=event_based
```

#### Get Section Details
```http
GET /api/v1/schema/sections/{section_key}
```

Returns field definitions including:
- Field name and label
- Data type (integer, float, boolean, string, enum, date, etc.)
- Unit (if applicable)
- Enum values (for dropdown fields)
- Required/optional status
- Min/max values (for validation)

Example response:
```json
{
  "section_key": "vitals",
  "section_label": "Vital Signs",
  "category": "event_based",
  "fields": [
    {
      "name": "pulse_rate",
      "label": "Pulse Rate",
      "field_type": "integer",
      "unit": "bpm",
      "nullable": false
    },
    {
      "name": "blood_pressure_systolic",
      "label": "Blood Pressure (Systolic)",
      "field_type": "integer",
      "unit": "mmHg",
      "nullable": false
    }
  ]
}
```

### Add Medical Data

#### Add Data for a Section
```http
POST /api/v1/medical-data/patients/{patient_id}/sections/{section_key}
```

Request body:
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

The system will:
1. Validate data types against the schema
2. Attach units automatically
3. Record the event with a timestamp
4. Create audit logs

#### Bulk Entry (Multiple Sections)
```http
POST /api/v1/medical-data/patients/{patient_id}/bulk-entry
```

Request body:
```json
{
  "patient_id": "uuid",
  "sections": [
    {
      "section_key": "vitals",
      "data_points": {
        "pulse_rate": 78,
        "blood_pressure_systolic": 110,
        "blood_pressure_diastolic": 70
      }
    },
    {
      "section_key": "blood_investigations",
      "data_points": {
        "hemoglobin": 11.2,
        "blood_group": "O+"
      }
    }
  ],
  "visit_note": "Second trimester ANC visit"
}
```

### Retrieve Data

#### Get Latest Data for a Section
```http
GET /api/v1/medical-data/patients/{patient_id}/sections/{section_key}/latest
```

Returns the most recent values for all fields in that section.

#### Get Historical Data (Time Series)
```http
GET /api/v1/medical-data/patients/{patient_id}/sections/{section_key}/history?limit=10
```

Returns multiple dated entries for event-based sections.

Example response:
```json
{
  "section_key": "vitals",
  "section_label": "Vital Signs",
  "entries": [
    {
      "event_id": "uuid",
      "event_time": "2026-01-24T10:30:00Z",
      "data_points": {
        "pulse_rate": 78,
        "blood_pressure_systolic": 110,
        "blood_pressure_diastolic": 70,
        "weight": 62
      },
      "note": "Routine checkup"
    },
    {
      "event_id": "uuid",
      "event_time": "2026-01-10T09:15:00Z",
      "data_points": {
        "pulse_rate": 76,
        "blood_pressure_systolic": 108,
        "blood_pressure_diastolic": 68,
        "weight": 60
      },
      "note": null
    }
  ],
  "total_entries": 2
}
```

## Frontend Integration

### 1. Fetch Schema on Load
```typescript
// Get schema for a section
const response = await api.get(`/api/v1/schema/sections/vitals`);
const schema = response.data;

// Generate form fields dynamically
schema.fields.forEach(field => {
  // Render input based on field.field_type
  // Display field.label and field.unit
  // For enums, use field.enum_values for dropdown
});
```

### 2. Display Units Automatically
```typescript
// Example: Display "Pulse Rate (bpm)"
<FormLabel>
  {field.label} {field.unit && `(${field.unit})`}
</FormLabel>
<TextField
  type={field.field_type === 'integer' ? 'number' : 'text'}
  required={!field.nullable}
/>
```

### 3. Submit Data
```typescript
const formData = {
  section_key: "vitals",
  data_points: {
    pulse_rate: 78,
    blood_pressure_systolic: 110,
    blood_pressure_diastolic: 70,
    temperature: 36.8
  },
  event_time: new Date().toISOString()
};

await api.post(
  `/api/v1/medical-data/patients/${patientId}/sections/vitals`,
  formData
);
```

### 4. Show Historical Data
```typescript
// Fetch history
const response = await api.get(
  `/api/v1/medical-data/patients/${patientId}/sections/vitals/history`
);

// Display as table or chart
response.data.entries.forEach(entry => {
  console.log(`${entry.event_time}: BP ${entry.data_points.blood_pressure_systolic}/${entry.data_points.blood_pressure_diastolic}`);
});
```

## Data Categories

### Static Sections
- Updated once or rarely modified
- Latest entry is displayed
- Examples: demographics, medical history, current pregnancy details

### Event-Based Sections
- New entry created each time
- Full history is preserved
- Examples: vitals, examinations, lab results
- Each entry has a timestamp (event_time)

## Benefits

1. **No Manual Type Selection**: Doctors don't choose data types; they're predefined
2. **Consistent Units**: Units are shown automatically (e.g., "mmHg", "g/dL", "bpm")
3. **Type Safety**: Backend validates all data against the schema
4. **Time-Series Ready**: Event-based sections support multiple dated entries
5. **Dynamic Forms**: Frontend can generate forms automatically from schema
6. **Audit Trail**: All entries are logged with user and timestamp
7. **Immutable Records**: Clinical events are never deleted, only appended

## Example Workflow

1. Doctor opens "Vitals" section
2. Frontend fetches schema: `/api/v1/schema/sections/vitals`
3. Form renders with proper labels, units, and input types
4. Doctor enters values (no type selection needed)
5. Data submitted with timestamp
6. System validates types and creates clinical events
7. Historical vitals can be viewed as a timeline

## Schema Definition Location

All medical field definitions are in:
```
backend/app/models/medical_schema.py
```

To add new fields or sections, update this file. The schema is immediately available via the API.
