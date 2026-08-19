import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Container,
  Grid,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  Typography,
  Card,
  CardContent,
  Divider,
  Link,
} from "@mui/material";
import { tokenStore } from "../services/api";
import { useUser } from "../hooks/useUser";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import LogoutIcon from "@mui/icons-material/Logout";

export default function Home() {
  const navigate = useNavigate();
  const isLoggedIn = !!tokenStore.get();
  const { user } = useUser();
  const userName = user?.full_name || user?.username || "User";
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const features = [
    {
      emoji: "👩‍⚕️",
      title: "Patient Management",
      description:
        "Structured registration and longitudinal medical history tracking with reliable updates.",
    },
    {
      emoji: "📋",
      title: "Smart Referrals",
      description:
        "Coordinated referrals across facilities to support continuity of care and faster handoffs.",
    },
    {
      emoji: "📊",
      title: "Clinical Data",
      description:
        "Standardized clinical events and investigations with time-series views for better decisions.",
    },
    {
      emoji: "🔒",
      title: "Secure & Compliant",
      description:
        "Role-based access control and audit trails designed to protect sensitive patient data.",
    },
  ];

  const BRAND = {
    primary: "#4F46E5",
    primary2: "#4338CA",
    ink: "#0F172A",
    muted: "rgba(255,255,255,0.85)",
    border: "rgba(15, 23, 42, 0.10)",
    paper: "#FFFFFF",
    section: "#F7F8FB",
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column", bgcolor: BRAND.paper }}>
      {/* Header / Navigation */}
      <Box
        sx={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: `linear-gradient(135deg, ${BRAND.primary} 0%, ${BRAND.primary2} 100%)`,
          color: "white",
          py: 2,
          boxShadow: "0 6px 24px rgba(15, 23, 42, 0.18)",
        }}
      >
        <Container maxWidth="lg">
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Box sx={{ fontSize: 28, lineHeight: 1 }}>💗</Box>
              <Stack spacing={0}>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 800,
                    letterSpacing: 0.2,
                    lineHeight: 1.1,
                  }}
                >
                  SmartAama
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ opacity: 0.9, letterSpacing: 0.6, textTransform: "uppercase" }}
                >
                  Maternal Care Platform
                </Typography>
              </Stack>
            </Stack>

            <Stack direction="row" spacing={1.5} alignItems="center">
              {isLoggedIn ? (
                <>
                  <Button
                    color="inherit"
                    variant="text"
                    onClick={() => navigate("/dashboard")}
                    sx={{
                      textTransform: "none",
                      fontSize: 15,
                      px: 1.5,
                      borderRadius: 2,
                      "&:hover": { background: "rgba(255,255,255,0.12)" },
                    }}
                  >
                    Dashboard
                  </Button>

                  <Box
                    sx={{
                      pl: 2,
                      ml: 1,
                      borderLeft: "1px solid rgba(255,255,255,0.25)",
                      display: { xs: "none", sm: "block" },
                    }}
                  >
                    <Button
                      onClick={(e) => setAnchorEl(e.currentTarget)}
                      endIcon={<ArrowDropDownIcon />}
                      sx={{
                        textTransform: "none",
                        color: "white",
                        borderRadius: 2,
                        px: 1.5,
                        py: 0.5,
                        "&:hover": { background: "rgba(255,255,255,0.10)" },
                      }}
                    >
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <AccountCircleIcon sx={{ fontSize: 22 }} />
                        <Stack spacing={0} alignItems="flex-start">
                          <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2, fontSize: 13 }}>
                            {userName}
                          </Typography>
                          <Typography variant="caption" sx={{ opacity: 0.8, lineHeight: 1, fontSize: 10 }}>
                            Logged in
                          </Typography>
                        </Stack>
                      </Stack>
                    </Button>

                    <Menu
                      anchorEl={anchorEl}
                      open={menuOpen}
                      onClose={() => setAnchorEl(null)}
                      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                      transformOrigin={{ vertical: "top", horizontal: "right" }}
                      slotProps={{
                        paper: {
                          sx: {
                            mt: 1,
                            minWidth: 180,
                            borderRadius: 2,
                            boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
                          },
                        },
                      }}
                    >
                      <MenuItem
                        onClick={() => {
                          setAnchorEl(null);
                          tokenStore.clear();
                          navigate("/login", { replace: true });
                        }}
                        sx={{ py: 1.5, px: 2 }}
                      >
                        <LogoutIcon sx={{ mr: 1.5, fontSize: 20, color: "text.secondary" }} />
                        <Typography variant="body2">Logout</Typography>
                      </MenuItem>
                    </Menu>
                  </Box>

                  <IconButton
                    onClick={() => {
                      tokenStore.clear();
                      navigate("/login", { replace: true });
                    }}
                    sx={{
                      display: { xs: "flex", sm: "none" },
                      color: "white",
                    }}
                  >
                    <LogoutIcon />
                  </IconButton>
                </>
              ) : (
                <Button
                  color="inherit"
                  variant="outlined"
                  onClick={() => navigate("/login")}
                  sx={{
                    textTransform: "none",
                    borderColor: "rgba(255,255,255,0.55)",
                    borderRadius: 2,
                    "&:hover": { borderColor: "rgba(255,255,255,0.8)", background: "rgba(255,255,255,0.08)" },
                  }}
                >
                  Login
                </Button>
              )}
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Hero Section */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${BRAND.primary} 0%, ${BRAND.primary2} 100%)`,
          color: "white",
          py: { xs: 7, md: 10 },
        }}
      >
        <Container maxWidth="lg">
          <Stack spacing={3} alignItems="center" textAlign="center">
            <Typography
              variant="h3"
              sx={{
                fontWeight: 800,
                letterSpacing: -0.4,
                maxWidth: 900,
                lineHeight: 1.12,
              }}
            >
              Maternal Health Operations, Simplified
            </Typography>

            <Typography
              variant="h6"
              sx={{
                maxWidth: 760,
                color: BRAND.muted,
                fontWeight: 400,
                lineHeight: 1.7,
              }}
            >
              SmartAama supports primary health centers in Nepal with a unified system for patient management,
              referrals, and clinical tracking—built for day-to-day clinical workflows.
            </Typography>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 2 }}>
              {isLoggedIn ? (
                <Button
                  variant="contained"
                  size="large"
                  sx={{
                    background: "white",
                    color: BRAND.primary2,
                    fontWeight: 700,
                    textTransform: "none",
                    borderRadius: 2,
                    px: 3,
                    "&:hover": { background: "rgba(255,255,255,0.92)" },
                  }}
                  onClick={() => navigate("/dashboard")}
                >
                  Go to Dashboard
                </Button>
              ) : (
                <>
                  <Button
                    variant="contained"
                    size="large"
                    sx={{
                      background: "white",
                      color: BRAND.primary2,
                      fontWeight: 700,
                      textTransform: "none",
                      borderRadius: 2,
                      px: 3,
                      "&:hover": { background: "rgba(255,255,255,0.92)" },
                    }}
                    onClick={() => navigate("/login")}
                  >
                    Sign in
                  </Button>

                  <Button
                    variant="outlined"
                    size="large"
                    sx={{
                      borderColor: "rgba(255,255,255,0.65)",
                      color: "white",
                      fontWeight: 700,
                      textTransform: "none",
                      borderRadius: 2,
                      px: 3,
                      "&:hover": { background: "rgba(255, 255, 255, 0.10)", borderColor: "rgba(255,255,255,0.85)" },
                    }}
                    onClick={() => {
                      document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    View features
                  </Button>
                </>
              )}
            </Stack>

            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.78)", mt: 2 }}>
              Designed for reliability, usability, and data integrity in clinical environments.
            </Typography>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Box id="features" sx={{ py: { xs: 8, md: 10 }, background: BRAND.section }}>
        <Container maxWidth="lg">
          <Stack spacing={5}>
            <Stack spacing={1.5} textAlign="center" alignItems="center">
              <Typography variant="h4" sx={{ fontWeight: 800, color: BRAND.ink }}>
                Core Capabilities
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720, lineHeight: 1.8 }}>
                Purpose-built tools to help care teams register patients, document clinical progress, and coordinate referrals
                with consistent, auditable records.
              </Typography>
            </Stack>

            <Grid container spacing={3}>
              {features.map((feature, idx) => (
                <Grid item xs={12} sm={6} md={3} key={idx}>
                  <Card
                    sx={{
                      height: "100%",
                      borderRadius: 3,
                      border: `1px solid ${BRAND.border}`,
                      boxShadow: "none",
                      transition: "transform 160ms ease, box-shadow 160ms ease",
                      "&:hover": {
                        transform: "translateY(-3px)",
                        boxShadow: "0 10px 28px rgba(15, 23, 42, 0.12)",
                      },
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Stack spacing={1.5} alignItems="flex-start">
                        <Box
                          sx={{
                            width: 44,
                            height: 44,
                            borderRadius: 2,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "rgba(79, 70, 229, 0.10)",
                            fontSize: 22,
                          }}
                        >
                          {feature.emoji}
                        </Box>

                        <Typography variant="h6" sx={{ fontWeight: 750, color: BRAND.ink }}>
                          {feature.title}
                        </Typography>

                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                          {feature.description}
                        </Typography>
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Stack>
        </Container>
      </Box>

      {/* About Section */}
      <Box sx={{ py: { xs: 8, md: 10 } }}>
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={6}>
              <Stack spacing={2.5}>
                <Typography variant="h4" sx={{ fontWeight: 800, color: BRAND.ink }}>
                  About SmartAama
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.9 }}>
                  SmartAama supports maternal and antenatal care delivery in Nepal’s primary health centers by consolidating
                  patient information, clinical documentation, and referral coordination into a single workflow.
                </Typography>

                <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.9 }}>
                  Developed with input from healthcare professionals, the platform emphasizes usability, accurate recordkeeping,
                  and alignment with clinical best practices to improve care quality and outcomes.
                </Typography>

                <Divider sx={{ opacity: 0.6 }} />

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Stack spacing={0.5}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, color: BRAND.primary2 }}>
                        Real-time
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Reliable patient record updates
                      </Typography>
                    </Stack>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Stack spacing={0.5}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, color: BRAND.primary2 }}>
                        Secure
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Access control and audit visibility
                      </Typography>
                    </Stack>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Stack spacing={0.5}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 800, color: BRAND.primary2 }}>
                        Scalable
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Operates across facility contexts
                      </Typography>
                    </Stack>
                  </Grid>
                </Grid>
              </Stack>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  borderRadius: 3,
                  p: { xs: 3.5, md: 4.5 },
                  color: "white",
                  background: `linear-gradient(135deg, ${BRAND.primary} 0%, ${BRAND.primary2} 100%)`,
                  boxShadow: "0 14px 40px rgba(15, 23, 42, 0.18)",
                }}
              >
                <Stack spacing={2.2} textAlign="left">
                  <Typography variant="overline" sx={{ opacity: 0.85, letterSpacing: 1 }}>
                    Clinical mission
                  </Typography>

                  <Typography variant="h5" sx={{ fontWeight: 850, lineHeight: 1.25 }}>
                    Enabling better maternal care through dependable workflows
                  </Typography>

                  <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)", lineHeight: 1.9 }}>
                    Built for care teams that need clarity, consistency, and accountability—without increasing administrative burden.
                  </Typography>

                  <Divider sx={{ opacity: 0.25 }} />

                  <Typography variant="caption" sx={{ opacity: 0.85 }}>
                    Every mother matters. Every life counts.
                  </Typography>
                </Stack>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Contact Section */}
      <Box sx={{ py: { xs: 8, md: 10 }, background: BRAND.section }}>
        <Container maxWidth="lg">
          <Stack spacing={5}>
            <Stack spacing={1.5} textAlign="center">
              <Typography variant="h4" sx={{ fontWeight: 800, color: BRAND.ink }}>
                Contact
              </Typography>
              <Typography variant="body1" color="text.secondary">
                For support, onboarding, or deployment inquiries, reach our team.
              </Typography>
            </Stack>

            <Grid container spacing={3} justifyContent="center">
              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", borderRadius: 3, border: `1px solid ${BRAND.border}`, boxShadow: "none" }}>
                  <CardContent sx={{ textAlign: "center", p: 3 }}>
                    <Box sx={{ fontSize: 28, mb: 1.5 }}>📍</Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 750, color: BRAND.ink, mb: 0.5 }}>
                      Address
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Kathmandu, Nepal
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", borderRadius: 3, border: `1px solid ${BRAND.border}`, boxShadow: "none" }}>
                  <CardContent sx={{ textAlign: "center", p: 3 }}>
                    <Box sx={{ fontSize: 28, mb: 1.5 }}>🛟</Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 750, color: BRAND.ink, mb: 0.5 }}>
                      Support
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Contact your facility administrator for access and support.
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", borderRadius: 3, border: `1px solid ${BRAND.border}`, boxShadow: "none" }}>
                  <CardContent sx={{ textAlign: "center", p: 3 }}>
                    <Box sx={{ fontSize: 28, mb: 1.5 }}>📧</Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 750, color: BRAND.ink, mb: 0.5 }}>
                      Email
                    </Typography>
                    <Link
                      href="mailto:info@smartaama.com"
                      sx={{
                        color: BRAND.primary2,
                        textDecoration: "none",
                        fontWeight: 600,
                        "&:hover": { textDecoration: "underline" },
                      }}
                    >
                      info@smartaama.com
                    </Link>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Stack>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ background: "#0B1220", color: "white", py: 4, mt: "auto", textAlign: "center" }}>
        <Container maxWidth="lg">
          <Divider sx={{ mb: 3, opacity: 0.18 }} />
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            © 2026 SmartAama. All rights reserved. Dedicated to improving maternal health in Nepal.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}
