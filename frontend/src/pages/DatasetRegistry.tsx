import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  PlusCircle,
  ExternalLink,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Trash2,
  Sparkles,
  FileSpreadsheet,
} from 'lucide-react';
import { Dataset } from '../types';
import { api } from '../services/api';

interface DatasetRegistryProps {
  onSelectDataset: (id: string) => void;
  onOpenRegister: () => void;
}

export const DatasetRegistry: React.FC<DatasetRegistryProps> = ({
  onSelectDataset,
  onOpenRegister,
}) => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formatFilter, setFormatFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [monitoringId, setMonitoringId] = useState<string | null>(null);

  const loadDatasets = async () => {
    try {
      const data = await api.getDatasets(search, statusFilter);
      setDatasets(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, [search, statusFilter]);

  const handleRunMonitor = async (e: React.MouseEvent, datasetId: string) => {
    e.stopPropagation();
    setMonitoringId(datasetId);
    try {
      await api.runMonitor(datasetId);
      await loadDatasets();
    } catch (err) {
      alert('Monitoring run failed: ' + err);
    } finally {
      setMonitoringId(null);
    }
  };

  const handleDelete = async (e: React.MouseEvent, datasetId: string, name: string) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete dataset "${name}" and all historical monitoring logs?`)) {
      try {
        await api.deleteDataset(datasetId);
        loadDatasets();
      } catch (err) {
        alert('Failed to delete dataset');
      }
    }
  };

  const filteredDatasets = datasets.filter((d) => {
    if (formatFilter !== 'all' && d.data_format !== formatFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header and Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Dataset Registry & Watchtower</h1>
          <p className="text-xs text-slate-500 mt-1">
            Catalog of tracked Indian Government datasets, scheduled audits, and health indicators
          </p>
        </div>
        <button
          onClick={onOpenRegister}
          className="px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Register Dataset</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by dataset title or publisher..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center space-x-1.5 text-xs text-slate-600">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
            >
              <option value="all">All Health States</option>
              <option value="healthy">Healthy (Score ≥ 80)</option>
              <option value="warning">Warning (Score 60-79)</option>
              <option value="critical">Critical (Score &lt; 60)</option>
            </select>
          </div>

          {/* Format Filter */}
          <select
            value={formatFilter}
            onChange={(e) => setFormatFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
          >
            <option value="all">All Formats</option>
            <option value="csv">CSV Format</option>
            <option value="json">JSON Format</option>
          </select>

          <button
            onClick={loadDatasets}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600"
            title="Reload Registry"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Dataset Cards List */}
      {isLoading ? (
        <div className="text-center py-12 text-slate-400 text-xs">Loading datasets...</div>
      ) : filteredDatasets.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <FileSpreadsheet className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No datasets found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search terms or register a new dataset or load bundled government presets.
          </p>
          <button
            onClick={async () => {
              setIsLoading(true);
              await api.loadAllSamples();
              loadDatasets();
            }}
            className="mt-4 px-4 py-2 rounded-xl bg-teal-600 text-white text-xs font-semibold shadow-xs inline-flex items-center space-x-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Load Bundled Indian Gov Datasets</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5">
          {filteredDatasets.map((d) => (
            <div
              key={d.id}
              onClick={() => onSelectDataset(d.id)}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-teal-500/80 hover:shadow-md transition-all cursor-pointer flex flex-col md:flex-row md:items-center md:justify-between gap-4"
            >
              {/* Left Column: Title & Metadata */}
              <div className="space-y-1.5 max-w-2xl">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-slate-900 hover:text-teal-700 transition-colors">
                    {d.name}
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                    {d.data_format}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-50 text-teal-800 border border-teal-200">
                    {d.update_cadence}
                  </span>
                </div>

                <p className="text-xs text-slate-500 line-clamp-1">
                  {d.description || 'Continuous monitoring active.'}
                </p>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-400 font-medium">
                  <span>Publisher: <strong className="text-slate-600">{d.publisher}</strong></span>
                  <span>Dimensions: <strong className="text-slate-600">{d.row_count} rows × {d.column_count} cols</strong></span>
                  <span>
                    Last Ingested: <strong className="text-slate-600">
                      {d.last_ingested_at ? new Date(d.last_ingested_at).toLocaleDateString() : 'Pending'}
                    </strong>
                  </span>
                </div>
              </div>

              {/* Right Column: Status, Score, Actions */}
              <div className="flex items-center space-x-3 self-end md:self-auto shrink-0">
                {/* Quality Score Badge */}
                <div className="text-right">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Quality Score</div>
                  <div
                    className={`text-xl font-bold font-mono ${
                      (d.latest_quality_score || 0) >= 80
                        ? 'text-emerald-600'
                        : (d.latest_quality_score || 0) >= 60
                        ? 'text-amber-600'
                        : 'text-rose-600'
                    }`}
                  >
                    {d.latest_quality_score !== null && d.latest_quality_score !== undefined
                      ? `${d.latest_quality_score}%`
                      : 'N/A'}
                  </div>
                </div>

                {/* Status Indicator */}
                <div className="w-24 text-center">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      d.status === 'healthy'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : d.status === 'warning'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {d.status === 'healthy' && <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-500" />}
                    {d.status === 'warning' && <AlertTriangle className="w-3 h-3 mr-1 text-amber-500" />}
                    {d.status === 'critical' && <XCircle className="w-3 h-3 mr-1 text-rose-500" />}
                    {d.status}
                  </span>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-1.5 pl-2 border-l border-slate-200">
                  <button
                    onClick={(e) => handleRunMonitor(e, d.id)}
                    disabled={monitoringId === d.id}
                    className="p-2 rounded-xl bg-slate-100 hover:bg-teal-50 hover:text-teal-700 text-slate-600 transition-colors"
                    title="Execute Live Sentinel Check"
                  >
                    <Play className={`w-3.5 h-3.5 ${monitoringId === d.id ? 'animate-spin text-teal-600' : ''}`} />
                  </button>

                  <button
                    onClick={(e) => handleDelete(e, d.id, d.name)}
                    className="p-2 rounded-xl hover:bg-rose-50 hover:text-rose-600 text-slate-400 transition-colors"
                    title="Delete Dataset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
