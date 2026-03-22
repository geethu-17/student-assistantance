import { useEffect, useState } from "react";
import AdminLayout from "./AdminLayout";
import { getIntegrationsStatus, sendSmtpTestEmail } from "../../services/api";

function StatusRow({ label, enabled, maskedValue }) {
  return (
    <div className="integration-row">
      <p>{label}</p>
      <p>
        <span className={`status-chip ${enabled ? "completed" : "rejected"}`}>
          {enabled ? "Configured" : "Missing"}
        </span>
        <span className="integration-mask">{maskedValue || "-"}</span>
      </p>
    </div>
  );
}

function IntegrationCard({ title, data }) {
  const fields = data?.fields || {};
  const masked = data?.masked || {};
  const keys = Object.keys(fields);

  return (
    <section className="insight-card integration-card">
      <div className="admin-page-head compact">
        <h3>{title}</h3>
        <span className={`status-chip ${data?.ready ? "completed" : "pending"}`}>
          {data?.ready ? "Ready" : "Needs Setup"}
        </span>
      </div>

      {keys.length === 0 && <div className="empty-state">No integration metadata available.</div>}

      {keys.map((key) => (
        <StatusRow key={key} label={key} enabled={Boolean(fields[key])} maskedValue={masked[key]} />
      ))}
    </section>
  );
}

function Integrations() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testEmail, setTestEmail] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testMessage, setTestMessage] = useState("");
  const [testError, setTestError] = useState("");

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getIntegrationsStatus();
      setData(res.data || {});
    } catch (err) {
      setData(null);
      setError(err.response?.data?.error || "Failed to load integrations status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSendTestEmail = async () => {
    if (!testEmail.trim()) {
      setTestError("Enter recipient email first");
      setTestMessage("");
      return;
    }

    try {
      setTestLoading(true);
      setTestError("");
      setTestMessage("");
      const res = await sendSmtpTestEmail(testEmail.trim());
      setTestMessage(res.data?.message || "SMTP test email sent");
    } catch (err) {
      setTestError(err.response?.data?.details || err.response?.data?.error || "Failed to send SMTP test email");
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Integrations</h2>
        <button className="admin-btn" onClick={loadStatus}>Refresh</button>
      </div>

      <p className="form-note">
        Check token readiness for WhatsApp, Instagram, Telegram, and SMTP. Values are masked for security.
      </p>

      {loading && <p>Loading integration status...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && (
        <>
          <div className="analytics-panels">
            <IntegrationCard title="WhatsApp" data={data?.whatsapp} />
            <IntegrationCard title="Instagram" data={data?.instagram} />
            <IntegrationCard title="Telegram" data={data?.telegram} />
            <IntegrationCard title="SMTP Email" data={data?.smtp} />
          </div>

          <section className="insight-card integration-card">
            <div className="admin-page-head compact">
              <h3>SMTP Test Email</h3>
            </div>

            <div className="admin-toolbar">
              <input
                className="admin-input"
                placeholder="Recipient email"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
              />
              <button className="admin-btn" onClick={handleSendTestEmail} disabled={testLoading}>
                {testLoading ? "Sending..." : "Send Test Email"}
              </button>
            </div>

            {testMessage && <p className="form-note">{testMessage}</p>}
            {testError && <p className="error">{testError}</p>}
          </section>
        </>
      )}
    </AdminLayout>
  );
}

export default Integrations;
