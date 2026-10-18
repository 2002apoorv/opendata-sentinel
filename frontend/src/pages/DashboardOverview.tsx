import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  TrendingUp,
  Activity,
  Layers,
  Sparkles,
  RefreshCw,
  FileText,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { DashboardSummary } from '../types';
import { api } from '../services/api';

interface DashboardOverviewProps {
  onSelectDataset: (id: string) => void;
  onNavigateRegistry: () => void;
  onOpenRegister: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  onSelectDataset,
  onNavigateRegistry,
  onOpenRegister,
}) => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchSummary = async () => {
    try {
      const data = await api.getDashboardSummary();
      setSummary(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchSummary();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="flex flex-col items-center space-y-3">
          <RefreshCw className="w-8 h-8 text-teal-600 animate-spin" />
          <p className="text-sm font-medium text-slate-500">Loading Sentinel monitoring status...</p>
        </div>
      </div>
    );
  }

  if (!summary || summary.total_datasets === 0) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center mx-auto mb-4">
          <Layers className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Welcome to OpenData Sentinel</h2>
        <p className="text-sm text-slate-500 max-w-md mx-auto mt-2">
          Monitor the reliability of open government datasets with automated completeness, validity, schema drift, and statistical anomaly detection.
        </p>
        <div className="mt-6 flex items-center justify-center space-x-3">
          <button
            onClick={onOpenRegister}
            className="px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold shadow-xs"
          >
            Register First Dataset
          </button>
          <button
            onClick={async () => {
              setIsLoading(true);
              await api.loadAllSamples();
              fetchSummary();
            }}
            className="px-4 py-2.5 rounded-xl bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold shadow-xs flex items-center space-x-2"
          >
            <Sparkles className="w-4 h-4 text-teal-600" />
            <span>Load Bundled Indian Gov Datasets</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Government Data Reliability Monitor</h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time automated auditing across registered public sector datasets
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNavigateRegistry}
            className="px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          >
            <span>View All Datasets</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Total Registered */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Datasets Tracked</span>
            <Layers className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{summary.total_datasets}</div>
          <div className="text-[11px] text-slate-400 mt-1">Ingested & monitored</div>
        </div>

        {/* Healthy */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Healthy</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-2">{summary.healthy_datasets}</div>
          <div className="text-[11px] text-emerald-600/80 font-medium mt-1">Quality score ≥ 80</div>
        </div>

        {/* Warnings */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Warnings</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-600 mt-2">{summary.warning_datasets}</div>
          <div className="text-[11px] text-amber-600/80 font-medium mt-1">Moderate anomalies</div>
        </div>

        {/* Critical */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Critical Failures</span>
            <XCircle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-600 mt-2">{summary.critical_datasets}</div>
          <div className="text-[11px] text-rose-600/80 font-medium mt-1">Requires manual audit</div>
        </div>

        {/* Sources Unavailable */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Overdue / Down</span>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-700 mt-2">{summary.unavailable_sources}</div>
          <div className="text-[11px] text-slate-400 mt-1">SLA cadence delay</div>
        </div>

        {/* Avg Quality Score */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Platform Quality</span>
            <TrendingUp className="w-4 h-4 text-teal-600" />
          </div>
          <div className="text-2xl font-bold text-teal-700 mt-2">{summary.average_quality_score}%</div>
          <div className="text-[11px] text-teal-600/80 font-medium mt-1">Across 6 dimensions</div>
        </div>
      </div>

      {/* Main Charts & Activity Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quality Score Trend History Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Historical Quality Score Trajectory</h2>
              <p className="text-xs text-slate-500">Multi-run quality scores across monitoring cycles</p>
            </div>
            <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200">
              Reliability Index
            </span>
          </div>

          <div className="h-64 w-full">
            {summary.quality_score_trends && summary.quality_score_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={summary.quality_score_trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0d9488" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#0d9488" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: '#64748b' }} stroke="#cbd5e1" />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#64748b' }} stroke="#cbd5e1" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', borderColor: '#e2e8f0', fontSize: '12px' }}
                    formatter={(val: any) => [`${val}/100`, 'Quality Score']}
                  />
                  <Area
                    type="monotone"
                    dataKey="quality_score"
                    stroke="#0d9488"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#scoreGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-xs text-slate-400">
                Execute additional monitoring runs to populate history chart
              </div>
            )}
          </div>
        </div>

        {/* Live Integrity Alerts & Schema Drift */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-900">Sentinel Alert Feed</h2>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Live In-App</span>
            </div>

            <div className="space-y-3">
              {summary.recent_schema_changes && summary.recent_schema_changes.length > 0 ? (
                summary.recent_schema_changes.map((al, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border text-xs flex items-start space-x-2.5 ${
                      al.severity === 'critical'
                        ? 'bg-rose-50/60 border-rose-200 text-rose-900'
                        : 'bg-amber-50/60 border-amber-200 text-amber-900'
                    }`}
                  >
                    {al.severity === 'critical' ? (
                      <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className="font-bold text-[11px]">{al.title}</div>
                      <p className="text-[11px] mt-0.5 opacity-90 line-clamp-2">{al.message}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-slate-400">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2 opacity-50" />
                  No open critical alerts or schema drift violations
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 text-center">
            <span className="text-[11px] text-slate-400 font-medium">
              SSRF Guard & Localized DB: Zero External Leakage
            </span>
          </div>
        </div>
      </div>

      {/* Recent Monitoring Runs & Recent Anomalies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Runs Table */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-slate-900">Recent Monitoring Runs</h2>
            <button
              onClick={onNavigateRegistry}
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 flex items-center space-x-1"
            >
              <span>Inspect All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Dataset</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Quality Score</th>
                  <th className="py-2.5 px-3">Records</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.recent_runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{r.dataset_name}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          r.status === 'success'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-800">
                      {r.quality_score !== null ? `${r.quality_score}%` : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">{r.row_count} rows</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => onSelectDataset(r.dataset_id)}
                        className="text-teal-600 hover:text-teal-800 font-semibold"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Anomaly Findings */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-slate-900">Recent Statistical Outliers Flagged</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                {summary.pending_anomalies_count} Pending
              </span>
            </div>
            <span className="text-[11px] text-slate-400">Explainable ML</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Column</th>
                  <th className="py-2.5 px-3">Observed Value</th>
                  <th className="py-2.5 px-3">Method</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3 text-right">Review</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.recent_anomalies.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-mono text-slate-800 font-medium">{a.column_name}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-amber-800">{a.value}</td>
                    <td className="py-2.5 px-3 uppercase text-[10px] font-bold text-teal-800">
                      {a.detection_method}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          a.severity === 'critical'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => onSelectDataset(a.dataset_id)}
                        className="text-teal-600 hover:text-teal-800 font-semibold"
                      >
                        Audit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
