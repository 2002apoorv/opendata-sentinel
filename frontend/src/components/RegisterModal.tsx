import React, { useState, useEffect } from 'react';
import { X, Globe, UploadCloud, Sparkles, AlertCircle, CheckCircle, ShieldAlert, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface RegisterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (datasetId: string) => void;
}

export const RegisterModal: React.FC<RegisterModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState<'url' | 'upload' | 'sample'>('sample');
  const [samples, setSamples] = useState<any[]>([]);
  const [selectedSample, setSelectedSample] = useState<any | null>(null);

  // Form states
  const [name, setName] = useState('');
  const [publisher, setPublisher] = useState('');
  const [description, setDescription] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [dataFormat, setDataFormat] = useState<'csv' | 'json'>('csv');
  const [updateCadence, setUpdateCadence] = useState('daily');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.getSamples().then((data) => {
        setSamples(data);
        if (data.length > 0 && !selectedSample) {
          selectSamplePreset(data[0]);
        }
      }).catch(() => {});
    }
  }, [isOpen]);

  const selectSamplePreset = (sample: any) => {
    setSelectedSample(sample);
    setName(sample.name);
    setPublisher(sample.publisher);
    setDescription(sample.description);
    setDataFormat(sample.format);
    setUpdateCadence(sample.update_cadence || 'daily');
    setSourceUrl(sample.filename);
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    try {
      if (activeTab === 'upload') {
        if (!uploadedFile) {
          throw new Error('Please select a CSV or JSON file to upload.');
        }
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('name', name);
        formData.append('publisher', publisher);
        formData.append('description', description);
        formData.append('data_format', dataFormat);
        formData.append('update_cadence', updateCadence);

        const dataset = await api.uploadDataset(formData);
        onSuccess(dataset.id);
        onClose();
      } else {
        const payload = {
          name,
          publisher,
          description,
          source_url: activeTab === 'sample' && selectedSample ? selectedSample.filename : sourceUrl,
          source_type: activeTab,
          data_format: dataFormat,
          update_cadence: updateCadence,
        };

        const dataset = await api.registerDataset(payload);
        onSuccess(dataset.id);
        onClose();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden transform transition-all animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div>
            <h3 className="text-base font-bold text-slate-900">Register Dataset for Sentinel Monitoring</h3>
            <p className="text-xs text-slate-500">Ingest, fingerprint, and establish baseline quality metrics</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Source Mode Tabs */}
        <div className="grid grid-cols-3 p-1.5 bg-slate-100/80 mx-6 mt-5 rounded-xl border border-slate-200 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('sample')}
            className={`py-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              activeTab === 'sample'
                ? 'bg-white text-teal-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            <span>Gov Presets (1-Click)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('url')}
            className={`py-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              activeTab === 'url'
                ? 'bg-white text-teal-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Globe className="w-3.5 h-3.5 text-teal-600" />
            <span>Public URL</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('upload')}
            className={`py-2 rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
              activeTab === 'upload'
                ? 'bg-white text-teal-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5 text-teal-600" />
            <span>File Upload</span>
          </button>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-2.5 text-rose-800 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Registration Rejected: </span>
              {errorMsg}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Preset Selector */}
          {activeTab === 'sample' && (
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">Select Indian Government Dataset</label>
              <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1">
                {samples.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => selectSamplePreset(s)}
                    className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                      selectedSample?.id === s.id
                        ? 'border-teal-500 bg-teal-50/40 ring-1 ring-teal-500'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">{s.name}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 uppercase">
                        {s.format}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{s.description}</p>
                    <div className="text-[10px] text-teal-700 font-medium mt-1">Publisher: {s.publisher}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* URL Input */}
          {activeTab === 'url' && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">Source Download URL (CSV / JSON)</label>
                <span className="inline-flex items-center space-x-1 text-[11px] text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  <ShieldAlert className="w-3 h-3" />
                  <span>SSRF Guard Active</span>
                </span>
              </div>
              <input
                type="url"
                required
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://data.gov.in/sites/default/files/agri_mandi_arrivals.csv"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
              <p className="text-[11px] text-slate-400">
                Only public http/https endpoints permitted. Localhost, RFC1918 private IPs, and cloud metadata destinations are strictly rejected.
              </p>
            </div>
          )}

          {/* File Upload Input */}
          {activeTab === 'upload' && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Select File from Computer</label>
              <div className="border-2 border-dashed border-slate-200 rounded-xl p-5 text-center hover:border-teal-500 hover:bg-slate-50/50 transition-colors">
                <input
                  type="file"
                  id="file-upload"
                  accept=".csv,.json"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setUploadedFile(file);
                      if (!name) setName(file.name.replace(/\.[^/.]+$/, ''));
                      setDataFormat(file.name.endsWith('.json') ? 'json' : 'csv');
                    }
                  }}
                  className="hidden"
                />
                <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
                  <UploadCloud className="w-8 h-8 text-teal-600 mb-2" />
                  <span className="text-xs font-semibold text-slate-800">
                    {uploadedFile ? uploadedFile.name : 'Click to select or drag and drop CSV or JSON'}
                  </span>
                  <span className="text-[11px] text-slate-400 mt-1">Maximum upload size: 50 MB</span>
                </label>
              </div>
            </div>
          )}

          {/* Metadata Fields */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Dataset Title *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Daily Commodity Arrivals"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Publisher / Ministry *</label>
              <input
                type="text"
                required
                value={publisher}
                onChange={(e) => setPublisher(e.target.value)}
                placeholder="e.g. Ministry of Agriculture"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Expected Update Cadence</label>
              <select
                value={updateCadence}
                onChange={(e) => setUpdateCadence(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden bg-white"
              >
                <option value="daily">Daily Cadence</option>
                <option value="weekly">Weekly Cadence</option>
                <option value="monthly">Monthly Cadence</option>
                <option value="quarterly">Quarterly Cadence</option>
                <option value="unknown">Unknown Cadence</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Data Format</label>
              <select
                value={dataFormat}
                onChange={(e) => setDataFormat(e.target.value as 'csv' | 'json')}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden bg-white"
              >
                <option value="csv">CSV (Comma Separated)</option>
                <option value="json">JSON Array</option>
              </select>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !name || !publisher}
              className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-all flex items-center space-x-2"
            >
              {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{isLoading ? 'Ingesting & Monitoring...' : 'Register & Run Sentinel'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
