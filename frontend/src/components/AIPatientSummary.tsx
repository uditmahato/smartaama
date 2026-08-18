// frontend/src/components/AIPatientSummary.tsx
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  AutoAwesome as AIIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
} from "@mui/icons-material";
import { api } from "../services/api";

interface AIPatientSummaryProps {
  patientId: string;
}

interface AISummary {
  summary: string;
  key_findings: string[];
  risk_level?: string;
  metadata?: any;
}

interface AIAnalysisResponse {
  patient_id: string;
  summary?: AISummary;
  last_analyzed_at: string;
  data_version: number;
  model_used?: string;
}

function AIPatientSummary({ patientId }: AIPatientSummaryProps) {
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
      }

      const params = new URLSearchParams({
        auto_generate: "true",
        ...(forceRegenerate && { force_regenerate: "true" }),
      });

      const response = await api.get(
        `/ai-analysis/patients/${patientId}/analysis?${params}`,
      );
      setAnalysis(response.data);
    } catch (err: any) {
      console.error("Error fetching AI analysis:", err);
      setError(err.response?.data?.detail || "Failed to load AI analysis");
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    if (patientId) {
      fetchAnalysis();
    }
  }, [patientId]);

  const getRiskColor = (level?: string) => {
    switch (level) {
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

  const getRiskIcon = (level?: string) => {
    switch (level) {
      case "critical":
      case "high":
        return <WarningIcon />;
      case "low":
        return <CheckIcon />;
      default:
        return null;
    }
  };

  if (loading && !regenerating) {
    return (
      <Stack alignItems="center" spacing={2} sx={{ py: 4 }}>
        <CircularProgress sx={{ color: "white" }} />
        <Typography variant="body2" sx={{ opacity: 0.9 }}>
          Generating AI summary...
        </Typography>
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert
        severity="error"
        sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}
      >
        {error}
      </Alert>
    );
  }

  if (!analysis?.summary) {
    return (
      <Alert
        severity="info"
        sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}
      >
        No AI summary available yet.
      </Alert>
    );
  }

  return (
    <Box
      sx={{
        background: "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
        borderRadius: 3,
        p: 0,
        border: "1px solid rgba(255, 255, 255, 0.2)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box sx={{ p: 3, pb: 2 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
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
              <AIIcon sx={{ color: "white", fontSize: 28 }} />
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
                AI Clinical Summary
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: "rgba(255, 255, 255, 0.8)",
                  fontSize: "0.875rem",
                  mt: 0.5,
                }}
              >
                Intelligent analysis of patient condition
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            {analysis.summary.risk_level && (
              <Chip
                {...(getRiskIcon(analysis.summary.risk_level) && {
                  icon: getRiskIcon(analysis.summary.risk_level),
                })}
                label={`${analysis.summary.risk_level.toUpperCase()} RISK`}
                color={getRiskColor(analysis.summary.risk_level) as any}
                sx={{
                  fontWeight: 700,
                  fontSize: "0.75rem",
                  height: 32,
                  "& .MuiChip-label": {
                    px: 2,
                  },
                }}
              />
            )}
            <Tooltip title="Regenerate analysis">
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
        </Stack>
      </Box>

      {/* Summary Content */}
      <Box
        sx={{
          mx: 3,
          mb: 3,
          p: 3,
          bgcolor: "rgba(255, 255, 255, 0.95)",
          borderRadius: 2,
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.1)",
        }}
      >
        <Typography
          variant="body1"
          sx={{
            lineHeight: 1.8,
            color: "#2c3e50",
            fontSize: "1rem",
            fontWeight: 400,
          }}
        >
          {analysis.summary.summary}
        </Typography>
      </Box>

      {/* Key Findings */}
      {analysis.summary.key_findings &&
        analysis.summary.key_findings.length > 0 && (
          <Box sx={{ mx: 3, mb: 3 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                color: "white",
                mb: 2,
                fontSize: "1.125rem",
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Box
                sx={{
                  width: 4,
                  height: 20,
                  bgcolor: "white",
                  borderRadius: 2,
                }}
              />
              Key Clinical Signs
            </Typography>
            <Stack spacing={2}>
              {analysis.summary.key_findings.map((finding, idx) => {
                const isElevated =
                  finding.includes("⚠️") ||
                  finding.includes("Elevated") ||
                  finding.includes("High") ||
                  finding.includes("Low");
                const isNormal = finding.includes("Normal");

                return (
                  <Box
                    key={idx}
                    sx={{
                      p: 2.5,
                      bgcolor: "rgba(255, 255, 255, 0.95)",
                      borderRadius: 2,
                      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
                      borderLeft: `4px solid ${
                        isElevated
                          ? "#e74c3c"
                          : isNormal
                            ? "#27ae60"
                            : "#3498db"
                      }`,
                    }}
                  >
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Box
                        sx={{
                          width: 32,
                          height: 32,
                          borderRadius: "50%",
                          bgcolor: isElevated
                            ? "#fee"
                            : isNormal
                              ? "#efe"
                              : "#eef",
                          color: isElevated
                            ? "#e74c3c"
                            : isNormal
                              ? "#27ae60"
                              : "#3498db",
                          fontSize: "1.25rem",
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        {isElevated ? "⚠" : isNormal ? "✓" : "📈"}
                      </Box>
                      <Typography
                        variant="body1"
                        sx={{
                          color: "#2c3e50",
                          lineHeight: 1.5,
                          fontSize: "1rem",
                          fontWeight: isElevated ? 600 : 500,
                        }}
                      >
                        {finding}
                      </Typography>
                    </Stack>
                  </Box>
                );
              })}
            </Stack>
          </Box>
        )}

      {/* Footer */}
      <Box
        sx={{
          px: 3,
          pb: 3,
        }}
      >
        <Box
          sx={{
            p: 2,
            bgcolor: "rgba(255, 255, 255, 0.1)",
            borderRadius: 2,
            border: "1px solid rgba(255, 255, 255, 0.2)",
          }}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", sm: "center" }}
            spacing={{ xs: 1, sm: 2 }}
          >
            <Stack direction="row" spacing={1} alignItems="center">
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: "#2ecc71",
                }}
              />
              <Typography
                variant="body2"
                sx={{
                  color: "rgba(255, 255, 255, 0.9)",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                }}
              >
                Last analyzed:{" "}
                {new Date(analysis.last_analyzed_at).toLocaleDateString()} at{" "}
                {new Date(analysis.last_analyzed_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </Typography>
            </Stack>
            {analysis.model_used && (
              <Chip
                label={`AI Model: ${analysis.model_used}`}
                size="small"
                sx={{
                  bgcolor: "rgba(255, 255, 255, 0.2)",
                  color: "white",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  "& .MuiChip-label": {
                    px: 1.5,
                  },
                }}
              />
            )}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

export default AIPatientSummary;
