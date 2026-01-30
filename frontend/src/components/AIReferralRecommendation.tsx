// Simplified AI Referral Recommendation Component
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  LocalHospital as HospitalIcon,
  Refresh as RefreshIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
} from "@mui/icons-material";
import { api } from "../services/api";

interface AIReferralRecommendationProps {
  patientId: string;
}

interface DetectedRisk {
  name: string;
  weight: number;
  value: string;
}

interface RiskFactors {
  detected_risks?: DetectedRisk[];
  confidence_calculation?: string;
  data_points_analyzed?: number;
}

interface ReferralRecommendation {
  referral_needed: boolean;
  urgency: string;
  confidence: number;
  reasons: string[];
  risk_factors: RiskFactors;
  clinical_indicators: any;
}

interface AIAnalysisResponse {
  patient_id: string;
  referral_recommendation?: ReferralRecommendation;
  last_analyzed_at: string;
  data_version: number;
  model_used?: string;
}

function AIReferralRecommendation({ patientId }: AIReferralRecommendationProps) {
  const [analysis, setAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = async (forceRegenerate = false) => {
    try {
      if (forceRegenerate) {
        setRegenerating(true);
      } else {
        setLoading(true);
      }
      
      const params = new URLSearchParams({
        auto_generate: "true",
        ...(forceRegenerate && { force_regenerate: "true" })
      });

      const response = await api.get(`/ai-analysis/patient/${patientId}?${params}`);
      setAnalysis(response.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch AI analysis:", err);
      setError(err.response?.data?.detail || "Failed to load AI analysis");
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [patientId]);

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "critical":
        return "error" as const;
      case "high":
        return "warning" as const;
      case "medium":
        return "info" as const;
      default:
        return "success" as const;
    }
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return "High Confidence";
    if (confidence >= 0.6) return "Moderate Confidence";
    return "Low Confidence";
  };

  if (loading && !regenerating) {
    return (
      <Stack alignItems="center" spacing={2} sx={{ py: 4 }}>
        <CircularProgress sx={{ color: "white" }} />
        <Typography variant="body2" sx={{ opacity: 0.9 }}>
          Analyzing referral needs...
        </Typography>
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}>
        {error}
      </Alert>
    );
  }

  if (!analysis?.referral_recommendation) {
    return (
      <Alert severity="info" sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}>
        No referral recommendation available yet.
      </Alert>
    );
  }

  const rec = analysis.referral_recommendation;

  return (
    <Box
      sx={{
        background: "linear-gradient(135deg, #e91e63 0%, #ad1457 100%)",
        borderRadius: 3,
        p: 0,
        border: "1px solid rgba(255, 255, 255, 0.2)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box sx={{ p: 3, pb: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={2} alignItems="center">
            <Box
              sx={{
                p: 1.5,
                bgcolor: "rgba(255, 255, 255, 0.2)",
                borderRadius: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <HospitalIcon sx={{ color: "white", fontSize: 28 }} />
            </Box>
            <Box>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 700,
                  color: "white",
                  fontSize: "1.5rem",
                  letterSpacing: "-0.5px",
                }}
              >
                Referral Decision
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: "rgba(255, 255, 255, 0.8)",
                  fontSize: "0.875rem",
                  mt: 0.5,
                }}
              >
                Based on clinical data analysis
              </Typography>
            </Box>
          </Stack>
          <Tooltip title="Regenerate recommendation">
            <IconButton
              size="small"
              onClick={() => fetchAnalysis(true)}
              disabled={regenerating}
              sx={{
                color: "white",
                bgcolor: "rgba(255, 255, 255, 0.1)",
                "&:hover": {
                  bgcolor: "rgba(255, 255, 255, 0.2)",
                },
              }}
            >
              {regenerating ? (
                <CircularProgress size={18} sx={{ color: "white" }} />
              ) : (
                <RefreshIcon fontSize="small" />
              )}
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* Main Decision */}
      <Box sx={{ mx: 3, mb: 3, p: 3, bgcolor: "rgba(255, 255, 255, 0.95)", borderRadius: 2 }}>
        <Stack direction="row" alignItems="center" spacing={3}>
          <Box
            sx={{
              p: 2,
              borderRadius: 3,
              bgcolor: rec.referral_needed ? "#e8f5e8" : "#f5f5f5",
              border: `2px solid ${rec.referral_needed ? "#4caf50" : "#9e9e9e"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {rec.referral_needed ? (
              <ThumbUpIcon sx={{ fontSize: 32, color: "#4caf50" }} />
            ) : (
              <ThumbDownIcon sx={{ fontSize: 32, color: "#9e9e9e" }} />
            )}
          </Box>
          <Box flex={1}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: "#2c3e50", fontSize: "1.75rem", mb: 0.5 }}>
              {rec.referral_needed ? "Referral Needed" : "No Referral Needed"}
            </Typography>
            <Typography variant="body1" sx={{ color: "#7f8c8d", fontSize: "1rem" }}>
              Confidence: {Math.round(rec.confidence * 100)}% • {getConfidenceLabel(rec.confidence)}
            </Typography>
          </Box>
          <Chip
            label={rec.urgency.toUpperCase()}
            color={getUrgencyColor(rec.urgency)}
            sx={{ fontWeight: 700, fontSize: "1rem", height: 40 }}
          />
        </Stack>

        {/* Confidence Bar */}
        <Box sx={{ mt: 3, p: 2, bgcolor: "#f8f9fa", borderRadius: 2 }}>
          <LinearProgress
            variant="determinate"
            value={rec.confidence * 100}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: "#e9ecef",
              "& .MuiLinearProgress-bar": {
                bgcolor: "linear-gradient(90deg, #e91e63, #ad1457)",
                borderRadius: 4,
              },
            }}
          />
        </Box>
      </Box>

      {/* Reasons */}
      {rec.reasons && rec.reasons.length > 0 && (
        <Box sx={{ mx: 3, mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "white", mb: 2, fontSize: "1.125rem" }}>
            Clinical Reasons
          </Typography>
          <Stack spacing={1.5}>
            {rec.reasons.map((reason, idx) => (
              <Box
                key={idx}
                sx={{
                  p: 2.5,
                  bgcolor: "rgba(255, 255, 255, 0.95)",
                  borderRadius: 2,
                  borderLeft: "4px solid #e91e63",
                }}
              >
                <Typography variant="body1" sx={{ color: "#2c3e50", fontWeight: 500 }}>
                  • {reason}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Risk Factors */}
      {rec.risk_factors?.detected_risks && rec.risk_factors.detected_risks.length > 0 ? (
        <Box sx={{ mx: 3, mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "white", mb: 2, fontSize: "1.125rem" }}>
            Detected Risk Factors ({rec.risk_factors.confidence_calculation || 'Calculating...'})
          </Typography>
          <Grid container spacing={2}>
            {rec.risk_factors.detected_risks.map((risk: DetectedRisk, idx: number) => (
              <Grid item xs={12} sm={6} key={idx}>
                <Box
                  sx={{
                    p: 2.5,
                    bgcolor: "rgba(255, 255, 255, 0.95)",
                    borderRadius: 2,
                    border: "2px solid #e91e63",
                  }}
                >
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#2c3e50" }}>
                      {risk.name}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: "#e91e63" }}>
                      {Math.round(risk.weight * 100)}%
                    </Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ color: "#7f8c8d" }}>
                    {risk.value}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Box>
      ) : (
        <Box sx={{ mx: 3, mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "white", mb: 2, fontSize: "1.125rem" }}>
            Risk Analysis
          </Typography>
          <Box sx={{ p: 2.5, bgcolor: "rgba(255, 255, 255, 0.95)", borderRadius: 2 }}>
            <Typography variant="body1" sx={{ color: "#2c3e50", textAlign: "center" }}>
              {rec.confidence > 0 ? "Analysis based on clinical data review" : "No specific risk factors detected"}
            </Typography>
          </Box>
        </Box>
      )}

      {/* Footer */}
      <Box sx={{ px: 3, pb: 3 }}>
        <Box sx={{ p: 2, bgcolor: "rgba(255, 255, 255, 0.1)", borderRadius: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems="center" spacing={2}>
            <Typography variant="body2" sx={{ color: "rgba(255, 255, 255, 0.9)", fontSize: "0.875rem" }}>
              Last analyzed: {new Date(analysis.last_analyzed_at).toLocaleDateString()} at{" "}
              {new Date(analysis.last_analyzed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </Typography>
            {analysis.model_used && (
              <Chip
                label={`AI: ${analysis.model_used}`}
                size="small"
                sx={{ bgcolor: "rgba(255, 255, 255, 0.2)", color: "white", fontWeight: 600 }}
              />
            )}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

export default AIReferralRecommendation;