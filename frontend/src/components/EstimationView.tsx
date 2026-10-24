import React, { useState } from 'react';
import {
  Calculator,
  Clock,
  DollarSign,
  TrendingUp,
  AlertCircle,
  Sparkles,
  GitCommit,
  CheckCircle2,
  Layers,
} from 'lucide-react';
import { ProjectEstimate } from '../types/estimation';
import { api } from '../services/api';

interface EstimationViewProps {
  estimate: ProjectEstimate | null;
  projectId: string;
  onRefresh: () => void;
}

export const EstimationView: React.FC<EstimationViewProps> = ({
  estimate,
  projectId,
  onRefresh,
}) => {
  const [contingencyPct, setContingencyPct] = useState<number>(
    estimate?.contingency_pct || 15.0
  );
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const handleRecalculate = async () => {
    setIsCalculating(true);
    setErrorMsg('');
    try {
      await api.calculateEstimate(projectId, contingencyPct);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to calculate deterministic estimate');
    } finally {
      setIsCalculating(false);
    }
  };

  const currencySymbol = (curr: string) => {
    switch (curr) {
      case 'USD':
        return '$';
      case 'EUR':
        return '€';
      case 'GBP':
        return '£';
      default:
        return '$';
    }
  };

  const sym = currencySymbol(estimate?.currency || 'USD');

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 5 &bull; Deterministic Estimation Engine
            </span>
            <span className="text-xs text-slate-400">
              Rate Card {estimate?.rate_card_version || '2026.Q1'}
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Effort, Cost & CPM Schedule Estimation
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Calculated using three-point PERT effort modeling, role rate cards, and Critical Path Method (CPM) dependency network analysis. Zero unreviewable AI calculations.
          </p>
        </div>

        {/* Action & Contingency Config */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-2 rounded-lg border border-slate-800">
            <label className="text-xs text-slate-400 font-medium">Contingency:</label>
            <input
              type="number"
              min="0"
              max="50"
              step="1"
              value={contingencyPct}
              onChange={(e) => setContingencyPct(parseFloat(e.target.value) || 0)}
              className="w-14 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white text-right focus:outline-none focus:border-indigo-500"
            />
            <span className="text-xs text-slate-400">%</span>
          </div>

          <button
            onClick={handleRecalculate}
            disabled={isCalculating || !projectId}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Calculator className={`h-4 w-4 ${isCalculating ? 'animate-spin' : ''}`} />
            <span>{isCalculating ? 'Calculating...' : 'Recalculate Estimate'}</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {!estimate ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
          <Calculator className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No Estimate Computed Yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Generate your Work Breakdown Structure first, then trigger the deterministic estimation engine to calculate PERT hours, CPM duration, and role costs.
          </p>
          <button
            onClick={handleRecalculate}
            disabled={isCalculating || !projectId}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition"
          >
            Compute Project Estimate
          </button>
        </div>
      ) : (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Total PERT Effort</span>
                <Clock className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {estimate.total_pert_hours.toLocaleString()}
                </span>
                <span className="text-xs text-slate-400 font-medium">hours</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Formula: (O + 4M + P) / 6
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">CPM Schedule Duration</span>
                <TrendingUp className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {estimate.estimated_duration_days}
                </span>
                <span className="text-xs text-slate-400 font-medium">business days</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                ~{(estimate.estimated_duration_days / 5).toFixed(1)} calendar weeks
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Base Labor Cost</span>
                <DollarSign className="h-4 w-4 text-blue-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-white">
                  {sym}{estimate.total_labor_cost.toLocaleString()}
                </span>
                <span className="text-xs text-slate-400 font-medium">{estimate.currency}</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                Across {Object.keys(estimate.role_breakdown || {}).length} roles
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 bg-gradient-to-br from-slate-900 to-indigo-950/40">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Total Cost (+Contingency)</span>
                <Sparkles className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-indigo-300">
                  {sym}{estimate.total_cost.toLocaleString()}
                </span>
                <span className="text-xs text-slate-400 font-medium">{estimate.currency}</span>
              </div>
              <p className="text-[11px] text-indigo-400/80 mt-2">
                Includes +{sym}{estimate.contingency_cost.toLocaleString()} ({estimate.contingency_pct}% buffer)
              </p>
            </div>
          </div>

          {/* Critical Path Tasks */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <GitCommit className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Critical Path Sequence</h3>
              </div>
              <span className="text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 px-2.5 py-0.5 rounded-full font-medium">
                Zero Slack &bull; Delaying any task delays delivery
              </span>
            </div>

            {estimate.critical_path_tasks && estimate.critical_path_tasks.length > 0 ? (
              <div className="flex flex-wrap items-center gap-2 p-4 bg-slate-950 rounded-lg border border-slate-800">
                {estimate.critical_path_tasks.map((taskCode, idx) => (
                  <React.Fragment key={taskCode}>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-mono text-xs font-semibold">
                      <span>{taskCode}</span>
                    </div>
                    {idx < estimate.critical_path_tasks.length - 1 && (
                      <span className="text-slate-600 font-bold">&rarr;</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-4 bg-slate-950 rounded-lg border border-slate-800">
                No dependencies registered yet. Add dependencies in the WBS tab to calculate the critical path.
              </p>
            )}
          </div>

          {/* Role Effort & Cost Breakdown Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Role Effort & Cost Allocation</h3>
              </div>
              <span className="text-xs text-slate-400">
                Approved Rate Card Version {estimate.rate_card_version}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Role Required</th>
                    <th className="py-3 px-4 text-right">Standard Rate</th>
                    <th className="py-3 px-4 text-right">PERT Effort</th>
                    <th className="py-3 px-4 text-right">Role Cost</th>
                    <th className="py-3 px-4 text-right">% of Total Effort</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {Object.entries(estimate.role_breakdown || {}).map(([roleName, data]) => {
                    const pct = estimate.total_pert_hours > 0
                      ? ((data.hours / estimate.total_pert_hours) * 100).toFixed(1)
                      : '0.0';
                    return (
                      <tr key={roleName} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3.5 px-4 font-medium text-white flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-indigo-400" />
                          <span>{roleName}</span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-slate-400">
                          {sym}{data.rate.toFixed(2)}/hr
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-slate-200">
                          {data.hours.toFixed(1)} hrs
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-semibold text-white">
                          {sym}{data.cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="inline-flex items-center gap-2">
                            <span className="text-slate-400 font-mono">{pct}%</span>
                            <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-500 rounded-full"
                                style={{ width: `${Math.min(parseFloat(pct), 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
