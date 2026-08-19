// frontend/src/pages/Login.tsx
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { getErrorMessage, login } from "../services/api";

export default function Login() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canLogin = useMemo(
    () => username.trim().length > 0 && password.length > 0,
    [username, password],
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canLogin || busy) return;

    setError(null);
    setBusy(true);

    try {
      // Backend uses OAuth2PasswordRequestForm: `username` + `password`
      // (registered users sign in with their email as the username). `login`
      // stores the access token and the refresh token used to renew it.
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        getErrorMessage(err, "Sign-in failed. Please check your credentials."),
      );
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
              <Typography
                variant="h5"
                sx={{ fontWeight: 800, letterSpacing: 0.2 }}
              >
                SmartAama
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.7 }}
              >
                Sign in to access maternal records, clinical tracking, and
                referrals.
              </Typography>
            </Stack>

            {error && <Alert severity="error">{error}</Alert>}

            <Box component="form" onSubmit={onSubmit} noValidate>
              <Stack spacing={2}>
                <TextField
                  label="Username or email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                  fullWidth
                  disabled={busy}
                />

                <TextField
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  type="password"
                  required
                  fullWidth
                  disabled={busy}
                />

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={!canLogin || busy}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    borderRadius: 2,
                    py: 1.1,
                  }}
                >
                  {busy ? <CircularProgress size={20} /> : "Sign in"}
                </Button>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ textAlign: "center" }}
                >
                  Use your assigned credentials. If you do not have access,
                  contact your system administrator.
                </Typography>
              </Stack>
            </Box>

            <Divider sx={{ opacity: 0.7 }} />

            <Button onClick={() => navigate("/signup")}>
              Register your account
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
