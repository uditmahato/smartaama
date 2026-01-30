// frontend/src/components/AIReferralRecommendation.tsx
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
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
  Place as LocationIcon,
} from "@mui/icons-material";
import { api } from "../services/api";

interface AIReferralRecommendationProps {
  patientId: string;
}

interface ReferralRecommendation {
  referral_needed: boolean;
  urgency: string;
  confidence: number;
  reasons: string[];
  recommended_facility?: string;
  recommended_specialties: string[];
  risk_factors: any;
  clinical_indicators: any;
  estimated_distance_km?: number;
}

interface AIAnalysisResponse {
  patient_id: string;
  referral_recommendation?: ReferralRecommendation;
  last_analyzed_at: string;
  data_version: number;
  model_used?: string;
}

function AIReferralRecommendation({ patientId }: AIReferralRecommendationProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  const fetchAnalysis = async (forceRegenerate = false) => {
    try {
      setLoading(true);
      setError(null);

      if (forceRegenerate) {
        setRegenerating(true);
        await api.post("/ai-analysis/generate", {
          patient_id: patientId,
          force_regenerate: true,
        });
        setRegenerating(false);
      }

      const response = await api.get(`/ai-analysis/patient/${patientId}?auto_generate=true`);
      setAnalysis(response.data);
    } catch (err: any) {
      console.error("Error fetching AI analysis:", err);
      setError(err.response?.data?.detail || "Failed to load AI analysis");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (patientId) {
      fetchAnalysis();
    }
  }, [patientId]);

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toLowerCase()) {
      case "critical":
        return "error";
      case "high":
        return "warning";
      case "medium":
        return "info";
      case "low":
        return "success";
      default:
        return "default";
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
        background: "linear-gradient(135deg, #d946a6 0%, #ec4899 50%, #f43f5e 100%)",
        borderRadius: 2,
        p: 3,
        border: "1px solid rgba(255, 255, 255, 0.2)",
      }}
    >
      <Stack spacing={2.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={1} alignItems="center">
            <HospitalIcon sx={{ color: "white" }} />
            <Typography variant="h6" sx={{ fontWeight: 700, color: "white" }}>
              AI Referral Solution
            </Typography>
          </Stack>
          <Tooltip title="Regenerate recommendation">
            <IconButton
            size="small"
            onClick={() => fetchAnalysis(true)}
            disabled={regenerating}
            sx={{ color: "white" }}
          >
            {regenerating ? <CircularProgress size={20} sx={{ color: "white" }} /> : <RefreshIcon />}
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Referral Decision Card */}
      <Box
        sx={{
          p: 3,
          bgcolor: "rgba(255, 255, 255, 0.15)",
          borderRadius: 2,
          backdropFilter: "blur(10px)",
        }}
      >
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" spacing={2}>
            {rec.referral_needed ? (
              <ThumbUpIcon sx={{ fontSize: 40, opacity: 0.9 }} />
            ) : (
              <ThumbDownIcon sx={{ fontSize: 40, opacity: 0.9 }} />
            )}
            <Box flex={1}>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {rec.referral_needed ? "Referral Recommended" : "No Referral Needed"}
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.85, mt: 0.5 }}>
                {rec.referral_needed
                  ? "Patient should be referred to a higher facility"
                  : "Patient can continue care at current facility"}
              </Typography>
            </Box>
            <Chip
              label={rec.urgency.toUpperCase()}
              color={getUrgencyColor(rec.urgency)}
              sx={{ fontWeight: 700, fontSize: "0.875rem" }}
            />
          </Stack>

          <Divider sx={{ borderColor: "rgba(255,255,255,0.2)" }} />

          {/* Confidence Score */}
          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600, opacity: 0.9 }}>
                {getConfidenceLabel(rec.confidence)}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700, opacity: 0.9 }}>
                {Math.round(rec.confidence * 100)}%
              </Typography>
            </Stack>
            <LinearProgress
              variant="determinate"
              value={rec.confidence * 100}
              sx={{
                height: 8,
                borderRadius: 1,
                bgcolor: "rgba(255,255,255,0.2)",
                "& .MuiLinearProgress-bar": {
                  bgcolor: "white",
                },
              }}
            />
          </Box>
        </Stack>
      </Box>

      {/* Reasons */}
      {rec.reasons && rec.reasons.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, opacity: 0.9 }}>
            Reasons for Recommendation:
          </Typography>
          <Stack spacing={1}>
            {rec.reasons.map((reason, idx) => (
              <Box
                key={idx}
                sx={{
                  p: 1.5,
                  bgcolor: "rgba(255, 255, 255, 0.1)",
                  borderRadius: 1,
                  borderLeft: "3px solid rgba(255, 255, 255, 0.5)",
                }}
              >
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  • {reason}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Recommended Facility */}
      {rec.referral_needed && rec.recommended_facility && (
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Box
              sx={{
                p: 2,
                bgcolor: "rgba(255, 255, 255, 0.1)",
                borderRadius: 2,
              }}
            >
              <Stack direction="row" spacing={1} alignItems="center">
                <HospitalIcon sx={{ opacity: 0.8 }} />
                <Box>
                  <Typography variant="caption" sx={{ opacity: 0.7, display: "block" }}>
                    Recommended Facility
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 700 }}>
                    {rec.recommended_facility}
                  </Typography>
                </Box>
              </Stack>
            </Box>
          </Grid>
          {rec.estimated_distance_km && (
            <Grid item xs={12} sm={6}>
              <Box
                sx={{
                  p: 2,
                  bgcolor: "rgba(255, 255, 255, 0.1)",
                  borderRadius: 2,
                }}
              >
                <Stack direction="row" spacing={1} alignItems="center">
                  <LocationIcon sx={{ opacity: 0.8 }} />
                  <Box>
                    <Typography variant="caption" sx={{ opacity: 0.7, display: "block" }}>
                      Estimated Distance
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 700 }}>
                      {rec.estimated_distance_km} km
                    </Typography>
                  </Box>
                </Stack>
              </Box>
            </Grid>
          )}
        </Grid>
      )}

      {/* Specialties */}
      {rec.recommended_specialties && rec.recommended_specialties.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, opacity: 0.9 }}>
            Recommended Specialties:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
            {rec.recommended_specialties.map((specialty, idx) => (
              <Chip
                key={idx}
                label={specialty}
                size="small"
                sx={{
                  bgcolor: "rgba(255, 255, 255, 0.2)",
                  color: "white",
                  fontWeight: 600,
                }}
              />
            ))}
          </Stack>
        </Box>
      )}

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ pt: 1 }}>
        <Typography variant="caption" sx={{ opacity: 0.7, color: "white" }}>
          Last analyzed: {new Date(analysis.last_analyzed_at).toLocaleString()}
        </Typography>
        {analysis.model_used && (
          <Typography variant="caption" sx={{ opacity: 0.7, color: "white" }}>
            Model: {analysis.model_used}
          </Typography>
        )}
      </Stack>
      </Stack>
    </Box>
  );
}

export default AIReferralRecommendation;
