import { useEffect, useMemo, useState } from "react";
import {
  getAcademicCalendar,
  getApplicationStatus,
  getCourseRegistrationGuidance,
  getCreditRequirements,
  getFeeInfo,
  getLoanAssistance,
  getPrograms,
  getScholarships,
  getStressResources,
  getStudentCounselingSlots,
  getTransportSchedules,
  submitCounselingRequest,
  getCounselingBookingStatus,
} from "../../services/api";
import "./Sidebar.css";

function Sidebar({
  newChat,
  onClose,
  onFunctionalModuleClick,
  onModuleResult,
  onModuleLoading,
  faqEnabled,
  chatSessions = [],
  activeChatId = null,
  onSelectChat,
  onDeleteChat,
}) {
  const [showBooking, setShowBooking] = useState(false);
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState("");

  const storedUser = useMemo(
    () => JSON.parse(localStorage.getItem("loggedInUser") || "null"),
    []
  );

  const [form, setForm] = useState({
    email: storedUser?.email || "",
    message: "",
    preferred_date: "",
    slot_id: "",
  });

  const [bookingInfo, setBookingInfo] = useState(null);
  const [bookingIdInput, setBookingIdInput] = useState("");
  const [statusInfo, setStatusInfo] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);
  const quickSupportItems = [
    "Application status",
    "Program information",
    "Eligibility check for B.Tech",
    "Course registration guidance",
    "Credit requirement queries",
    "Academic calendar",
    "Fee payment information",
    "Scholarship information",
    "Loan assistance information",
    "Transportation schedules",
    "Stress management resources",
  ];

  const setModuleText = (title, lines = []) => {
    onModuleResult?.({ title, lines: Array.isArray(lines) ? lines : [String(lines)] });
  };

  const handleModuleAction = async (item) => {
    onFunctionalModuleClick?.();
    onModuleLoading?.(true);
    setError("");
    onModuleResult?.(null);

    try {
      if (item === "Application status") {
        const registration = storedUser?.registration_number;
        if (!registration) {
          setModuleText("Application status", "No registration number found in your account profile.");
          return;
        }
        const res = await getApplicationStatus(registration);
        const data = res.data || {};
        setModuleText("Application status", [
          `Registration: ${data.registration_number || registration}`,
          `Status: ${data.status || "Not available"}`,
          `Application ID: ${data.application_id || "-"}`,
          `Program: ${data.program || "-"}`,
          `Last updated: ${data.last_updated || "-"}`,
        ]);
        return;
      }

      if (item === "Program information") {
        const res = await getPrograms();
        const rows = res.data?.items || [];
        setModuleText(
          "Program information",
          rows.slice(0, 5).map((row) => `${row.name} | ${row.degree || "-"} | Intake ${row.intake || "-"}`)
        );
        return;
      }

      if (item === "Eligibility check for B.Tech") {
        setModuleText("Eligibility check", [
          "Please provide your stream and marks.",
          "Example: stream MPC, marks 78",
        ]);
        return;
      }

      if (item === "Course registration guidance") {
        const res = await getCourseRegistrationGuidance();
        const row = (res.data?.items || [])[0];
        if (!row) {
          setModuleText("Course registration guidance", "No records available.");
          return;
        }
        setModuleText("Course registration guidance", [
          row.title || "Guidance",
          `Steps: ${(row.steps || []).join(" -> ") || "-"}`,
          `Documents: ${(row.required_documents || []).join(", ") || "-"}`,
          `Contacts: ${(row.contacts || []).join(", ") || "-"}`,
        ]);
        return;
      }

      if (item === "Credit requirement queries") {
        const res = await getCreditRequirements();
        const rows = res.data?.items || [];
        setModuleText(
          "Credit requirement queries",
          rows.slice(0, 5).map((row) => `${row.program} Sem ${row.semester}: ${row.required_credits} credits`)
        );
        return;
      }

      if (item === "Academic calendar") {
        const res = await getAcademicCalendar();
        const rows = Array.isArray(res.data) ? res.data : res.data?.items || [];
        setModuleText(
          "Academic calendar",
          rows.slice(0, 5).map((row) => `${row.date || "-"}: ${row.event || "-"}`)
        );
        return;
      }

      if (item === "Fee payment information") {
        const res = await getFeeInfo();
        const rows = res.data?.items || [];
        setModuleText(
          "Fee payment information",
          rows.slice(0, 5).map((row) => `${row.program}: Tuition ${row.tuition_fee} ${row.currency || "INR"}`)
        );
        return;
      }

      if (item === "Scholarship information") {
        const res = await getScholarships();
        const rows = res.data?.items || [];
        setModuleText(
          "Scholarship information",
          rows.slice(0, 5).map((row) => `${row.name}: ${row.benefit || "-"}`)
        );
        return;
      }

      if (item === "Loan assistance information") {
        const res = await getLoanAssistance();
        const row = (res.data?.items || [])[0];
        if (!row) {
          setModuleText("Loan assistance information", "No records available.");
          return;
        }
        setModuleText("Loan assistance information", [
          row.title || "Loan assistance",
          row.description || "-",
          `Contact: ${row.contact || "-"}`,
          `Documents: ${(row.required_documents || []).join(", ") || "-"}`,
        ]);
        return;
      }

      if (item === "Transportation schedules") {
        const res = await getTransportSchedules();
        const rows = res.data?.items || [];
        setModuleText(
          "Transportation schedules",
          rows.slice(0, 5).map((row) => `${row.route_name} | ${row.departure_time}-${row.arrival_time} | Bus ${row.bus_no}`)
        );
        return;
      }

      if (item === "Stress management resources") {
        const res = await getStressResources();
        const rows = res.data?.items || [];
        setModuleText(
          "Stress management resources",
          rows.slice(0, 5).map((row) => `${row.title}: ${row.description}`)
        );
      }
    } catch (err) {
      const message = err.response?.data?.error || "Failed to fetch module response";
      setError(message);
      setModuleText(item, [message]);
    } finally {
      onModuleLoading?.(false);
    }
  };

  const loadSlots = async () => {
    try {
      setLoadingSlots(true);
      setError("");
      const res = await getStudentCounselingSlots();
      setSlots(res.data?.items || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load counseling slots");
    } finally {
      setLoadingSlots(false);
    }
  };

  useEffect(() => {
    if (showBooking) {
      loadSlots();
    }
  }, [showBooking]);

  const submitBooking = async (event) => {
    event.preventDefault();
    if (!form.email || !form.message) {
      setError("Email and message are required");
      return;
    }

    try {
      setBookingLoading(true);
      setError("");
      setBookingInfo(null);
      const payload = {
        email: form.email,
        message: form.message,
        preferred_date: form.preferred_date,
        slot_id: form.slot_id,
      };
      const res = await submitCounselingRequest(payload);
      setBookingInfo(res.data || null);
      if (res.data?.booking_id) {
        setBookingIdInput(res.data.booking_id);
      }
      setForm((prev) => ({ ...prev, message: "", preferred_date: "", slot_id: "" }));
    } catch (err) {
      setError(err.response?.data?.error || "Failed to submit counseling request");
    } finally {
      setBookingLoading(false);
    }
  };

  const checkStatus = async () => {
    if (!bookingIdInput.trim()) {
      setError("Enter booking id to check status");
      return;
    }

    try {
      setStatusLoading(true);
      setError("");
      const res = await getCounselingBookingStatus(bookingIdInput.trim());
      setStatusInfo(res.data || null);
    } catch (err) {
      setStatusInfo(null);
      setError(err.response?.data?.error || "Failed to fetch booking status");
    } finally {
      setStatusLoading(false);
    }
  };

  return (
    <div className="sidebar">
      <button className="sidebar-close" onClick={onClose} type="button">Close</button>

      {faqEnabled ? (
        <>
          <button className="new-chat" onClick={newChat}>
            + New Chat
          </button>

          <div className="session-history">
            <h4>Chats</h4>
            {chatSessions.length === 0 && <p className="side-note">No chats yet.</p>}
            {chatSessions.map((session) => (
              <div key={session.id} className={`session-item ${activeChatId === session.id ? "active" : ""}`}>
                <button
                  type="button"
                  className="session-open"
                  onClick={() => onSelectChat?.(session.id)}
                >
                  {session.title || "New Chat"}
                </button>
                <div className="session-actions">
                  <button
                    type="button"
                    className="session-menu"
                    onClick={() => setOpenMenuId((prev) => (prev === session.id ? null : session.id))}
                    aria-label="Chat actions"
                    title="Chat actions"
                  >
                    ...
                  </button>
                  {openMenuId === session.id && (
                    <button
                      type="button"
                      className="session-delete"
                      onClick={() => {
                        onDeleteChat?.(session.id);
                        setOpenMenuId(null);
                      }}
                      aria-label="Delete chat"
                      title="Delete chat"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <button className="booking-btn" onClick={() => setShowBooking((prev) => !prev)}>
            {showBooking ? "Hide Booking" : "Counseling Booking"}
          </button>

          <div className="chat-history">
            <h4>Quick Support</h4>
            {quickSupportItems.map((item) => (
              <button
                key={item}
                className="quick-item"
                onClick={() => handleModuleAction(item)}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>

          {showBooking && (
            <div className="booking-panel">
              <h4>Request Counseling</h4>

              {loadingSlots && <p className="side-note">Loading slots...</p>}
              {error && <p className="side-error">{error}</p>}

              <form className="booking-form" onSubmit={submitBooking}>
                <input
                  type="email"
                  placeholder="Email"
                  value={form.email}
                  onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                  required
                />
                <textarea
                  rows={3}
                  placeholder="Tell your concern briefly"
                  value={form.message}
                  onChange={(e) => setForm((p) => ({ ...p, message: e.target.value }))}
                  required
                />
                <input
                  type="date"
                  value={form.preferred_date}
                  onChange={(e) => setForm((p) => ({ ...p, preferred_date: e.target.value }))}
                />
                <select
                  value={form.slot_id}
                  onChange={(e) => setForm((p) => ({ ...p, slot_id: e.target.value }))}
                >
                  <option value="">Select slot (optional)</option>
                  {slots.map((slot) => (
                    <option key={slot.id} value={slot.id}>
                      {slot.date} {slot.start_time}-{slot.end_time} ({slot.counselor || "Counselor"})
                    </option>
                  ))}
                </select>

                <button type="submit" disabled={bookingLoading}>
                  {bookingLoading ? "Submitting..." : "Book Counseling"}
                </button>
              </form>

              {bookingInfo?.booking_id && (
                <div className="side-card success">
                  <p><strong>Booking ID:</strong> {bookingInfo.booking_id}</p>
                  <p><strong>Status:</strong> {bookingInfo.status || "pending"}</p>
                </div>
              )}

              <h4>Check Booking Status</h4>
              <div className="status-checker">
                <input
                  placeholder="Enter booking ID"
                  value={bookingIdInput}
                  onChange={(e) => setBookingIdInput(e.target.value)}
                />
                <button type="button" onClick={checkStatus} disabled={statusLoading}>
                  {statusLoading ? "Checking..." : "Check"}
                </button>
              </div>

              {statusInfo && (
                <div className="side-card">
                  <p><strong>Status:</strong> {statusInfo.status || "pending"}</p>
                  {statusInfo.scheduled_slot ? (
                    <>
                      <p>
                        <strong>Schedule:</strong> {statusInfo.scheduled_slot.date} {statusInfo.scheduled_slot.start_time}-{statusInfo.scheduled_slot.end_time}
                      </p>
                      <p><strong>Counselor:</strong> {statusInfo.scheduled_slot.counselor || "Counselor"}</p>
                    </>
                  ) : (
                    <p className="side-note">Not scheduled yet.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Sidebar;

