// frontend/src/components/IdCardDialog.tsx
// Shows a user's uploaded ID card. The image is served by an admin-only,
// bearer-authenticated endpoint, so it is fetched as a Blob and displayed via
// an object URL (revoked when the dialog closes).
import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { fetchUserIdCardBlob, getErrorMessage } from "../services/api";

type IdCardDialogProps = {
  /** User whose ID card to show; `null` closes the dialog. */
  userId: string | null;
  title?: string;
  onClose: () => void;
};

export default function IdCardDialog({
  userId,
  title,
  onClose,
}: IdCardDialogProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    let url: string | null = null;

    setLoading(true);
    setError(null);
    setObjectUrl(null);

    fetchUserIdCardBlob(userId)
      .then((blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setObjectUrl(url);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(getErrorMessage(err, "Could not load the ID card image."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
      setObjectUrl(null);
    };
  }, [userId]);

  return (
    <Dialog open={Boolean(userId)} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{title ?? "ID Card"}</DialogTitle>
      <DialogContent>
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        )}
        {!loading && error && <Alert severity="error">{error}</Alert>}
        {!loading && !error && objectUrl && (
          <img
            src={objectUrl}
            alt="ID Card"
            style={{ width: "100%", height: "auto", display: "block" }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
