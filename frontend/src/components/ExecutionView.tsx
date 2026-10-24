import React, { useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Flag,
  Send,
  PlusCircle,
  User,
  History,
  ListTodo,
  RefreshCw,
  Sliders,
  Check,
  Flame,
  ShieldCheck,
} from 'lucide-react';
import { ExecutionSummary } from '../types/execution';
import { WBSTask } from '../types/wbs';
import { api } from '../services/api';

interface ExecutionViewProps {
  summary: ExecutionSummary | null;
  tasks: WBSTask[];
  projectId?: string;
  onRefresh: () => void;
}

export const ExecutionView: React.FC<ExecutionViewProps> = ({
  summary,
  tasks,
  onRefresh,
}) => {
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [hoursLogged, setHoursLogged] = useState<string>('0.0');
  const [newStatus, setNewStatus] = useState<string>('in_progress');
  const [progressPct, setProgressPct] = useState<number>(0);
  const [notes, setNotes] = useState<string>('');
  const [hasBlocker, setHasBlocker] = useState<boolean>(false);
  const [blockerDesc, setBlockerDesc] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [activeSubTab, setActiveSubTab] = useState<'tasks' | 'update' | 'history'>('tasks');

  // When selecting a task from the table to update
  const handleSelectTaskForUpdate = (t: WBSTask) => {
    setSelectedTaskId(t.id);
    setNewStatus(t.status || 'not_started');
    setProgressPct(t.progress_percentage || (t.status === 'completed' ? 100 : 0));
    setHoursLogged('0.0');
    setNotes('');
    setHasBlocker(t.status === 'blocked' || !!t.blocker_notes);
    setBlockerDesc(t.blocker_notes || '');
    setErrorMsg('');
    setSuccessMsg('');
    setActiveSubTab('update');
  };

  const handleStatusChange = (statusVal: string) => {
    setNewStatus(statusVal);
    if (statusVal === 'completed') {
      setProgressPct(100);
      setHasBlocker(false);
    } else if (statusVal === 'not_started') {
      setProgressPct(0);
      setHasBlocker(false);
    } else if (statusVal === 'blocked') {
      setHasBlocker(true);
    }
  };

  const handleLogProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTaskId) {
      setErrorMsg('Please select a task to update.');
      return;
    }
    const logged = parseFloat(hoursLogged);
    if (isNaN(logged) || logged < 0) {
      setErrorMsg('Hours logged cannot be negative.');
      return;
    }
    if (progressPct < 0 || progressPct > 100) {
      setErrorMsg('Progress percentage must be between 0 and 100.');
      return;
    }
    if ((newStatus === 'blocked' || hasBlocker) && (!blockerDesc || !blockerDesc.trim())) {
      setErrorMsg('A blocker description is required when status is Blocked or blocker flag is set.');
      return;
    }

    setIsUpdating(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      await api.updateTaskProgress(
        selectedTaskId,
        logged,
        newStatus,
        progressPct,
        notes,
        hasBlocker || newStatus === 'blocked',
        blockerDesc
      );
      setSuccessMsg('Progress update recorded with audit trail.');
      setNotes('');
      setBlockerDesc('');
      setHasBlocker(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to record progress update');
    } finally {
      setIsUpdating(false);
    }
  };

  const completionPct = summary?.completion_percentage || 0;
  const milestones = summary?.milestones || [];
  const blockers = summary?.active_blockers || [];
  const recentUpdates = summary?.recent_updates || [];
  const totalActual = summary?.total_actual_hours || 0;
  const totalPlanned = summary?.total_planned_hours || 0;

  // Selected task object
  const currentSelectedTask = tasks.find((t) => t.id === selectedTaskId);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 8 &bull; Project Execution & Progress
            </span>
            <span className="text-xs text-slate-400">
              Auditable Delivery Tracking
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Execution Tracking, Milestones & Blocker Management
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Track planned vs. actual effort, update task completion status with strict manager auditing, and clear operational blockers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh State</span>
          </button>
        </div>
      </div>

      {/* Guard / Empty State if project has no tasks */}
      {tasks.length === 0 ? (
        <div className="bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-12 text-center">
          <Activity className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-base font-semibold text-white">No WBS Tasks Generated Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
            This project does not have active WBS tasks. Review and approve the requirements baseline, then generate the Work Breakdown Structure first.
          </p>
        </div>
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Completion Progress</span>
                <Activity className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">{completionPct}%</span>
                <span className="text-xs text-slate-400">overall project</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full mt-3 overflow-hidden">
                <div
                  className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(completionPct, 100)}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Task Velocity</span>
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {summary?.completed_tasks || 0}
                </span>
                <span className="text-xs text-slate-400">
                  / {summary?.total_tasks || tasks.length} tasks
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                {summary?.in_progress_tasks || 0} in flight &bull; {summary?.blocked_tasks || 0} blocked
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Planned vs Actual Effort</span>
                <Clock className="h-4 w-4 text-blue-400" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-white">
                  {totalActual > 0 ? totalActual.toFixed(1) : '0.0'}
                </span>
                <span className="text-xs text-slate-400">
                  / {totalPlanned.toFixed(0)} hrs
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                {totalActual > 0 ? 'Verified contributor logged time' : 'No actual hours logged yet'}
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span className="font-medium">Active Impediments</span>
                <AlertTriangle className={`h-4 w-4 ${blockers.length > 0 ? 'text-rose-400' : 'text-slate-400'}`} />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className={`text-2xl font-bold ${blockers.length > 0 ? 'text-rose-400' : 'text-white'}`}>
                  {blockers.length}
                </span>
                <span className="text-xs text-slate-400">
                  {blockers.length === 1 ? 'blocker' : 'blockers'}
                  {summary?.overdue_milestones_count ? ` &bull; ${summary.overdue_milestones_count} overdue` : ''}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                {blockers.length > 0 ? 'Requires manager attention' : 'Execution flow clear'}
              </p>
            </div>
          </div>

          {/* Sub-tab Navigation */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
            <button
              onClick={() => setActiveSubTab('tasks')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'tasks'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <ListTodo className="h-3.5 w-3.5" />
              <span>WBS Tasks & Progress ({tasks.length})</span>
            </button>
            <button
              onClick={() => setActiveSubTab('update')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'update'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Sliders className="h-3.5 w-3.5" />
              <span>Update Task Status & Progress</span>
            </button>
            <button
              onClick={() => setActiveSubTab('history')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                activeSubTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              <span>Audit Trail & Milestones</span>
            </button>
          </div>

          {/* SUBTAB 1: WBS Tasks & Progress Table */}
          {activeSubTab === 'tasks' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Project Work Breakdown Tasks</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Planned effort, contributor assignments, completion percentage, and active status.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/70 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Code</th>
                      <th className="py-3 px-4 font-semibold">Task Title</th>
                      <th className="py-3 px-4 font-semibold">Assignee / Role</th>
                      <th className="py-3 px-4 font-semibold">Status</th>
                      <th className="py-3 px-4 font-semibold text-right">Planned</th>
                      <th className="py-3 px-4 font-semibold text-right">Actual</th>
                      <th className="py-3 px-4 font-semibold min-w-[150px]">Progress</th>
                      <th className="py-3 px-4 font-semibold text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {tasks.map((task) => {
                      const prog = task.progress_percentage || (task.status === 'completed' ? 100 : 0);
                      const isDone = task.status === 'completed';
                      const isBlocked = task.status === 'blocked';
                      const isInProgress = task.status === 'in_progress';
                      const isReview = task.status === 'in_review';

                      return (
                        <tr key={task.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-mono font-bold text-white flex items-center gap-1.5">
                            <span>{task.task_code}</span>
                            {task.is_critical_path && (
                              <span
                                title="Critical Path Task"
                                className="inline-flex items-center text-[10px] text-rose-400 bg-rose-500/10 px-1 py-0.5 rounded border border-rose-500/20"
                              >
                                <Flame className="h-2.5 w-2.5" />
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-medium text-white max-w-xs">
                            <div className="truncate" title={task.title}>{task.title}</div>
                            {task.blocker_notes && (
                              <div className="mt-1 flex items-center gap-1 text-[11px] text-rose-400">
                                <AlertTriangle className="h-3 w-3 shrink-0" />
                                <span className="truncate">{task.blocker_notes}</span>
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            {task.assigned_user_name ? (
                              <div className="flex items-center gap-1.5 text-slate-200">
                                <User className="h-3.5 w-3.5 text-indigo-400" />
                                <span>{task.assigned_user_name}</span>
                              </div>
                            ) : (
                              <span className="text-slate-400 text-[11px] italic bg-slate-800/80 px-2 py-0.5 rounded">
                                {task.required_role}
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase ${
                                isDone
                                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                  : isBlocked
                                  ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                                  : isInProgress
                                  ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                                  : isReview
                                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                  : 'bg-slate-800 text-slate-400 border border-slate-700'
                              }`}
                            >
                              {isDone && <CheckCircle2 className="h-3 w-3" />}
                              {isBlocked && <AlertTriangle className="h-3 w-3" />}
                              {isInProgress && <Activity className="h-3 w-3" />}
                              {task.status.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-300">
                            {task.expected_hours.toFixed(1)}h
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono">
                            {task.actual_hours > 0 ? (
                              <span className="text-white font-semibold">{task.actual_hours.toFixed(1)}h</span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2">
                              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all duration-300 ${
                                    isDone
                                      ? 'bg-emerald-500'
                                      : isBlocked
                                      ? 'bg-rose-500'
                                      : 'bg-indigo-500'
                                  }`}
                                  style={{ width: `${Math.min(prog, 100)}%` }}
                                />
                              </div>
                              <span className="text-[11px] font-mono text-slate-400 w-8 text-right shrink-0">
                                {prog}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <button
                              onClick={() => handleSelectTaskForUpdate(task)}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white rounded text-[11px] font-medium transition"
                            >
                              Update
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* SUBTAB 2: Update Task Status & Progress Form */}
          {activeSubTab === 'update' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 lg:col-span-2">
                <div className="flex items-center gap-2 mb-4">
                  <PlusCircle className="h-4 w-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">Record Verified Task Progress</h3>
                </div>

                {errorMsg && (
                  <div className="mb-4 bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-rose-300 text-xs">
                    {errorMsg}
                  </div>
                )}

                {successMsg && (
                  <div className="mb-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-emerald-300 text-xs">
                    {successMsg}
                  </div>
                )}

                <form onSubmit={handleLogProgress} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-slate-400 font-medium mb-1">Select Target Task:</label>
                    <select
                      value={selectedTaskId}
                      onChange={(e) => {
                        const t = tasks.find((item) => item.id === e.target.value);
                        if (t) handleSelectTaskForUpdate(t);
                        else setSelectedTaskId('');
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">-- Choose WBS Task --</option>
                      {tasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.task_code}: {t.title} ({t.status}, {t.progress_percentage || 0}%)
                        </option>
                      ))}
                    </select>
                  </div>

                  {currentSelectedTask && (
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80 flex items-center justify-between text-xs">
                      <div>
                        <span className="text-slate-400">Assigned: </span>
                        <span className="text-white font-medium">
                          {currentSelectedTask.assigned_user_name || currentSelectedTask.required_role}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Planned Effort: </span>
                        <span className="font-mono text-indigo-300 font-semibold">
                          {currentSelectedTask.expected_hours.toFixed(1)} hrs
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Total Logged: </span>
                        <span className="font-mono text-emerald-300 font-semibold">
                          {currentSelectedTask.actual_hours.toFixed(1)} hrs
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-slate-400 font-medium mb-1">Target Status:</label>
                      <select
                        value={newStatus}
                        onChange={(e) => handleStatusChange(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="not_started">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="blocked">Blocked</option>
                        <option value="in_review">In Review</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-400 font-medium mb-1">Hours Logged in this Update:</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max="500"
                        value={hoursLogged}
                        onChange={(e) => setHoursLogged(e.target.value)}
                        placeholder="0.0"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                  </div>

                  {/* Completion Percentage with Slider & Quick Buttons */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-slate-400 font-medium">
                        Completion Percentage (0 - 100%):
                      </label>
                      <span className="font-mono font-bold text-indigo-400 text-sm">
                        {progressPct}%
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        value={progressPct}
                        onChange={(e) => setProgressPct(parseInt(e.target.value, 10))}
                        className="w-full h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                      />
                    </div>

                    {/* Quick Presets */}
                    <div className="flex items-center gap-2 mt-2">
                      {[0, 25, 50, 75, 100].map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => {
                            setProgressPct(preset);
                            if (preset === 100) setNewStatus('completed');
                            else if (preset === 0) setNewStatus('not_started');
                            else if (newStatus === 'not_started' || newStatus === 'completed') setNewStatus('in_progress');
                          }}
                          className={`px-2.5 py-1 rounded text-[11px] font-mono font-medium transition ${
                            progressPct === preset
                              ? 'bg-indigo-600 text-white'
                              : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                          }`}
                        >
                          {preset}%
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-medium mb-1">Progress Notes & Summary:</label>
                    <textarea
                      rows={3}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Detail deliverables completed, milestones met, or pull requests submitted..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80">
                    <label className="flex items-center gap-2 cursor-pointer text-slate-300 font-medium">
                      <input
                        type="checkbox"
                        checked={hasBlocker || newStatus === 'blocked'}
                        onChange={(e) => {
                          setHasBlocker(e.target.checked);
                          if (!e.target.checked && newStatus === 'blocked') setNewStatus('in_progress');
                        }}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      <span>Flag as active blocker or dependency impediment</span>
                    </label>

                    {(hasBlocker || newStatus === 'blocked') && (
                      <div className="mt-2.5">
                        <input
                          type="text"
                          value={blockerDesc}
                          onChange={(e) => setBlockerDesc(e.target.value)}
                          placeholder="Describe external blocker or dependency impediment..."
                          className="w-full bg-slate-900 border border-rose-500/40 rounded px-2.5 py-1.5 text-rose-200 text-xs focus:outline-none"
                        />
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={isUpdating || !selectedTaskId}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg font-semibold shadow-md transition"
                  >
                    <Send className="h-3.5 w-3.5" />
                    <span>{isUpdating ? 'Recording Update...' : 'Submit Progress Update & Record Audit'}</span>
                  </button>
                </form>
              </div>

              {/* Right Sidebar: Active Blockers Callout */}
              <div className="space-y-6">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-white font-semibold text-xs mb-3">
                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                    <span>Active Project Blockers</span>
                  </div>
                  {blockers.length === 0 ? (
                    <div className="text-center py-6 text-slate-500 text-xs">
                      No impediments currently flagged.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {blockers.map((b, idx) => (
                        <div
                          key={idx}
                          className="bg-slate-950/80 border border-rose-500/20 p-3 rounded-lg flex items-start gap-2.5"
                        >
                          <span className="font-mono font-bold text-rose-400 text-xs shrink-0">
                            {b.task_code}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-white truncate">{b.title}</p>
                            <p className="text-[11px] text-rose-200/80 mt-0.5">{b.notes}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center gap-2 text-white font-semibold text-xs mb-3">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <span>Audit Safeguards Enforced</span>
                  </div>
                  <ul className="space-y-2 text-xs text-slate-400 list-disc list-inside">
                    <li>Manager review required for task progress updates.</li>
                    <li>Every status change creates an immutable audit log.</li>
                    <li>Completion requires 100% progress verification.</li>
                    <li>Tenant isolation blocks cross-project tampering.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* SUBTAB 3: Audit Trail & Milestones */}
          {activeSubTab === 'history' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Recent Updates Audit Log */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 lg:col-span-2 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <History className="h-4 w-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-white">Execution Audit Trail</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {recentUpdates.length} Logged Entries
                  </span>
                </div>

                {recentUpdates.length === 0 ? (
                  <p className="text-xs text-slate-500 italic p-8 text-center">
                    No task updates recorded yet for this project.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {recentUpdates.map((rec) => (
                      <div
                        key={rec.id}
                        className="p-3.5 bg-slate-950 rounded-lg border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{rec.user_name}</span>
                            <span className="text-slate-500">&bull;</span>
                            <span className="text-slate-400">
                              {new Date(rec.created_at).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-[11px]">
                            <span className="font-mono text-slate-400">
                              {rec.previous_status} &rarr;{' '}
                              <span className="text-white font-medium">{rec.new_status}</span>
                            </span>
                            <span className="text-slate-500">&bull;</span>
                            <span className="font-mono text-indigo-400">
                              {rec.progress_percentage}% completed
                            </span>
                            {rec.hours_logged > 0 && (
                              <>
                                <span className="text-slate-500">&bull;</span>
                                <span className="font-mono text-emerald-400">
                                  +{rec.hours_logged}h logged
                                </span>
                              </>
                            )}
                          </div>
                          {rec.progress_notes && (
                            <p className="text-slate-300 italic text-[11px] mt-1 bg-slate-900/60 p-2 rounded">
                              "{rec.progress_notes}"
                            </p>
                          )}
                          {rec.blocker_flag === 'true' && rec.blocker_description && (
                            <div className="flex items-center gap-1 text-[11px] text-rose-400 mt-1">
                              <AlertTriangle className="h-3 w-3 shrink-0" />
                              <span>Blocker: {rec.blocker_description}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column: Milestones */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Flag className="h-4 w-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-white">Project Milestones</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {milestones.filter((m) => m.status === 'completed').length} / {milestones.length}
                  </span>
                </div>

                {milestones.length === 0 ? (
                  <p className="text-xs text-slate-500 italic p-6 text-center">
                    No milestones defined for this project.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {milestones.map((m) => {
                      const isDone = m.status === 'completed';
                      return (
                        <div
                          key={m.id}
                          className="p-3 bg-slate-950 rounded-lg border border-slate-800/80"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div
                                className={`h-6 w-6 rounded-full flex items-center justify-center text-xs ${
                                  isDone
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-slate-800 text-slate-400'
                                }`}
                              >
                                {isDone ? <Check className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                              </div>
                              <span className="text-xs font-semibold text-white">{m.title}</span>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                isDone
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {m.status}
                            </span>
                          </div>
                          {m.description && (
                            <p className="text-[11px] text-slate-400 mt-1 pl-8">{m.description}</p>
                          )}
                          <p className="text-[10px] font-mono text-slate-500 mt-1 pl-8">
                            Due: {new Date(m.due_date).toLocaleDateString()}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
