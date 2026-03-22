import { useEffect, useState } from "react";
import { getDashboardStats } from "../../services/api";
import AdminLayout from "./AdminLayout";

function Dashboard() {
  const [stats, setStats] = useState({
    total_chats: 0,
    users: 0,
    negative_sentiment: 0,
    top_questions: [],
    unmatched_questions: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getDashboardStats();
      setStats(res.data || {});
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load dashboard statistics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Dashboard</h2>
        <button className="admin-btn" onClick={fetchStats}>Refresh</button>
      </div>

      {loading && <p>Loading dashboard...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Chats</h3>
              <p>{stats.total_chats || 0}</p>
            </div>

            <div className="stat-card">
              <h3>Total Users</h3>
              <p>{stats.users || 0}</p>
            </div>

            <div className="stat-card">
              <h3>Negative Sentiment</h3>
              <p>{stats.negative_sentiment || 0}</p>
            </div>
          </div>

          <div className="dashboard-insights">
            <section className="insight-card">
              <h3>Most Frequent Questions</h3>
              {Array.isArray(stats.top_questions) && stats.top_questions.length > 0 ? (
                <div className="table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Question</th>
                        <th>Count</th>
                        <th>Last Seen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.top_questions.map((item, index) => (
                        <tr key={`top-${index}`}>
                          <td>{item.question || "-"}</td>
                          <td>{item.count || 0}</td>
                          <td>{item.last_seen ? new Date(item.last_seen).toLocaleString() : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">No frequent question data yet.</div>
              )}
            </section>

            <section className="insight-card">
              <h3>Unmatched Questions</h3>
              {Array.isArray(stats.unmatched_questions) && stats.unmatched_questions.length > 0 ? (
                <div className="table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Question</th>
                        <th>Count</th>
                        <th>Last Seen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.unmatched_questions.map((item, index) => (
                        <tr key={`unmatched-${index}`}>
                          <td>{item.question || "-"}</td>
                          <td>{item.count || 0}</td>
                          <td>{item.last_seen ? new Date(item.last_seen).toLocaleString() : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">No unmatched questions found.</div>
              )}
            </section>
          </div>
        </>
      )}
    </AdminLayout>
  );
}

export default Dashboard;
