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

interface Municipality {
  local_level_name: string;
  local_level_type: string;
  wards: number;
}

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
  
  const [provinces, setProvinces] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [wards, setWards] = useState<number>(0);
  
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
    loadProvinces();
    loadPatient();
  }, [patientId]);

  const loadProvinces = async () => {
    try {
      const response = await api.get('/locations/provinces');
      setProvinces(response.data);
    } catch (err) {
      console.error('Failed to load provinces:', err);
    }
  };

  const loadDistricts = async (province: string) => {
    try {
      const response = await api.get('/locations/districts', {
        params: { province },
      });
      setDistricts(response.data);
    } catch (err) {
      console.error('Failed to load districts:', err);
      setDistricts([]);
    }
  };

  const loadMunicipalities = async (province: string, district: string) => {
    try {
      const response = await api.get('/locations/municipalities', {
        params: { province, district },
      });
      setMunicipalities(response.data);
    } catch (err) {
      console.error('Failed to load municipalities:', err);
      setMunicipalities([]);
    }
  };

  const loadWards = async (province: string, district: string, municipality: string) => {
    try {
      const response = await api.get('/locations/wards', {
        params: { province, district, municipality },
      });
      setWards(response.data);
    } catch (err) {
      console.error('Failed to load wards:', err);
      setWards(0);
    }
  };

  const loadPatient = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/patients/${patientId}`);
      setPatient(response.data);
      const patientData = response.data;
      setFormData({
        facility_mrn: patientData.facility_mrn || '',
        national_id: patientData.national_id || '',
        first_name: patientData.first_name || '',
        middle_name: patientData.middle_name || '',
        last_name: patientData.last_name || '',
        age_in_years: patientData.age_in_years?.toString() || '',
        sex: patientData.sex || '',
        phone_number: patientData.phone_number || '',
        address_line: patientData.address_line || '',
        ward: patientData.ward || '',
        municipality: patientData.municipality || '',
        district: patientData.district || '',
        province: patientData.province || '',
      });
      
      // Load cascading data if patient has province set
      if (patientData.province) {
        await loadDistricts(patientData.province);
        if (patientData.district) {
          await loadMunicipalities(patientData.province, patientData.district);
          if (patientData.municipality) {
            await loadWards(patientData.province, patientData.district, patientData.municipality);
          }
        }
      }
    } catch (err: any) {
      setError('Failed to load patient information');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | { name?: string; value: unknown }>) => {
    const { name, value } = e.target as any;
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Handle cascading dropdowns
    if (name === 'province' && value) {
      loadDistricts(value as string);
      setFormData((prev) => ({ ...prev, district: '', municipality: '', ward: '' }));
      setDistricts([]);
      setMunicipalities([]);
      setWards(0);
    } else if (name === 'district' && value && formData.province) {
      loadMunicipalities(formData.province, value as string);
      setFormData((prev) => ({ ...prev, municipality: '', ward: '' }));
      setMunicipalities([]);
      setWards(0);
    } else if (name === 'municipality' && value && formData.province && formData.district) {
      loadWards(formData.province, formData.district, value as string);
      setFormData((prev) => ({ ...prev, ward: '' }));
      setWards(0);
    }
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

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Patient ID / Facility MRN: {patient.facility_mrn || patient.patient_id}
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
                select
                label="Province"
                name="province"
                value={formData.province}
                onChange={handleChange}
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
                fullWidth
                select
                label="District"
                name="district"
                value={formData.district}
                onChange={handleChange}
                disabled={!formData.province}
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
                fullWidth
                select
                label="Metropolitan City / Sub Metropolitan City / Municipality"
                name="municipality"
                value={formData.municipality}
                onChange={handleChange}
                disabled={!formData.district}
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
                fullWidth
                select
                label="Ward"
                name="ward"
                value={formData.ward}
                onChange={handleChange}
                disabled={!formData.municipality || wards === 0}
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
