import React, { useState } from 'react';
import { X, CheckCircle, AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';
import { AnomalyFinding } from '../types';
import { api } from '../services/api';

interface AcknowledgeModalProps {
  anomaly: AnomalyFinding | null;
  datasetId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const AcknowledgeModal: React.FC<AcknowledgeModalProps> = ({
  anomaly,
  datasetId,
  onClose,
  onSuccess,
}) => {
  const [notes, setNotes] = useState('');
  const [isFalsePositive, setIsFalsePositive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  if (!anomaly) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.acknowledgeAnomaly(datasetId, anomaly.id, notes, isFalsePositive);
      onSuccess();
      onClose();
    } catch (err) {
      alert('Failed to acknowledge anomaly');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden transform transition-all animate-in fade-in zoom-in-95">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Review Anomaly Observation</h3>
            <p className="text-xs text-slate-500">Record analyst review & investigation notes</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Target Field:</span>
              <span className="font-mono font-bold text-slate-900">{anomaly.column_name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Observed Value:</span>
              <span className="font-mono font-bold text-amber-700">{anomaly.value}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Detection Method:</span>
              <span className="uppercase text-[11px] font-bold text-teal-800">{anomaly.detection_method}</span>
            </div>
            <div className="text-slate-600 pt-1 text-[11px] border-t border-slate-200 mt-1">
              <span className="font-semibold">Explanation: </span>
              {anomaly.explanation}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700">Review Classification</label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label
                className={`p-3 rounded-xl border cursor-pointer flex items-center space-x-2 transition-all ${
                  !isFalsePositive
                    ? 'border-teal-500 bg-teal-50/50 text-teal-900 font-medium'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="review_type"
                  checked={!isFalsePositive}
                  onChange={() => setIsFalsePositive(false)}
                  className="text-teal-600 focus:ring-teal-500"
                />
                <span>Acknowledge (Valid Outlier)</span>
              </label>

              <label
                className={`p-3 rounded-xl border cursor-pointer flex items-center space-x-2 transition-all ${
                  isFalsePositive
                    ? 'border-indigo-500 bg-indigo-50/50 text-indigo-900 font-medium'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="review_type"
                  checked={isFalsePositive}
                  onChange={() => setIsFalsePositive(true)}
                  className="text-indigo-600 focus:ring-indigo-500"
                />
                <span>Mark as False Positive</span>
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Investigation Notes & Rationale</label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Verified with Lasalgaon mandi arrivals; extreme modal price corresponds to seasonal festival demand spike, not recording error."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
            />
          </div>

          <div className="p-2.5 rounded-lg bg-teal-50/70 border border-teal-200/60 text-[11px] text-teal-900 flex items-start space-x-2">
            <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
            <p>
              Decision Support Guarantee: Acknowledging observations updates monitoring review status and does not alter, truncate, or overwrite raw dataset records.
            </p>
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold flex items-center space-x-1.5"
            >
              {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Save Review</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
