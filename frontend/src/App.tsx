// frontend/src/App.tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { CssBaseline } from "@mui/material";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import PatientSearch from "./pages/PatientSearch";
import PatientProfile from "./pages/PatientProfile";
import PatientEdit from "./pages/PatientEdit";
import PatientCreate from "./pages/PatientCreate";
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

        {/* Protected pages */}
        <Route
          path="/dashboard"
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
          path="/patients/:patientId"
          element={
            <RequireAuth>
              <PatientProfile />
            </RequireAuth>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
