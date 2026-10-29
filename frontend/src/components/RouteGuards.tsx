import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading your workspace…</div>;
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

export function RequireStaff() {
  const { user } = useAuth();
  return user?.role === "staff" ? <Outlet /> : <Navigate to="/chat" replace />;
}

export function PublicOnly() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Loading your workspace…</div>;
  if (user) return <Navigate to={user.role === "staff" ? "/staff" : "/chat"} replace />;
  return <Outlet />;
}
