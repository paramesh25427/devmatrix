export interface WorkforceMember {
  id: string;
  tenant_id: string;
  user_id?: string;
  full_name: string;
  role: string;
  hourly_rate: number;
  currency: string;
  skills: string[];
  skill_proficiencies?: Record<string, string>;
  experience_years: number;
  availability_pct: number;
  max_weekly_hours: number;
  active_projects_count: number;
  initial_assessed_score?: number;
  performance_score?: number;
  has_sufficient_evidence?: boolean;
  performance_score_version?: number;
  performance_status_label?: string;
  is_active?: boolean;
  is_synthetic?: boolean;
  created_by_user_id?: string;
  created_by_user_email?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AlternativeCandidate {
  candidate_id: string;
  candidate_name: string;
  role: string;
  hourly_rate?: number;
  match_score: number;
  skill_score: number;
  availability_score: number;
  experience_score: number;
  workload_score: number;
  performance_score?: number;
  rationale: string;
}

export interface TeamRecommendation {
  id: string;
  tenant_id: string;
  project_id: string;
  task_id?: string;
  task_code?: string;
  task_title?: string;
  role_needed: string;
  candidate_id: string;
  candidate_name: string;
  match_score: number;
  skill_score: number;
  availability_score: number;
  experience_score: number;
  workload_score: number;
  performance_score?: number;
  rationale: string;
  is_synthetic?: boolean;
  manager_status: 'proposed' | 'approved' | 'rejected' | 'overridden';
  manager_notes?: string;
  alternatives?: AlternativeCandidate[];
  created_at: string;
  reviewed_at?: string;
}

export interface MemberPerformanceEvidence {
  id: string;
  member_id: string;
  project_id: string;
  task_id: string;
  task_code?: string;
  event_type: string;
  planned_hours?: number;
  actual_hours?: number;
  effort_variance_ratio?: number;
  on_schedule?: boolean;
  was_blocked_externally?: boolean;
  quality_outcome?: string;
  evidence_notes?: string;
  created_at: string;
}

export interface MemberPerformanceScoreHistory {
  id: string;
  member_id: string;
  score_version: number;
  performance_score: number;
  has_sufficient_evidence: boolean;
  delivery_score?: number;
  quality_score?: number;
  formula_version?: string;
  contributing_evidence_count?: number;
  contributing_evidence_json?: string;
  is_manual_correction: boolean;
  correction_reason?: string;
  created_at: string;
  updated_by_user_email?: string;
}

export interface ScoreCorrectionRequest {
  corrected_score: number;
  reason: string;
}

export interface OnboardMemberRequest {
  full_name: string;
  role: string;
  hourly_rate: number;
  skills: string[];
  skill_proficiencies?: Record<string, string>;
  experience_years: number;
  availability_pct: number;
  max_weekly_hours?: number;
  initial_assessed_score?: number;
}

export interface AssignedTaskSummary {
  task_id: string;
  task_code: string;
  title: string;
  status: string;
  expected_hours: number;
  actual_hours: number;
  progress_percentage: number;
}

export interface MemberWorkload {
  member_id: string;
  full_name: string;
  role: string;
  hourly_rate: number;
  skills: string[];
  experience_years: number;
  max_weekly_hours: number;
  availability_pct: number;
  nominal_weekly_hours: number;
  assigned_tasks_count: number;
  total_planned_hours: number;
  total_actual_hours: number;
  global_planned_hours: number;
  utilization_pct: number;
  is_overallocated: boolean;
  overallocated_hours: number;
  remaining_capacity_hours: number;
  status_level: 'overallocated' | 'optimal' | 'underutilized';
  assigned_tasks: AssignedTaskSummary[];
}

export interface TeamCapacitySummary {
  project_id: string;
  total_members: number;
  total_nominal_capacity_hours: number;
  total_planned_effort_hours: number;
  total_actual_effort_hours: number;
  team_utilization_pct: number;
  overallocated_members_count: number;
  overallocated_members: string[];
  optimal_count: number;
  underutilized_count: number;
  members: MemberWorkload[];
}

export interface QualifiedMemberSummary {
  id: string;
  name: string;
  role: string;
  experience_years: number;
  availability_pct: number;
}

export interface SkillCoverageTask {
  task_id: string;
  task_code: string;
  title: string;
  required_role: string;
}

export interface SkillCoverageItem {
  skill: string;
  tasks_count: number;
  tasks: SkillCoverageTask[];
  qualified_count: number;
  qualified_members: QualifiedMemberSummary[];
  coverage_status: 'covered' | 'scarce' | 'missing';
}

export interface SkillGapAnalysis {
  project_id: string;
  total_skills_required: number;
  covered_skills_count: number;
  scarce_skills_count: number;
  missing_skills_count: number;
  skill_coverage_score: number;
  health_status: 'healthy' | 'moderate' | 'critical';
  skills: SkillCoverageItem[];
  upskilling_signals: string[];
}
