import AdminSidebar from "./AdminSidebar";
import AdminHeader from "./AdminHeader";
import "./Admin.css";

function AdminLayout({ children }) {

  return (
    <div className="admin-layout">

      <AdminSidebar />

      <div className="admin-main">

        <AdminHeader />

        <div className="admin-content">
          {children}
        </div>

      </div>

    </div>
  );

}

export default AdminLayout;