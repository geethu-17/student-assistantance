import { useEffect, useMemo, useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { getAnalytics } from "../../services/api";
import AdminLayout from "./AdminLayout";

ChartJS.register(ArcElement, Tooltip, Legend);

function Analytics() {
  const [stats, setStats] = useState({
    positive: 0,
    neutral: 0,
    negative: 0,
    total: 0,
    answered_count: 0,
    unanswered_count: 0,
    answered_percentage: 0,
    unanswered_percentage: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getAnalytics();
      const payload = res.data || {};

      setStats({
        positive: Number(payload.positive) || 0,
        neutral: Number(payload.neutral) || 0,
        negative: Number(payload.negative) || 0,
        total: Number(payload.total) || 0,
        answered_count: Number(payload.answered_count) || 0,
        unanswered_count: Number(payload.unanswered_count) || 0,
        answered_percentage: Number(payload.answered_percentage) || 0,
        unanswered_percentage: Number(payload.unanswered_percentage) || 0,
      });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  const sentimentData = useMemo(() => ({
    labels: ["Positive", "Neutral", "Negative"],
    datasets: [
      {
        data: [stats.positive, stats.neutral, stats.negative],
        backgroundColor: ["#16a34a", "#6b7280", "#dc2626"],
        borderWidth: 1,
      },
    ],
  }), [stats.positive, stats.neutral, stats.negative]);

  const efficiencyData = useMemo(() => ({
    labels: ["Answered", "Not Answered"],
    datasets: [
      {
        data: [stats.answered_count, stats.unanswered_count],
        backgroundColor: ["#2563eb", "#f97316"],
        borderWidth: 1,
      },
    ],
  }), [stats.answered_count, stats.unanswered_count]);

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Analytics Dashboard</h2>
        <button className="admin-btn" onClick={loadAnalytics}>Refresh</button>
      </div>

      {loading && <p>Loading analytics...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && stats.total === 0 && (
        <div className="empty-state">No chat analytics available yet.</div>
      )}

      {!loading && !error && stats.total > 0 && (
        <div className="analytics-layout">
          <div className="analytics-kpis">
            <div className="stat-card">
              <h3>Total Chats</h3>
              <p>{stats.total}</p>
            </div>
            <div className="stat-card">
              <h3>Answered</h3>
              <p>{stats.answered_count}</p>
            </div>
            <div className="stat-card">
              <h3>Not Answered</h3>
              <p>{stats.unanswered_count}</p>
            </div>
            <div className="stat-card">
              <h3>Success Rate</h3>
              <p>{stats.answered_percentage.toFixed(2)}%</p>
            </div>
          </div>

          <div className="analytics-panels">
            <section className="insight-card">
              <h3>Chatbot Efficiency</h3>
              <div className="chart-card modern-chart">
                <Doughnut data={efficiencyData} />
              </div>
              <div className="efficiency-bars">
                <div>
                  <div className="metric-head">
                    <span>Answered</span>
                    <strong>{stats.answered_percentage.toFixed(2)}%</strong>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill success" style={{ width: `${stats.answered_percentage}%` }} />
                  </div>
                </div>
                <div>
                  <div className="metric-head">
                    <span>Not Answered</span>
                    <strong>{stats.unanswered_percentage.toFixed(2)}%</strong>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill warn" style={{ width: `${stats.unanswered_percentage}%` }} />
                  </div>
                </div>
              </div>
            </section>

            <section className="insight-card">
              <h3>Sentiment Breakdown</h3>
              <div className="chart-card modern-chart">
                <Doughnut data={sentimentData} />
              </div>
              <div className="sentiment-legend">
                <p><span className="dot positive" />Positive: {stats.positive}</p>
                <p><span className="dot neutral" />Neutral: {stats.neutral}</p>
                <p><span className="dot negative" />Negative: {stats.negative}</p>
              </div>
            </section>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}

export default Analytics;
