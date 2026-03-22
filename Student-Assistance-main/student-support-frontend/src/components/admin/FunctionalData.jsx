import { useEffect, useMemo, useState } from "react";
import AdminLayout from "./AdminLayout";
import {
  createModuleData,
  deleteModuleData,
  exportModuleData,
  getModuleData,
  importModuleData,
  updateModuleData,
} from "../../services/api";

const MODULE_CONFIG = {
  applications: {
    label: "Applications",
    fields: ["registration_number", "email", "application_id", "program", "status", "last_updated"],
    required: ["registration_number", "application_id", "status"],
  },
  programs: {
    label: "Programs",
    fields: ["name", "degree", "department", "duration_years", "intake", "eligibility_summary"],
    required: ["name", "degree", "duration_years", "intake"],
  },
  course_registration_guidance: {
    label: "Course Registration",
    fields: ["title", "steps", "required_documents", "contacts"],
    required: ["title", "steps"],
  },
  academic_calendar: {
    label: "Academic Calendar",
    fields: ["event", "date"],
    required: ["event", "date"],
  },
  credit_requirements: {
    label: "Credit Requirements",
    fields: ["program", "semester", "required_credits", "notes"],
    required: ["program", "semester", "required_credits"],
  },
  student_credits: {
    label: "Student Credits",
    fields: ["registration_number", "program", "semester", "earned_credits"],
    required: ["registration_number", "program", "semester", "earned_credits"],
  },
  fee_structure: {
    label: "Fee Structure",
    fields: ["program", "tuition_fee", "hostel_fee", "other_charges", "currency"],
    required: ["program", "tuition_fee", "currency"],
  },
  scholarships: {
    label: "Scholarships",
    fields: ["name", "criteria", "benefit", "deadline", "link"],
    required: ["name", "criteria", "benefit"],
  },
  loan_assistance: {
    label: "Loan Assistance",
    fields: ["title", "description", "required_documents", "contact", "link"],
    required: ["title", "description"],
  },
  hostel_info: {
    label: "Hostel Info",
    fields: ["hostel_name", "type", "capacity", "fee_per_year", "facilities"],
    required: ["hostel_name", "type", "capacity"],
  },
  transport_schedules: {
    label: "Transport",
    fields: ["route_name", "pickup_points", "departure_time", "arrival_time", "bus_no"],
    required: ["route_name", "departure_time", "arrival_time", "bus_no"],
  },
  campus_navigation: {
    label: "Campus Navigation",
    fields: ["from", "to", "route_steps", "approx_minutes"],
    required: ["from", "to", "route_steps"],
  },
  stress_resources: {
    label: "Stress Resources",
    fields: ["title", "description", "type", "link", "contact"],
    required: ["title", "description", "type"],
  },
};

const ARRAY_FIELDS = new Set(["steps", "required_documents", "contacts", "pickup_points", "route_steps", "facilities"]);
const NUMBER_FIELDS = new Set([
  "duration_years",
  "intake",
  "required_credits",
  "earned_credits",
  "tuition_fee",
  "hostel_fee",
  "other_charges",
  "capacity",
  "fee_per_year",
  "approx_minutes",
  "semester",
]);
const TEXTAREA_FIELDS = new Set(["eligibility_summary", "description", "criteria", "benefit", "notes"]);
const DATE_FIELDS = new Set(["date", "deadline", "last_updated"]);
const TIME_FIELDS = new Set(["departure_time", "arrival_time"]);
const URL_FIELDS = new Set(["link"]);
const EMAIL_FIELDS = new Set(["email", "contact"]);
const STATUS_OPTIONS = ["Submitted", "Under Review", "Documents Verified", "Accepted", "Rejected", "Payment Pending"];
const MODULE_HELP = {
  applications: "Track student-level application progress for chatbot status responses.",
  programs: "Keep official program catalog updated for admission guidance.",
  course_registration_guidance: "Provide step-by-step course enrollment help.",
  academic_calendar: "Maintain important dates shown in academic support responses.",
  credit_requirements: "Program-wise required credits for graduation checks.",
  student_credits: "Student earned credits used for progress and deficit checks.",
  fee_structure: "Program fee details used in financial assistance answers.",
  scholarships: "Scholarship catalog with criteria and deadlines.",
  loan_assistance: "Loan process and contacts for financial support.",
  hostel_info: "Hostel facilities and fee data for campus support.",
  transport_schedules: "Route and timing details for transport support.",
  campus_navigation: "Directional routes and travel time on campus.",
  stress_resources: "Mental wellness resources available to students.",
};
const FIELD_SPEC = {
  registration_number: "Example: REG2026-0001",
  application_id: "Example: APP2026-0012",
  email: "Valid email format required",
  date: "YYYY-MM-DD",
  deadline: "YYYY-MM-DD",
  last_updated: "YYYY-MM-DD",
  departure_time: "24-hour format HH:MM",
  arrival_time: "24-hour format HH:MM",
  semester: "Numeric value (example: 1, 2, 3)",
  link: "Must start with http:// or https://",
};

