// Example: Dynamic Medical Data Form Component
// frontend/src/components/MedicalDataForm.tsx

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  FormLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
  Typography,
  Paper,
  Alert,
} from '@mui/material';
import api from '../services/api';

interface FieldDefinition {
  name: string;
  label: string;
  field_type: string;
  unit?: string;
  nullable: boolean;
  enum_values?: string[];
  min_value?: number;
  max_value?: number;
}

interface SectionSchema {
  section_key: string;
  section_label: string;
  category: string;
  fields: FieldDefinition[];
}

interface MedicalDataFormProps {
  patientId: string;
  sectionKey: string;
  onSuccess?: () => void;
}

export const MedicalDataForm: React.FC<MedicalDataFormProps> = ({
  patientId,
  sectionKey,
  onSuccess,
}) => {
  const [schema, setSchema] = useState<SectionSchema | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSchema();
  }, [sectionKey]);

  const loadSchema = async () => {
    try {
      const response = await api.get(`/api/v1/schema/sections/${sectionKey}`);
      setSchema(response.data);
      
      // Initialize form data with default values
      const initialData: Record<string, any> = {};
      response.data.fields.forEach((field: FieldDefinition) => {
        if (field.field_type === 'boolean') {
          initialData[field.name] = false;
        } else {
          initialData[field.name] = '';
        }
      });
      setFormData(initialData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load schema');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Filter out empty values for nullable fields
      const dataPoints: Record<string, any> = {};
      schema?.fields.forEach((field) => {
        const value = formData[field.name];
        if (value !== '' && value !== null && value !== undefined) {
          dataPoints[field.name] = value;
        } else if (!field.nullable) {
          dataPoints[field.name] = value;
        }
      });

      await api.post(
        `/api/v1/medical-data/patients/${patientId}/sections/${sectionKey}`,
        {
          section_key: sectionKey,
          data_points: dataPoints,
          event_time: new Date().toISOString(),
        }
      );

      alert('Data saved successfully!');
      onSuccess?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save data');
    } finally {
      setLoading(false);
    }
  };

  const renderField = (field: FieldDefinition) => {
    const fieldLabel = field.unit
      ? `${field.label} (${field.unit})`
      : field.label;

    switch (field.field_type) {
      case 'boolean':
        return (
          <FormControlLabel
            key={field.name}
            control={
              <Switch
                checked={!!formData[field.name]}
                onChange={(e) =>
                  setFormData({ ...formData, [field.name]: e.target.checked })
                }
              />
            }
            label={fieldLabel}
          />
        );

      case 'enum':
        return (
          <FormControl key={field.name} fullWidth margin="normal">
            <FormLabel>{fieldLabel}</FormLabel>
            <Select
              value={formData[field.name] || ''}
              onChange={(e) =>
                setFormData({ ...formData, [field.name]: e.target.value })
              }
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
            </Select>
          </FormControl>
        );

      case 'integer':
      case 'float':
        return (
          <TextField
            key={field.name}
            label={fieldLabel}
            type="number"
            value={formData[field.name] || ''}
            onChange={(e) =>
              setFormData({
                ...formData,
                [field.name]:
                  field.field_type === 'integer'
                    ? parseInt(e.target.value, 10)
                    : parseFloat(e.target.value),
              })
            }
            fullWidth
            margin="normal"
            required={!field.nullable}
            inputProps={{
              min: field.min_value,
              max: field.max_value,
              step: field.field_type === 'integer' ? 1 : 0.1,
            }}
          />
        );

      case 'date':
        return (
          <TextField
            key={field.name}
            label={fieldLabel}
            type="date"
            value={formData[field.name] || ''}
            onChange={(e) =>
              setFormData({ ...formData, [field.name]: e.target.value })
            }
            fullWidth
            margin="normal"
            required={!field.nullable}
            InputLabelProps={{ shrink: true }}
          />
        );

      case 'string':
      default:
        return (
          <TextField
            key={field.name}
            label={fieldLabel}
            value={formData[field.name] || ''}
            onChange={(e) =>
              setFormData({ ...formData, [field.name]: e.target.value })
            }
            fullWidth
            margin="normal"
            required={!field.nullable}
          />
        );
    }
  };

  if (!schema) {
    return <Typography>Loading form...</Typography>;
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        {schema.section_label}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {schema.fields.map(renderField)}
        </Box>

        <Box sx={{ mt: 3 }}>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Data'}
          </Button>
        </Box>
      </form>
    </Paper>
  );
};

// Example usage:
// <MedicalDataForm 
//   patientId="patient-uuid" 
//   sectionKey="vitals"
//   onSuccess={() => console.log('Data saved!')}
// />
