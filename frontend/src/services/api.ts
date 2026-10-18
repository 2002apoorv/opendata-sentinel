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

const BASE_URL = '/api';

export const api = {
  // Dashboard Summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${BASE_URL}/dashboard/summary`);
    if (!res.ok) throw new Error('Failed to load dashboard summary');
    return res.json();
  },

  // Dataset Registry
  async getDatasets(search?: string, status?: string): Promise<Dataset[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status && status !== 'all') params.append('status_filter', status);
    const res = await fetch(`${BASE_URL}/datasets?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch datasets');
    return res.json();
  },

  async getDataset(id: string): Promise<Dataset> {
    const res = await fetch(`${BASE_URL}/datasets/${id}`);
    if (!res.ok) throw new Error('Failed to fetch dataset');
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
    const res = await fetch(`${BASE_URL}/datasets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to register dataset');
    }
    return res.json();
  },

  async uploadDataset(formData: FormData): Promise<Dataset> {
    const res = await fetch(`${BASE_URL}/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload dataset');
    }
    return res.json();
  },

  async deleteDataset(id: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/datasets/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete dataset');
  },

  // Pipeline triggers
  async runMonitor(datasetId: string): Promise<IngestionRun> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/monitor`, { method: 'POST' });
    if (!res.ok) throw new Error('Monitoring run failed');
    return res.json();
  },

  // Preview
  async getPreview(datasetId: string, page = 1, pageSize = 25, search = ''): Promise<DatasetPreview> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (search) params.append('search', search);
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/preview?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load dataset preview');
    return res.json();
  },

  // Quality Report
  async getQualityReport(datasetId: string, runId?: string): Promise<QualityReport> {
    const url = runId
      ? `${BASE_URL}/datasets/${datasetId}/quality?run_id=${runId}`
      : `${BASE_URL}/datasets/${datasetId}/quality`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load quality report');
    return res.json();
  },

  // Anomalies
  async getAnomalies(datasetId: string, method?: string, severity?: string): Promise<AnomalyFinding[]> {
    const params = new URLSearchParams();
    if (method && method !== 'all') params.append('method', method);
    if (severity && severity !== 'all') params.append('severity', severity);
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/anomalies?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load anomalies');
    return res.json();
  },

  async acknowledgeAnomaly(datasetId: string, anomalyId: string, notes?: string, isFalsePositive = false): Promise<any> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/anomalies/${anomalyId}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes, is_false_positive: isFalsePositive }),
    });
    if (!res.ok) throw new Error('Failed to acknowledge anomaly');
    return res.json();
  },

  // Schema & Schema Drift
  async getSchema(datasetId: string): Promise<SchemaSnapshot> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/schema`);
    if (!res.ok) throw new Error('Failed to load schema snapshot');
    return res.json();
  },

  async getSchemaDiff(datasetId: string): Promise<SchemaDiff> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/schema/diff`);
    if (!res.ok) throw new Error('Failed to load schema diff');
    return res.json();
  },

  // Distribution Drift
  async getDrift(datasetId: string): Promise<DriftSummary> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/drift`);
    if (!res.ok) throw new Error('Failed to load drift summary');
    return res.json();
  },

  // Runs & Run Comparison
  async getRuns(datasetId: string): Promise<IngestionRun[]> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/runs`);
    if (!res.ok) throw new Error('Failed to load runs');
    return res.json();
  },

  async compareRun(datasetId: string, runId: string): Promise<RunComparison> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/runs/${runId}/compare`);
    if (!res.ok) throw new Error('Failed to compare runs');
    return res.json();
  },

  // AI Diagnostic Brief
  async getAiExplanation(datasetId: string): Promise<DiagnosticBrief> {
    const res = await fetch(`${BASE_URL}/datasets/${datasetId}/explain`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to generate diagnostic brief');
    return res.json();
  },

  // Samples & Benchmarks
  async getSamples(): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/samples`);
    if (!res.ok) throw new Error('Failed to load samples');
    return res.json();
  },

  async loadAllSamples(): Promise<any> {
    const res = await fetch(`${BASE_URL}/samples/load-all`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to load demo datasets');
    return res.json();
  },

  async getEvaluationBenchmarks(): Promise<any> {
    const res = await fetch(`${BASE_URL}/evaluation/benchmarks`);
    if (!res.ok) throw new Error('Failed to load evaluation benchmarks');
    return res.json();
  },
};
