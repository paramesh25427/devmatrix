import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  CheckCircle2,
  Sparkles,
  AlertCircle,
  Shield,
  XCircle,
  Tag,
  BarChart3,
  Layers,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  UserCheck,
  UserPlus,
  History,
  Power,
  X,
  Award,
  Check,
} from 'lucide-react';
import {
  WorkforceMember,
  TeamRecommendation,
  TeamCapacitySummary,
  SkillGapAnalysis,
  AlternativeCandidate,
  OnboardMemberRequest,
  MemberPerformanceEvidence,
  MemberPerformanceScoreHistory,
} from '../types/workforce';
import { api } from '../services/api';

interface WorkforceViewProps {
  workforce: WorkforceMember[];
  recommendations: TeamRecommendation[];
  projectId: string;
  userRole?: string;
  onRefresh: () => void;
}

const COMMON_ROLES = [
  'Full-Stack Engineer',
  'Senior Full-Stack Engineer',
  'Solutions Architect',
  'Backend Python Engineer',
  'Frontend React Engineer',
  'QA Automation Engineer',
  'Cloud DevOps Architect',
  'DevOps / SRE',
  'Data Engineer',
  'Product / Business Analyst',
  'Security Engineer',
];

const PROFICIENCY_LEVELS = ['Expert', 'Advanced', 'Intermediate', 'Novice'];

