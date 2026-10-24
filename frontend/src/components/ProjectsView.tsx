import React, { useState } from 'react';
import { FolderKanban, Plus, Calendar, DollarSign, ListTree, FileText, ArrowRight } from 'lucide-react';
import { Project } from '../types/project';
import { api } from '../services/api';

interface ProjectsViewProps {
  projects: Project[];
  currentProjectId: string;
  onSelectProject: (p: Project) => void;
  onRefresh: () => void;
  isLoading?: boolean;
  error?: string | null;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  currentProjectId,
  onSelectProject,
  onRefresh,
  isLoading = false,
  error = null,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [budget, setBudget] = useState('250000');
  const [deadline, setDeadline] = useState('2026-12-15');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    setErrorMsg('');
    try {
      const p = await api.createProject(name, desc, parseFloat(budget) || undefined, deadline);
      setShowCreateModal(false);
      setName('');
      setDesc('');
      onRefresh();
      onSelectProject(p);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Enterprise Delivery Projects</h2>
          <p className="text-xs text-slate-400 mt-1">Manage tenant project delivery portfolios and intake baselines</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm shadow-indigo-600/30 transition-all self-start"
        >
          <Plus className="h-4 w-4" />
          <span>New Delivery Project</span>
        </button>
      </div>

      {/* State Rendering: Loading / Error / Empty / Grid */}
      {isLoading ? (
        <div data-testid="projects-loading-state" className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <div className="h-10 w-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm font-medium text-white">Loading enterprise delivery projects...</p>
          <p className="text-xs text-slate-500 mt-1">Retrieving portfolio records from isolated tenant database</p>
        </div>
      ) : error ? (
        <div data-testid="projects-error-state" className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-8 text-center max-w-xl mx-auto">
          <div className="h-12 w-12 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center mx-auto mb-3">
            <FolderKanban className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-white tracking-tight">Failed to Load Projects</h3>
          <p className="text-xs text-rose-300/80 mt-1 mb-4">{error}</p>
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            Retry Connection
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div data-testid="projects-empty-state" className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center max-w-lg mx-auto">
          <div className="h-12 w-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-3">
            <FolderKanban className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-white tracking-tight">No Delivery Projects Available</h3>
          <p className="text-xs text-slate-400 mt-2 mb-4">
            No projects found in this tenant scope. Create your first delivery project to start intake and deterministic planning.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Create First Delivery Project</span>
          </button>
        </div>
      ) : (
        <div data-testid="projects-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => {
          const isSelected = p.id === currentProjectId;
          return (
            <div
              key={p.id}
              data-testid={`project-card-${p.id}`}
              onClick={() => onSelectProject(p)}
              className={`bg-slate-900 border rounded-xl p-5 cursor-pointer transition-all ${
                isSelected
                  ? 'border-indigo-500 shadow-md shadow-indigo-500/10 bg-slate-900/90 ring-1 ring-indigo-500/30'
                  : 'border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'}`}>
                    <FolderKanban className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white tracking-tight line-clamp-1">{p.name}</h3>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                      {p.status}
                    </span>
                  </div>
                </div>
                {isSelected && (
                  <span className="text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                    Active
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-400 mt-3 line-clamp-2 h-8">
                {p.description || 'Enterprise delivery initiative with automated requirement extraction and baseline planning.'}
              </p>

              <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
                <div className="flex items-center gap-1.5">
                  <DollarSign className="h-3.5 w-3.5 text-slate-500" />
                  <span>${(p.target_budget || 250000).toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-slate-500" />
                  <span>{p.target_deadline || 'Q4 2026'}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-slate-500" />
                  <span>{p.document_count} Documents</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <ListTree className="h-3.5 w-3.5 text-slate-500" />
                  <span>{p.task_count} Tasks</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs font-medium text-indigo-400 group">
                <span>Baseline Version: v{p.active_baseline_version || '1'}</span>
                <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>
    )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white tracking-tight">Create New Delivery Project</h3>
            <p className="text-xs text-slate-400 mt-1">Initialize a project container for document intake and planning</p>

            {errorMsg && (
              <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Project Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Core Banking API Migration"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  placeholder="Business context and delivery objectives..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Budget ($ USD)</label>
                  <input
                    type="number"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Deadline</label>
                  <input
                    type="date"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  {isSubmitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
