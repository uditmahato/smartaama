import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, getErrorMessage } from "../services/api";

type FacilityKind = "phc" | "hospital";

type FacilityOption = {
  id: string;
  name: string;
  kind: FacilityKind;
};

export default function Signup() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [nmcNumber, setNmcNumber] = useState("");
  const [workingHospital, setWorkingHospital] = useState("");

  const [facilityKind, setFacilityKind] = useState<FacilityKind | "">("");
  const [facilityId, setFacilityId] = useState("");

  const [facilityOptions, setFacilityOptions] = useState<
    Record<FacilityKind, FacilityOption[]>
  >({
    phc: [],
    hospital: [],
  });

  const [loadingFacilities, setLoadingFacilities] = useState(false);
  const [facilityError, setFacilityError] = useState<string | null>(null);

  const [idCardFile, setIdCardFile] = useState<File | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const canRegister = useMemo(() => {
    return (
      email.trim().length > 0 &&
      password.length >= 10 &&
      fullName.trim().length > 0 &&
      phoneNumber.trim().length > 0 &&
      nmcNumber.trim().length > 0 &&
      workingHospital.trim().length > 0 &&
      facilityKind &&
      facilityId &&
      !!idCardFile
    );
  }, [
    email,
    password,
    fullName,
    phoneNumber,
    nmcNumber,
    workingHospital,
    facilityKind,
    facilityId,
    idCardFile,
  ]);

  async function loadFacilities() {
    if (loadingFacilities) return;

    setFacilityError(null);
    setLoadingFacilities(true);

    try {
      const [phcResp, hospitalResp] = await Promise.all([
        api.get<FacilityOption[]>("/facilities", { params: { kind: "phc" } }),
        api.get<FacilityOption[]>("/facilities", {
          params: { kind: "hospital" },
        }),
      ]);

      setFacilityOptions({ phc: phcResp.data, hospital: hospitalResp.data });
    } catch (err) {
      setFacilityError(getErrorMessage(err, "Could not load facilities"));
    } finally {
      setLoadingFacilities(false);
    }
  }

  useEffect(() => {
    void loadFacilities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setFacilityId("");
  }, [facilityKind]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canRegister || busy) return;

    setError(null);
    setInfo(null);
    setBusy(true);

    try {
      const formData = new FormData();
      formData.append("username", email.trim()); // important
      formData.append("email", email.trim());
      formData.append("password", password);
      formData.append("full_name", fullName.trim());
      formData.append("phone_number", phoneNumber.trim());
      formData.append("nmc_number", nmcNumber.trim());
      formData.append("working_hospital", workingHospital.trim());

      formData.append("facility_type", facilityKind);
      formData.append("facility_id", facilityId);

      if (idCardFile) {
        formData.append("id_card_image", idCardFile);
      }

      await api.post("/auth/register", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setInfo("Registration successful! Awaiting approval by admin.");
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(getErrorMessage(err, "Registration failed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
        py: 6,
        bgcolor: "#F7F8FB",
      }}
    >
      <Card
        sx={{
          width: 520,
          maxWidth: "100%",
          borderRadius: 3,
          boxShadow: "0 12px 40px rgba(15, 23, 42, 0.10)",
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2.25}>
            <Stack spacing={0.5}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                Register
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Create your account to access SmartAama.
              </Typography>
            </Stack>

            {(error || info) && (
              <Stack spacing={1}>
                {error && <Alert severity="error">{error}</Alert>}
                {info && <Alert severity="success">{info}</Alert>}
              </Stack>
            )}

            <Box component="form" onSubmit={onSubmit} noValidate>
              <Stack spacing={2}>
                <TextField
                  label="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Password (min 10 characters)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Full Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Phone Number"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Nepal Medical Council Number"
                  value={nmcNumber}
                  onChange={(e) => setNmcNumber(e.target.value)}
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Currently Working Hospital"
                  value={workingHospital}
                  onChange={(e) => setWorkingHospital(e.target.value)}
                  required
                  fullWidth
                  disabled={busy}
                />

                <Button variant="outlined" component="label" disabled={busy}>
                  Upload ID Card Image
                  <input
                    type="file"
                    hidden
                    accept="image/*"
                    onChange={(e) => setIdCardFile(e.target.files?.[0] ?? null)}
                  />
                </Button>

                <Typography variant="caption" color="text.secondary">
                  {idCardFile
                    ? `Selected: ${idCardFile.name}`
                    : "No file selected"}
                </Typography>

                <FormControl component="fieldset" disabled={loadingFacilities}>
                  <FormLabel component="legend">Facility</FormLabel>
                  <RadioGroup
                    row
                    value={facilityKind}
                    onChange={(e) =>
                      setFacilityKind(e.target.value as FacilityKind)
                    }
                  >
                    <FormControlLabel
                      value="phc"
                      control={<Radio />}
                      label="PHC"
                    />
                    <FormControlLabel
                      value="hospital"
                      control={<Radio />}
                      label="Hospital"
                    />
                  </RadioGroup>
                </FormControl>

                {facilityKind && (
                  <TextField
                    select
                    label={
                      facilityKind === "phc" ? "Select PHC" : "Select Hospital"
                    }
                    value={facilityId}
                    onChange={(e) => setFacilityId(e.target.value)}
                    fullWidth
                    disabled={loadingFacilities}
                    helperText={
                      facilityError
                        ? facilityError
                        : loadingFacilities
                          ? "Loading facilities..."
                          : "Choose from the list"
                    }
                    error={Boolean(facilityError)}
                  >
                    {(facilityKind === "phc"
                      ? facilityOptions.phc
                      : facilityOptions.hospital
                    ).map((opt) => (
                      <MenuItem key={opt.id} value={opt.id}>
                        {opt.name}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={!canRegister || busy}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    borderRadius: 2,
                    py: 1.1,
                  }}
                >
                  {busy ? <CircularProgress size={20} /> : "Register"}
                </Button>

                <Button onClick={() => navigate("/login")}>
                  Already have an account? Sign in
                </Button>
              </Stack>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
