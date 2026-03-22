import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Login from "./components/Auth/Login";
import Signup from "./components/Auth/Signup";
import Chatbot from "./components/Chatbot/Chatbot";

import AdminLogin from "./components/admin/AdminLogin";
import Dashboard from "./components/admin/Dashboard";
import ChatLogs from "./components/admin/ChatLogs";
import Users from "./components/admin/Users";
import Analytics from "./components/admin/Analytics";
import Intents from "./components/admin/Intents";
import Counseling from "./components/admin/Counseling";
import FunctionalData from "./components/admin/FunctionalData";
import AuditLogs from "./components/admin/AuditLogs";
import Integrations from "./components/admin/Integrations";

function ProtectedAdminRoute({ children }) {
  const admin = localStorage.getItem("admin");
  const adminToken = localStorage.getItem("adminToken");
  if (!admin || !adminToken) {
    return <Navigate to="/admin/login" replace />;
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/chat" element={<Chatbot />} />

        <Route path="/admin/login" element={<AdminLogin />} />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedAdminRoute>
              <Dashboard />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/chats"
          element={
            <ProtectedAdminRoute>
              <ChatLogs />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedAdminRoute>
              <Users />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/analytics"
          element={
            <ProtectedAdminRoute>
              <Analytics />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/intents"
          element={
            <ProtectedAdminRoute>
              <Intents />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/functional-data"
          element={
            <ProtectedAdminRoute>
              <FunctionalData />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/audit-logs"
          element={
            <ProtectedAdminRoute>
              <AuditLogs />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/integrations"
          element={
            <ProtectedAdminRoute>
              <Integrations />
            </ProtectedAdminRoute>
          }
        />
        <Route
          path="/admin/counseling"
          element={
            <ProtectedAdminRoute>
              <Counseling />
            </ProtectedAdminRoute>
          }
        />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
