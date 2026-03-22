import { useEffect, useState } from "react";
import AdminLayout from "./AdminLayout";
import { getUsers, deleteUser, exportUsers, importUsers } from "../../services/api";

function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, pages: 0, total: 0, limit: 20 });
  const [importing, setImporting] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [exporting, setExporting] = useState("");

  const loadUsers = async ({ requestedPage = page, requestedSearch = search } = {}) => {
    try {
      setLoading(true);
      setError("");
      const res = await getUsers({ page: requestedPage, limit: 20, search: requestedSearch.trim() });
      const items = res.data?.items;
      const pageInfo = res.data?.pagination;

      if (Array.isArray(items)) {
        setUsers(items);
        setPagination(pageInfo || { page: 1, pages: 0, total: 0, limit: 20 });
        setPage(pageInfo?.page || requestedPage || 1);
      } else {
        setUsers([]);
        setPagination({ page: 1, pages: 0, total: 0, limit: 20 });
        setError("Unexpected users response from server");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers({ requestedPage: 1, requestedSearch: "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (id, email) => {
    const isConfirmed = window.confirm(`Delete user ${email || id}? This action cannot be undone.`);
    if (!isConfirmed) {
      return;
    }

    try {
      await deleteUser(id);
      await loadUsers({ requestedPage: page, requestedSearch: search });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to delete user");
    }
  };

  const submitSearch = (event) => {
    event.preventDefault();
    setPage(1);
    loadUsers({ requestedPage: 1, requestedSearch: search });
  };

  const resetSearch = () => {
    setSearch("");
    setPage(1);
    loadUsers({ requestedPage: 1, requestedSearch: "" });
  };

  const goPrev = () => {
    if (page > 1) {
      loadUsers({ requestedPage: page - 1, requestedSearch: search });
    }
  };

  const goNext = () => {
    if (pagination.pages > page) {
      loadUsers({ requestedPage: page + 1, requestedSearch: search });
    }
  };

  const downloadBlob = (blob, fallbackName) => {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fallbackName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleExport = async (format) => {
    try {
      setExporting(format);
      const res = await exportUsers({ format, search: search.trim() });
      downloadBlob(res.data, `users_export.${format}`);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to export users");
    } finally {
      setExporting("");
    }
  };

  const handleImport = async () => {
    if (!selectedFile) {
      setError("Choose a CSV or JSON file first");
      return;
    }
    try {
      setImporting(true);
      await importUsers(selectedFile);
      setSelectedFile(null);
      await loadUsers({ requestedPage: 1, requestedSearch: search });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to import users");
    } finally {
      setImporting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Users</h2>
        <div className="row-actions">
          <input
            type="file"
            accept=".csv,.json,application/json,text/csv"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          />
          <button className="admin-btn" onClick={handleImport} disabled={importing}>
            {importing ? "Importing..." : "Import File"}
          </button>
          <button className="muted-btn" onClick={() => handleExport("csv")} disabled={exporting === "csv"}>
            {exporting === "csv" ? "Exporting CSV..." : "Export CSV"}
          </button>
          <button className="muted-btn" onClick={() => handleExport("json")} disabled={exporting === "json"}>
            {exporting === "json" ? "Exporting JSON..." : "Export JSON"}
          </button>
          <button className="admin-btn" onClick={() => loadUsers({ requestedPage: page, requestedSearch: search })}>Refresh</button>
        </div>
      </div>

      <form className="admin-toolbar" onSubmit={submitSearch}>
        <input
          className="admin-input"
          placeholder="Search name, email, registration"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="admin-btn">Search</button>
        <button type="button" className="muted-btn" onClick={resetSearch}>Clear</button>
      </form>

      {loading && <p>Loading users...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && users.length === 0 && (
        <div className="empty-state">No users found for your current filter.</div>
      )}

      {!loading && !error && users.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Registration</th>
                <th>Role</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id || user.email}>
                  <td>{user.name || "-"}</td>
                  <td>{user.email || "-"}</td>
                  <td>{user.registration_number || "-"}</td>
                  <td>{user.role || "student"}</td>
                  <td>
                    <button
                      className="danger-btn"
                      onClick={() => handleDelete(user.id, user.email)}
                      disabled={!user.id}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && pagination.pages > 0 && (
        <div className="pager">
          <button className="muted-btn" onClick={goPrev} disabled={page <= 1}>Previous</button>
          <p>Page {page} of {Math.max(1, pagination.pages)} | {pagination.total} users</p>
          <button className="muted-btn" onClick={goNext} disabled={page >= pagination.pages}>Next</button>
        </div>
      )}
    </AdminLayout>
  );
}

export default Users;
