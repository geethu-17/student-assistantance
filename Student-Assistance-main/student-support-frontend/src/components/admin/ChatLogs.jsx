import { useEffect, useState } from "react";
import AdminLayout from "./AdminLayout";
import { getChatLogs } from "../../services/api";

function ChatLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, pages: 0, total: 0, limit: 25 });

  const loadLogs = async ({ requestedPage = page, requestedSearch = search } = {}) => {
    try {
      setLoading(true);
      setError("");
      const res = await getChatLogs({ page: requestedPage, limit: 25, search: requestedSearch.trim() });
      const items = res.data?.items;
      const pageInfo = res.data?.pagination;

      if (Array.isArray(items)) {
        setLogs(items);
        setPagination(pageInfo || { page: 1, pages: 0, total: 0, limit: 25 });
        setPage(pageInfo?.page || requestedPage || 1);
      } else {
        setLogs([]);
        setPagination({ page: 1, pages: 0, total: 0, limit: 25 });
        setError("Unexpected chat logs response from server");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load chat logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs({ requestedPage: 1, requestedSearch: "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitSearch = (event) => {
    event.preventDefault();
    setPage(1);
    loadLogs({ requestedPage: 1, requestedSearch: search });
  };

  const resetSearch = () => {
    setSearch("");
    setPage(1);
    loadLogs({ requestedPage: 1, requestedSearch: "" });
  };

  const goPrev = () => {
    if (page > 1) {
      loadLogs({ requestedPage: page - 1, requestedSearch: search });
    }
  };

  const goNext = () => {
    if (pagination.pages > page) {
      loadLogs({ requestedPage: page + 1, requestedSearch: search });
    }
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Chat Logs</h2>
        <button className="admin-btn" onClick={() => loadLogs({ requestedPage: page, requestedSearch: search })}>Refresh</button>
      </div>

      <form className="admin-toolbar" onSubmit={submitSearch}>
        <input
          className="admin-input"
          placeholder="Search by user or message"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="admin-btn">Search</button>
        <button type="button" className="muted-btn" onClick={resetSearch}>Clear</button>
      </form>

      {loading && <p>Loading chat logs...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && logs.length === 0 && (
        <div className="empty-state">No chat logs found for your current filter.</div>
      )}

      {!loading && !error && logs.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Message</th>
                <th>Sentiment</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <tr key={`${log.timestamp || "no-ts"}-${i}`}>
                  <td>{log.user || "guest"}</td>
                  <td>{log.message || "-"}</td>
                  <td>{log.sentiment || "neutral"}</td>
                  <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && pagination.pages > 0 && (
        <div className="pager">
          <button className="muted-btn" onClick={goPrev} disabled={page <= 1}>Previous</button>
          <p>Page {page} of {Math.max(1, pagination.pages)} | {pagination.total} records</p>
          <button className="muted-btn" onClick={goNext} disabled={page >= pagination.pages}>Next</button>
        </div>
      )}
    </AdminLayout>
  );
}

export default ChatLogs;
