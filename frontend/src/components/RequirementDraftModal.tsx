import React, { useState } from 'react';
import { RequirementDraftResponse } from '../types/requirement';
import { api } from '../services/api';
import {
  X,
  Sparkles,
  ShieldAlert,
  HelpCircle,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  FileCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Cpu,
} from 'lucide-react';

interface Props {
  draft: RequirementDraftResponse | null;
  onClose: () => void;
  onUpdateDraft?: (updated: RequirementDraftResponse) => void;
}

export const RequirementDraftModal: React.FC<Props> = ({ draft, onClose, onUpdateDraft }) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'functional' | 'non_functional' | 'risks' | 'review'>('summary');
  const [showAttempts, setShowAttempts] = useState(false);
  const [managerNotes, setManagerNotes] = useState(draft?.manager_notes || '');
  const [reviewStatus, setReviewStatus] = useState<'pending_review' | 'approved' | 'rejected'>(
    draft?.review_status || 'pending_review'
  );
  const [savingReview, setSavingReview] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  if (!draft) return null;

  const reqs = draft.requirements;
  const isOffline =
    draft.provider_used.toLowerCase().includes('offline') ||
    draft.provider_used.toLowerCase().includes('deterministic') ||
    draft.model_used.toLowerCase().includes('deterministic') ||
    draft.model_used.toLowerCase().includes('mock');

  const handleSaveReview = async () => {
    setSavingReview(true);
    setSaveSuccess(null);
    try {
      const updated = await api.updateManagerReview(draft.id, reviewStatus, managerNotes);
      if (onUpdateDraft) onUpdateDraft(updated);
      setSaveSuccess('Manager review decision recorded successfully.');
    } catch (err: any) {
      alert(`Failed to save review: ${err.message}`);
    } finally {
      setSavingReview(false);
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">High Confidence</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Medium Confidence</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Low / Inferred</span>;
    }
  };

  const getReviewBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />
            Manager Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5 mr-1 text-rose-400" />
            Revision Requested
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5 mr-1 text-amber-400" />
            Pending Review
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg ${
              isOffline
                ? 'bg-gradient-to-br from-amber-500 to-orange-600 shadow-amber-500/20'
                : 'bg-gradient-to-br from-indigo-500 to-purple-600 shadow-indigo-500/20'
            }`}>
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-white truncate max-w-md">
                  {draft.document_name}
                </h3>
                {isOffline ? (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    Offline Demo Mode
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    {draft.provider_used.replace('_', ' ')}
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-[11px] font-mono text-slate-400 bg-slate-800 border border-slate-700">
                  {draft.model_used}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {isOffline
                  ? 'Deterministic Demo Output • Not live AI generated'
                  : `AI Requirement Draft • Generated ${new Date(draft.created_at).toLocaleDateString()}`}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {getReviewBadge(draft.review_status)}

            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Prominent Offline Demo Mode Notice */}
        {isOffline && (
          <div className="px-6 py-2.5 bg-amber-950/40 border-b border-amber-800/40 flex items-center justify-between text-xs text-amber-300">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Deterministic Demonstration Mode:</strong> Generated offline without invoking live cloud AI credentials.
              </span>
            </div>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-900/50 text-amber-200 border border-amber-700/50">
              Offline Mock
            </span>
          </div>
        )}

        {/* Fallback Attempt History Banner / Accordion */}
        <div className="px-6 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs flex flex-col">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-300">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>
                Resolved via <strong className="text-white capitalize">{draft.provider_used}</strong> after{' '}
                {(draft.attempt_history || []).length} routing {(draft.attempt_history || []).length === 1 ? 'attempt' : 'attempts'}
              </span>
              {reqs && (
                <span className="text-slate-400 ml-2">
                  &bull; Confidence Score: <strong className="text-emerald-400">{Math.round(reqs.overall_confidence * 100)}%</strong>
                </span>
              )}
            </div>
            <button
              onClick={() => setShowAttempts(!showAttempts)}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center font-medium"
            >
              {showAttempts ? 'Hide Telemetry' : 'View Routing Telemetry'}
              {showAttempts ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
            </button>
          </div>

          {showAttempts && (
            <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
              <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                Multi-Provider Fallback Trace:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {(draft.attempt_history || []).map((att, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg border text-[11px] font-mono ${
                      att.status === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : att.status === 'skipped'
                        ? 'bg-slate-800/40 border-slate-800 text-slate-400'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span className="capitalize">{att.provider}</span>
                      <span className="uppercase text-[10px]">{att.status}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 truncate mt-0.5">{att.model}</p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {att.duration_ms}ms {att.error_category ? `(${att.error_category})` : ''}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="px-6 border-b border-slate-800/80 bg-slate-950/40 flex space-x-1 overflow-x-auto text-xs">
          {[
            { id: 'summary', label: 'Summary & Scope', icon: Layers },
            { id: 'functional', label: `Functional Requirements (${reqs?.functional_requirements?.length || 0})`, icon: FileCheck },
            { id: 'non_functional', label: `Non-Functional (${reqs?.non_functional_requirements?.length || 0})`, icon: ShieldAlert },
            { id: 'risks', label: `Risks & Clarifications (${(reqs?.risks?.length || 0) + (reqs?.missing_information?.length || 0)})`, icon: AlertTriangle },
            { id: 'review', label: 'Manager Review & Sign-off', icon: CheckCircle2 },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-3.5 border-b-2 font-medium flex items-center space-x-2 transition ${
                  isActive
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Area */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-900/30">
          {!reqs ? (
            <div className="h-full flex items-center justify-center text-slate-500">
              No structured requirements payload available for this draft.
            </div>
          ) : activeTab === 'summary' ? (
            <div className="space-y-6">
              {/* Executive Summary */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-2">
                  Executive Summary
                </h4>
                <p className="text-sm text-slate-300 leading-relaxed font-sans">
                  {reqs.project_summary}
                </p>
              </div>

              {/* Objectives */}
              {reqs.objectives?.length > 0 && (
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
                    Project Objectives
                  </h4>
                  <ul className="space-y-2">
                    {reqs.objectives.map((obj, i) => (
                      <li key={i} className="flex items-start text-sm text-slate-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-2 mr-2.5 flex-shrink-0" />
                        <span>{obj}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Scope Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <h4 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                    Scope Inclusions
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {reqs.scope?.scope_inclusions?.map((inc, i) => (
                      <li key={i} className="flex items-center">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mr-2 flex-shrink-0" />
                        <span>{inc}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <h4 className="text-sm font-semibold text-rose-400 uppercase tracking-wider mb-2">
                    Scope Exclusions
                  </h4>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {reqs.scope?.scope_exclusions?.map((exc, i) => (
                      <li key={i} className="flex items-center">
                        <XCircle className="w-3.5 h-3.5 text-rose-400 mr-2 flex-shrink-0" />
                        <span>{exc}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Deliverables & Constraints */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Deliverables</h5>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {reqs.scope?.deliverables?.map((d, i) => <li key={i}>&bull; {d}</li>)}
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Constraints</h5>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {reqs.constraints?.map((c, i) => <li key={i}>&bull; {c}</li>)}
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Dependencies</h5>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {reqs.dependencies?.map((d, i) => <li key={i}>&bull; {d}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          ) : activeTab === 'functional' ? (
            <div className="space-y-4">
              {reqs.functional_requirements?.map((req) => (
                <div
                  key={req.id}
                  className={`p-5 rounded-xl border transition ${
                    req.needs_verification
                      ? 'bg-amber-500/5 border-amber-500/30'
                      : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="flex items-center space-x-2.5">
                      <span className="px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-indigo-600 text-white shadow-sm">
                        {req.id}
                      </span>
                      <h4 className="text-base font-semibold text-white">{req.title}</h4>
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300">
                        {req.category}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getConfidenceBadge(req.confidence)}
                      {req.needs_verification && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center">
                          <AlertTriangle className="w-3 h-3 mr-1 text-amber-400" />
                          Needs Verification
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-slate-300 leading-relaxed mb-3">
                    {req.description}
                  </p>

                  {req.needs_verification && req.verification_reason && (
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 mb-3">
                      <strong>Verification Note:</strong> {req.verification_reason}
                    </div>
                  )}

                  {/* Provenance Citations */}
                  {req.source_references?.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="font-semibold text-slate-500">Source:</span>
                      {req.source_references.map((src, sIdx) => (
                        <span
                          key={sIdx}
                          className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300"
                        >
                          {src.location} {src.excerpt ? `— "${src.excerpt}"` : ''}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : activeTab === 'non_functional' ? (
            <div className="space-y-4">
              {reqs.non_functional_requirements?.map((req) => (
                <div
                  key={req.id}
                  className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-purple-600 text-white">
                        {req.id}
                      </span>
                      <h4 className="text-base font-semibold text-white">{req.title}</h4>
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300">
                        {req.category}
                      </span>
                    </div>
                    {getConfidenceBadge(req.confidence)}
                  </div>
                  <p className="text-sm text-slate-300">{req.description}</p>
                  {req.source_references?.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 text-xs text-slate-400">
                      <span className="font-semibold text-slate-500">Citation:</span>
                      {req.source_references.map((src, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300">
                          {src.location}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : activeTab === 'risks' ? (
            <div className="space-y-6">
              {/* Risks Section */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-1.5 text-rose-400" />
                  Identified Risks ({reqs.risks?.length || 0})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {reqs.risks?.map((risk) => (
                    <div key={risk.id} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-slate-400">{risk.id}</span>
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                          risk.severity === 'high' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {risk.severity} Severity
                        </span>
                      </div>
                      <p className="text-xs text-slate-200">{risk.description}</p>
                      {risk.mitigation_hint && (
                        <p className="text-[11px] text-emerald-400/90 pt-1 border-t border-slate-800/60">
                          <strong>Mitigation:</strong> {risk.mitigation_hint}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing Information / Questions Section */}
              <div className="space-y-3 pt-4 border-t border-slate-800">
                <h4 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center">
                  <HelpCircle className="w-4 h-4 mr-1.5 text-indigo-400" />
                  Missing Information & Stakeholder Clarifications ({reqs.missing_information?.length || 0})
                </h4>
                <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300">
                  <strong>Notice:</strong> These gaps are explicitly identified as missing from the document and must NOT be treated as confirmed facts until answered by project leadership.
                </div>
                <div className="space-y-2">
                  {reqs.missing_information?.map((item) => (
                    <div key={item.id} className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start space-x-3">
                      <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-slate-800 text-indigo-300">
                        {item.id}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold text-white">{item.topic}</span>
                          <span className="text-[11px] uppercase font-bold text-amber-400">{item.impact} Impact</span>
                        </div>
                        <p className="text-xs text-slate-300">{item.question}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Manager Review Tab */
            <div className="space-y-6 max-w-2xl mx-auto">
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div>
                  <h4 className="text-base font-semibold text-white mb-1">
                    Manager Review & Sign-Off
                  </h4>
                  <p className="text-xs text-slate-400">
                    AI-extracted requirements are proposed drafts. Human verification is required before committing to sprint planning.
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Review Decision</label>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      type="button"
                      onClick={() => setReviewStatus('approved')}
                      className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center space-y-1 transition ${
                        reviewStatus === 'approved'
                          ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <span>Approve Draft</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setReviewStatus('rejected')}
                      className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center space-y-1 transition ${
                        reviewStatus === 'rejected'
                          ? 'bg-rose-500/20 border-rose-500 text-rose-300 shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <XCircle className="w-5 h-5 text-rose-400" />
                      <span>Request Changes</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setReviewStatus('pending_review')}
                      className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center justify-center space-y-1 transition ${
                        reviewStatus === 'pending_review'
                          ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <Clock className="w-5 h-5 text-amber-400" />
                      <span>Keep Pending</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300">Manager Notes & Feedback</label>
                  <textarea
                    rows={4}
                    value={managerNotes}
                    onChange={(e) => setManagerNotes(e.target.value)}
                    placeholder="Enter approval conditions, scope adjustments, or stakeholder instructions..."
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {saveSuccess && (
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span>{saveSuccess}</span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleSaveReview}
                  disabled={savingReview}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition disabled:opacity-50"
                >
                  {savingReview ? 'Saving Decision...' : 'Commit Review Decision'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <span>DevMatrix AI &bull; Module 2 Requirement Extraction</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
