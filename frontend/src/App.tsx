// frontend/src/App.tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CssBaseline, Container } from "@mui/material";

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
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route
            path="/"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
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
            path="/patients/:patientId"
            element={
              <RequireAuth>
                <PatientProfile />
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

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Container>
    </BrowserRouter>
  );
}
