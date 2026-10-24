export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface SourceReference {
  source_type: string;
  location: string;
  excerpt?: string | null;
}

export interface RequirementItem {
  id: string;
  title: string;
  description: string;
  category: string;
  source_references: SourceReference[];
  confidence: ConfidenceLevel;
  needs_verification: boolean;
  verification_reason?: string | null;
}

export interface RiskItem {
  id: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  mitigation_hint?: string | null;
  source_reference?: SourceReference | null;
}

export interface MissingInfoItem {
  id: string;
  topic: string;
  question: string;
  impact: 'high' | 'medium' | 'low';
}

export interface ProjectScope {
  deliverables: string[];
  scope_inclusions: string[];
  scope_exclusions: string[];
}

export interface ProjectRequirementsData {
  project_summary: string;
  objectives: string[];
  scope: ProjectScope;
  functional_requirements: RequirementItem[];
  non_functional_requirements: RequirementItem[];
  constraints: string[];
  dependencies: string[];
  assumptions: string[];
  risks: RiskItem[];
  missing_information: MissingInfoItem[];
  overall_confidence: number;
  uncertainty_notes: string[];
}

export interface ProviderAttemptLog {
  provider: string;
  model: string;
  duration_ms: number;
  attempt_count: number;
  status: string;
  error_category?: string | null;
}

export interface RequirementDraftResponse {
  id: string;
  document_id: string;
  document_name: string;
  provider_used: string;
  model_used: string;
  status: 'draft_ready' | 'failed';
  review_status: 'pending_review' | 'approved' | 'rejected';
  manager_notes?: string | null;
  attempt_history: ProviderAttemptLog[];
  requirements?: ProjectRequirementsData | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewUpdateRequest {
  review_status: 'approved' | 'rejected' | 'pending_review';
  manager_notes?: string | null;
}
