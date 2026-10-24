export interface ProjectRisk {
  id: string;
  tenant_id: string;
  project_id: string;
  risk_code: string;
  title: string;
  category: string;
  description: string;
  likelihood: number;
  impact: number;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  supporting_evidence?: string;
  mitigation_strategy?: string;
  risk_owner?: string;
  status: 'identified' | 'mitigated' | 'accepted' | 'closed';
  source?: 'deterministic' | 'ai_extracted';
  created_at: string;
}

export interface FeasibilityDimension {
  status: 'feasible' | 'caution' | 'infeasible';
  score: number;
  notes: string;
}

export interface FeasibilityOverview {
  overall_status: string;
  overall_score: number;
  dimensions: Record<string, FeasibilityDimension>;
  limitations: string[];
  summary: string;
  risks: ProjectRisk[];
}
