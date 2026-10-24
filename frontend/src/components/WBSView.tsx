import React, { useState } from 'react';
import {
  ListTree,
  Plus,
  GitBranch,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { WBSOverview } from '../types/wbs';
import { api } from '../services/api';

interface WBSViewProps {
  overview: WBSOverview | null;
  projectId: string;
  hasApprovedBaseline?: boolean;
  isBaselineLoading?: boolean;
  onRefresh: () => void;
}

export const WBSView: React.FC<WBSViewProps> = ({
  overview,
  projectId,
  hasApprovedBaseline = false,
  isBaselineLoading = false,
  onRefresh,
}) => {
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [showDepModal, setShowDepModal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Task form state
  const [code, setCode] = useState('TSK-');
  const [title, setTitle] = useState('');
  const [role, setRole] = useState('Full-Stack Engineer');
  const [opt, setOpt] = useState('16');
  const [ml, setMl] = useState('24');
  const [pess, setPess] = useState('40');

  // Dependency form state
  const [predId, setPredId] = useState('');
  const [succId, setSuccId] = useState('');

  const handleGenerate = async () => {
    setIsGenerating(true);
    setErrorMsg('');
    try {
      await api.generateWBS(projectId);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate WBS');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createTask({
        project_id: projectId,
        task_code: code,
        title,
        required_role: role,
        optimistic_hours: parseFloat(opt) || 8.0,
        most_likely_hours: parseFloat(ml) || 16.0,
        pessimistic_hours: parseFloat(pess) || 32.0,
      });
      setShowTaskModal(false);
      setTitle('');
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create task');
    }
  };

  const handleAddDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!predId || !succId) return;
    setErrorMsg('');
    try {
      await api.addDependency(projectId, predId, succId);
      setShowDepModal(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to add dependency');
    }
  };

  const tasks = overview?.tasks || [];
  const isGenerateDisabled = isGenerating || isBaselineLoading || !hasApprovedBaseline;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
            Work Breakdown Structure
          </span>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Tasks, Dependencies & PERT Effort
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Topologically sorted DAG graph with automated cycle detection and Critical Path analysis
          </p>
        </div>

        <div className="flex items-center gap-3">
          {tasks.length === 0 ? (
            <button
              onClick={handleGenerate}
              disabled={isGenerateDisabled}
              title={!hasApprovedBaseline ? "An approved requirements baseline is required. Review and approve the requirements draft first." : undefined}
              className={`flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-lg transition-all ${
                isGenerateDisabled
                  ? 'bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed shadow-none'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm shadow-indigo-600/30 cursor-pointer'
              }`}
            >
              <Sparkles className={`h-4 w-4 ${isGenerateDisabled ? 'text-slate-500' : 'text-indigo-200'}`} />
              <span>
                {isBaselineLoading
                  ? 'Checking Baseline...'
                  : isGenerating
                  ? 'Generating...'
                  : 'Generate WBS from Baseline'}
              </span>
            </button>
          ) : (
            <>
              <button
                onClick={() => setShowDepModal(true)}
                className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-700"
              >
                <GitBranch className="h-4 w-4 text-indigo-400" />
                <span>Link Dependency</span>
              </button>
              <button
                onClick={() => setShowTaskModal(true)}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-2 rounded-lg"
              >
                <Plus className="h-4 w-4" />
                <span>Add Task</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Baseline Approval Guidance Banner */}
      {!hasApprovedBaseline && !isBaselineLoading && (
        <div
          data-testid="wbs-baseline-guidance-banner"
          className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs flex items-start gap-3"
        >
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-amber-200">Requirements Baseline Required</p>
            <p className="mt-0.5 text-amber-300/90">
              An approved requirements baseline is required. Review and approve the requirements draft first.
            </p>
          </div>
        </div>
      )}

      {/* Cyclic Dependency Error Banner */}
      {!overview?.is_dag_valid && overview?.cycle_error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">DAG Validation Error: Circular Dependency Detected</p>
            <p className="mt-0.5 text-rose-200/90">{overview.cycle_error}</p>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Tasks Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListTree className="h-4 w-4 text-indigo-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Project Deliverable Tasks ({tasks.length})
            </h3>
          </div>
          <span className="text-xs text-indigo-400 font-semibold">
            Total Expected Effort: {overview?.total_pert_hours || 0} Hours
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Code</th>
                <th className="py-3 px-4">Task Title & Description</th>
                <th className="py-3 px-4">Required Role</th>
                <th className="py-3 px-4 text-center">Opt / ML / Pess</th>
                <th className="py-3 px-4 text-right">PERT Expected</th>
                <th className="py-3 px-4 text-center">Critical Path</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    {isBaselineLoading
                      ? 'Checking requirements baseline status...'
                      : !hasApprovedBaseline
                      ? 'An approved requirements baseline is required. Review and approve the requirements draft first.'
                      : 'No WBS tasks generated yet. Click "Generate WBS from Baseline" to begin planning.'}
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-300">
                      {task.task_code}
                    </td>
                    <td className="py-3 px-4 max-w-xs">
                      <p className="font-semibold text-white truncate">{task.title}</p>
                      <p className="text-[11px] text-slate-400 truncate">{task.epic_name || 'General'}</p>
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {task.required_role}
                    </td>
                    <td className="py-3 px-4 text-center text-slate-400 font-mono text-[11px]">
                      {task.optimistic_hours} / {task.most_likely_hours} / {task.pessimistic_hours}h
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-white">
                      {task.expected_hours.toFixed(1)}h
                    </td>
                    <td className="py-3 px-4 text-center">
                      {task.is_critical_path ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          YES (CPM)
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">No</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                        {task.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Creation Modal */}
      {showTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-base font-bold text-white tracking-tight">Add Task to Work Breakdown</h3>
            <form onSubmit={handleCreateTask} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 mb-1">Task Code *</label>
                <input
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Task deliverable description..."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 mb-1">Required Role *</label>
                <input
                  type="text"
                  required
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-slate-300 mb-1">Opt (h)</label>
                  <input
                    type="number"
                    value={opt}
                    onChange={(e) => setOpt(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">ML (h)</label>
                  <input
                    type="number"
                    value={ml}
                    onChange={(e) => setMl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1">Pess (h)</label>
                  <input
                    type="number"
                    value={pess}
                    onChange={(e) => setPess(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTaskModal(false)}
                  className="text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded"
                >
                  Save Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dependency Modal */}
      {showDepModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl text-xs">
            <h3 className="text-base font-bold text-white tracking-tight">Add Task Dependency</h3>
            <p className="text-slate-400 mt-1">Predecessor must complete before Successor can begin</p>
            <form onSubmit={handleAddDependency} className="mt-4 space-y-4">
              <div>
                <label className="block text-slate-300 mb-1">Predecessor Task (Must finish first)</label>
                <select
                  value={predId}
                  onChange={(e) => setPredId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                >
                  <option value="">Select Predecessor...</option>
                  {tasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.task_code}: {t.title}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-300 mb-1">Successor Task (Cannot start before)</label>
                <select
                  value={succId}
                  onChange={(e) => setSuccId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white"
                >
                  <option value="">Select Successor...</option>
                  {tasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.task_code}: {t.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowDepModal(false)}
                  className="text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded"
                >
                  Link & Validate DAG
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
