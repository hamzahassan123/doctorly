import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import { PublicOnly, RequireAuth, RequireStaff } from "./components/RouteGuards";
import { useAuth } from "./context/AuthContext";
import AppointmentsPage from "./pages/AppointmentsPage";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import StaffPage from "./pages/StaffPage";

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.role === "staff" ? "/staff" : "/chat"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<HomeRedirect />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route element={<RequireStaff />}>
            <Route path="/staff" element={<StaffPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
