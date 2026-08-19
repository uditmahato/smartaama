import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useUser } from "../hooks/useUser";

export default function RequireAdmin({ children }: { children: ReactElement }) {
  const { user, loading, isAuthenticated } = useUser();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  // Token present but no cached user yet: wait for /auth/me instead of
  // bouncing the admin to /login or /dashboard.
  if (!user && loading) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;

  return children;
}
