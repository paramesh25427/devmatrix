import React, { useState } from 'react';
import {
  CheckSquare,
  AlertTriangle,
  HelpCircle,
  FileCheck2,
  CheckCircle2,
  Layers,
  Shield,
  FileText,
} from 'lucide-react';
import { RequirementDraftResponse } from '../types/requirement';
import { api } from '../services/api';

interface RequirementsViewProps {
  draft: RequirementDraftResponse | null;
  baseline: any | null;
  projectId?: string;
  onBaselineApproved: () => void;
}

export const RequirementsView: React.FC<RequirementsViewProps> = ({
  draft,
  baseline,
  onBaselineApproved,
}) => {
  const [activeTab, setActiveTab] = useState<'functional' | 'non_functional' | 'conflicts' | 'scope'>('functional');
  const [isApproving, setIsApproving] = useState(false);
  const [managerNotes, setManagerNotes] = useState('Reviewed and approved for WBS generation');
  const [approvalSuccess, setApprovalSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Source data either from approved baseline or draft
  const reqData = baseline ? baseline.requirements : draft?.requirements;
  const isApproved = !!baseline;
  const version = baseline?.version || draft?.requirements ? 1 : 0;

  const handleApprove = async () => {
    if (!draft?.id) return;
    setIsApproving(true);
    setErrorMsg('');
    try {
      await api.approveBaseline(draft.id, managerNotes, `Approved baseline version v${version}`);
      setApprovalSuccess(true);
      onBaselineApproved();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to approve baseline');
    } finally {
      setIsApproving(false);
    }
  };

  if (!reqData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center max-w-lg mx-auto">
        <div className="h-12 w-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-4">
          <CheckSquare className="h-6 w-6" />
        </div>
        <h3 className="text-base font-bold text-white tracking-tight">No Requirements Baseline Available</h3>
        <p className="text-xs text-slate-400 mt-2">
          Upload a project specification document in the Document Vault and trigger AI requirement extraction to populate candidate requirements.
        </p>
      </div>
    );
  }

  const functional = reqData.functional_requirements || [];
  const nonFunctional = reqData.non_functional_requirements || [];
  const conflicts = reqData.contradictions || [];
  const questions = reqData.missing_information || [];
  const scope = reqData.scope || { deliverables: [], scope_inclusions: [], scope_exclusions: [] };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                isApproved
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}
            >
              {isApproved ? `Baseline v${baseline.version} Approved` : 'Candidate Draft (Awaiting Approval)'}
            </span>
            <span className="text-xs text-slate-400">• Confidence: 92% (High)</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            {reqData.project_summary?.project_name || 'Project Requirements Baseline'}
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl line-clamp-2">
            {reqData.project_summary?.summary || reqData.project_summary || 'Validated requirements baseline extracted from intake documents.'}
          </p>
        </div>

        {/* Action Button */}
        {!isApproved && draft?.id && (
          <div className="flex flex-col items-end gap-2">
            <input
              type="text"
              value={managerNotes}
              onChange={(e) => setManagerNotes(e.target.value)}
              placeholder="Manager review notes..."
              className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 w-64"
            />
            <button
              onClick={handleApprove}
              disabled={isApproving}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm shadow-emerald-600/30 transition-all"
            >
              <FileCheck2 className="h-4 w-4" />
              <span>{isApproving ? 'Approving Baseline...' : 'Approve Baseline (v1)'}</span>
            </button>
            <span className="text-[11px] text-slate-500">Requires Delivery Manager sign-off</span>
          </div>
        )}
      </div>

      {approvalSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>Requirements baseline approved successfully! WBS tasks can now be generated.</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-300 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Conflicts & Open Questions Alert Banner */}
      {(conflicts.length > 0 || questions.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {conflicts.length > 0 && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
                <AlertTriangle className="h-4 w-4" />
                <span>{conflicts.length} Document Contradiction(s) Flagged</span>
              </div>
              <p className="text-[11px] text-amber-300/80">
                Opposing statements detected across document sections. Both sides are preserved for manager resolution.
              </p>
            </div>
          )}
          {questions.length > 0 && (
            <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs">
                <HelpCircle className="h-4 w-4" />
                <span>{questions.length} Open Stakeholder Clarification(s)</span>
              </div>
              <p className="text-[11px] text-indigo-300/80">
                Critical missing specifications isolated as questions rather than hallucinated assumptions.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6 text-xs font-medium">
        <button
          onClick={() => setActiveTab('functional')}
          className={`pb-3 border-b-2 transition-colors ${
            activeTab === 'functional'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Functional Requirements ({functional.length})
        </button>
        <button
          onClick={() => setActiveTab('non_functional')}
          className={`pb-3 border-b-2 transition-colors ${
            activeTab === 'non_functional'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Non-Functional Requirements ({nonFunctional.length})
        </button>
        <button
          onClick={() => setActiveTab('conflicts')}
          className={`pb-3 border-b-2 transition-colors ${
            activeTab === 'conflicts'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Contradictions & Questions ({conflicts.length + questions.length})
        </button>
        <button
          onClick={() => setActiveTab('scope')}
          className={`pb-3 border-b-2 transition-colors ${
            activeTab === 'scope'
              ? 'border-indigo-500 text-indigo-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Scope & Governance Boundaries
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-4">
        {activeTab === 'functional' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {functional.map((item: any) => (
              <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    {item.id}
                  </span>
                  <span className="text-[10px] font-semibold uppercase text-slate-400">
                    {item.category}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-white tracking-tight">{item.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>
                {item.source_references && item.source_references.length > 0 && (
                  <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center gap-1.5">
                    <FileText className="h-3 w-3" />
                    <span>Source: {item.source_references[0]?.location || 'Overview'}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'non_functional' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {nonFunctional.map((item: any) => (
              <div key={item.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/20">
                    {item.id}
                  </span>
                  <span className="text-[10px] font-semibold uppercase text-slate-400">
                    {item.category}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-white tracking-tight">{item.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'conflicts' && (
          <div className="space-y-4">
            {conflicts.map((c: any) => (
              <div key={c.conflict_id || c.topic} className="bg-slate-900 border border-amber-500/30 rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Contradiction: {c.topic}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase">Statement A</span>
                    <p className="text-slate-300 mt-1">{c.statement_a}</p>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase">Statement B</span>
                    <p className="text-slate-300 mt-1">{c.statement_b}</p>
                  </div>
                </div>
                <p className="text-xs text-amber-300/90 pt-1">
                  <b>Resolution Guidance:</b> {c.suggested_resolution || 'Confirm authoritative ceiling with Delivery Manager prior to sprint kickoff.'}
                </p>
              </div>
            ))}

            {questions.map((q: any) => (
              <div key={q.id || q.question} className="bg-slate-900 border border-indigo-500/30 rounded-xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400">
                  <HelpCircle className="h-4 w-4" />
                  <span>Open Clarification ({q.topic || 'Architecture'})</span>
                </div>
                <p className="text-xs text-slate-200">{q.question}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'scope' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                <Layers className="h-4 w-4 text-emerald-400" />
                <span>Explicitly In-Scope Deliverables</span>
              </h4>
              <ul className="space-y-2 text-xs text-slate-300">
                {(scope.scope_inclusions || scope.deliverables || []).map((item: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{typeof item === 'object' ? (item as any).statement : item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h4 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                <Shield className="h-4 w-4 text-rose-400" />
                <span>Explicitly Out-of-Scope / Prohibited Boundaries</span>
              </h4>
              <ul className="space-y-2 text-xs text-slate-300">
                {(scope.scope_exclusions || []).map((item: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2 text-rose-300/80">
                    <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0 mt-1.5" />
                    <span>{typeof item === 'object' ? (item as any).statement : item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
