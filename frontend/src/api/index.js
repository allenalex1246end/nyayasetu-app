import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8001",
  timeout: 20000,
});

// Request interceptor — attach Content-Type header
api.interceptors.request.use(
  (config) => {
    config.headers["Content-Type"] = "application/json";
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — surface server-side errors
api.interceptors.response.use(
  (response) => {
    if (response.data && response.data.success === false) {
      const err = new Error(response.data.error || "Request failed");
      err.response = response;
      throw err;
    }
    return response;
  },
  (error) => Promise.reject(error)
);

/* ────────── Grievance endpoints ────────── */

export const submitGrievance = (data) => api.post("/api/grievances", data);

export const getGrievances = (params) =>
  api.get("/api/grievances", { params });

export const getGrievance = (id) => api.get(`/api/grievances/${id}`);

export const resolveGrievance = (id) =>
  api.patch(`/api/grievances/${id}/resolve`);

export const confirmResolution = (id) =>
  api.patch(`/api/grievances/${id}/confirm`);

/* ────────── Dashboard endpoints ────────── */

export const getDashboardStats = () => api.get("/api/dashboard/stats");

export const getDashboardClusters = () => api.get("/api/dashboard/clusters");

export const getDashboardMap = () => api.get("/api/dashboard/map");

export const generateBrief = () => api.get("/api/dashboard/brief");

export const getDashboardTrends = () => api.get("/api/dashboard/trends");

/* ────────── Legal / Justice-Link endpoints ────────── */

export const getLegalCases = () => api.get("/api/legal");

export const addLegalCase = (data) => api.post("/api/legal", data);

export const checkEligibility = (id) => api.get(`/api/legal/check/${id}`);

/* ────────── Translation endpoint ────────── */

export const translateGrievance = (id) => api.get(`/api/translate/${id}`);

/* ────────── AI Identity Extraction endpoint ────────── */

export const extractIdentity = (transcript) => api.post("/api/extract-identity", { transcript });

/* ────────── Community endpoint ────────── */

export const supportGrievance = (id) => api.post(`/api/grievances/${id}/support`);

/* ────────── Railway (RailMadad 2.0) endpoints ────────── */

export const submitRailwayGrievance = (data) => api.post("/api/railway/grievances", data);

export const getRailwayGrievances = (params) => api.get("/api/railway/grievances", { params });

export const getRailwayGrievance = (id) => api.get(`/api/railway/grievances/${id}`);

export const resolveRailwayGrievance = (id) => api.patch(`/api/railway/grievances/${id}/resolve`);

export const getRailwayDashboardStats = () => api.get("/api/railway/dashboard/stats");

export const getRailwayDashboardClusters = () => api.get("/api/railway/dashboard/clusters");

export const getRailwayDashboardTrends = () => api.get("/api/railway/dashboard/trends");

export const generateRailwayBrief = () => api.get("/api/railway/dashboard/brief");

/* ────────── Audit & Budget endpoints ────────── */

export const getBudgetEntries = (params) => api.get("/api/audit/budget", { params });

export const getBudgetStats = () => api.get("/api/audit/budget/stats");

export const getFlaggedEntries = () => api.get("/api/audit/flagged");

export const createBudgetEntry = (data) => api.post("/api/audit/budget", data);

export const flagBudgetEntry = (id, reason) => api.patch(`/api/audit/budget/${id}/flag`, null, { params: { reason } });

/* ────────── Predictions endpoints ────────── */

export const getPredictions = (params) => api.get("/api/predictions", { params });

export const runPredictions = () => api.post("/api/predictions/run");

export default api;
