import React from 'react';
import { ShieldCheck, Database, BarChart3, PlusCircle, Activity, Sparkles } from 'lucide-react';

interface HeaderProps {
  currentTab: 'overview' | 'registry' | 'evaluation' | 'detail';
  setCurrentTab: (tab: 'overview' | 'registry' | 'evaluation') => void;
  onOpenRegister: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, setCurrentTab, onOpenRegister }) => {
  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Name */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setCurrentTab('overview')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-700 to-teal-500 flex items-center justify-center text-white shadow-md shadow-teal-500/20">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold tracking-tight text-slate-900 font-sans">OpenData Sentinel</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200">
                  Gov Monitor
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">Government Data Quality & Anomaly Detection Platform</p>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setCurrentTab('overview')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'overview'
                  ? 'bg-slate-100 text-teal-800 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Activity className="w-4 h-4 text-teal-600" />
              <span>Overview</span>
            </button>

            <button
              onClick={() => setCurrentTab('registry')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'registry' || currentTab === 'detail'
                  ? 'bg-slate-100 text-teal-800 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Database className="w-4 h-4 text-teal-600" />
              <span>Dataset Registry</span>
            </button>

            <button
              onClick={() => setCurrentTab('evaluation')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'evaluation'
                  ? 'bg-slate-100 text-teal-800 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <BarChart3 className="w-4 h-4 text-teal-600" />
              <span>ML & Benchmarks</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                Ground Truth
              </span>
            </button>
          </nav>

          {/* Action Button & Live Status */}
          <div className="flex items-center space-x-3">
            <div className="hidden lg:flex items-center space-x-2 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Pipeline Active</span>
            </div>

            <button
              onClick={onOpenRegister}
              className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium shadow-xs transition-colors focus:ring-2 focus:ring-teal-500 focus:ring-offset-1"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Register Dataset</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
