export interface ProjectEstimate {
  id: string;
  tenant_id: string;
  project_id: string;
  baseline_version: number;
  total_pert_hours: number;
  total_labor_cost: number;
  contingency_pct: number;
  contingency_cost: number;
  total_cost: number;
  currency: string;
  estimated_duration_days: number;
  critical_path_tasks: string[];
  role_breakdown: Record<string, { hours: number; cost: number; rate: number }>;
  rate_card_version: string;
  created_at: string;
}
