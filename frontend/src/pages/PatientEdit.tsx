import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  CircularProgress,
  MenuItem,
} from '@mui/material';
import { ArrowBack, Save } from '@mui/icons-material';
import { api } from '../services/api';

interface Patient {
  id: string;
  patient_id: string;
  facility_mrn?: string;
  national_id?: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  age_in_years?: number;
  sex?: string;
  phone_number?: string;
  address_line?: string;
  ward?: string;
  municipality?: string;
  district?: string;
  province?: string;
}

const PatientEdit: React.FC = () => {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    facility_mrn: '',
    national_id: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    age_in_years: '',
    sex: '',
    phone_number: '',
    address_line: '',
    ward: '',
    municipality: '',
    district: '',
    province: '',
  });

  useEffect(() => {
    loadPatient();
  }, [patientId]);

  const loadPatient = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/patients/${patientId}`);
      setPatient(response.data);
      setFormData({
        facility_mrn: response.data.facility_mrn || '',
        national_id: response.data.national_id || '',
        first_name: response.data.first_name || '',
        middle_name: response.data.middle_name || '',
        last_name: response.data.last_name || '',
        age_in_years: response.data.age_in_years?.toString() || '',
        sex: response.data.sex || '',
        phone_number: response.data.phone_number || '',
        address_line: response.data.address_line || '',
        ward: response.data.ward || '',
        municipality: response.data.municipality || '',
        district: response.data.district || '',
        province: response.data.province || '',
      });
    } catch (err: any) {
      setError('Failed to load patient information');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const payload: any = {};
      
      // Only include fields that have changed
      if (formData.facility_mrn !== (patient?.facility_mrn || '')) {
        payload.facility_mrn = formData.facility_mrn || null;
      }
      if (formData.national_id !== (patient?.national_id || '')) {
        payload.national_id = formData.national_id || null;
      }
      if (formData.first_name !== (patient?.first_name || '')) {
        payload.first_name = formData.first_name;
      }
      if (formData.middle_name !== (patient?.middle_name || '')) {
        payload.middle_name = formData.middle_name || null;
      }
      if (formData.last_name !== (patient?.last_name || '')) {
        payload.last_name = formData.last_name;
      }
      if (formData.age_in_years !== (patient?.age_in_years?.toString() || '')) {
        payload.age_in_years = formData.age_in_years ? parseInt(formData.age_in_years) : null;
      }
      if (formData.sex !== (patient?.sex || '')) {
        payload.sex = formData.sex || null;
      }
      if (formData.phone_number !== (patient?.phone_number || '')) {
        payload.phone_number = formData.phone_number || null;
      }
      if (formData.address_line !== (patient?.address_line || '')) {
        payload.address_line = formData.address_line || null;
      }
      if (formData.ward !== (patient?.ward || '')) {
        payload.ward = formData.ward || null;
      }
      if (formData.municipality !== (patient?.municipality || '')) {
        payload.municipality = formData.municipality || null;
      }
      if (formData.district !== (patient?.district || '')) {
        payload.district = formData.district || null;
      }
      if (formData.province !== (patient?.province || '')) {
        payload.province = formData.province || null;
      }

      await api.patch(`/patients/${patientId}`, payload);
      setSuccess(true);
      setTimeout(() => {
        navigate(`/patients/${patientId}`);
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update patient information');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!patient) {
    return (
      <Alert severity="error">Patient not found</Alert>
    );
  }

  return (
    <Box sx={{ py: 4 }}>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate(`/patients/${patientId}`)}
        sx={{ mb: 3 }}
      >
        Back to Patient Profile
      </Button>

      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
          Edit Patient Information
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Patient ID: {patient.patient_id}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 3 }}>Patient information updated successfully! Redirecting...</Alert>}

        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            {/* Identifiers */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2 }}>
                Identifiers
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Facility MRN"
                name="facility_mrn"
                value={formData.facility_mrn}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="National ID"
                name="national_id"
                value={formData.national_id}
                onChange={handleChange}
              />
            </Grid>

            {/* Personal Details */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2, mt: 2 }}>
                Personal Details
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                required
                label="First Name"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Middle Name"
                name="middle_name"
                value={formData.middle_name}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                required
                label="Last Name"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Age (Years)"
                name="age_in_years"
                type="number"
                value={formData.age_in_years}
                onChange={handleChange}
                inputProps={{ min: 0, max: 150 }}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Sex"
                name="sex"
                value={formData.sex}
                onChange={handleChange}
              >
                <MenuItem value="">Not Specified</MenuItem>
                <MenuItem value="Male">Male</MenuItem>
                <MenuItem value="Female">Female</MenuItem>
                <MenuItem value="Other">Other</MenuItem>
              </TextField>
            </Grid>

            {/* Contact Information */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2, mt: 2 }}>
                Contact Information
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Phone Number"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
              />
            </Grid>

            {/* Address */}
            <Grid item xs={12}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 2, mt: 2 }}>
                Address
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Province"
                name="province"
                value={formData.province}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="District"
                name="district"
                value={formData.district}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Metropolitan City / Sub Metropolitan City / Municipality"
                name="municipality"
                value={formData.municipality}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Ward"
                name="ward"
                value={formData.ward}
                onChange={handleChange}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Tole Name"
                name="address_line"
                value={formData.address_line}
                onChange={handleChange}
                multiline
                rows={2}
              />
            </Grid>

            {/* Submit Button */}
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  startIcon={<Save />}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate(`/patients/${patientId}`)}
                  disabled={saving}
                >
                  Cancel
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  );
};

export default PatientEdit;
