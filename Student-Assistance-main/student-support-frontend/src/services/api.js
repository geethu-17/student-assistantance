import axios from "axios";

const resolveApiBaseUrl = () => {
  if (typeof window === "undefined") {
    const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();
    if (configuredBaseUrl) {
      return configuredBaseUrl;
    }
    return "/api";
  }

  const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();
  const hostname = window.location.hostname;
  const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";

  if (isLocalhost && configuredBaseUrl) {
    return configuredBaseUrl;
  }

  return "/api";
};

const API_BASE_URL = resolveApiBaseUrl();

const API = axios.create({
  baseURL: API_BASE_URL
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("adminToken");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const requestUrl = error?.config?.url || "";
    if (status === 401 && requestUrl.includes("/admin/")) {
      localStorage.removeItem("admin");
      localStorage.removeItem("adminToken");
      if (typeof window !== "undefined" && window.location.pathname !== "/admin/login") {
        window.location.assign("/admin/login");
      }
    }
    return Promise.reject(error);
  }
);

/* ==========================
   CHATBOT
========================== */

export const sendMessage = (message, user = "guest") =>
  API.post("/chat", { message, user });

export const sendVoiceMessage = (transcript, user = "voice_user") =>
  API.post("/ai/voice/chat", { transcript, user });

export const getGeneratedFaqs = (limit = 8) =>
  API.get("/ai/faqs/generated", { params: { limit } });


/* ==========================
   USER AUTH
========================== */

export const registerUser = (data) =>
  API.post("/register", data);

export const loginUser = (data) =>
  API.post("/login", data);

export const forgotPassword = (identifier) =>
  API.post("/forgot-password", { identifier });

export const resetPassword = (data) =>
  API.post("/reset-password", data);


/* ==========================
   ADMIN AUTH
========================== */

export const adminLogin = (data) =>
  API.post("/admin/login", data);

export const adminForgotPassword = (identifier) =>
  API.post("/admin/forgot-password", { identifier });

export const adminResetPassword = (data) =>
  API.post("/admin/reset-password", data);


/* ==========================
   INTENT MANAGEMENT
========================== */

export const getIntents = (params = {}) =>
  API.get("/admin/intents", { params });

export const addIntent = (data) =>
  API.post("/admin/intents", data);

export const updateIntent = (tag, data) =>
  API.put(`/admin/intents/${encodeURIComponent(tag)}`, data);

export const deleteIntent = (tag) =>
  API.delete(`/admin/intents/${encodeURIComponent(tag)}`);

export const getFaqSuggestions = (params = {}) =>
  API.get("/admin/faq-suggestions", { params });

export const createIntentFromSuggestion = (data) =>
  API.post("/admin/faq-suggestions/create-intent", data);

export const exportIntents = (params = {}) =>
  API.get("/admin/intents/export", { params, responseType: "blob" });

export const importIntents = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post("/admin/intents/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};


/* ==========================
   ADMIN DASHBOARD
========================== */

export const getDashboardStats = () =>
  API.get("/admin/dashboard");


/* ==========================
   CHAT LOGS
========================== */

export const getChatLogs = (params = {}) =>
  API.get("/admin/chat-logs", { params });


/* ==========================
   USERS MANAGEMENT
========================== */

export const getUsers = (params = {}) =>
  API.get("/admin/users", { params });

export const deleteUser = (id) =>
  API.delete(`/admin/users/${encodeURIComponent(id)}`);

export const exportUsers = (params = {}) =>
  API.get("/admin/users/export", { params, responseType: "blob" });

export const importUsers = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post("/admin/users/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};


/* ==========================
   ANALYTICS
========================== */

export const getAnalytics = () =>
  API.get("/admin/analytics");

export const getSentimentReport = () =>
  API.get("/admin/sentiment-report");

export const getAdminAuditLogs = (params = {}) =>
  API.get("/admin/audit-logs", { params });

export const exportAdminAuditLogs = (params = {}) =>
  API.get("/admin/audit-logs/export", { params, responseType: "blob" });

export const getIntegrationsStatus = () =>
  API.get("/admin/integrations/status");

export const sendSmtpTestEmail = (toEmail) =>
  API.post("/admin/integrations/smtp-test", { to_email: toEmail });

export const getModuleData = (moduleName, params = {}) =>
  API.get(`/admin/module-data/${encodeURIComponent(moduleName)}`, { params });

export const createModuleData = (moduleName, data) =>
  API.post(`/admin/module-data/${encodeURIComponent(moduleName)}`, data);

export const updateModuleData = (moduleName, recordId, data) =>
  API.put(`/admin/module-data/${encodeURIComponent(moduleName)}/${encodeURIComponent(recordId)}`, data);

export const deleteModuleData = (moduleName, recordId) =>
  API.delete(`/admin/module-data/${encodeURIComponent(moduleName)}/${encodeURIComponent(recordId)}`);

export const exportModuleData = (moduleName, params = {}) =>
  API.get(`/admin/module-data/${encodeURIComponent(moduleName)}/export`, {
    params,
    responseType: "blob",
  });

export const importModuleData = (moduleName, file) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post(`/admin/module-data/${encodeURIComponent(moduleName)}/import`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

/* ==========================
   COUNSELING MANAGEMENT
========================== */

export const getStudentCounselingSlots = (params = {}) =>
  API.get("/counseling-slots", { params });

export const submitCounselingRequest = (data) =>
  API.post("/counseling-request", data);

export const getCounselingBookingStatus = (bookingId) =>
  API.get(`/counseling-booking-status/${encodeURIComponent(bookingId)}`);

export const getPrograms = (params = {}) =>
  API.get("/programs", { params });

export const getCourseRegistrationGuidance = () =>
  API.get("/course-registration-guidance");

export const getAcademicCalendar = () =>
  API.get("/academic-calendar");

export const getCreditRequirements = (params = {}) =>
  API.get("/credit-requirements", { params });

export const getCreditStatus = (registrationNumber) =>
  API.get(`/credit-status/${encodeURIComponent(registrationNumber)}`);

export const getFeeInfo = (params = {}) =>
  API.get("/fees", { params });

export const getScholarships = () =>
  API.get("/scholarships");

export const getLoanAssistance = () =>
  API.get("/loan-assistance");

export const getHostelInfo = () =>
  API.get("/hostel-info");

export const getTransportSchedules = () =>
  API.get("/transport-schedules");

export const getCampusNavigation = () =>
  API.get("/campus-navigation");

export const getStressResources = () =>
  API.get("/stress-resources");

export const getApplicationStatus = (registrationNumber) =>
  API.get(`/application-status/${encodeURIComponent(registrationNumber)}`);

export const getCounselingSlots = (params = {}) =>
  API.get("/admin/counseling-slots", { params });

export const createCounselingSlot = (data) =>
  API.post("/admin/counseling-slots", data);

export const deleteCounselingSlot = (slotId) =>
  API.delete(`/admin/counseling-slots/${encodeURIComponent(slotId)}`);

export const getCounselingBookings = (params = {}) =>
  API.get("/admin/counseling-bookings", { params });

export const updateCounselingBookingStatus = (bookingId, data) =>
  API.put(`/admin/counseling-bookings/${encodeURIComponent(bookingId)}/status`, data);

export const getApiErrorMessage = (error, fallback) => {
  if (!error?.response) {
    return "Cannot reach backend API. Check that the deployed frontend is pointing to a live backend.";
  }

  return (
    error.response?.data?.details ||
    error.response?.data?.error ||
    fallback
  );
};

export default API;
