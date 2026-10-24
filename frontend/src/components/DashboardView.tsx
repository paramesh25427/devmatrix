import React from 'react';
import {
  Clock,
  DollarSign,
  ShieldCheck,
  Calendar,
  AlertTriangle,
  ArrowRight,
  FileDown,
  CheckCircle2,
  Users,
} from 'lucide-react';
import { Project } from '../types/project';
import { ProjectEstimate } from '../types/estimation';
import { FeasibilityOverview } from '../types/risk';
import { ExecutionSummary } from '../types/execution';
import { ActiveTab } from './Sidebar';

interface DashboardViewProps {
  currentProject: Project | null;
  estimate: ProjectEstimate | null;
  feasibility: FeasibilityOverview | null;
  execution: ExecutionSummary | null;
  onNavigate: (tab: ActiveTab) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  currentProject,
  estimate,
  feasibility,
  execution,
  onNavigate,
}) => {
  const hasEstimate =
    estimate !== null &&
    typeof estimate === 'object' &&
    !Array.isArray(estimate) &&
    typeof estimate.total_pert_hours === 'number';
  const hasFeasibility =
    feasibility !== null &&
    typeof feasibility === 'object' &&
    !Array.isArray(feasibility) &&
    typeof feasibility.overall_status === 'string';
  const hasExecution =
    execution !== null &&
    typeof execution === 'object' &&
    !Array.isArray(execution) &&
    typeof execution.completion_percentage === 'number';
  const progressPct = hasExecution ? execution.completion_percentage : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-900/40 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
            Active Delivery Portfolio
          </span>
          <h2 className="text-2xl font-bold text-white tracking-tight mt-2">
            {currentProject ? currentProject.name : 'No Project Selected'}
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            {currentProject
              ? currentProject.description || 'Deterministic delivery baseline with PERT estimation and verified workforce allocations.'
              : 'Select an existing project or create a new delivery engagement from the top navigation to begin systematic intake and planning.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('reports')}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm shadow-indigo-600/30 transition-all"
          >
            <FileDown className="h-4 w-4" />
            <span>Generate PDF Report</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Total Effort */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total PERT Effort</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {hasEstimate ? `${estimate.total_pert_hours.toLocaleString()}h` : '—'}
            </span>
            <span className="text-xs text-indigo-400 ml-2 font-medium">
              {hasEstimate ? 'Expected (PERT)' : 'Pending Estimate'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Calculated via (O + 4M + P) / 6 formula</p>
        </div>

        {/* Metric 2: Total Labor & Contingency Cost */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Commercial Baseline</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {hasEstimate ? `$${estimate.total_cost.toLocaleString()}` : '—'}
            </span>
            <span className="text-xs text-emerald-400 ml-2 font-medium">
              {hasEstimate ? `${currentProject?.currency || 'USD'}` : 'Pending Cost'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Includes verified contingency buffer</p>
        </div>

        {/* Metric 3: Critical Path Schedule */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Schedule Duration</span>
            <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
              <Calendar className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-white tracking-tight">
              {hasEstimate ? `${estimate.estimated_duration_days}` : '—'}
            </span>
            <span className="text-xs text-violet-400 ml-2 font-medium">
              {hasEstimate ? 'Working Days' : 'Pending CPM'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Critical Path Method (CPM) duration</p>
        </div>

        {/* Metric 4: Feasibility Status */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Feasibility Rating</span>
            <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xl font-bold text-teal-300 tracking-tight">
              {hasFeasibility ? feasibility.overall_status.toUpperCase() : 'PENDING'}
            </span>
            {hasFeasibility ? (
              <span className="text-xs px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 font-semibold">
                {feasibility.overall_score || 0}/100
              </span>
            ) : (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-medium">
                Not Evaluated
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">7-dimension architectural evaluation</p>
        </div>
      </div>

      {/* Two Column Layout: Execution Pulse & Quick Workflow Access */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Delivery Progress & Highlights */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-white tracking-tight">Delivery Pulse & Execution</h3>
              <p className="text-xs text-slate-400 mt-0.5">Planned effort burnup versus verified completed deliverables</p>
            </div>
            <button
              onClick={() => onNavigate('execution')}
              className="text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
            >
              <span>View Tasks</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-400">
              <span>Overall Milestone Completion</span>
              <span className="font-semibold text-white">{progressPct}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 to-violet-500 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Requirements</span>
              <p className="text-base font-semibold text-slate-200 mt-1">
                {currentProject?.active_baseline_version && currentProject.active_baseline_version !== '0'
                  ? `v${currentProject.active_baseline_version} Approved`
                  : 'Pending Approval'}
              </p>
            </div>
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Critical Path Tasks</span>
              <p className="text-base font-semibold text-indigo-300 mt-1">
                {hasEstimate && estimate.critical_path_tasks ? `${estimate.critical_path_tasks.length} Tasks` : 'Pending CPM'}
              </p>
            </div>
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Open Blockers</span>
              <p className="text-base font-semibold text-emerald-400 mt-1">
                {hasExecution ? `${execution.blocked_tasks || 0} Critical` : '0 Critical'}
              </p>
            </div>
          </div>

          {/* Active Risk Banner */}
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold text-amber-200">Governance Notice: Contingency Buffer Active</p>
              <p className="text-amber-300/80 mt-0.5">
                Baseline cost incorporates a 15% contingency reserve against cloud resource autoscaling and third-party API rate limits.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Workflow Steps */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-base font-semibold text-white tracking-tight">Project Planning Pipeline</h3>
          <p className="text-xs text-slate-400">Systematic delivery planning stages</p>

          <div className="space-y-3 pt-2">
            {[
              { id: 'documents', title: '1. Document Ingestion', desc: 'Upload PDF, DOCX, XLSX specs', icon: CheckCircle2, complete: Boolean(currentProject) },
              { id: 'requirements', title: '2. Requirements Review', desc: 'Review & approve baseline', icon: CheckCircle2, complete: Boolean(currentProject?.active_baseline_version && currentProject.active_baseline_version !== '0') },
              { id: 'wbs', title: '3. Work Breakdown (WBS)', desc: 'Task breakdown & DAG dependencies', icon: CheckCircle2, complete: hasEstimate },
              { id: 'estimation', title: '4. PERT & CPM Estimation', desc: 'Effort, cost, and schedule calculation', icon: CheckCircle2, complete: hasEstimate },
              { id: 'workforce', title: '5. Workforce Allocation', desc: 'Multi-criteria candidate matching', icon: Users, complete: hasExecution },
              { id: 'reports', title: '6. Executive PDF Export', desc: 'Generate downloadable plan', icon: FileDown, complete: hasEstimate },
            ].map((step) => {
              const Icon = step.icon;
              return (
                <button
                  key={step.id}
                  onClick={() => onNavigate(step.id as ActiveTab)}
                  className="w-full text-left p-3 rounded-lg border border-slate-800 hover:border-indigo-500/40 hover:bg-slate-800/40 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${step.complete ? 'text-indigo-400' : 'text-slate-500'}`} />
                    <div>
                      <p className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300 transition-colors">
                        {step.title}
                      </p>
                      <p className="text-[11px] text-slate-500">{step.desc}</p>
                    </div>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
