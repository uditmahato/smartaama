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

type UserMeResponse = {
  id: string;
  username: string;
  full_name?: string | null;
  role: string;
  is_active: bool;
};

// TS helper (because backend returns boolean, not bool; keep defensive)
type bool = boolean;

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

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const canLogin = useMemo(() => username.trim().length > 0 && password.length > 0, [username, password]);

  const canBootstrap = useMemo(() => {
    return (
      bootstrapToken.trim().length > 0 &&
      adminUsername.trim().length >= 3 &&
      adminPassword.length >= 10
    );
  }, [bootstrapToken, adminUsername, adminPassword]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
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
      setError(err?.response?.data?.detail ?? "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function bootstrapAdmin() {
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      const payload: BootstrapAdminRequest = {
        username: adminUsername.trim(),
        password: adminPassword,
        full_name: adminFullName.trim() || null,
      };

      const resp = await api.post<UserMeResponse>("/auth/bootstrap-admin", payload, {
        headers: {
          "X-Bootstrap-Token": bootstrapToken.trim(),
        },
      });

      setInfo(`Admin created: ${resp.data.username}. You can now log in.`);
      // Pre-fill login fields for convenience (no auto-login to avoid surprise)
      setUsername(payload.username);
      setPassword(payload.password);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Bootstrap failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
      <Card sx={{ width: 480 }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h5">Smart Aama</Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to access PHC maternal records and referrals.
            </Typography>

            {error && <Alert severity="error">{error}</Alert>}
            {info && <Alert severity="info">{info}</Alert>}

            <Box component="form" onSubmit={onSubmit}>
              <Stack spacing={2}>
                <TextField
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
                <TextField
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  type="password"
                  required
                />
                <Button type="submit" variant="contained" disabled={busy || !canLogin}>
                  {busy ? <CircularProgress size={20} /> : "Login"}
                </Button>
              </Stack>
            </Box>

            <Divider />

            <Stack spacing={1}>
              <Button variant="text" onClick={() => setShowBootstrap((v) => !v)}>
                {showBootstrap ? "Hide Bootstrap Admin (DEV)" : "Bootstrap Admin (DEV)"}
              </Button>

              <Collapse in={showBootstrap}>
                <Card variant="outlined">
                  <CardContent>
                    <Stack spacing={1.5}>
                      <Typography variant="subtitle1">Bootstrap Admin (DEV only)</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Requires backend ENV=dev and a matching BOOTSTRAP_TOKEN.
                      </Typography>

                      <TextField
                        label="Bootstrap token"
                        value={bootstrapToken}
                        onChange={(e) => setBootstrapToken(e.target.value)}
                        type="password"
                        fullWidth
                      />

                      <TextField
                        label="Admin username"
                        value={adminUsername}
                        onChange={(e) => setAdminUsername(e.target.value)}
                        fullWidth
                      />

                      <TextField
                        label="Admin password (min 10 chars)"
                        value={adminPassword}
                        onChange={(e) => setAdminPassword(e.target.value)}
                        type="password"
                        fullWidth
                      />

                      <TextField
                        label="Full name (optional)"
                        value={adminFullName}
                        onChange={(e) => setAdminFullName(e.target.value)}
                        fullWidth
                      />

                      <Button variant="outlined" onClick={bootstrapAdmin} disabled={busy || !canBootstrap}>
                        {busy ? <CircularProgress size={20} /> : "Create Admin"}
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
