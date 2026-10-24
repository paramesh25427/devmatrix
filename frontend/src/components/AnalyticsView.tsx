import React from 'react';
import {
  BarChart3,
  ShieldCheck,
  AlertTriangle,
  History,
  Info,
} from 'lucide-react';
import { DeliveryIntelligence, HistoricalSummary } from '../types/analytics';

interface AnalyticsViewProps {
  intelligence: DeliveryIntelligence | null;
  historical: HistoricalSummary | null;
  projectId?: string;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  intelligence,
  historical,
}) => {
  const hasSample = historical?.has_minimum_sample ?? false;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Modules 9 & 10 &bull; Delivery Intelligence & Calibration
            </span>
            <span className="text-xs text-slate-400">
              Fair Work-Related Signals
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Delivery Performance & Historical Learning Engine
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Inspect verified delivery variance and empirical calibration curves. Built on legitimate work records with minimum sample policies.
          </p>
        </div>
      </div>

      {/* Fair Metrics Policy Statement */}
      <div className="bg-slate-900 border border-indigo-500/30 rounded-xl p-5 bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900">
        <div className="flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
          <div className="space-y-1.5 text-xs">
            <h4 className="font-bold text-white">Ethical Delivery Intelligence & Fair Metrics Policy</h4>
            <p className="text-slate-300 leading-relaxed">
              {intelligence?.fair_metrics_policy ||
                'Metrics account for task complexity, dependency shifts, and verified acceptance. Never equate raw task count, hours online, or computer activity with productivity.'}
            </p>
            <p className="text-indigo-300 font-medium">
              {intelligence?.surveillance_statement ||
                'Surveillance statement: No keystroke recording, webcam feeds, screenshot captures, or continuous activity telemetry are collected or tolerated.'}
            </p>
          </div>
        </div>
      </div>

      {/* Current Project Delivery Intelligence */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Active Project Delivery Metrics</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Current Snapshot</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Planned Effort</span>
            <div className="mt-2 text-xl font-bold text-white font-mono">
              {intelligence?.total_planned_hours.toFixed(1) || '0.0'} hrs
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Approved PERT baseline</span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Actual Effort Logged</span>
            <div className="mt-2 text-xl font-bold text-white font-mono">
              {intelligence?.total_actual_hours.toFixed(1) || '0.0'} hrs
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Verified contributor time</span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Effort Variance</span>
            <div
              className={`mt-2 text-xl font-bold font-mono ${
                (intelligence?.effort_variance_pct || 0) > 10
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {(intelligence?.effort_variance_pct || 0) > 0 ? '+' : ''}
              {intelligence?.effort_variance_pct.toFixed(1) || '0.0'}%
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">
              {(intelligence?.effort_variance_pct || 0) <= 10 ? 'Within tolerance' : 'Overrun notice'}
            </span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Completed Deliverables</span>
            <div className="mt-2 text-xl font-bold text-indigo-400 font-mono">
              {intelligence?.completed_tasks_count || 0}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">
              {intelligence?.open_blockers_count || 0} blockers pending
            </span>
          </div>
        </div>
      </div>

      {/* Historical Learning & Calibration Engine */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">
              Historical Calibration & Estimation Learning
            </h3>
          </div>

          {/* Sample Size Policy Notice */}
          <div className="flex items-center gap-2">
            {!hasSample ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Insufficient Sample Size (N &lt; 5 Policy)</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Statistically Calibrated (N &ge; 5)</span>
              </span>
            )}
          </div>
        </div>

        {/* Policy Explanation Banner */}
        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
          <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-slate-300">Minimum Sample Policy: </span>
            {historical?.sample_size_policy_message ||
              'Calibration adjustments require at least 5 completed, manager-validated project outcomes to prevent statistical distortion from small samples.'}
          </div>
        </div>

        {/* Historical Aggregates */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Completed Projects</span>
            <div className="mt-2 text-xl font-bold text-white font-mono">
              {historical?.total_completed_projects || 0}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Validated outcomes</span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Avg Effort Variance</span>
            <div className="mt-2 text-xl font-bold text-slate-200 font-mono">
              {historical?.average_effort_variance_pct ? `${historical.average_effort_variance_pct.toFixed(1)}%` : '0.0%'}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Historical mean</span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Avg Cost Variance</span>
            <div className="mt-2 text-xl font-bold text-slate-200 font-mono">
              {historical?.average_cost_variance_pct ? `${historical.average_cost_variance_pct.toFixed(1)}%` : '0.0%'}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Historical mean</span>
          </div>

          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
            <span className="text-slate-400 text-xs">Calibration Factor</span>
            <div className="mt-2 text-xl font-bold text-indigo-300 font-mono">
              {historical?.composite_calibration_factor ? `${historical.composite_calibration_factor.toFixed(2)}x` : '1.00x'}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">
              {hasSample ? 'Active multiplier' : 'Inactive (Default 1.0x)'}
            </span>
          </div>
        </div>

        {/* Historical Projects Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Historical Project</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">Estimated</th>
                <th className="py-3 px-4 text-right">Actual</th>
                <th className="py-3 px-4 text-right">Effort Var</th>
                <th className="py-3 px-4 text-right">Cost Var</th>
                <th className="py-3 px-4 text-right">Calibration</th>
                <th className="py-3 px-4 text-right">Recorded Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {(historical?.projects || []).map((p) => (
                <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-white">
                    {p.project_name}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                      {p.category}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                    {p.estimated_hours}h
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                    {p.actual_hours}h
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono font-semibold text-slate-200">
                    {p.effort_variance_pct > 0 ? '+' : ''}{p.effort_variance_pct.toFixed(1)}%
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono font-semibold text-slate-200">
                    {p.cost_variance_pct > 0 ? '+' : ''}{p.cost_variance_pct.toFixed(1)}%
                  </td>
                  <td className="py-3.5 px-4 text-right font-mono font-bold text-indigo-400">
                    {p.calibration_factor.toFixed(2)}x
                  </td>
                  <td className="py-3.5 px-4 text-right text-slate-500 font-mono">
                    {new Date(p.recorded_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {(!historical?.projects || historical.projects.length === 0) && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                    No completed historical projects on record yet.
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
