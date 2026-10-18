import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileSpreadsheet,
  Layers,
  Sparkles,
  GitCompare,
  TrendingDown,
  Clock,
  History,
  ShieldAlert,
  Search,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  Check,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import {
  Dataset,
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
import { api } from '../services/api';
import { AcknowledgeModal } from '../components/AcknowledgeModal';

interface DatasetDetailProps {
  datasetId: string;
  onBack: () => void;
}

export const DatasetDetail: React.FC<DatasetDetailProps> = ({ datasetId, onBack }) => {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [activeTab, setActiveTab] = useState<
    'overview' | 'preview' | 'quality' | 'schema' | 'anomalies' | 'drift' | 'freshness' | 'history'
  >('overview');

  // Sub-resource states
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyFinding[]>([]);
  const [schemaSnapshot, setSchemaSnapshot] = useState<SchemaSnapshot | null>(null);
  const [schemaDiff, setSchemaDiff] = useState<SchemaDiff | null>(null);
  const [driftSummary, setDriftSummary] = useState<DriftSummary | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [aiBrief, setAiBrief] = useState<DiagnosticBrief | null>(null);

  // Preview pagination & search
  const [previewPage, setPreviewPage] = useState(1);
  const [previewSearch, setPreviewSearch] = useState('');

  // Filtering states
  const [checkStatusFilter, setCheckStatusFilter] = useState('all');
  const [checkCategoryFilter, setCheckCategoryFilter] = useState('all');
  const [anomalyMethodFilter, setAnomalyMethodFilter] = useState('all');

  // Run comparison modal / view
  const [selectedRunForDiff, setSelectedRunForDiff] = useState<IngestionRun | null>(null);
  const [runDiffData, setRunDiffData] = useState<RunComparison | null>(null);

  // Anomaly modal state
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyFinding | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isMonitoring, setIsMonitoring] = useState(false);

  const loadAllData = async () => {
    try {
      const [d, q, a, s, sd, dr, r, b] = await Promise.all([
        api.getDataset(datasetId),
        api.getQualityReport(datasetId).catch(() => null),
        api.getAnomalies(datasetId).catch(() => []),
        api.getSchema(datasetId).catch(() => null),
        api.getSchemaDiff(datasetId).catch(() => null),
        api.getDrift(datasetId).catch(() => null),
        api.getRuns(datasetId).catch(() => []),
        api.getAiExplanation(datasetId).catch(() => null),
      ]);

      setDataset(d);
      setQualityReport(q);
      setAnomalies(a);
      setSchemaSnapshot(s);
      setSchemaDiff(sd);
      setDriftSummary(dr);
      setRuns(r);
      setAiBrief(b);

      // Load initial preview page
      api.getPreview(datasetId, 1, 15).then(setPreview).catch(() => {});
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [datasetId]);

  const handleRunMonitoring = async () => {
    setIsMonitoring(true);
    try {
      await api.runMonitor(datasetId);
      await loadAllData();
    } catch (err) {
      alert('Monitoring cycle failed: ' + err);
    } finally {
      setIsMonitoring(false);
    }
  };

  const handlePreviewPageChange = async (newPage: number) => {
    setPreviewPage(newPage);
    try {
      const data = await api.getPreview(datasetId, newPage, 15, previewSearch);
      setPreview(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handlePreviewSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setPreviewPage(1);
    try {
      const data = await api.getPreview(datasetId, 1, 15, previewSearch);
      setPreview(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectRunForDiff = async (run: IngestionRun) => {
    setSelectedRunForDiff(run);
    try {
      const diff = await api.compareRun(datasetId, run.id);
      setRunDiffData(diff);
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading || !dataset) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-2 text-slate-500 text-xs">
          <RefreshCw className="w-7 h-7 text-teal-600 animate-spin" />
          <span>Loading dataset monitoring telemetry...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Back button & Action Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Registry</span>
        </button>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleRunMonitoring}
            disabled={isMonitoring}
            className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isMonitoring ? 'animate-spin' : ''}`} />
            <span>{isMonitoring ? 'Executing Audit...' : 'Execute Monitor Run'}</span>
          </button>
        </div>
      </div>

      {/* Dataset Master Telemetry Header Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">{dataset.name}</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">
              {dataset.data_format}
            </span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                dataset.status === 'healthy'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : dataset.status === 'warning'
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
            >
              {dataset.status}
            </span>
          </div>

          <p className="text-xs text-slate-500 max-w-3xl">{dataset.description || 'Continuous monitoring active.'}</p>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-slate-500 pt-1">
            <span>Publisher: <strong className="text-slate-700">{dataset.publisher}</strong></span>
            <span>Cadence: <strong className="text-slate-700 uppercase">{dataset.update_cadence}</strong></span>
            <span>Rows: <strong className="text-slate-700">{dataset.row_count}</strong></span>
            <span>Cols: <strong className="text-slate-700">{dataset.column_count}</strong></span>
            {dataset.file_hash && (
              <span className="font-mono text-[11px] text-slate-400" title={`SHA256: ${dataset.file_hash}`}>
                Hash: {dataset.file_hash.substring(0, 10)}...
              </span>
            )}
          </div>
        </div>

        {/* Quality Score Hero Gauge */}
        <div className="flex items-center space-x-4 bg-slate-50 p-4 rounded-xl border border-slate-200 self-start lg:self-auto shrink-0">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Explainable Quality Score</div>
            <div
              className={`text-3xl font-extrabold font-mono mt-0.5 ${
                (dataset.latest_quality_score || 0) >= 80
                  ? 'text-emerald-600'
                  : (dataset.latest_quality_score || 0) >= 60
                  ? 'text-amber-600'
                  : 'text-rose-600'
              }`}
            >
              {dataset.latest_quality_score !== null && dataset.latest_quality_score !== undefined
                ? `${dataset.latest_quality_score}%`
                : 'Pending'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {qualityReport ? `${qualityReport.breakdown.passed_checks}/${qualityReport.breakdown.total_checks} checks passed` : 'Pending initial run'}
            </div>
          </div>
        </div>
      </div>

      {/* 8-Tab Navigation Bar */}
      <div className="border-b border-slate-200 flex items-center space-x-1 overflow-x-auto text-xs font-semibold">
        {[
          { id: 'overview', label: 'Executive Diagnostic Brief', icon: Sparkles },
          { id: 'preview', label: 'Data Preview', icon: FileSpreadsheet },
          { id: 'quality', label: `Quality Checks (${qualityReport?.checks.length || 0})`, icon: CheckCircle2 },
          { id: 'schema', label: 'Schema & Drift', icon: Layers },
          { id: 'anomalies', label: `Anomaly Explorer (${anomalies.length})`, icon: AlertTriangle },
          { id: 'drift', label: 'Distribution Drift', icon: GitCompare },
          { id: 'freshness', label: 'Freshness & SLA', icon: Clock },
          { id: 'history', label: `Run History (${runs.length})`, icon: History },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`py-3 px-3.5 border-b-2 font-medium flex items-center space-x-1.5 whitespace-nowrap transition-all ${
                isActive
                  ? 'border-teal-600 text-teal-800 font-bold bg-teal-50/20'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: EXECUTIVE DIAGNOSTIC BRIEF & AI EXPLANATION */}
      {/* ========================================================================= */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {aiBrief && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Executive Data Reliability Brief</h3>
                    <p className="text-xs text-slate-500">Root-cause hypotheses and explainable analytics</p>
                  </div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                    aiBrief.verdict.includes('HEALTHY')
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : aiBrief.verdict.includes('CAUTION')
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                  }`}
                >
                  {aiBrief.verdict}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 text-xs text-slate-700 leading-relaxed border border-slate-200">
                {aiBrief.executive_summary}
              </div>

              {/* Action Items Checklist */}
              {aiBrief.action_items && aiBrief.action_items.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Recommended Next Actions</h4>
                  <div className="space-y-1.5">
                    {aiBrief.action_items.map((act: string, idx: number) => (
                      <div key={idx} className="flex items-start space-x-2 text-xs text-slate-700 bg-teal-50/40 p-2.5 rounded-lg border border-teal-200/50">
                        <Check className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Quality Dimension Breakdown Cards */}
          {qualityReport && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Multi-Dimensional Quality Breakdown</h3>
                <p className="text-xs text-slate-500">Transparent scoring weighted across 6 diagnostic pillars</p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {Object.entries(qualityReport.breakdown.dimensions).map(([key, dim]) => (
                  <div key={key} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase text-slate-600">{key}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{(dim.weight * 100).toFixed(0)}% wt</span>
                    </div>

                    <div className="text-xl font-bold font-mono text-slate-900">
                      {dim.score.toFixed(1)}%
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          dim.score >= 80 ? 'bg-emerald-500' : dim.score >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${dim.score}%` }}
                      ></div>
                    </div>

                    <p className="text-[10px] text-slate-500 line-clamp-2">{dim.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: DATA PREVIEW */}
      {/* ========================================================================= */}
      {activeTab === 'preview' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Dataset Records Preview</h3>
              <p className="text-xs text-slate-500">
                Safe windowed display of underlying parsed observations ({preview?.total_rows || 0} total records)
              </p>
            </div>

            <form onSubmit={handlePreviewSearch} className="flex items-center space-x-2">
              <input
                type="text"
                placeholder="Filter preview rows..."
                value={previewSearch}
                onChange={(e) => setPreviewSearch(e.target.value)}
                className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
              <button
                type="submit"
                className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700"
              >
                Search
              </button>
            </form>
          </div>

          {preview && preview.data.length > 0 ? (
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs divide-y divide-slate-200">
                <thead className="bg-slate-50 text-slate-700 font-semibold">
                  <tr>
                    {preview.columns.map((col) => (
                      <th key={col} className="py-2.5 px-3 whitespace-nowrap">
                        <div className="text-slate-900">{col}</div>
                        <div className="text-[10px] text-slate-400 font-mono font-normal">
                          {preview.column_types[col] || 'string'}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px] text-slate-800">
                  {preview.data.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-50">
                      {preview.columns.map((col) => (
                        <td key={col} className="py-2 px-3 whitespace-nowrap">
                          {row[col] !== null && row[col] !== undefined ? (
                            String(row[col])
                          ) : (
                            <span className="text-slate-400 italic font-sans text-[10px]">null</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-xs text-slate-400">No records found matching query.</div>
          )}

          {/* Pagination Controls */}
          {preview && (
            <div className="flex items-center justify-between text-xs text-slate-500 pt-2">
              <span>
                Showing page {preview.page} of {Math.ceil(preview.total_rows / preview.page_size) || 1}
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handlePreviewPageChange(preview.page - 1)}
                  disabled={preview.page <= 1}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handlePreviewPageChange(preview.page + 1)}
                  disabled={preview.page >= Math.ceil(preview.total_rows / preview.page_size)}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: QUALITY CHECKS */}
      {/* ========================================================================= */}
      {activeTab === 'quality' && (
        <div className="space-y-4">
          {/* Check Filters */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-3">
              <span className="font-semibold text-slate-700">Filter Status:</span>
              {['all', 'passed', 'warning', 'failed'].map((st) => (
                <button
                  key={st}
                  onClick={() => setCheckStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg font-medium capitalize transition-all ${
                    checkStatusFilter === st
                      ? 'bg-teal-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-700">Category:</span>
              <select
                value={checkCategoryFilter}
                onChange={(e) => setCheckCategoryFilter(e.target.value)}
                className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white"
              >
                <option value="all">All Categories</option>
                <option value="completeness">Completeness</option>
                <option value="uniqueness">Uniqueness</option>
                <option value="validity">Validity</option>
                <option value="consistency">Consistency</option>
                <option value="schema">Schema</option>
                <option value="structure">Structure</option>
              </select>
            </div>
          </div>

          {/* Structured Check Results List */}
          <div className="space-y-3">
            {qualityReport?.checks
              .filter((c) => {
                if (checkStatusFilter !== 'all' && c.status !== checkStatusFilter) return false;
                if (checkCategoryFilter !== 'all' && c.category !== checkCategoryFilter) return false;
                return true;
              })
              .map((chk) => (
                <div
                  key={chk.id}
                  className={`p-4 rounded-2xl border transition-all ${
                    chk.status === 'failed'
                      ? 'bg-rose-50/40 border-rose-200'
                      : chk.status === 'warning'
                      ? 'bg-amber-50/40 border-amber-200'
                      : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-slate-500">[{chk.check_id}]</span>
                        <h4 className="text-xs font-bold text-slate-900">{chk.check_name}</h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-600">
                          {chk.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{chk.explanation}</p>
                    </div>

                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase shrink-0 ${
                        chk.status === 'passed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : chk.status === 'warning'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {chk.status}
                    </span>
                  </div>

                  {/* Evidence & Suggested Action Box */}
                  <div className="mt-3 pt-3 border-t border-slate-200/60 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="font-semibold text-slate-700">Affected Scope: </span>
                      <span className="text-slate-600">
                        {chk.affected_rows} row(s)
                        {chk.affected_columns && chk.affected_columns.length > 0 && (
                          <span> across columns: {chk.affected_columns.join(', ')}</span>
                        )}
                      </span>
                    </div>

                    {chk.suggested_action && (
                      <div>
                        <span className="font-semibold text-teal-800">Remediation: </span>
                        <span className="text-slate-600">{chk.suggested_action}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: SCHEMA & SCHEMA DRIFT */}
      {/* ========================================================================= */}
      {activeTab === 'schema' && (
        <div className="space-y-6">
          {/* Schema Drift Diff Card */}
          {schemaDiff && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Schema Drift Detection</h3>
                  <p className="text-xs text-slate-500">Comparison with previous successful baseline ingestion</p>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${
                    !schemaDiff.has_drift
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : schemaDiff.severity === 'critical'
                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                  }`}
                >
                  {schemaDiff.has_drift ? `${schemaDiff.severity} drift` : 'No schema drift'}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
                <span className="font-semibold">Summary: </span>
                {schemaDiff.summary}
              </div>

              {schemaDiff.diff_items.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800">Detected Schema Changes</h4>
                  <div className="space-y-2">
                    {schemaDiff.diff_items.map((item, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border text-xs flex items-start justify-between ${
                          item.severity === 'critical'
                            ? 'bg-rose-50/50 border-rose-200'
                            : item.severity === 'warning'
                            ? 'bg-amber-50/50 border-amber-200'
                            : 'bg-slate-50 border-slate-200'
                        }`}
                      >
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-slate-900">{item.column_name}</span>
                            <span className="uppercase text-[10px] font-bold px-1.5 py-0.2 rounded bg-white border border-slate-200 text-slate-700">
                              {item.change_type}
                            </span>
                          </div>
                          <p className="text-slate-600 mt-1">{item.impact_analysis}</p>
                        </div>
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-white text-slate-700">
                          {item.severity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Current Inferred Schema Snapshot Table */}
          {schemaSnapshot && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Active Schema Snapshot</h3>
                <p className="text-xs text-slate-500">
                  Inferred column data types, nullability rates, and unique value cardinality
                </p>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-700 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Column Name</th>
                      <th className="py-2.5 px-3">Inferred Type</th>
                      <th className="py-2.5 px-3">Nullability</th>
                      <th className="py-2.5 px-3">Unique Values</th>
                      <th className="py-2.5 px-3">Sample Values</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {schemaSnapshot.columns_schema.map((c) => (
                      <tr key={c.name} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-bold text-slate-900">{c.name}</td>
                        <td className="py-2.5 px-3 text-teal-700 font-bold uppercase text-[10px]">
                          {c.inferred_type}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] ${
                              c.nullable ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'
                            }`}
                          >
                            {c.null_percentage}% null ({c.null_count})
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">{c.unique_count} distinct</td>
                        <td className="py-2.5 px-3 text-slate-500 truncate max-w-xs">
                          {c.sample_values ? c.sample_values.join(', ') : 'None'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: ANOMALY EXPLORER */}
      {/* ========================================================================= */}
      {activeTab === 'anomalies' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-3">
              <span className="font-semibold text-slate-700">Detection Method:</span>
              {['all', 'iqr', 'mad', 'isolation_forest'].map((m) => (
                <button
                  key={m}
                  onClick={() => setAnomalyMethodFilter(m)}
                  className={`px-3 py-1 rounded-lg font-medium uppercase transition-all ${
                    anomalyMethodFilter === m
                      ? 'bg-teal-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>

            <div className="text-slate-400 text-[11px]">
              Decision support indicator: Outliers represent unusual observations, not automatically bad data
            </div>
          </div>

          {anomalies.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-400">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2 opacity-60" />
              No numerical or statistical anomalies detected in this dataset.
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-700 font-semibold">
                    <tr>
                      <th className="py-3 px-3.5">Target Field</th>
                      <th className="py-3 px-3.5">Observed Value</th>
                      <th className="py-3 px-3.5">Row Identifier</th>
                      <th className="py-3 px-3.5">Method</th>
                      <th className="py-3 px-3.5">Severity</th>
                      <th className="py-3 px-3.5">Explanation</th>
                      <th className="py-3 px-3.5">Status</th>
                      <th className="py-3 px-3.5 text-right">Human Review</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {anomalies
                      .filter((a) => anomalyMethodFilter === 'all' || a.detection_method === anomalyMethodFilter)
                      .map((anom) => (
                        <tr key={anom.id} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3.5 font-bold text-slate-900">{anom.column_name}</td>
                          <td className="py-2.5 px-3.5 font-bold text-amber-800">{anom.value}</td>
                          <td className="py-2.5 px-3.5 text-slate-500">{anom.row_identifier || `#${anom.row_index}`}</td>
                          <td className="py-2.5 px-3.5 uppercase font-bold text-teal-800 text-[10px]">
                            {anom.detection_method}
                          </td>
                          <td className="py-2.5 px-3.5">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                                anom.severity === 'critical'
                                  ? 'bg-rose-100 text-rose-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}
                            >
                              {anom.severity}
                            </span>
                          </td>
                          <td className="py-2.5 px-3.5 font-sans text-slate-600 max-w-xs truncate" title={anom.explanation}>
                            {anom.explanation}
                          </td>
                          <td className="py-2.5 px-3.5 font-sans">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                anom.review_status === 'acknowledged'
                                  ? 'bg-teal-50 text-teal-800 border border-teal-200'
                                  : anom.review_status === 'false_positive'
                                  ? 'bg-slate-100 text-slate-600'
                                  : 'bg-amber-50 text-amber-800 border border-amber-200'
                              }`}
                            >
                              {anom.review_status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3.5 text-right font-sans">
                            <button
                              onClick={() => setSelectedAnomaly(anom)}
                              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-teal-600 hover:text-white text-slate-700 font-semibold transition-all text-[11px]"
                            >
                              Review
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 6: DISTRIBUTION DRIFT */}
      {/* ========================================================================= */}
      {activeTab === 'drift' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Historical Distribution Drift Analysis</h3>
            <p className="text-xs text-slate-500">
              Evaluates Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov statistics against baseline
            </p>
          </div>

          {!driftSummary || !driftSummary.drift_available ? (
            <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500">
              <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="font-semibold text-slate-700">Distribution Drift Comparison Unavailable</p>
              <p className="mt-1 max-w-md mx-auto">
                Drift detection requires at least two completed monitoring runs to compare the baseline snapshot with the current dataset. Execute a second monitor run after updating records to populate drift metrics.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800">
                <span className="font-semibold">Drift Summary: </span>
                {driftSummary.summary}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {driftSummary.metrics.map((m) => (
                  <div
                    key={m.column_name}
                    className={`p-4 rounded-xl border space-y-2 ${
                      m.drift_detected ? 'bg-amber-50/50 border-amber-200' : 'bg-white border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-slate-900">{m.column_name}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          m.drift_detected ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {m.drift_detected ? 'Drift Detected' : 'Stable'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-bold">PSI Score:</span>
                        <div className="font-mono font-bold text-slate-800">{m.metric_value.toFixed(4)}</div>
                      </div>
                      {m.p_value !== null && m.p_value !== undefined && (
                        <div>
                          <span className="text-slate-400 text-[10px] uppercase font-bold">KS p-value:</span>
                          <div className="font-mono font-bold text-slate-800">{m.p_value.toFixed(5)}</div>
                        </div>
                      )}
                    </div>

                    <p className="text-[11px] text-slate-600 pt-1 border-t border-slate-100">{m.interpretation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 7: FRESHNESS & SLA */}
      {/* ========================================================================= */}
      {activeTab === 'freshness' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Data Freshness & Source SLA Monitoring</h3>
            <p className="text-xs text-slate-500">Track publisher release cadence, source availability, and overdue states</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <span className="text-[10px] uppercase font-bold text-slate-400">Publication Cadence</span>
              <div className="text-lg font-bold text-slate-900 uppercase mt-1">{dataset.update_cadence}</div>
              <p className="text-[11px] text-slate-500 mt-1">Configured expected update cycle</p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <span className="text-[10px] uppercase font-bold text-slate-400">Last Content Update</span>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {dataset.last_content_change_at
                  ? new Date(dataset.last_content_change_at).toLocaleDateString()
                  : 'Initial Run'}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">SHA256 fingerprint verified</p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <span className="text-[10px] uppercase font-bold text-slate-400">Source Health</span>
              <div className="text-lg font-bold text-emerald-600 mt-1">Operational</div>
              <p className="text-[11px] text-slate-500 mt-1">Latest fetch completed without HTTP errors</p>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 8: RUN HISTORY & RUN DIFF */}
      {/* ========================================================================= */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Historical Monitoring Runs</h3>
                <p className="text-xs text-slate-500">Chronological execution record and run-to-run diff comparison</p>
              </div>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs divide-y divide-slate-200">
                <thead className="bg-slate-50 text-slate-700 font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Run ID</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Execution Time</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Quality Score</th>
                    <th className="py-2.5 px-3">Row Count</th>
                    <th className="py-2.5 px-3 text-right">Run Comparison</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                  {runs.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3 font-bold text-slate-900">{r.id.substring(0, 8)}...</td>
                      <td className="py-2.5 px-3 uppercase text-[10px] font-bold text-slate-600">{r.run_type}</td>
                      <td className="py-2.5 px-3 font-sans text-slate-500">
                        {new Date(r.started_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 font-sans">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            r.status === 'success'
                              ? 'bg-emerald-50 text-emerald-800'
                              : 'bg-amber-50 text-amber-800'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-slate-900">{r.quality_score}%</td>
                      <td className="py-2.5 px-3 text-slate-600">{r.row_count}</td>
                      <td className="py-2.5 px-3 text-right font-sans">
                        <button
                          onClick={() => handleSelectRunForDiff(r)}
                          className="px-2.5 py-1 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-[11px]"
                        >
                          Compare with Prior
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Run Comparison Diff View */}
          {selectedRunForDiff && runDiffData && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4 animate-in fade-in">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2">
                  <GitCompare className="w-5 h-5 text-teal-600" />
                  <h4 className="text-sm font-bold text-slate-900">
                    Run Comparison: {selectedRunForDiff.id.substring(0, 8)} vs Prior
                  </h4>
                </div>
                <button
                  onClick={() => {
                    setSelectedRunForDiff(null);
                    setRunDiffData(null);
                  }}
                  className="text-xs text-slate-400 hover:text-slate-700 font-semibold"
                >
                  Close Diff
                </button>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 text-xs text-slate-800 border border-slate-200">
                <span className="font-semibold">Diff Summary: </span>
                {runDiffData.summary}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold uppercase text-slate-400">Score Delta</span>
                  <div
                    className={`text-lg font-bold font-mono mt-0.5 ${
                      runDiffData.quality_score_change >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {runDiffData.quality_score_change > 0 ? `+${runDiffData.quality_score_change}` : runDiffData.quality_score_change} pts
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold uppercase text-slate-400">Row Delta</span>
                  <div className="text-lg font-bold font-mono text-slate-800 mt-0.5">
                    {runDiffData.row_count_change > 0 ? `+${runDiffData.row_count_change}` : runDiffData.row_count_change}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold uppercase text-slate-400">New Failures</span>
                  <div className="text-lg font-bold font-mono text-rose-600 mt-0.5">
                    {runDiffData.new_failures.length}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold uppercase text-slate-400">Resolved Failures</span>
                  <div className="text-lg font-bold font-mono text-emerald-600 mt-0.5">
                    {runDiffData.resolved_failures.length}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Acknowledge Anomaly Modal */}
      <AcknowledgeModal
        anomaly={selectedAnomaly}
        datasetId={datasetId}
        onClose={() => setSelectedAnomaly(null)}
        onSuccess={() => {
          api.getAnomalies(datasetId).then(setAnomalies);
        }}
      />
    </div>
  );
};
