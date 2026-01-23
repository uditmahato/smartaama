import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Container,
  Grid,
  Stack,
  Typography,
  Card,
  CardContent,
  Divider,
  Link,
} from "@mui/material";
import { tokenStore } from "../services/api";

export default function Home() {
  const navigate = useNavigate();
  const isLoggedIn = !!tokenStore.get();

  const features = [
    {
      emoji: "👩‍⚕️",
      title: "Patient Management",
      description: "Comprehensive patient registration and medical history tracking with real-time updates.",
    },
    {
      emoji: "📋",
      title: "Smart Referrals",
      description: "Streamlined referral system for seamless inter-facility communication and patient care coordination.",
    },
    {
      emoji: "📊",
      title: "Clinical Data",
      description: "Structured clinical events and investigations with time-series data analysis capabilities.",
    },
    {
      emoji: "🔒",
      title: "Secure & Compliant",
      description: "Role-based access control and audit logs ensuring data security and regulatory compliance.",
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header/Navigation */}
      <Box
        sx={{
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
          py: 3,
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.1)",
        }}
      >
        <Container maxWidth="lg">
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" alignItems="center" spacing={1}>
              <Box sx={{ fontSize: "2rem" }}>💗</Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                SmartAama
              </Typography>
            </Stack>
            <Stack direction="row" spacing={2}>
              {isLoggedIn ? (
                <>
                  <Button
                    color="inherit"
                    variant="text"
                    onClick={() => navigate("/dashboard")}
                    sx={{ textTransform: "none", fontSize: 16 }}
                  >
                    Dashboard
                  </Button>
                  <Button
                    color="inherit"
                    variant="outlined"
                    onClick={() => {
                      tokenStore.clear();
                      navigate("/login", { replace: true });
                    }}
                    sx={{ textTransform: "none" }}
                  >
                    Logout
                  </Button>
                </>
              ) : (
                <Button
                  color="inherit"
                  variant="outlined"
                  onClick={() => navigate("/admin")}
                  sx={{ textTransform: "none" }}
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
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
          py: { xs: 6, md: 10 },
        }}
      >
        <Container maxWidth="lg">
          <Stack spacing={4} alignItems="center" textAlign="center">
            <Typography variant="h3" sx={{ fontWeight: 700, mb: 2 }}>
              Maternal Health Made Simple
            </Typography>
            <Typography variant="h6" sx={{ maxWidth: 600, opacity: 0.95, fontWeight: 300 }}>
              SmartAama is a comprehensive maternal and antenatal care management system designed for primary health centers in Nepal. 
              Streamline patient care, manage referrals, and track clinical data with ease.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 4 }}>
              {isLoggedIn ? (
                <Button
                  variant="contained"
                  size="large"
                  sx={{
                    background: "white",
                    color: "#667eea",
                    fontWeight: 600,
                    "&:hover": { background: "#f5f5f5" },
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
                      color: "#667eea",
                      fontWeight: 600,
                      "&:hover": { background: "#f5f5f5" },
                    }}
                    onClick={() => navigate("/admin")}
                  >
                    Login to System
                  </Button>
                  <Button
                    variant="outlined"
                    size="large"
                    sx={{
                      borderColor: "white",
                      color: "white",
                      fontWeight: 600,
                      "&:hover": { background: "rgba(255, 255, 255, 0.1)" },
                    }}
                    onClick={() => {
                      document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Learn More
                  </Button>
                </>
              )}
            </Stack>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Box id="features" sx={{ py: 10, background: "#f8f9fa" }}>
        <Container maxWidth="lg">
          <Stack spacing={6}>
            <Stack spacing={2} textAlign="center">
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                Key Features
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: "auto" }}>
                Designed specifically for maternal health management with powerful tools for clinical care coordination
              </Typography>
            </Stack>

            <Grid container spacing={3}>
              {features.map((feature, idx) => (
                <Grid item xs={12} sm={6} md={3} key={idx}>
                  <Card
                    sx={{
                      height: "100%",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      textAlign: "center",
                      p: 3,
                      transition: "all 0.3s ease",
                      border: "1px solid #e0e0e0",
                      "&:hover": {
                        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.12)",
                        transform: "translateY(-4px)",
                      },
                    }}
                  >
                    <Box sx={{ fontSize: "3rem", mb: 2 }}>
                      {feature.emoji}
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      {feature.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {feature.description}
                    </Typography>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Stack>
        </Container>
      </Box>

      {/* About Section */}
      <Box sx={{ py: 10 }}>
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={6}>
              <Stack spacing={3}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  About SmartAama
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                  SmartAama is specifically designed to support maternal and antenatal care delivery in Nepal's primary health centers. 
                  Our system helps healthcare providers manage patient information, track clinical progress, coordinate referrals, 
                  and make informed decisions through integrated data visualization.
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                  Built with input from healthcare professionals, SmartAama prioritizes ease of use, data accuracy, and clinical best practices 
                  to improve maternal health outcomes in underserved communities.
                </Typography>
                <Stack direction="row" spacing={3} sx={{ mt: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: "#667eea" }}>
                      Real-time
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Live patient data sync
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: "#667eea" }}>
                      Secure
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      HIPAA compliant storage
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: "#667eea" }}>
                      Scalable
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Works offline & online
                    </Typography>
                  </Box>
                </Stack>
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  borderRadius: 3,
                  p: 4,
                  color: "white",
                  textAlign: "center",
                }}
              >
                <Box sx={{ fontSize: 80, mb: 2 }}>💕</Box>
                <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
                  Supporting Maternal Health
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9, mb: 3 }}>
                  Empowering healthcare workers with technology to deliver better maternal care
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  "Every mother matters. Every life counts."
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Contact Section */}
      <Box sx={{ py: 10, background: "#f8f9fa" }}>
        <Container maxWidth="lg">
          <Stack spacing={6}>
            <Stack spacing={2} textAlign="center">
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                Contact Us
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Questions? We're here to help. Reach out to our team.
              </Typography>
            </Stack>

            <Grid container spacing={4} justifyContent="center">
              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", border: "1px solid #e0e0e0" }}>
                  <CardContent sx={{ textAlign: "center" }}>
                    <Box sx={{ fontSize: 32, mb: 2 }}>📍</Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Address
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Kathmandu, Nepal
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", border: "1px solid #e0e0e0" }}>
                  <CardContent sx={{ textAlign: "center" }}>
                    <Box sx={{ fontSize: 32, mb: 2 }}>📞</Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Phone
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      +977-1-XXX-XXXX
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card sx={{ height: "100%", border: "1px solid #e0e0e0" }}>
                  <CardContent sx={{ textAlign: "center" }}>
                    <Box sx={{ fontSize: 32, mb: 2 }}>📧</Box>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                      Email
                    </Typography>
                    <Link
                      href="mailto:info@smartaama.com"
                      sx={{
                        color: "#667eea",
                        textDecoration: "none",
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
      <Box
        sx={{
          background: "#2c3e50",
          color: "white",
          py: 4,
          mt: "auto",
          textAlign: "center",
        }}
      >
        <Container maxWidth="lg">
          <Divider sx={{ mb: 3, opacity: 0.2 }} />
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            &copy; 2026 SmartAama. All rights reserved. | Dedicated to improving maternal health in Nepal.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}
