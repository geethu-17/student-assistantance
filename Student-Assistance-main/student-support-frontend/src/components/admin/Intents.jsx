import { useEffect, useMemo, useState } from "react";
import AdminLayout from "./AdminLayout";
import {
  getIntents,
  deleteIntent,
  addIntent,
  updateIntent,
  getFaqSuggestions,
  createIntentFromSuggestion,
  exportIntents,
  importIntents,
} from "../../services/api";

function toLines(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function Intents() {
  const [intents, setIntents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, pages: 0, total: 0, limit: 20 });

  const [tag, setTag] = useState("");
  const [patternsText, setPatternsText] = useState("");
  const [responsesText, setResponsesText] = useState("");
  const [saving, setSaving] = useState(false);

  const [editingTag, setEditingTag] = useState("");
  const [faqSuggestions, setFaqSuggestions] = useState([]);
  const [faqLoading, setFaqLoading] = useState(false);
  const [faqError, setFaqError] = useState("");
  const [creatingSuggestionKey, setCreatingSuggestionKey] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState("");

  const isEditing = useMemo(() => Boolean(editingTag), [editingTag]);

  const loadIntents = async ({ requestedPage = page, requestedSearch = search } = {}) => {
    try {
      setLoading(true);
      setError("");
      const res = await getIntents({ page: requestedPage, limit: 20, search: requestedSearch.trim() });
      const items = res.data?.items;
      const pageInfo = res.data?.pagination;

      if (Array.isArray(items)) {
        setIntents(items);
        setPagination(pageInfo || { page: 1, pages: 0, total: 0, limit: 20 });
        setPage(pageInfo?.page || requestedPage || 1);
      } else {
        setIntents([]);
        setPagination({ page: 1, pages: 0, total: 0, limit: 20 });
        setError("Unexpected intents response from server");
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load intents");
    } finally {
      setLoading(false);
    }
  };

  const loadFaqSuggestions = async () => {
    try {
      setFaqLoading(true);
      setFaqError("");
      const res = await getFaqSuggestions({ limit: 12, min_count: 2 });
      const items = res.data?.items;
      if (Array.isArray(items)) {
        setFaqSuggestions(items);
      } else {
        setFaqSuggestions([]);
        setFaqError("Unexpected FAQ suggestions response");
      }
    } catch (err) {
      setFaqError(err.response?.data?.error || "Failed to load FAQ suggestions");
    } finally {
      setFaqLoading(false);
    }
  };

  useEffect(() => {
    loadIntents({ requestedPage: 1, requestedSearch: "" });
    loadFaqSuggestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearForm = () => {
    setTag("");
    setPatternsText("");
    setResponsesText("");
    setEditingTag("");
  };

  const onEdit = (intent) => {
    setEditingTag(intent.tag);
    setTag(intent.tag || "");
    setPatternsText((intent.patterns || []).join("\n"));
    setResponsesText((intent.responses || []).join("\n"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const applySuggestionAsDraft = (suggestion) => {
    setEditingTag("");
    setTag(suggestion.suggested_tag || "");
    setPatternsText((suggestion.suggested_patterns || [suggestion.question || ""]).join("\n"));
    setResponsesText((suggestion.suggested_responses || []).join("\n"));
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const createFromSuggestion = async (suggestion) => {
    const key = suggestion.normalized_question || suggestion.question || "";
    if (!key) {
      return;
    }

    const isConfirmed = window.confirm("Create new intent from this suggestion now?");
    if (!isConfirmed) {
      return;
    }

    try {
      setCreatingSuggestionKey(key);
      setError("");
      await createIntentFromSuggestion({
        question: suggestion.question,
        normalized_question: suggestion.normalized_question,
        suggested_tag: suggestion.suggested_tag,
        suggested_patterns: suggestion.suggested_patterns,
        suggested_responses: suggestion.suggested_responses,
      });
      await Promise.all([
        loadIntents({ requestedPage: 1, requestedSearch: search }),
        loadFaqSuggestions(),
      ]);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create intent from suggestion");
    } finally {
      setCreatingSuggestionKey("");
    }
  };

  const onDelete = async (targetTag) => {
    const isConfirmed = window.confirm(`Delete intent '${targetTag}'? This action cannot be undone.`);
    if (!isConfirmed) {
      return;
    }

    try {
      await deleteIntent(targetTag);
      if (isEditing && editingTag === targetTag) {
        clearForm();
      }
      await loadIntents({ requestedPage: page, requestedSearch: search });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to delete intent");
    }
  };

  const onSubmit = async (event) => {
    event.preventDefault();

    const cleanTag = tag.trim();
    const patterns = toLines(patternsText);
    const responses = toLines(responsesText);

    if (!cleanTag) {
      setError("Intent tag is required");
      return;
    }

    if (patterns.length === 0) {
      setError("Add at least one pattern (one per line)");
      return;
    }

    if (responses.length === 0) {
      setError("Add at least one response (one per line)");
      return;
    }

    try {
      setSaving(true);
      setError("");
      if (isEditing) {
        await updateIntent(editingTag, {
          tag: cleanTag,
          patterns,
          responses,
        });
      } else {
        await addIntent({
          tag: cleanTag,
          patterns,
          responses,
        });
      }

      clearForm();
      await loadIntents({ requestedPage: 1, requestedSearch: search });
    } catch (err) {
      setError(err.response?.data?.error || (isEditing ? "Failed to update intent" : "Failed to add intent"));
    } finally {
      setSaving(false);
    }
  };

  const submitSearch = (event) => {
    event.preventDefault();
    setPage(1);
    loadIntents({ requestedPage: 1, requestedSearch: search });
  };

  const resetSearch = () => {
    setSearch("");
    setPage(1);
    loadIntents({ requestedPage: 1, requestedSearch: "" });
  };

  const goPrev = () => {
    if (page > 1) {
      loadIntents({ requestedPage: page - 1, requestedSearch: search });
    }
  };

  const goNext = () => {
    if (pagination.pages > page) {
      loadIntents({ requestedPage: page + 1, requestedSearch: search });
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
      const res = await exportIntents({ format, search: search.trim() });
      downloadBlob(res.data, `intents_export.${format}`);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to export intents");
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
      await importIntents(selectedFile);
      setSelectedFile(null);
      await loadIntents({ requestedPage: 1, requestedSearch: search });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to import intents");
    } finally {
      setImporting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="admin-page-head">
        <h2>Intent Manager</h2>
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
          <button className="admin-btn" onClick={() => loadIntents({ requestedPage: page, requestedSearch: search })}>Refresh</button>
        </div>
      </div>

      <form className="intent-form" onSubmit={onSubmit}>
        <h3>{isEditing ? `Edit Intent: ${editingTag}` : "Add New Intent"}</h3>

        <input
          className="admin-input"
          placeholder="Intent tag"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
        />

        <textarea
          className="admin-textarea"
          rows={5}
          placeholder="Patterns (one per line)"
          value={patternsText}
          onChange={(e) => setPatternsText(e.target.value)}
        />

        <textarea
          className="admin-textarea"
          rows={5}
          placeholder="Responses (one per line)"
          value={responsesText}
          onChange={(e) => setResponsesText(e.target.value)}
        />

        <div className="form-actions">
          <button className="admin-btn" type="submit" disabled={saving}>
            {saving ? "Saving..." : isEditing ? "Update Intent" : "Add Intent"}
          </button>
          <button className="muted-btn" type="button" onClick={clearForm} disabled={saving}>
            Clear
          </button>
        </div>
      </form>

      <section className="insight-card">
        <div className="admin-page-head compact">
          <h3>AI FAQ Suggestions (From Unanswered Questions)</h3>
          <button className="admin-btn" onClick={loadFaqSuggestions} disabled={faqLoading}>
            {faqLoading ? "Loading..." : "Refresh Suggestions"}
          </button>
        </div>

        {faqError && <p className="error">{faqError}</p>}
        {!faqLoading && !faqError && faqSuggestions.length === 0 && (
          <div className="empty-state">No strong FAQ suggestions yet. Keep collecting chat logs.</div>
        )}

        {!faqLoading && faqSuggestions.length > 0 && (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Count</th>
                  <th>Suggested Tag</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {faqSuggestions.map((item, index) => (
                  <tr key={`${item.normalized_question || item.question}-${index}`}>
                    <td>{item.question || "-"}</td>
                    <td>{item.count || 0}</td>
                    <td>{item.suggested_tag || "-"}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="admin-btn"
                          onClick={() => applySuggestionAsDraft(item)}
                        >
                          Use as Draft
                        </button>
                        <button
                          className="muted-btn"
                          onClick={() => createFromSuggestion(item)}
                          disabled={creatingSuggestionKey === (item.normalized_question || item.question || "")}
                        >
                          {creatingSuggestionKey === (item.normalized_question || item.question || "")
                            ? "Creating..."
                            : "Create Intent"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <form className="admin-toolbar" onSubmit={submitSearch}>
        <input
          className="admin-input"
          placeholder="Search by intent tag"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="submit" className="admin-btn">Search</button>
        <button type="button" className="muted-btn" onClick={resetSearch}>Clear</button>
      </form>

      {loading && <p>Loading intents...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && intents.length === 0 && (
        <div className="empty-state">No intents found for your current filter.</div>
      )}

      {!loading && !error && intents.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Tag</th>
                <th>Patterns</th>
                <th>Responses</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {intents.map((intent) => (
                <tr key={intent.tag}>
                  <td>{intent.tag}</td>
                  <td>{(intent.patterns || []).length}</td>
                  <td>{(intent.responses || []).length}</td>
                  <td>
                    <div className="row-actions">
                      <button className="admin-btn" onClick={() => onEdit(intent)}>Edit</button>
                      <button className="danger-btn" onClick={() => onDelete(intent.tag)}>Delete</button>
                    </div>
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
          <p>Page {page} of {Math.max(1, pagination.pages)} | {pagination.total} intents</p>
          <button className="muted-btn" onClick={goNext} disabled={page >= pagination.pages}>Next</button>
        </div>
      )}
    </AdminLayout>
  );
}

export default Intents;
