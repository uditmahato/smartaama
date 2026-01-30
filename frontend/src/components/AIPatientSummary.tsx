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
      <Alert severity="error" sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}>
        {error}
      </Alert>
    );
  }

  if (!analysis?.summary) {
    return (
      <Alert severity="info" sx={{ bgcolor: "rgba(255,255,255,0.15)", color: "white" }}>
        No AI summary available yet.
      </Alert>
    );
  }

  return (
    <Box
      sx={{
        background: "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
        borderRadius: 2,
        p: 3,
        border: "1px solid rgba(255, 255, 255, 0.2)",
      }}
    >
      <Stack spacing={2}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={1} alignItems="center">
            <AIIcon sx={{ color: "white" }} />
            <Typography variant="h6" sx={{ fontWeight: 700, color: "white" }}>
              AI Patient Summary
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            {analysis.summary.risk_level && (
              <Chip
                icon={getRiskIcon(analysis.summary.risk_level)}
                label={`Risk: ${analysis.summary.risk_level.toUpperCase()}`}
                color={getRiskColor(analysis.summary.risk_level)}
                size="small"
                sx={{ fontWeight: 600 }}
              />
            )}
            <Tooltip title="Regenerate analysis">
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
      </Stack>

      <Box
        sx={{
          p: 2,
          bgcolor: "rgba(255, 255, 255, 0.15)",
          borderRadius: 2,
          backdropFilter: "blur(10px)",
        }}
      >
        <Typography variant="body1" sx={{ lineHeight: 1.7, opacity: 0.95 }}>
          {analysis.summary.summary}
        </Typography>
      </Box>

      {analysis.summary.key_findings && analysis.summary.key_findings.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, opacity: 0.9 }}>
            Key Findings:
          </Typography>
          <Stack spacing={1}>
            {analysis.summary.key_findings.map((finding, idx) => (
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
                  • {finding}
                </Typography>
              </Box>
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

export default AIPatientSummary;
