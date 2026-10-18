export interface Dataset {
  id: string;
  name: string;
  description?: string;
  publisher: string;
  source_url?: string;
  source_type: 'url' | 'upload' | 'sample';
  data_format: 'csv' | 'json';
  update_cadence: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'unknown';
  status: 'healthy' | 'warning' | 'critical' | 'unavailable' | 'pending';
  latest_quality_score?: number;
  row_count: number;
  column_count: number;
  file_hash?: string;
  last_ingested_at?: string;
  last_successful_ingestion_at?: string;
  last_content_change_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DimensionScore {
  score: number;
  weight: number;
  checks_count: number;
  passed_count: number;
  warning_count: number;
  failed_count: number;
  explanation: string;
}

export interface QualityScoreBreakdown {
  overall_score: number;
  is_passing: boolean;
  critical_failures_count: number;
  total_checks: number;
  passed_checks: number;
  warning_checks: number;
  failed_checks: number;
  dimensions: Record<string, DimensionScore>;
  summary_text: string;
}

export interface QualityCheckResult {
  id: string;
  run_id: string;
  dataset_id: string;
  check_id: string;
  check_name: string;
  category: string;
  status: 'passed' | 'warning' | 'failed' | 'not_applicable';
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  affected_rows: number;
  affected_columns?: string[];
  explanation: string;
  evidence?: any;
  suggested_action?: string;
  created_at: string;
}

export interface QualityReport {
  dataset_id: string;
  run_id?: string;
  evaluated_at?: string;
  overall_score: number;
  breakdown: QualityScoreBreakdown;
  checks: QualityCheckResult[];
}

export interface AnomalyFinding {
  id: string;
  run_id: string;
  dataset_id: string;
  column_name: string;
  row_index: number;
  row_identifier?: string;
  value: string;
  detection_method: 'iqr' | 'zscore' | 'mad' | 'isolation_forest';
  threshold_rule: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  score?: number;
  explanation: string;
  review_status: 'pending' | 'acknowledged' | 'false_positive';
  acknowledged_notes?: string;
  acknowledged_at?: string;
  created_at: string;
}

export interface ColumnSchemaItem {
  name: string;
  inferred_type: string;
  nullable: boolean;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: any[];
}

export interface SchemaSnapshot {
  id: string;
  run_id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  columns_schema: ColumnSchemaItem[];
  created_at: string;
}

export interface ColumnDiffItem {
  column_name: string;
  change_type: string;
  severity: string;
  old_value?: any;
  new_value?: any;
  impact_analysis: string;
  evidence?: any;
}

export interface SchemaDiff {
  has_drift: boolean;
  severity: string;
  baseline_run_id?: string;
  current_run_id: string;
  added_columns: string[];
  removed_columns: string[];
  type_changes: ColumnDiffItem[];
  possible_renames: any[];
  diff_items: ColumnDiffItem[];
  summary: string;
}

export interface DriftMetricDetail {
  column_name: string;
  metric_type: string;
  metric_value: number;
  p_value?: number;
  drift_detected: boolean;
  interpretation: string;
  details?: any;
}

export interface DriftSummary {
  dataset_id: string;
  baseline_run_id?: string;
  current_run_id?: string;
  baseline_date?: string;
  current_date?: string;
  drift_available: boolean;
  columns_analyzed: number;
  drifted_columns_count: number;
  has_significant_drift: boolean;
  summary: string;
  metrics: DriftMetricDetail[];
}

export interface IngestionRun {
  id: string;
  dataset_id: string;
  run_type: string;
  status: string;
  started_at: string;
  completed_at?: string;
  row_count: number;
  column_count: number;
  quality_score?: number;
  summary?: string;
  error_message?: string;
  file_hash?: string;
}

export interface RunComparison {
  dataset_id: string;
  current_run_id: string;
  previous_run_id?: string;
  has_comparison: boolean;
  quality_score_change: number;
  row_count_change: number;
  new_failures: any[];
  resolved_failures: any[];
  new_anomalies_count: number;
  schema_changed: boolean;
  summary: string;
}

export interface DashboardSummary {
  total_datasets: number;
  healthy_datasets: number;
  warning_datasets: number;
  critical_datasets: number;
  unavailable_sources: number;
  average_quality_score: number;
  total_anomalies_detected: number;
  pending_anomalies_count: number;
  recent_runs: any[];
  recent_anomalies: any[];
  recent_schema_changes: any[];
  quality_score_trends: any[];
}

export interface DatasetPreview {
  dataset_id: string;
  dataset_name: string;
  total_rows: number;
  total_columns: number;
  columns: string[];
  column_types: Record<string, string>;
  page: number;
  page_size: number;
  data: Record<string, any>[];
}

export interface DiagnosticBrief {
  dataset_name: string;
  verdict: string;
  executive_summary: string;
  overall_score: number;
  findings_analysis: any[];
  anomaly_summary: any[];
  schema_notes: string[];
  drift_notes: string[];
  action_items: string[];
}