export const WorkforceView: React.FC<WorkforceViewProps> = ({
  workforce,
  recommendations,
  projectId,
  userRole,
  onRefresh,
}) => {
  const isManager = !userRole || userRole === 'delivery_manager' || userRole === 'tenant_admin';

  const [activeSubTab, setActiveSubTab] = useState<'recommendations' | 'capacity' | 'skill-gaps' | 'directory'>('recommendations');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [expandedAltId, setExpandedAltId] = useState<string | null>(null);

  // Workforce v2 State: Dynamic Capacity & Skill Gaps
  const [capacityData, setCapacityData] = useState<TeamCapacitySummary | null>(null);
  const [capacityLoading, setCapacityLoading] = useState<boolean>(false);
  const [skillGapData, setSkillGapData] = useState<SkillGapAnalysis | null>(null);
  const [skillGapLoading, setSkillGapLoading] = useState<boolean>(false);

  // Onboarding Modal State
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);
  const [onboardForm, setOnboardForm] = useState<{
    full_name: string;
    role: string;
    hourly_rate: number;
    skills_text: string;
    skill_proficiencies: Record<string, string>;
    experience_years: number;
    availability_pct: number;
    max_weekly_hours: number;
    initial_assessed_score: number;
  }>({
    full_name: '',
    role: 'Full-Stack Engineer',
    hourly_rate: 95.0,
    skills_text: 'Python, FastAPI, React',
    skill_proficiencies: { Python: 'Advanced', FastAPI: 'Advanced', React: 'Intermediate' },
    experience_years: 5.0,
    availability_pct: 100.0,
    max_weekly_hours: 40.0,
    initial_assessed_score: 85.0,
  });
  const [onboardSubmitting, setOnboardSubmitting] = useState<boolean>(false);
  const [onboardError, setOnboardError] = useState<string>('');

  // Performance Score History & Corrections Modal State
  const [selectedMemberForHistory, setSelectedMemberForHistory] = useState<WorkforceMember | null>(null);
  const [historyRecords, setHistoryRecords] = useState<MemberPerformanceScoreHistory[]>([]);
  const [evidenceRecords, setEvidenceRecords] = useState<MemberPerformanceEvidence[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [historyActiveTab, setHistoryActiveTab] = useState<'history' | 'evidence' | 'correction'>('history');
  const [correctionScore, setCorrectionScore] = useState<number>(90.0);
  const [correctionReason, setCorrectionReason] = useState<string>('');
  const [correctionSubmitting, setCorrectionSubmitting] = useState<boolean>(false);
  const [correctionSuccessMsg, setCorrectionSuccessMsg] = useState<string>('');
  const [correctionErrorMsg, setCorrectionErrorMsg] = useState<string>('');

  // Load Capacity Data
  const loadCapacity = useCallback(async () => {
    if (!projectId) return;
    setCapacityLoading(true);
    try {
      const data = await api.getWorkforceCapacity(projectId);
      setCapacityData(data);
    } catch {
      // Handled gracefully
    } finally {
      setCapacityLoading(false);
    }
  }, [projectId]);

  // Load Skill Gap Analysis
  const loadSkillGaps = useCallback(async () => {
    if (!projectId) return;
    setSkillGapLoading(true);
    try {
      const data = await api.getSkillGapAnalysis(projectId);
      setSkillGapData(data);
    } catch {
      // Handled gracefully
    } finally {
      setSkillGapLoading(false);
    }
  }, [projectId]);

  // Fetch v2 data on tab change or project change
  useEffect(() => {
    if (activeSubTab === 'capacity') {
      loadCapacity();
    } else if (activeSubTab === 'skill-gaps') {
      loadSkillGaps();
    }
  }, [activeSubTab, loadCapacity, loadSkillGaps]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setErrorMsg('');
    try {
      await api.generateRecommendations(projectId);
      onRefresh();
      loadCapacity();
      loadSkillGaps();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate recommendations');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApprove = async (recId: string) => {
    setActionLoadingId(recId);
    setErrorMsg('');
    try {
      await api.approveRecommendation(recId);
      onRefresh();
      loadCapacity();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to approve recommendation');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReject = async (recId: string) => {
    setActionLoadingId(recId);
    setErrorMsg('');
    try {
      await api.rejectRecommendation(recId, 'Declined by delivery manager during team review');
      onRefresh();
      loadCapacity();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reject recommendation');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSelectAlternative = async (recId: string, alt: AlternativeCandidate) => {
    setActionLoadingId(recId);
    setErrorMsg('');
    try {
      await api.selectAlternativeCandidate(
        recId,
        alt.candidate_id,
        `Selected runner-up alternative (${alt.candidate_name}, ${alt.match_score}% fit) by delivery manager`
      );
      setExpandedAltId(null);
      onRefresh();
      loadCapacity();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to select alternative candidate');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Open Score History Modal
  const handleOpenScoreHistory = async (member: WorkforceMember) => {
    setSelectedMemberForHistory(member);
    setHistoryLoading(true);
    setHistoryActiveTab('history');
    setCorrectionScore(member.performance_score || member.initial_assessed_score || 85.0);
    setCorrectionReason('');
    setCorrectionSuccessMsg('');
    setCorrectionErrorMsg('');
    try {
      const [hist, ev] = await Promise.all([
        api.getMemberScoreHistory(member.id).catch(() => []),
        api.getMemberEvidence(member.id).catch(() => []),
      ]);
      setHistoryRecords(hist);
      setEvidenceRecords(ev);
    } catch {
      // Handled gracefully
    } finally {
      setHistoryLoading(false);
    }
  };

  // Toggle Member Active / Deactivate
  const handleToggleMemberActive = async (member: WorkforceMember) => {
    setActionLoadingId(member.id);
    try {
      if (member.is_active === false) {
        await api.activateWorkforceMember(member.id);
      } else {
        await api.deactivateWorkforceMember(member.id);
      }
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to toggle member status');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Submit Score Correction
  const handleScoreCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMemberForHistory) return;
    setCorrectionSubmitting(true);
    setCorrectionSuccessMsg('');
    setCorrectionErrorMsg('');
    try {
      const updatedScore = await api.correctMemberScore(selectedMemberForHistory.id, {
        corrected_score: Number(correctionScore),
        reason: correctionReason,
      });
      setCorrectionSuccessMsg(`Correction applied successfully (v${updatedScore.score_version}). Audit log created.`);
      const [hist, ev] = await Promise.all([
        api.getMemberScoreHistory(selectedMemberForHistory.id).catch(() => []),
        api.getMemberEvidence(selectedMemberForHistory.id).catch(() => []),
      ]);
      setHistoryRecords(hist);
      setEvidenceRecords(ev);
      onRefresh();
    } catch (err: any) {
      setCorrectionErrorMsg(err.message || 'Failed to submit score correction');
    } finally {
      setCorrectionSubmitting(false);
    }
  };

  // Submit Onboard Member Form
  const handleOnboardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOnboardSubmitting(true);
    setOnboardError('');
    try {
      const parsedSkills = onboardForm.skills_text
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const payload: OnboardMemberRequest = {
        full_name: onboardForm.full_name,
        role: onboardForm.role,
        hourly_rate: Number(onboardForm.hourly_rate),
        skills: parsedSkills,
        skill_proficiencies: onboardForm.skill_proficiencies,
        experience_years: Number(onboardForm.experience_years),
        availability_pct: Number(onboardForm.availability_pct),
        max_weekly_hours: Number(onboardForm.max_weekly_hours),
        initial_assessed_score: Number(onboardForm.initial_assessed_score),
      };

      await api.createWorkforceMember(payload);
      setIsOnboardingOpen(false);
      onRefresh();
    } catch (err: any) {
      setOnboardError(err.message || 'Failed to onboard team member');
    } finally {
      setOnboardSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded-full border border-indigo-500/20">
              Module 7 &bull; Workforce Intelligence v2
            </span>
            <span className="text-xs text-slate-400">
              Onboarding &bull; Verified Performance Scoring &bull; Workload Heatmap
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-2">
            Workforce Allocation & Performance Intelligence
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Automatic outcome-based performance scoring (Delivery & Quality) feeding future recommendations, manager onboarding with skill proficiencies, and non-intrusive project tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isManager && (
            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="flex items-center justify-center gap-2 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold border border-slate-700 transition cursor-pointer"
            >
              <UserPlus className="h-4 w-4 text-emerald-400" />
              <span>Onboard Member</span>
            </button>
          )}

          <button
            onClick={handleGenerate}
            disabled={isGenerating || !projectId}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            <Sparkles className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>{isGenerating ? 'Computing Recommendations...' : 'Generate Recommendations'}</span>
          </button>
        </div>
      </div>

      {/* Ethical Guardrail Alert */}
      <div className="bg-slate-900/60 border border-indigo-500/20 rounded-xl p-4 flex items-center gap-3 text-xs text-indigo-300">
        <Shield className="h-5 w-5 text-indigo-400 shrink-0" />
        <div>
          <span className="font-semibold text-white">Ethical Delivery Intelligence Guarantee:</span>{' '}
          Zero covert surveillance, keystroke logging, or screen recording. Performance scores are computed exclusively from objective deliverables (on-time milestones, effort variance, and test outcomes). Project managers retain final assignment authority.
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Subtab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveSubTab('recommendations')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeSubTab === 'recommendations'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Team Recommendations ({recommendations.length})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('capacity')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeSubTab === 'capacity'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <BarChart3 className="h-3.5 w-3.5" />
          <span>Workload & Capacity</span>
          {capacityData && capacityData.overallocated_members_count > 0 && (
            <span className="bg-rose-500/20 text-rose-300 text-[10px] px-1.5 py-0.2 rounded font-bold border border-rose-500/30">
              {capacityData.overallocated_members_count} over
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveSubTab('skill-gaps')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeSubTab === 'skill-gaps'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          <span>Skill Gap Matrix</span>
          {skillGapData && (
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold border ${
              skillGapData.health_status === 'healthy'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                : skillGapData.health_status === 'critical'
                ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
            }`}>
              {skillGapData.skill_coverage_score}%
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveSubTab('directory')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeSubTab === 'directory'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          <span>Talent Directory ({workforce.length})</span>
        </button>
      </div>

      {/* SUBTAB 1: RECOMMENDATIONS */}
      {activeSubTab === 'recommendations' && (
        <div className="space-y-4">
          {recommendations.length === 0 ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
              <Users className="h-12 w-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-300">No Recommendations Generated Yet</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                Click Generate Recommendations above to match available talent against required WBS roles using our multi-factor scoring model.
              </p>
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !projectId}
                className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer disabled:cursor-not-allowed"
              >
                Generate Team Candidates
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendations.map((rec) => {
                const isApproved = rec.manager_status === 'approved';
                const isRejected = rec.manager_status === 'rejected';
                const isActionLoading = actionLoadingId === rec.id;
                const alternatives = rec.alternatives || [];
                const isAltExpanded = expandedAltId === rec.id;
                const hasVerifiedPerf = rec.performance_score != null;

                return (
                  <div
                    key={rec.id}
                    data-testid={`rec-card-${rec.id}`}
                    className={`bg-slate-900 border rounded-xl p-5 flex flex-col justify-between transition-all ${
                      isApproved
                        ? 'border-emerald-500/40 shadow-sm shadow-emerald-500/5'
                        : isRejected
                        ? 'border-rose-500/30 opacity-75'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      {/* Card Header: Task & Role Information */}
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {rec.task_code && (
                              <span className="text-[11px] font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                                {rec.task_code}
                              </span>
                            )}
                            <span className="text-[11px] font-semibold text-slate-300 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                              {rec.role_needed}
                            </span>
                            {rec.is_synthetic ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                                <Tag className="h-2.5 w-2.5" />
                                <span>Synthetic Demo</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-300 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                                <UserCheck className="h-2.5 w-2.5" />
                                <span>Real Profile</span>
                              </span>
                            )}
                          </div>
                          <h4 className="text-base font-bold text-white mt-2">
                            {rec.candidate_name}
                          </h4>
                          {rec.task_title && (
                            <p className="text-xs text-slate-400 mt-0.5 font-medium">
                              Task: {rec.task_title}
                            </p>
                          )}
                        </div>

                        {/* Match & Performance Score Badges */}
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center gap-1 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
                            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                            <span className="text-sm font-bold text-white">{rec.match_score}%</span>
                            <span className="text-[10px] text-slate-500">fit</span>
                          </div>
                          {hasVerifiedPerf ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                              <Award className="h-3 w-3" />
                              <span>{rec.performance_score}% Verified</span>
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                              Insufficient history
                            </span>
                          )}
                          <span className={`text-[10px] font-semibold uppercase mt-0.5 ${
                            isApproved
                              ? 'text-emerald-400'
                              : isRejected
                              ? 'text-rose-400'
                              : 'text-amber-400'
                          }`}>
                            {rec.manager_status}
                          </span>
                        </div>
                      </div>

                      {/* Factor Breakdown */}
                      {hasVerifiedPerf ? (
                        <div className="grid grid-cols-5 gap-1.5 mt-4 p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 text-center text-xs">
                          <div>
                            <p className="text-[9px] text-slate-500 uppercase">Skill (35%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.skill_score}%</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-emerald-400 uppercase font-semibold">Perf (20%)</p>
                            <p className="font-bold text-emerald-300 mt-0.5">{rec.performance_score}%</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-slate-500 uppercase">Avail (25%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.availability_score}%</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-slate-500 uppercase">Exp (10%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.experience_score}%</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-slate-500 uppercase">Work (10%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.workload_score}%</p>
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-4 gap-2 mt-4 p-3 bg-slate-950 rounded-lg border border-slate-800/80 text-center text-xs">
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">Skill (40%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.skill_score}%</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">Avail (30%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.availability_score}%</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">Exp (20%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.experience_score}%</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">Workload (10%)</p>
                            <p className="font-bold text-slate-200 mt-0.5">{rec.workload_score}%</p>
                          </div>
                        </div>
                      )}

                      {/* Explainable Rationale */}
                      <div className="mt-3 p-2.5 rounded bg-slate-950/70 border border-slate-800/70 text-xs text-slate-400 leading-relaxed">
                        <span className="text-slate-300 font-semibold">Recommendation Rationale: </span>
                        {rec.rationale}
                      </div>

                      {rec.manager_notes && (
                        <div className="mt-2 text-xs text-slate-400 italic">
                          <span className="font-semibold text-slate-500">Manager Notes: </span>
                          {rec.manager_notes}
                        </div>
                      )}

                      {/* Workforce v2: Runner-up / Alternative Candidates Section */}
                      {alternatives.length > 0 && (
                        <div className="mt-3 border-t border-slate-800/60 pt-2.5">
                          <button
                            type="button"
                            onClick={() => setExpandedAltId(isAltExpanded ? null : rec.id)}
                            className="flex items-center justify-between w-full text-xs text-indigo-400 hover:text-indigo-300 transition-colors py-1 cursor-pointer"
                          >
                            <span className="flex items-center gap-1 font-semibold">
                              <Users className="h-3.5 w-3.5" />
                              <span>{alternatives.length} Alternative Candidates Evaluated</span>
                            </span>
                            {isAltExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>

                          {isAltExpanded && (
                            <div className="mt-2 space-y-2">
                              {alternatives.map((alt) => (
                                <div
                                  key={alt.candidate_id}
                                  className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs"
                                >
                                  <div className="space-y-0.5">
                                    <div className="flex items-center gap-2">
                                      <span className="font-semibold text-white">{alt.candidate_name}</span>
                                      <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-1.5 py-0.2 rounded border border-indigo-500/20">
                                        {alt.match_score}% fit
                                      </span>
                                      {alt.performance_score != null && (
                                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                                          {alt.performance_score}% perf
                                        </span>
                                      )}
                                      {alt.hourly_rate && (
                                        <span className="text-[10px] text-slate-400">
                                          ${alt.hourly_rate}/hr
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-[11px] text-slate-400 line-clamp-2">
                                      {alt.rationale}
                                    </p>
                                  </div>

                                  <button
                                    onClick={() => handleSelectAlternative(rec.id, alt)}
                                    disabled={isActionLoading || isApproved}
                                    className="px-2.5 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded text-[11px] font-semibold transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap self-end md:self-center"
                                  >
                                    Select Alternative
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action Buttons: Manager Approval Controls */}
                    <div className="flex items-center justify-end gap-2 mt-5 pt-3 border-t border-slate-800/80">
                      <button
                        onClick={() => handleReject(rec.id)}
                        disabled={isActionLoading || isRejected}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 rounded-lg text-xs font-semibold transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                      <button
                        onClick={() => handleApprove(rec.id)}
                        disabled={isActionLoading || isApproved}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Accept & Assign</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: WORKLOAD & CAPACITY */}
      {activeSubTab === 'capacity' && (
        <div className="space-y-5">
          {capacityLoading ? (
            <div className="p-12 text-center text-slate-500 text-xs">Computing real-time team workload and capacity...</div>
          ) : !capacityData ? (
            <div className="p-8 text-center text-slate-400 text-xs">No capacity data available for this project.</div>
          ) : (
            <>
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Total Nominal Capacity</p>
                  <p className="text-xl font-bold text-white mt-1">{capacityData.total_nominal_capacity_hours}h</p>
                  <span className="text-[11px] text-slate-500">{capacityData.total_members} team members</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Planned Project Effort</p>
                  <p className="text-xl font-bold text-indigo-400 mt-1">{capacityData.total_planned_effort_hours}h</p>
                  <span className="text-[11px] text-slate-500">Across assigned WBS tasks</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Team Utilization</p>
                  <p className={`text-xl font-bold mt-1 ${
                    capacityData.team_utilization_pct > 100
                      ? 'text-rose-400'
                      : capacityData.team_utilization_pct > 80
                      ? 'text-emerald-400'
                      : 'text-amber-400'
                  }`}>
                    {capacityData.team_utilization_pct}%
                  </p>
                  <span className="text-[11px] text-slate-500">Target: 70–85% optimal</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Over-allocated Members</p>
                  <p className={`text-xl font-bold mt-1 ${
                    capacityData.overallocated_members_count > 0 ? 'text-rose-400' : 'text-emerald-400'
                  }`}>
                    {capacityData.overallocated_members_count}
                  </p>
                  <span className="text-[11px] text-slate-500">Exceeding nominal weekly limit</span>
                </div>
              </div>

              {/* Over-allocation Warning Banner */}
              {capacityData.overallocated_members_count > 0 && (
                <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-start gap-3 text-xs text-rose-300">
                  <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-white">Capacity Warning: </span>
                    {capacityData.overallocated_members_count} contributor(s) are allocated beyond their nominal weekly availability ({capacityData.overallocated_members.join(', ')}). Consider redistributing tasks to runner-up candidates or adjusting schedule targets.
                  </div>
                </div>
              )}

              {/* Member Workload Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Contributor Workload & Allocation Heatmap</h3>
                  <span className="text-xs text-slate-400">{capacityData.members.length} contributors</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="py-3 px-4">Contributor</th>
                        <th className="py-3 px-4">Role</th>
                        <th className="py-3 px-4 text-center">Nominal Cap.</th>
                        <th className="py-3 px-4 text-center">Project Effort</th>
                        <th className="py-3 px-4 text-center">Tasks</th>
                        <th className="py-3 px-4">Utilization</th>
                        <th className="py-3 px-4 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {capacityData.members.map((m) => {
                        const isOver = m.is_overallocated;
                        const isOpt = m.status_level === 'optimal';

                        return (
                          <tr key={m.member_id} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-white">
                              {m.full_name}
                            </td>
                            <td className="py-3.5 px-4 text-slate-300">
                              {m.role}
                            </td>
                            <td className="py-3.5 px-4 text-center font-mono">
                              {m.nominal_weekly_hours}h/wk
                            </td>
                            <td className="py-3.5 px-4 text-center font-mono font-bold text-indigo-400">
                              {m.total_planned_hours}h
                            </td>
                            <td className="py-3.5 px-4 text-center font-mono">
                              {m.assigned_tasks_count}
                            </td>
                            <td className="py-3.5 px-4 min-w-[140px]">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                                  <div
                                    className={`h-full rounded-full transition-all ${
                                      isOver
                                        ? 'bg-rose-500'
                                        : isOpt
                                        ? 'bg-emerald-500'
                                        : 'bg-amber-400'
                                    }`}
                                    style={{ width: `${Math.min(m.utilization_pct, 100)}%` }}
                                  />
                                </div>
                                <span className={`text-[11px] font-mono font-bold ${
                                  isOver ? 'text-rose-400' : isOpt ? 'text-emerald-400' : 'text-slate-400'
                                }`}>
                                  {m.utilization_pct}%
                                </span>
                              </div>
                            </td>
                            <td className="py-3.5 px-4 text-center whitespace-nowrap">
                              <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                                isOver
                                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                  : isOpt
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              }`}>
                                {isOver ? `+${m.overallocated_hours}h over` : m.status_level}
                              </span>
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
      )}

      {/* SUBTAB 3: SKILL GAP MATRIX */}
      {activeSubTab === 'skill-gaps' && (
        <div className="space-y-5">
          {skillGapLoading ? (
            <div className="p-12 text-center text-slate-500 text-xs">Evaluating competency coverage across WBS tasks...</div>
          ) : !skillGapData ? (
            <div className="p-8 text-center text-slate-400 text-xs">No skill gap data available for this project.</div>
          ) : (
            <>
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Overall Coverage Score</p>
                  <p className={`text-xl font-bold mt-1 ${
                    skillGapData.health_status === 'healthy'
                      ? 'text-emerald-400'
                      : skillGapData.health_status === 'critical'
                      ? 'text-rose-400'
                      : 'text-amber-400'
                  }`}>
                    {skillGapData.skill_coverage_score}%
                  </p>
                  <span className="text-[11px] text-slate-500 capitalize">{skillGapData.health_status} coverage</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Required Skills</p>
                  <p className="text-xl font-bold text-white mt-1">{skillGapData.total_skills_required}</p>
                  <span className="text-[11px] text-slate-500">Identified from WBS roles</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Fully Covered</p>
                  <p className="text-xl font-bold text-emerald-400 mt-1">{skillGapData.covered_skills_count}</p>
                  <span className="text-[11px] text-slate-500">2+ qualified team members</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <p className="text-xs text-slate-400 font-medium">Scarce or Missing</p>
                  <p className={`text-xl font-bold mt-1 ${
                    skillGapData.missing_skills_count > 0 ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    {skillGapData.missing_skills_count + skillGapData.scarce_skills_count}
                  </p>
                  <span className="text-[11px] text-slate-500">
                    {skillGapData.missing_skills_count} missing, {skillGapData.scarce_skills_count} single-point
                  </span>
                </div>
              </div>

              {/* Upskilling & Hiring Signals Banner */}
              {skillGapData.upskilling_signals && skillGapData.upskilling_signals.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-xs text-amber-200 space-y-1.5">
                  <div className="flex items-center gap-2 font-bold text-white">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <span>Upskilling & Capacity Signals:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300 ml-1">
                    {skillGapData.upskilling_signals.map((sig, i) => (
                      <li key={i}>{sig}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Skills Coverage Breakdown Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Competency Coverage Matrix</h3>
                  <span className="text-xs text-slate-400">{skillGapData.skills.length} skills analyzed</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                      <tr>
                        <th className="py-3 px-4">Required Competency</th>
                        <th className="py-3 px-4 text-center">WBS Tasks</th>
                        <th className="py-3 px-4">Qualified Team Members</th>
                        <th className="py-3 px-4 text-center">Coverage Level</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {skillGapData.skills.map((item) => {
                        const isMissing = item.coverage_status === 'missing';
                        const isScarce = item.coverage_status === 'scarce';

                        return (
                          <tr key={item.skill} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-white whitespace-nowrap">
                              {item.skill}
                            </td>
                            <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-300">
                              {item.tasks_count}
                            </td>
                            <td className="py-3.5 px-4">
                              {item.qualified_members.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {item.qualified_members.map((m) => (
                                    <span
                                      key={m.id}
                                      className="inline-flex items-center gap-1 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-[11px] text-slate-300"
                                    >
                                      <span className="font-semibold text-white">{m.name}</span>
                                      <span className="text-slate-500">({m.experience_years}y, {m.availability_pct}%)</span>
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-slate-500 italic text-[11px]">
                                  No internal talent matches found
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-center whitespace-nowrap">
                              <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                                isMissing
                                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                  : isScarce
                                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                  : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              }`}>
                                {item.coverage_status}
                              </span>
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
      )}

      {/* SUBTAB 4: TALENT DIRECTORY */}
      {activeSubTab === 'directory' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Talent Directory & Capacity Registry</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {workforce.length} verified contributors with attributable performance baselines
              </p>
            </div>
            {isManager && (
              <button
                onClick={() => setIsOnboardingOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition cursor-pointer self-start sm:self-auto"
              >
                <UserPlus className="h-3.5 w-3.5" />
                <span>Onboard Contributor</span>
              </button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Contributor</th>
                  <th className="py-3 px-4">Primary Role</th>
                  <th className="py-3 px-4">Skills & Proficiency</th>
                  <th className="py-3 px-4 text-center">Experience</th>
                  <th className="py-3 px-4 text-right">Standard Rate</th>
                  <th className="py-3 px-4 text-center">Available Capacity</th>
                  <th className="py-3 px-4 text-center">Initial Rating</th>
                  <th className="py-3 px-4 text-center">Verified Performance</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {workforce.map((m) => {
                  const isActive = m.is_active !== false;
                  const isActionLoading = actionLoadingId === m.id;
                  const hasEvidence = Boolean(m.has_sufficient_evidence);

                  return (
                    <tr key={m.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-4 font-semibold text-white whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-white">{m.full_name}</span>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            {m.is_synthetic ? (
                              <span className="text-[10px] text-amber-300 bg-amber-500/10 px-1 rounded border border-amber-500/20">
                                Synthetic Demo
                              </span>
                            ) : (
                              <span className="text-[10px] text-emerald-300 bg-emerald-500/10 px-1 rounded border border-emerald-500/20">
                                Real Contributor
                              </span>
                            )}
                            <span className={`text-[10px] font-semibold px-1 rounded border ${
                              isActive
                                ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                                : 'text-slate-400 bg-slate-800 border-slate-700'
                            }`}>
                              {isActive ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-300 whitespace-nowrap font-medium">
                        {m.role}
                      </td>
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="flex flex-wrap gap-1">
                          {m.skills.map((s) => {
                            const prof = m.skill_proficiencies?.[s];
                            return (
                              <span
                                key={s}
                                className="bg-slate-950 border border-slate-800 px-1.5 py-0.5 rounded text-[10px] text-slate-300 inline-flex items-center gap-1"
                              >
                                <span>{s}</span>
                                {prof && (
                                  <span className="text-[9px] text-indigo-400 font-semibold bg-indigo-500/10 px-1 rounded">
                                    {prof}
                                  </span>
                                )}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono">
                        {m.experience_years} yrs
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-semibold text-white">
                        ${m.hourly_rate.toFixed(2)}/hr
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <div className="inline-flex items-center gap-1.5">
                          <span className={`font-mono font-bold ${
                            m.availability_pct >= 70 ? 'text-emerald-400' : 'text-amber-400'
                          }`}>
                            {m.availability_pct}%
                          </span>
                          <span className="text-[10px] text-slate-500">
                            ({((m.max_weekly_hours * m.availability_pct) / 100).toFixed(0)}h/wk)
                          </span>
                        </div>
                      </td>
                      {/* Distinct Column 1: Initial Manager Assessed Score */}
                      <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-300">
                        {m.initial_assessed_score != null ? `${m.initial_assessed_score}%` : '—'}
                      </td>
                      {/* Distinct Column 2: Objective Verified Delivery Performance Score */}
                      <td className="py-3.5 px-4 text-center">
                        {hasEvidence && m.performance_score != null ? (
                          <div className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-mono font-bold text-[11px]">
                            <Award className="h-3 w-3" />
                            <span>{m.performance_score.toFixed(1)}% Verified</span>
                          </div>
                        ) : (
                          <span className="text-[10px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700 whitespace-nowrap">
                            Insufficient performance history
                          </span>
                        )}
                      </td>
                      {/* Actions: Score History & Activate/Deactivate */}
                      <td className="py-3.5 px-4 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => handleOpenScoreHistory(m)}
                            className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-[11px] font-medium transition cursor-pointer"
                            title="View Score History & Evidence"
                          >
                            <History className="h-3 w-3 text-indigo-400" />
                            <span>History</span>
                          </button>
                          {isManager && (
                            <button
                              onClick={() => handleToggleMemberActive(m)}
                              disabled={isActionLoading}
                              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium border transition cursor-pointer disabled:opacity-40 ${
                                isActive
                                  ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/20'
                                  : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/20'
                              }`}
                              title={isActive ? 'Deactivate Member' : 'Activate Member'}
                            >
                              <Power className="h-3 w-3" />
                              <span>{isActive ? 'Deactivate' : 'Activate'}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: MANAGER-ONLY MEMBER ONBOARDING                                    */}
      {/* ========================================================================= */}
      {isOnboardingOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Onboard Team Contributor</h3>
              </div>
              <button
                onClick={() => setIsOnboardingOpen(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Creates a persistent contributor profile. Initial ratings are documented separately from future project delivery outcomes. New contributors start with an explicit <span className="text-amber-300 font-semibold">&ldquo;Insufficient performance history&rdquo;</span> state until project deliverables are completed.
            </p>

            {onboardError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{onboardError}</span>
              </div>
            )}

            <form onSubmit={handleOnboardSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={onboardForm.full_name}
                    onChange={(e) => setOnboardForm({ ...onboardForm, full_name: e.target.value })}
                    placeholder="e.g. Jordan Blake"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Primary Role *</label>
                  <select
                    value={onboardForm.role}
                    onChange={(e) => setOnboardForm({ ...onboardForm, role: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    {COMMON_ROLES.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Experience (Years)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={onboardForm.experience_years}
                    onChange={(e) => setOnboardForm({ ...onboardForm, experience_years: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Standard Rate ($/hr)</label>
                  <input
                    type="number"
                    step="1"
                    min="10"
                    value={onboardForm.hourly_rate}
                    onChange={(e) => setOnboardForm({ ...onboardForm, hourly_rate: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Availability (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={onboardForm.availability_pct}
                    onChange={(e) => setOnboardForm({ ...onboardForm, availability_pct: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Weekly Max Capacity (hrs)</label>
                  <input
                    type="number"
                    min="10"
                    max="60"
                    value={onboardForm.max_weekly_hours}
                    onChange={(e) => setOnboardForm({ ...onboardForm, max_weekly_hours: parseFloat(e.target.value) || 40 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Initial Manager Rating (0–100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={onboardForm.initial_assessed_score}
                    onChange={(e) => setOnboardForm({ ...onboardForm, initial_assessed_score: parseFloat(e.target.value) || 80 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <span className="text-[10px] text-slate-500">Documented initial baseline (distinct from delivery score)</span>
                </div>
              </div>

              <div className="text-xs">
                <label className="block text-slate-300 font-medium mb-1">Skills (Comma-separated) *</label>
                <input
                  type="text"
                  required
                  value={onboardForm.skills_text}
                  onChange={(e) => {
                    const text = e.target.value;
                    const parsed = text.split(',').map((s) => s.trim()).filter(Boolean);
                    const newProfs: Record<string, string> = { ...onboardForm.skill_proficiencies };
                    parsed.forEach((s) => {
                      if (!newProfs[s]) newProfs[s] = 'Advanced';
                    });
                    setOnboardForm({ ...onboardForm, skills_text: text, skill_proficiencies: newProfs });
                  }}
                  placeholder="e.g. React, TypeScript, GraphQL, Node.js"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Skill Proficiency Mapping */}
              <div className="text-xs space-y-1.5 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <label className="block text-slate-300 font-semibold mb-1">Skill Proficiency Ratings</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {onboardForm.skills_text.split(',').map((s) => s.trim()).filter(Boolean).map((s) => (
                    <div key={s} className="flex flex-col">
                      <span className="text-[11px] text-slate-400 font-medium truncate">{s}</span>
                      <select
                        value={onboardForm.skill_proficiencies[s] || 'Advanced'}
                        onChange={(e) => setOnboardForm({
                          ...onboardForm,
                          skill_proficiencies: { ...onboardForm.skill_proficiencies, [s]: e.target.value },
                        })}
                        className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-white focus:outline-none"
                      >
                        {PROFICIENCY_LEVELS.map((lvl) => (
                          <option key={lvl} value={lvl}>{lvl}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsOnboardingOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={onboardSubmitting}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition cursor-pointer disabled:opacity-50"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>{onboardSubmitting ? 'Onboarding...' : 'Onboard Contributor'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: PERFORMANCE SCORE HISTORY & AUTHORIZED CORRECTIONS              */}
      {/* ========================================================================= */}
      {selectedMemberForHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <Award className="h-5 w-5 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">{selectedMemberForHistory.full_name}</h3>
                  <span className="text-xs text-slate-400 font-medium">({selectedMemberForHistory.role})</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs">
                  <span className="text-slate-400">
                    Initial Rating: <strong className="text-white">{selectedMemberForHistory.initial_assessed_score ?? '—'}%</strong>
                  </span>
                  <span className="text-slate-400">
                    Verified Performance:{' '}
                    <strong className={selectedMemberForHistory.performance_score ? 'text-emerald-400' : 'text-amber-400'}>
                      {selectedMemberForHistory.performance_score ? `${selectedMemberForHistory.performance_score.toFixed(1)}%` : 'Insufficient history'}
                    </strong>
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedMemberForHistory(null)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-1">
              <button
                onClick={() => setHistoryActiveTab('history')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  historyActiveTab === 'history' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Score History ({historyRecords.length})
              </button>
              <button
                onClick={() => setHistoryActiveTab('evidence')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  historyActiveTab === 'evidence' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Contributing Evidence ({evidenceRecords.length})
              </button>
              {isManager && (
                <button
                  onClick={() => setHistoryActiveTab('correction')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                    historyActiveTab === 'correction' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Authorized Correction
                </button>
              )}
            </div>

            {historyLoading ? (
              <div className="py-8 text-center text-slate-500 text-xs">Loading performance records...</div>
            ) : (
              <>
                {/* TAB A: SCORE HISTORY */}
                {historyActiveTab === 'history' && (
                  <div className="space-y-3">
                    {historyRecords.length === 0 ? (
                      <div className="py-8 text-center text-slate-500 text-xs">
                        No previous score versions recorded yet. Initial profile state.
                      </div>
                    ) : (
                      <div className="max-h-72 overflow-y-auto space-y-2">
                        {historyRecords.map((h) => (
                          <div
                            key={h.id}
                            className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-start justify-between gap-3 text-xs"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-white font-mono">v{h.score_version}</span>
                                <span className="font-mono font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                                  {h.performance_score.toFixed(1)}% Score
                                </span>
                                {h.is_manual_correction ? (
                                  <span className="text-[10px] text-amber-300 bg-amber-500/10 px-1.5 py-0.2 rounded border border-amber-500/20 font-semibold">
                                    Manual Correction
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-1.5 py-0.2 rounded border border-indigo-500/20">
                                    Automatic Recalculation
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-400">
                                Formula: <span className="font-mono text-slate-300">{h.formula_version || 'v2.0'}</span> &bull; Delivery: <strong className="text-white">{h.delivery_score ?? '—'}%</strong> &bull; Quality: <strong className="text-white">{h.quality_score ?? '—'}%</strong>
                              </div>
                              {h.correction_reason && (
                                <p className="text-[11px] text-amber-200/90 italic bg-amber-500/5 p-1.5 rounded border border-amber-500/10">
                                  Correction Note: {h.correction_reason}
                                </p>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-500 whitespace-nowrap">
                              {new Date(h.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB B: CONTRIBUTING EVIDENCE */}
                {historyActiveTab === 'evidence' && (
                  <div className="space-y-3">
                    {evidenceRecords.length === 0 ? (
                      <div className="py-8 text-center text-slate-500 text-xs">
                        No task delivery evidence logged yet. Evidence is captured automatically upon task progress and completion.
                      </div>
                    ) : (
                      <div className="max-h-72 overflow-y-auto space-y-2">
                        {evidenceRecords.map((ev) => (
                          <div
                            key={ev.id}
                            className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-indigo-400">{ev.task_code || 'Task'}</span>
                                <span className="font-semibold text-white capitalize">{ev.event_type.replace('_', ' ')}</span>
                                {ev.was_blocked_externally && (
                                  <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-1.5 py-0.2 rounded border border-indigo-500/20">
                                    External Delay Protected
                                  </span>
                                )}
                              </div>
                              <span className="text-[10px] text-slate-500">
                                {new Date(ev.created_at).toLocaleDateString()}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-[11px] text-slate-400">
                              <span>Planned: <strong className="text-slate-200">{ev.planned_hours ?? '—'}h</strong></span>
                              <span>Actual: <strong className="text-slate-200">{ev.actual_hours ?? '—'}h</strong></span>
                              <span>Variance: <strong className="text-slate-200">{ev.effort_variance_ratio ? `${(ev.effort_variance_ratio * 100).toFixed(0)}%` : '—'}</strong></span>
                              <span>Quality: <strong className="text-emerald-400 capitalize">{ev.quality_outcome || 'Pass'}</strong></span>
                            </div>
                            {ev.evidence_notes && (
                              <p className="text-[11px] text-slate-400 italic">
                                &ldquo;{ev.evidence_notes}&rdquo;
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB C: AUTHORIZED CORRECTION FORM */}
                {historyActiveTab === 'correction' && isManager && (
                  <form onSubmit={handleScoreCorrectionSubmit} className="space-y-4 p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                    <p className="text-slate-400 leading-relaxed">
                      Delivery managers can submit an authorized correction for exceptional circumstances (e.g. post-delivery client commendation or unrecorded external constraints). An immutable audit log entry will be created.
                    </p>

                    {correctionSuccessMsg && (
                      <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded flex items-center gap-2">
                        <Check className="h-4 w-4 shrink-0" />
                        <span>{correctionSuccessMsg}</span>
                      </div>
                    )}

                    {correctionErrorMsg && (
                      <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{correctionErrorMsg}</span>
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-300 font-medium mb-1">Corrected Score (0–100) *</label>
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          max="100"
                          required
                          value={correctionScore}
                          onChange={(e) => setCorrectionScore(parseFloat(e.target.value) || 0)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-indigo-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Audit Justification / Correction Reason *</label>
                      <textarea
                        required
                        rows={3}
                        value={correctionReason}
                        onChange={(e) => setCorrectionReason(e.target.value)}
                        placeholder="Provide formal explanation for this correction (e.g. Verified zero-defect retrospective outcome)..."
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={correctionSubmitting}
                        className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold transition cursor-pointer disabled:opacity-50"
                      >
                        <Shield className="h-3.5 w-3.5" />
                        <span>{correctionSubmitting ? 'Recording Audit...' : 'Submit Authorized Correction'}</span>
                      </button>
                    </div>
                  </form>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
