import { Navigate } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import { JSX } from "react";

export default function RequireAdmin({ children }: { children: JSX.Element }) {
  const user = useUser();

  if (!user) return <Navigate to="/login" replace />;

  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;

  return children;
}
