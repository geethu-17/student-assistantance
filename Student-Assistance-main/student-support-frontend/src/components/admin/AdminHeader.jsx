import { useNavigate } from "react-router-dom";

function AdminHeader() {
  const navigate = useNavigate();
  const admin = JSON.parse(localStorage.getItem("admin") || "null");

  const logout = () => {
    localStorage.removeItem("admin");
    localStorage.removeItem("adminToken");
    navigate("/admin/login");
  };

  return (
    <header className="admin-header">
      <div>
        <h2>AI Student Support Admin</h2>
        <p>{admin?.username ? `Signed in as ${admin.username}` : "Admin session"}</p>
      </div>
      <button className="danger-btn" onClick={logout}>Logout</button>
    </header>
  );
}

export default AdminHeader;
