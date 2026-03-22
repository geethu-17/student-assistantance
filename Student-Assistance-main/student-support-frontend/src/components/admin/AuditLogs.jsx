import { useEffect, useState } from "react";
import AdminLayout from "./AdminLayout";
import { getAdminAuditLogs, exportAdminAuditLogs } from "../../services/api";

function AuditLogs() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, pages: 0, total: 0, limit: 30 });
  const [exporting, setExporting] = useState("");

  const loadLogs = async ({ requestedPage = page } = {}) => {
    try {
      setLoading(true);
      setError("");
      const res = await getAdminAuditLogs({
        page: requestedPage,
        limit: 30,
        search: search.trim(),
        module: moduleFilter,
        action: actionFilter,
      });
      setRows(res.data?.items || []);
      setPagination(res.data?.pagination || { page: 1, pages: 0, total: 0, limit: 30 });
      setPage(res.data?.pagination?.page || requestedPage || 1);
    } catch (err) {
      setRows([]);
      setError(err.response?.data?.error || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs({ requestedPage: 1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      const res = await exportAdminAuditLogs({
        format,
        search: search.trim(),
        module: moduleFilter,
        action: actionFilter,
      });
      downloadBlob(res.data, `admin_audit_logs.${format}`);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to export audit logs");
    } finally {
      setExporting("");
    }
  };

  const goPrev = () => {
    if (page > 1) {
      loadLogs({ requestedPage: page - 1 });
    }
  };

  const goNext = () => {
    if (pagination.pages > page) {
      loadLogs({ requestedPage: page + 1 });
    }
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Audit Logs</h2>
        <div className="row-actions">
          <button className="muted-btn" onClick={() => handleExport("csv")} disabled={exporting === "csv"}>
            {exporting === "csv" ? "Exporting CSV..." : "Export CSV"}
          </button>
          <button className="muted-btn" onClick={() => handleExport("json")} disabled={exporting === "json"}>
            {exporting === "json" ? "Exporting JSON..." : "Export JSON"}
          </button>
          <button className="admin-btn" onClick={() => loadLogs({ requestedPage: page })}>Refresh</button>
        </div>
      </div>

      <form
        className="admin-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          loadLogs({ requestedPage: 1 });
        }}
      >
        <input
          className="admin-input"
          placeholder="Search admin/module/action/record"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <input
          className="admin-input"
          placeholder="Module filter (e.g. users, intents, programs)"
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
        />
        <select className="admin-input" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
          <option value="">All Actions</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
          <option value="import">Import</option>
          <option value="export">Export</option>
          <option value="read">Read</option>
        </select>
        <button className="admin-btn" type="submit">Apply</button>
      </form>

      {loading && <p>Loading audit logs...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && rows.length === 0 && <div className="empty-state">No audit records found.</div>}

      {!loading && rows.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Admin</th>
                <th>Action</th>
                <th>Module</th>
                <th>Record</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.timestamp ? new Date(row.timestamp).toLocaleString() : "-"}</td>
                  <td>{row.admin || "-"}</td>
                  <td>{row.action || "-"}</td>
                  <td>{row.module || "-"}</td>
                  <td>{row.record_id || "-"}</td>
                  <td>{JSON.stringify(row.details || {})}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && pagination.pages > 0 && (
        <div className="pager">
          <button className="muted-btn" onClick={goPrev} disabled={page <= 1}>Previous</button>
          <p>Page {page} of {Math.max(1, pagination.pages)} | {pagination.total} logs</p>
          <button className="muted-btn" onClick={goNext} disabled={page >= pagination.pages}>Next</button>
        </div>
      )}
    </AdminLayout>
  );
}

export default AuditLogs;
