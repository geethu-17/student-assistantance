import { NavLink } from "react-router-dom";

function AdminSidebar() {
  return (
    <aside className="admin-sidebar">
      <h2>Admin Panel</h2>

      <nav>
        <NavLink to="/admin/dashboard">Dashboard</NavLink>
        <NavLink to="/admin/chats">Chat Logs</NavLink>
        <NavLink to="/admin/users">Users</NavLink>
        <NavLink to="/admin/analytics">Analytics</NavLink>
        <NavLink to="/admin/intents">Intent Manager</NavLink>
        <NavLink to="/admin/functional-data">Functional Data</NavLink>
        <NavLink to="/admin/audit-logs">Audit Logs</NavLink>
        <NavLink to="/admin/integrations">Integrations</NavLink>
        <NavLink to="/admin/counseling">Counseling</NavLink>
      </nav>
    </aside>
  );
}

export default AdminSidebar;
