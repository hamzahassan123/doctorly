import { Activity, CalendarDays, LogOut, MessageCircle, Shield } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const signOut = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/">
          <span className="brand-mark"><Activity size={21} /></span>
          <span>doctorly<span className="brand-period">.</span></span>
        </NavLink>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="primary-nav">
          {user?.role === "staff" ? (
            <NavLink to="/staff" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <Shield size={18} /> Staff dashboard
            </NavLink>
          ) : (
            <>
              <NavLink to="/chat" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <MessageCircle size={18} /> Care assistant
              </NavLink>
              <NavLink to="/appointments" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <CalendarDays size={18} /> Appointments
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="profile-chip">
            <span className="avatar">{user?.email.slice(0, 1).toUpperCase()}</span>
            <span className="profile-copy">
              <strong>{user?.email}</strong>
              <small>{user?.role === "staff" ? "Care team" : "Patient account"}</small>
            </span>
          </div>
          <button className="nav-link signout" onClick={signOut}>
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>
      <main className="main-panel">
        <Outlet />
      </main>
    </div>
  );
}
