import { useEffect, useMemo, useState } from "react";
import AdminLayout from "./AdminLayout";
import {
  getCounselingBookings,
  updateCounselingBookingStatus,
  getCounselingSlots,
  createCounselingSlot,
  deleteCounselingSlot,
} from "../../services/api";

function Counseling() {
  const [bookings, setBookings] = useState([]);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [updatingId, setUpdatingId] = useState("");

  const [bookingChanges, setBookingChanges] = useState({});

  const [slotForm, setSlotForm] = useState({
    date: "",
    start_time: "",
    end_time: "",
    counselor: "",
    mode: "in_person",
  });
  const [creatingSlot, setCreatingSlot] = useState(false);

  const activeSlotOptions = useMemo(
    () => slots.filter((slot) => slot.is_active !== false),
    [slots]
  );

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");
      const [bookingsRes, slotsRes] = await Promise.all([
        getCounselingBookings({ page: 1, limit: 30, search: search.trim(), status: statusFilter }),
        getCounselingSlots(),
      ]);

      const fetchedBookings = bookingsRes.data?.items || [];
      const fetchedSlots = slotsRes.data?.items || [];

      setBookings(fetchedBookings);
      setSlots(fetchedSlots);

      const nextChanges = {};
      fetchedBookings.forEach((booking) => {
        nextChanges[booking.id] = {
          status: booking.status || "pending",
          slot_id: booking.scheduled_slot_id || "",
        };
      });
      setBookingChanges(nextChanges);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load counseling data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateSlot = async (event) => {
    event.preventDefault();
    try {
      setCreatingSlot(true);
      setError("");
      await createCounselingSlot(slotForm);
      setSlotForm({ date: "", start_time: "", end_time: "", counselor: "", mode: "in_person" });
      await loadData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create slot");
    } finally {
      setCreatingSlot(false);
    }
  };

  const handleDeleteSlot = async (slotId) => {
    const yes = window.confirm("Deactivate this slot?");
    if (!yes) {
      return;
    }
    try {
      setError("");
      await deleteCounselingSlot(slotId);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to deactivate slot");
    }
  };

  const setBookingField = (bookingId, field, value) => {
    setBookingChanges((prev) => ({
      ...prev,
      [bookingId]: {
        ...(prev[bookingId] || {}),
        [field]: value,
      },
    }));
  };

  const handleBookingUpdate = async (bookingId) => {
    const change = bookingChanges[bookingId] || {};
    const payload = {
      status: change.status || "pending",
      slot_id: change.slot_id || "",
    };

    if (payload.status === "scheduled" && !payload.slot_id) {
      setError("Please select a slot before marking status as scheduled");
      return;
    }

    try {
      setUpdatingId(bookingId);
      setError("");
      await updateCounselingBookingStatus(bookingId, payload);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update booking status");
    } finally {
      setUpdatingId("");
    }
  };

  const runFilter = (event) => {
    event.preventDefault();
    loadData();
  };

  const getStatusClass = (status) => {
    const key = (status || "").toLowerCase();
    if (key === "scheduled") return "status-chip scheduled";
    if (key === "completed") return "status-chip completed";
    if (key === "rejected") return "status-chip rejected";
    if (key === "in_review") return "status-chip review";
    return "status-chip pending";
  };

  return (
    <AdminLayout>
      <div className="admin-page-head counseling-head">
        <h2>Counseling Management</h2>
        <button className="admin-btn" onClick={loadData}>Refresh</button>
      </div>

      <form className="intent-form" onSubmit={handleCreateSlot}>
        <h3>Create Counseling Slot</h3>
        <p className="form-note">
          Slot input format: Date `YYYY-MM-DD`, Time `HH:MM` (24-hour). End time must be after start time.
        </p>
        <div className="admin-toolbar">
          <input
            className="admin-input"
            type="date"
            title="Use date format YYYY-MM-DD"
            value={slotForm.date}
            onChange={(e) => setSlotForm((p) => ({ ...p, date: e.target.value }))}
            required
          />
          <input
            className="admin-input"
            type="time"
            title="Use 24-hour format HH:MM"
            value={slotForm.start_time}
            onChange={(e) => setSlotForm((p) => ({ ...p, start_time: e.target.value }))}
            required
          />
          <input
            className="admin-input"
            type="time"
            title="Use 24-hour format HH:MM"
            value={slotForm.end_time}
            onChange={(e) => setSlotForm((p) => ({ ...p, end_time: e.target.value }))}
            required
          />
          <input
            className="admin-input"
            placeholder="Counselor name"
            value={slotForm.counselor}
            onChange={(e) => setSlotForm((p) => ({ ...p, counselor: e.target.value }))}
          />
          <select
            className="admin-input"
            value={slotForm.mode}
            onChange={(e) => setSlotForm((p) => ({ ...p, mode: e.target.value }))}
          >
            <option value="in_person">In Person</option>
            <option value="online">Online</option>
          </select>
        </div>
        <button className="admin-btn" type="submit" disabled={creatingSlot}>
          {creatingSlot ? "Creating..." : "Create Slot"}
        </button>
      </form>

      <form className="admin-toolbar" onSubmit={runFilter}>
        <input
          className="admin-input"
          placeholder="Search student or message"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="admin-input"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_review">In Review</option>
          <option value="scheduled">Scheduled</option>
          <option value="completed">Completed</option>
          <option value="rejected">Rejected</option>
        </select>
        <button className="admin-btn" type="submit">Apply</button>
      </form>

      {loading && <p>Loading counseling records...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && (
        <section className="insight-card">
          <h3>Active Counseling Slots</h3>
          {slots.length === 0 ? (
            <div className="empty-state">No active slots yet.</div>
          ) : (
            <div className="table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Mode</th>
                    <th>Counselor</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {slots.map((slot) => (
                    <tr key={slot.id}>
                      <td>{slot.date || "-"}</td>
                      <td>{slot.start_time} - {slot.end_time}</td>
                      <td>{slot.mode || "in_person"}</td>
                      <td>{slot.counselor || "Counselor"}</td>
                      <td>
                        <button className="danger-btn" onClick={() => handleDeleteSlot(slot.id)}>Deactivate</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {!loading && !error && (
        <section className="insight-card">
          <h3>Counseling Requests</h3>
          {bookings.length === 0 ? (
            <div className="empty-state">No counseling requests found.</div>
          ) : (
            <div className="table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Message</th>
                    <th>Preferred Date</th>
                    <th>Status</th>
                    <th>Assign Slot</th>
                    <th>Save</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.map((booking) => {
                    const current = bookingChanges[booking.id] || { status: booking.status || "pending", slot_id: booking.scheduled_slot_id || "" };
                    const slotLabel = booking.scheduled_slot
                      ? `${booking.scheduled_slot.date} ${booking.scheduled_slot.start_time}-${booking.scheduled_slot.end_time}`
                      : "Not assigned";

                    return (
                      <tr key={booking.id}>
                        <td>{booking.student || "-"}</td>
                        <td>{booking.message || "-"}</td>
                        <td>{booking.preferred_date || "-"}</td>
                        <td className="status-cell">
                          <span className={getStatusClass(current.status)}>
                            {current.status.replace("_", " ")}
                          </span>
                          <select
                            className="admin-input"
                            value={current.status}
                            onChange={(e) => setBookingField(booking.id, "status", e.target.value)}
                            disabled={updatingId === booking.id}
                          >
                            <option value="pending">Pending</option>
                            <option value="in_review">In Review</option>
                            <option value="scheduled">Scheduled</option>
                            <option value="completed">Completed</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </td>
                        <td>
                          <select
                            className="admin-input"
                            value={current.slot_id || ""}
                            onChange={(e) => setBookingField(booking.id, "slot_id", e.target.value)}
                            disabled={updatingId === booking.id}
                          >
                            <option value="">{slotLabel}</option>
                            {activeSlotOptions.map((slot) => (
                              <option key={slot.id} value={slot.id}>
                                {slot.date} {slot.start_time}-{slot.end_time} ({slot.mode})
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <button
                            className="admin-btn"
                            onClick={() => handleBookingUpdate(booking.id)}
                            disabled={updatingId === booking.id}
                          >
                            {updatingId === booking.id ? "Saving..." : "Update"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </AdminLayout>
  );
}

export default Counseling;
