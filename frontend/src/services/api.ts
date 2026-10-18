import {
  Dataset,
  DashboardSummary,
  QualityReport,
  AnomalyFinding,
  SchemaSnapshot,
  SchemaDiff,
  DriftSummary,
  IngestionRun,
  RunComparison,
  DatasetPreview,
  DiagnosticBrief,
} from '../types';

function getBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (!envUrl) return '/api';
  const clean = envUrl.trim().replace(/\/+$/, '');
  if (clean.startsWith('http') && !clean.endsWith('/api')) {
    return `${clean}/api`;
  }
  return clean;
}

export const BASE_URL = getBaseUrl();

async function safeFetch(url: string, options: RequestInit = {}, timeoutMs = 20000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timer);
    return res;
  } catch (err: any) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error(`Connection timed out after ${timeoutMs / 1000}s while reaching ${url}. If using Render free tier, the server may take ~50s to wake up from cold sleep.`);
    }
    throw err;
  }
}

export const api = {
  // Dashboard Summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await safeFetch(`${BASE_URL}/dashboard/summary`);
    if (!res.ok) throw new Error(`Failed to load dashboard summary (HTTP ${res.status})`);
    return res.json();
  },

  // Dataset Registry
  async getDatasets(search?: string, status?: string): Promise<Dataset[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status && status !== 'all') params.append('status_filter', status);
    const res = await safeFetch(`${BASE_URL}/datasets?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to fetch datasets (HTTP ${res.status})`);
    return res.json();
  },

  async getDataset(id: string): Promise<Dataset> {
    const res = await safeFetch(`${BASE_URL}/datasets/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch dataset (HTTP ${res.status})`);
    return res.json();
  },

  async registerDataset(payload: {
    name: string;
    publisher: string;
    description?: string;
    source_url?: string;
    source_type: 'url' | 'sample';
    data_format: 'csv' | 'json';
    update_cadence: string;
  }): Promise<Dataset> {
    const res = await safeFetch(`${BASE_URL}/datasets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to register dataset (HTTP ${res.status})`);
    }
    return res.json();
  },

  async uploadDataset(formData: FormData): Promise<Dataset> {
    const res = await safeFetch(`${BASE_URL}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to upload dataset (HTTP ${res.status})`);
    }
    return res.json();
  },

  async deleteDataset(id: string): Promise<void> {
    const res = await safeFetch(`${BASE_URL}/datasets/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Failed to delete dataset (HTTP ${res.status})`);
  },

  // Pipeline triggers
  async runMonitor(datasetId: string): Promise<IngestionRun> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/monitor`, { method: 'POST' });
    if (!res.ok) throw new Error(`Monitoring run failed (HTTP ${res.status})`);
    return res.json();
  },

  // Preview
  async getPreview(datasetId: string, page = 1, pageSize = 25, search = ''): Promise<DatasetPreview> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (search) params.append('search', search);
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/preview?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to load dataset preview (HTTP ${res.status})`);
    return res.json();
  },

  // Quality Report
  async getQualityReport(datasetId: string, runId?: string): Promise<QualityReport> {
    const url = runId
      ? `${BASE_URL}/datasets/${datasetId}/quality?run_id=${runId}`
      : `${BASE_URL}/datasets/${datasetId}/quality`;
    const res = await safeFetch(url);
    if (!res.ok) throw new Error(`Failed to load quality report (HTTP ${res.status})`);
    return res.json();
  },

  // Anomalies
  async getAnomalies(datasetId: string, method?: string, severity?: string): Promise<AnomalyFinding[]> {
    const params = new URLSearchParams();
    if (method && method !== 'all') params.append('method', method);
    if (severity && severity !== 'all') params.append('severity', severity);
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/anomalies?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to load anomalies (HTTP ${res.status})`);
    return res.json();
  },

  async acknowledgeAnomaly(datasetId: string, anomalyId: string, notes?: string, isFalsePositive = false): Promise<any> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/anomalies/${anomalyId}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes, is_false_positive: isFalsePositive }),
    });
    if (!res.ok) throw new Error(`Failed to acknowledge anomaly (HTTP ${res.status})`);
    return res.json();
  },

  // Schema & Schema Drift
  async getSchema(datasetId: string): Promise<SchemaSnapshot> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/schema`);
    if (!res.ok) throw new Error(`Failed to load schema snapshot (HTTP ${res.status})`);
    return res.json();
  },

  async getSchemaDiff(datasetId: string): Promise<SchemaDiff> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/schema/diff`);
    if (!res.ok) throw new Error(`Failed to load schema diff (HTTP ${res.status})`);
    return res.json();
  },

  // Distribution Drift
  async getDrift(datasetId: string): Promise<DriftSummary> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/drift`);
    if (!res.ok) throw new Error(`Failed to load drift summary (HTTP ${res.status})`);
    return res.json();
  },

  // Runs & Run Comparison
  async getRuns(datasetId: string): Promise<IngestionRun[]> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/runs`);
    if (!res.ok) throw new Error(`Failed to load runs (HTTP ${res.status})`);
    return res.json();
  },

  async compareRun(datasetId: string, runId: string): Promise<RunComparison> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/runs/${runId}/compare`);
    if (!res.ok) throw new Error(`Failed to compare runs (HTTP ${res.status})`);
    return res.json();
  },

  // AI Diagnostic Brief
  async getAiExplanation(datasetId: string): Promise<DiagnosticBrief> {
    const res = await safeFetch(`${BASE_URL}/datasets/${datasetId}/explain`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to generate diagnostic brief (HTTP ${res.status})`);
    return res.json();
  },

  // Samples & Benchmarks
  async getSamples(): Promise<any[]> {
    const res = await safeFetch(`${BASE_URL}/samples`);
    if (!res.ok) throw new Error(`Failed to load samples (HTTP ${res.status})`);
    return res.json();
  },

  async loadAllSamples(): Promise<any> {
    const res = await safeFetch(`${BASE_URL}/samples/load-all`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to load demo datasets (HTTP ${res.status})`);
    return res.json();
  },

  async getEvaluationBenchmarks(): Promise<any> {
    const res = await safeFetch(`${BASE_URL}/evaluation/benchmarks`);
    if (!res.ok) throw new Error(`Failed to load evaluation benchmarks (HTTP ${res.status})`);
    return res.json();
  },
};
