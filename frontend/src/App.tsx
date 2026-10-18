import React, { useState } from 'react';
import { Header } from './components/Header';
import { DashboardOverview } from './pages/DashboardOverview';
import { DatasetRegistry } from './pages/DatasetRegistry';
import { DatasetDetail } from './pages/DatasetDetail';
import { EvaluationPage } from './pages/EvaluationPage';
import { RegisterModal } from './components/RegisterModal';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'overview' | 'registry' | 'evaluation' | 'detail'>('overview');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  const handleSelectDataset = (id: string) => {
    setSelectedDatasetId(id);
    setCurrentTab('detail');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToRegistry = () => {
    setSelectedDatasetId(null);
    setCurrentTab('registry');
  };

  const handleRegistrationSuccess = (datasetId: string) => {
    handleSelectDataset(datasetId);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans selection:bg-teal-500/20 selection:text-teal-900">
      {/* Platform Header */}
      <Header
        currentTab={currentTab}
        setCurrentTab={(tab) => {
          setSelectedDatasetId(null);
          setCurrentTab(tab);
        }}
        onOpenRegister={() => setIsRegisterOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {currentTab === 'overview' && (
          <DashboardOverview
            onSelectDataset={handleSelectDataset}
            onNavigateRegistry={() => setCurrentTab('registry')}
            onOpenRegister={() => setIsRegisterOpen(true)}
          />
        )}

        {currentTab === 'registry' && (
          <DatasetRegistry
            onSelectDataset={handleSelectDataset}
            onOpenRegister={() => setIsRegisterOpen(true)}
          />
        )}

        {currentTab === 'evaluation' && <EvaluationPage />}

        {currentTab === 'detail' && selectedDatasetId && (
          <DatasetDetail
            datasetId={selectedDatasetId}
            onBack={handleBackToRegistry}
          />
        )}
      </main>

      {/* Dataset Registration Modal */}
      <RegisterModal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onSuccess={handleRegistrationSuccess}
      />

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-800">OpenData Sentinel</span>
            <span>—</span>
            <span>AI-Powered Government Data Quality Monitoring & Anomaly Detection</span>
          </div>
          <div className="flex items-center space-x-4">
            <span>Local SQLite Engine</span>
            <span>•</span>
            <span>SSRF Protected</span>
            <span>•</span>
            <span>Empirical Ground-Truth Benchmarks</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
