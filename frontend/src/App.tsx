// frontend/src/App.tsx
import { lazy, Suspense, type ReactElement } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Box, CircularProgress, CssBaseline } from "@mui/material";

import { tokenStore } from "./services/api";
import RequireAdmin from "./components/RequiredAdmin";

// Route-level code splitting: each page is its own chunk and is only
// downloaded when first visited (keeps the initial bundle small).
const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const PatientSearch = lazy(() => import("./pages/PatientSearch"));
const PatientProfile = lazy(() => import("./pages/PatientProfile"));
const PatientEdit = lazy(() => import("./pages/PatientEdit"));
const PatientCreate = lazy(() => import("./pages/PatientCreate"));
const UpdateRecord = lazy(() => import("./pages/UpdateRecord"));
const Referral = lazy(() => import("./pages/Referral"));
const Users = lazy(() => import("./pages/admin/Users"));
const PendingUsers = lazy(() => import("./pages/admin/PendingUsers"));

function RequireAuth({ children }: { children: ReactElement }) {
  const token = tokenStore.get();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

/** Shown while a lazily loaded page chunk is being fetched. */
function RouteFallback() {
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

export default function App() {
  return (
    <BrowserRouter>
      <CssBaseline />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          {/* Public pages (no container) */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          {/* Legacy alias kept as a redirect */}
          <Route path="/admin" element={<Navigate to="/login" replace />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected pages */}
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          {/* Admin only routes */}
          <Route
            path="/admin/users"
            element={
              <RequireAdmin>
                <Users />
              </RequireAdmin>
            }
          />

          <Route
            path="/admin/pending"
            element={
              <RequireAdmin>
                <PendingUsers />
              </RequireAdmin>
            }
          />
          <Route
            path="/patients"
            element={
              <RequireAuth>
                <PatientSearch />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/new"
            element={
              <RequireAuth>
                <PatientCreate />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/:patientId/edit"
            element={
              <RequireAuth>
                <PatientEdit />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/:patientId/update"
            element={
              <RequireAuth>
                <UpdateRecord />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/:patientId/referral"
            element={
              <RequireAuth>
                <Referral />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/:patientId/referral/:referralId"
            element={
              <RequireAuth>
                <Referral />
              </RequireAuth>
            }
          />

          <Route
            path="/patients/:patientId"
            element={
              <RequireAuth>
                <PatientProfile />
              </RequireAuth>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
