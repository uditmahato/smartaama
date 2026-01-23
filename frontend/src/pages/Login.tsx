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
  Collapse,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, tokenStore } from "../services/api";

type TokenResponse = {
  access_token: string;
  token_type: "bearer";
};

type BootstrapAdminRequest = {
  username: string;
  password: string;
  full_name?: string | null;
};

type bool = boolean;

type UserMeResponse = {
  id: string;
  username: string;
  full_name?: string | null;
  role: string;
  is_active: bool;
};

export default function Login() {
  const navigate = useNavigate();

  // Login
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Bootstrap panel (DEV-only usage)
  const [showBootstrap, setShowBootstrap] = useState(false);
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminFullName, setAdminFullName] = useState("");

  // Separate busy flags to avoid "Login" and "Bootstrap" blocking each other unnecessarily
  const [busyLogin, setBusyLogin] = useState(false);
  const [busyBootstrap, setBusyBootstrap] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const canLogin = useMemo(
    () => username.trim().length > 0 && password.length > 0,
    [username, password]
  );

  const canBootstrap = useMemo(() => {
    return (
      bootstrapToken.trim().length > 0 &&
      adminUsername.trim().length >= 3 &&
      adminPassword.length >= 10
    );
  }, [bootstrapToken, adminUsername, adminPassword]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canLogin || busyLogin) return;

    setError(null);
    setInfo(null);
    setBusyLogin(true);

    try {
      const body = new URLSearchParams();
      body.set("username", username.trim());
      body.set("password", password);
      // OAuth2PasswordRequestForm fields (safe defaults)
      body.set("grant_type", "");
      body.set("scope", "");
      body.set("client_id", "");
      body.set("client_secret", "");

      const resp = await api.post<TokenResponse>("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      tokenStore.set(resp.data.access_token);
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Sign-in failed. Please check your credentials.");
    } finally {
      setBusyLogin(false);
    }
  }

  async function bootstrapAdmin() {
    if (!canBootstrap || busyBootstrap) return;

    setError(null);
    setInfo(null);
    setBusyBootstrap(true);

    try {
      const payload: BootstrapAdminRequest = {
        username: adminUsername.trim(),
        password: adminPassword,
        full_name: adminFullName.trim() || null,
      };

      const resp = await api.post<UserMeResponse>("/auth/bootstrap-admin", payload, {
        headers: { "X-Bootstrap-Token": bootstrapToken.trim() },
      });

      setInfo(`Admin account created for "${resp.data.username}". You can now sign in.`);
      // Pre-fill login fields for convenience (no auto-login)
      setUsername(payload.username);
      setPassword(payload.password);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Bootstrap failed. Verify token and server environment.");
    } finally {
      setBusyBootstrap(false);
    }
  }

  const isBusy = busyLogin || busyBootstrap;

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
              <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: 0.2 }}>
                SmartAama
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                Sign in to access maternal records, clinical tracking, and referrals.
              </Typography>
            </Stack>

            {(error || info) && (
              <Stack spacing={1}>
                {error && <Alert severity="error">{error}</Alert>}
                {info && <Alert severity="info">{info}</Alert>}
              </Stack>
            )}

            <Box component="form" onSubmit={onSubmit} noValidate>
              <Stack spacing={2}>
                <TextField
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                  fullWidth
                  disabled={isBusy}
                />

                <TextField
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  type="password"
                  required
                  fullWidth
                  disabled={isBusy}
                />

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={!canLogin || isBusy}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    borderRadius: 2,
                    py: 1.1,
                  }}
                >
                  {busyLogin ? <CircularProgress size={20} /> : "Sign in"}
                </Button>

                <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
                  Use your assigned credentials. If you do not have access, contact your system administrator.
                </Typography>
              </Stack>
            </Box>

            <Divider sx={{ opacity: 0.7 }} />

            <Stack spacing={1}>
              <Button
                variant="text"
                onClick={() => setShowBootstrap((v) => !v)}
                disabled={busyLogin} // allow reading, but avoid toggling mid-login
                sx={{
                  textTransform: "none",
                  justifyContent: "space-between",
                  px: 1,
                  borderRadius: 2,
                }}
              >
                {showBootstrap ? "Hide admin bootstrap (DEV)" : "Admin bootstrap (DEV)"}
              </Button>

              <Collapse in={showBootstrap}>
                <Card
                  variant="outlined"
                  sx={{
                    borderRadius: 3,
                    borderColor: "rgba(15, 23, 42, 0.12)",
                    bgcolor: "rgba(15, 23, 42, 0.02)",
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={1.75}>
                      <Stack spacing={0.5}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                          Bootstrap admin account
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                          Development-only action. Requires backend <b>ENV=dev</b> and a valid <b>BOOTSTRAP_TOKEN</b>.
                        </Typography>
                      </Stack>

                      <TextField
                        label="Bootstrap token"
                        value={bootstrapToken}
                        onChange={(e) => setBootstrapToken(e.target.value)}
                        type="password"
                        fullWidth
                        disabled={isBusy}
                      />

                      <TextField
                        label="Admin username"
                        value={adminUsername}
                        onChange={(e) => setAdminUsername(e.target.value)}
                        fullWidth
                        disabled={isBusy}
                      />

                      <TextField
                        label="Admin password (min 10 characters)"
                        value={adminPassword}
                        onChange={(e) => setAdminPassword(e.target.value)}
                        type="password"
                        fullWidth
                        disabled={isBusy}
                      />

                      <TextField
                        label="Full name (optional)"
                        value={adminFullName}
                        onChange={(e) => setAdminFullName(e.target.value)}
                        fullWidth
                        disabled={isBusy}
                      />

                      <Button
                        variant="outlined"
                        size="large"
                        onClick={bootstrapAdmin}
                        disabled={!canBootstrap || isBusy}
                        sx={{
                          textTransform: "none",
                          fontWeight: 700,
                          borderRadius: 2,
                          py: 1.05,
                        }}
                      >
                        {busyBootstrap ? <CircularProgress size={20} /> : "Create admin"}
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              </Collapse>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
