import React, { useState } from 'react';
import {
  FileDown,
  FileText,
  Download,
  CheckCircle2,
  AlertCircle,
  Layers,
} from 'lucide-react';
import { ProjectReportSummary } from '../types/report';
import { api } from '../services/api';

interface ReportsViewProps {
  reports: ProjectReportSummary[];
  projectId: string;
  onRefresh: () => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  reports,
  projectId,
  onRefresh,
}) => {
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [latestReport, setLatestReport] = useState<ProjectReportSummary | null>(null);

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    setErrorMsg('');
    setSuccessMsg('');
    setLatestReport(null);
    try {
      const generated = await api.generateReport(projectId);
      setLatestReport(generated);
      setSuccessMsg('Executive Project Delivery PDF Report generated successfully.');
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate PDF report');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (report: ProjectReportSummary) => {
    setDownloadingId(report.id);
    setErrorMsg('');
    try {
      const safeTitle = (report.title || 'Project_Delivery_Report')
        .replace(/[^a-zA-Z0-9_\-\.]/g, '_');
      const filename = `${safeTitle}.pdf`;
      await api.downloadReportBlob(report.id, filename);
    } catch (err: any) {
      // Fallback to direct URL window opening if blob fetch fails
      window.open(api.getReportDownloadUrl(report.id), '_blank');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 12 &bull; Professional PDF Reporting
            </span>
            <span className="text-xs text-slate-400">
              Executive Project Delivery Book
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Executive Project Delivery Book & PDF Generation
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Compile the complete, approved project state into an executive delivery report. Includes requirements baseline, PERT estimates, CPM schedule, feasibility audit, risk register, and workforce plan.
          </p>
        </div>

        <button
          onClick={handleGenerateReport}
          disabled={isGenerating || !projectId}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all"
        >
          <FileDown className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
          <span>{isGenerating ? 'Compiling PDF...' : 'Generate PDF Report'}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-emerald-300 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
          {latestReport && (
            <button
              onClick={() => handleDownload(latestReport)}
              disabled={downloadingId === latestReport.id}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-sm transition disabled:opacity-50"
            >
              <Download className={`h-3.5 w-3.5 ${downloadingId === latestReport.id ? 'animate-bounce' : ''}`} />
              <span>{downloadingId === latestReport.id ? 'Downloading...' : 'Download PDF'}</span>
            </button>
          )}
        </div>
      )}

      {/* Report Specification Highlight Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <Layers className="h-4 w-4 text-indigo-400" />
          <span>Report Specification & Included Sections</span>
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">1. Executive Summary & Scope</span>
            <p className="text-slate-400 text-[11px] mt-1">Project metadata, objectives, and baseline version.</p>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">2. Approved Requirements Baseline</span>
            <p className="text-slate-400 text-[11px] mt-1">Audited requirements with source document references.</p>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">3. Work Breakdown Structure</span>
            <p className="text-slate-400 text-[11px] mt-1">Full task hierarchy, dependencies, and roles.</p>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">4. Effort, Cost & CPM Schedule</span>
            <p className="text-slate-400 text-[11px] mt-1">PERT calculations, critical path, and role cost tables.</p>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">5. Feasibility & Risk Register</span>
            <p className="text-slate-400 text-[11px] mt-1">7-dimension score and L &times; I risk matrix with mitigations.</p>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200">6. Workforce & Delivery Analytics</span>
            <p className="text-slate-400 text-[11px] mt-1">Approved team assignments and delivery intelligence.</p>
          </div>
        </div>
      </div>

      {/* Generated Reports Vault Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Generated Report Vault</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {reports.length} reports archived
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Report Title</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4 text-center">Baseline Version</th>
                <th className="py-3 px-4 text-right">File Size</th>
                <th className="py-3 px-4">Generated By</th>
                <th className="py-3 px-4 text-right">Generated Date</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {reports.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-white flex items-center gap-2">
                    <FileText className="h-4 w-4 text-rose-400 shrink-0" />
                    <span>{r.title}</span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                      {r.report_type}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-center font-mono font-bold text-indigo-400">
                    v{r.baseline_version}
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-slate-400">
                    {(r.file_size_bytes / 1024).toFixed(1)} KB
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {r.generated_by}
                  </td>
                  <td className="py-3.5 px-4 text-right text-slate-500 font-mono">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <button
                      onClick={() => handleDownload(r)}
                      disabled={downloadingId === r.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 transition text-xs font-semibold disabled:opacity-50"
                    >
                      <Download className={`h-3.5 w-3.5 ${downloadingId === r.id ? 'animate-bounce' : ''}`} />
                      <span>{downloadingId === r.id ? 'Downloading...' : 'Download PDF'}</span>
                    </button>
                  </td>
                </tr>
              ))}
              {reports.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 italic">
                    No reports generated yet for this project.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