function fieldToLabel(field) {
  return field.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isEmailLike(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function isDateLike(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function isTimeLike(value) {
  return /^([01]\d|2[0-3]):([0-5]\d)$/.test(value);
}

function normalizeForSubmit(field, value) {
  const raw = (value ?? "").toString().trim();
  if (!raw) return "";
  if (ARRAY_FIELDS.has(field)) {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (NUMBER_FIELDS.has(field)) {
    const asNumber = Number(raw);
    return Number.isNaN(asNumber) ? raw : asNumber;
  }
  return raw;
}

function getFieldSpec(field) {
  if (ARRAY_FIELDS.has(field)) return "Multiple values: comma separated";
  return FIELD_SPEC[field] || "";
}

function FunctionalData() {
  const moduleKeys = useMemo(() => Object.keys(MODULE_CONFIG), []);
  const [moduleKey, setModuleKey] = useState(moduleKeys[0]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState("");
  const [importing, setImporting] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState({});

  const config = MODULE_CONFIG[moduleKey];
  const fields = config.fields;
  const required = new Set(config.required || []);

  const buildEmptyForm = () => {
    const next = {};
    fields.forEach((field) => {
      next[field] = "";
    });
    return next;
  };

  const loadData = async (requestedSearch = search) => {
    try {
      setLoading(true);
      setError("");
      const res = await getModuleData(moduleKey, { page: 1, limit: 200, search: requestedSearch.trim() });
      setRows(res.data?.items || []);
    } catch (err) {
      setRows([]);
      setError(err.response?.data?.error || "Failed to load module data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setForm(buildEmptyForm());
    setEditingId("");
    loadData("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleKey]);

  const validateForm = () => {
    for (const field of fields) {
      const value = (form[field] ?? "").toString().trim();
      if (required.has(field) && !value) {
        return `${fieldToLabel(field)} is required`;
      }
      if (!value) continue;

      if (DATE_FIELDS.has(field) && !isDateLike(value)) {
        return `${fieldToLabel(field)} must be in YYYY-MM-DD format`;
      }
      if (TIME_FIELDS.has(field) && !isTimeLike(value)) {
        return `${fieldToLabel(field)} must be in HH:MM 24-hour format`;
      }
      if (EMAIL_FIELDS.has(field) && field === "email" && !isEmailLike(value)) {
        return "Email format is invalid";
      }
      if (URL_FIELDS.has(field)) {
        const ok = value.startsWith("http://") || value.startsWith("https://");
        if (!ok) {
          return `${fieldToLabel(field)} must start with http:// or https://`;
        }
      }
      if (NUMBER_FIELDS.has(field)) {
        const n = Number(value);
        if (Number.isNaN(n)) {
          return `${fieldToLabel(field)} must be a valid number`;
        }
        if (n < 0) {
          return `${fieldToLabel(field)} cannot be negative`;
        }
      }
    }

    if (moduleKey === "transport_schedules") {
      const start = (form.departure_time || "").trim();
      const end = (form.arrival_time || "").trim();
      if (start && end && isTimeLike(start) && isTimeLike(end) && start >= end) {
        return "Arrival Time must be later than Departure Time";
      }
    }

    if (moduleKey === "applications") {
      const reg = (form.registration_number || "").trim();
      const appId = (form.application_id || "").trim();
      if (reg && !/^[A-Za-z0-9-]{5,30}$/.test(reg)) {
        return "Registration Number should be 5-30 chars using letters, numbers or '-'";
      }
      if (appId && !/^[A-Za-z0-9-]{5,30}$/.test(appId)) {
        return "Application ID should be 5-30 chars using letters, numbers or '-'";
      }
    }

    return "";
  };

  const onSubmit = async (event) => {
    event.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = {};
    fields.forEach((field) => {
      const normalized = normalizeForSubmit(field, form[field]);
      if (normalized !== "") {
        payload[field] = normalized;
      }
    });

    if (Object.keys(payload).length === 0) {
      setError("Please enter at least one field");
      return;
    }

    try {
      setSaving(true);
      setError("");
      if (editingId) {
        await updateModuleData(moduleKey, editingId, payload);
      } else {
        await createModuleData(moduleKey, payload);
      }
      setForm(buildEmptyForm());
      setEditingId("");
      await loadData(search);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to save record");
    } finally {
      setSaving(false);
    }
  };

  const onEdit = (row) => {
    const next = buildEmptyForm();
    fields.forEach((field) => {
      const value = row[field];
      next[field] = Array.isArray(value) ? value.join(", ") : value ?? "";
    });
    setForm(next);
    setEditingId(row.id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const onDelete = async (row) => {
    if (!window.confirm("Delete this record?")) return;
    try {
      await deleteModuleData(moduleKey, row.id);
      await loadData(search);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to delete record");
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

  const downloadTemplate = () => {
    const headerRow = fields.join(",");
    const sampleRow = fields
      .map((field) => {
        if (required.has(field)) {
          const spec = getFieldSpec(field);
          return `"${spec || `sample_${field}`}"`;
        }
        return '""';
      })
      .join(",");
    const blob = new Blob([`${headerRow}\n${sampleRow}\n`], { type: "text/csv;charset=utf-8;" });
    const stamp = new Date().toISOString().slice(0, 10);
    downloadBlob(blob, `${moduleKey}_template_${stamp}.csv`);
  };

  const onExport = async (format) => {
    try {
      setExporting(format);
      setError("");
      const res = await exportModuleData(moduleKey, {
        format,
        search: search.trim(),
      });
      const stamp = new Date().toISOString().slice(0, 19).replaceAll(":", "").replaceAll("-", "").replace("T", "_");
      const defaultName = `${moduleKey}_${stamp}.${format}`;
      downloadBlob(res.data, defaultName);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to export data");
    } finally {
      setExporting("");
    }
  };

  const onImport = async () => {
    if (!selectedFile) {
      setError("Choose a CSV or JSON file first");
      return;
    }
    try {
      setImporting(true);
      setError("");
      await importModuleData(moduleKey, selectedFile);
      setSelectedFile(null);
      await loadData(search);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to import file");
    } finally {
      setImporting(false);
    }
  };

  const renderField = (field) => {
    const value = form[field] ?? "";
    const requiredMark = required.has(field) ? " *" : "";
    const commonProps = {
      className: "admin-input",
      value,
      onChange: (e) => setForm((prev) => ({ ...prev, [field]: e.target.value })),
      placeholder: `${fieldToLabel(field)}${requiredMark}`,
    };

    if (moduleKey === "applications" && field === "status") {
      return (
        <select key={field} className="admin-input" value={value} onChange={commonProps.onChange}>
          <option value="">Select Status{requiredMark}</option>
          {STATUS_OPTIONS.map((option) => (
            <option value={option} key={option}>{option}</option>
          ))}
        </select>
      );
    }
    if (TEXTAREA_FIELDS.has(field) || ARRAY_FIELDS.has(field)) {
      return (
        <div key={field}>
          <textarea
            className="admin-textarea"
            rows={ARRAY_FIELDS.has(field) ? 2 : 3}
            value={value}
            onChange={commonProps.onChange}
            placeholder={`${fieldToLabel(field)}${requiredMark}${ARRAY_FIELDS.has(field) ? " (comma separated)" : ""}`}
          />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    if (DATE_FIELDS.has(field)) {
      return (
        <div key={field}>
          <input type="date" {...commonProps} />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    if (TIME_FIELDS.has(field)) {
      return (
        <div key={field}>
          <input type="time" {...commonProps} />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    if (NUMBER_FIELDS.has(field)) {
      return (
        <div key={field}>
          <input type="number" min="0" step="any" {...commonProps} />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    if (URL_FIELDS.has(field)) {
      return (
        <div key={field}>
          <input type="url" {...commonProps} placeholder={`${fieldToLabel(field)}${requiredMark} (https://...)`} />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    if (field === "email") {
      return (
        <div key={field}>
          <input type="email" {...commonProps} />
          <p className="form-note">{getFieldSpec(field) || " "}</p>
        </div>
      );
    }
    return (
      <div key={field}>
        <input type="text" {...commonProps} />
        <p className="form-note">{getFieldSpec(field) || " "}</p>
      </div>
    );
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Functional Data Manager</h2>
        <div className="row-actions">
          <input
            type="file"
            accept=".csv,.json,application/json,text/csv"
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
          />
          <button className="admin-btn" onClick={onImport} disabled={importing}>
            {importing ? "Importing..." : "Import File"}
          </button>
          <button className="muted-btn" type="button" onClick={downloadTemplate}>
            Download Template
          </button>
          <button className="muted-btn" onClick={() => onExport("csv")} disabled={exporting === "csv"}>
            {exporting === "csv" ? "Exporting CSV..." : "Export CSV"}
          </button>
          <button className="muted-btn" onClick={() => onExport("json")} disabled={exporting === "json"}>
            {exporting === "json" ? "Exporting JSON..." : "Export JSON"}
          </button>
          <button className="admin-btn" onClick={() => loadData(search)}>Refresh</button>
        </div>
      </div>

      <form className="intent-form" onSubmit={onSubmit}>
        <h3>{editingId ? "Edit Record" : "Add Record"}</h3>
        <p className="form-note">Fields marked with `*` are required for this module.</p>
        <p className="form-note">{MODULE_HELP[moduleKey]}</p>

        <select
          className="admin-input"
          value={moduleKey}
          onChange={(e) => setModuleKey(e.target.value)}
          disabled={saving}
        >
          {moduleKeys.map((key) => (
            <option value={key} key={key}>
              {MODULE_CONFIG[key].label}
            </option>
          ))}
        </select>

        {fields.map((field) => renderField(field))}

        <div className="form-actions">
          <button className="admin-btn" type="submit" disabled={saving}>
            {saving ? "Saving..." : editingId ? "Update Record" : "Add Record"}
          </button>
          <button
            className="muted-btn"
            type="button"
            onClick={() => {
              setEditingId("");
              setForm(buildEmptyForm());
            }}
          >
            Clear
          </button>
        </div>
      </form>

      <form
        className="admin-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          loadData(search);
        }}
      >
        <input
          className="admin-input"
          placeholder="Search records"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="admin-btn" type="submit">
          Search
        </button>
        <button
          className="muted-btn"
          type="button"
          onClick={() => {
            setSearch("");
            loadData("");
          }}
        >
          Clear
        </button>
      </form>

      {loading && <p>Loading records...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && rows.length === 0 && <div className="empty-state">No records found.</div>}

      {!loading && rows.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                {fields.slice(0, 4).map((field) => (
                  <th key={field}>{fieldToLabel(field)}</th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {fields.slice(0, 4).map((field) => {
                    const value = row[field];
                    const text = Array.isArray(value) ? value.join(", ") : value ?? "-";
                    return <td key={`${row.id}-${field}`}>{String(text)}</td>;
                  })}
                  <td>
                    <div className="row-actions">
                      <button className="admin-btn" onClick={() => onEdit(row)}>
                        Edit
                      </button>
                      <button className="danger-btn" onClick={() => onDelete(row)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdminLayout>
  );
}

export default FunctionalData;
