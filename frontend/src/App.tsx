// frontend/src/App.tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CssBaseline, Container } from "@mui/material";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import PatientSearch from "./pages/PatientSearch";
import PatientProfile from "./pages/PatientProfile";
import UpdateRecord from "./pages/UpdateRecord";
import Referral from "./pages/Referral";
import { tokenStore } from "./services/api";
import { JSX } from "react";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = tokenStore.get();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <CssBaseline />
      <Routes>
        {/* Public pages (no container) */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/admin" element={<Login />} />

        {/* Protected pages (with container) */}
        <Route
          path="/dashboard"
          element={
            <Container maxWidth="lg" sx={{ py: 3 }}>
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            </Container>
          }
        />

        <Route
          path="/patients"
          element={
            <Container maxWidth="lg" sx={{ py: 3 }}>
              <RequireAuth>
                <PatientSearch />
              </RequireAuth>
            </Container>
          }
        />

        <Route
          path="/patients/:patientId"
          element={
            <Container maxWidth="lg" sx={{ py: 3 }}>
              <RequireAuth>
                <PatientProfile />
              </RequireAuth>
            </Container>
          }
        />

        <Route
          path="/patients/:patientId/update"
          element={
            <Container maxWidth="lg" sx={{ py: 3 }}>
              <RequireAuth>
                <UpdateRecord />
              </RequireAuth>
            </Container>
          }
        />

        <Route
          path="/patients/:patientId/referral"
          element={
            <Container maxWidth="lg" sx={{ py: 3 }}>
              <RequireAuth>
                <Referral />
              </RequireAuth>
            </Container>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
