import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileWarning,
  ShieldCheck,
  Cpu,
  Calculator,
} from 'lucide-react';
import { FeasibilityOverview, ProjectRisk } from '../types/risk';
import { api } from '../services/api';

interface RisksViewProps {
  overview: FeasibilityOverview | null;
  projectId: string;
  hasApprovedBaseline?: boolean;
  isBaselineLoading?: boolean;
  onRefresh: () => void;
}

export const RisksView: React.FC<RisksViewProps> = ({
  overview,
  projectId,
  hasApprovedBaseline = true,
  isBaselineLoading = false,
  onRefresh,
}) => {
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [updatingRiskId, setUpdatingRiskId] = useState<string | null>(null);

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setErrorMsg('');
    try {
      await api.evaluateFeasibility(projectId);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to evaluate feasibility');
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleStatusChange = async (risk: ProjectRisk, newStatus: string) => {
    setUpdatingRiskId(risk.id);
    setErrorMsg('');
    try {
      await api.updateRiskItem(risk.id, { status: newStatus as any });
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update risk status');
    } finally {
      setUpdatingRiskId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'feasible':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            <span>Feasible</span>
          </span>
        );
      case 'caution':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-3 w-3" />
            <span>Caution</span>
          </span>
        );
      case 'infeasible':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3 w-3" />
            <span>Infeasible</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {status}
          </span>
        );
    }
  };

  const getRiskLevelBadge = (level: string) => {
    switch (level) {
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
            Critical
          </span>
        );
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
            High
          </span>
        );
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
            Medium
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium uppercase bg-slate-800 text-slate-300 border border-slate-700">
            Low
          </span>
        );
    }
  };

  const dimensionLabels: Record<string, string> = {
    schedule: 'Schedule Feasibility',
    budget: 'Budget & Cost Feasibility',
    skills_capacity: 'Skills & Capacity',
    technical_dependencies: 'Technical Dependencies',
    scope_complexity: 'Scope Complexity',
    data_completeness: 'Data Completeness',
    operational_security: 'Operational & Security Risks',
  };

  const risks = overview?.risks || [];
  const filteredRisks = selectedCategory === 'all'
    ? risks
    : risks.filter((r) => r.category.toLowerCase() === selectedCategory.toLowerCase());

  const categories = Array.from(new Set(risks.map((r) => r.category)));
  const canEvaluate = Boolean(projectId && hasApprovedBaseline && !isBaselineLoading && !isEvaluating);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 6 &bull; Feasibility & Risk Intelligence
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            7-Dimension Feasibility & $L \times I$ Risk Register
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Evaluate deliverability across schedule, budget, capacity, dependencies, complexity, data, and security. Documented formulas with transparent evidence.
          </p>
        </div>

        <button
          onClick={handleEvaluate}
          disabled={!canEvaluate}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
        >
          <ShieldAlert className={`h-4 w-4 ${isEvaluating ? 'animate-spin' : ''}`} />
          <span>{isEvaluating ? 'Evaluating...' : 'Run Feasibility Audit'}</span>
        </button>
      </div>

      {!hasApprovedBaseline && !isBaselineLoading && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-center gap-3 text-amber-300 text-xs">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>An approved requirements baseline is required. Review and approve the requirements draft first.</span>
        </div>
      )}

      {errorMsg && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-center gap-3 text-rose-300 text-xs">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {!overview || overview.overall_status === 'pending_baseline' ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
          <ShieldAlert className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No Feasibility Assessment on Record</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            {hasApprovedBaseline
              ? 'Click Run Feasibility Audit to analyze baseline requirements, estimates, and project dependencies across the 7 delivery dimensions.'
              : 'An approved requirements baseline is required before feasibility and risk evaluation can run.'}
          </p>
          <button
            onClick={handleEvaluate}
            disabled={!canEvaluate}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition cursor-pointer disabled:cursor-not-allowed"
          >
            Run Feasibility Audit
          </button>
        </div>
      ) : (
        <>
          {/* Executive Feasibility Overview Banner */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <ShieldCheck className="h-6 w-6 text-indigo-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">Overall Project Feasibility</h3>
                    {getStatusBadge(overview.overall_status)}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{overview.summary}</p>
                </div>
              </div>

              <div className="flex items-baseline gap-2 bg-slate-950 px-4 py-3 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400 font-medium">Composite Score:</span>
                <span className="text-2xl font-bold text-white">{overview.overall_score}</span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
            </div>

            {/* Limitations Notice */}
            {overview.limitations && overview.limitations.length > 0 && (
              <div className="mt-4 p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold mb-1.5">
                  <FileWarning className="h-4 w-4" />
                  <span>Identified Project Limitations & Unknowns</span>
                </div>
                <ul className="list-disc list-inside text-xs text-amber-200/90 space-y-1">
                  {overview.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 7 Dimensions Grid */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>7 Delivery Feasibility Dimensions</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(overview.dimensions || {}).map(([dimKey, dimData]) => (
                <div
                  key={dimKey}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-white">
                        {dimensionLabels[dimKey] || dimKey}
                      </span>
                      {getStatusBadge(dimData.status)}
                    </div>
                    <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                      {dimData.notes}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span className="text-slate-500">Confidence Score</span>
                    <span className="font-mono font-bold text-slate-200">
                      {dimData.score} / 100
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Register Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Project Risk Register</h3>
                <span className="text-xs text-slate-400 font-mono">
                  ({filteredRisks.length} entries &bull; Score = Likelihood &times; Impact)
                </span>
              </div>

              {/* Category Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Filter:</span>
                <select
                  aria-label="Filter risks by category"
                  data-testid="risk-category-filter"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="all">All Categories ({risks.length})</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Code & Source</th>
                    <th className="py-3 px-4">Risk Title & Details</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-center">Likelihood</th>
                    <th className="py-3 px-4 text-center">Impact</th>
                    <th className="py-3 px-4 text-center">Score</th>
                    <th className="py-3 px-4 text-center">Level</th>
                    <th className="py-3 px-4">Mitigation Strategy</th>
                    <th className="py-3 px-4">Owner</th>
                    <th className="py-3 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {filteredRisks.map((risk) => {
                    const isAi = risk.source === 'ai_extracted' || Boolean(risk.supporting_evidence && risk.supporting_evidence.includes('[AI-Extracted'));
                    return (
                      <tr key={risk.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <div className="flex flex-col gap-1 items-start">
                            <span className="font-mono font-bold text-indigo-400">{risk.risk_code}</span>
                            {isAi ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/25">
                                <Cpu className="h-2.5 w-2.5" />
                                <span>AI Suggestion</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-sky-500/15 text-sky-300 border border-sky-500/25">
                                <Calculator className="h-2.5 w-2.5" />
                                <span>Deterministic</span>
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 max-w-sm">
                          <p className="font-semibold text-white">{risk.title}</p>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            {risk.description}
                          </p>
                          {risk.supporting_evidence && (
                            <div className="mt-2 p-2 rounded bg-slate-950/80 border border-slate-800/80 text-[11px] text-slate-400">
                              <span className="font-semibold text-slate-300">Evidence / Rationale: </span>
                              <span>{risk.supporting_evidence}</span>
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                          <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                            {risk.category}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold">
                          {risk.likelihood} / 5
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold">
                          {risk.impact} / 5
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold text-white">
                          <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                            {risk.risk_score}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center whitespace-nowrap">
                          {getRiskLevelBadge(risk.risk_level)}
                        </td>
                        <td className="py-3.5 px-4 max-w-xs text-[11px] text-slate-300">
                          {risk.mitigation_strategy || (
                            <span className="text-slate-500 italic">No mitigation logged</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap text-[11px]">
                          {risk.risk_owner || 'Project Lead'}
                        </td>
                        <td className="py-3.5 px-4 text-center whitespace-nowrap">
                          <select
                            value={risk.status}
                            disabled={updatingRiskId === risk.id}
                            onChange={(e) => handleStatusChange(risk, e.target.value)}
                            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer disabled:opacity-50"
                          >
                            <option value="identified">Identified</option>
                            <option value="mitigated">Mitigated</option>
                            <option value="accepted">Accepted</option>
                            <option value="closed">Closed</option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                  {filteredRisks.length === 0 && (
                    <tr>
                      <td colSpan={10} className="py-8 text-center text-slate-500 italic">
                        No risks found for selected filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
